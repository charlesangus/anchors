"""Regression tests for GitHub issues #12 and #13.

Issue #12: Copy-pasted anchors, when copy-pasted, do not relink correctly.
    Root cause: copy_anchors() guard `if is_link(node): continue` skipped anchor
    nodes that had KNOB_NAME set from a prior old paste.  The stale KNOB_NAME
    (pointing to the original anchor) was never re-stamped, so the subsequent
    paste created a link to the wrong anchor.

Issue #13: Copying an Anchor — recolouring the original also recolours the copy.
    Root cause: get_links_for_anchor() (and related nuke.allNodes() scans) did not
    exclude anchor nodes.  An old-pasted anchor with KNOB_NAME pointing to the
    original was treated as a link to it, so colour propagation, rename propagation,
    and reconnect all affected the copy incorrectly.

Covers:
- BUG-12: copy_anchors() must re-stamp KNOB_NAME for anchor nodes that are also
  is_link (old-paste artefact) so the next paste links to the correct anchor.
- BUG-13: get_links_for_anchor() must exclude anchor nodes from its results.
- BUG-13b: rename_anchor_to() propagation must exclude anchor nodes.
- BUG-13c: reconnect_anchor_node() must exclude anchor nodes.
- BUG-13d: reconnect_all_links() must exclude anchor nodes.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call

from tests.stubs import StubKnob, StubNode


# ---------------------------------------------------------------------------
# Helpers shared across test classes
# ---------------------------------------------------------------------------

def _make_anchor_node(anchor_name, stored_fqnn='', extra_knobs=None):
    """Return a StubNode representing a NoOp anchor (name starts with Anchor_)."""
    import nuke as _nuke
    from constants import KNOB_NAME, TAB_NAME
    knobs = {
        KNOB_NAME: StubKnob(stored_fqnn, knob_name=KNOB_NAME),
        TAB_NAME: StubKnob('', knob_name=TAB_NAME),
        'tile_color': StubKnob(0, knob_name='tile_color'),
        'label': StubKnob('', knob_name='label'),
        # hide_input is required because NoOp is in HIDDEN_INPUT_CLASSES and
        # copy_anchors() Path B checks node['hide_input'].getValue().
        # Anchors always have hide_input=False (they are visible nodes).
        'hide_input': StubKnob(False, knob_name='hide_input'),
    }
    if extra_knobs:
        knobs.update(extra_knobs)
    return StubNode(
        name=f'Anchor_{anchor_name}',
        node_class='NoOp',
        knobs_dict=knobs,
    )


def _make_link_node(stored_fqnn, node_name='Dot1', node_class='Dot'):
    """Return a StubNode representing a link Dot (not an anchor)."""
    import nuke as _nuke
    from constants import KNOB_NAME, TAB_NAME
    knobs = {
        KNOB_NAME: StubKnob(stored_fqnn, knob_name=KNOB_NAME),
        TAB_NAME: StubKnob('', knob_name=TAB_NAME),
        'tile_color': StubKnob(0, knob_name='tile_color'),
        'label': StubKnob('', knob_name='label'),
        'hide_input': StubKnob(True, knob_name='hide_input'),
    }
    return StubNode(name=node_name, node_class=node_class, knobs_dict=knobs)


# ---------------------------------------------------------------------------
# BUG-12: copy_anchors() must not skip anchor nodes that have KNOB_NAME set
# ---------------------------------------------------------------------------

class TestBug12CopyAnchorsGuard(unittest.TestCase):
    """BUG-12: copy_anchors() guard must skip regular link nodes but not anchor nodes.

    The guard is `if is_link(node) and not is_anchor(node): continue`, so plain
    link nodes (hide_input Dots, etc.) are skipped while anchors pass through to
    the remaining copy paths.
    """

    def test_regular_link_node_is_still_skipped_by_copy_guard(self):
        """The guard change must not break existing behaviour: regular link nodes
        (is_link=True, is_anchor=False) must still be skipped by copy_anchors().
        """
        link_dot = _make_link_node('destScript.Anchor_One')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.is_link', return_value=True), \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.add_input_knob') as mock_add_input_knob, \
             patch('anchors.get_fully_qualified_node_name') as mock_fqnn:

            mock_nuke.selectedNodes.return_value = [link_dot]

            from anchors import copy_anchors
            copy_anchors()

        # Neither add_input_knob nor get_fully_qualified_node_name should run
        mock_add_input_knob.assert_not_called()
        mock_fqnn.assert_not_called()


# ---------------------------------------------------------------------------
# BUG-13: anchor nodes must be excluded from is_link scans in anchor.py
# ---------------------------------------------------------------------------

class TestBug13GetLinksForAnchorExcludesAnchors(unittest.TestCase):
    """BUG-13: get_links_for_anchor() must not include anchor nodes in its
    results, even when those nodes have KNOB_NAME pointing to the queried anchor
    (as happens after an old paste of an anchor).
    """

    def _run_get_links(self, all_nodes, source_anchor_fqnn):
        """Run get_links_for_anchor() with nuke.allNodes() stubbed to all_nodes."""
        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.get_fully_qualified_node_name',
                   return_value=source_anchor_fqnn):
            mock_nuke.allNodes.return_value = all_nodes
            # Use real is_link / is_anchor via link module
            from anchor import get_links_for_anchor
            source_anchor = _make_anchor_node('One', stored_fqnn=source_anchor_fqnn)
            return get_links_for_anchor(source_anchor)

    def test_old_pasted_anchor_excluded_from_get_links_for_anchor(self):
        """An old-pasted anchor node (is_link=True, is_anchor=True, KNOB_NAME
        pointing to the source anchor) must NOT appear in get_links_for_anchor()
        results — it is an independent anchor, not a link."""
        from constants import KNOB_NAME
        fqnn = 'destScript.Anchor_One'

        # A genuine link Dot pointing to Anchor_One
        genuine_link = _make_link_node(fqnn, node_name='Dot1')
        # An old-pasted anchor that has a stale KNOB_NAME pointing to Anchor_One
        old_pasted_anchor = _make_anchor_node('Two', stored_fqnn=fqnn)

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.get_fully_qualified_node_name', return_value=fqnn):

            mock_nuke.allNodes.return_value = [genuine_link, old_pasted_anchor]

            from anchor import get_links_for_anchor
            source = _make_anchor_node('One', stored_fqnn=fqnn)
            results = get_links_for_anchor(source)

        self.assertIn(genuine_link, results,
                      "Genuine link Dot should be in get_links_for_anchor() results")
        self.assertNotIn(old_pasted_anchor, results,
                         "Old-pasted anchor must NOT appear in get_links_for_anchor() — "
                         "it is an independent anchor, not a link")

    def test_get_links_for_anchor_returns_empty_when_only_old_pasted_anchors_present(self):
        """If the only nodes with matching KNOB_NAME are anchor nodes (old pastes),
        get_links_for_anchor() must return an empty list."""
        fqnn = 'destScript.Anchor_One'
        old_pasted_anchor = _make_anchor_node('Two', stored_fqnn=fqnn)

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.get_fully_qualified_node_name', return_value=fqnn):

            mock_nuke.allNodes.return_value = [old_pasted_anchor]

            from anchor import get_links_for_anchor
            source = _make_anchor_node('One', stored_fqnn=fqnn)
            results = get_links_for_anchor(source)

        self.assertEqual(results, [],
                         "get_links_for_anchor() must return [] when only anchor nodes "
                         "match — old-pasted anchors are independent, not links")


class TestBug13RenameAnchorPropagationExcludesAnchors(unittest.TestCase):
    """BUG-13b: rename_anchor_to() must not propagate label/KNOB_NAME updates
    to anchor nodes that happen to have a matching KNOB_NAME (old-paste artefact).
    """

    def test_rename_does_not_update_old_pasted_anchor_knob_name(self):
        """After renaming Anchor_One → Anchor_OneRenamed, an old-pasted anchor
        node with KNOB_NAME pointing to Anchor_One must NOT have its KNOB_NAME
        rewritten (it is independent, not a link to Anchor_One)."""
        from constants import KNOB_NAME

        old_fqnn = 'destScript.Anchor_One'
        old_pasted_anchor = _make_anchor_node('Two', stored_fqnn=old_fqnn)

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.get_fully_qualified_node_name',
                   side_effect=['destScript.Anchor_One', 'destScript.Anchor_OneRenamed']), \
             patch('anchor.sanitize_anchor_name', return_value='OneRenamed'), \
             patch('anchor.propagate_anchor_color'), \
             patch('anchor.anchor_display_name', return_value='OneRenamed'):

            mock_nuke.allNodes.return_value = [old_pasted_anchor]

            from anchor import rename_anchor_to
            source = _make_anchor_node('One', stored_fqnn=old_fqnn)
            rename_anchor_to(source, 'OneRenamed')

        # The old-pasted anchor's KNOB_NAME must remain pointing to Anchor_One
        self.assertEqual(
            old_pasted_anchor[KNOB_NAME].getText(),
            old_fqnn,
            "rename_anchor_to() must not update KNOB_NAME on independent anchor nodes",
        )


class TestBug13ReconnectExcludesAnchors(unittest.TestCase):
    """BUG-13c/d: reconnect_anchor_node() and reconnect_all_links() must not
    call reconnect_link_node() on anchor nodes.
    """

    def test_reconnect_anchor_node_excludes_old_pasted_anchors(self):
        """reconnect_anchor_node() must skip nodes that are is_anchor=True,
        even if their KNOB_NAME matches the queried anchor's FQNN."""
        fqnn = 'destScript.Anchor_One'
        old_pasted_anchor = _make_anchor_node('Two', stored_fqnn=fqnn)

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.get_fully_qualified_node_name', return_value=fqnn), \
             patch('anchor.reconnect_link_node') as mock_reconnect:

            mock_nuke.allNodes.return_value = [old_pasted_anchor]

            from anchor import reconnect_anchor_node
            source = _make_anchor_node('One', stored_fqnn=fqnn)
            reconnect_anchor_node(source)

        mock_reconnect.assert_not_called()

    def test_reconnect_all_links_excludes_anchor_nodes(self):
        """reconnect_all_links() must not call reconnect_link_node() on anchor
        nodes that have KNOB_NAME set (old-paste artefact)."""
        old_pasted_anchor = _make_anchor_node('Two', stored_fqnn='destScript.Anchor_One')
        genuine_link = _make_link_node('destScript.Anchor_One', node_name='Dot1')

        with patch('anchor.nuke') as mock_nuke, \
             patch('anchor.reconnect_link_node') as mock_reconnect:

            mock_nuke.allNodes.return_value = [old_pasted_anchor, genuine_link]

            from anchor import reconnect_all_links
            reconnect_all_links()

        called_nodes = [call_args[0][0] for call_args in mock_reconnect.call_args_list]
        self.assertIn(genuine_link, called_nodes,
                      "reconnect_all_links() must still reconnect genuine link nodes")
        self.assertNotIn(old_pasted_anchor, called_nodes,
                         "reconnect_all_links() must not reconnect old-pasted anchor nodes")
