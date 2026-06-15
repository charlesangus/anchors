"""Anchor system: creation, renaming, reconnection, and the tabtabtab picker."""

import os
import re

import nuke
import nukescripts

try:
    if hasattr(nuke, 'NUKE_VERSION_MAJOR') and nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
    else:
        from PySide2 import QtCore, QtGui, QtWidgets
        from PySide2.QtCore import Qt
except ImportError:
    QtGui = None
    QtWidgets = None
    QtCore = None

import prefs
import tabtabtab_anchors as _tabtabtab
from colors import ColorPaletteDialog, adjust_color_for_backdrop_contrast
from constants import (
    ANCHOR_DEFAULT_COLOR,
    ANCHOR_PREFIX,
    ANCHOR_RECONNECT_KNOB_NAME,
    ANCHOR_RENAME_KNOB_NAME,
    ANCHOR_SET_COLOR_KNOB_NAME,
    DOT_ANCHOR_PREFIX,
    DOT_LABEL_FONT_SIZE_LARGE,
    DOT_LABEL_FONT_SIZE_MEDIUM,
    KNOB_NAME,
    MODULE_ZOOM_MARGIN_FACTOR,
    NODE_LABEL_FONT_SIZE_LARGE,
)
from link import (
    find_anchor_node,
    find_node_color,
    find_smallest_containing_backdrop,
    get_fully_qualified_node_name,
    get_link_class_for_source,
    is_anchor,
    is_link,
    reconnect_link_node,
    setup_link_node,
)


def sanitize_anchor_name(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name.strip())


def _strip_html_tags(text):
    """Remove HTML tags from *text*, handling both closed and unclosed tags.

    Nuke allows unclosed tags in node labels (e.g. ``<b>PLATES``), so this
    uses a simple regex rather than an HTML parser.
    """
    return re.sub(r'<[^>]*>', '', text)


def _find_first_non_dot_input(node):
    """Traverse input(0) upward through Dot nodes and return the first non-Dot node.

    Returns None if the input chain runs out before a non-Dot node is found.
    """
    visited = set()
    current = node.input(0)
    while current is not None:
        node_id = id(current)
        if node_id in visited:
            break  # Guard against cycles
        visited.add(node_id)
        if current.Class() != 'Dot':
            return current
        current = current.input(0)
    return None


def find_anchor_color(anchor):
    """Return the tile color an anchor should display.

    Priority:
      1. Smallest BackdropNode containing the anchor (any input node type).
      2. The effective input node color (with Preferences fallback).
      3. Hard-coded default purple if neither is available.

    For unlabelled Dot inputs, traverses up to the first non-Dot node so that
    the color reflects the actual source rather than an intermediate Dot.
    """
    direct_input = anchor.input(0)

    # Resolve effective input: for unlabelled Dots, walk up to first non-Dot.
    if direct_input is not None and direct_input.Class() == 'Dot':
        dot_label = direct_input['label'].getValue().strip() if 'label' in direct_input.knobs() else ''
        if not dot_label:
            effective_input = _find_first_non_dot_input(direct_input)
        else:
            effective_input = direct_input
    else:
        effective_input = direct_input

    # --- 1. Backdrop color (any input node type) ---
    if effective_input is not None:
        smallest = find_smallest_containing_backdrop(anchor)
        if smallest is not None:
            color = smallest['tile_color'].value()
            if color != 0:
                return adjust_color_for_backdrop_contrast(color)

    # --- 2. Effective input node color (with Preferences fallback) ---
    if effective_input is not None:
        return find_node_color(effective_input)

    # --- 3. Default anchor color ---
    return ANCHOR_DEFAULT_COLOR


def add_reconnect_anchor_knob(node):
    if ANCHOR_RECONNECT_KNOB_NAME in node.knobs():
        return
    # Bug fix: use ANCHOR_RECONNECT_KNOB_NAME (not LINK_RECONNECT_KNOB_NAME) so
    # the guard above actually fires on subsequent calls.
    knob = nuke.PyScript_Knob(ANCHOR_RECONNECT_KNOB_NAME, "Reconnect Child Links",
        """import anchor
anchor.reconnect_anchor_node(nuke.thisNode())""")
    node.addKnob(knob)


def add_rename_anchor_knob(node):
    if ANCHOR_RENAME_KNOB_NAME in node.knobs():
        return
    knob = nuke.PyScript_Knob(ANCHOR_RENAME_KNOB_NAME, "Rename",
        """import anchor
anchor.rename_anchor(nuke.thisNode())""")
    node.addKnob(knob)


def add_set_color_anchor_knob(node):
    """Add a 'Set Color' PyScript_Knob to *node* if it does not already have one.

    Dot anchors are excluded from the color system — this function is a no-op for them.
    """
    if node.Class() == 'Dot':
        return
    if ANCHOR_SET_COLOR_KNOB_NAME in node.knobs():
        return
    knob = nuke.PyScript_Knob(ANCHOR_SET_COLOR_KNOB_NAME, "Set Color",
        """import anchor
anchor.set_anchor_color(nuke.thisNode())""")
    node.addKnob(knob)


