"""Migration helpers for legacy knob names, prefs files, and foreign anchor rigs.

This module is the single source of truth for:

- ``migrate_script()`` — rewrite legacy ``paste_hidden_*`` and ``copy_hidden_*``
  knobs (and the legacy PyScript_Knob button knobs ``reconnect_link``,
  ``reconnect_child_links``, ``rename_anchor``, ``set_anchor_color``) on every
  node in the current script to the unified ``anchors_*`` namespace.
- ``migrate_to_stemless_names()`` — rewrite stored anchor references from the
  old ``scriptStem.fullName`` format to the new ``fullName``-only format.
- ``migrate_prefs_files()`` — copy the legacy ``paste_hidden_prefs.json`` to
  the new ``anchors_prefs.json`` location when the new file is absent.
- ``migrate_palette_file()`` — load custom colours from the legacy
  ``paste_hidden_user_palette.json`` into ``prefs.custom_colors`` when no new
  prefs file exists yet.
- ``upgrade_to_anchors()`` — adopt an anchor-like rig built by *another* tool
  (a labelled, coloured NoOp/Dot/PostageStamp with hidden-input nodes pointing
  at it) as real anchors and Links.  See the "Upgrade to Anchors" section below.

All functions are idempotent: calling them multiple times on already-migrated
state is a no-op.

CRITICAL ORDERING: ``migrate_script()`` is registered via
``nuke.addOnScriptLoad`` in ``menu.py`` so it runs before any other code path
reads the new constants from a not-yet-migrated script.
"""

import json
import os

import nuke

import constants
from constants import (
    ANCHOR_PREFIX,
    ANCHOR_RECONNECT_KNOB_NAME,
    ANCHOR_RENAME_KNOB_NAME,
    ANCHOR_SET_COLOR_KNOB_NAME,
    DOT_ANCHOR_KNOB_NAME,
    DOT_ANCHOR_MIN_FONT_SIZE,
    DOT_ANCHOR_PREFIX,
    DOT_TYPE_KNOB_NAME,
    HIDDEN_INPUT_CLASSES,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    NAME_SOURCE_AUTO,
    NAME_SOURCE_LABEL,
    NAME_SOURCE_NODE_NAME,
    TAB_NAME,
    UPGRADE_SCOPE_SCRIPT,
    UPGRADE_SCOPE_SELECTED,
)
from link import (
    get_fully_qualified_node_name,
    is_anchor,
    is_link,
    mark_dot_as_anchor,
    setup_link_node,
)

# OLD_PREFS_PATH, PREFS_PATH and USER_PALETTE_PATH are read via the constants
# module attribute every call — tests in tests/test_prefs.py monkeypatch these
# at the constants-module level, and the prefs migrators must honour the live
# values, not values frozen at import time.


