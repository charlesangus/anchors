"""Tests for spatial_view.py — the grid layout, the filter, and the entry points.

The Qt widgets are not under test (a stubbed PySide6 cannot lay out or paint
anything). What is tested is everything the widgets are a thin shell over:

  - assign_cells / build_layout — the DAG-to-grid mapping that makes the popup a
    map of the script: relative order preserved, nearby nodes sharing a cell
    row/column, collisions resolved to distinct cells, the grid capped in size,
    and backdrops spanning the cells of the anchors they contain.
  - rank_entries — the pickers' fuzzy search applied to cards, including the
    space-prefix search modes and the selection weights.
  - cell_in_direction — spatial arrow-key movement across the matched cards.
  - collect_entries / layout_for_entries — what the view lists in each mode.
  - open_view — the guards that make the command a silent no-op.

The fuzzy-find functions live in tabtabtab_anchors, which the shared test stubs
replace with a bare module; the real (Qt-free) search functions are loaded onto
that stub here so the filter is exercised against the code that actually ships.
"""

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from tests.stubs import StubKnob, StubNode

_REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SEARCH_ATTRIBUTES = (
    'consec_find',
    'nonconsec_find',
    'parse_search_modes',
    'menupath_uiname',
    'DEFAULT_SPACE_MODE_ORDER',
    'VALID_MODES',
    'MODE_ANCHORED_FUZZY',
    'MODE_NON_ANCHORED_FUZZY',
    'MODE_CONSECUTIVE',
)


def _install_real_search_functions():
    """Copy tabtabtab_anchors' real search functions onto the stub module."""
    spec = importlib.util.spec_from_file_location(
        'tabtabtab_anchors_real', os.path.join(_REPOSITORY_ROOT, 'tabtabtab_anchors.py'))
    real_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real_module)
    stub_module = sys.modules['tabtabtab_anchors']
    for attribute_name in _SEARCH_ATTRIBUTES:
        setattr(stub_module, attribute_name, getattr(real_module, attribute_name))


_install_real_search_functions()

import spatial_view  # noqa: E402 — must follow the stub set-up above


def _anchor(key, x, y):
    return {'key': key, 'x': x, 'y': y}


def _backdrop(key, x, y, width, height):
    return {'key': key, 'x': x, 'y': y, 'width': width, 'height': height}


def _entry(key, menupath, kind='anchor', selectable=True, node=None):
    return {
        'key': key,
        'menupath': menupath,
        'node': node,
        'item': {'menuobj': node, 'menupath': menupath},
        'kind': kind,
        'selectable': selectable,
    }


