"""Build a large comp for trying the spatial view at a scale that overflows the screen.

Run headless under Nuke's terminal mode, naming the script to write::

    nuke -t validation/build_large_script.py large_script.nk

The comp is shaped like a busy feature shot: rows of labelled input modules
(plates, per-character CG passes, FX, matte paintings, cameras, roto), each holding
a handful of anchors, a few nested sub-modules and empty note backdrops, and below
them several comp branches carrying Dot anchors down their spines.  At the map's
tile size it comes out several times larger than an HD screen in both directions.

Anchors are made with the plugin's own ``anchor.create_anchor_named`` and Dot
anchors with ``link.mark_dot_as_anchor``, so the nodes carry the same knobs as
ones made by hand.
"""

import os
import sys

import nuke

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT)

import anchor  # noqa: E402
import link  # noqa: E402
import prefs  # noqa: E402

prefs.plugin_enabled = True

MODULE_COLUMNS = 7
MODULE_WIDTH = 620
MODULE_HEIGHT = 420
MODULE_SPACING_X = 900
MODULE_SPACING_Y = 800
ANCHOR_SPACING_X = 150
ANCHOR_SPACING_Y = 110

# (module label, colour, anchor names), laid out in rows of MODULE_COLUMNS.
MODULES = [
    ('plates', 0x7A6A2AFF, ['plate_main', 'plate_clean', 'plate_ref', 'plate_grain', 'plate_lens']),
    ('bg_plates', 0x7A6A2AFF, ['bg_left', 'bg_right', 'bg_sky', 'bg_tile']),
    ('cam', 0x2A7A3AFF, ['cam_main', 'cam_witness', 'cam_projection']),
    ('lidar', 0x2A7A3AFF, ['lidar_set', 'lidar_props']),
    ('hero_cg', 0x2A5A8AFF, ['hero_beauty', 'hero_diffuse', 'hero_spec', 'hero_sss',
                             'hero_emission', 'hero_crypto', 'hero_depth', 'hero_motion']),
    ('creature_cg', 0x2A5A8AFF, ['creature_beauty', 'creature_fur', 'creature_spec',
                                 'creature_crypto', 'creature_depth']),
    ('vehicle_cg', 0x2A5A8AFF, ['vehicle_beauty', 'vehicle_refl', 'vehicle_crypto']),
    ('env_cg', 0x2A5A8AFF, ['env_beauty', 'env_volume', 'env_depth', 'env_crypto']),
    ('crowd_cg', 0x2A5A8AFF, ['crowd_beauty', 'crowd_crypto', 'crowd_depth']),
    ('fx_fire', 0x8A3A2AFF, ['fire_core', 'fire_glow', 'fire_embers']),
    ('fx_smoke', 0x8A3A2AFF, ['smoke_dense', 'smoke_wisps', 'smoke_holdout']),
    ('fx_debris', 0x8A3A2AFF, ['debris_large', 'debris_small', 'debris_dust', 'debris_crypto']),
    ('fx_water', 0x8A3A2AFF, ['water_splash', 'water_mist', 'water_foam']),
    ('dmp', 0x5A3A8AFF, ['dmp_sky', 'dmp_city', 'dmp_mountains', 'dmp_haze']),
    ('roto', 0x3A7A7AFF, ['roto_hero', 'roto_actor2', 'roto_fg_props', 'roto_garbage']),
    ('keys', 0x3A7A7AFF, ['key_hero', 'key_actor2', 'key_hair']),
    ('lens', 0x6A6A6AFF, ['lens_distort', 'lens_flare', 'lens_dirt']),
    ('elements', 0x6A6A6AFF, ['elem_sparks', 'elem_dust', 'elem_rain', 'elem_bokeh']),
    ('soldier_cg', 0x2A5A8AFF, ['soldier_beauty', 'soldier_spec', 'soldier_crypto']),
    ('horse_cg', 0x2A5A8AFF, ['horse_beauty', 'horse_fur', 'horse_crypto', 'horse_depth']),
    ('dragon_cg', 0x2A5A8AFF, ['dragon_beauty', 'dragon_scales', 'dragon_wings',
                               'dragon_fire_light', 'dragon_crypto', 'dragon_depth']),
    ('ship_cg', 0x2A5A8AFF, ['ship_beauty', 'ship_wake', 'ship_crypto']),
    ('fx_sparks', 0x8A3A2AFF, ['sparks_hot', 'sparks_trails']),
    ('fx_magic', 0x8A3A2AFF, ['magic_core', 'magic_wisps', 'magic_glow', 'magic_light']),
    ('stock', 0x6A6A6AFF, ['stock_fire', 'stock_smoke', 'stock_explosion', 'stock_flare']),
    ('plates_extra', 0x7A6A2AFF, ['plate_pickup', 'plate_stunt', 'plate_insert']),
    ('bg_extension', 0x5A3A8AFF, ['ext_left', 'ext_right', 'ext_top']),
    ('atmos', 0x6A6A6AFF, ['atmos_fog', 'atmos_godrays', 'atmos_haze']),
]