# ---------------------------------------------------------------------------
# Legacy → new knob-name mapping.
#
# Each entry is keyed by the OLD knob name a .nk file may carry; the value
# describes the NEW knob name and the kind of knob to re-create.
#
#   kind == 'tab'      → nuke.Tab_Knob, no value transfer (tabs are containers)
#   kind == 'string'   → nuke.String_Knob; value is preserved across rename
#   kind == 'pyscript' → nuke.PyScript_Knob; value (button label and python
#                        body) is re-created from the canonical button-script
#                        body that anchor.py / link.py produce when adding the
#                        knob to a fresh node.  The OLD knob's stored python
#                        body is intentionally discarded — pre-existing scripts
#                        in the wild may have stale code, and the canonical
#                        body is what every fresh anchor/link node carries.
# ---------------------------------------------------------------------------
LEGACY_TO_NEW_KNOB_NAMES = {
    'copy_hidden_tab': {
        'new_name': TAB_NAME,
        'kind': 'tab',
        'label': None,
        'body': None,
    },
    'copy_hidden_input_node': {
        'new_name': KNOB_NAME,
        'kind': 'string',
        'label': None,
        'body': None,
    },
    'paste_hidden_dot_anchor': {
        'new_name': DOT_ANCHOR_KNOB_NAME,
        'kind': 'string',
        'label': None,
        'body': None,
    },
    'paste_hidden_dot_type': {
        'new_name': DOT_TYPE_KNOB_NAME,
        'kind': 'string',
        'label': None,
        'body': None,
    },
    'reconnect_link': {
        'new_name': LINK_RECONNECT_KNOB_NAME,
        'kind': 'pyscript',
        'label': 'Reconnect',
        'body': 'import link\nlink.reconnect_link_node(nuke.thisNode())',
    },
    'reconnect_child_links': {
        'new_name': ANCHOR_RECONNECT_KNOB_NAME,
        'kind': 'pyscript',
        'label': 'Reconnect Child Links',
        'body': 'import anchor\nanchor.reconnect_anchor_node(nuke.thisNode())',
    },
    'rename_anchor': {
        'new_name': ANCHOR_RENAME_KNOB_NAME,
        'kind': 'pyscript',
        'label': 'Rename',
        'body': 'import anchor\nanchor.rename_anchor(nuke.thisNode())',
    },
    'set_anchor_color': {
        'new_name': ANCHOR_SET_COLOR_KNOB_NAME,
        'kind': 'pyscript',
        'label': 'Set Color',
        'body': 'import anchor\nanchor.set_anchor_color(nuke.thisNode())',
    },
}


def _migrate_one_knob(node, old_name, spec):
    """Migrate a single knob on *node* from *old_name* to spec['new_name'].

    Idempotency contract:
      - acts only when the old knob is present AND the new knob is absent
      - on mixed state (both present), leaves both untouched
    Returns True iff a knob was migrated, False otherwise.
    """
    knobs_on_node = node.knobs()
    new_name = spec['new_name']
    if old_name not in knobs_on_node:
        return False
    if new_name in knobs_on_node:
        # Mixed state: both old and new present. Leave both untouched —
        # this matches the existing dot-knob migrator's contract.
        return False

    kind = spec['kind']
    if kind == 'tab':
        new_knob = nuke.Tab_Knob(new_name)
        new_knob.setFlag(nuke.INVISIBLE)
        new_knob.setVisible(False)
        node.addKnob(new_knob)
    elif kind == 'string':
        old_value = node[old_name].getValue()
        new_knob = nuke.String_Knob(new_name)
        new_knob.setFlag(nuke.INVISIBLE)
        new_knob.setVisible(False)
        node.addKnob(new_knob)
        node[new_name].setValue(old_value)
    elif kind == 'pyscript':
        new_knob = nuke.PyScript_Knob(new_name, spec['label'], spec['body'])
        node.addKnob(new_knob)
    else:
        # Defensive: unknown kind → do nothing rather than crash a script load.
        return False

    node.removeKnob(node[old_name])
    return True


def migrate_script():
    """Rewrite legacy knob names on every node in the current script.

    Scans every node (including inside Groups) and rewrites legacy
    ``paste_hidden_*``, ``copy_hidden_*``, ``reconnect_link``,
    ``reconnect_child_links``, ``rename_anchor`` and ``set_anchor_color``
    knobs to their unified ``anchors_*`` equivalents.

    Idempotent: re-running on an already-migrated script is a no-op.

    Wired via ``nuke.addOnScriptLoad`` in ``menu.py`` so that newly opened
    scripts are migrated before any code path reads the new constants.

    Usage (Python console):
        import anchors
        anchors.migrate_script()
    """
    nodes_updated = 0
    knobs_renamed = 0

    for node in nuke.allNodes(recurseGroups=True):
        node_changed = False
        for old_name, spec in LEGACY_TO_NEW_KNOB_NAMES.items():
            if _migrate_one_knob(node, old_name, spec):
                knobs_renamed += 1
                node_changed = True
        if node_changed:
            nodes_updated += 1

    print(
        "anchors.migrate_script(): updated "
        f"{nodes_updated} node(s), renamed {knobs_renamed} knob(s)."
    )


