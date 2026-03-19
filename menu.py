import nuke

import anchor
import labels
import anchors
import prefs

menu = nuke.menu("Nuke")
edit_menu = menu.findItem("Edit")

menu.addCommand("Edit/Copy",  "anchors.copy_anchors()",  "^C")
menu.addCommand("Edit/Cut",   "anchors.cut_anchors()",   "^X")
menu.addCommand("Edit/Paste", "anchors.paste_anchors()", "^V")

def _find_item_index(parent_menu, item_name):
    for position, menu_item in enumerate(parent_menu.items()):
        if menu_item.name() == item_name:
            return position
    return -1

paste_index = _find_item_index(edit_menu, "Paste")
edit_menu.addCommand(
    "Paste Multiple",
    "anchors.paste_multiple_anchors()",
    index=paste_index + 1,
)

anchors_menu = edit_menu.addMenu("Anchors")

# ---------------------------------------------------------------------------
# Gated items — disabled when plugin_enabled is False.
# Store references so set_anchors_menu_enabled() can toggle them dynamically.
# ---------------------------------------------------------------------------
_gated_menu_items = []


def _add_gated_command(menu, name, command, shortcut=None):
    """Register a menu command and track its item reference for enable/disable."""
    if shortcut is not None:
        item = menu.addCommand(name, command, shortcut)
    else:
        item = menu.addCommand(name, command)
    if item is not None:
        _gated_menu_items.append(item)


_add_gated_command(anchors_menu, "Create Anchor",       "anchor.create_anchor()")
_add_gated_command(anchors_menu, "Rename Anchor",       "anchor.rename_selected_anchor()")
_add_gated_command(anchors_menu, "Create Link",         "anchor.select_anchor_and_create()")
_add_gated_command(anchors_menu, "Anchor",              "anchor.anchor_shortcut()",            "A")
_add_gated_command(anchors_menu, "Reconnect All Links", "anchor.reconnect_all_links()")
_add_gated_command(anchors_menu, "Anchor Find", "anchor.select_anchor_and_navigate()", "alt+A")
_add_gated_command(anchors_menu, "Anchor Back", "anchor.navigate_back()", "alt+Z")

anchors_menu.addSeparator()

_add_gated_command(anchors_menu, "Label (Large)",  "labels.create_large_label()",  "+M")
_add_gated_command(anchors_menu, "Label (Medium)", "labels.create_medium_label()", "+N")
_add_gated_command(anchors_menu, "Label (Small)",  "labels.create_small_label()",  "+B")
_add_gated_command(anchors_menu, "Append Label",   "labels.append_to_label()",     "^M")

anchors_menu.addSeparator()

# ---------------------------------------------------------------------------
# Always-active items — ungated regardless of plugin_enabled.
# Copy (old) / Cut (old) / Paste (old) are explicit fallback commands.
# Preferences entry is added by Phase 7 and must also remain always active.
# ---------------------------------------------------------------------------
anchors_menu.addCommand("Copy (old)",  "anchors.copy_old()")
anchors_menu.addCommand("Cut (old)",   "anchors.cut_old()")
anchors_menu.addCommand("Paste (old)", "anchors.paste_old()", "+^D")

anchors_menu.addSeparator()
anchors_menu.addCommand(
    "Anchor Preferences...",
    "from colors import PrefsDialog; dlg = PrefsDialog(); dlg.exec()"
)


def set_anchors_menu_enabled(enabled):
    """Enable or disable all gated Anchors menu items.

    Called by Phase 7 PrefsDialog after the user toggles plugin_enabled.
    Uses hasattr guard for Nuke version compatibility (setEnabled available Nuke 13+).
    """
    for menu_item in _gated_menu_items:
        if hasattr(menu_item, 'setEnabled'):
            menu_item.setEnabled(enabled)


# Store a reference in prefs so PrefsDialog can call it without import conflicts.
# colors.py imports prefs cleanly; this avoids any paste_hidden package import issues.
prefs.set_anchors_menu_enabled = set_anchors_menu_enabled

# Apply initial state at startup in case prefs loads plugin_enabled=False
set_anchors_menu_enabled(prefs.plugin_enabled)
