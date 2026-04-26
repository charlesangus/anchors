"""Tests for labels.py — label-shortcut commands and the shared preamble.

Covers:
- create_large_label happy path: dot font size + node font size applied
- create_medium_label happy path: dot font size only (non-Dot unchanged)
- create_small_label happy path: dot font size only (non-Dot unchanged)
- append_to_label happy path: suffix appended to existing label
- User cancel (nuke.getInput returns None) → no mutation for all four
- Plugin disabled → no mutation for all four
- Empty selection → no mutation
- Dot anchor: applying a label propagates label to all link nodes referencing it
"""

import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_dot_node(name='Dot1', label='', font_size=0):
    """Return a Dot StubNode with label and note_font_size knobs."""
    import nuke as _nuke
    return _nuke.StubNode(
        name=name,
        node_class='Dot',
        knobs_dict={
            'label': _nuke.StubKnob(label),
            'note_font_size': _nuke.StubKnob(font_size),
            'tile_color': _nuke.StubKnob(0),
        }
    )


def _make_non_dot_node(name='NoOp1', node_class='NoOp', label='', font_size=0):
    """Return a non-Dot StubNode with label and note_font_size knobs."""
    import nuke as _nuke
    return _nuke.StubNode(
        name=name,
        node_class=node_class,
        knobs_dict={
            'label': _nuke.StubKnob(label),
            'note_font_size': _nuke.StubKnob(font_size),
        }
    )


def _make_link_node(knob_name_value='', label='', font_size=0):
    """Return a NoOp StubNode that looks like a link node (has KNOB_NAME knob)."""
    import nuke as _nuke
    from constants import KNOB_NAME
    return _nuke.StubNode(
        name='LinkNoOp',
        node_class='NoOp',
        knobs_dict={
            KNOB_NAME: _nuke.StubKnob(knob_name_value),
            'label': _nuke.StubKnob(label),
            'note_font_size': _nuke.StubKnob(font_size),
        }
    )


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

class TestCreateLargeLabelHappyPath(unittest.TestCase):
    """create_large_label() applies entered text and large font sizing."""

    def test_create_large_label_on_dot_sets_label_and_dot_large_font_size(self):
        import nuke as _nuke
        from constants import DOT_LABEL_FONT_SIZE_LARGE

        dot_node = _make_dot_node(name='Dot1', label='')
        _nuke.selectedNodes = MagicMock(return_value=[dot_node])
        _nuke.getInput = MagicMock(return_value='HelloLabel')
        _nuke.allNodes = MagicMock(return_value=[dot_node])

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs, \
             patch('labels.mark_dot_as_anchor'), \
             patch('labels._update_dot_link_labels'):
            mock_prefs.plugin_enabled = True
            from labels import create_large_label
            create_large_label()

        self.assertEqual(dot_node['label'].getValue(), 'HelloLabel')
        self.assertEqual(dot_node['note_font_size'].getValue(), DOT_LABEL_FONT_SIZE_LARGE)

    def test_create_large_label_on_non_dot_sets_label_and_node_large_font_size(self):
        import nuke as _nuke
        from constants import NODE_LABEL_FONT_SIZE_LARGE

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp')
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        _nuke.getInput = MagicMock(return_value='WorldLabel')

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            from labels import create_large_label
            create_large_label()

        self.assertEqual(non_dot_node['label'].getValue(), 'WorldLabel')
        self.assertEqual(non_dot_node['note_font_size'].getValue(), NODE_LABEL_FONT_SIZE_LARGE)


class TestCreateMediumLabelHappyPath(unittest.TestCase):
    """create_medium_label() applies medium dot font size; non-Dot font_size untouched."""

    def test_create_medium_label_on_dot_sets_dot_medium_font_size(self):
        import nuke as _nuke
        from constants import DOT_LABEL_FONT_SIZE_MEDIUM

        dot_node = _make_dot_node(name='Dot1', label='')
        _nuke.selectedNodes = MagicMock(return_value=[dot_node])
        _nuke.getInput = MagicMock(return_value='Medium')
        _nuke.allNodes = MagicMock(return_value=[dot_node])

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs, \
             patch('labels.mark_dot_as_anchor'), \
             patch('labels._update_dot_link_labels'):
            mock_prefs.plugin_enabled = True
            from labels import create_medium_label
            create_medium_label()

        self.assertEqual(dot_node['label'].getValue(), 'Medium')
        self.assertEqual(dot_node['note_font_size'].getValue(), DOT_LABEL_FONT_SIZE_MEDIUM)

    def test_create_medium_label_on_non_dot_sets_label_but_not_font_size(self):
        """Non-Dot nodes do not get a node font size in create_medium_label.

        Note: this matches CURRENT behaviour — the original code passes None as
        node_font_size, so non-Dot note_font_size is left at its previous value.
        """
        import nuke as _nuke

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp', font_size=42)
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        _nuke.getInput = MagicMock(return_value='Medium')

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            from labels import create_medium_label
            create_medium_label()

        self.assertEqual(non_dot_node['label'].getValue(), 'Medium')
        self.assertEqual(
            non_dot_node['note_font_size'].getValue(), 42,
            "Non-Dot note_font_size must remain unchanged for create_medium_label"
        )


