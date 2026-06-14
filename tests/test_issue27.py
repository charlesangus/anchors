"""Regression tests for GitHub issue #27 — Issues with Anchors/Links in Test Script.

Covers five bugs found when using old-format scripts:

  Bug A  create_from_anchor() produced a Dot link when a NoOp anchor's input was a Dot.
  Bug B  (removed) anchors no longer receive FQNNs during copy, so cross-script paste
         can never create a broken self-referential link — tested via copy_anchors.
  Bug C  get_links_for_anchor() / rename_anchor_to() missed links whose KNOB_NAME was
         stored in the very-old full-file-path format ("/path/to/script.Anchor_Foo").
  Bug D  reconnect_anchor_node() had a duplicated inline loop that also missed
         old-format links; it now delegates to get_links_for_anchor().
  Bug E  reconnect_link_node() failed to reconnect when KNOB_NAME held a very-old
         full-file-path FQNN; fixed by find_anchor_node() stripping the first segment.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

import nuke as _nuke
from constants import ANCHOR_PREFIX, KNOB_NAME
from tests.stubs import StubKnob, StubNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_knob(value='', knob_name=''):
    return StubKnob(value=value, knob_name=knob_name)


def _make_anchor(name='PLATE_fg01', stored_fqnn='', hide_input=False):
    """Return a NoOp anchor StubNode (name already includes ANCHOR_PREFIX)."""
    knobs = {
        KNOB_NAME: _make_knob(stored_fqnn),
        'label': _make_knob(name),
        'tile_color': _make_knob(0),
        'hide_input': _make_knob(hide_input),
        'selected': _make_knob(False),
    }
    return StubNode(name=ANCHOR_PREFIX + name, node_class='NoOp', knobs_dict=knobs)


def _make_link(stored_fqnn, name='NoOp1', node_class='NoOp'):
    """Return a link StubNode with KNOB_NAME set to *stored_fqnn*."""
    knobs = {
        KNOB_NAME: _make_knob(stored_fqnn),
        'label': _make_knob('Link: PLATE_fg01'),
        'tile_color': _make_knob(0),
        'hide_input': _make_knob(True),
        'selected': _make_knob(False),
    }
    return StubNode(name=name, node_class=node_class, knobs_dict=knobs)


# ---------------------------------------------------------------------------
# Bug A — create_from_anchor uses anchor class, not input class
# ---------------------------------------------------------------------------

class TestCreateFromAnchorLinkClass(unittest.TestCase):
    """Bug A: create_from_anchor() must use the anchor's own class to pick the
    link node type, not the class of the anchor's input node."""

    def test_noop_anchor_with_dot_input_creates_noop_link(self):
        """A NoOp anchor whose input(0) is a Dot must create a NoOp link, not a Dot."""
        dot_input = StubNode(name='Dot98', node_class='Dot', knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
        })
        anchor = _make_anchor()
        anchor._input = dot_input  # anchor.input(0) is a Dot

        created_link = StubNode(name='NoOp1', node_class='NoOp', knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'note_font_size': _make_knob(0),
            'selected': _make_knob(False),
            KNOB_NAME: _make_knob(''),
        })

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.nukescripts'), \
             patch('anchor.setup_link_node'):
            mock_nuke.createNode.return_value = created_link

            import anchor as anchor_module
            anchor_module.create_from_anchor(anchor)

        mock_nuke.createNode.assert_called_once_with('NoOp')

    def test_dot_anchor_creates_dot_link(self):
        """A Dot anchor must still create a Dot link."""
        dot_anchor = StubNode(name='Anchor_PLATE_fg01', node_class='Dot', knobs_dict={
            'label': _make_knob('PLATE_fg01'),
            'tile_color': _make_knob(0),
            'note_font_size': _make_knob(111),
            'hide_input': _make_knob(False),
        })

        created_link = StubNode(name='Dot2', node_class='Dot', knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'note_font_size': _make_knob(0),
            'selected': _make_knob(False),
            KNOB_NAME: _make_knob(''),
        })

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.nukescripts'), \
             patch('anchor.setup_link_node'):
            mock_nuke.createNode.return_value = created_link

            import anchor as anchor_module
            anchor_module.create_from_anchor(dot_anchor)

        mock_nuke.createNode.assert_called_once_with('Dot')

    def test_noop_anchor_with_no_input_creates_noop_link(self):
        """A NoOp anchor with no input at all must create a NoOp link."""
        anchor = _make_anchor()
        anchor._input = None

        created_link = StubNode(name='NoOp1', node_class='NoOp', knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'note_font_size': _make_knob(0),
            'selected': _make_knob(False),
            KNOB_NAME: _make_knob(''),
        })

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.nukescripts'), \
             patch('anchor.setup_link_node'):
            mock_nuke.createNode.return_value = created_link

            import anchor as anchor_module
            anchor_module.create_from_anchor(anchor)

        mock_nuke.createNode.assert_called_once_with('NoOp')


