"""Shared constants for the anchors plugin."""

import os

# FROZEN: value stored in .nk files — do not rename
TAB_NAME = 'copy_hidden_tab'
# FROZEN: value stored in .nk files — do not rename
KNOB_NAME = 'copy_hidden_input_node'
# FROZEN: value stored in .nk files — do not rename
LINK_RECONNECT_KNOB_NAME = "reconnect_link"
HIDDEN_INPUT_CLASSES = ['PostageStamp', 'Dot', 'NoOp']
LINK_SOURCE_CLASSES = frozenset({
    "Read", "DeepRead", "ReadGeo",
    "Camera", "Camera2", "Camera3", "Camera4",
    "GeoImport",
})

ANCHOR_PREFIX = 'Anchor_'
# FROZEN: value stored in .nk files — do not rename
ANCHOR_RECONNECT_KNOB_NAME = "reconnect_child_links"
# FROZEN: value stored in .nk files — do not rename
ANCHOR_RENAME_KNOB_NAME = "rename_anchor"
ANCHOR_DEFAULT_COLOR = 0x6f3399ff

DOT_LABEL_FONT_SIZE_LARGE = 111
DOT_LABEL_FONT_SIZE_MEDIUM = 66
DOT_LABEL_FONT_SIZE_SMALL = 33
NODE_LABEL_FONT_SIZE_LARGE = 33
DOT_LINK_LABEL_FONT_SIZE = 33
DOT_ANCHOR_MIN_FONT_SIZE = 33

# FROZEN: value stored in .nk files — do not rename
DOT_ANCHOR_KNOB_NAME = 'anchors_dot_anchor'

# FROZEN: value stored in .nk files — do not rename
DOT_TYPE_KNOB_NAME = 'anchors_dot_type'
# darkened burnt orange: R=122,G=58,B=0 (~30% darker than previous 0xB35A00FF)
LOCAL_DOT_COLOR = 0x7A3A00FF

# FROZEN: value stored in .nk files — do not rename
ANCHOR_SET_COLOR_KNOB_NAME = "set_anchor_color"
USER_PALETTE_PATH = os.path.expanduser('~/.nuke/paste_hidden_user_palette.json')
OLD_PREFS_PATH = os.path.expanduser('~/.nuke/paste_hidden_prefs.json')
PREFS_PATH = os.path.expanduser('~/.nuke/anchors_prefs.json')
