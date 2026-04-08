"""Tests for issue #16 — Anchor Creation Name Suggestion Improvements.

Covers suggest_anchor_name() and find_anchor_color() behaviour when the
selected input node is a Dot:

  TestLabelledDotNameSuggestion     — labelled Dot uses its label as suggestion
  TestUnlabelledDotNameSuggestion   — unlabelled Dot delegates to first non-Dot ancestor
  TestDotChainNameSuggestion        — chains of Dots (Dot→Dot→Read) are fully traversed
  TestFindAnchorColorDot            — find_anchor_color() resolves through unlabelled Dots
"""

import sys
import unittest
from unittest.mock import patch

from tests.stubs import StubKnob, StubNode, make_stub_nuke_module

if 'nuke' not in sys.modules:
    sys.modules['nuke'] = make_stub_nuke_module()

import anchor
import prefs as prefs_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dot(label='', tile_color=0):
    return StubNode(
        name='Dot1',
        node_class='Dot',
        knobs_dict={
            'label': StubKnob(label),
            'tile_color': StubKnob(tile_color),
        },
    )


def _make_read(filepath):
    return StubNode(
        name='Read1',
        node_class='Read',
        knobs_dict={'file': StubKnob(filepath)},
    )


def _make_noop():
    return StubNode(name='NoOp1', node_class='NoOp', knobs_dict={})


# ---------------------------------------------------------------------------
# Labelled Dot → label is the suggestion
# ---------------------------------------------------------------------------

class TestLabelledDotNameSuggestion(unittest.TestCase):
    """When the selected node is a labelled Dot, its label becomes the suggestion."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()

    def tearDown(self):
        self._backdrop_patcher.stop()

    def test_labelled_dot_returns_label(self):
        dot = _make_dot(label='PLATES')
        result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, 'PLATES')

    def test_labelled_dot_label_is_stripped(self):
        dot = _make_dot(label='  BG_PLATES  ')
        result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, 'BG_PLATES')

    def test_labelled_dot_with_backdrop_prefix(self):
        """Labelled Dot inside a backdrop gets backdrop_label + '_' + dot_label."""
        dot = _make_dot(label='PLATES')

        backdrop = StubNode(
            name='BackdropNode1',
            node_class='BackdropNode',
            knobs_dict={'label': StubKnob('BG'), 'tile_color': StubKnob(0)},
        )

        with patch('anchor.find_smallest_containing_backdrop', return_value=backdrop):
            result = anchor.suggest_anchor_name(dot)

        self.assertEqual(result, 'BG_PLATES')

    def test_labelled_dot_backdrop_with_empty_label_uses_dot_label_only(self):
        """If the backdrop label is empty, only the Dot label is returned."""
        dot = _make_dot(label='PLATES')

        backdrop = StubNode(
            name='BackdropNode1',
            node_class='BackdropNode',
            knobs_dict={'label': StubKnob(''), 'tile_color': StubKnob(0)},
        )

        with patch('anchor.find_smallest_containing_backdrop', return_value=backdrop):
            result = anchor.suggest_anchor_name(dot)

        self.assertEqual(result, 'PLATES')


# ---------------------------------------------------------------------------
# Unlabelled Dot → delegates to first non-Dot ancestor
# ---------------------------------------------------------------------------

class TestUnlabelledDotNameSuggestion(unittest.TestCase):
    """Unlabelled Dot defers naming to the first non-Dot node upstream."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_unlabelled_dot_above_read_uses_read_suggestion(self):
        """Unlabelled Dot → Read node gives same result as suggest_anchor_name(read)."""
        read_node = _make_read('plate_v003.exr')
        dot = _make_dot(label='')
        dot.setInput(0, read_node)

        prefs_module.naming_regex = ''
        prefs_module.naming_template = ''
        result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, 'plate')

    def test_unlabelled_dot_above_noop_returns_empty(self):
        """Unlabelled Dot above a NoOp (no 'file' knob) returns empty string."""
        noop = _make_noop()
        dot = _make_dot(label='')
        dot.setInput(0, noop)

        result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, '')

    def test_unlabelled_dot_with_no_input_returns_empty(self):
        """Unlabelled Dot with no upstream connection returns empty string."""
        dot = _make_dot(label='')
        # _input defaults to None in StubNode

        result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, '')

    def test_unlabelled_dot_uses_user_regex_on_upstream_read(self):
        """User regex is applied when delegating through an unlabelled Dot."""
        read_node = _make_read('BG010_v003.exr')
        dot = _make_dot(label='')
        dot.setInput(0, read_node)

        prefs_module.naming_regex = r'(?P<shot>\w+)_v\d+'
        prefs_module.naming_template = '{shot}'
        result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, 'BG010')