# ---------------------------------------------------------------------------
# Bug B — anchors do not receive FQNNs during copy
# ---------------------------------------------------------------------------

class TestCopyAnchorsDoesNotStampFqnnOnAnchors(unittest.TestCase):
    """Bug B: copy_anchors() must not store any FQNN on anchor nodes.

    Previously Path C stamped the anchor's own FQNN onto itself, causing
    paste_anchors() to create a broken self-referential link when pasted
    cross-script.  Path C has been removed; anchors are left untouched.
    """

    def test_copy_anchors_does_not_call_add_input_knob_for_anchor_in_mixed_selection(self):
        """add_input_knob must not be called for an anchor node when the selection
        is mixed (contains non-anchor nodes).

        Issue #37 introduced all-anchor stamping, but mixed selections must still
        leave anchors unstamped so they paste as anchor copies, not links.
        """
        anchor = _make_anchor()
        non_anchor = StubNode(name='Merge1', node_class='Merge', knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.add_input_knob') as mock_add_input_knob, \
             patch('anchors.get_fully_qualified_node_name') as mock_fqnn:

            mock_nuke.selectedNodes.return_value = [anchor, non_anchor]
            mock_nuke.allNodes.return_value = []

            from anchors import copy_anchors
            copy_anchors()

        mock_add_input_knob.assert_not_called()
        mock_fqnn.assert_not_called()

    def test_anchor_pasted_cross_script_stays_as_anchor(self):
        """paste_anchors() must not replace an anchor with a link.

        With find_anchor_node returning None (cross-script) the anchor must be
        left unchanged — no createNode, no delete.
        """
        anchor = _make_anchor(stored_fqnn='sourceScript.Anchor_PLATE_fg01')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.is_anchor', return_value=True):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [anchor]

            from anchors import paste_anchors
            paste_anchors()

        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()

    def test_anchor_pasted_same_script_stays_as_anchor(self):
        """paste_anchors() must not replace an anchor with a link even when
        find_anchor_node resolves to a node (same-script paste)."""
        original_anchor = _make_anchor()
        pasted_anchor = _make_anchor(stored_fqnn='Anchor_PLATE_fg01')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=original_anchor), \
             patch('anchors.is_anchor', return_value=True):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_anchor]

            from anchors import paste_anchors
            paste_anchors()

        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()

    def test_copy_anchors_clears_stale_knob_name_on_anchor_in_mixed_selection(self):
        """copy_anchors() must clear KNOB_NAME to '' on an anchor that has a stale
        reference from a prior old paste, when the selection is mixed (contains
        non-anchor nodes), so the clipboard copy carries no spurious reference.

        Issue #37 introduced all-anchor stamping, so the stale-clear path only
        fires when the selection is not exclusively anchors.
        """
        anchor = _make_anchor(stored_fqnn='oldScript.Anchor_Foo')
        non_anchor = StubNode(name='Merge1', node_class='Merge', knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        })

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.add_input_knob'):

            mock_nuke.selectedNodes.return_value = [anchor, non_anchor]
            mock_nuke.allNodes.return_value = []
            captured = {}
            mock_nuke.nodeCopy.side_effect = \
                lambda *a, **k: captured.update(fqnn=anchor[KNOB_NAME].getText())

            from anchors import copy_anchors
            copy_anchors()

        self.assertEqual(
            captured['fqnn'], '',
            "Expected KNOB_NAME cleared to '' on the clipboard copy in mixed selection, "
            f"but got '{captured['fqnn']}'",
        )
        # Live original is left untouched — copy is non-destructive (issue #56).
        self.assertEqual(anchor[KNOB_NAME].getText(), 'oldScript.Anchor_Foo')

    def test_group_qualified_anchor_pasted_cross_script_stays_as_anchor(self):
        """A Group-qualified anchor pasted cross-script must not be replaced with a link.

        After copy_anchors clears its stale KNOB_NAME to '', paste_anchors receives
        an anchor with an empty stored name and must leave it untouched.
        """
        pasted_anchor = StubNode(
            name='Group1.Anchor_CamMain',
            node_class='NoOp',
            knobs_dict={
                KNOB_NAME: _make_knob(''),  # cleared by copy_anchors
                'label': _make_knob('CamMain'),
                'tile_color': _make_knob(0),
                'hide_input': _make_knob(False),
                'selected': _make_knob(False),
            },
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=None):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_anchor]

            from anchors import paste_anchors
            paste_anchors()

        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()

    def test_autorename_anchor_pasted_cross_script_stays_as_anchor(self):
        """An anchor that Nuke auto-renamed on paste (digit appended, e.g. Anchor_Foo1)
        must not be replaced with a link.

        After copy_anchors clears its stale KNOB_NAME to '', paste_anchors must
        leave the renamed anchor untouched regardless of the new name.
        """
        pasted_anchor = StubNode(
            name='Anchor_DeepAnchor1',  # Nuke appended '1' due to name collision
            node_class='NoOp',
            knobs_dict={
                KNOB_NAME: _make_knob(''),  # cleared by copy_anchors
                'label': _make_knob('DeepAnchor'),
                'tile_color': _make_knob(0),
                'hide_input': _make_knob(False),
                'selected': _make_knob(False),
            },
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=None):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_anchor]

            from anchors import paste_anchors
            paste_anchors()

        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Bug C — old-format FQNN matching in get_links_for_anchor / rename_anchor_to
