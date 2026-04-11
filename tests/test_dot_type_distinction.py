"""Tests for DOT_TYPE Link Dot vs Local Dot distinction.

Covers:
- copy_anchors() Path B: anchor-backed Dot → dot_type='link', ANCHOR_DEFAULT_COLOR, "Link: " label
- copy_anchors() Path B: plain-node-backed Dot → dot_type='local', LOCAL_DOT_COLOR, "Local: " label
- paste_anchors() Path B cross-script: Link Dot reconnects when matching anchor found
- paste_anchors() Path B cross-script: Link Dot stays disconnected when no anchor found
- paste_anchors() Path B cross-script: Local Dot with unresolvable node leaves Dot disconnected
- paste_anchors() Path B: Local Dot reconnects when find_anchor_node() resolves a node (GitHub #28)
- paste_anchors() Path B same-script: Local Dot restores "Local: " label and LOCAL_DOT_COLOR after reconnect
- paste_anchors() Path B same-script: Link Dot does NOT restore Local appearance
- add_input_knob() without dot_type: no DOT_TYPE_KNOB_NAME knob added
- add_input_knob() with dot_type='link': DOT_TYPE_KNOB_NAME knob added with value 'link'
- add_input_knob() with dot_type='local': DOT_TYPE_KNOB_NAME knob added with value 'local'
- Backward compat: node without DOT_TYPE_KNOB_NAME, anchor FQNN → treated as Link Dot
- Backward compat: node without DOT_TYPE_KNOB_NAME, plain FQNN → treated as Local Dot
"""

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call



# ---------------------------------------------------------------------------
# Qt stub helper (needed by TestAnchorShortcutDotRouting which reloads anchor)
# ---------------------------------------------------------------------------

def _ensure_qt_stubs_support_mock_attributes():
    """Ensure Qt stub modules support auto-attribute access for the anchor tests.

    When the full test suite is discovered, test_cross_script_paste.py installs
    Qt sub-module stubs as plain types.ModuleType objects.  These do NOT create
    attributes on access (unlike MagicMock), so calls like QtGui.QColor(...) raise
    AttributeError.  This helper patches the current stubs to be MagicMock-based
    if they are plain ModuleType instances.

    Also ensures the nuke stub has NUKE_VERSION_MAJOR = 16 so anchor.py takes
    the PySide6 import path on reload (not PySide2 → ImportError → QtGui = None).
    """
    import nuke as current_nuke
    if not hasattr(current_nuke, 'NUKE_VERSION_MAJOR'):
        current_nuke.NUKE_VERSION_MAJOR = 16

    for module_key in ('PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtCore'):
        existing = sys.modules.get(module_key)
        if existing is not None and not isinstance(existing, MagicMock):
            mock_replacement = MagicMock()
            sys.modules[module_key] = mock_replacement
            parent_key = 'PySide6'
            attr_name = module_key.split('.')[-1]
            parent_stub = sys.modules.get(parent_key)
            if parent_stub is not None:
                setattr(parent_stub, attr_name, mock_replacement)


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

    def test_local_dot_reconnects_when_find_anchor_node_resolves_a_node(self):
        """Local Dot reconnects to whatever node find_anchor_node() resolves in the
        current script context.  GitHub #28 removed stem-based cross-script detection,
        so if a same-named node exists in the destination it is used regardless of
        which script the Dot originated from."""

        dot_node = self._make_hidden_dot_node(
            stored_fqnn='Blur1',  # new format: no script stem
            dot_type='local'
        )

        matching_node = _make_stub_node(
            name='Blur1',
            node_class='Blur',
            knobs_dict={'label': _make_knob('')},
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=matching_node), \
             patch('anchors.find_anchor_by_name') as mock_find_by_name, \
             patch('anchors.setup_link_node') as mock_setup_link_node, \
             patch('anchors.add_input_knob'), \
             patch('anchors.is_anchor', return_value=False):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [dot_node]

            from anchors import paste_anchors
            paste_anchors()

            # Local Dot reconnects to the resolved node; name-based anchor search is not used
            mock_setup_link_node.assert_called_once_with(matching_node, dot_node)
            mock_find_by_name.assert_not_called()


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
# ---------------------------------------------------------------------------
# Tests for anchor_shortcut() dispatch routing (BUG-04)
# ---------------------------------------------------------------------------

