"""Tests for Issue #37: Copy-Paste Heuristics — copy-all-anchors pastes as Links.

Covers:
- copy_anchors() Path C: all-anchor selection stamps each anchor with its own FQNN and dot_type='link'
- copy_anchors() Path C: mixed selection does NOT stamp anchors; stale KNOB_NAME is cleared as before
- paste_anchors() Path D: pasted anchor with KNOB_NAME + DOT_TYPE_KNOB_NAME='link' → replaced by Link node
- paste_anchors() Path D: pasted anchor with KNOB_NAME but no DOT_TYPE_KNOB_NAME → skipped (BUG-02 compat)
- paste_anchors() Path D cross-script: FQNN not resolvable, name-based lookup succeeds → Link created
- paste_anchors() Path D cross-script: FQNN not resolvable, no name match → pasted anchor left as-is
"""

import unittest
from unittest.mock import MagicMock, patch

from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME, ANCHOR_PREFIX
from tests.stubs import StubKnob, StubNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_knob(value='', knob_name=''):
    return StubKnob(value=value, knob_name=knob_name)


def _make_anchor_node(name='Anchor_Foo', xpos=100, ypos=200):
    """Return a stub NoOp anchor node with no KNOB_NAME (clean anchor)."""
    return StubNode(
        name=ANCHOR_PREFIX + name.replace(ANCHOR_PREFIX, ''),
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        },
    )


def _make_stamped_anchor_node(anchor_name, stored_fqnn, xpos=100, ypos=200):
    """Return a stub anchor node already stamped for paste-as-link (as produced
    by copy_anchors() when selection_is_all_anchors is True)."""
    return StubNode(
        name=anchor_name,
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            KNOB_NAME: _make_knob(stored_fqnn, knob_name=KNOB_NAME),
            DOT_TYPE_KNOB_NAME: _make_knob('link', knob_name=DOT_TYPE_KNOB_NAME),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        },
    )


def _make_stale_knob_anchor_node(anchor_name, stored_fqnn, xpos=100, ypos=200):
    """Return a stub anchor node with a stale KNOB_NAME but NO DOT_TYPE_KNOB_NAME
    (old-style nodes that should NOT be replaced on paste, per BUG-02)."""
    return StubNode(
        name=anchor_name,
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            KNOB_NAME: _make_knob(stored_fqnn, knob_name=KNOB_NAME),
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        },
    )


def _make_plain_node(name='Merge1'):
    """Return a stub non-anchor, non-link node."""
    return StubNode(
        name=name,
        node_class='Merge',
        knobs_dict={
            'label': _make_knob(''),
            'tile_color': _make_knob(0),
            'hide_input': _make_knob(False),
            'selected': _make_knob(False),
        },
    )


def _patch_copy(mock_nuke, selected_nodes, prefs_mock):
    """Configure common copy_anchors() mock state."""
    mock_nuke.lastHitGroup.return_value = MagicMock()
    mock_nuke.selectedNodes.return_value = selected_nodes
    mock_nuke.nodeCopy.return_value = None
    mock_nuke.allNodes.return_value = []
    prefs_mock.plugin_enabled = True


# ---------------------------------------------------------------------------
# copy_anchors() — Path C (Issue #37)
# ---------------------------------------------------------------------------

