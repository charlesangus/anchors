"""Shared constants for the anchors plugin."""

import os

# === Hidden knob names written to .nk files. Renaming requires migrations.py. ===
# Each constant below is FROZEN: its value is serialised into .nk files on save.
# Renaming the value requires extending migrations.LEGACY_TO_NEW_KNOB_NAMES so
# scripts saved under the old name keep loading.  The migrator is registered via
# nuke.addOnScriptLoad in menu.py and runs before any code path reads these
# constants from a not-yet-migrated script.

# FROZEN: value stored in .nk files — do not rename
TAB_NAME = 'anchors_tab'
# FROZEN: value stored in .nk files — do not rename
KNOB_NAME = 'anchors_input_node'
# FROZEN: value stored in .nk files — do not rename
LINK_RECONNECT_KNOB_NAME = 'anchors_reconnect_link'
# FROZEN: value stored in .nk files — do not rename
ANCHOR_RECONNECT_KNOB_NAME = 'anchors_reconnect_child_links'
# FROZEN: value stored in .nk files — do not rename
ANCHOR_RENAME_KNOB_NAME = 'anchors_rename_anchor'
# FROZEN: value stored in .nk files — do not rename
ANCHOR_SET_COLOR_KNOB_NAME = 'anchors_set_anchor_color'
# FROZEN: value stored in .nk files — do not rename
DOT_ANCHOR_KNOB_NAME = 'anchors_dot_anchor'
# FROZEN: value stored in .nk files — do not rename
DOT_TYPE_KNOB_NAME = 'anchors_dot_type'

# === Anchor lifecycle constants (node-name prefixes, defaults). ===
HIDDEN_INPUT_CLASSES = ['PostageStamp', 'Dot', 'NoOp']
ANCHOR_PREFIX = 'Anchor_'
DOT_ANCHOR_PREFIX = 'Anchor_Dot_'
ANCHOR_DEFAULT_COLOR = 0x6f3399ff
# darkened burnt orange: R=122,G=58,B=0 (~30% darker than previous 0xB35A00FF)
LOCAL_DOT_COLOR = 0x7A3A00FF

# === Font sizes and colours. ===
DOT_LABEL_FONT_SIZE_LARGE = 111
DOT_LABEL_FONT_SIZE_MEDIUM = 66
DOT_LABEL_FONT_SIZE_SMALL = 33
NODE_LABEL_FONT_SIZE_LARGE = 33
DOT_LINK_LABEL_FONT_SIZE = 33
DOT_ANCHOR_MIN_FONT_SIZE = 33

# === On-disk preferences paths. ===
USER_PALETTE_PATH = os.path.expanduser('~/.nuke/paste_hidden_user_palette.json')
OLD_PREFS_PATH = os.path.expanduser('~/.nuke/paste_hidden_prefs.json')
PREFS_PATH = os.path.expanduser('~/.nuke/anchors_prefs.json')