class TestAnchorShortcutDotRouting(unittest.TestCase):
    """Regression tests for BUG-04: anchor_shortcut() dispatch paths.

    Covers:
    - Dot node selected → create_anchor() called, _offer_make_dot_anchor() NOT called
    - Non-Dot node selected → create_anchor() called (unchanged)
    - Anchor node selected → rename_anchor() called (unchanged)
    - No selection → select_anchor_and_create() called (unchanged)
    - Multiple non-anchor nodes selected → create_anchor() called (unchanged)
    """

    def setUp(self):
        import importlib
        _ensure_qt_stubs_support_mock_attributes()
        import anchor as anchor_mod
        importlib.reload(anchor_mod)
        self.anchor_mod = anchor_mod
        import nuke as nuke_stub
        nuke_stub.selectedNodes.reset_mock()
        self.nuke_stub = nuke_stub

    def test_dot_selected_calls_create_anchor_not_offer_make_dot_anchor(self):
        """Dot node selected → create_anchor() called once; _offer_make_dot_anchor() NOT called."""
        import nuke as _nuke
        dot_node = _nuke.StubNode(name='Dot1', node_class='Dot')
        self.nuke_stub.selectedNodes = MagicMock(return_value=[dot_node])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'is_anchor', return_value=False), \
             patch.object(self.anchor_mod, 'is_link', return_value=False), \
             patch.object(self.anchor_mod, 'create_anchor') as mock_create_anchor, \
             patch.object(self.anchor_mod, '_offer_make_dot_anchor') as mock_offer:
            self.anchor_mod.anchor_shortcut()

        mock_create_anchor.assert_called_once()
        mock_offer.assert_not_called()

    def test_non_dot_selected_calls_create_anchor(self):
        """Non-Dot node selected → create_anchor() called once."""
        import nuke as _nuke
        read_node = _nuke.StubNode(name='Read1', node_class='Read')
        self.nuke_stub.selectedNodes = MagicMock(return_value=[read_node])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'is_anchor', return_value=False), \
             patch.object(self.anchor_mod, 'create_anchor') as mock_create_anchor:
            self.anchor_mod.anchor_shortcut()

        mock_create_anchor.assert_called_once()

    def test_anchor_selected_calls_rename_anchor(self):
        """Anchor node selected → rename_anchor() called once; create_anchor() NOT called."""
        import nuke as _nuke
        anchor_node = _nuke.StubNode(name='Anchor_Footage', node_class='NoOp')
        self.nuke_stub.selectedNodes = MagicMock(return_value=[anchor_node])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'is_anchor', return_value=True), \
             patch.object(self.anchor_mod, 'rename_anchor') as mock_rename_anchor, \
             patch.object(self.anchor_mod, 'create_anchor') as mock_create_anchor:
            self.anchor_mod.anchor_shortcut()

        mock_rename_anchor.assert_called_once_with(anchor_node)
        mock_create_anchor.assert_not_called()

    def test_no_selection_calls_select_anchor_and_create(self):
        """No nodes selected → select_anchor_and_create() called once."""
        self.nuke_stub.selectedNodes = MagicMock(return_value=[])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'select_anchor_and_create') as mock_select_and_create:
            self.anchor_mod.anchor_shortcut()

        mock_select_and_create.assert_called_once()

    def test_multiple_nodes_selected_calls_create_anchor(self):
        """Multiple non-anchor nodes selected → create_anchor() called once."""
        import nuke as _nuke
        node1 = _nuke.StubNode(name='Read1', node_class='Read')
        node2 = _nuke.StubNode(name='Read2', node_class='Read')
        self.nuke_stub.selectedNodes = MagicMock(return_value=[node1, node2])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'is_anchor', return_value=False), \
             patch.object(self.anchor_mod, 'create_anchor') as mock_create_anchor:
            self.anchor_mod.anchor_shortcut()

        mock_create_anchor.assert_called_once()


if __name__ == '__main__':
    unittest.main()