def propagate_anchor_color(anchor_node, color_int):
    """Set *anchor_node* tile_color to *color_int* and propagate to all referencing Link nodes.

    Dot anchors have fixed colors managed by the system — this function returns
    early without making any changes for Dot anchors.
    """
    if anchor_node.Class() == 'Dot':
        return
    anchor_node['tile_color'].setValue(color_int)
    for link_node in get_links_for_anchor(anchor_node):
        link_node['tile_color'].setValue(color_int)


def _persist_custom_colors_from_dialog(dialog):
    """Save any newly staged custom colors from *dialog* back to prefs and disk.

    Call this on every accepted ColorPaletteDialog so custom colors added via
    "Custom Color..." persist across sessions.  Only saves when the staged list
    differs from the current prefs.custom_colors to avoid spurious disk writes.
    """
    staged = dialog.chosen_custom_colors()
    if staged != prefs.custom_colors:
        prefs.custom_colors = staged
        prefs.save()


def set_anchor_color(anchor_node):
    """Open the color palette dialog and apply the chosen color to *anchor_node*.

    This is the entry point called by the 'Set Color' PyScript_Knob on the anchor node.
    """
    if ColorPaletteDialog is None:
        return
    if anchor_node.Class() == 'Dot':
        return
    current_color = int(anchor_node['tile_color'].value()) or int(find_anchor_color(anchor_node))
    dialog = ColorPaletteDialog(
        initial_color=current_color,
        show_name_field=False,
        custom_colors=prefs.custom_colors,
    )
    if dialog.exec_() == ColorPaletteDialog.Accepted:
        _persist_custom_colors_from_dialog(dialog)
        chosen_color = dialog.selected_color_int()
        if chosen_color is not None:
            propagate_anchor_color(anchor_node, chosen_color)


def _anchor_sort_key(node):
    """Return a lower-cased sort key for an anchor node.

    Uses the raw label for Dot anchors and the node-name suffix for NoOp
    anchors.  This avoids calling anchor_display_name() (which may trigger an
    allNodes() scan per element when duplicates are present) and keeps the sort
    O(n log n) instead of O(n² log n).

    Both branches return a two-element tuple so Python can compare any two
    anchor nodes without a TypeError.  For Dot anchors, the node name is used
    as a tie-breaker when two Dots share the same label, producing a stable
    and deterministic ordering.
    """
    if node.Class() == 'Dot':
        label = node['label'].getValue().strip().lower()
        return (label, node.name().lower())
    return (node.name()[len(ANCHOR_PREFIX):].lower(), '')


def _dot_anchor_duplicate_labels():
    """Return the set of Dot-anchor labels that appear more than once."""
    from collections import Counter
    dot_labels = [
        n['label'].getValue().strip()
        for n in nuke.allNodes()
        if is_anchor(n) and n.Class() == 'Dot'
    ]
    return {label for label, count in Counter(dot_labels).items() if count > 1}


def anchor_display_name(node, duplicate_dot_labels=None):
    """Return the human-readable display name for an anchor node.

    For Dot anchors whose label appears on more than one Dot anchor, the node
    name is appended in parentheses so the user can tell them apart in the
    tabtabtab picker (issue #34).

    Parameters
    ----------
    node : nuke.Node
        The anchor node.
    duplicate_dot_labels : set[str] or None
        Pre-computed set of ambiguous labels.  When None the function calls
        _dot_anchor_duplicate_labels() itself (one allNodes() scan per call).
        Pass a pre-computed set in loops (e.g. get_items()) to avoid O(n²) scans.
    """
    if node.Class() == 'Dot':
        label = node['label'].getValue().strip()
        if duplicate_dot_labels is None:
            duplicate_dot_labels = _dot_anchor_duplicate_labels()
        if label in duplicate_dot_labels:
            return f"{label} ({node.name()})"
        return label
    return node.name()[len(ANCHOR_PREFIX):]


def all_anchors():
    anchors = [n for n in nuke.allNodes() if is_anchor(n)]
    anchors.sort(key=_anchor_sort_key)
    return anchors


def find_anchor_by_name(display_name):
    """Return the anchor node whose display name equals *display_name*, or None."""
    duplicate_dot_labels = _dot_anchor_duplicate_labels()
    for anchor in all_anchors():
        if anchor_display_name(anchor, duplicate_dot_labels) == display_name:
            return anchor
    return None


