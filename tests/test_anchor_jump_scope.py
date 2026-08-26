"""Tests for the per-anchor jump scope checkbox (issue #66).

Covers:
- add_jump_scope_knob() adds an unticked checkbox and is idempotent.
- create_anchor_named() and mark_dot_as_anchor() give new anchors the checkbox.
- jumps_to_node_only() reads the knob and defaults to False when it is absent
  (anchors written by earlier versions must keep framing their tree).
- navigate_to_anchor() frames the anchor alone when the box is ticked, and the
  anchor plus its upstream tree when it is not.
- migrations.migrate_script() backfills the checkbox onto anchors that predate
  it in its single graph pass, skips non-anchors, and is idempotent.
"""

import importlib
import sys
import unittest
from unittest.mock import MagicMock, patch


def _ensure_stub_modules():
    """Make sure the shared nuke/Qt stubs carry everything these tests touch.

    Mirrors the helper in tests/test_anchor_navigation.py: when the whole suite
    is discovered, an earlier test file may have swapped a stub module out for a
    plainer one.
    """
    import nuke as current_nuke
    if not hasattr(current_nuke, 'NUKE_VERSION_MAJOR'):
        current_nuke.NUKE_VERSION_MAJOR = 16
    if not isinstance(getattr(current_nuke, 'zoom', None), MagicMock):
        current_nuke.zoom = MagicMock(return_value=1.0)
    if not isinstance(getattr(current_nuke, 'center', None), MagicMock):
        current_nuke.center = MagicMock(return_value=[0.0, 0.0])
    if not hasattr(current_nuke, 'zoomToFitSelected'):
        current_nuke.zoomToFitSelected = MagicMock()

    for module_key in ('PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtCore'):
        existing = sys.modules.get(module_key)
        if existing is not None and not isinstance(existing, MagicMock):
            mock_replacement = MagicMock()
            sys.modules[module_key] = mock_replacement
            parent_stub = sys.modules.get('PySide6')
            if parent_stub is not None:
                setattr(parent_stub, module_key.split('.')[-1], mock_replacement)


import anchor  # noqa: E402
import link as link_module  # noqa: E402
import migrations  # noqa: E402
from constants import (  # noqa: E402
    ANCHOR_JUMP_NODE_ONLY_KNOB_NAME,
    ANCHOR_PREFIX,
    DOT_ANCHOR_KNOB_NAME,
    DOT_ANCHOR_PREFIX,
    NODE_ONLY_JUMP_ZOOM,
)


def _make_anchor_stub(name='Anchor_Foo', node_class='NoOp', xpos=0, ypos=0, jump_node_only=None):
    """Return a StubNode acting as an anchor, optionally carrying the checkbox.

    jump_node_only=None means the knob is absent entirely — the shape an anchor
    saved by a version that predates the checkbox has.
    """
    import nuke as nuke_stub
    knobs = {
        'selected': nuke_stub.StubKnob(False),
        'label': nuke_stub.StubKnob('Foo'),
        'tile_color': nuke_stub.StubKnob(0),
    }
    if jump_node_only is not None:
        knobs[ANCHOR_JUMP_NODE_ONLY_KNOB_NAME] = nuke_stub.StubKnob(
            jump_node_only, knob_name=ANCHOR_JUMP_NODE_ONLY_KNOB_NAME
        )
    return nuke_stub.StubNode(
        name=name, node_class=node_class, xpos=xpos, ypos=ypos, knobs_dict=knobs
    )


# ---------------------------------------------------------------------------
# add_jump_scope_knob() / jumps_to_node_only()
# ---------------------------------------------------------------------------

class TestJumpScopeKnob(unittest.TestCase):
    """The checkbox itself: creation, default state, idempotency, tolerant read."""

    def setUp(self):
        _ensure_stub_modules()
        importlib.reload(link_module)

    def test_add_jump_scope_knob_adds_checkbox(self):
        """add_jump_scope_knob() puts the frozen knob name on the node."""
        node = _make_anchor_stub()
        link_module.add_jump_scope_knob(node)
        self.assertIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, node.knobs())

    def test_added_checkbox_defaults_to_unticked(self):
        """A freshly added checkbox is unticked — the tree-framing default."""
        node = _make_anchor_stub()
        link_module.add_jump_scope_knob(node)
        self.assertFalse(link_module.jumps_to_node_only(node))

    def test_add_jump_scope_knob_is_idempotent(self):
        """A second call must not replace a checkbox the user has already ticked."""
        node = _make_anchor_stub(jump_node_only=True)
        link_module.add_jump_scope_knob(node)
        self.assertTrue(link_module.jumps_to_node_only(node))

    def test_jumps_to_node_only_false_when_knob_absent(self):
        """An anchor from before the checkbox existed reads as tree-framing."""
        node = _make_anchor_stub()
        self.assertFalse(link_module.jumps_to_node_only(node))

    def test_jumps_to_node_only_true_when_ticked(self):
        node = _make_anchor_stub(jump_node_only=True)
        self.assertTrue(link_module.jumps_to_node_only(node))

    def test_jumps_to_node_only_false_when_unticked(self):
        node = _make_anchor_stub(jump_node_only=False)
        self.assertFalse(link_module.jumps_to_node_only(node))


