"""Tests for spatial_view.py — the map layout, what the map lists, and how it opens.

The Qt widgets are not under test (a stubbed PySide6 cannot lay out or paint
anything). What is tested is everything they are a thin shell over:

  - compress_axis / build_layout — the DAG-to-map mapping: real order kept,
    empty space squeezed out, nothing colliding, backdrops framing exactly what
    they enclose, and empty backdrops drawn as boxes of their own.
  - fit_zoom / clamp_user_zoom — how far fitting and the user may zoom.
  - collect_entries / layout_items_for — what the map shows in each mode.
  - open_picker, and the A / Alt+A entry points that call it only when the
    preference is on.
"""

import ast
import importlib
import itertools
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

from tests.stubs import StubKnob, StubNode

import spatial_view
from constants import (
    SPATIAL_BACKDROP_HEADER,
    SPATIAL_BACKDROP_PADDING,
    SPATIAL_DOT_TIERS,
    SPATIAL_EMPTY_BACKDROP_SCALE,
    SPATIAL_ITEM_GAP,
    SPATIAL_MAX_GAP,
    SPATIAL_MAX_USER_ZOOM,
    SPATIAL_MIN_FIT_ZOOM,
    SPATIAL_MIN_USER_ZOOM,
    SPATIAL_TILE_HEIGHT,
    SPATIAL_TILE_WIDTH,
)

def _char_width(text, _point_size):
    return len(text)


_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

_TILE_SIZE = (SPATIAL_TILE_WIDTH, SPATIAL_TILE_HEIGHT)
_EMPTY_SIZE = (SPATIAL_TILE_WIDTH * SPATIAL_EMPTY_BACKDROP_SCALE,
               SPATIAL_TILE_HEIGHT * SPATIAL_EMPTY_BACKDROP_SCALE)


def _tile(key, x, y):
    return {'key': key, 'kind': spatial_view.KIND_TILE, 'x': x, 'y': y,
            'size': _TILE_SIZE, 'origin': (_TILE_SIZE[0] / 2.0, _TILE_SIZE[1] / 2.0)}


def _dot(key, x, y, width=60):
    return {'key': key, 'kind': spatial_view.KIND_DOT, 'x': x, 'y': y,
            'size': (width, 14), 'origin': (6, 7)}


def _backdrop(key, x, y, width, height, min_width=0):
    return {'key': key, 'kind': spatial_view.KIND_BACKDROP, 'x': x, 'y': y,
            'width': width, 'height': height, 'size': _EMPTY_SIZE, 'min_width': min_width}


def _overlaps(first, second, clearance=0):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return (ax < bx + bw + clearance and bx < ax + aw + clearance
            and ay < by + bh + clearance and by < ay + ah + clearance)


def _encloses(outer, inner):
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh


def _centre_x(rect):
    return rect[0] + rect[2] / 2.0


def _centre_y(rect):
    return rect[1] + rect[3] / 2.0


class TestCompressAxis(unittest.TestCase):
    """Order survives, small gaps keep their proportion, big gaps collapse."""

    def test_order_is_preserved(self):
        positions = spatial_view.compress_axis([300, -100, 50])
        self.assertLess(positions[-100], positions[50])
        self.assertLess(positions[50], positions[300])

    def test_first_value_is_at_zero(self):
        self.assertEqual(spatial_view.compress_axis([500, 700])[500], 0)

    def test_small_gaps_are_scaled(self):
        positions = spatial_view.compress_axis([0, 20], scale=0.5, max_gap=100)
        self.assertEqual(positions[20], 10)

    def test_large_gaps_are_capped(self):
        positions = spatial_view.compress_axis([0, 5000, 5010], scale=0.5, max_gap=40)
        self.assertEqual(positions[5000], 40)
        self.assertEqual(positions[5010], 45)

    def test_equal_values_share_a_position(self):
        positions = spatial_view.compress_axis([10, 10, 30])
        self.assertEqual(len(positions), 2)

    def test_no_values_gives_no_positions(self):
        self.assertEqual(spatial_view.compress_axis([]), {})