def migrate_to_stemless_names():
    """Rewrite stored anchor references from old (stem-prefixed) to new format.

    Old format: ``scriptStem.fullName``       e.g. ``myScript.Anchor_Foo``
    New format: ``fullName`` only             e.g. ``Anchor_Foo`` or ``Group1.Anchor_Foo``

    Scans every node in the current script (including inside Groups) that has a
    ``KNOB_NAME`` knob.  If the stored value cannot be resolved by ``nuke.toNode()``
    but CAN be resolved after stripping the first segment, the stored value is
    rewritten to the shorter form.  References that cannot be resolved either way
    (orphaned or pointing to a node in a different script) are left unchanged.

    Prints a summary of how many nodes were updated.

    Usage (Python console or Anchors menu):
        import anchors
        anchors.migrate_to_stemless_names()
    """
    nodes_updated = 0

    for node in nuke.allNodes(recurseGroups=True):
        if KNOB_NAME not in node.knobs():
            continue

        stored_name = node[KNOB_NAME].getText()
        if not stored_name:
            continue

        name_parts = stored_name.split('.')
        if len(name_parts) <= 1:
            # Single segment — already new format, nothing to strip
            continue

        if nuke.toNode(stored_name) is not None:
            # Resolves as-is: stored value is already new format (or first segment
            # happens to be a group name that Nuke resolves correctly)
            continue

        name_without_stem = '.'.join(name_parts[1:])
        if nuke.toNode(name_without_stem) is not None:
            # Old format confirmed: full value failed but stripped value resolves
            node[KNOB_NAME].setValue(name_without_stem)
            nodes_updated += 1
        # else: orphaned or cross-script reference — leave unchanged

    print(f"anchors.migrate_to_stemless_names(): updated {nodes_updated} node(s).")


# ---------------------------------------------------------------------------
# Prefs-file migrators.
#
# These are kept as two separate top-level functions so each can be tested
# (and mocked) independently.  Both are idempotent and silent-fallback on
# missing/corrupt files.
# ---------------------------------------------------------------------------

def migrate_prefs_files():
    """Copy ``paste_hidden_prefs.json`` to ``anchors_prefs.json`` if needed.

    Called only when ``anchors_prefs.json`` does not exist but
    ``paste_hidden_prefs.json`` does.  Never modifies the old file or an
    existing new file.  Silent no-op if the new file already exists or the
    old file is absent or unreadable.
    """
    if os.path.exists(constants.PREFS_PATH):
        return
    if not os.path.exists(constants.OLD_PREFS_PATH):
        return
    try:
        import shutil
        shutil.copy2(constants.OLD_PREFS_PATH, constants.PREFS_PATH)
    except OSError:
        pass


def migrate_palette_file():
    """Load custom colours from the legacy palette file into ``prefs.custom_colors``.

    Called only when ``anchors_prefs.json`` does not exist.  Never writes to the
    old palette file.  Silent no-op if the new prefs file already exists or the
    old palette file is absent or corrupt; on any failure ``prefs.custom_colors``
    is set to ``[]``.
    """
    if os.path.exists(constants.PREFS_PATH):
        return
    import prefs as prefs_module
    try:
        with open(constants.USER_PALETTE_PATH) as file_handle:
            data = json.load(file_handle)
        prefs_module.custom_colors = [
            int(color_value) for color_value in data
            if isinstance(color_value, (int, float))
        ]
    except (OSError, ValueError, json.JSONDecodeError):
        prefs_module.custom_colors = []