def _stored_fqnn_matches_anchor(stored_fqnn, anchor_fqnn, legacy_fqnn):
    """Return True if *stored_fqnn* refers to the same anchor as *anchor_fqnn*.

    Handles three formats in descending recency:
      1. Current:        ``Anchor_Foo`` or ``Group1.Anchor_Foo``
      2. Legacy stem:    ``scriptStem.Anchor_Foo``
      3. Very old:       full file path prefix, e.g. ``/path/to/script.Anchor_Foo``

    For formats 2 and 3 the first dot-segment is stripped and the remainder is
    compared against *anchor_fqnn*, matching the same stripping logic used in
    ``find_anchor_node`` for the forward lookup direction.
    """
    if not stored_fqnn:
        return False
    if stored_fqnn in (anchor_fqnn, legacy_fqnn):
        return True
    parts = stored_fqnn.split('.')
    if len(parts) > 1:
        stripped = '.'.join(parts[1:])
        if stripped == anchor_fqnn:
            return True
    return False


def get_links_for_anchor(anchor_node):
    """Return all link nodes in the current script that reference *anchor_node*."""
    fqnn = get_fully_qualified_node_name(anchor_node)
    legacy_fqnn = f"{nuke.root().name().split('.')[0]}.{fqnn}"
    return [node for node in nuke.allNodes()
            if is_link(node) and not is_anchor(node)
            and _stored_fqnn_matches_anchor(node[KNOB_NAME].getText(), fqnn, legacy_fqnn)]


# Compiled once at module level — covers %d, %04d, ####, %V, %v frame token styles
_FRAME_TOKEN_PATTERN = re.compile(r'[._]?(?:%0?\d*d|#{1,}|%[Vv])')


def suggest_anchor_name(input_node):
    """Return a suggested anchor name based on the input node's type and context.

    Dot nodes are handled specially:
    - Labelled Dot: the label is used as the name suggestion (plus backdrop prefix).
    - Unlabelled Dot: delegates to the first non-Dot ancestor via
      _find_first_non_dot_input(), or returns "" if the chain is empty.
    All other nodes use the 'file' knob and backdrop context as before.
    """
    import prefs

    # --- Dot node: label or upstream delegation ---
    if input_node.Class() == 'Dot':
        dot_label = _strip_html_tags(input_node['label'].getValue().strip()) if 'label' in input_node.knobs() else ''
        if dot_label:
            # Labelled Dot: suggest the label, prefixed by containing backdrop if present.
            smallest = find_smallest_containing_backdrop(input_node)
            if smallest is not None:
                backdrop_label = _strip_html_tags(smallest['label'].getValue().strip())
                if backdrop_label:
                    return backdrop_label + '_' + dot_label
            return dot_label
        else:
            # Unlabelled Dot: act as if the first non-Dot ancestor was the input.
            effective_node = _find_first_non_dot_input(input_node)
            if effective_node is None:
                return ""
            return suggest_anchor_name(effective_node)

    suggestion = ""

    if 'file' in input_node.knobs():
        filepath = input_node['file'].getValue()
        if filepath:
            filename = os.path.basename(filepath)
            stripped_filename = _FRAME_TOKEN_PATTERN.sub('', filename)
            user_regex = prefs.naming_regex
            if user_regex:
                try:
                    compiled_pattern = re.compile(user_regex)
                    regex_match = compiled_pattern.match(stripped_filename)
                    if regex_match:
                        naming_template = prefs.naming_template
                        if naming_template:
                            try:
                                suggestion = naming_template.format_map(regex_match.groupdict())
                            except (KeyError, ValueError):
                                suggestion = regex_match.group(0)
                        else:
                            suggestion = regex_match.group(0)
                    # No match — fall through to hardcoded path below
                except re.error:
                    pass  # Invalid regex — fall through to hardcoded path below
            # Hardcoded fallback: runs when user_regex is blank, regex has no match, or re.error
            if not suggestion:
                hardcoded_match = re.match(r'^(.+)_v\d+(?:\.[^.]+)?\.[^.]+$', stripped_filename)
                suggestion = hardcoded_match.group(1) if hardcoded_match else os.path.splitext(stripped_filename)[0]

    smallest = find_smallest_containing_backdrop(input_node)
    if smallest is not None:
        label = _strip_html_tags(smallest['label'].getValue().strip())
        if label:
            suggestion = label + '_' + suggestion

    return suggestion


def _update_links_for_renamed_anchor(old_fqnn, old_fqnn_legacy, new_fqnn, new_link_label):
    """Update KNOB_NAME and label on every link node whose stored FQNN refers to
    the renamed anchor (matched against either the current or legacy FQNN form).

    Iterates every node in the script exactly once.  Skips anchor nodes and
    non-link nodes.  This helper is shared by the Dot and NoOp branches of
    rename_anchor_to() so the two branches stay in sync.
    """
    for node in nuke.allNodes():
        if (is_link(node) and not is_anchor(node)
                and _stored_fqnn_matches_anchor(node[KNOB_NAME].getText(), old_fqnn, old_fqnn_legacy)):
            node[KNOB_NAME].setValue(new_fqnn)
            node['label'].setValue(f"Link: {new_link_label}")