class TestCopyAnchorsAllAnchorSelection(unittest.TestCase):
    """copy_anchors() Path C: all-anchor selection stamps each anchor for paste-as-link."""

    def test_all_anchor_selection_stamps_each_anchor_with_its_own_fqnn(self):
        """When every node in the selection is an anchor, each anchor gets
        KNOB_NAME = its own FQNN and DOT_TYPE_KNOB_NAME = 'link'."""
        anchor_a = _make_anchor_node('Foo')
        anchor_b = _make_anchor_node('Bar')

        knobs_added = {}

        def fake_add_input_knob(node, dot_type=None):
            """Simulate add_input_knob: add KNOB_NAME (and optionally DOT_TYPE_KNOB_NAME)."""
            knob = StubKnob(knob_name=KNOB_NAME)
            node._knobs[KNOB_NAME] = knob
            if dot_type is not None:
                dt_knob = StubKnob(dot_type, knob_name=DOT_TYPE_KNOB_NAME)
                node._knobs[DOT_TYPE_KNOB_NAME] = dt_knob
            knobs_added[node.name()] = dot_type

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.add_input_knob', side_effect=fake_add_input_knob), \
             patch('anchors.get_fully_qualified_node_name', side_effect=lambda n: n.name()):

            _patch_copy(mock_nuke, [anchor_a, anchor_b], mock_prefs)
            captured = {}
            mock_nuke.nodeCopy.side_effect = lambda *a, **k: captured.update(
                a=anchor_a[KNOB_NAME].getText(), b=anchor_b[KNOB_NAME].getText())

            from anchors import copy_anchors
            copy_anchors()

        # Both anchors should have been stamped with dot_type='link'
        self.assertEqual(knobs_added.get(anchor_a.name()), 'link')
        self.assertEqual(knobs_added.get(anchor_b.name()), 'link')

        # The clipboard copy carries each anchor's own FQNN in KNOB_NAME...
        self.assertEqual(captured['a'], anchor_a.name())
        self.assertEqual(captured['b'], anchor_b.name())
        # ...while the live originals are restored (the stamp would otherwise leave
        # them looking like stale links — issue #56 non-destructive copy).
        self.assertNotIn(KNOB_NAME, anchor_a.knobs())
        self.assertNotIn(KNOB_NAME, anchor_b.knobs())

    def test_all_anchor_selection_single_anchor_is_stamped(self):
        """A single anchor in the selection should also be stamped."""
        anchor = _make_anchor_node('Solo')

        def fake_add_input_knob(node, dot_type=None):
            knob = StubKnob(knob_name=KNOB_NAME)
            node._knobs[KNOB_NAME] = knob
            if dot_type is not None:
                dt_knob = StubKnob(dot_type, knob_name=DOT_TYPE_KNOB_NAME)
                node._knobs[DOT_TYPE_KNOB_NAME] = dt_knob

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.add_input_knob', side_effect=fake_add_input_knob), \
             patch('anchors.get_fully_qualified_node_name', side_effect=lambda n: n.name()):

            _patch_copy(mock_nuke, [anchor], mock_prefs)
            captured = {}
            mock_nuke.nodeCopy.side_effect = lambda *a, **k: captured.update(
                fqnn=anchor[KNOB_NAME].getText(),
                dot_type=anchor[DOT_TYPE_KNOB_NAME].getValue())

            from anchors import copy_anchors
            copy_anchors()

        # The clipboard copy carries the anchor's own FQNN and dot_type='link'...
        self.assertEqual(captured['fqnn'], anchor.name())
        self.assertEqual(captured['dot_type'], 'link')
        # ...while the live original is restored (issue #56 non-destructive copy).
        self.assertNotIn(KNOB_NAME, anchor.knobs())
        self.assertNotIn(DOT_TYPE_KNOB_NAME, anchor.knobs())


class TestCopyAnchorsMixedSelection(unittest.TestCase):
    """copy_anchors() Path C: mixed selection leaves anchors unstamped."""

    def test_mixed_selection_anchor_is_not_stamped(self):
        """When the selection contains non-anchor nodes, anchors must NOT be
        stamped — they remain plain copies on paste."""
        anchor = _make_anchor_node('Foo')
        plain = _make_plain_node('Merge1')

        add_input_knob_calls = []

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.add_input_knob', side_effect=lambda n, **kw: add_input_knob_calls.append(n)):

            _patch_copy(mock_nuke, [anchor, plain], mock_prefs)

            from anchors import copy_anchors
            copy_anchors()

        # add_input_knob must NOT have been called for the anchor
        self.assertNotIn(anchor, add_input_knob_calls)
        # And the anchor must not have KNOB_NAME stamped
        self.assertNotIn(KNOB_NAME, anchor.knobs())

    def test_mixed_selection_stale_knob_anchor_is_cleared(self):
        """When the selection is mixed and an anchor has a stale KNOB_NAME
        (is_link=True for that anchor), the knob value must be cleared."""
        # Anchor that also has a stale KNOB_NAME
        stale_anchor = StubNode(
            name=ANCHOR_PREFIX + 'Foo',
            node_class='NoOp',
            knobs_dict={
                KNOB_NAME: _make_knob('OldScript.Anchor_Foo', knob_name=KNOB_NAME),
                'label': _make_knob(''),
                'tile_color': _make_knob(0),
                'hide_input': _make_knob(False),
                'selected': _make_knob(False),
            },
        )
        plain = _make_plain_node('Merge1')

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', side_effect=lambda n: KNOB_NAME in n.knobs()), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)):

            _patch_copy(mock_nuke, [stale_anchor, plain], mock_prefs)
            captured = {}
            mock_nuke.nodeCopy.side_effect = \
                lambda *a, **k: captured.update(fqnn=stale_anchor[KNOB_NAME].getValue())

            from anchors import copy_anchors
            copy_anchors()

        # The clipboard copy carries no spurious reference (KNOB_NAME cleared)...
        self.assertEqual(captured['fqnn'], '')
        # ...while the live original is left untouched (issue #56 non-destructive copy).
        self.assertEqual(stale_anchor[KNOB_NAME].getValue(), 'OldScript.Anchor_Foo')