# ---------------------------------------------------------------------------
# Upgrade to Anchors — adopt an anchor-like rig built by another tool.
#
# Other "pointer"/"stamp" tools produce the same shape as ours without our
# machinery: a labelled, coloured NoOp (or Dot, or PostageStamp) under a source
# node, with hidden-input nodes elsewhere in the script wired back to it.  The
# upgrade converts those nodes IN PLACE rather than replacing them, because:
#
#   - the children keep their class (a PostageStamp child stays a PostageStamp
#     while becoming a perfectly valid Link — is_link() is knob-based, not
#     class-based), their position, and every downstream connection they have;
#   - the parent keeps any non-link downstream wires it may also have.
#
# In-place conversion is the same gesture anchors._convert_hidden_dot_in_place()
# already performs for a single freshly-hidden Dot; this generalises it to a
# whole rig, or a whole script, at once.
# ---------------------------------------------------------------------------

# Characters trimmed from a derived name once a strip prefix/suffix has been
# removed, so "Pointer_Foo" minus "Pointer" yields "Foo" rather than "_Foo".
_AFFIX_SEPARATORS = ' _-'


def _anchor_module():
    """Import ``anchor`` lazily and return the module.

    ``migrations`` must not import ``anchor`` at module level: ``prefs`` imports
    ``migrations`` from inside its own import-time ``_load()``, and ``anchor``
    imports ``prefs``.  A top-level import here would therefore let ``prefs``
    observe a half-initialised ``migrations`` module (anchor → prefs →
    migrations) and fail with an AttributeError.  Every upgrade helper resolves
    the module through this function instead.
    """
    import anchor
    return anchor


class UpgradeOptions:
    """How anchor-like nodes should be turned into real anchors and Links.

    Attributes
    ----------
    include_noop_parents : bool
        Upgrade NoOp/PostageStamp parents.
    include_dot_parents : bool
        Upgrade Dot parents.
    noop_name_source, dot_name_source : str
        One of ``NAME_SOURCE_AUTO`` (the node's label if it has one, else its
        name), ``NAME_SOURCE_NODE_NAME`` or ``NAME_SOURCE_LABEL``.  The two kinds
        of parent are configured separately because a foreign NoOp usually
        carries a meaningful node name while a Dot is usually named ``Dot17``
        and carries its meaning in the label.
    strip_prefix, strip_suffix : str
        Literal leading/trailing text removed from the derived name, e.g. a
        ``Pointer_`` prefix turning ``Pointer_Foo`` into ``Foo``.  A strip that
        would consume the whole name is ignored.
    keep_colors : bool
        True keeps each parent's existing tile colour; False replaces it with the
        colour the plugin derives for a new anchor (backdrop, then source node,
        then the default purple).  Dot anchors are excluded from this choice —
        the plugin manages their colour and keeps them at the default purple.
    """

    def __init__(self, include_noop_parents=True, include_dot_parents=True,
                 noop_name_source=NAME_SOURCE_AUTO, dot_name_source=NAME_SOURCE_AUTO,
                 strip_prefix='', strip_suffix='', keep_colors=True):
        self.include_noop_parents = include_noop_parents
        self.include_dot_parents = include_dot_parents
        self.noop_name_source = noop_name_source
        self.dot_name_source = dot_name_source
        self.strip_prefix = strip_prefix
        self.strip_suffix = strip_suffix
        self.keep_colors = keep_colors

    @classmethod
    def from_dict(cls, option_values):
        """Build options from the plain dict returned by UpgradeAnchorsDialog."""
        return cls(
            include_noop_parents=bool(option_values.get('include_noop_parents', True)),
            include_dot_parents=bool(option_values.get('include_dot_parents', True)),
            noop_name_source=option_values.get('noop_name_source', NAME_SOURCE_AUTO),
            dot_name_source=option_values.get('dot_name_source', NAME_SOURCE_AUTO),
            strip_prefix=option_values.get('strip_prefix', ''),
            strip_suffix=option_values.get('strip_suffix', ''),
            keep_colors=bool(option_values.get('keep_colors', True)),
        )