class TestBuildLayoutPlacement(unittest.TestCase):
    """Items stay where the DAG puts them, relative to each other."""

    def test_empty_layout_is_empty(self):
        layout = spatial_view.build_layout([])
        self.assertEqual(layout['rects'], {})
        self.assertEqual((layout['width'], layout['height']), (0, 0))

    def test_left_right_and_above_below_are_preserved(self):
        rects = spatial_view.build_layout([
            _tile('top_left', 0, 0),
            _tile('top_right', 2000, 0),
            _tile('bottom_left', 0, 1500),
        ])['rects']
        self.assertLess(_centre_x(rects['top_left']), _centre_x(rects['top_right']))
        self.assertLess(_centre_y(rects['top_left']), _centre_y(rects['bottom_left']))

    def test_blank_space_between_distant_items_is_collapsed(self):
        rects = spatial_view.build_layout([_tile('a', 0, 0), _tile('b', 10000, 0)])['rects']
        distance = _centre_x(rects['b']) - _centre_x(rects['a'])
        self.assertLessEqual(distance, SPATIAL_TILE_WIDTH + SPATIAL_MAX_GAP + SPATIAL_ITEM_GAP)

    def test_layout_is_normalised_to_the_origin(self):
        layout = spatial_view.build_layout([_tile('a', -5000, -3000), _tile('b', 400, 90)])
        self.assertEqual(min(x for x, _y, _w, _h in layout['rects'].values()), 0)
        self.assertEqual(min(y for _x, y, _w, _h in layout['rects'].values()), 0)

    def test_extent_covers_every_item(self):
        layout = spatial_view.build_layout([_tile('a', 0, 0), _dot('b', 300, 400)])
        for x, y, width, height in layout['rects'].values():
            self.assertLessEqual(x + width, layout['width'])
            self.assertLessEqual(y + height, layout['height'])

    def test_layout_does_not_depend_on_input_order(self):
        items = [_tile('a', 0, 0), _tile('b', 30, 5), _dot('c', 10, 10),
                 _backdrop('bd', -100, -100, 400, 400)]
        expected = spatial_view.build_layout(items)['rects']
        for permutation in itertools.permutations(items):
            self.assertEqual(spatial_view.build_layout(list(permutation))['rects'], expected)

    def test_backdrop_modules_keep_their_order(self):
        # A row of modules, staggered vertically, as in a typical comp: packing
        # must close the gaps between them without swapping or stacking any.
        items = [
            _backdrop('plates', 0, 330, 870, 500), _tile('plates_main', 200, 700),
            _tile('plates_ref', 530, 540),
            _backdrop('cg', 960, 70, 690, 560), _tile('cg_main', 1130, 370),
            _tile('cg_atmo', 1350, 370),
            _backdrop('camera', 1670, -330, 440, 500), _tile('camera_main', 1780, -20),
            _backdrop('foo', 2150, 0, 500, 470), _tile('foo_foo', 2330, 300),
            _backdrop('roto', 2750, 50, 530, 480), _tile('roto_head', 2900, 300),
        ]
        rects = spatial_view.build_layout(items)['rects']
        modules = ['plates', 'cg', 'camera', 'foo', 'roto']
        for left_module, right_module in zip(modules, modules[1:]):
            self.assertLessEqual(rects[left_module][0] + rects[left_module][2],
                                 rects[right_module][0])
        tops = sorted(modules, key=lambda module: rects[module][1])
        self.assertEqual(tops, ['camera', 'foo', 'roto', 'cg', 'plates'])

    def test_diagonal_neighbours_tuck_in_without_a_sideways_push(self):
        rects = spatial_view.build_layout([_tile('a', 0, 0), _tile('b', 100, 400)])['rects']
        self.assertLess(_centre_x(rects['a']), _centre_x(rects['b']))
        self.assertLess(_centre_x(rects['b']) - _centre_x(rects['a']), SPATIAL_TILE_WIDTH)
        self.assertFalse(_overlaps(rects['a'], rects['b']))

    def test_packing_never_swaps_two_items(self):
        dag_positions = [(column * 37 % 290, row * 23 % 170)
                         for row in range(6) for column in range(7)]
        items = [_tile('t%d' % index, x, y) for index, (x, y) in enumerate(dag_positions)]
        rects = spatial_view.build_layout(items)['rects']
        for first, second in itertools.combinations(items, 2):
            first_rect, second_rect = rects[first['key']], rects[second['key']]
            if first['x'] < second['x']:
                self.assertLess(_centre_x(first_rect), _centre_x(second_rect))
            if first['y'] < second['y']:
                self.assertLess(_centre_y(first_rect), _centre_y(second_rect))


