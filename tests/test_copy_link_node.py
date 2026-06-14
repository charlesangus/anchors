"""Tests for copy_anchors() Path L and paste_anchors() "input in selection" re-setup.

Covers:
- copy_anchors() Path L: existing link nodes are re-setup via setup_link_node() on copy
  rather than silently skipped.
- copy_anchors() Path L: when a link node's input is in the selection, KNOB_NAME is
  stamped to "" so paste can re-setup from the pasted input.
- paste_anchors(): when KNOB_NAME=="" and node.input(0) is not None (Nuke re-connected
  the pasted copy to the pasted copy of the input), setup_link_node() is called.
"""

import unittest
from unittest.mock import MagicMock, patch, call

from constants import KNOB_NAME
from tests.stubs import StubKnob, StubNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_knob(value='', knob_name=''):
    return StubKnob(value=value, knob_name=knob_name)


def _make_link_node(stored_fqnn='Anchor_Foo', node_class='Dot', name='Dot1', hide_input=True):
    """Return a stub link node (already has KNOB_NAME, so is_link() → True)."""
    knobs = {
        KNOB_NAME: _make_knob(stored_fqnn, knob_name=KNOB_NAME),
        'label': _make_knob('Link: Foo'),
        'tile_color': _make_knob(0),
        'hide_input': _make_knob(hide_input),
        'selected': _make_knob(False),
    }
    return StubNode(name=name, node_class=node_class, knobs_dict=knobs)


def _make_anchor_node(name='Anchor_Foo'):
    """Return a stub anchor node (name starts with ANCHOR_PREFIX)."""
    knobs = {
        'label': _make_knob('Foo'),
        'tile_color': _make_knob(0),
        'hide_input': _make_knob(False),
        'selected': _make_knob(False),
    }
    return StubNode(name=name, node_class='NoOp', knobs_dict=knobs)


def _make_plain_node(name='Merge1'):
    """Return a stub plain (non-anchor, non-link) node."""
    knobs = {
        'label': _make_knob(''),
        'tile_color': _make_knob(0),
        'hide_input': _make_knob(False),
        'selected': _make_knob(False),
    }
    return StubNode(name=name, node_class='Merge', knobs_dict=knobs)


def _patch_copy(mock_nuke, selected_nodes, prefs_mock):
    """Configure common copy_anchors() mock behaviour."""
    mock_nuke.lastHitGroup.return_value = MagicMock()
    mock_nuke.selectedNodes.return_value = selected_nodes
    mock_nuke.nodeCopy.return_value = None
    prefs_mock.plugin_enabled = True


# ---------------------------------------------------------------------------
# copy_anchors() Path L — re-setup on copy
# ---------------------------------------------------------------------------