class UpgradePlanEntry:
    """One anchor-like parent plus the link-like children that will follow it.

    Parameters
    ----------
    parent_node : nuke.Node
        The node that becomes an anchor.
    display_name : str
        The name the anchor will display — the Dot's label, or the NoOp anchor's
        node name with ``ANCHOR_PREFIX`` stripped.
    target_node_name : str
        The node name the parent will be given (already made unique).
    children : list of nuke.Node
        The hidden-input nodes that will be stamped as Links to the parent.
    already_anchor : bool
        True when the parent is already a real anchor and only its children need
        upgrading; its name and colour are then left untouched.
    """

    def __init__(self, parent_node, display_name, target_node_name, children,
                 already_anchor=False):
        self.parent_node = parent_node
        self.display_name = display_name
        self.target_node_name = target_node_name
        self.children = children
        self.already_anchor = already_anchor

    def describe(self):
        """Return the one-line summary shown in the dialog's preview list."""
        link_count = len(self.children)
        links = '1 link' if link_count == 1 else f'{link_count} links'
        if self.already_anchor:
            return f"{self.parent_node.name()}  (already an anchor)  →  {links}"
        return f"{self.parent_node.name()}  →  {self.target_node_name}  ({links})"


def _strip_affixes(text, strip_prefix, strip_suffix):
    """Return *text* with *strip_prefix* / *strip_suffix* and separator debris removed.

    A strip that would leave nothing behind is ignored, so a prefix of ``Foo``
    never reduces the node ``Foo`` to an empty name.  Separator characters are
    only trimmed when an affix was actually removed, so an intentionally
    underscore-wrapped name is left alone.
    """
    stripped = text
    affix_removed = False
    if strip_prefix and stripped.startswith(strip_prefix):
        candidate = stripped[len(strip_prefix):]
        if candidate.strip(_AFFIX_SEPARATORS):
            stripped = candidate
            affix_removed = True
    if strip_suffix and stripped.endswith(strip_suffix):
        candidate = stripped[:len(stripped) - len(strip_suffix)]
        if candidate.strip(_AFFIX_SEPARATORS):
            stripped = candidate
            affix_removed = True
    return stripped.strip(_AFFIX_SEPARATORS) if affix_removed else stripped


def _node_label_text(node):
    """Return *node*'s label as a single line of plain text, or ''.

    Nuke labels may carry HTML tags and span several lines; anchors are named
    from a single plain-text line, so the tags are removed (via anchor.py's
    helper, the plugin's single source of truth for label cleaning) and the
    first non-blank line is used.
    """
    if 'label' not in node.knobs():
        return ''
    label_value = node['label'].getValue() or ''
    for line in _anchor_module()._strip_html_tags(label_value).splitlines():
        if line.strip():
            return line.strip()
    return ''


def derive_upgrade_name(parent_node, options):
    """Return the plain-text name *parent_node* should be upgraded under, or ''.

    Applies the name source configured for this kind of parent, then the strip
    prefix/suffix.  The result is not sanitised — callers that need a node name
    pass it through ``anchor.sanitize_anchor_name()``; a Dot's label keeps the
    unsanitised text, matching ``anchor.rename_anchor_to()``.
    """
    if parent_node.Class() == 'Dot':
        name_source = options.dot_name_source
    else:
        name_source = options.noop_name_source

    label_text = _node_label_text(parent_node)
    if name_source == NAME_SOURCE_LABEL:
        raw_name = label_text
    elif name_source == NAME_SOURCE_NODE_NAME:
        raw_name = parent_node.name()
    else:
        raw_name = label_text or parent_node.name()

    return _strip_affixes(raw_name.strip(), options.strip_prefix, options.strip_suffix)