def rename_anchor_to(anchor_node, name, color=None):
    """Rename an anchor to *name* and update all referencing link nodes.

    Raises ValueError if *name* sanitizes to an empty string.
    For Dot anchors the node name is kept in sync with the label so that the
    FQNN (which embeds the node name) reflects the new name.  Old FQNNs stored
    on link nodes are updated to the new FQNN.

    Parameters
    ----------
    anchor_node : nuke.Node
        The anchor node to rename.
    name : str
        New display name for the anchor.
    color : int or None
        If provided, propagate this color to the anchor and all its Link nodes
        after renaming.
    """
    sanitized = sanitize_anchor_name(name)
    if not sanitized:
        raise ValueError(f"Anchor name {name!r} produces an empty sanitized name")

    old_fqnn = get_fully_qualified_node_name(anchor_node)
    old_fqnn_legacy = f"{nuke.root().name().split('.')[0]}.{old_fqnn}"

    if anchor_node.Class() == 'Dot':
        anchor_node.setName(DOT_ANCHOR_PREFIX + sanitized)
        new_link_label = name.strip()
        anchor_node['label'].setValue(new_link_label)
    else:
        anchor_node.setName(ANCHOR_PREFIX + sanitized)
        anchor_node['label'].setValue(anchor_display_name(anchor_node))
        new_link_label = anchor_node['label'].getText() or anchor_node.name()

    new_fqnn = get_fully_qualified_node_name(anchor_node)
    _update_links_for_renamed_anchor(old_fqnn, old_fqnn_legacy, new_fqnn, new_link_label)

    if color is not None:
        propagate_anchor_color(anchor_node, color)


def rename_anchor(anchor_node):
    """Prompt the user for a new name (and optionally a new color) and rename the anchor."""
    if anchor_node.Class() == 'Dot':
        suggested = anchor_node['label'].getValue().strip()
    else:
        suggested = anchor_display_name(anchor_node)

    if ColorPaletteDialog is None:
        # Qt unavailable — fall back to plain text input
        name = nuke.getInput("Rename anchor:", suggested)
        if not name or not name.strip():
            return
        if not sanitize_anchor_name(name):
            return  # Name sanitises to empty — silently skip, matching prior behaviour.
        rename_anchor_to(anchor_node, name)
        return

    current_color = int(anchor_node['tile_color'].value())
    auto_derived_color = int(find_anchor_color(anchor_node))
    dialog = ColorPaletteDialog(
        initial_color=current_color,
        show_name_field=True,
        initial_name=suggested,
        custom_colors=prefs.custom_colors,
        default_color=auto_derived_color,
    )
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    _persist_custom_colors_from_dialog(dialog)
    chosen_name = dialog.chosen_name
    if not chosen_name or not chosen_name.strip():
        return
    chosen_color = dialog.selected_color_int()
    try:
        rename_anchor_to(anchor_node, chosen_name)
    except ValueError:
        nuke.message(f"Invalid anchor name: {chosen_name!r}")
        return
    if chosen_color is not None:
        propagate_anchor_color(anchor_node, chosen_color)


def rename_selected_anchor():
    if not prefs.plugin_enabled:
        return
    selected = nuke.selectedNodes()
    if len(selected) == 1 and is_anchor(selected[0]):
        rename_anchor(selected[0])


def reconnect_anchor_node(anchor_node):
    for link_node in get_links_for_anchor(anchor_node):
        reconnect_link_node(link_node)


def reconnect_all_links():
    for node in nuke.allNodes():
        if is_link(node) and not is_anchor(node):
            reconnect_link_node(node)


def _derive_dialog_default_color(input_node):
    """Derive the auto-computed colour for a not-yet-created anchor.

    We cannot call find_anchor_color() here because that function expects the
    anchor to already exist and calls anchor.input(0) — passing input_node
    would instead examine what is upstream *of* input_node.  Mirror the same
    priority logic directly:
      1. Backdrop colour (any input node type)
      2. Effective input node's own colour (tile_color with Preferences fallback)
      3. Hard-coded default purple

    For unlabelled Dot inputs, the effective node is the first non-Dot ancestor,
    so color derivation reflects the actual source.
    """
    if input_node is None:
        return ANCHOR_DEFAULT_COLOR

    if input_node.Class() == 'Dot':
        dot_label = input_node['label'].getValue().strip() if 'label' in input_node.knobs() else ''
        if not dot_label:
            color_source_node = _find_first_non_dot_input(input_node) or input_node
        else:
            color_source_node = input_node
    else:
        color_source_node = input_node

    containing_backdrop = find_smallest_containing_backdrop(color_source_node)
    if containing_backdrop is not None and containing_backdrop['tile_color'].value() != 0:
        return adjust_color_for_backdrop_contrast(int(containing_backdrop['tile_color'].value()))
    return int(find_node_color(color_source_node))