class TestBuildLayoutDeOverlap(unittest.TestCase):
    """Nothing collides, however crowded the DAG is."""

    def _assert_no_collisions(self, rects, keys):
        for first, second in itertools.combinations(keys, 2):
            self.assertFalse(
                _overlaps(rects[first], rects[second]),
                "%s %s collides with %s %s" % (first, rects[first], second, rects[second]))

    def test_items_at_the_same_position_are_pulled_apart(self):
        rects = spatial_view.build_layout([_tile('a', 0, 0), _tile('b', 0, 0)])['rects']
        self._assert_no_collisions(rects, ['a', 'b'])

    def test_a_crowded_cluster_ends_with_no_collisions(self):
        items = [_tile('t%d_%d' % (row, column), column * 40, row * 20)
                 for row in range(5) for column in range(6)]
        items += [_dot('d%d' % index, index * 25, 30) for index in range(8)]
        rects = spatial_view.build_layout(items)['rects']
        self._assert_no_collisions(rects, [item['key'] for item in items])

    def test_separated_items_keep_the_gap_between_them(self):
        rects = spatial_view.build_layout([_tile('a', 0, 0), _tile('b', 1, 0)])['rects']
        self.assertFalse(_overlaps(rects['a'], rects['b'], clearance=SPATIAL_ITEM_GAP - 0.01))

    def test_side_by_side_neighbours_separate_sideways(self):
        rects = spatial_view.build_layout([_tile('a', 0, 0), _tile('b', 60, 0)])['rects']
        self.assertEqual(_centre_y(rects['a']), _centre_y(rects['b']))
        self.assertLess(_centre_x(rects['a']), _centre_x(rects['b']))

    def test_backdrop_frames_do_not_collide_with_each_other(self):
        items = [
            _backdrop('left', 0, 0, 200, 200), _tile('a', 100, 100),
            _backdrop('right', 210, 0, 200, 200), _tile('b', 310, 100),
        ]
        rects = spatial_view.build_layout(items)['rects']
        self.assertFalse(_overlaps(rects['left'], rects['right']))


