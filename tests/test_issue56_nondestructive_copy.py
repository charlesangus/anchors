"""Regression tests for issue #56 — copy_anchors() must be non-destructive.

Before the fix, copy_anchors() stamped the live selected nodes in the DAG before
nuke.nodeCopy(), so the act of copying changed a node's label/colour/knobs.  After
an undo this left nodes in an inconsistent state, and the next copy turned a dot
into a brown "Local: …" dot.  The stamps must reach only the clipboard; the live
originals must be left exactly as the user left them.

A faithful fake add_input_knob adds the same knobs the real one would (TAB,
KNOB_NAME, DOT_TYPE, reconnect), so the knobs added during stamping are genuinely
added and then genuinely removed on restore — proving no knob drift accumulates
across repeated copies, without depending on global stub state set by other tests.
"""

import unittest
from unittest.mock import patch

from constants import (
    DOT_TYPE_KNOB_NAME,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    LOCAL_DOT_COLOR,
    TAB_NAME,
)
from tests.stubs import StubKnob, StubNode


def _make_knob(value='', knob_name=''):
    return StubKnob(value=value, knob_name=knob_name)


class _IntKnob:
    """Mimics a Nuke integer knob (e.g. tile_color): getValue() returns a float,
    but setValue() rejects a float — it must be given an int."""

    def __init__(self, value, knob_name=''):
        self._value = value
        self._knob_name = knob_name

    def name(self):
        return self._knob_name

    def getValue(self):
        return float(self._value)

    def value(self):
        return self._value

    def setValue(self, new_value):
        if isinstance(new_value, float):
            raise TypeError("'float' object cannot be interpreted as an integer")
        self._value = new_value


def _fake_add_input_knob(node, dot_type=None):
    """Mirror link.add_input_knob: (re)add the custom knobs as real named stubs."""
    node._knobs[LINK_RECONNECT_KNOB_NAME] = StubKnob(knob_name=LINK_RECONNECT_KNOB_NAME)
    node._knobs[TAB_NAME] = StubKnob(knob_name=TAB_NAME)
    node._knobs[KNOB_NAME] = StubKnob(knob_name=KNOB_NAME)
    if dot_type is not None:
        node._knobs[DOT_TYPE_KNOB_NAME] = StubKnob(dot_type, knob_name=DOT_TYPE_KNOB_NAME)


def _make_local_dot():
    """A Dot that is already a Local-style link (has KNOB_NAME) wired to a plain node."""
    dot = StubNode(name='Dot1', node_class='Dot', knobs_dict={
        KNOB_NAME: _make_knob('Merge1', knob_name=KNOB_NAME),
        'label': _make_knob('Link: Foo'),
        'tile_color': _make_knob(0),
        'hide_input': _make_knob(True, knob_name='hide_input'),
        'note_font_size': _make_knob(0),
        'selected': _make_knob(False),
    })
    plain = StubNode(name='Merge1', node_class='Merge',
                     knobs_dict={'label': _make_knob('my merge')})
    dot._input = plain
    return dot, plain


def _snapshot(dot):
    """Capture the observable state of *dot* for before/after comparison."""
    return {
        'knob_names': set(dot.knobs()),
        'label': dot['label'].getValue(),
        'tile_color': dot['tile_color'].getValue(),
        'fqnn': dot[KNOB_NAME].getText() if KNOB_NAME in dot.knobs() else None,
    }


class TestIssue56NonDestructiveCopy(unittest.TestCase):

    def test_copy_does_not_mutate_original(self):
        """A single copy leaves the original byte-for-byte unchanged while the
        clipboard copy carries the Local stamp."""
        dot, plain = _make_local_dot()
        before = _snapshot(dot)
        captured = {}

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node'), \
             patch('anchors.add_input_knob', side_effect=_fake_add_input_knob):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [dot]
            mock_nuke.root.return_value.name.return_value = 'sourceScript.nk'
            mock_nuke.nodeCopy.side_effect = lambda *a, **k: captured.update(
                label=dot['label'].getValue(),
                tile_color=dot['tile_color'].getValue(),
                dot_type=(dot[DOT_TYPE_KNOB_NAME].getValue()
                          if DOT_TYPE_KNOB_NAME in dot.knobs() else None),
            )

            from anchors import copy_anchors
            copy_anchors()

        # Clipboard copy was stamped...
        self.assertEqual(captured['label'], 'Local: my merge')
        self.assertEqual(captured['tile_color'], LOCAL_DOT_COLOR)
        self.assertEqual(captured['dot_type'], 'local')
        # ...the live original is fully restored, including no leftover knobs.
        self.assertEqual(_snapshot(dot), before)
        self.assertNotIn(TAB_NAME, dot.knobs())
        self.assertNotIn(DOT_TYPE_KNOB_NAME, dot.knobs())

    def test_repeated_copy_never_drifts(self):
        """Issue #56 scenario proxy: copying the same node many times must never
        accumulate state — the dot never becomes a persisted brown 'Local:' dot."""
        dot, plain = _make_local_dot()
        before = _snapshot(dot)

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node'), \
             patch('anchors.add_input_knob', side_effect=_fake_add_input_knob):

            mock_prefs.plugin_enabled = True
            mock_nuke.selectedNodes.return_value = [dot]
            mock_nuke.root.return_value.name.return_value = 'sourceScript.nk'

            from anchors import copy_anchors
            for _ in range(5):
                copy_anchors()
                self.assertEqual(
                    _snapshot(dot), before,
                    "Repeated copy must not mutate the original (issue #56)",
                )
                self.assertNotEqual(dot['tile_color'].getValue(), LOCAL_DOT_COLOR,
                                    "Original must never persist as a brown Local dot")


class TestRestoreIntegerKnob(unittest.TestCase):
    """Issue #56 follow-up: integer knobs (tile_color) return a float from
    getValue() but require an int on setValue(); restore must cast."""

    def test_restore_casts_float_to_int_for_integer_knobs(self):
        from anchors import _snapshot_node_state, _restore_node_state

        node = StubNode(name='Dot1', node_class='Dot', knobs_dict={
            'tile_color': _IntKnob(0, knob_name='tile_color'),
            'label': _make_knob('orig'),
        })
        snapshot = _snapshot_node_state(node)

        # Stamp-like mutation, then restore.
        node['tile_color'].setValue(0x7A3A00FF)
        node['label'].setValue('Local: changed')
        _restore_node_state(node, snapshot)

        self.assertEqual(node['tile_color'].value(), 0,
                         "tile_color must be restored (cast back to int)")
        self.assertEqual(node['label'].getValue(), 'orig')


if __name__ == '__main__':
    unittest.main()