# ---------------------------------------------------------------------------
# Anchor creation paths
# ---------------------------------------------------------------------------

class TestNewAnchorsCarryCheckbox(unittest.TestCase):
    """Both anchor tiers must offer the toggle as soon as they are created."""

    def setUp(self):
        _ensure_stub_modules()
        importlib.reload(link_module)
        importlib.reload(anchor)

    def test_create_anchor_named_adds_checkbox(self):
        """create_anchor_named() gives the NoOp anchor the jump-scope checkbox."""
        import nuke as nuke_stub
        created = _make_anchor_stub(name='NoOp1')
        nuke_stub.createNode = MagicMock(return_value=created)

        with patch.object(anchor, 'find_anchor_color', return_value=0):
            result = anchor.create_anchor_named('Foo')

        self.assertIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, result.knobs())
        self.assertFalse(link_module.jumps_to_node_only(result))

    def test_mark_dot_as_anchor_adds_checkbox(self):
        """mark_dot_as_anchor() gives the Dot anchor the jump-scope checkbox."""
        dot_node = _make_anchor_stub(name='Dot1', node_class='Dot')
        link_module.mark_dot_as_anchor(dot_node)
        self.assertIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, dot_node.knobs())

    def test_mark_dot_as_anchor_backfills_existing_dot_anchor(self):
        """Re-labelling an older Dot anchor backfills the checkbox."""
        import nuke as nuke_stub
        dot_node = _make_anchor_stub(name=DOT_ANCHOR_PREFIX + 'Foo', node_class='Dot')
        dot_node.addKnob(nuke_stub.StubKnob(True, knob_name=DOT_ANCHOR_KNOB_NAME))

        link_module.mark_dot_as_anchor(dot_node)

        self.assertIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, dot_node.knobs())


# ---------------------------------------------------------------------------
# navigate_to_anchor() framing
# ---------------------------------------------------------------------------

class TestNavigateHonoursJumpScope(unittest.TestCase):
    """navigate_to_anchor() frames the tree or the anchor alone, per the knob."""

    def setUp(self):
        _ensure_stub_modules()
        importlib.reload(link_module)
        importlib.reload(anchor)
        import nuke as nuke_stub
        nuke_stub.zoom = MagicMock(return_value=1.0)
        nuke_stub.center = MagicMock(return_value=[0.0, 0.0])
        nuke_stub.zoomToFitSelected.reset_mock(side_effect=True)
        nuke_stub.selectedNodes.reset_mock()
        nuke_stub.selectedNodes.return_value = []

    def tearDown(self):
        import nuke as nuke_stub
        nuke_stub.zoom = MagicMock(return_value=1.0)
        nuke_stub.center = MagicMock(return_value=[0.0, 0.0])
        nuke_stub.zoomToFitSelected.reset_mock(side_effect=True)

    def test_node_only_anchor_centres_at_fixed_zoom(self):
        """A ticked anchor is centred at NODE_ONLY_JUMP_ZOOM on the node's centre."""
        import nuke as nuke_stub
        anchor_node = _make_anchor_stub(xpos=100, ypos=200, jump_node_only=True)

        anchor.navigate_to_anchor(anchor_node)

        expected_center = [
            100 + anchor_node.screenWidth() / 2.0,
            200 + anchor_node.screenHeight() / 2.0,
        ]
        nuke_stub.zoom.assert_called_once_with(NODE_ONLY_JUMP_ZOOM, expected_center)

    def test_node_only_anchor_does_not_fit_the_tree(self):
        """A ticked anchor must not select or fit its upstream nodes."""
        import nuke as nuke_stub
        anchor_node = _make_anchor_stub(jump_node_only=True)

        with patch.object(anchor, 'upstream_ignoring_hidden') as mock_upstream:
            anchor.navigate_to_anchor(anchor_node)

        mock_upstream.assert_not_called()
        nuke_stub.zoomToFitSelected.assert_not_called()
        self.assertFalse(anchor_node['selected'].value(),
                         msg="node-only jumps must leave the selection untouched")

    def test_node_only_dot_anchor_skips_the_module_margin(self):
        """A ticked Dot anchor gets the fixed zoom, not the module margin zoom-out."""
        import nuke as nuke_stub
        anchor_node = _make_anchor_stub(
            name=DOT_ANCHOR_PREFIX + 'Foo', node_class='Dot', jump_node_only=True
        )

        anchor.navigate_to_anchor(anchor_node)

        setter_calls = [c for c in nuke_stub.zoom.call_args_list if c.args]
        self.assertEqual(len(setter_calls), 1,
                         msg="a node-only jump applies exactly one zoom")
        self.assertEqual(setter_calls[0].args[0], NODE_ONLY_JUMP_ZOOM)

    def test_unticked_anchor_still_fits_the_tree(self):
        """An unticked anchor keeps the existing zoomToFitSelected framing."""
        import nuke as nuke_stub
        anchor_node = _make_anchor_stub(name=ANCHOR_PREFIX + 'Foo', jump_node_only=False)

        with patch.object(anchor, 'upstream_ignoring_hidden', return_value=set()):
            anchor.navigate_to_anchor(anchor_node)

        nuke_stub.zoomToFitSelected.assert_called_once()

    def test_legacy_anchor_without_knob_still_fits_the_tree(self):
        """An anchor with no checkbox at all behaves exactly as it did before."""
        import nuke as nuke_stub
        anchor_node = _make_anchor_stub(name=ANCHOR_PREFIX + 'Foo')

        with patch.object(anchor, 'upstream_ignoring_hidden', return_value=set()):
            anchor.navigate_to_anchor(anchor_node)

        nuke_stub.zoomToFitSelected.assert_called_once()

    def test_jump_to_selected_anchor_uses_node_only_framing(self):
        """Alt+J from a link lands on a ticked anchor without framing its tree."""
        import nuke as nuke_stub

        import prefs as prefs_module
        prefs_module.plugin_enabled = True
        anchor_node = _make_anchor_stub(xpos=10, ypos=20, jump_node_only=True)
        link_node = _make_anchor_stub(name='Link1')
        nuke_stub.selectedNodes.return_value = [link_node]

        with patch.object(anchor, 'is_link', return_value=True), \
             patch.object(anchor, 'find_anchor_node', return_value=anchor_node):
            anchor.jump_to_selected_anchor()

        nuke_stub.zoomToFitSelected.assert_not_called()
        self.assertIsNotNone(anchor._back_position,
                             "the viewport must still be saved for Alt+Z")