class TestBuildLayoutBackdrops(unittest.TestCase):
    """Backdrops frame what they really enclose; empty ones are faded boxes."""

    def test_backdrop_frames_the_anchors_inside_it(self):
        layout = spatial_view.build_layout([
            _backdrop('bd', 0, 0, 1000, 600),
            _tile('a', 100, 100), _tile('b', 800, 500), _dot('c', 400, 300),
        ])
        self.assertIn('bd', layout['frames'])
        for key in ('a', 'b', 'c'):
            self.assertTrue(_encloses(layout['rects']['bd'], layout['rects'][key]), key)

    def test_frame_leaves_room_for_the_header_and_padding(self):
        rects = spatial_view.build_layout([
            _backdrop('bd', 0, 0, 500, 500), _tile('a', 100, 100)])['rects']
        frame_x, frame_y, _w, _h = rects['bd']
        tile_x, tile_y, _tw, _th = rects['a']
        self.assertEqual(tile_x - frame_x, SPATIAL_BACKDROP_PADDING)
        self.assertEqual(tile_y - frame_y, SPATIAL_BACKDROP_PADDING + SPATIAL_BACKDROP_HEADER)

    def test_frame_is_at_least_as_wide_as_its_label(self):
        rects = spatial_view.build_layout([
            _backdrop('bd', 0, 0, 500, 500, min_width=400), _tile('a', 100, 100)])['rects']
        self.assertEqual(rects['bd'][2], 400)

    def test_anchor_outside_the_backdrop_is_not_framed(self):
        layout = spatial_view.build_layout([
            _backdrop('bd', 0, 0, 300, 300), _tile('inside', 100, 100),
            _tile('outside', 350, 100)])
        self.assertIsNone(layout['parent']['outside'])
        self.assertFalse(_overlaps(layout['rects']['bd'], layout['rects']['outside']))

    def test_anchors_belong_to_the_innermost_backdrop(self):
        layout = spatial_view.build_layout([
            _backdrop('outer', 0, 0, 1000, 1000),
            _backdrop('inner', 100, 100, 300, 300),
            _tile('a', 200, 200), _tile('b', 700, 700),
        ])
        self.assertEqual(layout['parent']['a'], 'inner')
        self.assertEqual(layout['parent']['b'], 'outer')
        self.assertEqual(layout['parent']['inner'], 'outer')
        self.assertTrue(_encloses(layout['rects']['outer'], layout['rects']['inner']))
        self.assertTrue(_encloses(layout['rects']['inner'], layout['rects']['a']))
        self.assertEqual(layout['depth'], {'outer': 0, 'inner': 1})

    def test_backdrop_without_anchors_is_a_box_half_as_large_again_as_a_tile(self):
        layout = spatial_view.build_layout([
            _backdrop('empty', 0, 0, 300, 300), _tile('a', 1000, 0)])
        self.assertNotIn('empty', layout['frames'])
        _x, _y, width, height = layout['rects']['empty']
        self.assertEqual((width, height), (SPATIAL_TILE_WIDTH * 1.5, SPATIAL_TILE_HEIGHT * 1.5))

    def test_empty_backdrop_inside_a_framed_one_is_enclosed_by_it(self):
        layout = spatial_view.build_layout([
            _backdrop('outer', 0, 0, 2000, 2000),
            _backdrop('empty', 100, 100, 200, 200),
            _tile('a', 1500, 1500),
        ])
        self.assertEqual(layout['parent']['empty'], 'outer')
        self.assertTrue(_encloses(layout['rects']['outer'], layout['rects']['empty']))

    def test_empty_backdrop_nested_in_another_empty_one_stays_a_box(self):
        layout = spatial_view.build_layout([
            _backdrop('outer', 0, 0, 1000, 1000),
            _backdrop('inner', 100, 100, 200, 200),
            _tile('a', 3000, 0),
        ])
        self.assertEqual(layout['frames'], set())
        self.assertFalse(_overlaps(layout['rects']['outer'], layout['rects']['inner']))


class TestZoomLimits(unittest.TestCase):
    """Fitting fills the view without blowing up or shrinking past readable."""

    def test_matches_that_fit_are_shown_at_full_size(self):
        self.assertEqual(spatial_view.fit_zoom(300, 200, 1400, 900), 1.0)

    def test_matches_wider_than_the_view_are_zoomed_out_to_fit(self):
        self.assertAlmostEqual(spatial_view.fit_zoom(1600, 400, 1400, 900), 1400 / 1600.0)

    def test_the_tighter_axis_decides_the_zoom(self):
        self.assertAlmostEqual(spatial_view.fit_zoom(1500, 1000, 1400, 900), 0.9)

    def test_fitting_stops_at_the_readable_minimum(self):
        self.assertEqual(spatial_view.fit_zoom(6000, 400, 1400, 900), SPATIAL_MIN_FIT_ZOOM)

    def test_empty_bounds_fit_at_full_size(self):
        self.assertEqual(spatial_view.fit_zoom(0, 0, 1400, 900), 1.0)

    def test_user_zoom_is_clamped_to_its_range(self):
        self.assertEqual(spatial_view.clamp_user_zoom(0.01), SPATIAL_MIN_USER_ZOOM)
        self.assertEqual(spatial_view.clamp_user_zoom(50), SPATIAL_MAX_USER_ZOOM)
        self.assertEqual(spatial_view.clamp_user_zoom(1.3), 1.3)

    def test_the_user_can_zoom_out_further_than_fitting_does(self):
        self.assertLess(SPATIAL_MIN_USER_ZOOM, SPATIAL_MIN_FIT_ZOOM)