def create_anchor():
    if not prefs.plugin_enabled:
        return
    # Capture the group context before any Qt event loop runs so we can restore
    # it when calling create_anchor_named() (which calls nuke.createNode()).
    hit_group = nuke.lastHitGroup()
    with hit_group:
        selected = nuke.selectedNodes()
    input_node = selected[0] if len(selected) == 1 else None

    suggested = suggest_anchor_name(input_node) if input_node is not None else ""

    if ColorPaletteDialog is None:
        # Qt unavailable — fall back to plain text input
        name = nuke.getInput("Anchor name:", suggested)
        if not name or not name.strip():
            return
        if not sanitize_anchor_name(name):
            return  # Name sanitises to empty — silently skip, matching prior behaviour.
        with hit_group:
            create_anchor_named(name, input_node)
        return

    pre_color = _derive_dialog_default_color(input_node)

    dialog = ColorPaletteDialog(
        initial_color=pre_color,
        show_name_field=True,
        initial_name=suggested,
        custom_colors=prefs.custom_colors,
        default_color=pre_color,
    )
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    _persist_custom_colors_from_dialog(dialog)
    chosen_name = dialog.chosen_name
    if not chosen_name or not chosen_name.strip():
        return
    if not sanitize_anchor_name(chosen_name):
        return  # Name sanitises to empty — silently skip, matching prior behaviour.
    chosen_color = dialog.selected_color_int()
    with hit_group:
        create_anchor_named(chosen_name, input_node, color=chosen_color)


def create_from_anchor(anchor_node):
    nukescripts.clear_selection_recursive()
    link_class = 'Dot' if anchor_node.Class() == 'Dot' else 'NoOp'
    link = nuke.createNode(link_class)
    setup_link_node(anchor_node, link)
    return link


def create_anchor_named(name, input_node=None, color=None):
    """Create an anchor with the given *name* without any user prompt.

    Returns the new anchor node.
    Raises ValueError if *name* sanitizes to an empty string.

    Parameters
    ----------
    name : str
        Display name for the anchor.
    input_node : nuke.Node or None
        Optional input node to connect the anchor to.
    color : int or None
        Explicit tile color as 0xRRGGBBAA int.  If None, falls back to
        find_anchor_color() for backward-compatible color derivation.
    """
    sanitized = sanitize_anchor_name(name)
    if not sanitized:
        raise ValueError(f"Anchor name {name!r} produces an empty sanitized name")

    nukescripts.clear_selection_recursive()
    anchor = nuke.createNode('NoOp')
    anchor.setName(ANCHOR_PREFIX + sanitized)
    anchor['label'].setValue(anchor_display_name(anchor))

    if input_node is not None:
        anchor.setInput(0, input_node)
        anchor.setXYpos(
            input_node.xpos() + input_node.screenWidth() // 2 - anchor.screenWidth() // 2,
            input_node.ypos() + input_node.screenHeight() + 20
        )

    if color is not None:
        anchor['tile_color'].setValue(color)
    else:
        anchor['tile_color'].setValue(find_anchor_color(anchor))
    add_reconnect_anchor_knob(anchor)
    add_rename_anchor_knob(anchor)
    add_set_color_anchor_knob(anchor)
    return anchor


def create_anchor_silent(input_node=None):
    """Create an anchor using the auto-suggested name without any user prompt.

    Falls back to the input node's name, then to ``"Anchor"`` if no suggestion
    can be derived.  Returns the new anchor node.
    """
    if input_node is not None:
        suggested = suggest_anchor_name(input_node) or input_node.name()
    else:
        suggested = "Anchor"
    return create_anchor_named(suggested, input_node)


def create_link_for_anchor_named(display_name):
    """Create a link node wired to the anchor with *display_name*.

    Returns the new link node.
    Raises ValueError if no anchor with that display name exists.
    """
    anchor = find_anchor_by_name(display_name)
    if anchor is None:
        raise ValueError(f"No anchor found with display name {display_name!r}")
    return create_from_anchor(anchor)


def try_create_link_for_anchor_named(display_name):
    """Create a link node wired to the anchor with *display_name*, or None.

    Returns the new link node, or None if no anchor with that display name exists.
    """
    anchor = find_anchor_by_name(display_name)
    if anchor is None:
        return None
    return create_from_anchor(anchor)


def _anchor_picker_items():
    """get_items() body for the link-creation picker — anchors only."""
    anchors = all_anchors()
    duplicate_dot_labels = _dot_anchor_duplicate_labels()
    return [
        {
            'menuobj': anchor,
            'menupath': 'Anchors/' + anchor_display_name(anchor, duplicate_dot_labels),
        }
        for anchor in anchors
    ]


