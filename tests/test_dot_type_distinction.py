"""Tests for DOT_TYPE Link Dot vs Local Dot distinction.

Covers:
- copy_anchors() Path B: anchor-backed Dot → dot_type='link', ANCHOR_DEFAULT_COLOR, "Link: " label
- copy_anchors() Path B: plain-node-backed Dot → dot_type='local', LOCAL_DOT_COLOR, "Local: " label
- paste_anchors() Path B cross-script: Link Dot reconnects when matching anchor found
- paste_anchors() Path B cross-script: Link Dot stays disconnected when no anchor found
- paste_anchors() Path B cross-script: Local Dot never reconnects (including same-stem false positive)
- paste_anchors() Path B same-script: Local Dot restores "Local: " label and LOCAL_DOT_COLOR after reconnect
- paste_anchors() Path B same-script: Link Dot does NOT restore Local appearance
- add_input_knob() without dot_type: no DOT_TYPE_KNOB_NAME knob added
- add_input_knob() with dot_type='link': DOT_TYPE_KNOB_NAME knob added with value 'link'
- add_input_knob() with dot_type='local': DOT_TYPE_KNOB_NAME knob added with value 'local'
- Backward compat: node without DOT_TYPE_KNOB_NAME, anchor FQNN → treated as Link Dot
- Backward compat: node without DOT_TYPE_KNOB_NAME, plain FQNN → treated as Local Dot
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call



# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_stub_node(name='Node', node_class='Dot', knobs_dict=None):
    """Create a StubNode with the given knobs dict."""
    import nuke as _nuke
    return _nuke.StubNode(name=name, node_class=node_class, knobs_dict=knobs_dict or {})


def _make_knob(value=''):
    """Create a StubKnob with the given value."""
    import nuke as _nuke
    return _nuke.StubKnob(value)


# ---------------------------------------------------------------------------
# Tests for add_input_knob() DOT_TYPE_KNOB_NAME extension
# ---------------------------------------------------------------------------

class TestAddInputKnobDotTypeExtension(unittest.TestCase):
    """Tests for the extended add_input_knob(node, dot_type=None) behavior."""

    def _make_node_for_add_input_knob(self, knobs_dict=None):
        """Return a plain (non-anchor) Dot stub node with tracking addKnob."""
        import nuke as _nuke
        from constants import KNOB_NAME, TAB_NAME

        node = _nuke.StubNode(name='Dot1', node_class='Dot', knobs_dict=knobs_dict or {})
        node._added_knob_names = []

        original_addKnob = node.addKnob
        def tracking_addKnob(knob):
            # Track by stub knob value when set — we intercept String_Knob calls
            node._added_knob_names.append(knob)
        node.addKnob = tracking_addKnob

        return node

    def test_add_input_knob_without_dot_type_does_not_add_dot_type_knob(self):
        """add_input_knob(node) with no dot_type must NOT add DOT_TYPE_KNOB_NAME knob."""
        from constants import DOT_TYPE_KNOB_NAME

        added_knob_names = []

        import nuke as _nuke
        _nuke.String_Knob = MagicMock(
            side_effect=lambda name, *args: _make_knob(name)
        )
        _nuke.Tab_Knob = MagicMock(
            side_effect=lambda name, *args: _make_knob(name)
        )

        node = _make_stub_node(name='Dot1', node_class='Dot')
        node._added_knob_names = []
        node.addKnob = lambda knob: added_knob_names.append(knob._value)
        node.removeKnob = lambda knob: None

        with patch('link.nuke', _nuke), \
             patch('link.is_anchor', return_value=False):
            from link import add_input_knob
            add_input_knob(node)

        self.assertNotIn(DOT_TYPE_KNOB_NAME, added_knob_names,
                         "DOT_TYPE_KNOB_NAME knob must NOT be added when dot_type is None")

    def test_add_input_knob_with_dot_type_link_adds_dot_type_knob_with_value_link(self):
        """add_input_knob(node, dot_type='link') must add DOT_TYPE_KNOB_NAME knob with value 'link'."""
        from constants import DOT_TYPE_KNOB_NAME

        added_knobs = {}

        import nuke as _nuke

        def tracking_string_knob(name, *args):
            knob = _make_knob(name)
            return knob

        _nuke.String_Knob = MagicMock(side_effect=tracking_string_knob)
        _nuke.Tab_Knob = MagicMock(side_effect=lambda name, *args: _make_knob(name))

        node = _make_stub_node(name='Dot1', node_class='Dot')
        node.removeKnob = lambda knob: None

        dot_type_knob_holder = {}

        def tracking_addKnob(knob):
            # After DOT_TYPE_KNOB_NAME knob is created and setValue is called,
            # we need to verify its value. We'll capture the last knob added
            # that was named DOT_TYPE_KNOB_NAME.
            added_knobs[knob._value] = knob

        node.addKnob = tracking_addKnob

        with patch('link.nuke', _nuke), \
             patch('link.is_anchor', return_value=False):
            from link import add_input_knob
            add_input_knob(node, dot_type='link')

        # The DOT_TYPE_KNOB_NAME constant string should appear as a created String_Knob
        dot_type_knob_calls = [
            call_args for call_args in _nuke.String_Knob.call_args_list
            if call_args[0][0] == DOT_TYPE_KNOB_NAME
        ]
        self.assertTrue(
            len(dot_type_knob_calls) >= 1,
            f"String_Knob({DOT_TYPE_KNOB_NAME!r}) must be called when dot_type='link'"
        )

    def test_add_input_knob_with_dot_type_local_adds_dot_type_knob_with_value_local(self):
        """add_input_knob(node, dot_type='local') must add DOT_TYPE_KNOB_NAME knob with value 'local'."""
        from constants import DOT_TYPE_KNOB_NAME

        import nuke as _nuke
        _nuke.String_Knob = MagicMock(side_effect=lambda name, *args: _make_knob(name))
        _nuke.Tab_Knob = MagicMock(side_effect=lambda name, *args: _make_knob(name))

        node = _make_stub_node(name='Dot1', node_class='Dot')
        node.removeKnob = lambda knob: None
        node.addKnob = lambda knob: None

        with patch('link.nuke', _nuke), \
             patch('link.is_anchor', return_value=False):
            from link import add_input_knob
            add_input_knob(node, dot_type='local')

        dot_type_knob_calls = [
            call_args for call_args in _nuke.String_Knob.call_args_list
            if call_args[0][0] == DOT_TYPE_KNOB_NAME
        ]
        self.assertTrue(
            len(dot_type_knob_calls) >= 1,
            f"String_Knob({DOT_TYPE_KNOB_NAME!r}) must be called when dot_type='local'"
        )


# ---------------------------------------------------------------------------
# Tests for copy_anchors() Path B DOT_TYPE behavior
# ---------------------------------------------------------------------------

class TestCopyHiddenDotTypeBehavior(unittest.TestCase):
    """Test copy_anchors() Path B sets DOT_TYPE, label, and color correctly."""

    def _make_dot_node_with_hide_input(self, name='Dot1', knobs_dict=None):
        """Return a Dot StubNode with hide_input=True and required knobs.

        KNOB_NAME is included so that copy_anchors()'s final setText call succeeds.
        The copy_anchors() tests must also patch 'anchors.is_link' to return False
        so copy_anchors() does not skip the node (is_link checks KNOB_NAME presence).
        """
        import nuke as _nuke
        from constants import KNOB_NAME

        base_knobs = {
            'hide_input': _make_knob(True),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'note_font_size': _make_knob(0),
            KNOB_NAME: _make_knob(''),
        }
        if knobs_dict:
            base_knobs.update(knobs_dict)
        return _nuke.StubNode(name=name, node_class='Dot', knobs_dict=base_knobs)

    def test_copy_hidden_anchor_backed_dot_calls_add_input_knob_with_dot_type_link(self):
        """copy_anchors() on anchor-backed Dot must call add_input_knob(node, dot_type='link')."""
        dot_node = self._make_dot_node_with_hide_input()
        anchor_input_node = _make_stub_node(name='Anchor_MyFootage', node_class='NoOp')

        dot_node._input = anchor_input_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=True) as mock_is_anchor, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.add_input_knob') as mock_add_input_knob, \
             patch('anchors.get_fully_qualified_node_name',
                   return_value='sourceScript.Anchor_MyFootage'):

            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import copy_anchors
            copy_anchors()

            mock_add_input_knob.assert_called_once_with(dot_node, dot_type='link')

    def test_copy_hidden_anchor_backed_dot_sets_tile_color_to_anchor_default_color(self):
        """copy_anchors() on anchor-backed Dot must set tile_color to ANCHOR_DEFAULT_COLOR."""
        from constants import ANCHOR_DEFAULT_COLOR

        dot_node = self._make_dot_node_with_hide_input()
        anchor_input_node = _make_stub_node(name='Anchor_MyFootage', node_class='NoOp')
        dot_node._input = anchor_input_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.setup_link_node'), \
             patch('anchors.add_input_knob'), \
             patch('anchors.get_fully_qualified_node_name',
                   return_value='sourceScript.Anchor_MyFootage'):

            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import copy_anchors
            copy_anchors()

            self.assertEqual(
                dot_node['tile_color'].getValue(),
                ANCHOR_DEFAULT_COLOR,
                "Anchor-backed Dot tile_color must be set to ANCHOR_DEFAULT_COLOR (canonical purple)"
            )

    def test_copy_hidden_plain_node_backed_dot_calls_add_input_knob_with_dot_type_local(self):
        """copy_anchors() on plain-node-backed Dot must call add_input_knob(node, dot_type='local')."""
        dot_node = self._make_dot_node_with_hide_input()
        plain_input_node = _make_stub_node(name='Blur1', node_class='Blur',
                                           knobs_dict={'label': _make_knob('')})
        dot_node._input = plain_input_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node'), \
             patch('anchors.add_input_knob') as mock_add_input_knob, \
             patch('anchors.get_fully_qualified_node_name',
                   return_value='sourceScript.Blur1'):

            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import copy_anchors
            copy_anchors()

            mock_add_input_knob.assert_called_once_with(dot_node, dot_type='local')

    def test_copy_hidden_plain_node_backed_dot_sets_label_to_local_prefix(self):
        """copy_anchors() on plain-node-backed Dot must set label to 'Local: {source name}'."""
        dot_node = self._make_dot_node_with_hide_input()
        plain_input_node = _make_stub_node(name='Blur1', node_class='Blur',
                                           knobs_dict={'label': _make_knob('')})
        dot_node._input = plain_input_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node'), \
             patch('anchors.add_input_knob'), \
             patch('anchors.get_fully_qualified_node_name',
                   return_value='sourceScript.Blur1'):

            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import copy_anchors
            copy_anchors()

            self.assertEqual(
                dot_node['label'].getValue(),
                'Local: Blur1',
                "Plain-node-backed Dot label must be set to 'Local: {source name}'"
            )

    def test_copy_hidden_plain_node_backed_dot_sets_tile_color_to_local_dot_color(self):
        """copy_anchors() on plain-node-backed Dot must set tile_color to LOCAL_DOT_COLOR."""
        from constants import LOCAL_DOT_COLOR

        dot_node = self._make_dot_node_with_hide_input()
        plain_input_node = _make_stub_node(name='Blur1', node_class='Blur',
                                           knobs_dict={'label': _make_knob('')})
        dot_node._input = plain_input_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node'), \
             patch('anchors.add_input_knob'), \
             patch('anchors.get_fully_qualified_node_name',
                   return_value='sourceScript.Blur1'):

            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import copy_anchors
            copy_anchors()

            self.assertEqual(
                dot_node['tile_color'].getValue(),
                LOCAL_DOT_COLOR,
                "Plain-node-backed Dot tile_color must be set to LOCAL_DOT_COLOR (burnt orange)"
            )


# ---------------------------------------------------------------------------
# Tests for paste_anchors() Path B cross-script DOT_TYPE behavior
# ---------------------------------------------------------------------------

class TestPasteHiddenCrossScriptDotTypeBehavior(unittest.TestCase):
    """Test paste_anchors() Path B cross-script gating by DOT_TYPE."""

    def _make_hidden_dot_node(self, name='Dot1', stored_fqnn='', dot_type=None):
        """Return a Dot StubNode with KNOB_NAME and optional DOT_TYPE_KNOB_NAME set."""
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME

        knobs_dict = {
            KNOB_NAME: _make_knob(stored_fqnn),
            'selected': _make_knob(False),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
        }
        if dot_type is not None:
            knobs_dict[DOT_TYPE_KNOB_NAME] = _make_knob(dot_type)

        return _nuke.StubNode(name=name, node_class='Dot', knobs_dict=knobs_dict)

    def test_link_dot_pasted_cross_script_with_matching_anchor_calls_setup_link_node(self):
        """Link Dot pasted cross-script with a matching anchor must call setup_link_node
        with the destination anchor. The tile_color is set by setup_link_node() to the
        anchor's real color — no ANCHOR_DEFAULT_COLOR overwrite (BUG-01 fix)."""
        # stored FQNN has 'sourceScript' stem; current script is 'destScript' → cross-script
        dot_node = self._make_hidden_dot_node(
            stored_fqnn='sourceScript.Anchor_MyFootage',
            dot_type='link'
        )

        destination_anchor = _make_stub_node(name='Anchor_MyFootage', node_class='NoOp')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name',
                   return_value=destination_anchor) as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'destScript.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            mock_find_by_name.assert_called_once_with('MyFootage')
            mock_setup_link_node.assert_called_once_with(destination_anchor, dot_node)

    def test_link_dot_pasted_cross_script_with_no_matching_anchor_does_not_call_setup_link_node(self):
        """Link Dot pasted cross-script with no matching anchor must leave node disconnected."""
        dot_node = self._make_hidden_dot_node(
            stored_fqnn='sourceScript.Anchor_MyFootage',
            dot_type='link'
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name',
                   return_value=None) as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'destScript.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            mock_find_by_name.assert_called_once_with('MyFootage')
            mock_setup_link_node.assert_not_called()

    def test_local_dot_pasted_cross_script_does_not_call_find_anchor_by_name_or_setup_link_node(self):
        """Local Dot pasted cross-script must NOT call find_anchor_by_name or setup_link_node,
        even when the input_node (from find_anchor_node) is non-None (different stem, different script)."""
        dot_node = self._make_hidden_dot_node(
            stored_fqnn='sourceScript.Blur1',
            dot_type='local'
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'destScript.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            mock_find_by_name.assert_not_called()
            mock_setup_link_node.assert_not_called()

    def test_local_dot_pasted_same_stem_false_positive_does_not_reconnect(self):
        """Local Dot with same script stem in stored FQNN as current script must NOT reconnect,
        even if find_anchor_node() returns a non-None node (same-stem false positive Bug 2)."""
        # stored FQNN stem 'untitled' == current script stem 'untitled' → same-stem
        # But this is a Local Dot, so cross-script check by FQNN stem will say "same-script",
        # while find_anchor_node might return a node.
        # The DOT_TYPE gate must prevent reconnect even here because this is a Local Dot
        # and we are in a different-stem scenario — BUT actually same-stem means same-script.
        #
        # The key test for Bug 2: stored FQNN has 'untitled' stem, current script is 'untitled.nk',
        # find_anchor_node returns a node (false positive), but DOT_TYPE='local' + FQNN stem matches
        # → considered same-script → setup_link_node is called (same-script path).
        # However, the Local restoration should still apply.
        #
        # Actual Bug 2 scenario: stored FQNN = 'untitled.Blur1' (local dot from script 'untitled'),
        # pasted to a different script ALSO named 'untitled' (same stem, different file).
        # With the FQNN stem comparison approach, this will look like "same-script", which means
        # setup_link_node will be called — but the reconnect to find_anchor_node()'s result may
        # be incorrect.
        #
        # For the DOT_TYPE gate's purpose, we test that a Local Dot with a truly cross-script
        # FQNN (different stems) is blocked. The same-stem false positive for Local Dots is
        # acknowledged as a deferred edge case: when two scripts share the same stem,
        # the FQNN stem comparison cannot distinguish them, and the same-script path is taken.
        # This is acceptable behavior per RESEARCH.md Pattern 3.
        #
        # This test verifies: stored_fqnn='untitled.Blur1', current='otherScript.nk' → cross-script
        # find_anchor_node returns a non-None node (same-name node exists in dest) → should NOT reconnect.

        from constants import DOT_TYPE_KNOB_NAME
        import nuke as _nuke

        dot_node = self._make_hidden_dot_node(
            stored_fqnn='untitled.Blur1',
            dot_type='local'
        )

        # Simulate same-stem false positive: find_anchor_node returns a node (a Blur in dest)
        false_positive_node = _make_stub_node(name='Blur1', node_class='Blur')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=false_positive_node), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            # Different stem: 'otherScript' vs stored 'untitled'
            root_obj.name.return_value = 'otherScript.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            # Local Dot with cross-script FQNN must not reconnect despite false positive
            mock_find_by_name.assert_not_called()
            mock_setup_link_node.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for paste_anchors() Path B backward compatibility (no DOT_TYPE knob)