# Modules that hold a nested, labelled sub-module around their last few anchors.
NESTED_SUBMODULES = {'hero_cg': ('hero_utility', 3), 'fx_debris': ('debris_passes', 2)}

# Labelled backdrops with no anchors inside: notes and parked setups.
EMPTY_NOTES = [('notes', 0), ('parked_setups', 4), ('old_versions', 8)]

COMP_BRANCHES = 6
DOTS_PER_BRANCH = 18
DOT_SPACING_Y = 260
BRANCH_SPACING_X = 1300
DOT_LABELS = ['fg', 'bg', 'key', 'core', 'edge', 'hero', 'alpha', 'holdout', 'glow', 'depth']
DOT_LABEL_FONT_SIZES = (22, 44, 88)


def make_backdrop(label, xpos, ypos, width, height, color):
    backdrop = nuke.nodes.BackdropNode()
    backdrop['label'].setValue(label)
    backdrop['tile_color'].setValue(color)
    backdrop['bdwidth'].setValue(width)
    backdrop['bdheight'].setValue(height)
    backdrop.setXYpos(xpos, ypos)
    return backdrop


def build_module(label, color, anchor_names, left, top):
    make_backdrop(label, left, top, MODULE_WIDTH, MODULE_HEIGHT, color)
    anchors_per_row = 3
    positions = []
    for index, name in enumerate(anchor_names):
        column = index % anchors_per_row
        row = index // anchors_per_row
        # A slight stagger, as hand-placed nodes never line up exactly.
        xpos = left + 60 + column * ANCHOR_SPACING_X + (row * 17) % 40
        ypos = top + 90 + row * ANCHOR_SPACING_Y + (column * 11) % 30
        anchor_node = anchor.create_anchor_named(name, color=color)
        anchor_node.setXYpos(xpos, ypos)
        positions.append((xpos, ypos))
    if label in NESTED_SUBMODULES:
        sub_label, count = NESTED_SUBMODULES[label]
        nested = positions[-count:]
        sub_left = min(x for x, _y in nested) - 25
        sub_top = min(y for _x, y in nested) - 45
        sub_right = max(x for x, _y in nested) + 105
        sub_bottom = max(y for _x, y in nested) + 45
        make_backdrop(sub_label, sub_left, sub_top, sub_right - sub_left,
                      sub_bottom - sub_top, color)


def build_comp_branches(top):
    for branch in range(COMP_BRANCHES):
        xpos = 400 + branch * BRANCH_SPACING_X
        for index in range(DOTS_PER_BRANCH):
            dot = nuke.nodes.Dot()
            label = DOT_LABELS[(branch + index) % len(DOT_LABELS)]
            dot['label'].setValue(label)
            dot['note_font_size'].setValue(DOT_LABEL_FONT_SIZES[(branch * 3 + index) % 3])
            link.mark_dot_as_anchor(dot)
            dot.setXYpos(xpos + (index % 3) * 70, top + index * DOT_SPACING_Y)


def main():
    if len(sys.argv) < 2:
        print("usage: nuke -t validation/build_large_script.py OUTPUT.nk")
        sys.exit(2)
    output_path = os.path.abspath(sys.argv[1])

    nuke.scriptClear()
    for index, (label, color, anchor_names) in enumerate(MODULES):
        column = index % MODULE_COLUMNS
        row = index // MODULE_COLUMNS
        build_module(label, color, anchor_names,
                     column * MODULE_SPACING_X, row * MODULE_SPACING_Y)
    rows = (len(MODULES) + MODULE_COLUMNS - 1) // MODULE_COLUMNS
    notes_top = rows * MODULE_SPACING_Y
    for label, column in EMPTY_NOTES:
        make_backdrop(label, column * MODULE_SPACING_X, notes_top, 400, 250, 0x444444FF)
    build_comp_branches(notes_top + 500)

    nuke.scriptSaveAs(output_path, overwrite=1)
    anchor_count = len([node for node in nuke.allNodes() if link.is_anchor(node)])
    print("Wrote %s with %d anchors" % (output_path, anchor_count))


main()
