"""Unit tests for link.find_anchor_node().

These tests call the real find_anchor_node() implementation directly, using
StubNodes and a patched nuke module.  Every other test file that exercises
find_anchor_node() does so indirectly via paste_anchors() with the function
mocked out — these tests provide the direct coverage for the function itself.

Coverage:
  - Current (single-segment) FQNN format
  - Legacy two-segment stem-prefix format (scriptStem.Anchor_Foo)
  - Very-old filesystem-path prefix format (/path/to/script.Anchor_Foo)
  - Empty stored name
  - Unresolvable name (orphaned reference)
  - Group-context guard: same-group link resolves same-group anchor
  - Group-context guard: root link cannot resolve group anchor
  - Group-context guard: group link cannot resolve different-group anchor
  - Group-context guard: group link cannot resolve root anchor
  - Legacy stem-prefix format for group-qualified anchor
"""

import unittest
from unittest.mock import patch

from constants import KNOB_NAME
from tests.stubs import StubKnob, StubNode


def _make_link_node(stored_fqnn, full_name='NoOp1', node_class='NoOp'):
    """Return a stub link node with KNOB_NAME set to stored_fqnn.

    full_name is used as both name() and fullName() via StubNode._name.
    """
    knobs = {KNOB_NAME: StubKnob(stored_fqnn)}
    return StubNode(name=full_name, node_class=node_class, knobs_dict=knobs)


def _make_anchor_node(full_name='Anchor_Foo', node_class='NoOp'):
    """Return a stub anchor node with the given full name."""
    return StubNode(name=full_name, node_class=node_class, knobs_dict={})


# ---------------------------------------------------------------------------
# FQNN format resolution
# ---------------------------------------------------------------------------

class TestFindAnchorNodeFqnnFormats(unittest.TestCase):
    """find_anchor_node() must resolve anchors stored in any of the three
    historical FQNN formats."""

    def test_current_format_resolves_on_first_attempt(self):
        """Single-segment FQNN (current format) resolves on the first toNode call."""
        anchor = _make_anchor_node('Anchor_Foo')
        link = _make_link_node('Anchor_Foo')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIs(result, anchor)
        mock_nuke.toNode.assert_called_once_with('Anchor_Foo')

    def test_legacy_stem_format_resolves_after_stripping_first_segment(self):
        """Two-segment FQNN with a script-stem prefix resolves after the stem is stripped."""
        anchor = _make_anchor_node('Anchor_Foo')
        link = _make_link_node('scriptStem.Anchor_Foo')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIs(result, anchor)

    def test_very_old_filesystem_path_prefix_resolves_after_stripping_first_segment(self):
        """Old filesystem-path prefix (e.g. '/mnt/proj/script.Anchor_Foo') resolves
        after the first dot-segment is stripped."""
        anchor = _make_anchor_node('Anchor_Foo')
        link = _make_link_node('/mnt/proj/editorial/script_v008.Anchor_Foo')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIs(result, anchor)

    def test_empty_stored_name_returns_none_without_calling_to_node(self):
        """Empty KNOB_NAME returns None immediately and never calls nuke.toNode."""
        link = _make_link_node('')

        with patch('link.nuke') as mock_nuke:
            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIsNone(result)
        mock_nuke.toNode.assert_not_called()

    def test_unresolvable_name_returns_none(self):
        """A stored name that cannot be resolved by either toNode attempt returns None."""
        link = _make_link_node('oldScript.Anchor_Gone')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.return_value = None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Group-context guard
# ---------------------------------------------------------------------------

class TestFindAnchorNodeGroupContext(unittest.TestCase):
    """find_anchor_node() enforces group context: a link can only resolve an
    anchor that lives in the same group (same name-prefix hierarchy)."""

    def test_root_link_resolves_root_anchor(self):
        """A root-level link node resolves a root-level anchor."""
        anchor = _make_anchor_node('Anchor_Foo')
        link = _make_link_node('Anchor_Foo', full_name='NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIs(result, anchor)

    def test_group_link_resolves_same_group_anchor(self):
        """A link inside Group1 resolves an anchor that is also inside Group1."""
        anchor = _make_anchor_node('Group1.Anchor_Foo')
        link = _make_link_node('Group1.Anchor_Foo', full_name='Group1.NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Group1.Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIs(result, anchor)

    def test_root_link_cannot_resolve_group_level_anchor(self):
        """A root-level link node cannot resolve an anchor that lives inside a Group."""
        anchor = _make_anchor_node('Group1.Anchor_Foo')
        link = _make_link_node('Group1.Anchor_Foo', full_name='NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Group1.Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIsNone(result)

    def test_group_link_cannot_resolve_anchor_in_different_group(self):
        """A link inside Group2 cannot resolve an anchor that lives inside Group1."""
        anchor = _make_anchor_node('Group1.Anchor_Foo')
        link = _make_link_node('Group1.Anchor_Foo', full_name='Group2.NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Group1.Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIsNone(result)

    def test_group_link_cannot_resolve_root_level_anchor(self):
        """A link inside Group1 cannot resolve a root-level anchor."""
        anchor = _make_anchor_node('Anchor_Foo')
        link = _make_link_node('Anchor_Foo', full_name='Group1.NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIsNone(result)

    def test_legacy_stem_group_format_resolves_with_correct_group_context(self):
        """A legacy stem-prefixed FQNN for a group-level anchor resolves correctly
        when the link is in the same group after the stem is stripped."""
        anchor = _make_anchor_node('Group1.Anchor_Foo')
        link = _make_link_node('scriptStem.Group1.Anchor_Foo', full_name='Group1.NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Group1.Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIs(result, anchor)

    def test_legacy_stem_group_format_blocked_for_wrong_group_link(self):
        """A legacy stem-prefixed FQNN for a group-level anchor is blocked when the
        link is in a different group."""
        anchor = _make_anchor_node('Group1.Anchor_Foo')
        link = _make_link_node('scriptStem.Group1.Anchor_Foo', full_name='Group2.NoOp1')

        with patch('link.nuke') as mock_nuke:
            mock_nuke.toNode.side_effect = lambda name: anchor if name == 'Group1.Anchor_Foo' else None

            import link as link_module
            result = link_module.find_anchor_node(link)

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