class TestAssignCells(unittest.TestCase):
    """The grid echoes DAG geometry: same order, no overlaps, bounded size."""

    def test_no_placements_gives_no_cells(self):
        self.assertEqual(spatial_view.assign_cells([]), {})

    def test_single_placement_lands_on_the_origin_cell(self):
        cells = spatial_view.assign_cells([('a', 900, -400)])
        self.assertEqual(cells, {'a': (0, 0)})

    def test_left_to_right_order_is_preserved(self):
        cells = spatial_view.assign_cells(
            [('left', 0, 0), ('middle', 500, 0), ('right', 1000, 0)], tolerance=100)
        self.assertLess(cells['left'][1], cells['middle'][1])
        self.assertLess(cells['middle'][1], cells['right'][1])

    def test_top_to_bottom_order_is_preserved(self):
        cells = spatial_view.assign_cells(
            [('top', 0, 0), ('bottom', 0, 600)], tolerance=100)
        self.assertLess(cells['top'][0], cells['bottom'][0])

    def test_nearby_coordinates_share_a_column(self):
        # Two anchors 40 units apart in x are one module's worth apart, so they
        # belong in the same column of the simplified map.
        cells = spatial_view.assign_cells(
            [('a', 0, 0), ('b', 40, 300)], tolerance=140)
        self.assertEqual(cells['a'][1], cells['b'][1])

    def test_coordinates_beyond_the_tolerance_get_their_own_column(self):
        cells = spatial_view.assign_cells(
            [('a', 0, 0), ('b', 400, 0)], tolerance=140)
        self.assertNotEqual(cells['a'][1], cells['b'][1])

    def test_identical_positions_still_get_distinct_cells(self):
        cells = spatial_view.assign_cells(
            [('a', 100, 100), ('b', 100, 100), ('c', 100, 100)])
        self.assertEqual(len(set(cells.values())), 3)

    def test_colliding_cards_stack_down_their_own_column(self):
        # A module's anchors sit at nearly the same x, so a collision must never
        # push a card into a neighbouring module's column.
        cells = spatial_view.assign_cells(
            [('a', 0, 0), ('b', 0, 0), ('c', 0, 0)], tolerance=140)
        self.assertEqual({column for _row, column in cells.values()}, {0})
        self.assertEqual(sorted(row for row, _column in cells.values()), [0, 1, 2])

    def test_cells_are_normalised_to_the_origin(self):
        cells = spatial_view.assign_cells(
            [('a', -5000, -5000), ('b', -4000, -4000)], tolerance=100)
        self.assertEqual(min(row for row, _column in cells.values()), 0)
        self.assertEqual(min(column for _row, column in cells.values()), 0)

    def test_wide_scripts_are_capped_at_the_maximum_columns(self):
        # 30 anchors spread across a huge script would otherwise give 30 columns.
        placements = [(index, index * 1000, 0) for index in range(30)]
        cells = spatial_view.assign_cells(placements, tolerance=140, max_rows=8, max_columns=6)
        self.assertLessEqual(max(column for _row, column in cells.values()), 5)
        self.assertEqual(len(set(cells.values())), len(placements))

    def test_binning_widens_the_tolerance_until_the_axis_fits(self):
        values = [index * 1000 for index in range(30)]
        bins = spatial_view._binned_axis(values, tolerance=140, maximum=6)
        self.assertLessEqual(max(bins.values()) + 1, 6)
        # Widening merges neighbours, so the original order still holds.
        self.assertLessEqual(bins[values[0]], bins[values[-1]])

    def test_layout_does_not_depend_on_input_order(self):
        placements = [('a', 0, 0), ('b', 500, 0), ('c', 0, 500), ('d', 500, 500)]
        first = spatial_view.assign_cells(placements, tolerance=140)
        second = spatial_view.assign_cells(list(reversed(placements)), tolerance=140)
        self.assertEqual(first, second)


class TestBuildLayout(unittest.TestCase):
    """Backdrops become outlines spanning the cells of the anchors inside them."""

    def test_backdrop_spans_the_cells_of_the_anchors_it_contains(self):
        anchors = [_anchor('a', 0, 0), _anchor('b', 500, 0), _anchor('outside', 5000, 5000)]
        backdrops = [_backdrop('bd', -50, -50, 700, 200)]
        layout = spatial_view.build_layout(anchors, backdrops)

        top, left, bottom, right = layout['spans']['bd']
        anchor_cells = [layout['cells']['a'], layout['cells']['b']]
        self.assertEqual(top, min(row for row, _column in anchor_cells))
        self.assertEqual(left, min(column for _row, column in anchor_cells))
        self.assertEqual(bottom, max(row for row, _column in anchor_cells))
        self.assertEqual(right, max(column for _row, column in anchor_cells))

    def test_anchor_outside_the_backdrop_is_not_spanned(self):
        anchors = [_anchor('inside', 10, 10), _anchor('outside', 9000, 10)]
        backdrops = [_backdrop('bd', 0, 0, 100, 100)]
        layout = spatial_view.build_layout(anchors, backdrops)
        top, left, bottom, right = layout['spans']['bd']
        outside_row, outside_column = layout['cells']['outside']
        self.assertFalse(top <= outside_row <= bottom and left <= outside_column <= right)

    def test_backdrop_with_no_anchors_takes_a_cell_of_its_own(self):
        anchors = [_anchor('a', 0, 0)]
        backdrops = [_backdrop('empty', 4000, 4000, 200, 200)]
        layout = spatial_view.build_layout(anchors, backdrops)

        self.assertIn('empty', layout['cells'])
        row, column = layout['cells']['empty']
        self.assertEqual(layout['spans']['empty'], (row, column, row, column))
        self.assertNotEqual(layout['cells']['a'], layout['cells']['empty'])

    def test_anchors_only_layout_has_no_spans(self):
        layout = spatial_view.build_layout([_anchor('a', 0, 0)], [])
        self.assertEqual(layout['spans'], {})
        self.assertEqual((layout['rows'], layout['columns']), (1, 1))

    def test_rows_and_columns_report_the_grid_extent(self):
        anchors = [_anchor('a', 0, 0), _anchor('b', 1000, 1000)]
        layout = spatial_view.build_layout(anchors, [], tolerance=140)
        self.assertEqual(layout['rows'], 2)
        self.assertEqual(layout['columns'], 2)

    def test_empty_layout_is_empty(self):
        layout = spatial_view.build_layout([], [])
        self.assertEqual(layout['cells'], {})
        self.assertEqual((layout['rows'], layout['columns']), (0, 0))