def _anchor_navigate_items():
    """get_items() body for the navigation picker — anchors plus labelled BackdropNodes."""
    anchor_nodes = all_anchors()
    duplicate_dot_labels = _dot_anchor_duplicate_labels()
    items = [
        {
            'menuobj': anchor_node,
            'menupath': 'Anchors/' + anchor_display_name(anchor_node, duplicate_dot_labels),
        }
        for anchor_node in anchor_nodes
    ]
    for backdrop_node in nuke.allNodes('BackdropNode'):
        label = backdrop_node['label'].value().strip()
        if label:
            items.append({
                'menuobj': backdrop_node,
                'menupath': 'Backdrops/' + label,
            })
    return items


def _anchor_picker_invoke(thing, hit_group):
    """invoke() body for the link-creation picker — wraps create_from_anchor in hit_group."""
    anchor = thing['menuobj']
    with hit_group:
        if nuke.exists(anchor.name()):
            create_from_anchor(anchor)


def _anchor_navigate_invoke(thing, hit_group):
    """invoke() body for the navigation picker.

    Defers navigation until after the picker widget closes and Qt restores
    focus to the DAG panel.  nuke.zoom() targets whichever panel has Qt
    focus, so calling it while the picker is still open would zoom the
    wrong panel (or do nothing).
    """
    node = thing['menuobj']
    target_group = hit_group or nuke.root()

    def _deferred_navigate():
        with target_group:
            if not nuke.exists(node.name()):
                return
            _save_dag_position()
            if node.Class() == 'BackdropNode':
                navigate_to_backdrop(node)
                return
            navigate_to_anchor(node)

    QtCore.QTimer.singleShot(0, _deferred_navigate)


class _AnchorPickerPlugin(_tabtabtab.TabTabTabPlugin):
    """Unified tabtabtab plugin for both anchor link-creation and navigation.

    Parameterised by:
    - get_items_fn: callable returning the menu items (called inside hit_group).
    - invoke_fn: callable taking (item_dict, hit_group) — invoked when the user
      selects an item from the picker.
    - weights_filename: absolute path to the per-plugin TabTabTabWidget weights
      file (kept distinct so picker vs navigate weights don't cross-contaminate).
    """

    def __init__(self, get_items_fn, invoke_fn, weights_filename):
        self._get_items_fn = get_items_fn
        self._invoke_fn = invoke_fn
        self._weights_filename = weights_filename
        self._hit_group = None

    def get_items(self):
        # _hit_group is set externally by the select_anchor_and_* entry point
        # BEFORE show() calls get_items().  We must NOT capture lastHitGroup()
        # here because show() runs after the original menu-callback context
        # has exited, so lastHitGroup() would return root.
        hit_group = self._hit_group or nuke.root()
        with hit_group:
            return self._get_items_fn()

    def get_weights_file(self):
        return self._weights_filename

    def invoke(self, thing):
        self._invoke_fn(thing, self._hit_group)

    def get_icon(self, menuobj):
        return None

    def get_color(self, menuobj):
        color_int = menuobj['tile_color'].value()  # 0xRRGGBBAA — reads what was actually set
        r = (color_int >> 24) & 0xFF
        g = (color_int >> 16) & 0xFF
        b = (color_int >> 8) & 0xFF
        color = QtGui.QColor(r, g, b)
        return (color, color)


def _make_anchor_picker_plugin():
    """Build the link-creation picker plugin.  Original weights filename preserved byte-for-byte."""
    return _AnchorPickerPlugin(
        get_items_fn=_anchor_picker_items,
        invoke_fn=_anchor_picker_invoke,
        weights_filename=os.path.expanduser('~/.nuke/anchors_anchor_weights.json'),
    )


def _make_anchor_navigate_plugin():
    """Build the navigation picker plugin.  Original weights filename preserved byte-for-byte."""
    return _AnchorPickerPlugin(
        get_items_fn=_anchor_navigate_items,
        invoke_fn=_anchor_navigate_invoke,
        weights_filename=os.path.expanduser('~/.nuke/anchors_anchor_navigate_weights.json'),
    )


def pick_anchor(on_pick, hit_group=None):
    """Open the tabtabtab anchor picker; call *on_pick(anchor_node, hit_group)* on selection.

    Reuses the same picker geometry, weights file, and item list as the
    link-creation picker so muscle-memory ordering carries over across the
    leader-key Set-Input-To commands.

    The callback is invoked synchronously from inside the picker's invoke()
    context — callers that need DAG focus (e.g. for nuke.zoom()) must defer
    via QtCore.QTimer.singleShot themselves, mirroring _anchor_navigate_invoke.

    Silent no-op when:
      - The plugin is disabled (prefs.plugin_enabled is False)
      - Qt is unavailable (headless / test environment)
      - There are no anchors to choose from in the active group

    Parameters
    ----------
    on_pick : callable
        Called with (anchor_node, hit_group) when the user selects an anchor.
    hit_group : nuke.Group or None
        Group context for the picker.  Defaults to nuke.lastHitGroup().
    """
    if not prefs.plugin_enabled:
        return
    if QtWidgets is None:
        return
    if hit_group is None:
        hit_group = nuke.lastHitGroup()
    with hit_group:
        if not all_anchors():
            return

    def _custom_invoke(thing, captured_hit_group):
        anchor = thing['menuobj']
        with captured_hit_group:
            if nuke.exists(anchor.name()):
                on_pick(anchor, captured_hit_group)

    plugin = _AnchorPickerPlugin(
        get_items_fn=_anchor_picker_items,
        invoke_fn=_custom_invoke,
        weights_filename=os.path.expanduser('~/.nuke/anchors_anchor_weights.json'),
    )
    plugin._hit_group = hit_group
    widget = _tabtabtab.TabTabTabWidget(plugin, winflags=Qt.FramelessWindowHint)
    widget.under_cursor()
    widget.show()
    widget.raise_()