def _anchor_node(name, xpos=0, ypos=0, tile_color=0xAABBCCFF):
    return StubNode(name=name, node_class='NoOp', xpos=xpos, ypos=ypos,
                    knobs_dict={'tile_color': StubKnob(tile_color)})


def _dot_node(name, xpos=0, ypos=0, hide_input=False, font_size=33):
    return StubNode(name=name, node_class='Dot', xpos=xpos, ypos=ypos,
                    knobs_dict={'tile_color': StubKnob(0x7F00FFFF),
                                'hide_input': StubKnob(hide_input),
                                'note_font_size': StubKnob(font_size),
                                'label': StubKnob(name)})


def _backdrop_node(name, xpos=0, ypos=0, width=400, height=400, label='plates'):
    return StubNode(name=name, node_class='BackdropNode', xpos=xpos, ypos=ypos,
                    knobs_dict={
                        'tile_color': StubKnob(0x223344FF),
                        'label': StubKnob(label),
                        'bdwidth': StubKnob(width),
                        'bdheight': StubKnob(height),
                    })


def _item(node, menupath):
    return {'menuobj': node, 'menupath': menupath}


class TestCollectEntries(unittest.TestCase):
    """The map shows what the picker lists, plus backdrops for context."""

    def test_entries_are_keyed_by_node_name_and_sorted_into_kinds(self):
        items = [
            _item(_anchor_node('Anchor_BG'), 'Anchors/BG'),
            _item(_dot_node('Dot1'), 'Anchors/keyer'),
            _item(_backdrop_node('BackdropNode1'), 'Backdrops/plates'),
        ]
        entries = spatial_view.collect_entries(items, spatial_view.MODE_NAVIGATE, None)
        self.assertEqual([entry['key'] for entry in entries],
                         ['Anchor_BG', 'Dot1', 'BackdropNode1'])
        self.assertEqual([entry['kind'] for entry in entries],
                         [spatial_view.KIND_TILE, spatial_view.KIND_DOT,
                          spatial_view.KIND_BACKDROP])
        self.assertEqual([entry['name'] for entry in entries], ['BG', 'keyer', 'plates'])
        self.assertTrue(all(entry['selectable'] for entry in entries))

    def test_local_dots_never_appear(self):
        items = [_item(_dot_node('Dot2', hide_input=True), 'Anchors/Local: Grade1')]
        self.assertEqual(
            spatial_view.collect_entries(items, spatial_view.MODE_NAVIGATE, None), [])

    def test_create_link_mode_adds_backdrops_as_unselectable_context(self):
        items = [_item(_anchor_node('Anchor_BG'), 'Anchors/BG')]
        with patch.object(sys.modules['nuke'], 'allNodes',
                          return_value=[_backdrop_node('BackdropNode1')]):
            entries = spatial_view.collect_entries(
                items, spatial_view.MODE_CREATE_LINK, MagicMock())
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]['kind'], spatial_view.KIND_BACKDROP)
        self.assertFalse(entries[1]['selectable'])
        self.assertEqual(entries[1]['item']['menupath'], 'Backdrops/plates')

    def test_create_link_mode_skips_unlabelled_backdrops(self):
        items = [_item(_anchor_node('Anchor_BG'), 'Anchors/BG')]
        with patch.object(sys.modules['nuke'], 'allNodes',
                          return_value=[_backdrop_node('BackdropNode2', label='  ')]):
            entries = spatial_view.collect_entries(
                items, spatial_view.MODE_CREATE_LINK, MagicMock())
        self.assertEqual(len(entries), 1)


