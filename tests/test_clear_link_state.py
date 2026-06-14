"""Tests for clear_link_state() — reverting a Local/Link dot back to a plain node.

This is the inverse of the Input On/Off (Alt+H) conversion: it strips the custom
knobs, clears the stamped label/colour, and reveals the input again.
"""

import unittest
from unittest.mock import patch

from constants import (
    DOT_ANCHOR_MIN_FONT_SIZE,
    DOT_LINK_LABEL_FONT_SIZE,
    DOT_TYPE_KNOB_NAME,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    LOCAL_DOT_COLOR,
    TAB_NAME,
)
from tests.stubs import StubKnob, StubNode

# A plain Dot's font size sits below the anchor threshold; the link conversion
# bumps it up to DOT_LINK_LABEL_FONT_SIZE (== DOT_ANCHOR_MIN_FONT_SIZE).
PLAIN_DOT_FONT_DEFAULT = DOT_ANCHOR_MIN_FONT_SIZE - 22


def _make_knob(value='', knob_name='', default=None):
    return StubKnob(value=value, knob_name=knob_name, default=default)


def _make_local_dot():
    return StubNode(name='Dot1', node_class='Dot', knobs_dict={
        KNOB_NAME: _make_knob('sourceScript.Merge1', knob_name=KNOB_NAME),
        DOT_TYPE_KNOB_NAME: _make_knob('local', knob_name=DOT_TYPE_KNOB_NAME),
        TAB_NAME: _make_knob('', knob_name=TAB_NAME),
        LINK_RECONNECT_KNOB_NAME: _make_knob('', knob_name=LINK_RECONNECT_KNOB_NAME),
        'label': _make_knob('Local: my merge'),
        'tile_color': _make_knob(LOCAL_DOT_COLOR),
        'hide_input': _make_knob(True, knob_name='hide_input'),
        'note_font_size': _make_knob(DOT_LINK_LABEL_FONT_SIZE,
                                     knob_name='note_font_size',
                                     default=PLAIN_DOT_FONT_DEFAULT),
    })


class TestClearLinkState(unittest.TestCase):

    def test_clear_reverts_local_dot_to_plain(self):
        dot = _make_local_dot()

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [dot]

            from anchors import clear_link_state
            clear_link_state()

        for knob_name in (KNOB_NAME, DOT_TYPE_KNOB_NAME, TAB_NAME, LINK_RECONNECT_KNOB_NAME):
            self.assertNotIn(knob_name, dot.knobs())
        self.assertEqual(dot['label'].getValue(), '')
        self.assertEqual(dot['tile_color'].getValue(), 0)
        self.assertFalse(dot['hide_input'].value())

    def test_clear_leaves_anchor_untouched(self):
        anchor = StubNode(name='Anchor_Foo', node_class='NoOp', knobs_dict={
            KNOB_NAME: _make_knob('Anchor_Foo', knob_name=KNOB_NAME),
            'label': _make_knob('Foo'),
            'tile_color': _make_knob(123),
            'hide_input': _make_knob(False),
        })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=True):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [anchor]

            from anchors import clear_link_state
            clear_link_state()

        self.assertIn(KNOB_NAME, anchor.knobs())
        self.assertEqual(anchor['label'].getValue(), 'Foo')
        self.assertEqual(anchor['tile_color'].getValue(), 123)

    def test_clear_leaves_unmarked_node_untouched(self):
        plain = StubNode(name='Dot1', node_class='Dot', knobs_dict={
            'label': _make_knob('just a note'),
            'tile_color': _make_knob(456),
            'hide_input': _make_knob(False),
        })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [plain]

            from anchors import clear_link_state
            clear_link_state()

        self.assertEqual(plain['label'].getValue(), 'just a note')
        self.assertEqual(plain['tile_color'].getValue(), 456)

    def test_clear_resets_note_font_size_to_default(self):
        """Clearing must drop the link-label font bump back to the knob default."""
        dot = _make_local_dot()

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [dot]

            from anchors import clear_link_state
            clear_link_state()

        self.assertEqual(dot['note_font_size'].value(), PLAIN_DOT_FONT_DEFAULT)

    def test_cleared_dot_is_not_an_anchor_after_relabel(self):
        """Regression: a cleared dot must fall below the anchor font gate, so
        re-labelling it does not make is_anchor() (the real predicate) return True."""
        from link import is_anchor as real_is_anchor

        dot = _make_local_dot()

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [dot]

            from anchors import clear_link_state
            clear_link_state()

        # The user re-labels the now-plain dot.
        dot['label'].setValue('my note')
        self.assertFalse(
            real_is_anchor(dot),
            "A cleared, re-labelled dot must remain a plain note, not an anchor",
        )

    def test_clear_noop_when_plugin_disabled(self):
        dot = _make_local_dot()

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False):

            mock_prefs.plugin_enabled = False
            mock_nuke.selectedNodes.return_value = [dot]

            from anchors import clear_link_state
            clear_link_state()

        # Nothing stripped.
        self.assertIn(KNOB_NAME, dot.knobs())
        self.assertEqual(dot['label'].getValue(), 'Local: my merge')


if __name__ == '__main__':
    unittest.main()