class TestCreateSmallLabelHappyPath(unittest.TestCase):
    """create_small_label() applies small dot font size; non-Dot font_size untouched."""

    def test_create_small_label_on_dot_sets_dot_small_font_size(self):
        import nuke as _nuke
        from constants import DOT_LABEL_FONT_SIZE_SMALL

        dot_node = _make_dot_node(name='Dot1', label='')
        _nuke.selectedNodes = MagicMock(return_value=[dot_node])
        _nuke.getInput = MagicMock(return_value='Small')
        _nuke.allNodes = MagicMock(return_value=[dot_node])

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs, \
             patch('labels.mark_dot_as_anchor'), \
             patch('labels._update_dot_link_labels'):
            mock_prefs.plugin_enabled = True
            from labels import create_small_label
            create_small_label()

        self.assertEqual(dot_node['label'].getValue(), 'Small')
        self.assertEqual(dot_node['note_font_size'].getValue(), DOT_LABEL_FONT_SIZE_SMALL)

    def test_create_small_label_on_non_dot_sets_label_but_not_font_size(self):
        """Non-Dot nodes do not get a node font size in create_small_label."""
        import nuke as _nuke

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp', font_size=99)
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        _nuke.getInput = MagicMock(return_value='Small')

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            from labels import create_small_label
            create_small_label()

        self.assertEqual(non_dot_node['label'].getValue(), 'Small')
        self.assertEqual(non_dot_node['note_font_size'].getValue(), 99)


class TestAppendToLabelHappyPath(unittest.TestCase):
    """append_to_label() appends entered text to existing label.

    Note: the dialog default is empty string (NOT the existing label) — only the
    final label-set call concatenates existing + entered. This matches CURRENT
    behaviour in labels.py.
    """

    def test_append_to_label_appends_entered_suffix_to_existing_label(self):
        import nuke as _nuke

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp', label='Hello')
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        _nuke.getInput = MagicMock(return_value=' World')

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            from labels import append_to_label
            append_to_label()

        self.assertEqual(non_dot_node['label'].getValue(), 'Hello World')

    def test_append_to_label_uses_empty_string_as_dialog_default(self):
        """append_to_label() must call nuke.getInput with default '' regardless of existing label."""
        import nuke as _nuke

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp', label='Existing')
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        get_input_mock = MagicMock(return_value='')
        _nuke.getInput = get_input_mock

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            from labels import append_to_label
            append_to_label()

        # The dialog default for append_to_label is '', not the existing label
        get_input_mock.assert_called_once_with("Append to label:", "")


# ---------------------------------------------------------------------------
# User cancels (nuke.getInput returns None)
# ---------------------------------------------------------------------------

class TestUserCancelNoMutation(unittest.TestCase):
    """When nuke.getInput returns None (user cancelled), no node knob is mutated."""

    def _run_with_cancel_and_assert_unchanged(self, command_name):
        import nuke as _nuke
        import labels

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp',
                                          label='Original', font_size=21)
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        _nuke.getInput = MagicMock(return_value=None)  # user cancelled

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            command = getattr(labels, command_name)
            command()

        self.assertEqual(
            non_dot_node['label'].getValue(), 'Original',
            f"{command_name}: label must remain unchanged after user cancel"
        )
        self.assertEqual(
            non_dot_node['note_font_size'].getValue(), 21,
            f"{command_name}: note_font_size must remain unchanged after user cancel"
        )

    def test_create_large_label_user_cancel_no_mutation(self):
        self._run_with_cancel_and_assert_unchanged('create_large_label')

    def test_create_medium_label_user_cancel_no_mutation(self):
        self._run_with_cancel_and_assert_unchanged('create_medium_label')

    def test_create_small_label_user_cancel_no_mutation(self):
        self._run_with_cancel_and_assert_unchanged('create_small_label')

    def test_append_to_label_user_cancel_no_mutation(self):
        self._run_with_cancel_and_assert_unchanged('append_to_label')


# ---------------------------------------------------------------------------
# Plugin disabled
# ---------------------------------------------------------------------------