class TestRankEntries(unittest.TestCase):
    """The cards are filtered by exactly the search the pickers use."""

    def setUp(self):
        self.entries = [
            _entry(0, 'Anchors/BG_Plate'),
            _entry(1, 'Anchors/CG_Env'),
            _entry(2, 'Anchors/bg_matte'),
            _entry(3, 'Backdrops/plates'),
        ]

    def test_empty_query_matches_everything(self):
        self.assertEqual(
            sorted(spatial_view.rank_entries('', self.entries)), [0, 1, 2, 3])

    def test_anchored_fuzzy_is_the_default(self):
        # "bgp" matches BG_Plate from its first letter, but not CG_Env.
        matched = spatial_view.rank_entries('bgp', self.entries)
        self.assertIn(0, matched)
        self.assertNotIn(1, matched)

    def test_non_matching_entries_are_excluded(self):
        self.assertEqual(spatial_view.rank_entries('zzzz', self.entries), [])

    def test_one_leading_space_switches_to_non_anchored_by_default(self):
        # "matte" is not at the start of "bg_matte [Anchors]", so it needs the
        # one-space (non-anchored) mode to match.
        self.assertNotIn(2, spatial_view.rank_entries('matte', self.entries))
        self.assertIn(2, spatial_view.rank_entries(' matte', self.entries))

    def test_space_mode_order_from_preferences_is_honoured(self):
        # With non-anchored fuzzy mapped to no leading space, the same query
        # matches without the user typing a space.
        reordered = [
            'non_anchored_fuzzy',
            'anchored_fuzzy',
            'consecutive',
        ]
        matched = spatial_view.rank_entries(
            'matte', self.entries, space_mode_order=reordered)
        self.assertIn(2, matched)

    def test_weights_float_the_most_used_entry_first(self):
        weights = {'Anchors/CG_Env': 1.0}
        matched = spatial_view.rank_entries(
            '', self.entries, weight_fn=lambda menupath: weights.get(menupath, 0.0))
        self.assertEqual(matched[0], 1)

    def test_consecutive_matches_rank_above_merely_fuzzy_ones(self):
        entries = [
            _entry(0, 'Anchors/bxgx'),   # fuzzy: b, g in order but not adjacent
            _entry(1, 'Anchors/bg_key'),  # consecutive: literally starts "bg"
        ]
        self.assertEqual(spatial_view.rank_entries('bg', entries), [1, 0])