def _is_formal_anchor(node):
    """Return True if *node* already carries an anchor node name.

    Deliberately narrower than ``link.is_anchor()``: a big-labelled Dot passes
    ``is_anchor()`` through the legacy heuristic while still being named
    ``Dot17``, so its FQNN carries no anchor prefix and cross-script link
    resolution cannot recover its name.  Such a Dot is still worth formalising,
    so only an already-prefixed node counts as "leave the name alone".
    """
    node_name = node.name()
    return node_name.startswith(ANCHOR_PREFIX) or node_name.startswith(DOT_ANCHOR_PREFIX)


def _link_like_children_by_parent():
    """Return {parent full name: [child nodes]} for the current group.

    A link-like child is a hidden-input NoOp/Dot/PostageStamp wired to another
    node — the shape every "pointer" tool produces, and the shape our own Links
    have.  Anchors are excluded: an anchor whose input wire is hidden is routine
    (issue #55) and must never be demoted to a Link.
    """
    children_by_parent = {}
    for node in nuke.allNodes():
        if node.Class() not in HIDDEN_INPUT_CLASSES:
            continue
        if 'hide_input' not in node.knobs() or not node['hide_input'].getValue():
            continue
        if is_anchor(node):
            continue
        parent_node = node.input(0)
        if parent_node is None:
            continue
        children_by_parent.setdefault(parent_node.fullName(), []).append(node)
    return children_by_parent


def _child_needs_upgrade(child_node, parent_node, parent_is_renamed):
    """Return True if *child_node* is not already a Link resolving to *parent_node*.

    When the parent is being renamed every child must be restamped, because the
    FQNN each child stores is about to change.  When it is not, children that
    already point at it are left alone — which is what makes a second run of the
    upgrade a no-op.
    """
    if parent_is_renamed:
        return True
    if not is_link(child_node):
        return True
    return child_node[KNOB_NAME].getText() != get_fully_qualified_node_name(parent_node)


def _is_eligible_parent(node, options, children_by_parent):
    """Return True if *node* is an anchor-like parent the options ask us to upgrade."""
    if node.Class() not in HIDDEN_INPUT_CLASSES:
        return False
    if is_link(node) and not is_anchor(node):
        return False  # already one of our Links — a Link is never a parent
    if node.Class() == 'Dot':
        if not options.include_dot_parents:
            return False
    elif not options.include_noop_parents:
        return False
    return bool(children_by_parent.get(node.fullName()))


def _unique_node_name(preferred_name, claimed_names):
    """Return *preferred_name*, or the first free ``<name><n>`` variant.

    Checked against both the live script and the names already claimed earlier
    in the same batch, so upgrading two ``Pointer_Foo``-style nodes that derive
    the same name cannot collide.
    """
    if preferred_name not in claimed_names and nuke.toNode(preferred_name) is None:
        return preferred_name
    index = 1
    while True:
        candidate_name = f"{preferred_name}{index}"
        if candidate_name not in claimed_names and nuke.toNode(candidate_name) is None:
            return candidate_name
        index += 1