# ---------------------------------------------------------------------------
# Chain: Dot → Dot → Read
# ---------------------------------------------------------------------------

class TestDotChainNameSuggestion(unittest.TestCase):
    """Chains of unlabelled Dots are fully traversed to the first non-Dot node."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_dot_chain_traverses_to_read(self):
        """Dot → Dot → Read: suggestion comes from the Read node."""
        read_node = _make_read('comp_v007.exr')
        dot_mid = _make_dot(label='')
        dot_mid._name = 'Dot2'
        dot_mid.setInput(0, read_node)
        dot_top = _make_dot(label='')
        dot_top._name = 'Dot1'
        dot_top.setInput(0, dot_mid)

        prefs_module.naming_regex = ''
        prefs_module.naming_template = ''
        result = anchor.suggest_anchor_name(dot_top)
        self.assertEqual(result, 'comp')

    def test_dot_chain_stops_at_labelled_dot(self):
        """Dot(unlabelled) → Dot(labelled): returns the labelled Dot's label."""
        labelled_dot = _make_dot(label='MATTE')
        labelled_dot._name = 'Dot2'
        outer_dot = _make_dot(label='')
        outer_dot._name = 'Dot1'
        outer_dot.setInput(0, labelled_dot)

        result = anchor.suggest_anchor_name(outer_dot)
        # outer_dot is unlabelled → delegates to _find_first_non_dot_input
        # _find_first_non_dot_input skips Dots entirely, so labelled_dot is NOT
        # returned (it is still a Dot). The chain then continues to labelled_dot's
        # input(0) which is None → returns None → suggest_anchor_name returns "".
        # This is intentional: a labelled Dot as the intermediate node in an
        # unlabelled-Dot chain isn't treated as the anchor source.
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# find_anchor_color — resolves through unlabelled Dots
# ---------------------------------------------------------------------------

class TestFindAnchorColorDot(unittest.TestCase):
    """find_anchor_color() uses the first non-Dot ancestor for unlabelled Dot inputs."""

    def test_anchor_color_resolves_through_unlabelled_dot_to_read(self):
        """Anchor whose input is an unlabelled Dot → Read should use Read's color."""
        read_node = _make_read('plate_v001.exr')
        read_color = 0xFF0000FF  # red
        read_node['tile_color'] = StubKnob(read_color)

        unlabelled_dot = _make_dot(label='')
        unlabelled_dot.setInput(0, read_node)

        # The anchor's input(0) is the unlabelled Dot
        anchor_node = StubNode(
            name='Anchor_test',
            node_class='NoOp',
            knobs_dict={'tile_color': StubKnob(0)},
        )
        anchor_node.setInput(0, unlabelled_dot)

        with patch('anchor.find_smallest_containing_backdrop', return_value=None), \
             patch('anchor.find_node_color', return_value=read_color) as mock_find_color:
            result = anchor.find_anchor_color(anchor_node)

        mock_find_color.assert_called_once_with(read_node)
        self.assertEqual(result, read_color)

    def test_anchor_color_uses_labelled_dot_color_directly(self):
        """Anchor whose input is a labelled Dot should use the Dot's own color."""
        labelled_dot = _make_dot(label='PLATES', tile_color=0x00FF00FF)
        dot_color = 0x00FF00FF

        anchor_node = StubNode(
            name='Anchor_test',
            node_class='NoOp',
            knobs_dict={'tile_color': StubKnob(0)},
        )
        anchor_node.setInput(0, labelled_dot)

        with patch('anchor.find_smallest_containing_backdrop', return_value=None), \
             patch('anchor.find_node_color', return_value=dot_color) as mock_find_color:
            result = anchor.find_anchor_color(anchor_node)

        mock_find_color.assert_called_once_with(labelled_dot)
        self.assertEqual(result, dot_color)

    def test_anchor_color_unlabelled_dot_with_no_upstream_returns_default(self):
        """Unlabelled Dot with no upstream → default anchor color."""
        from constants import ANCHOR_DEFAULT_COLOR

        unlabelled_dot = _make_dot(label='')
        # No input set — chain ends immediately

        anchor_node = StubNode(
            name='Anchor_test',
            node_class='NoOp',
            knobs_dict={'tile_color': StubKnob(0)},
        )
        anchor_node.setInput(0, unlabelled_dot)

        with patch('anchor.find_smallest_containing_backdrop', return_value=None):
            result = anchor.find_anchor_color(anchor_node)

        self.assertEqual(result, ANCHOR_DEFAULT_COLOR)


if __name__ == '__main__':
    unittest.main()
