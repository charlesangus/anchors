"""Tests for Dot anchor node name sync in mark_dot_as_anchor() and rename_anchor_to().

Covers:
- mark_dot_as_anchor() with labelled Dot: node name becomes 'Dot_<sanitized_label>'
- mark_dot_as_anchor() with empty-label Dot: node name unchanged
- mark_dot_as_anchor() called twice on same node: idempotent (knob guard fires, name still correct)
- rename_anchor_to() Dot anchor: label updated
- rename_anchor_to() Dot anchor: node name updated to 'Dot_<sanitized>'
- rename_anchor_to() Dot anchor: old FQNN in link nodes updated to new FQNN
- rename_anchor_to() Dot anchor with name that sanitizes to empty: raises ValueError
- anchor_display_name() for Dot still returns label (not derived from node name)
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


def _make_dot_node(name='Dot1', label=''):
    """Return a Dot StubNode with a label and tile_color knob set."""
    import nuke as _nuke
    return _nuke.StubNode(
        name=name,
        node_class='Dot',
        knobs_dict={
            'label': _nuke.StubKnob(label),
            'tile_color': _nuke.StubKnob(0),
        }
    )


def _make_link_node(knob_name_value='', label=''):
    """Return a NoOp StubNode that looks like a link node (has KNOB_NAME knob)."""
    import nuke as _nuke
    from constants import KNOB_NAME
    return _nuke.StubNode(
        name='NoOp1',
        node_class='NoOp',
        knobs_dict={
            KNOB_NAME: _nuke.StubKnob(knob_name_value),
            'label': _nuke.StubKnob(label),
        }
    )


# ---------------------------------------------------------------------------
# Tests for mark_dot_as_anchor() — node name sync
# ---------------------------------------------------------------------------

class TestMarkDotAsAnchorNameSync(unittest.TestCase):
    """mark_dot_as_anchor() must sync the Dot node name to 'Dot_<sanitized_label>'."""

    def test_mark_dot_as_anchor_with_labelled_dot_sets_node_name_to_dot_prefix_plus_sanitized_label(self):
        """mark_dot_as_anchor() on a Dot with label 'My Footage' must set node name to 'Dot_My_Footage'."""
        import nuke as _nuke
        from constants import DOT_ANCHOR_KNOB_NAME, DOT_ANCHOR_PREFIX

        dot_node = _make_dot_node(name='Dot1', label='My Footage')

        stub_boolean_knob = _nuke.StubKnob()
        _nuke.Boolean_Knob = MagicMock(return_value=stub_boolean_knob)

        with patch('link.nuke', _nuke):
            from link import mark_dot_as_anchor
            mark_dot_as_anchor(dot_node)

        self.assertEqual(
            dot_node.name(),
            'Dot_My_Footage',
            "mark_dot_as_anchor() must set node name to 'Dot_<sanitized_label>' when label is non-empty"
        )

    def test_mark_dot_as_anchor_with_empty_label_dot_leaves_node_name_unchanged(self):
        """mark_dot_as_anchor() on a Dot with empty label must NOT change the node name."""
        import nuke as _nuke

        dot_node = _make_dot_node(name='Dot3', label='')

        stub_boolean_knob = _nuke.StubKnob()
        _nuke.Boolean_Knob = MagicMock(return_value=stub_boolean_knob)

        with patch('link.nuke', _nuke):
            from link import mark_dot_as_anchor
            mark_dot_as_anchor(dot_node)

        self.assertEqual(
            dot_node.name(),
            'Dot3',
            "mark_dot_as_anchor() must NOT change node name when label is empty"
        )

    def test_mark_dot_as_anchor_called_twice_is_idempotent_and_node_name_is_still_correct(self):
        """Calling mark_dot_as_anchor() twice must be idempotent.

        The second call hits the knob guard (DOT_ANCHOR_KNOB_NAME already present),
        sets the knob to True, and returns early. The node name set on the first call
        must still be 'Dot_MyClip'.
        """
        import nuke as _nuke
        from constants import DOT_ANCHOR_KNOB_NAME

        stub_anchor_knob = _nuke.StubKnob(True)
        dot_node = _nuke.StubNode(
            name='Dot1',
            node_class='Dot',
            knobs_dict={
                'label': _nuke.StubKnob('MyClip'),
                DOT_ANCHOR_KNOB_NAME: stub_anchor_knob,
            }
        )
        # Pre-set name as if the first call already renamed it
        dot_node._name = 'Dot_MyClip'

        stub_boolean_knob = _nuke.StubKnob()
        _nuke.Boolean_Knob = MagicMock(return_value=stub_boolean_knob)

        with patch('link.nuke', _nuke):
            from link import mark_dot_as_anchor
            mark_dot_as_anchor(dot_node)

        self.assertEqual(
            dot_node.name(),
            'Dot_MyClip',
            "Node name must remain 'Dot_MyClip' after idempotent second call"
        )
        # The early-return path must have set the knob value to True
        self.assertEqual(
            stub_anchor_knob.getValue(),
            True,
            "DOT_ANCHOR_KNOB_NAME knob must be set to True on second call"
        )

    def test_mark_dot_as_anchor_sets_tile_color_to_anchor_default_color(self):
        """mark_dot_as_anchor() must set tile_color to ANCHOR_DEFAULT_COLOR (purple)."""
        import nuke as _nuke
        from constants import ANCHOR_DEFAULT_COLOR

        dot_node = _make_dot_node(name='Dot1', label='My Footage')

        stub_boolean_knob = _nuke.StubKnob()
        _nuke.Boolean_Knob = MagicMock(return_value=stub_boolean_knob)

        with patch('link.nuke', _nuke):
            from link import mark_dot_as_anchor
            mark_dot_as_anchor(dot_node)

        self.assertEqual(
            dot_node['tile_color'].getValue(),
            ANCHOR_DEFAULT_COLOR,
            "mark_dot_as_anchor() must set tile_color to ANCHOR_DEFAULT_COLOR"
        )


# ---------------------------------------------------------------------------
# Tests for rename_anchor_to() Dot anchor path — node name + FQNN sync
# ---------------------------------------------------------------------------

class TestRenameAnchorToDotPath(unittest.TestCase):
    """rename_anchor_to() for Dot anchors must update node name, label, and link FQNNs."""

    def _make_dot_anchor_with_label(self, name='Dot1', label='OldName'):
        """Return a Dot StubNode that represents a Dot anchor with a label."""
        import nuke as _nuke
        return _nuke.StubNode(
            name=name,
            node_class='Dot',
            knobs_dict={
                'label': _nuke.StubKnob(label),
            }
        )

    def test_rename_anchor_to_dot_updates_label(self):
        """rename_anchor_to(dot_anchor, 'NewName') must update the Dot's label knob."""
        import nuke as _nuke

        dot_anchor = self._make_dot_anchor_with_label(name='Dot_OldName', label='OldName')

        with patch('anchor.nuke', _nuke), \
             patch('anchor.nuke.allNodes', return_value=[]), \
             patch('anchor.is_link', return_value=False), \
             patch('anchor.get_fully_qualified_node_name',
                   side_effect=['myScript.Dot_OldName', 'myScript.Dot_NewName']):
            from anchor import rename_anchor_to
            rename_anchor_to(dot_anchor, 'NewName')

        self.assertEqual(
            dot_anchor['label'].getValue(),
            'NewName',
            "rename_anchor_to() must set the Dot's label to 'NewName'"
        )

    def test_rename_anchor_to_dot_updates_node_name_to_dot_prefix_plus_sanitized(self):
        """rename_anchor_to(dot_anchor, 'New Name') must set node name to 'Dot_New_Name'."""
        import nuke as _nuke

        dot_anchor = self._make_dot_anchor_with_label(name='Dot_OldName', label='OldName')

        with patch('anchor.nuke', _nuke), \
             patch('anchor.nuke.allNodes', return_value=[]), \
             patch('anchor.is_link', return_value=False), \
             patch('anchor.get_fully_qualified_node_name',
                   side_effect=['myScript.Dot_OldName', 'myScript.Dot_New_Name']):
            from anchor import rename_anchor_to
            rename_anchor_to(dot_anchor, 'New Name')

        self.assertEqual(
            dot_anchor.name(),
            'Dot_New_Name',
            "rename_anchor_to() must set node name to 'Dot_New_Name' (sanitized)"
        )

    def test_rename_anchor_to_dot_updates_link_node_knob_name_from_old_fqnn_to_new_fqnn(self):
        """rename_anchor_to() must update KNOB_NAME on all link nodes that stored the old FQNN."""
        import nuke as _nuke
        from constants import KNOB_NAME

        dot_anchor = self._make_dot_anchor_with_label(name='Dot_OldName', label='OldName')

        old_fqnn = 'myScript.Dot_OldName'
        new_fqnn = 'myScript.Dot_NewName'

        link_node_matching = _make_link_node(knob_name_value=old_fqnn, label='Link: OldName')
        link_node_unrelated = _make_link_node(knob_name_value='myScript.Dot_OtherNode', label='Link: OtherNode')

        def is_link_stub(node):
            return KNOB_NAME in node.knobs()

        with patch('anchor.nuke', _nuke), \
             patch('anchor.nuke.allNodes', return_value=[link_node_matching, link_node_unrelated]), \
             patch('anchor.is_link', side_effect=is_link_stub), \
             patch('anchor.get_fully_qualified_node_name',
                   side_effect=[old_fqnn, new_fqnn]):
            from anchor import rename_anchor_to
            rename_anchor_to(dot_anchor, 'NewName')

        self.assertEqual(
            link_node_matching[KNOB_NAME].getValue(),
            new_fqnn,
            "Matching link node KNOB_NAME must be updated from old FQNN to new FQNN"
        )
        self.assertEqual(
            link_node_unrelated[KNOB_NAME].getValue(),
            'myScript.Dot_OtherNode',
            "Unrelated link node KNOB_NAME must remain unchanged"
        )

    def test_rename_anchor_to_dot_updates_link_node_label_to_new_name(self):
        """rename_anchor_to() must update the label of matching link nodes to 'Link: NewName'."""
        import nuke as _nuke
        from constants import KNOB_NAME

        dot_anchor = self._make_dot_anchor_with_label(name='Dot_OldName', label='OldName')

        old_fqnn = 'myScript.Dot_OldName'
        new_fqnn = 'myScript.Dot_NewName'

        link_node = _make_link_node(knob_name_value=old_fqnn, label='Link: OldName')

        def is_link_stub(node):
            return KNOB_NAME in node.knobs()

        with patch('anchor.nuke', _nuke), \
             patch('anchor.nuke.allNodes', return_value=[link_node]), \
             patch('anchor.is_link', side_effect=is_link_stub), \
             patch('anchor.get_fully_qualified_node_name',
                   side_effect=[old_fqnn, new_fqnn]):
            from anchor import rename_anchor_to
            rename_anchor_to(dot_anchor, 'NewName')

        self.assertEqual(
            link_node['label'].getValue(),
            'Link: NewName',
            "Matching link node label must be updated to 'Link: NewName'"
        )

    def test_rename_anchor_to_dot_with_name_that_sanitizes_to_empty_raises_value_error(self):
        """rename_anchor_to() with a name that sanitizes to '' must raise ValueError for Dot anchors.

        The sanitize_anchor_name() regex keeps only [A-Za-z0-9_], so a name consisting
        entirely of spaces (after strip() → '') produces an empty sanitized result.
        """
        import nuke as _nuke

        dot_anchor = self._make_dot_anchor_with_label(name='Dot_OldName', label='OldName')

        with patch('anchor.nuke', _nuke), \
             patch('anchor.nuke.allNodes', return_value=[]), \
             patch('anchor.is_link', return_value=False), \
             patch('anchor.get_fully_qualified_node_name',
                   return_value='myScript.Dot_OldName'):
            from anchor import rename_anchor_to
            with self.assertRaises(ValueError):
                # A name of only spaces: strip() → '', sanitize → '' → ValueError
                rename_anchor_to(dot_anchor, '   ')


