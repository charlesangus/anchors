"""Tests for Issue #55: copy-pasting an Anchor must paste an Anchor unchanged
when the anchor's input wire is hidden.

Root cause fixed: the copy/paste dispatch chains classified a node as a
hidden-input Dot (NoOp/Dot are both in HIDDEN_INPUT_CLASSES) *before* checking
is_anchor().  An anchor whose input was hidden (routine after Alt+H, or for Dot
anchors) was therefore misrouted into the hidden-dot path and stamped /
reconnected as a Local/Link dot.

Covers:
- Scenario C: anchor (hide_input=True) + its plain input → anchor NOT stamped.
- Scenario D: anchor (hide_input=True) + a Dot input → anchor NOT stamped.
- Scenario B: anchor (hide_input=True) + a Link → anchor NOT stamped.
- Paste defensive guard: a pasted anchor carrying a stale KNOB_NAME +
  DOT_TYPE='local' is left as an anchor (never enters _handle_pasted_hidden_input).
- Scenario A lock-in: an all-anchor selection still stamps DOT_TYPE='link'
  (Issue #37) even when the anchor's input is hidden.  This is the *desired*
  paste-as-link behaviour, NOT a misfeature.
"""

import unittest
from unittest.mock import MagicMock, patch

from constants import ANCHOR_PREFIX, DOT_TYPE_KNOB_NAME, KNOB_NAME
from tests.stubs import StubKnob, StubNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_knob(value='', knob_name=''):
    return StubKnob(value=value, knob_name=knob_name)


def _make_hidden_input_anchor(name='Anchor_Foo'):
    """A NoOp anchor whose input wire is hidden (hide_input=True)."""
    return StubNode(
        name=name,
        node_class='NoOp',
        knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(True),
            'selected': _make_knob(False),
        },
    )


def _make_plain_node(name='Read1', node_class='Read'):
    return StubNode(
        name=name,
        node_class=node_class,
        knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        },
    )


def _make_link_node(name='NoOp1'):
    """A plain Link node (is_link True via KNOB_NAME, is_anchor False)."""
    return StubNode(
        name=name,
        node_class='NoOp',
        knobs_dict={
            KNOB_NAME: _make_knob('', knob_name=KNOB_NAME),
            'label': _make_knob('Link: Foo'),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(True),
            'selected': _make_knob(False),
        },
    )


def _patch_copy(mock_nuke, selected_nodes, prefs_mock):
    mock_nuke.lastHitGroup.return_value = MagicMock()
    mock_nuke.selectedNodes.return_value = selected_nodes
    mock_nuke.nodeCopy.return_value = None
    mock_nuke.allNodes.return_value = []
    root_obj = MagicMock()
    root_obj.name.return_value = 'sourceScript.nk'
    mock_nuke.root.return_value = root_obj
    prefs_mock.plugin_enabled = True


# ---------------------------------------------------------------------------
# Scenarios C, D, B — a hidden-input anchor in a mixed selection is NOT stamped
# ---------------------------------------------------------------------------