class TestLayoutItemsFor(unittest.TestCase):
    """Node geometry becomes layout geometry."""

    def _entries(self, *items):
        return spatial_view.collect_entries(list(items), spatial_view.MODE_NAVIGATE, None)

    def test_anchors_are_placed_by_their_centre(self):
        entries = self._entries(_item(_anchor_node('Anchor_BG', 100, 200), 'Anchors/BG'))
        (layout_item,) = spatial_view.layout_items_for(entries, _char_width)
        self.assertEqual((layout_item['x'], layout_item['y']), (150, 225))
        self.assertEqual(layout_item['size'], _TILE_SIZE)

    def test_dot_box_makes_room_for_its_label(self):
        short, long_ = spatial_view.layout_items_for(self._entries(
            _item(_dot_node('Dot1'), 'Anchors/a'),
            _item(_dot_node('Dot2'), 'Anchors/a much longer label'),
        ), lambda text, _point_size: 7 * len(text))
        self.assertGreater(long_['size'][0], short['size'][0])
        self.assertEqual(short['origin'][0], SPATIAL_DOT_TIERS[0][1] / 2.0)

    def test_larger_dot_labels_get_larger_dots_and_text(self):
        measured_point_sizes = []

        def text_width(text, point_size):
            measured_point_sizes.append(point_size)
            return 7 * len(text)

        small, large = spatial_view.layout_items_for(self._entries(
            _item(_dot_node('Dot1', font_size=33), 'Anchors/key'),
            _item(_dot_node('Dot2', font_size=111), 'Anchors/key'),
        ), text_width)
        self.assertEqual(small['origin'][0], SPATIAL_DOT_TIERS[0][1] / 2.0)
        self.assertEqual(large['origin'][0], SPATIAL_DOT_TIERS[2][1] / 2.0)
        self.assertGreater(large['size'][1], small['size'][1])
        self.assertEqual(measured_point_sizes, [SPATIAL_DOT_TIERS[0][2], SPATIAL_DOT_TIERS[2][2]])


    def test_backdrops_carry_their_dag_bounds(self):
        (layout_item,) = spatial_view.layout_items_for(self._entries(
            _item(_backdrop_node('BackdropNode1', 10, 20, 300, 400), 'Backdrops/plates')), _char_width)
        self.assertEqual(
            (layout_item['x'], layout_item['y'], layout_item['width'], layout_item['height']),
            (10, 20, 300, 400))
        self.assertEqual(layout_item['size'], _EMPTY_SIZE)


class TestDotTier(unittest.TestCase):
    """A Dot's map size follows the nearest of the three Dot label presets."""

    def test_presets_map_to_their_own_tier(self):
        self.assertEqual([spatial_view.dot_tier(33), spatial_view.dot_tier(66),
                          spatial_view.dot_tier(111)], [0, 1, 2])

    def test_in_between_sizes_take_the_nearest_preset(self):
        self.assertEqual(spatial_view.dot_tier(45), 0)
        self.assertEqual(spatial_view.dot_tier(55), 1)
        self.assertEqual(spatial_view.dot_tier(95), 2)
        self.assertEqual(spatial_view.dot_tier(400), 2)

    def test_collected_dots_carry_their_tier(self):
        (entry,) = spatial_view.collect_entries(
            [_item(_dot_node('Dot1', font_size=66), 'Anchors/key')],
            spatial_view.MODE_NAVIGATE, None)
        self.assertEqual(entry['tier'], 1)


class TestColours(unittest.TestCase):
    """Map items read like the nodes they stand for."""

    def test_tile_colour_is_used_when_set(self):
        self.assertEqual(spatial_view.node_color(_anchor_node('A', tile_color=0x123456FF)),
                         0x123456FF)

    def test_uncoloured_backdrop_falls_back_to_the_default(self):
        node = _backdrop_node('BackdropNode1')
        node['tile_color'].setValue(0)
        self.assertEqual(spatial_view.node_color(node), spatial_view._DEFAULT_BACKDROP_COLOR)

    def test_uncoloured_anchor_falls_back_to_the_dag_colour(self):
        node = _anchor_node('Anchor_BG', tile_color=0)
        with patch('anchor.find_anchor_color', return_value=0x998877FF):
            self.assertEqual(spatial_view.node_color(node), 0x998877FF)

    def test_light_and_dark_tiles(self):
        self.assertTrue(spatial_view.is_light(0xFFFFFFFF))
        self.assertFalse(spatial_view.is_light(0x101010FF))