# ---------------------------------------------------------------------------
# Tests for anchor_display_name() — must remain label-based for Dot anchors
# ---------------------------------------------------------------------------

class TestAnchorDisplayNameDotPath(unittest.TestCase):
    """anchor_display_name() must still return label text for Dot anchors, not node name."""

    def test_anchor_display_name_returns_label_for_dot_anchor_with_dot_prefix_node_name(self):
        """anchor_display_name() on a Dot with node name 'Dot_MyFootage' must return the label, not the node name."""
        import nuke as _nuke

        dot_anchor = _nuke.StubNode(
            name='Dot_MyFootage',
            node_class='Dot',
            knobs_dict={
                'label': _nuke.StubKnob('MyFootage'),
            }
        )

        with patch('anchor.nuke', _nuke):
            from anchor import anchor_display_name
            display_name = anchor_display_name(dot_anchor)

        self.assertEqual(
            display_name,
            'MyFootage',
            "anchor_display_name() must return the label text for Dot anchors, not the node name"
        )

    def test_anchor_display_name_returns_label_for_dot_anchor_with_spaces_in_label(self):
        """anchor_display_name() must return the label with spaces preserved."""
        import nuke as _nuke

        dot_anchor = _nuke.StubNode(
            name='Dot_My_Footage',
            node_class='Dot',
            knobs_dict={
                'label': _nuke.StubKnob('My Footage'),
            }
        )

        with patch('anchor.nuke', _nuke):
            from anchor import anchor_display_name
            display_name = anchor_display_name(dot_anchor)

        self.assertEqual(
            display_name,
            'My Footage',
            "anchor_display_name() must return label text 'My Footage' (spaces preserved)"
        )