# ---------------------------------------------------------------------------

class TestOldFormatFqnnMatching(unittest.TestCase):
    """Bug C: get_links_for_anchor() and rename_anchor_to() must find links whose
    KNOB_NAME was stored in the very-old full-file-path format:
        /path/to/script.Anchor_Foo
    stripping the first dot-segment must yield the current FQNN.
    """

    def _make_nuke_root(self, script_name='currentScript'):
        root = MagicMock()
        root.name.return_value = f'{script_name}.nk'
        return root

    def test_get_links_for_anchor_finds_old_format_link(self):
        """get_links_for_anchor() must return a link whose stored FQNN uses the
        very-old full-file-path prefix format."""
        anchor = _make_anchor('PLATE_fg01')
        # Old-format: full filesystem path before the dot, then anchor name
        old_format_stored = '/mnt/proj/editorial/script_v008.Anchor_PLATE_fg01'
        link = _make_link(old_format_stored)

        with patch('anchor.nuke') as mock_nuke:
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, link]

            import anchor as anchor_module
            result = anchor_module.get_links_for_anchor(anchor)

        self.assertIn(link, result)
        self.assertNotIn(anchor, result)

    def test_get_links_for_anchor_finds_legacy_stem_format_link(self):
        """get_links_for_anchor() must also find links using the legacy
        script-stem-prefixed format: 'scriptStem.Anchor_Foo'."""
        anchor = _make_anchor('PLATE_fg01')
        legacy_stored = 'currentScript.Anchor_PLATE_fg01'
        link = _make_link(legacy_stored)

        with patch('anchor.nuke') as mock_nuke:
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, link]

            import anchor as anchor_module
            result = anchor_module.get_links_for_anchor(anchor)

        self.assertIn(link, result)

    def test_get_links_for_anchor_finds_current_format_link(self):
        """get_links_for_anchor() continues to find current-format links."""
        anchor = _make_anchor('PLATE_fg01')
        current_stored = 'Anchor_PLATE_fg01'
        link = _make_link(current_stored)

        with patch('anchor.nuke') as mock_nuke:
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, link]

            import anchor as anchor_module
            result = anchor_module.get_links_for_anchor(anchor)

        self.assertIn(link, result)

    def test_get_links_for_anchor_does_not_match_different_anchor(self):
        """A link pointing at a different anchor must not be returned."""
        anchor = _make_anchor('PLATE_fg01')
        wrong_link = _make_link('/mnt/proj/script.Anchor_OTHER')

        with patch('anchor.nuke') as mock_nuke:
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, wrong_link]

            import anchor as anchor_module
            result = anchor_module.get_links_for_anchor(anchor)

        self.assertNotIn(wrong_link, result)

    def test_rename_anchor_to_updates_old_format_link(self):
        """rename_anchor_to() must update a link's KNOB_NAME even when the link
        stores the FQNN in the very-old full-file-path format."""
        anchor = _make_anchor('PLATE_fg01')
        old_format_stored = '/mnt/proj/editorial/script_v008.Anchor_PLATE_fg01'
        link = _make_link(old_format_stored)

        with patch('anchor.nuke') as mock_nuke:
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, link]

            import anchor as anchor_module
            anchor_module.rename_anchor_to(anchor, 'PLATE_fg02')

        self.assertEqual(link[KNOB_NAME].getText(), 'Anchor_PLATE_fg02')
        self.assertEqual(link['label'].getText(), 'Link: PLATE_fg02')

    def test_rename_anchor_to_updates_legacy_stem_format_link(self):
        """rename_anchor_to() must update a link using the legacy stem format."""
        anchor = _make_anchor('PLATE_fg01')
        legacy_stored = 'currentScript.Anchor_PLATE_fg01'
        link = _make_link(legacy_stored)

        with patch('anchor.nuke') as mock_nuke:
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, link]

            import anchor as anchor_module
            anchor_module.rename_anchor_to(anchor, 'PLATE_fg02')

        self.assertEqual(link[KNOB_NAME].getText(), 'Anchor_PLATE_fg02')