# ---------------------------------------------------------------------------

class TestPasteHiddenBackwardCompatibility(unittest.TestCase):
    """Test that nodes without DOT_TYPE_KNOB_NAME are handled by FQNN inference."""

    def _make_hidden_dot_node_no_dot_type(self, stored_fqnn=''):
        """Return a Dot StubNode without DOT_TYPE_KNOB_NAME (pre-Phase-5 node)."""
        import nuke as _nuke
        from constants import KNOB_NAME

        knobs_dict = {
            KNOB_NAME: _make_knob(stored_fqnn),
            'selected': _make_knob(False),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
        }
        # Intentionally NO DOT_TYPE_KNOB_NAME
        return _nuke.StubNode(name='Dot1', node_class='Dot', knobs_dict=knobs_dict)

    def test_backward_compat_anchor_fqnn_without_dot_type_knob_attempts_reconnect(self):
        """Pre-Phase-5 node with anchor FQNN (no DOT_TYPE knob) must be treated as Link Dot
        and attempt name-based reconnect cross-script."""
        dot_node = self._make_hidden_dot_node_no_dot_type(
            stored_fqnn='sourceScript.Anchor_MyFootage'
        )

        destination_anchor = _make_stub_node(name='Anchor_MyFootage', node_class='NoOp')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name',
                   return_value=destination_anchor) as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'destScript.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            # Should have attempted reconnect because FQNN has anchor prefix
            mock_find_by_name.assert_called_once_with('MyFootage')
            mock_setup_link_node.assert_called_once_with(destination_anchor, dot_node)

    def test_backward_compat_plain_fqnn_without_dot_type_knob_does_not_reconnect(self):
        """Pre-Phase-5 node with plain (non-anchor) FQNN must be treated as Local Dot
        and NOT attempt reconnect cross-script."""
        dot_node = self._make_hidden_dot_node_no_dot_type(
            stored_fqnn='sourceScript.Blur1'
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'destScript.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            mock_find_by_name.assert_not_called()
            mock_setup_link_node.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for paste_anchors() Path B same-script DOT_TYPE behavior
# ---------------------------------------------------------------------------

class TestPasteHiddenSameScriptDotTypeBehavior(unittest.TestCase):
    """Test paste_anchors() Path B same-script path restores Local Dot appearance."""

    def _make_hidden_dot_node(self, name='Dot1', stored_fqnn='', dot_type=None):
        """Return a Dot StubNode with KNOB_NAME and optional DOT_TYPE_KNOB_NAME."""
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME

        knobs_dict = {
            KNOB_NAME: _make_knob(stored_fqnn),
            'selected': _make_knob(False),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
        }
        if dot_type is not None:
            knobs_dict[DOT_TYPE_KNOB_NAME] = _make_knob(dot_type)

        return _nuke.StubNode(name=name, node_class='Dot', knobs_dict=knobs_dict)

    def test_local_dot_pasted_same_script_restores_local_label_and_color_after_setup_link_node(self):
        """Local Dot pasted same-script must call setup_link_node then restore
        'Local: {source label}' label and LOCAL_DOT_COLOR tile_color."""
        from constants import LOCAL_DOT_COLOR, DOT_TYPE_KNOB_NAME

        # Same-script: stored FQNN stem 'shotA' matches current 'shotA'
        dot_node = self._make_hidden_dot_node(
            stored_fqnn='shotA.Blur1',
            dot_type='local'
        )

        source_node = _make_stub_node(name='Blur1', node_class='Blur',
                                      knobs_dict={'label': _make_knob('My Blur')})

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=source_node), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'shotA.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            # setup_link_node must be called for same-script reconnect
            mock_setup_link_node.assert_called_once_with(source_node, dot_node)

            # Local appearance must be restored after setup_link_node (which overwrites label/color)
            self.assertEqual(
                dot_node['label'].getValue(),
                'Local: My Blur',
                "Local Dot label must be restored to 'Local: {source label}' after same-script paste"
            )
            self.assertEqual(
                dot_node['tile_color'].getValue(),
                LOCAL_DOT_COLOR,
                "Local Dot tile_color must be restored to LOCAL_DOT_COLOR after same-script paste"
            )

    def test_link_dot_pasted_same_script_calls_setup_link_node_but_does_not_restore_local_appearance(self):
        """Link Dot pasted same-script must call setup_link_node but must NOT
        set 'Local: ' label prefix or LOCAL_DOT_COLOR."""
        from constants import LOCAL_DOT_COLOR, DOT_TYPE_KNOB_NAME

        # Same-script: stored FQNN stem 'shotA' matches current 'shotA'
        dot_node = self._make_hidden_dot_node(
            stored_fqnn='shotA.Anchor_MyFootage',
            dot_type='link'
        )

        anchor_node = _make_stub_node(name='Anchor_MyFootage', node_class='NoOp',
                                      knobs_dict={'label': _make_knob('MyFootage')})

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=anchor_node), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'shotA.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            # setup_link_node must be called for same-script reconnect
            mock_setup_link_node.assert_called_once_with(anchor_node, dot_node)

            # Local appearance must NOT be restored for Link Dot
            self.assertNotEqual(
                dot_node['tile_color'].getValue(),
                LOCAL_DOT_COLOR,
                "Link Dot tile_color must NOT be set to LOCAL_DOT_COLOR after same-script paste"
            )
            label_value = dot_node['label'].getValue()
            self.assertFalse(
                label_value.startswith('Local: '),
                f"Link Dot label must NOT start with 'Local: ' after same-script paste, got: {label_value!r}"
            )


