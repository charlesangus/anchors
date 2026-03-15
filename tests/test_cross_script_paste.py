"""Tests for cross-script paste reconnection logic.

Covers:
- _extract_display_name_from_fqnn() helper
- paste_anchors() Path A/C cross-script name-based reconnect for NoOp anchors (XSCRIPT-01)
- paste_anchors() Path B Dot cross-script disconnection (XSCRIPT-02 / PASTE-04)
- LINK_SOURCE_CLASSES frozenset membership
- ANCHOR_LINK_CLASS_KNOB_NAME removed from constants
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call



# ---------------------------------------------------------------------------
# Tests for LINK_SOURCE_CLASSES and removed ANCHOR_LINK_CLASS_KNOB_NAME
# ---------------------------------------------------------------------------

class TestConstantsCleanup(unittest.TestCase):

    def test_link_source_classes_contains_all_eight_expected_class_names(self):
        from constants import LINK_SOURCE_CLASSES
        expected_classes = {
            "Read", "DeepRead", "ReadGeo",
            "Camera", "Camera2", "Camera3", "Camera4",
            "GeoImport",
        }
        self.assertEqual(LINK_SOURCE_CLASSES, expected_classes)

    def test_link_source_classes_is_a_frozenset(self):
        from constants import LINK_SOURCE_CLASSES
        self.assertIsInstance(LINK_SOURCE_CLASSES, frozenset)

    def test_anchor_link_class_knob_name_not_importable_from_constants(self):
        import constants
        self.assertFalse(
            hasattr(constants, 'ANCHOR_LINK_CLASS_KNOB_NAME'),
            "ANCHOR_LINK_CLASS_KNOB_NAME should have been removed from constants.py",
        )


# ---------------------------------------------------------------------------
# Tests for _extract_display_name_from_fqnn() helper
# ---------------------------------------------------------------------------

class TestExtractDisplayNameFromFqnn(unittest.TestCase):

    def setUp(self):
        # Import inside setUp to ensure stub is in place
        from anchors import _extract_display_name_from_fqnn
        self.extract = _extract_display_name_from_fqnn

    def test_simple_anchor_fqnn_returns_display_name(self):
        result = self.extract('shotA.Anchor_MyFootage')
        self.assertEqual(result, 'MyFootage')

    def test_group_nested_anchor_fqnn_returns_last_segment_display_name(self):
        # last segment only — Group nesting is collapsed
        result = self.extract('shotA.Group1.Anchor_MyFootage')
        self.assertEqual(result, 'MyFootage')

    def test_empty_fqnn_returns_none(self):
        result = self.extract('')
        self.assertIsNone(result)

    def test_fqnn_without_anchor_prefix_returns_none(self):
        # File node case — last segment does not start with ANCHOR_PREFIX
        result = self.extract('shotA.Read1')
        self.assertIsNone(result)

    def test_fqnn_with_anchor_prefix_only_returns_empty_string(self):
        # 'Anchor_' with nothing after the prefix — edge case
        result = self.extract('shotA.Anchor_')
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# Integration tests for paste_hidden() cross-script reconnect behavior
# ---------------------------------------------------------------------------

class TestCrossScriptReconnect(unittest.TestCase):
    """Test paste_anchors() Path A/C cross-script reconnection via stubs."""

    def _make_noop_anchor_node(self, anchor_name, stored_fqnn, xpos=100, ypos=200):
        """Return a stub NoOp anchor node with KNOB_NAME set."""
        import nuke as _nuke
        from constants import KNOB_NAME, ANCHOR_PREFIX
        knob = _nuke.StubKnob(stored_fqnn)
        selected_knob = _nuke.StubKnob(False)
        node = _nuke.StubNode(
            name=ANCHOR_PREFIX + anchor_name,
            node_class='NoOp',
            xpos=xpos,
            ypos=ypos,
            knobs_dict={KNOB_NAME: knob, 'selected': selected_knob},
        )
        return node

    def _make_dot_anchor_node(self, stored_fqnn):
        """Return a stub Dot anchor node with KNOB_NAME set."""
        import nuke as _nuke
        from constants import KNOB_NAME
        knob = _nuke.StubKnob(stored_fqnn)
        selected_knob = _nuke.StubKnob(False)
        node = _nuke.StubNode(
            name='Dot1',
            node_class='Dot',
            knobs_dict={KNOB_NAME: knob, 'selected': selected_knob},
        )
        return node

    def test_cross_script_anchor_with_matching_anchor_stays_as_anchor_placeholder(self):
        """When a NoOp anchor is pasted cross-script and a matching anchor exists in the
        destination script, paste_anchors() must leave the pasted anchor in place — it must
        NOT be replaced by a link node (BUG-02 fix)."""
        import nuke as _nuke
        from constants import KNOB_NAME

        pasted_anchor_node = self._make_noop_anchor_node(
            anchor_name='MyFootage',
            stored_fqnn='sourceScript.Anchor_MyFootage',
            xpos=100,
            ypos=200,
        )

        destination_anchor = _nuke.StubNode(
            name='Anchor_MyFootage',
            node_class='NoOp',
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=destination_anchor), \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=True):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_anchor_node]

            from anchors import paste_anchors
            paste_anchors()

            # Anchor placeholder must NOT be replaced — createNode and delete must not be called
            mock_nuke.createNode.assert_not_called()
            mock_nuke.delete.assert_not_called()

    def test_cross_script_reconnect_with_no_matching_anchor_leaves_placeholder(self):
        """When a NoOp anchor is pasted cross-script but no matching anchor exists in
        the destination, paste_anchors() should leave the placeholder node intact."""
        import nuke as _nuke

        pasted_anchor_node = self._make_noop_anchor_node(
            anchor_name='UnknownFootage',
            stored_fqnn='sourceScript.Anchor_UnknownFootage',
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=None), \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=True):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_anchor_node]

            from anchors import paste_anchors
            paste_anchors()

            # No new node should be created; placeholder stays
            mock_nuke.createNode.assert_not_called()
            mock_nuke.delete.assert_not_called()

    def test_dot_anchor_pasted_cross_script_does_not_attempt_reconnect(self):
        """A Dot anchor pasted cross-script must NOT trigger the name-based
        reconnect — the node.Class() == 'Dot' gate must prevent it."""
        import nuke as _nuke

        dot_anchor_node = self._make_dot_anchor_node(
            stored_fqnn='sourceScript.Dot1',
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=True):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_anchor_node]

            from anchors import paste_anchors
            paste_anchors()

            # find_anchor_by_name must NOT be called for Dot anchors
            mock_find_by_name.assert_not_called()
            mock_nuke.createNode.assert_not_called()
            mock_nuke.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Regression tests for BUG-01 and BUG-02 — both tests FAIL before any fix
# ---------------------------------------------------------------------------

class TestBugRegressions(unittest.TestCase):
    """Regression tests for cross-script paste bugs.

    Both tests are written to FAIL against the current (unfixed) code.
    They exercise the exact buggy code paths identified in the research phase.
    All pre-existing tests must remain green after this class is added.
    """

    def _make_link_dot_node(self, stored_fqnn):
        """Return a stub Dot node configured as a cross-script Link Dot."""
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME
        return _nuke.StubNode(
            name='Dot1',
            node_class='Dot',
            knobs_dict={
                KNOB_NAME: _nuke.StubKnob(stored_fqnn),
                DOT_TYPE_KNOB_NAME: _nuke.StubKnob('link'),
                'selected': _nuke.StubKnob(False),
                'hide_input': _nuke.StubKnob(True),
                'tile_color': _nuke.StubKnob(0),
                'label': _nuke.StubKnob(''),
                'note_font_size': _nuke.StubKnob(0),
            },
        )

    def _make_noop_anchor_node_for_bug02(self, stored_fqnn, xpos=100, ypos=200):
        """Return a stub NoOp anchor node with a cross-script FQNN for BUG-02."""
        import nuke as _nuke
        from constants import KNOB_NAME, ANCHOR_PREFIX
        return _nuke.StubNode(
            name=ANCHOR_PREFIX + 'MyFootage',
            node_class='NoOp',
            xpos=xpos,
            ypos=ypos,
            knobs_dict={
                KNOB_NAME: _nuke.StubKnob(stored_fqnn),
                'selected': _nuke.StubKnob(False),
            },
        )

    def test_bug01_link_dot_cross_script_color(self):
        """BUG-01 regression: a Link Dot pasted cross-script must display the
        anchor's tile_color, not ANCHOR_DEFAULT_COLOR (purple 0x6f3399ff).

        This test FAILS before the fix because paste_anchors() line 212 calls
        node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR) after setup_link_node()
        has already set the correct anchor color.
        """
        import nuke as _nuke
        from constants import ANCHOR_DEFAULT_COLOR
        from tests.stubs import make_stub_nuke_module

        anchor_color = 0xff0000ff  # red — distinct from purple ANCHOR_DEFAULT_COLOR
        cross_script_fqnn = 'sourceScript.Anchor_MyFootage'

        link_dot_node = self._make_link_dot_node(stored_fqnn=cross_script_fqnn)

        destination_anchor = _nuke.StubNode(
            name='Anchor_MyFootage',
            node_class='NoOp',
            knobs_dict={
                'tile_color': _nuke.StubKnob(anchor_color),
                'label': _nuke.StubKnob(''),
                'hide_input': _nuke.StubKnob(False),
            },
        )

        stub_nuke_for_link = make_stub_nuke_module()

        with patch('anchors.nuke') as mock_paste_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=destination_anchor), \
             patch('link.find_node_color', return_value=anchor_color), \
             patch('link.nuke', stub_nuke_for_link):

            mock_paste_nuke.root.return_value.name.return_value = 'destScript.nk'
            mock_paste_nuke.nodePaste.return_value = None
            mock_paste_nuke.selectedNodes.return_value = [link_dot_node]

            from anchors import paste_anchors
            paste_anchors()

        result_color = link_dot_node['tile_color'].getValue()
        self.assertEqual(
            result_color,
            anchor_color,
            f"Expected tile_color {hex(anchor_color)} (anchor color) but got "
            f"{hex(result_color)} — BUG-01: line 212 is overwriting with ANCHOR_DEFAULT_COLOR "
            f"{hex(ANCHOR_DEFAULT_COLOR)}",
        )

    def test_bug02_anchor_stays_anchor_cross_script(self):
        """BUG-02 regression: a NoOp anchor pasted cross-script must remain an
        anchor node — it must NOT be deleted and replaced by a link node, even
        when a same-named anchor exists in the destination script.

        This test FAILS before the fix because paste_anchors() lines 162-171 call
        nuke.createNode() and nuke.delete() to replace the anchor placeholder.
        """
        import nuke as _nuke
        from constants import KNOB_NAME

        cross_script_fqnn = 'sourceScript.Anchor_MyFootage'
        pasted_anchor_node = self._make_noop_anchor_node_for_bug02(
            stored_fqnn=cross_script_fqnn,
        )

        destination_anchor = _nuke.StubNode(
            name='Anchor_MyFootage',
            node_class='NoOp',
            knobs_dict={
                'tile_color': _nuke.StubKnob(0),
                'label': _nuke.StubKnob(''),
                'hide_input': _nuke.StubKnob(False),
            },
        )

        def is_anchor_side_effect(node):
            """Return True only for the pasted anchor node, False for anything else."""
            return node is pasted_anchor_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=destination_anchor), \
             patch('anchors.setup_link_node'), \
             patch('anchors.is_anchor', side_effect=is_anchor_side_effect):

            mock_nuke.root.return_value.name.return_value = 'destScript.nk'
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_anchor_node]

            from anchors import paste_anchors
            paste_anchors()

        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