class TestHiddenInputAnchorNotMisclassified(unittest.TestCase):
    """A hidden-input anchor copied alongside other nodes must remain an anchor."""

    def _run_copy_and_collect_stamps(self, anchor, other_node):
        """Copy [anchor, other_node] and return the list of nodes passed to
        add_input_knob (i.e. the nodes that got stamped)."""
        add_input_knob_calls = []

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.add_input_knob',
                   side_effect=lambda n, **kw: add_input_knob_calls.append(n)), \
             patch('anchors.setup_link_node'), \
             patch('anchors.get_fully_qualified_node_name', side_effect=lambda n: n.name()):

            _patch_copy(mock_nuke, [anchor, other_node], mock_prefs)

            from anchors import copy_anchors
            copy_anchors()

        return add_input_knob_calls

    def test_scenario_c_anchor_with_plain_input_is_not_stamped(self):
        """Scenario C: anchor (hidden input) + its plain input → anchor unstamped."""
        anchor = _make_hidden_input_anchor()
        plain_input = _make_plain_node('Read1')

        stamped = self._run_copy_and_collect_stamps(anchor, plain_input)

        self.assertNotIn(anchor, stamped,
                         "Hidden-input anchor must not be stamped as a Local/Link dot")
        self.assertNotIn(KNOB_NAME, anchor.knobs())
        self.assertNotIn(DOT_TYPE_KNOB_NAME, anchor.knobs())

    def test_scenario_d_anchor_with_dot_input_is_not_stamped(self):
        """Scenario D: anchor (hidden input) + a Dot input → anchor unstamped."""
        anchor = _make_hidden_input_anchor()
        dot_input = _make_plain_node('Dot1', node_class='Dot')

        stamped = self._run_copy_and_collect_stamps(anchor, dot_input)

        self.assertNotIn(anchor, stamped,
                         "Hidden-input anchor must not be stamped as a Local Dot")
        self.assertNotIn(KNOB_NAME, anchor.knobs())
        self.assertNotIn(DOT_TYPE_KNOB_NAME, anchor.knobs())

    def test_scenario_b_anchor_with_link_is_not_stamped(self):
        """Scenario B: anchor (hidden input) + a Link → anchor unstamped, link handled."""
        anchor = _make_hidden_input_anchor()
        link = _make_link_node('NoOp1')  # input is None → _stamp_for_link sets KNOB_NAME=""

        stamped = self._run_copy_and_collect_stamps(anchor, link)

        self.assertNotIn(anchor, stamped,
                         "Anchor must not be stamped when copied alongside a Link")
        self.assertNotIn(KNOB_NAME, anchor.knobs())


# ---------------------------------------------------------------------------
# Paste defensive guard — anchors never enter the hidden-input reconnect path
# ---------------------------------------------------------------------------

class TestPasteAnchorDefensiveGuard(unittest.TestCase):
    """A pasted anchor carrying stale link knobs must remain an anchor."""

    def test_stale_local_stamped_anchor_is_left_as_anchor(self):
        """A pasted anchor with KNOB_NAME + DOT_TYPE='local' (as a pre-fix
        clipboard could produce) must NOT be reconnected as a Local dot."""
        stale_anchor = StubNode(
            name=ANCHOR_PREFIX + 'Foo',
            node_class='NoOp',
            knobs_dict={
                KNOB_NAME: _make_knob('sourceScript.Read1', knob_name=KNOB_NAME),
                DOT_TYPE_KNOB_NAME: _make_knob('local', knob_name=DOT_TYPE_KNOB_NAME),
                'label': _make_knob(''),
                'tile_color': _make_knob(0),
                'hide_input': _make_knob(True),
                'selected': _make_knob(False),
            },
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors._find_local_node') as mock_find_local_node:

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [stale_anchor]

            from anchors import paste_anchors
            paste_anchors()

        # The anchor must NOT have been routed into _handle_pasted_hidden_input().
        mock_setup_link_node.assert_not_called()
        mock_find_local_node.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario A lock-in — copy-only-anchors still pastes as Links (Issue #37)
# ---------------------------------------------------------------------------

class TestScenarioAStillPastesAsLink(unittest.TestCase):
    """Issue #55 confirms Scenario A is desired, not a misfeature: an all-anchor
    selection must still be stamped DOT_TYPE='link' so it pastes as a Link —
    even when the anchor's input wire is hidden."""

    def test_all_anchor_selection_with_hidden_input_is_stamped_as_link(self):
        anchor = _make_hidden_input_anchor('Anchor_Solo')

        captured = {}

        def fake_add_input_knob(node, dot_type=None):
            node._knobs[KNOB_NAME] = StubKnob(knob_name=KNOB_NAME)
            if dot_type is not None:
                node._knobs[DOT_TYPE_KNOB_NAME] = StubKnob(dot_type, knob_name=DOT_TYPE_KNOB_NAME)
            captured['dot_type'] = dot_type

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.add_input_knob', side_effect=fake_add_input_knob), \
             patch('anchors.get_fully_qualified_node_name', side_effect=lambda n: n.name()):

            _patch_copy(mock_nuke, [anchor], mock_prefs)

            from anchors import copy_anchors
            copy_anchors()

        self.assertEqual(captured.get('dot_type'), 'link',
                         "All-anchor selection must still be stamped for paste-as-link (Issue #37)")


if __name__ == '__main__':
    unittest.main()