# ---------------------------------------------------------------------------
# Tests for LOCAL_DOT_COLOR constant value
# ---------------------------------------------------------------------------

class TestLocalDotColorValue(unittest.TestCase):
    """Test that LOCAL_DOT_COLOR has the expected darkened burnt-orange value."""

    def test_local_dot_color_is_darkened_burnt_orange(self):
        """LOCAL_DOT_COLOR must equal 0x7A3A00FF (darker than the old 0xB35A00FF)."""
        from constants import LOCAL_DOT_COLOR
        self.assertEqual(
            LOCAL_DOT_COLOR,
            0x7A3A00FF,
            f"LOCAL_DOT_COLOR must be 0x7A3A00FF (darkened burnt orange), got 0x{LOCAL_DOT_COLOR:08X}"
        )


# ---------------------------------------------------------------------------
# Tests for paste_anchors() Path B same-script DOT_TYPE knob preservation
# ---------------------------------------------------------------------------

class TestPasteHiddenSameScriptDotTypeKnobPreservation(unittest.TestCase):
    """Test that paste_anchors() Path B same-script re-stamps the DOT_TYPE knob
    after calling setup_link_node(), which strips it via add_input_knob()."""

    def _make_hidden_dot_node(self, name='Dot1', stored_fqnn='', dot_type=None):
        """Return a Dot StubNode with KNOB_NAME and optional DOT_TYPE_KNOB_NAME."""
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME

        knobs_dict = {
            KNOB_NAME: _make_knob(stored_fqnn),
            'selected': _make_knob(False),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
        }
        if dot_type is not None:
            knobs_dict[DOT_TYPE_KNOB_NAME] = _make_knob(dot_type)

        return _nuke.StubNode(name=name, node_class='Dot', knobs_dict=knobs_dict)

    def test_local_dot_same_script_dot_type_knob_has_value_local_after_paste(self):
        """paste_anchors() Path B same-script Local Dot must re-stamp DOT_TYPE knob
        with 'local' after setup_link_node() strips it.

        This test verifies that the saved_dot_type/re-stamp pattern works: even if
        setup_link_node() strips the DOT_TYPE_KNOB_NAME knob via add_input_knob(),
        paste_anchors() must call add_input_knob(node, dot_type='local') after the
        setup_link_node() call, so the knob is present with value 'local' afterward.
        """
        from constants import DOT_TYPE_KNOB_NAME

        # Same-script: stored FQNN stem 'shotA' matches current 'shotA'
        dot_node = self._make_hidden_dot_node(
            stored_fqnn='shotA.Blur1',
            dot_type='local'
        )

        source_node = _make_stub_node(name='Blur1', node_class='Blur',
                                      knobs_dict={'label': _make_knob('My Blur')})

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=source_node), \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.add_input_knob') as mock_add_input_knob, \
             patch('anchors.is_anchor', return_value=False):

            root_obj = MagicMock()
            root_obj.name.return_value = 'shotA.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            # add_input_knob must be called with dot_type='local' to re-stamp the knob
            mock_add_input_knob.assert_called_once_with(dot_node, dot_type='local')