# ---------------------------------------------------------------------------
# Bug D — reconnect_anchor_node delegates to get_links_for_anchor
# ---------------------------------------------------------------------------

class TestReconnectAnchorNodeOldFormat(unittest.TestCase):
    """Bug D: reconnect_anchor_node() must reconnect links stored in old-format
    FQNNs, by delegating to get_links_for_anchor() rather than using an inline
    loop with a hardcoded equality check."""

    def _make_nuke_root(self, script_name='currentScript'):
        root = MagicMock()
        root.name.return_value = f'{script_name}.nk'
        return root

    def test_reconnect_anchor_node_finds_old_format_link(self):
        """reconnect_anchor_node() must call reconnect_link_node for a link
        whose KNOB_NAME uses the very-old full-file-path prefix format."""
        anchor = _make_anchor('PLATE_fg01')
        old_format_stored = '/mnt/proj/editorial/script_v008.Anchor_PLATE_fg01'
        link = _make_link(old_format_stored)

        reconnected = []

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.reconnect_link_node',
                   side_effect=lambda node: reconnected.append(node)):
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, link]

            import anchor as anchor_module
            anchor_module.reconnect_anchor_node(anchor)

        self.assertIn(link, reconnected)

    def test_reconnect_anchor_node_does_not_reconnect_different_anchor_link(self):
        """reconnect_anchor_node() must not touch links pointing at a different anchor."""
        anchor = _make_anchor('PLATE_fg01')
        wrong_link = _make_link('/mnt/proj/script.Anchor_OTHER')

        reconnected = []

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.reconnect_link_node',
                   side_effect=lambda node: reconnected.append(node)):
            mock_nuke.root.return_value = self._make_nuke_root()
            mock_nuke.allNodes.return_value = [anchor, wrong_link]

            import anchor as anchor_module
            anchor_module.reconnect_anchor_node(anchor)

        self.assertNotIn(wrong_link, reconnected)


# ---------------------------------------------------------------------------
# Bug E — reconnect_link_node resolves old-format stored FQNNs
# ---------------------------------------------------------------------------

class TestReconnectLinkNodeOldFormat(unittest.TestCase):
    """Bug E: reconnect_link_node() must reconnect to the anchor even when the
    link's KNOB_NAME holds a very-old full-file-path FQNN.

    find_anchor_node() strips the first dot-segment as a backward-compat
    fallback, so reconnect_link_node() (which calls find_anchor_node()) must
    also work transparently with old-format stored names.
    """

    def test_reconnect_link_node_with_old_format_fqnn_sets_input_to_anchor(self):
        """reconnect_link_node() must wire the link's input to the resolved anchor
        when KNOB_NAME stores a very-old full-file-path prefix FQNN."""
        old_format_stored = '/mnt/proj/editorial/script_v008.Anchor_PLATE_fg01'
        anchor = StubNode(name='Anchor_PLATE_fg01', node_class='NoOp', knobs_dict={})
        link = _make_link(old_format_stored)

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = (
                lambda name: anchor if name == 'Anchor_PLATE_fg01' else None
            )

            from link import reconnect_link_node
            reconnect_link_node(link)

        self.assertIs(link._input, anchor)

    def test_reconnect_link_node_with_unresolvable_old_format_fqnn_leaves_input_unchanged(self):
        """reconnect_link_node() must leave the link untouched when the anchor
        cannot be resolved (orphaned reference)."""
        old_format_stored = '/mnt/proj/editorial/script_v008.Anchor_DELETED'
        link = _make_link(old_format_stored)
        link._input = None

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.return_value = None

            from link import reconnect_link_node
            reconnect_link_node(link)

        self.assertIsNone(link._input)


if __name__ == '__main__':
    unittest.main()