class TestPluginDisabledNoMutation(unittest.TestCase):
    """When prefs.plugin_enabled is False, no node knob is mutated and no dialog opens."""

    def _run_with_plugin_disabled_and_assert_unchanged(self, command_name):
        import nuke as _nuke
        import labels

        non_dot_node = _make_non_dot_node(name='NoOp1', node_class='NoOp',
                                          label='Original', font_size=21)
        _nuke.selectedNodes = MagicMock(return_value=[non_dot_node])
        get_input_mock = MagicMock(return_value='ShouldNotMatter')
        _nuke.getInput = get_input_mock

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = False
            command = getattr(labels, command_name)
            command()

        self.assertEqual(
            non_dot_node['label'].getValue(), 'Original',
            f"{command_name}: label must remain unchanged when plugin disabled"
        )
        self.assertEqual(
            non_dot_node['note_font_size'].getValue(), 21,
            f"{command_name}: note_font_size must remain unchanged when plugin disabled"
        )
        get_input_mock.assert_not_called()

    def test_create_large_label_plugin_disabled_no_mutation(self):
        self._run_with_plugin_disabled_and_assert_unchanged('create_large_label')

    def test_create_medium_label_plugin_disabled_no_mutation(self):
        self._run_with_plugin_disabled_and_assert_unchanged('create_medium_label')

    def test_create_small_label_plugin_disabled_no_mutation(self):
        self._run_with_plugin_disabled_and_assert_unchanged('create_small_label')

    def test_append_to_label_plugin_disabled_no_mutation(self):
        self._run_with_plugin_disabled_and_assert_unchanged('append_to_label')


# ---------------------------------------------------------------------------
# Empty selection
# ---------------------------------------------------------------------------

class TestEmptySelectionNoMutation(unittest.TestCase):
    """When nuke.selectedNodes() returns [], no dialog opens and no mutation happens."""

    def _run_with_empty_selection(self, command_name):
        import nuke as _nuke
        import labels

        _nuke.selectedNodes = MagicMock(return_value=[])
        get_input_mock = MagicMock(return_value='ShouldNotMatter')
        _nuke.getInput = get_input_mock

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs:
            mock_prefs.plugin_enabled = True
            command = getattr(labels, command_name)
            command()

        get_input_mock.assert_not_called()

    def test_create_large_label_empty_selection_no_mutation(self):
        self._run_with_empty_selection('create_large_label')

    def test_create_medium_label_empty_selection_no_mutation(self):
        self._run_with_empty_selection('create_medium_label')

    def test_create_small_label_empty_selection_no_mutation(self):
        self._run_with_empty_selection('create_small_label')

    def test_append_to_label_empty_selection_no_mutation(self):
        self._run_with_empty_selection('append_to_label')


# ---------------------------------------------------------------------------
# Dot anchor link propagation
# ---------------------------------------------------------------------------

class TestDotAnchorLabelPropagatesToLinkNodes(unittest.TestCase):
    """Applying a label to a Dot anchor must propagate to all link nodes referencing it."""

    def test_create_large_label_on_dot_propagates_label_to_link_nodes(self):
        """When a Dot receives a large label, link nodes pointing to it get 'Link: <text>'."""
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_LINK_LABEL_FONT_SIZE

        anchor_fqnn = 'myScript.Anchor_Dot_NewLabel'

        dot_node = _make_dot_node(name='Anchor_Dot_OldLabel', label='OldLabel')

        link_node_matching = _make_link_node(
            knob_name_value=anchor_fqnn,
            label='Link: OldLabel',
        )
        link_node_unrelated = _make_link_node(
            knob_name_value='myScript.Anchor_Dot_Other',
            label='Link: Other',
        )

        _nuke.selectedNodes = MagicMock(return_value=[dot_node])
        _nuke.getInput = MagicMock(return_value='NewLabel')
        _nuke.allNodes = MagicMock(return_value=[dot_node, link_node_matching,
                                                 link_node_unrelated])

        def is_link_stub(node):
            return KNOB_NAME in node.knobs()

        def is_anchor_stub(node):
            return node is dot_node

        with patch('labels.nuke', _nuke), \
             patch('labels.prefs') as mock_prefs, \
             patch('labels.mark_dot_as_anchor'), \
             patch('labels.is_link', side_effect=is_link_stub), \
             patch('labels.is_anchor', side_effect=is_anchor_stub), \
             patch('labels.get_fully_qualified_node_name', return_value=anchor_fqnn), \
             patch('labels.reconnect_link_node') as mock_reconnect:
            from labels import create_large_label
            create_large_label()

        # The matching link node received the propagated label
        self.assertEqual(
            link_node_matching['label'].getValue(), 'Link: NewLabel',
            "Matching link node label must be updated to 'Link: NewLabel'"
        )
        self.assertEqual(
            link_node_matching['note_font_size'].getValue(), DOT_LINK_LABEL_FONT_SIZE,
            "Matching link node note_font_size must be set to DOT_LINK_LABEL_FONT_SIZE"
        )
        # The unrelated link node was NOT modified
        self.assertEqual(
            link_node_unrelated['label'].getValue(), 'Link: Other',
            "Unrelated link node label must remain unchanged"
        )
        # reconnect_link_node was called for the matching link node
        mock_reconnect.assert_called_once_with(link_node_matching)


if __name__ == '__main__':
    unittest.main()
