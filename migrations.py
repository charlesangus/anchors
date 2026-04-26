"""Migration helpers for legacy knob names and prefs files.

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
    ANCHOR_RECONNECT_KNOB_NAME,
    ANCHOR_RENAME_KNOB_NAME,
    ANCHOR_SET_COLOR_KNOB_NAME,
    DOT_ANCHOR_KNOB_NAME,
    DOT_TYPE_KNOB_NAME,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    TAB_NAME,
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
        new_knob = nuke.String_Knob(new_name, '')
        new_knob.setFlag(nuke.INVISIBLE)
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
    ``paste_hidden_prefs.json`` does.  Never modifies the old file.  Silent
    no-op if old file is absent or unreadable.
    """
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
    old palette file.  Silent no-op if old file is absent or corrupt; on any
    failure ``prefs.custom_colors`` is set to ``[]``.
    """
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