def anchor_shortcut():
    """If a node is selected, create an anchor from it. Otherwise, pick an anchor to create from."""
    if not prefs.plugin_enabled:
        return
    hit_group = nuke.lastHitGroup()
    with hit_group:
        selected = nuke.selectedNodes()
    if len(selected) == 1 and is_anchor(selected[0]):
        rename_anchor(selected[0])
    elif selected:
        create_anchor()
    else:
        select_anchor_and_create(hit_group)


_anchor_picker_widget = None


def select_anchor_and_create(hit_group=None):
    if not prefs.plugin_enabled:
        return
    if QtWidgets is None:
        return
    if hit_group is None:
        hit_group = nuke.lastHitGroup()
    with hit_group:
        if not all_anchors():
            return
    global _anchor_picker_widget
    if _anchor_picker_widget is not None:
        try:
            _anchor_picker_widget.plugin._hit_group = hit_group
            _anchor_picker_widget.under_cursor()
            _anchor_picker_widget.show()
            _anchor_picker_widget.raise_()
            return
        except RuntimeError:
            _anchor_picker_widget = None
    plugin = _make_anchor_picker_plugin()
    plugin._hit_group = hit_group
    _anchor_picker_widget = _tabtabtab.TabTabTabWidget(
        plugin, winflags=Qt.FramelessWindowHint
    )
    _anchor_picker_widget.under_cursor()
    _anchor_picker_widget.show()
    _anchor_picker_widget.raise_()


def _save_dag_position():
    """Capture the current DAG viewport state into the back-navigation slot.

    Called before every navigate-to-anchor or navigate-to-backdrop jump.
    Overwrites any previously saved position — single-slot, no history stack.
    """
    global _back_position
    _back_position = (nuke.zoom(), nuke.center())


def navigate_back():
    """Restore the DAG to the position saved before the last Alt+A jump.

    Silent no-op if no position has been saved yet. Consumes the slot —
    subsequent calls are no-ops until the next navigate-to-anchor jump.
    """
    if not prefs.plugin_enabled:
        return
    global _back_position
    if _back_position is None:
        return
    zoom_level, center_xy = _back_position
    _back_position = None
    nuke.zoom(zoom_level, center_xy)
    nukescripts.clear_selection_recursive()


def jump_to_selected_anchor():
    """Navigate to the source anchor's upstream tree for the selected link node.

    Saves the current DAG viewport first so Alt+Z (navigate_back) can return.
    Silent no-op when:
    - The plugin is disabled (prefs.plugin_enabled is False)
    - No nodes are currently selected
    - The first selected node is not a link
    - The link's source anchor cannot be found
    """
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    first_selected_node = selected_nodes[0]
    if not is_link(first_selected_node):
        return
    anchor_node = find_anchor_node(first_selected_node)
    if anchor_node is None:
        return
    _save_dag_position()
    navigate_to_anchor(anchor_node)


# --- Cycle-through-links state ---
_cycle_anchor_name = None
_cycle_links = []
_cycle_link_index = 0


def cycle_next_link():
    """Navigate to the next link node referencing the selected anchor.

    On first invocation (or when the selected anchor changes), saves the DAG
    position, collects all links for the anchor sorted by name, and zooms to
    the first one.  Each subsequent invocation advances to the next link.
    After the last link, navigates back to the anchor and resets the cycle.

    Silent no-op when:
    - The plugin is disabled
    - No nodes are selected
    - The selected node is not an anchor
    - The anchor has no link nodes
    """
    global _cycle_anchor_name, _cycle_links, _cycle_link_index

    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    first_selected_node = selected_nodes[0]
    if not is_anchor(first_selected_node):
        return

    anchor_name = first_selected_node.name()
    links = sorted(get_links_for_anchor(first_selected_node), key=lambda n: n.name())
    if not links:
        return

    if anchor_name != _cycle_anchor_name or links != _cycle_links:
        _cycle_anchor_name = anchor_name
        _cycle_links = links
        _cycle_link_index = 0
        _save_dag_position()
    else:
        _cycle_link_index += 1

    if _cycle_link_index >= len(_cycle_links):
        _cycle_anchor_name = None
        _cycle_links = []
        _cycle_link_index = 0
        navigate_back()
        return

    target_link = _cycle_links[_cycle_link_index]
    saved_selection = nuke.selectedNodes()
    nukescripts.clear_selection_recursive()
    target_link["selected"].setValue(True)
    nuke.zoomToFitSelected()
    nukescripts.clear_selection_recursive()
    for node in saved_selection:
        node["selected"].setValue(True)