# ---------------------------------------------------------------------------
# paste_anchors() — Path D (Issue #37)
# ---------------------------------------------------------------------------

class TestPasteAnchorAsLink(unittest.TestCase):
    """paste_anchors() Path D: stamped anchors are replaced by Link nodes."""

    def test_same_script_stamped_anchor_is_replaced_by_link_node(self):
        """A pasted anchor that was stamped for paste-as-link (has KNOB_NAME +
        DOT_TYPE_KNOB_NAME='link') must be replaced by a Link node pointing to
        the original anchor when find_anchor_node() resolves it."""
        import nuke as _nuke

        original_anchor = StubNode(
            name=ANCHOR_PREFIX + 'Foo',
            node_class='NoOp',
            knobs_dict={
                'tile_color': _make_knob(0),
                'label': _make_knob(''),
                'hide_input': _make_knob(False),
            },
        )

        pasted_copy = _make_stamped_anchor_node(
            anchor_name=ANCHOR_PREFIX + 'Foo1',   # Nuke renamed the paste
            stored_fqnn=ANCHOR_PREFIX + 'Foo',
            xpos=50, ypos=60,
        )

        created_link_nodes = []

        def fake_create_node(node_class):
            link = StubNode(
                name='NoOp_link',
                node_class=node_class,
                knobs_dict={'selected': _make_knob(False)},
            )
            created_link_nodes.append(link)
            return link

        deleted_nodes = []

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=original_anchor), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.get_link_class_for_source', return_value='NoOp'), \
             patch('anchors.setup_link_node'):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_copy]
            mock_nuke.createNode.side_effect = fake_create_node
            mock_nuke.delete.side_effect = deleted_nodes.append

            from anchors import paste_anchors
            paste_anchors()

        # Pasted anchor must have been deleted and replaced by a link node
        self.assertEqual(len(created_link_nodes), 1, "Expected one Link node to be created")
        self.assertIn(pasted_copy, deleted_nodes, "Pasted anchor copy must be deleted")

    def test_pasted_anchor_without_dot_type_knob_is_not_replaced(self):
        """A pasted anchor with a stale KNOB_NAME but no DOT_TYPE_KNOB_NAME must
        be left untouched — this preserves the BUG-02 fix."""
        import nuke as _nuke

        original_anchor = StubNode(
            name=ANCHOR_PREFIX + 'Foo',
            node_class='NoOp',
            knobs_dict={
                'tile_color': _make_knob(0),
                'label': _make_knob(''),
                'hide_input': _make_knob(False),
            },
        )

        stale_anchor = _make_stale_knob_anchor_node(
            anchor_name=ANCHOR_PREFIX + 'Foo1',
            stored_fqnn='sourceScript.' + ANCHOR_PREFIX + 'Foo',
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=original_anchor), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.setup_link_node'):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [stale_anchor]

            from anchors import paste_anchors
            paste_anchors()

        # Must NOT be replaced
        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()

    def test_cross_script_stamped_anchor_name_match_creates_link(self):
        """Cross-script paste: when find_anchor_node() returns None but
        find_anchor_by_name() finds a matching anchor, a Link node is created."""
        import nuke as _nuke

        destination_anchor = StubNode(
            name=ANCHOR_PREFIX + 'Foo',
            node_class='NoOp',
            knobs_dict={
                'tile_color': _make_knob(0),
                'label': _make_knob(''),
                'hide_input': _make_knob(False),
            },
        )

        pasted_copy = _make_stamped_anchor_node(
            anchor_name=ANCHOR_PREFIX + 'Foo',
            stored_fqnn=ANCHOR_PREFIX + 'Foo',   # no-stem FQNN from source script
        )

        created_link_nodes = []

        def fake_create_node(node_class):
            link = StubNode(
                name='NoOp_link',
                node_class=node_class,
                knobs_dict={'selected': _make_knob(False)},
            )
            created_link_nodes.append(link)
            return link

        deleted_nodes = []

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=destination_anchor), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.get_link_class_for_source', return_value='NoOp'), \
             patch('anchors.setup_link_node'):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_copy]
            mock_nuke.createNode.side_effect = fake_create_node
            mock_nuke.delete.side_effect = deleted_nodes.append

            from anchors import paste_anchors
            paste_anchors()

        self.assertEqual(len(created_link_nodes), 1, "Expected a Link node to be created")
        self.assertIn(pasted_copy, deleted_nodes, "Pasted anchor copy must be deleted")

    def test_cross_script_stamped_anchor_no_match_leaves_anchor_intact(self):
        """Cross-script paste: when neither find_anchor_node() nor find_anchor_by_name()
        resolve the anchor, the pasted copy must be left as-is."""
        pasted_copy = _make_stamped_anchor_node(
            anchor_name=ANCHOR_PREFIX + 'Unknown',
            stored_fqnn=ANCHOR_PREFIX + 'Unknown',
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.find_anchor_node', return_value=None), \
             patch('anchors.find_anchor_by_name', return_value=None), \
             patch('anchors.is_anchor', side_effect=lambda n: n.name().startswith(ANCHOR_PREFIX)), \
             patch('anchors.setup_link_node'):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_copy]

            from anchors import paste_anchors
            paste_anchors()

        mock_nuke.createNode.assert_not_called()
        mock_nuke.delete.assert_not_called()


# ---------------------------------------------------------------------------
# copy_anchors(cut=True) — all-anchor cut must NOT stamp anchors
# ---------------------------------------------------------------------------

class TestCopyAnchorsAllAnchorCut(unittest.TestCase):
    """copy_anchors(cut=True): all-anchor cut must leave anchors unstamped.

    When the user cuts (rather than copies) an all-anchor selection the original
    nodes will be deleted immediately after copy_anchors() returns.  Stamping
    them with DOT_TYPE_KNOB_NAME='link' and their own FQNN would mean that on
    paste, Path D fires but cannot find the (deleted) originals, leaving the
    pasted copies with stale link knobs and is_link() == True.  The `not cut`
    guard prevents this by skipping the stamp step entirely for cuts.
    """

    def test_cut_all_anchor_selection_does_not_stamp_anchors(self):
        """add_input_knob must NOT be called for anchors when cut=True,
        even when the entire selection is anchors."""
        anchor_a = _make_anchor_node('Foo')
        anchor_b = _make_anchor_node('Bar')

        add_input_knob_calls = []

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.prefs') as mock_prefs, \
             patch('anchors.is_link', return_value=False), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.add_input_knob', side_effect=lambda n, **kw: add_input_knob_calls.append(n)):

            _patch_copy(mock_nuke, [anchor_a, anchor_b], mock_prefs)

            from anchors import copy_anchors
            copy_anchors(cut=True)

        # add_input_knob must NOT have been called — anchors are not stamped on cut
        self.assertEqual(add_input_knob_calls, [],
                         "add_input_knob must not be called for anchors when cut=True")
        # KNOB_NAME must not have been added to either anchor
        self.assertNotIn(KNOB_NAME, anchor_a.knobs())
        self.assertNotIn(KNOB_NAME, anchor_b.knobs())


if __name__ == '__main__':
    unittest.main()