# ---------------------------------------------------------------------------
# Regression: re-labelling a Dot anchor that has KNOB_NAME (from copy_anchors)
# must not cause _update_dot_link_labels to overwrite the anchor's own label
# ---------------------------------------------------------------------------

class TestApplyLabelDoesNotTreatAnchorAsLink(unittest.TestCase):
    """_update_dot_link_labels must skip anchor nodes even when they have KNOB_NAME."""

    def test_relabelling_dot_anchor_with_knob_name_does_not_set_link_label_on_anchor(self):
        """After copy_anchors adds KNOB_NAME to a Dot anchor, re-labelling it must not
        cause _update_dot_link_labels to match the anchor as a link node and overwrite
        its label with 'Link: bla bla'.

        Regression for: copy_anchors dot → paste → re-label original → original gets 'Link: ' prefix.
        """
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_ANCHOR_KNOB_NAME

        anchor_fqnn = 'myScript.Dot_bla_bla'

        # Original Dot anchor: has DOT_ANCHOR_KNOB_NAME (anchor) AND KNOB_NAME (added
        # by copy_anchors Path C), with KNOB_NAME pointing to its own FQNN.
        original_anchor = _nuke.StubNode(
            name='Dot_bla_bla',
            node_class='Dot',
            knobs_dict={
                'label': _nuke.StubKnob('bla bla'),
                'tile_color': _nuke.StubKnob(0),
                'note_font_size': _nuke.StubKnob(0),
                DOT_ANCHOR_KNOB_NAME: _nuke.StubKnob(True),
                KNOB_NAME: _nuke.StubKnob(anchor_fqnn),
            }
        )

        # Separate Dot link: legitimately points to the anchor.
        link_dot = _nuke.StubNode(
            name='Dot2',
            node_class='Dot',
            knobs_dict={
                'label': _nuke.StubKnob('Link: bla bla'),
                'note_font_size': _nuke.StubKnob(0),
                KNOB_NAME: _nuke.StubKnob(anchor_fqnn),
            }
        )

        stub_boolean_knob = _nuke.StubKnob()
        _nuke.Boolean_Knob = MagicMock(return_value=stub_boolean_knob)

        root_obj = MagicMock()
        root_obj.name.return_value = 'myScript.nk'
        _nuke.root = MagicMock(return_value=root_obj)

        with patch('link.nuke', _nuke), \
             patch('labels.nuke', _nuke), \
             patch('labels.nuke.allNodes', return_value=[original_anchor, link_dot]), \
             patch('labels.reconnect_link_node') as mock_reconnect:
            from labels import _apply_label
            _apply_label(original_anchor, 'bla bla')

        # The anchor's label must remain 'bla bla', not become 'Link: bla bla'.
        self.assertEqual(
            original_anchor['label'].getValue(),
            'bla bla',
            "Re-labelling a Dot anchor must not set its label to 'Link: bla bla'"
        )

        # reconnect_link_node must NOT have been called on the anchor.
        for call_args in mock_reconnect.call_args_list:
            called_node = call_args[0][0]
            self.assertIsNot(
                called_node,
                original_anchor,
                "reconnect_link_node must not be called on an anchor node"
            )


if __name__ == '__main__':
    unittest.main()