class TestCellInDirection(unittest.TestCase):
    """Arrow keys step across the map, not down a list."""

    def setUp(self):
        #  a b
        #  c d
        self.cells = {'a': (0, 0), 'b': (0, 1), 'c': (1, 0), 'd': (1, 1)}
        self.all_keys = ['a', 'b', 'c', 'd']

    def test_right_moves_to_the_card_on_the_right(self):
        self.assertEqual(
            spatial_view.cell_in_direction(self.cells, 'a', 'right', self.all_keys), 'b')

    def test_down_moves_to_the_card_below(self):
        self.assertEqual(
            spatial_view.cell_in_direction(self.cells, 'a', 'down', self.all_keys), 'c')

    def test_left_and_up_move_back(self):
        self.assertEqual(
            spatial_view.cell_in_direction(self.cells, 'd', 'left', self.all_keys), 'c')
        self.assertEqual(
            spatial_view.cell_in_direction(self.cells, 'd', 'up', self.all_keys), 'b')

    def test_no_card_in_that_direction_returns_none(self):
        self.assertIsNone(
            spatial_view.cell_in_direction(self.cells, 'a', 'up', self.all_keys))

    def test_filtered_out_cards_are_skipped(self):
        # 'b' is greyed out by the search, so Right lands on the next match.
        cells = {'a': (0, 0), 'b': (0, 1), 'far': (0, 5)}
        self.assertEqual(
            spatial_view.cell_in_direction(cells, 'a', 'right', ['a', 'far']), 'far')

    def test_same_row_is_preferred_over_a_nearer_diagonal(self):
        cells = {'a': (1, 0), 'same_row': (1, 2), 'diagonal': (0, 1)}
        self.assertEqual(
            spatial_view.cell_in_direction(cells, 'a', 'right', ['same_row', 'diagonal']),
            'same_row')

    def test_unknown_direction_returns_none(self):
        self.assertIsNone(
            spatial_view.cell_in_direction(self.cells, 'a', 'sideways', self.all_keys))


def _make_anchor_node(name, xpos, ypos, tile_color=0xAABBCCFF):
    return StubNode(name=name, node_class='NoOp', xpos=xpos, ypos=ypos,
                    knobs_dict={'tile_color': StubKnob(tile_color)})


def _make_backdrop_node(name, xpos, ypos, width, height, label='backdrop'):
    return StubNode(name=name, node_class='BackdropNode', xpos=xpos, ypos=ypos,
                    knobs_dict={
                        'tile_color': StubKnob(0x223344FF),
                        'label': StubKnob(label),
                        'bdwidth': StubKnob(width),
                        'bdheight': StubKnob(height),
                    })


class TestCollectEntries(unittest.TestCase):
    """Each mode lists what its picker lists, plus backdrops for context."""

    def setUp(self):
        self.anchor_node = _make_anchor_node('Anchor_BG', 0, 0)
        self.backdrop_node = _make_backdrop_node('BackdropNode1', -50, -50, 400, 400)
        self.hit_group = MagicMock()

    def _plugin_returning(self, items):
        plugin = MagicMock()
        plugin.get_items.return_value = items
        return plugin

    def test_navigate_mode_marks_backdrops_selectable(self):
        items = [
            {'menuobj': self.anchor_node, 'menupath': 'Anchors/BG'},
            {'menuobj': self.backdrop_node, 'menupath': 'Backdrops/plates'},
        ]
        with patch.object(spatial_view, '_plugin_for_mode',
                          return_value=self._plugin_returning(items)):
            _plugin, entries = spatial_view.collect_entries(
                spatial_view.MODE_NAVIGATE, self.hit_group)

        self.assertEqual([entry['kind'] for entry in entries], ['anchor', 'backdrop'])
        self.assertTrue(all(entry['selectable'] for entry in entries))

    def test_create_link_mode_adds_backdrops_as_unselectable_context(self):
        items = [{'menuobj': self.anchor_node, 'menupath': 'Anchors/BG'}]
        nuke_stub = sys.modules['nuke']
        with patch.object(spatial_view, '_plugin_for_mode',
                          return_value=self._plugin_returning(items)), \
                patch.object(nuke_stub, 'allNodes', return_value=[self.backdrop_node]):
            _plugin, entries = spatial_view.collect_entries(
                spatial_view.MODE_CREATE_LINK, self.hit_group)

        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0]['selectable'])
        self.assertEqual(entries[1]['kind'], 'backdrop')
        self.assertFalse(entries[1]['selectable'])
        self.assertEqual(entries[1]['menupath'], 'Backdrops/backdrop')

    def test_create_link_mode_skips_unlabelled_backdrops(self):
        unlabelled = _make_backdrop_node('BackdropNode2', 0, 0, 100, 100, label='   ')
        items = [{'menuobj': self.anchor_node, 'menupath': 'Anchors/BG'}]
        nuke_stub = sys.modules['nuke']
        with patch.object(spatial_view, '_plugin_for_mode',
                          return_value=self._plugin_returning(items)), \
                patch.object(nuke_stub, 'allNodes', return_value=[unlabelled]):
            _plugin, entries = spatial_view.collect_entries(
                spatial_view.MODE_CREATE_LINK, self.hit_group)

        self.assertEqual(len(entries), 1)

    def test_entry_keys_are_unique(self):
        items = [
            {'menuobj': self.anchor_node, 'menupath': 'Anchors/BG'},
            {'menuobj': self.backdrop_node, 'menupath': 'Backdrops/plates'},
        ]
        with patch.object(spatial_view, '_plugin_for_mode',
                          return_value=self._plugin_returning(items)):
            _plugin, entries = spatial_view.collect_entries(
                spatial_view.MODE_NAVIGATE, self.hit_group)
        keys = [entry['key'] for entry in entries]
        self.assertEqual(len(set(keys)), len(keys))