def plan_upgrades(candidate_nodes, options):
    """Return the ``UpgradePlanEntry`` list describing what upgrading would do.

    *candidate_nodes* is the pool to consider — the current selection, or every
    node in the group.  Nodes that are not anchor-like parents are skipped, so
    the whole script can be passed in safely.  Nothing is mutated: the plan is
    what the dialog previews and what ``apply_upgrade_plan()`` then applies.
    """
    anchor_module = _anchor_module()
    children_by_parent = _link_like_children_by_parent()

    eligible_parents = [
        node for node in candidate_nodes
        if _is_eligible_parent(node, options, children_by_parent)
    ]
    # A node that is both a parent and someone else's hidden-input child stays a
    # parent: it becomes an anchor, and is excluded from the upstream parent's
    # children so it never ends up being an anchor and a Link at once.
    eligible_parent_names = {node.fullName() for node in eligible_parents}

    claimed_names = set()
    entries = []
    for parent_node in eligible_parents:
        already_anchor = _is_formal_anchor(parent_node)
        children = [
            child_node
            for child_node in children_by_parent[parent_node.fullName()]
            if child_node.fullName() not in eligible_parent_names
            and _child_needs_upgrade(child_node, parent_node, not already_anchor)
        ]
        if not children:
            continue

        if already_anchor:
            entries.append(UpgradePlanEntry(
                parent_node,
                anchor_module.anchor_display_name(parent_node),
                parent_node.name(),
                children,
                already_anchor=True,
            ))
            continue

        derived_name = derive_upgrade_name(parent_node, options)
        sanitized_name = anchor_module.sanitize_anchor_name(derived_name)
        if not sanitized_name:
            continue  # nothing usable to name the anchor with — leave the node alone

        is_dot_parent = parent_node.Class() == 'Dot'
        name_prefix = DOT_ANCHOR_PREFIX if is_dot_parent else ANCHOR_PREFIX
        target_node_name = _unique_node_name(name_prefix + sanitized_name, claimed_names)
        claimed_names.add(target_node_name)
        # A Dot anchor displays its label, so it keeps the unsanitised text; a
        # NoOp anchor displays its node name minus the prefix, which is what
        # anchor.anchor_display_name() will report once it has been renamed.
        display_name = derived_name if is_dot_parent else target_node_name[len(name_prefix):]
        entries.append(UpgradePlanEntry(
            parent_node, display_name, target_node_name, children,
        ))

    return entries


def _convert_parent_to_anchor(entry, options):
    """Turn ``entry.parent_node`` into a real anchor in place."""
    anchor_module = _anchor_module()
    parent_node = entry.parent_node
    existing_color = int(parent_node['tile_color'].value())
    parent_node['label'].setValue(entry.display_name)

    if parent_node.Class() == 'Dot':
        if parent_node['note_font_size'].value() < DOT_ANCHOR_MIN_FONT_SIZE:
            parent_node['note_font_size'].setValue(DOT_ANCHOR_MIN_FONT_SIZE)
        # mark_dot_as_anchor() adds the marker knob, names the Dot after its
        # label and applies the anchor colour Dot anchors always carry.  It is
        # called before setName() because it derives the name from the label and
        # would otherwise undo the de-duplicated name chosen by plan_upgrades().
        mark_dot_as_anchor(parent_node)
        parent_node.setName(entry.target_node_name)
        return

    parent_node.setName(entry.target_node_name)
    if options.keep_colors and existing_color:
        parent_node['tile_color'].setValue(existing_color)
    else:
        parent_node['tile_color'].setValue(int(anchor_module.find_anchor_color(parent_node)))
    _ensure_anchor_knobs(parent_node)


def _ensure_anchor_knobs(anchor_node):
    """Give *anchor_node* the anchor buttons it is missing.

    A node hand-named ``Anchor_Foo`` reads as an anchor but may carry none of the
    buttons a created anchor has.  Each ``add_*_knob()`` helper is a no-op when
    its knob is already present.  Dot anchors are skipped: the only knob the
    plugin puts on them is the marker knob ``mark_dot_as_anchor()`` adds.
    """
    if anchor_node.Class() == 'Dot':
        return
    anchor_module = _anchor_module()
    anchor_module.add_reconnect_anchor_knob(anchor_node)
    anchor_module.add_rename_anchor_knob(anchor_node)
    anchor_module.add_set_color_anchor_knob(anchor_node)


def apply_upgrade_plan(entries, options):
    """Apply *entries* in place; return an ``(anchor_count, link_count)`` tuple.

    Every parent is converted before any child is stamped, so each Link stores
    its anchor's final fully qualified name.
    """
    for entry in entries:
        if entry.already_anchor:
            _ensure_anchor_knobs(entry.parent_node)
        else:
            _convert_parent_to_anchor(entry, options)

    link_count = 0
    for entry in entries:
        for child_node in entry.children:
            # setup_link_node() leaves the child in exactly the state a freshly
            # created Link has: hidden input, "Link: …" label, the anchor's
            # colour, a Reconnect knob and the anchor's FQNN.  The child's class,
            # position and downstream connections are untouched.
            setup_link_node(entry.parent_node, child_node)
            link_count += 1

    return len(entries), link_count