# ---------------------------------------------------------------------------
# The jump-scope backfill inside migrations.migrate_script()
# ---------------------------------------------------------------------------

class TestBackfillJumpScopeKnobs(unittest.TestCase):
    """Anchors in older scripts pick up the checkbox on script load."""

    def setUp(self):
        _ensure_stub_modules()
        importlib.reload(link_module)
        importlib.reload(migrations)

    def _run_backfill(self, nodes):
        return sum(migrations._backfill_jump_scope_knob(node) for node in nodes)

    def test_backfills_anchor_without_checkbox(self):
        anchor_node = _make_anchor_stub(name=ANCHOR_PREFIX + 'Foo')

        updated = self._run_backfill([anchor_node])

        self.assertEqual(updated, 1)
        self.assertIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, anchor_node.knobs())

    def test_backfilled_checkbox_is_unticked(self):
        """Backfilled anchors keep the framing they already had."""
        anchor_node = _make_anchor_stub(name=ANCHOR_PREFIX + 'Foo')

        self._run_backfill([anchor_node])

        self.assertFalse(link_module.jumps_to_node_only(anchor_node))

    def test_skips_non_anchor_nodes(self):
        plain_node = _make_anchor_stub(name='Grade1')

        updated = self._run_backfill([plain_node])

        self.assertEqual(updated, 0)
        self.assertNotIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, plain_node.knobs())

    def test_is_idempotent(self):
        """A second load leaves the ticked state alone and reports no updates."""
        anchor_node = _make_anchor_stub(name=ANCHOR_PREFIX + 'Foo', jump_node_only=True)

        updated = self._run_backfill([anchor_node])

        self.assertEqual(updated, 0)
        self.assertTrue(link_module.jumps_to_node_only(anchor_node))

    def test_migrate_script_backfills_in_a_single_graph_pass(self):
        """Script load backfills the checkbox without a second full-graph scan."""
        anchor_node = _make_anchor_stub(name=ANCHOR_PREFIX + 'Foo')
        plain_node = _make_anchor_stub(name='Grade1')

        with patch.object(migrations.nuke, 'allNodes',
                          return_value=[anchor_node, plain_node]) as mock_all_nodes:
            migrations.migrate_script()

        mock_all_nodes.assert_called_once_with(recurseGroups=True)
        self.assertIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, anchor_node.knobs())
        self.assertNotIn(ANCHOR_JUMP_NODE_ONLY_KNOB_NAME, plain_node.knobs())


if __name__ == '__main__':
    unittest.main()