class TestLayoutForEntries(unittest.TestCase):
    """Geometry is read off the nodes the entries stand for."""

    def test_backdrop_entry_spans_the_anchor_inside_it(self):
        anchor_entry = _entry(0, 'Anchors/BG', node=_make_anchor_node('Anchor_BG', 100, 100))
        backdrop_entry = _entry(
            1, 'Backdrops/plates', kind='backdrop',
            node=_make_backdrop_node('BackdropNode1', 0, 0, 500, 500))

        layout = spatial_view.layout_for_entries([anchor_entry, backdrop_entry])
        top, left, bottom, right = layout['spans'][1]
        self.assertEqual((top, left, bottom, right), (0, 0, 0, 0))
        self.assertEqual(layout['cells'][0], (0, 0))


class TestDisplayName(unittest.TestCase):
    """Cards are named exactly as the picker rows are."""

    def test_display_name_is_the_menupath_leaf(self):
        self.assertEqual(spatial_view.display_name_for(_entry(0, 'Anchors/BG_Plate')), 'BG_Plate')
        self.assertEqual(
            spatial_view.display_name_for(_entry(1, 'Backdrops/plates fg')), 'plates fg')


class TestTextColor(unittest.TestCase):
    """Card text stays legible on any tile colour."""

    def test_light_tile_gets_dark_text(self):
        self.assertEqual(spatial_view.text_color_for(0xFFFFFFFF), '#111111')

    def test_dark_tile_gets_light_text(self):
        self.assertEqual(spatial_view.text_color_for(0x101010FF), '#eeeeee')


class TestNodeColor(unittest.TestCase):
    """An uncoloured node still gets a readable card."""

    def test_tile_colour_is_used_when_set(self):
        node = _make_anchor_node('Anchor_BG', 0, 0, tile_color=0x123456FF)
        self.assertEqual(spatial_view.node_color(node), 0x123456FF)

    def test_uncoloured_backdrop_falls_back_to_the_default(self):
        node = _make_backdrop_node('BackdropNode1', 0, 0, 100, 100)
        node['tile_color'].setValue(0)
        self.assertEqual(spatial_view.node_color(node), spatial_view._DEFAULT_BACKDROP_COLOR)

    def test_uncoloured_anchor_falls_back_to_the_dag_colour(self):
        node = _make_anchor_node('Anchor_BG', 0, 0, tile_color=0)
        with patch('anchor.find_anchor_color', return_value=0x998877FF):
            self.assertEqual(spatial_view.node_color(node), 0x998877FF)