def upgrade_nodes_to_anchors(candidate_nodes, options=None):
    """Upgrade every anchor-like parent in *candidate_nodes* without prompting.

    Returns an ``(anchor_count, link_count)`` tuple.  This is the entry point for
    pipeline scripts; ``upgrade_to_anchors()`` is the interactive one.
    """
    if options is None:
        options = UpgradeOptions()
    return apply_upgrade_plan(plan_upgrades(candidate_nodes, options), options)


def _upgrade_summary(anchor_count, link_count):
    """Return the message shown once an upgrade has been applied."""
    if not anchor_count:
        return "No anchor-like nodes found to upgrade."
    anchors = '1 anchor' if anchor_count == 1 else f'{anchor_count} anchors'
    links = '1 link' if link_count == 1 else f'{link_count} links'
    return f"Upgraded {anchors} and {links}."


def _upgrade_pool(scope, selected_nodes):
    """Return the node pool for *scope* — the selection, or the whole group."""
    if scope == UPGRADE_SCOPE_SELECTED:
        return selected_nodes
    return nuke.allNodes()


def _upgrade_without_dialog(hit_group, selected_nodes):
    """Qt-less fallback: confirm, then upgrade with the default options.

    Only reached when PySide is unavailable (a headless or test session), where
    the options dialog cannot be shown.
    """
    options = UpgradeOptions()
    with hit_group:
        entries = plan_upgrades(selected_nodes or nuke.allNodes(), options)
        if not entries:
            nuke.message(_upgrade_summary(0, 0))
            return
        if not nuke.ask(f"Upgrade {len(entries)} anchor-like node(s) to anchors?"):
            return
        anchor_count, link_count = apply_upgrade_plan(entries, options)
    nuke.message(_upgrade_summary(anchor_count, link_count))


def upgrade_to_anchors():
    """Open the upgrade dialog and adopt the chosen anchor-like nodes.

    This is the ``Edit > Anchors > Upgrade to Anchors...`` entry point.  The
    dialog previews exactly what would change before anything is mutated.

    Usage (Python console):
        import anchors
        anchors.upgrade_to_anchors()
    """
    import prefs
    if not prefs.plugin_enabled:
        return

    # Capture the group context and selection before any Qt event loop runs, so
    # the plan and the mutation both happen in the group the user clicked in.
    hit_group = nuke.lastHitGroup()
    with hit_group:
        selected_nodes = nuke.selectedNodes()

    def preview_provider(option_values):
        options = UpgradeOptions.from_dict(option_values)
        scope = option_values.get('scope', UPGRADE_SCOPE_SCRIPT)
        with hit_group:
            pool = _upgrade_pool(scope, selected_nodes)
            return [entry.describe() for entry in plan_upgrades(pool, options)]

    from colors import UpgradeAnchorsDialog
    if UpgradeAnchorsDialog is None:
        _upgrade_without_dialog(hit_group, selected_nodes)
        return

    dialog = UpgradeAnchorsDialog(
        preview_provider=preview_provider,
        selection_count=len(selected_nodes),
    )
    if dialog.exec_() != UpgradeAnchorsDialog.Accepted:
        return

    option_values = dialog.chosen_options()
    options = UpgradeOptions.from_dict(option_values)
    with hit_group:
        pool = _upgrade_pool(option_values.get('scope', UPGRADE_SCOPE_SCRIPT), selected_nodes)
        anchor_count, link_count = apply_upgrade_plan(plan_upgrades(pool, options), options)
    nuke.message(_upgrade_summary(anchor_count, link_count))
