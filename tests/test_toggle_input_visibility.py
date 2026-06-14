"""Tests for toggle_input_visibility() — the wrapper around Nuke's
Edit > Node > Input On/Off (Alt+H).

Hiding a wired Dot's input is the deliberate "manual link" gesture that converts
the Dot into a Local/Link dot in place.  This replaces the old behaviour where
the conversion was a side effect of copy_anchors() stamping the original, which
caused issue #56 (copying alone mutated nodes in the DAG).
"""

import unittest
from unittest.mock import patch

from constants import (
    ANCHOR_DEFAULT_COLOR,
    DOT_TYPE_KNOB_NAME,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    LOCAL_DOT_COLOR,
    TAB_NAME,
)
from tests.stubs import StubKnob, StubNode


def _make_knob(value='', knob_name=''):
    return StubKnob(value=value, knob_name=knob_name)


def _make_dot(name='Dot1', hide_input=False, node_class='Dot'):
    """A Dot with the knobs the wrapper and stamping helpers touch."""
    return StubNode(name=name, node_class=node_class, knobs_dict={
        'hide_input': _make_knob(hide_input, knob_name='hide_input'),
        'label': _make_knob(''),
        'tile_color': _make_knob(0),
        'note_font_size': _make_knob(0),
        KNOB_NAME: _make_knob('', knob_name=KNOB_NAME),
    })


def _patch_common(mock_nuke, selected, plugin_enabled=True):
    mock_nuke.selectedNodes.return_value = selected
    mock_nuke.root.return_value.name.return_value = 'sourceScript.nk'


class TestToggleInputVisibility(unittest.TestCase):

    def test_hiding_wired_plain_backed_dot_stamps_local(self):
        """Hiding a Dot wired to a plain node stamps it as a Local dot in place."""
        dot = _make_dot(hide_input=False)
        plain = StubNode(name='Merge1', node_class='Merge',
                         knobs_dict={'label': _make_knob('my merge')})
        dot._input = plain

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.add_input_knob') as mock_add_input_knob:

            mock_prefs.plugin_enabled = True
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        # Built-in effect: input is now hidden.
        self.assertTrue(dot['hide_input'].value())
        # Stamped as a Local dot.
        mock_setup.assert_called_once_with(plain, dot)
        mock_add_input_knob.assert_called_once_with(dot, dot_type='local')
        self.assertEqual(dot['label'].getValue(), 'Local: my merge')
        self.assertEqual(dot['tile_color'].getValue(), LOCAL_DOT_COLOR)
        self.assertEqual(dot[KNOB_NAME].getText(), 'sourceScript.Merge1')

    def test_hiding_wired_anchor_backed_dot_stamps_link(self):
        """Hiding a Dot wired to an anchor stamps it as a Link dot in place."""
        dot = _make_dot(hide_input=False)
        anchor = StubNode(name='Anchor_Foo', node_class='NoOp',
                          knobs_dict={'label': _make_knob('Foo'), 'tile_color': _make_knob(0)})
        dot._input = anchor

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', side_effect=lambda n: n is anchor), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.add_input_knob') as mock_add_input_knob:

            mock_prefs.plugin_enabled = True
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        self.assertTrue(dot['hide_input'].value())
        mock_setup.assert_called_once_with(anchor, dot)
        mock_add_input_knob.assert_called_once_with(dot, dot_type='link')
        self.assertEqual(dot['tile_color'].getValue(), ANCHOR_DEFAULT_COLOR)

    def test_hiding_unwired_dot_only_toggles(self):
        """Hiding a Dot with no input toggles hide_input but does not stamp."""
        dot = _make_dot(hide_input=False)
        dot._input = None

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.add_input_knob') as mock_add_input_knob:

            mock_prefs.plugin_enabled = True
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        self.assertTrue(dot['hide_input'].value())
        mock_setup.assert_not_called()
        mock_add_input_knob.assert_not_called()
        self.assertNotIn(DOT_TYPE_KNOB_NAME, dot.knobs())

    def test_already_marked_dot_is_not_restamped(self):
        """Hiding an already-marked (link) Dot must not re-stamp it."""
        dot = _make_dot(hide_input=False)
        plain = StubNode(name='Merge1', node_class='Merge',
                         knobs_dict={'label': _make_knob('m')})
        dot._input = plain

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=True), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.add_input_knob') as mock_add_input_knob:

            mock_prefs.plugin_enabled = True
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        self.assertTrue(dot['hide_input'].value())
        mock_setup.assert_not_called()
        mock_add_input_knob.assert_not_called()

    def test_plugin_disabled_toggles_but_does_not_stamp(self):
        """When the plugin is disabled the built-in toggle still runs, but no stamping."""
        dot = _make_dot(hide_input=False)
        plain = StubNode(name='Merge1', node_class='Merge',
                         knobs_dict={'label': _make_knob('m')})
        dot._input = plain

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.add_input_knob') as mock_add_input_knob:

            mock_prefs.plugin_enabled = False
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        self.assertTrue(dot['hide_input'].value())
        mock_setup.assert_not_called()
        mock_add_input_knob.assert_not_called()

    def test_unhiding_unmarked_dot_does_not_stamp(self):
        """Toggling a currently-hidden, unmarked Dot back to visible must not stamp it."""
        dot = _make_dot(hide_input=True)
        plain = StubNode(name='Merge1', node_class='Merge',
                         knobs_dict={'label': _make_knob('m')})
        dot._input = plain

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.add_input_knob') as mock_add_input_knob:

            mock_prefs.plugin_enabled = True
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        # hide_input toggled True -> False; no stamping because it was just revealed.
        self.assertFalse(dot['hide_input'].value())
        mock_setup.assert_not_called()
        mock_add_input_knob.assert_not_called()

    def test_unhiding_marked_dot_clears_link_state(self):
        """Revealing the input of a Local/Link dot reverts it to a plain node."""
        dot = StubNode(name='Dot1', node_class='Dot', knobs_dict={
            KNOB_NAME: _make_knob('sourceScript.Merge1', knob_name=KNOB_NAME),
            DOT_TYPE_KNOB_NAME: _make_knob('local', knob_name=DOT_TYPE_KNOB_NAME),
            TAB_NAME: _make_knob('', knob_name=TAB_NAME),
            LINK_RECONNECT_KNOB_NAME: _make_knob('', knob_name=LINK_RECONNECT_KNOB_NAME),
            'label': _make_knob('Local: my merge'),
            'tile_color': _make_knob(LOCAL_DOT_COLOR),
            'hide_input': _make_knob(True, knob_name='hide_input'),
            'note_font_size': _make_knob(0),
        })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False):

            mock_prefs.plugin_enabled = True
            _patch_common(mock_nuke, [dot])

            from anchors import toggle_input_visibility
            toggle_input_visibility()

        self.assertFalse(dot['hide_input'].value())
        for knob_name in (KNOB_NAME, DOT_TYPE_KNOB_NAME, TAB_NAME, LINK_RECONNECT_KNOB_NAME):
            self.assertNotIn(knob_name, dot.knobs())
        self.assertEqual(dot['label'].getValue(), '')
        self.assertEqual(dot['tile_color'].getValue(), 0)


if __name__ == '__main__':
    unittest.main()
