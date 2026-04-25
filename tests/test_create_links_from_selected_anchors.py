"""Tests for create_links_from_selected_anchors() in anchor.py.

Covers:
- No-op when prefs.plugin_enabled is False
- No-op when the selection contains no anchors
- create_from_anchor() is called once per selected anchor
- Each created link node has setXYpos() called with the correct coordinates
- Non-anchor nodes in the selection are filtered out and ignored
"""

import unittest
from unittest.mock import MagicMock, patch, call

from constants import ANCHOR_PREFIX, KNOB_NAME
from tests.stubs import StubKnob, StubNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_anchor_node(name='Foo', xpos=100, ypos=200):
    """Return a StubNode that acts as a NoOp anchor."""
    return StubNode(
        name=ANCHOR_PREFIX + name,
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            'label': StubKnob(name),
            'tile_color': StubKnob(0),
            'selected': StubKnob(True),
        },
    )


def _make_non_anchor_node(name='Merge1', xpos=50, ypos=50):
    """Return a StubNode that is not an anchor (e.g. a plain Merge)."""
    return StubNode(
        name=name,
        node_class='Merge',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            'label': StubKnob(''),
            'tile_color': StubKnob(0),
            'selected': StubKnob(True),
        },
    )


def _make_link_node(name='NoOp1', xpos=0, ypos=0):
    """Return a StubNode representing a newly-created link node."""
    return StubNode(
        name=name,
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            'selected': StubKnob(False),
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateLinksFromSelectedAnchorsPluginDisabled(unittest.TestCase):
    """No-op when prefs.plugin_enabled is False."""

    def test_noop_when_plugin_disabled(self):
        """create_links_from_selected_anchors() returns immediately when plugin is disabled."""
        anchor_node = _make_anchor_node('Foo')

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke:
            mock_prefs.plugin_enabled = False

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

            mock_nuke.lastHitGroup.assert_not_called()
            mock_nuke.selectedNodes.assert_not_called()


class TestCreateLinksFromSelectedAnchorsNoAnchorsSelected(unittest.TestCase):
    """No-op when the selection contains no anchors."""

    def test_noop_when_selection_is_empty(self):
        """No link nodes are created when selectedNodes returns an empty list."""
        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', return_value=False), \
             patch('anchor.create_from_anchor') as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = []

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

            mock_create_from_anchor.assert_not_called()

    def test_noop_when_selection_contains_only_non_anchor_nodes(self):
        """No link nodes are created when all selected nodes are non-anchors."""
        plain_node_a = _make_non_anchor_node('Merge1')
        plain_node_b = _make_non_anchor_node('Grade1')

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', return_value=False), \
             patch('anchor.create_from_anchor') as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [plain_node_a, plain_node_b]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

            mock_create_from_anchor.assert_not_called()


class TestCreateLinksFromSelectedAnchorsCreateFromAnchorCalls(unittest.TestCase):
    """create_from_anchor() is called exactly once per selected anchor."""

    def test_single_anchor_calls_create_from_anchor_once(self):
        """A single selected anchor causes exactly one create_from_anchor() call."""
        anchor_node = _make_anchor_node('Foo', xpos=100, ypos=200)
        link_node = _make_link_node()

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', return_value=True), \
             patch('anchor.create_from_anchor', return_value=link_node) as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [anchor_node]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

            mock_create_from_anchor.assert_called_once_with(anchor_node)

    def test_multiple_anchors_calls_create_from_anchor_for_each(self):
        """Two selected anchors cause exactly two create_from_anchor() calls."""
        anchor_node_a = _make_anchor_node('Foo', xpos=100, ypos=200)
        anchor_node_b = _make_anchor_node('Bar', xpos=400, ypos=300)
        link_node_a = _make_link_node('Link1')
        link_node_b = _make_link_node('Link2')

        created_link_nodes = iter([link_node_a, link_node_b])

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', return_value=True), \
             patch('anchor.create_from_anchor', side_effect=lambda n: next(created_link_nodes)) as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [anchor_node_a, anchor_node_b]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

            self.assertEqual(mock_create_from_anchor.call_count, 2)
            mock_create_from_anchor.assert_any_call(anchor_node_a)
            mock_create_from_anchor.assert_any_call(anchor_node_b)


class TestCreateLinksFromSelectedAnchorsPositioning(unittest.TestCase):
    """Each created link node has setXYpos() called with the correct coordinates."""

    def test_link_node_positioned_to_right_of_anchor(self):
        """setXYpos is called with anchor.xpos() + anchor.screenWidth() + 20, anchor.ypos()."""
        anchor_node = _make_anchor_node('Foo', xpos=100, ypos=200)
        # anchor_node.screenWidth() returns 100 per StubNode definition
        expected_x = anchor_node.xpos() + anchor_node.screenWidth() + 20  # 100 + 100 + 20 = 220
        expected_y = anchor_node.ypos()  # 200

        link_node = _make_link_node()

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', return_value=True), \
             patch('anchor.create_from_anchor', return_value=link_node):
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [anchor_node]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

        self.assertEqual(link_node.xpos(), expected_x,
                         f"Link xpos should be {expected_x}, got {link_node.xpos()}")
        self.assertEqual(link_node.ypos(), expected_y,
                         f"Link ypos should be {expected_y}, got {link_node.ypos()}")

    def test_each_link_node_positioned_relative_to_its_own_anchor(self):
        """When multiple anchors are selected, each link is positioned next to its own anchor."""
        anchor_node_a = _make_anchor_node('Foo', xpos=100, ypos=50)
        anchor_node_b = _make_anchor_node('Bar', xpos=500, ypos=300)
        link_node_a = _make_link_node('Link1')
        link_node_b = _make_link_node('Link2')

        link_nodes_by_anchor = {
            id(anchor_node_a): link_node_a,
            id(anchor_node_b): link_node_b,
        }

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', return_value=True), \
             patch('anchor.create_from_anchor', side_effect=lambda n: link_nodes_by_anchor[id(n)]):
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [anchor_node_a, anchor_node_b]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

        # anchor_node_a: xpos=100, screenWidth=100 → link xpos = 220, ypos = 50
        self.assertEqual(link_node_a.xpos(), 220)
        self.assertEqual(link_node_a.ypos(), 50)

        # anchor_node_b: xpos=500, screenWidth=100 → link xpos = 620, ypos = 300
        self.assertEqual(link_node_b.xpos(), 620)
        self.assertEqual(link_node_b.ypos(), 300)


class TestCreateLinksFromSelectedAnchorsFiltersNonAnchors(unittest.TestCase):
    """Non-anchor nodes in a mixed selection are filtered out and ignored."""

    def test_non_anchor_nodes_are_ignored(self):
        """Only anchor nodes trigger create_from_anchor(); plain nodes are skipped."""
        anchor_node = _make_anchor_node('Foo', xpos=100, ypos=200)
        plain_node = _make_non_anchor_node('Merge1')
        link_node = _make_link_node()

        def is_anchor_side_effect(node):
            return node.name().startswith(ANCHOR_PREFIX)

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', side_effect=is_anchor_side_effect), \
             patch('anchor.create_from_anchor', return_value=link_node) as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [anchor_node, plain_node]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

        # Only the anchor node should have triggered a create_from_anchor call
        mock_create_from_anchor.assert_called_once_with(anchor_node)

    def test_mixed_selection_with_multiple_anchors_and_non_anchors(self):
        """Two anchors and two plain nodes: create_from_anchor called exactly twice."""
        anchor_node_a = _make_anchor_node('Foo', xpos=100, ypos=50)
        anchor_node_b = _make_anchor_node('Bar', xpos=300, ypos=50)
        plain_node_a = _make_non_anchor_node('Merge1')
        plain_node_b = _make_non_anchor_node('Grade1')
        link_node_a = _make_link_node('Link1')
        link_node_b = _make_link_node('Link2')

        link_nodes_by_anchor = {
            id(anchor_node_a): link_node_a,
            id(anchor_node_b): link_node_b,
        }

        def is_anchor_side_effect(node):
            return node.name().startswith(ANCHOR_PREFIX)

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.is_anchor', side_effect=is_anchor_side_effect), \
             patch('anchor.create_from_anchor', side_effect=lambda n: link_nodes_by_anchor[id(n)]) as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = [anchor_node_a, plain_node_a, anchor_node_b, plain_node_b]

            import anchor as anchor_module
            anchor_module.create_links_from_selected_anchors()

        self.assertEqual(mock_create_from_anchor.call_count, 2)
        mock_create_from_anchor.assert_any_call(anchor_node_a)
        mock_create_from_anchor.assert_any_call(anchor_node_b)


if __name__ == '__main__':
    unittest.main()