def navigate_to_backdrop(backdrop_node):
    """Zoom the DAG to fit *backdrop_node*.

    Selects the backdrop and uses nuke.zoomToFitSelected() so the zoom scale
    adapts to the backdrop's size.  The previous implementation used
    nuke.zoom(1.0, center), which always jumped to 100% zoom regardless of
    backdrop size and so zoomed in too far on large backdrops.  Navigation is
    dispatched after the picker closes (see _anchor_navigate_invoke), so the
    focused DAG panel is the active one by the time this runs — matching how
    navigate_to_anchor already relies on zoomToFitSelected.
    """
    nukescripts.clear_selection_recursive()
    backdrop_node['selected'].setValue(True)
    nuke.zoomToFitSelected()
    nukescripts.clear_selection_recursive()


def upstream_ignoring_hidden(node, nodes_so_far=None, _visited=None):
    if _visited is None:
        _visited = set()
    if node in _visited:
        return nodes_so_far
    _visited.add(node)

    inputs = node.dependencies(what=nuke.INPUTS)
    if not inputs:
        return nodes_so_far
    if nodes_so_far is None:
        nodes_so_far = set(inputs)
    else:
        nodes_so_far.update(inputs)
    for input_node in inputs:
        upstream_ignoring_hidden(input_node, nodes_so_far, _visited)
    return nodes_so_far


def navigate_to_anchor(anchor_node):
    """Zoom the DAG to frame *anchor_node* and its visible-path upstream nodes."""
    upstream_nodes = upstream_ignoring_hidden(anchor_node) or set()
    nodes_to_fit = upstream_nodes | {anchor_node}

    saved_selection = nuke.selectedNodes()
    nukescripts.clear_selection_recursive()
    for node in nodes_to_fit:
        node["selected"].setValue(True)

    nuke.zoomToFitSelected()

    # A labelled-dot module (the nodes above a Dot anchor) frames too tight with
    # zoomToFitSelected, which has no padding parameter (issue #61). Zoom out
    # slightly from the fitted framing to leave a margin around the module. Only
    # Dot anchors get this margin; other anchor types keep the tight fit they had
    # before, matching the framing that already worked for them.
    if anchor_node.Class() == 'Dot':
        fitted_scale = nuke.zoom()
        fitted_center = nuke.center()
        nuke.zoom(fitted_scale * MODULE_ZOOM_MARGIN_FACTOR, fitted_center)

    nukescripts.clear_selection_recursive()
    for node in saved_selection:
        node["selected"].setValue(True)


_anchor_navigate_widget = None
_back_position = None  # (zoom_level, center_xy) tuple or None — session-only back-navigation slot


def select_anchor_and_navigate():
    if not prefs.plugin_enabled:
        return
    if QtWidgets is None:
        return
    hit_group = nuke.lastHitGroup()
    with hit_group:
        labelled_backdrops = [
            bd for bd in nuke.allNodes('BackdropNode')
            if bd['label'].value().strip()
        ]
        if not all_anchors() and not labelled_backdrops:
            return
    global _anchor_navigate_widget
    if _anchor_navigate_widget is not None:
        try:
            _anchor_navigate_widget.plugin._hit_group = hit_group
            _anchor_navigate_widget.under_cursor()
            _anchor_navigate_widget.show()
            _anchor_navigate_widget.raise_()
            return
        except RuntimeError:
            _anchor_navigate_widget = None
    plugin = _make_anchor_navigate_plugin()
    plugin._hit_group = hit_group
    _anchor_navigate_widget = _tabtabtab.TabTabTabWidget(
        plugin, winflags=Qt.FramelessWindowHint
    )
    _anchor_navigate_widget.under_cursor()
    _anchor_navigate_widget.show()
    _anchor_navigate_widget.raise_()


def create_links_from_selected_anchors():
    """Create a link node for each selected anchor, placed near the anchor.

    For each anchor in the current selection, calls create_from_anchor() to
    produce a wired link node and positions it to the right of the anchor.
    Silent no-op when the plugin is disabled or no anchors are selected.
    """
    if not prefs.plugin_enabled:
        return
    hit_group = nuke.lastHitGroup()
    with hit_group:
        selected_nodes = nuke.selectedNodes()
        selected_anchors = [node for node in selected_nodes if is_anchor(node)]
        if not selected_anchors:
            return
        for anchor_node in selected_anchors:
            link_node = create_from_anchor(anchor_node)
            link_node.setXYpos(
                anchor_node.xpos() + anchor_node.screenWidth() + 20,
                anchor_node.ypos(),
            )