class TestCopyLinkNodePathL(unittest.TestCase):
    """copy_anchors() must call setup_link_node() for existing link nodes."""

    def test_copy_link_dot_calls_setup_link_node_with_anchor_input(self):
        """Copying a Link Dot (input is an anchor NOT in the selection) calls
        setup_link_node(anchor, link_dot)."""
        anchor = _make_anchor_node('Anchor_Foo')
        link_dot = _make_link_node(stored_fqnn='Anchor_Foo', node_class='Dot')
        link_dot._input = anchor

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith('Anchor_')), \
             patch('anchors.setup_link_node') as mock_setup:

            _patch_copy(mock_nuke, [link_dot], mock_prefs)

            from anchors import copy_anchors
            copy_anchors()

        mock_setup.assert_called_once_with(anchor, link_dot)

    def test_copy_noop_link_calls_setup_link_node_with_anchor_input(self):
        """Copying a NoOp link node (input is an anchor, hide_input=True, NOT in selection)
        calls setup_link_node(anchor, noop_link)."""
        anchor = _make_anchor_node('Anchor_Foo')
        noop_link = _make_link_node(stored_fqnn='Anchor_Foo', node_class='NoOp', name='NoOp1')
        noop_link._input = anchor

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith('Anchor_')), \
             patch('anchors.setup_link_node') as mock_setup:

            _patch_copy(mock_nuke, [noop_link], mock_prefs)

            from anchors import copy_anchors
            copy_anchors()

        mock_setup.assert_called_once_with(anchor, noop_link)

    def test_copy_local_dot_restores_local_appearance(self):
        """Copying a Local Dot (input is a plain node NOT in the selection) stamps the
        Local label, LOCAL_DOT_COLOR, and dot_type='local' onto the clipboard copy,
        then restores the live original (issue #56 — copy is non-destructive)."""
        from constants import DOT_TYPE_KNOB_NAME, LOCAL_DOT_COLOR
        plain = _make_plain_node('Merge1')
        plain.knobs()['label']._value = 'my merge'
        local_dot = _make_link_node(stored_fqnn='Merge1', node_class='Dot', name='Dot1')
        local_dot._input = plain

        captured = {}

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup:

            _patch_copy(mock_nuke, [local_dot], mock_prefs)
            mock_nuke.root.return_value.name.return_value = 'sourceScript.nk'
            mock_nuke.nodeCopy.side_effect = lambda *a, **k: captured.update(
                label=local_dot['label'].getValue(),
                tile_color=local_dot['tile_color'].getValue(),
                has_dot_type=DOT_TYPE_KNOB_NAME in local_dot.knobs(),
                dot_type=(local_dot[DOT_TYPE_KNOB_NAME].getValue()
                          if DOT_TYPE_KNOB_NAME in local_dot.knobs() else None),
            )

            from anchors import copy_anchors
            copy_anchors()

        mock_setup.assert_called_once_with(plain, local_dot)
        # Clipboard copy carries the Local stamp...
        self.assertEqual(captured['label'], 'Local: my merge')
        self.assertEqual(captured['tile_color'], LOCAL_DOT_COLOR)
        self.assertTrue(captured['has_dot_type'])
        self.assertEqual(captured['dot_type'], 'local')
        # ...while the live original is restored to its pre-copy state.
        self.assertEqual(local_dot['label'].getValue(), 'Link: Foo')
        self.assertEqual(local_dot['tile_color'].getValue(), 0)
        self.assertNotIn(DOT_TYPE_KNOB_NAME, local_dot.knobs())

    def test_copy_link_dot_no_input_stamps_empty_fqnn(self):
        """Copying a disconnected link node (input(0)=None) stamps KNOB_NAME="" onto the
        clipboard copy, then restores the original's KNOB_NAME (issue #56)."""
        link_dot = _make_link_node(stored_fqnn='Anchor_Foo', node_class='Dot')
        link_dot._input = None

        captured = {}

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.setup_link_node') as mock_setup:

            _patch_copy(mock_nuke, [link_dot], mock_prefs)
            mock_nuke.nodeCopy.side_effect = \
                lambda *a, **k: captured.update(fqnn=link_dot[KNOB_NAME].getText())

            from anchors import copy_anchors
            copy_anchors()

        mock_setup.assert_not_called()
        self.assertEqual(captured['fqnn'], "")
        self.assertEqual(link_dot[KNOB_NAME].getText(), 'Anchor_Foo',
                         "Live original KNOB_NAME must be restored after copy")

    def test_copy_link_dot_input_in_selection_stamps_empty_fqnn(self):
        """When a Link Dot and its anchor are both in the selection, KNOB_NAME is
        stamped to "" on the clipboard copy so paste can re-setup from the pasted
        anchor copy; the live original is then restored (issue #56)."""
        anchor = _make_anchor_node('Anchor_Foo')
        link_dot = _make_link_node(stored_fqnn='Anchor_Foo', node_class='Dot')
        link_dot._input = anchor

        captured = {}

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith('Anchor_')), \
             patch('anchors.setup_link_node') as mock_setup:

            # Both nodes in selection — anchor is input_node and also in selected_nodes.
            _patch_copy(mock_nuke, [link_dot, anchor], mock_prefs)
            mock_nuke.nodeCopy.side_effect = \
                lambda *a, **k: captured.update(fqnn=link_dot[KNOB_NAME].getText())

            from anchors import copy_anchors
            copy_anchors()

        mock_setup.assert_not_called()
        self.assertEqual(captured['fqnn'], "")
        self.assertEqual(link_dot[KNOB_NAME].getText(), 'Anchor_Foo',
                         "Live original KNOB_NAME must be restored after copy")


# ---------------------------------------------------------------------------
# paste_anchors() — "input in selection" re-setup
# ---------------------------------------------------------------------------

class TestPasteLinkNodeInputInSelection(unittest.TestCase):
    """paste_anchors() must re-setup a link node whose KNOB_NAME=="" when Nuke
    has already re-connected it to the pasted copy of the input."""

    def _make_pasted_link(self, node_class='Dot', name='Dot1'):
        """Return a link stub with KNOB_NAME="" (as stamped by copy when input was in selection)."""
        knobs = {
            KNOB_NAME: _make_knob('', knob_name=KNOB_NAME),
            'label': _make_knob('Link: Foo'),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(True),
            'selected': _make_knob(False),
        }
        return StubNode(name=name, node_class=node_class, knobs_dict=knobs)

    def test_paste_dot_link_with_empty_fqnn_and_live_input_calls_setup_link_node(self):
        """When a pasted Dot has KNOB_NAME="" and input(0) is not None, setup_link_node
        is called with the actual pasted input."""
        pasted_anchor = _make_anchor_node('Anchor_Foo')
        pasted_link = self._make_pasted_link(node_class='Dot')
        pasted_link._input = pasted_anchor   # Nuke re-connected it

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith('Anchor_')):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_link]
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nukescripts.clear_selection_recursive = MagicMock()

            from anchors import paste_anchors
            paste_anchors()

        mock_setup.assert_called_once_with(pasted_anchor, pasted_link)

    def test_paste_noop_link_with_empty_fqnn_and_live_input_calls_setup_link_node(self):
        """Same as above but for a NoOp link node."""
        pasted_anchor = _make_anchor_node('Anchor_Foo')
        pasted_link = self._make_pasted_link(node_class='NoOp', name='NoOp1')
        pasted_link._input = pasted_anchor

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.setup_link_node') as mock_setup, \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith('Anchor_')):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_link]
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nukescripts.clear_selection_recursive = MagicMock()

            from anchors import paste_anchors
            paste_anchors()

        mock_setup.assert_called_once_with(pasted_anchor, pasted_link)

    def test_paste_dot_link_with_empty_fqnn_and_no_input_does_not_call_setup_link_node(self):
        """When KNOB_NAME=="" but input(0) is None (truly disconnected), setup_link_node
        must NOT be called — nothing to reconnect to."""
        pasted_link = self._make_pasted_link(node_class='Dot')
        pasted_link._input = None   # no live input

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.setup_link_node') as mock_setup:

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_link]
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nukescripts.clear_selection_recursive = MagicMock()

            from anchors import paste_anchors
            paste_anchors()

        mock_setup.assert_not_called()
