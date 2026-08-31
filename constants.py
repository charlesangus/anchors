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

# === "Upgrade to Anchors" options. ===
# Shared by the upgrade logic in migrations.py and the dialog in colors.py.
# These are option values only — they are never written to .nk files, so unlike
# the knob names above they are free to change.
# Where an upgraded anchor takes its name from.
NAME_SOURCE_AUTO = 'auto'       # the node's label when it has one, else its name
NAME_SOURCE_NODE_NAME = 'name'
NAME_SOURCE_LABEL = 'label'
# Which nodes the upgrade considers.
UPGRADE_SCOPE_SELECTED = 'selected'
UPGRADE_SCOPE_SCRIPT = 'script'

# === Navigation framing. ===
# After nuke.zoomToFitSelected() frames a module edge-to-edge, navigate_to_anchor
# zooms out by this factor to leave a margin around the module, for every anchor
# type (issue #61, widened by issue #73). Nuke's zoomToFitSelected() has no
# padding parameter, so the margin is applied as a post-fit zoom-out: 0.75 leaves
# ~12.5% of the viewport as margin per side, which lands in the requested
# ~200-300px range on a typical DAG panel.
MODULE_ZOOM_MARGIN_FACTOR = 0.75

# === Keyboard shortcut context. ===
# Nuke's menu.addCommand() accepts a shortcutContext that scopes where a
# keyboard shortcut fires: 0 = window, 1 = application, 2 = DAG (Node Graph).
# Anchor functions are only meaningful in the Node Graph, so binding their
# shortcuts to the DAG context stops them from intercepting keys in the Script
# Editor, Viewer, or other panels (issue #54).
DAG_SHORTCUT_CONTEXT = 2

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

# === Leader-key bindings — single source of truth for leader.py and leader_overlay.py. ===
# Each entry: (key_letter, action_label, row, col, kind)
#   kind: 'single' (disarm-then-dispatch) or 'chaining' (stay-armed)
# The key_letter must be a single uppercase ASCII letter (or ',' for the comma key).
# Row/col positions mirror physical QWERTY geometry so the grid reads like a
# keyboard.  Column indices are the key's position in its physical row:
#   Row 0 (Q-row): Q=0 W=1 E=2 R=3 T=4 Y=5 U=6 I=7 O=8 P=9
#   Row 1 (A-row): A=0 S=1 D=2 F=3 G=4 H=5 J=6 K=7 L=8 ;=9
#   Row 2 (Z-row): Z=0 X=1 C=2 V=3 B=4 N=5 M=6 ,=7 .=8 /=9
# Empty cells are left blank in the overlay grid.
LEADER_BINDINGS = (
    ('Q', 'Set B Input',     0, 0, 'single'),
    ('W', 'Set A Input',     0, 1, 'single'),
    ('E', 'Set Mask Input',  0, 2, 'single'),
    ('R', 'Set First Free',  0, 3, 'single'),
    ('F', 'Anchor Find',     1, 3, 'single'),
    ('J', 'Anchor Jump',     1, 6, 'single'),
    ('L', 'Cycle Links',     1, 8, 'chaining'),
    ('Z', 'Anchor Back',     2, 0, 'single'),
    ('X', 'Reconnect All',   2, 1, 'single'),
    (',', 'Preferences',     2, 7, 'single'),
)