class TestOpenPicker(unittest.TestCase):
    """One picker per mode, reused, always pointed at the current group."""

    def setUp(self):
        spatial_view._pickers.clear()

    def tearDown(self):
        spatial_view._pickers.clear()

    def test_without_qt_nothing_opens(self):
        with patch.object(spatial_view, 'SpatialPicker', None):
            self.assertIsNone(spatial_view.open_picker(spatial_view.MODE_NAVIGATE, MagicMock()))

    def test_first_open_builds_and_shows_a_picker(self):
        hit_group = MagicMock()
        plugin = MagicMock()
        with patch.object(spatial_view, 'SpatialPicker') as picker_class, \
                patch.object(spatial_view, '_plugin_for_mode', return_value=plugin), \
                patch.object(spatial_view, 'host_main_window', return_value=None), \
                patch.object(spatial_view, 'space_mode_order', return_value=['x']):
            picker = spatial_view.open_picker(spatial_view.MODE_NAVIGATE, hit_group)
        self.assertIs(picker, picker_class.return_value)
        self.assertIs(plugin._hit_group, hit_group)
        picker.show.assert_called_once_with()

    def test_reopening_reuses_the_picker_with_the_new_group(self):
        cached = MagicMock()
        spatial_view._pickers[spatial_view.MODE_CREATE_LINK] = cached
        hit_group = MagicMock()
        with patch.object(spatial_view, 'SpatialPicker') as picker_class, \
                patch.object(spatial_view, 'host_main_window', return_value=None), \
                patch.object(spatial_view, 'space_mode_order', return_value=['x']):
            picker = spatial_view.open_picker(spatial_view.MODE_CREATE_LINK, hit_group)
        picker_class.assert_not_called()
        self.assertIs(picker, cached)
        self.assertIs(cached.plugin._hit_group, hit_group)
        self.assertEqual(cached.things_model._space_mode_order, ['x'])

    def test_a_given_plugin_replaces_the_reused_pickers_plugin(self):
        cached = MagicMock()
        spatial_view._pickers[spatial_view.MODE_CREATE_LINK] = cached
        custom_plugin = MagicMock()
        hit_group = MagicMock()
        with patch.object(spatial_view, 'SpatialPicker'), \
                patch.object(spatial_view, 'space_mode_order', return_value=['x']):
            spatial_view.open_picker(spatial_view.MODE_CREATE_LINK, hit_group,
                                     plugin=custom_plugin)
        self.assertIs(cached.plugin, custom_plugin)
        self.assertIs(custom_plugin._hit_group, hit_group)

    def test_reopening_without_a_plugin_restores_the_default_one(self):
        cached = MagicMock()
        spatial_view._pickers[spatial_view.MODE_CREATE_LINK] = cached
        default_plugin = MagicMock()
        with patch.object(spatial_view, 'SpatialPicker'), \
                patch.object(spatial_view, '_plugin_for_mode', return_value=default_plugin), \
                patch.object(spatial_view, 'space_mode_order', return_value=['x']):
            spatial_view.open_picker(spatial_view.MODE_CREATE_LINK, MagicMock())
        self.assertIs(cached.plugin, default_plugin)

    def test_a_destroyed_picker_is_rebuilt(self):
        dead = MagicMock()
        dead.isVisible.side_effect = RuntimeError
        spatial_view._pickers[spatial_view.MODE_NAVIGATE] = dead
        with patch.object(spatial_view, 'SpatialPicker') as picker_class, \
                patch.object(spatial_view, '_plugin_for_mode', return_value=MagicMock()), \
                patch.object(spatial_view, 'host_main_window', return_value=None), \
                patch.object(spatial_view, 'space_mode_order', return_value=['x']):
            picker = spatial_view.open_picker(spatial_view.MODE_NAVIGATE, MagicMock())
        self.assertIs(picker, picker_class.return_value)