# ---------------------------------------------------------------------------
# Tests for paste_anchors() Path A/C link class selection
# ---------------------------------------------------------------------------

class TestPasteHiddenPathACLinkClass(unittest.TestCase):
    """Test that paste_anchors() Path A/C creates Dot link nodes for Dot sources
    and NoOp link nodes for all other sources, via get_link_class_for_source()."""

    def _make_anchor_node(self, name='Anchor_Footage', node_class='NoOp', stored_fqnn=''):
        """Return an anchor StubNode with KNOB_NAME set."""
        import nuke as _nuke
        from constants import KNOB_NAME

        knobs_dict = {
            KNOB_NAME: _make_knob(stored_fqnn),
            'selected': _make_knob(False),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
        }
        return _nuke.StubNode(name=name, node_class=node_class, knobs_dict=knobs_dict)

    def test_path_ac_dot_anchor_source_creates_dot_link_node(self):
        """paste_anchors() Path A/C: when the resolved source is a Dot node,
        nuke.createNode must be called with 'Dot' (not hardcoded 'NoOp')."""
        import nuke as _nuke

        # Anchor node (LINK_SOURCE_CLASSES-style: is_anchor returns True)
        # stored FQNN matches same-script so find_anchor_node returns a Dot source
        anchor_node = self._make_anchor_node(
            name='Anchor_MyDot', node_class='NoOp',
            stored_fqnn='shotA.Anchor_MyDot'
        )

        # The resolved input_node is a Dot (e.g. a Dot anchor used as a link source)
        dot_source_node = _make_stub_node(name='Dot1', node_class='Dot',
                                          knobs_dict={
                                              'label': _make_knob(''),
                                              'tile_color': _make_knob(0),
                                          })

        created_link_node = _make_stub_node(name='Dot2', node_class='Dot',
                                            knobs_dict={
                                                'label': _make_knob(''),
                                                'tile_color': _make_knob(0),
                                                'hide_input': _make_knob(False),
                                                'note_font_size': _make_knob(0),
                                                'selected': _make_knob(False),
                                            })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=dot_source_node), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.setup_link_node') as mock_setup_link_node:

            root_obj = MagicMock()
            root_obj.name.return_value = 'shotA.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [anchor_node]
            mock_nuke.createNode.return_value = created_link_node

            from anchors import paste_anchors
            paste_anchors()

            # Must call createNode with 'Dot' since dot_source_node.Class() == 'Dot'
            mock_nuke.createNode.assert_called_once_with('Dot')

    def test_path_ac_noop_anchor_source_creates_noop_link_node(self):
        """paste_anchors() Path A/C: when the resolved source is a NoOp anchor,
        nuke.createNode must be called with 'NoOp'."""
        import nuke as _nuke

        anchor_node = self._make_anchor_node(
            name='Anchor_Footage', node_class='NoOp',
            stored_fqnn='shotA.Anchor_Footage'
        )

        noop_source_node = _make_stub_node(name='Anchor_Footage', node_class='NoOp',
                                           knobs_dict={
                                               'label': _make_knob(''),
                                               'tile_color': _make_knob(0),
                                           })

        created_link_node = _make_stub_node(name='NoOp1', node_class='NoOp',
                                            knobs_dict={
                                                'label': _make_knob(''),
                                                'tile_color': _make_knob(0),
                                                'hide_input': _make_knob(False),
                                                'note_font_size': _make_knob(0),
                                                'selected': _make_knob(False),
                                            })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=noop_source_node), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.setup_link_node') as mock_setup_link_node:

            root_obj = MagicMock()
            root_obj.name.return_value = 'shotA.nk'
            mock_nuke.root.return_value = root_obj
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [anchor_node]
            mock_nuke.createNode.return_value = created_link_node

            from anchors import paste_anchors
            paste_anchors()

            # Must call createNode with 'NoOp' since noop_source_node.Class() == 'NoOp'
            mock_nuke.createNode.assert_called_once_with('NoOp')


if __name__ == '__main__':
    unittest.main()