class TestOpenView(unittest.TestCase):
    """The command is a silent no-op whenever there is nothing to show."""

    def tearDown(self):
        spatial_view._active_view = None

    def test_disabled_plugin_opens_nothing(self):
        with patch.object(spatial_view.prefs, 'plugin_enabled', False), \
                patch.object(spatial_view, 'collect_entries') as collect:
            self.assertIsNone(spatial_view.open_view(spatial_view.MODE_NAVIGATE))
        collect.assert_not_called()

    def test_no_selectable_entries_opens_nothing(self):
        context_only = [_entry(0, 'Backdrops/plates', kind='backdrop', selectable=False)]
        with patch.object(spatial_view.prefs, 'plugin_enabled', True), \
                patch.object(spatial_view, 'collect_entries',
                             return_value=(MagicMock(), context_only)), \
                patch.object(spatial_view, 'SpatialView') as view_class:
            self.assertIsNone(spatial_view.open_view(
                spatial_view.MODE_NAVIGATE, hit_group=MagicMock()))
        view_class.assert_not_called()

    def test_view_is_built_shown_and_kept_referenced(self):
        entries = [_entry(0, 'Anchors/BG')]
        with patch.object(spatial_view.prefs, 'plugin_enabled', True), \
                patch.object(spatial_view, 'collect_entries',
                             return_value=(MagicMock(), entries)), \
                patch.object(spatial_view, 'host_main_window', return_value=None), \
                patch.object(spatial_view, 'SpatialView') as view_class:
            view = spatial_view.open_view(spatial_view.MODE_NAVIGATE, hit_group=MagicMock())

        self.assertIs(view, view_class.return_value)
        self.assertIs(spatial_view._active_view, view)
        view.under_cursor.assert_called_once_with()
        view.show.assert_called_once_with()

    def test_reopening_closes_the_previous_view(self):
        previous_view = MagicMock()
        spatial_view._active_view = previous_view
        entries = [_entry(0, 'Anchors/BG')]
        with patch.object(spatial_view.prefs, 'plugin_enabled', True), \
                patch.object(spatial_view, 'collect_entries',
                             return_value=(MagicMock(), entries)), \
                patch.object(spatial_view, 'host_main_window', return_value=None), \
                patch.object(spatial_view, 'SpatialView'):
            spatial_view.open_view(spatial_view.MODE_NAVIGATE, hit_group=MagicMock())

        previous_view.close.assert_called_once_with()
        previous_view.deleteLater.assert_called_once_with()

    def test_navigate_and_create_link_entry_points_pick_their_modes(self):
        with patch.object(spatial_view, 'open_view') as open_view:
            spatial_view.open_navigate_view()
            spatial_view.open_create_link_view()
        self.assertEqual(
            [call.args[0] for call in open_view.call_args_list],
            [spatial_view.MODE_NAVIGATE, spatial_view.MODE_CREATE_LINK])


class TestLeaderBinding(unittest.TestCase):
    """The spatial view is reachable from the leader key as well as Alt+S."""

    def test_binding_table_carries_the_spatial_view_entry(self):
        from constants import LEADER_BINDINGS
        self.assertIn(('S', 'Spatial View', 1, 1, 'single'), LEADER_BINDINGS)

    def test_leader_dispatches_s_to_the_navigate_view(self):
        prefs_stub = types.ModuleType('prefs')
        prefs_stub.keyboard_layout = 'qwerty'
        prefs_stub.plugin_enabled = True
        original_prefs = sys.modules.get('prefs')
        sys.modules['prefs'] = prefs_stub
        try:
            import leader
            self.assertIs(leader._DISPATCH_BY_LETTER['S'], leader._dispatch_spatial_view)
            with patch.object(spatial_view, 'open_navigate_view') as open_navigate_view:
                leader._dispatch_spatial_view()
            open_navigate_view.assert_called_once_with()
        finally:
            if original_prefs is not None:
                sys.modules['prefs'] = original_prefs
            else:
                sys.modules.pop('prefs', None)
            sys.modules.pop('leader', None)


if __name__ == '__main__':
    unittest.main()