class TestPickerEntryPoints(unittest.TestCase):
    """A / Alt+A open the spatial picker only when the preference is on."""

    def setUp(self):
        from tests.test_anchor_navigation import _ensure_qt_stubs_support_mock_attributes
        _ensure_qt_stubs_support_mock_attributes()
        import anchor
        importlib.reload(anchor)
        self.anchor = anchor
        anchor._anchor_picker_widget = None
        anchor._anchor_navigate_widget = None
        nuke_stub = sys.modules['nuke']
        nuke_stub.allNodes.side_effect = None
        nuke_stub.allNodes.return_value = [_backdrop_node('BackdropNode1')]

    def _run(self, entry_point, spatial_enabled):
        with patch.object(self.anchor.prefs, 'plugin_enabled', True), \
                patch.object(self.anchor.prefs, 'spatial_view_enabled', spatial_enabled), \
                patch.object(self.anchor, 'all_anchors', return_value=[_anchor_node('Anchor_BG')]), \
                patch.object(spatial_view, 'open_picker', return_value=MagicMock()) as open_picker, \
                patch.object(sys.modules['tabtabtab_anchors'], 'TabTabTabWidget') as widget_class:
            entry_point()
        return open_picker, widget_class

    def test_navigate_opens_the_spatial_picker_when_enabled(self):
        open_picker, widget_class = self._run(self.anchor.select_anchor_and_navigate, True)
        self.assertEqual(open_picker.call_args.args[0], spatial_view.MODE_NAVIGATE)
        widget_class.assert_not_called()

    def test_create_link_opens_the_spatial_picker_when_enabled(self):
        open_picker, widget_class = self._run(lambda: self.anchor.select_anchor_and_create(MagicMock()), True)
        self.assertEqual(open_picker.call_args.args[0], spatial_view.MODE_CREATE_LINK)
        widget_class.assert_not_called()

    def test_set_input_picker_opens_the_spatial_picker_when_enabled(self):
        on_pick = MagicMock()
        open_picker, widget_class = self._run(
            lambda: self.anchor.pick_anchor(on_pick, MagicMock()), True)
        self.assertEqual(open_picker.call_args.args[0], spatial_view.MODE_CREATE_LINK)
        plugin = open_picker.call_args.kwargs['plugin']
        anchor_node = _anchor_node('Anchor_BG')
        with patch.object(sys.modules['nuke'], 'exists', return_value=True, create=True):
            plugin.invoke({'menuobj': anchor_node})
        on_pick.assert_called_once()
        widget_class.assert_not_called()

    def test_plain_pickers_open_unchanged_when_disabled(self):
        for entry_point in (self.anchor.select_anchor_and_navigate,
                            lambda: self.anchor.select_anchor_and_create(MagicMock()),
                            lambda: self.anchor.pick_anchor(MagicMock(), MagicMock())):
            self.anchor._anchor_picker_widget = None
            self.anchor._anchor_navigate_widget = None
            open_picker, widget_class = self._run(entry_point, False)
            open_picker.assert_not_called()
            widget_class.assert_called_once()


class TestPrefsDialogSpatialViewCheckbox(unittest.TestCase):
    """The preference is exposed in the Preferences dialog."""

    def _method_source(self, method_name):
        source_text = (_REPO_ROOT / 'colors.py').read_text()
        for node in ast.walk(ast.parse(source_text)):
            if isinstance(node, ast.ClassDef) and node.name == 'PrefsDialog':
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        lines = source_text.splitlines()
                        return '\n'.join(lines[item.lineno - 1:item.end_lineno])
        self.fail(method_name + " not found in PrefsDialog")

    def test_dialog_seeds_shows_and_flushes_the_preference(self):
        self.assertIn('self._local_spatial_view_enabled = prefs_module.spatial_view_enabled',
                      self._method_source('__init__'))
        self.assertIn('setChecked(self._local_spatial_view_enabled)',
                      self._method_source('_build_ui'))
        on_accept_source = self._method_source('_on_accept')
        self.assertIn('self._spatial_view_checkbox.isChecked()', on_accept_source)
        self.assertIn('prefs_module.spatial_view_enabled', on_accept_source)


if __name__ == '__main__':
    unittest.main()
