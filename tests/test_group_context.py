"""Tests verifying Group-context-aware node scanning.

All tests confirm that plugin operations use all_nodes_in_context() (which
passes group=nuke.thisGroup()) rather than bare nuke.allNodes(), ensuring
correct behaviour inside Group node nested DAGs.
"""

import unittest

import nuke

from tests.stubs import StubKnob, StubNode


def _restore_knob_constructors():
    """Reset nuke stub knob constructors to their original side_effects.

    Some test files replace nuke.String_Knob / nuke.Tab_Knob with custom
    MagicMock instances that don't preserve knob_name. This helper restores
    them to the canonical stub behaviour so that add_input_knob() and
    similar helpers correctly register knobs on StubNode instances.
    """
    from unittest.mock import MagicMock
    nuke.String_Knob = MagicMock(side_effect=lambda name, *args: StubKnob(knob_name=name))
    nuke.Tab_Knob = MagicMock(side_effect=lambda name, *args: StubKnob(knob_name=name))
    nuke.Boolean_Knob = MagicMock(side_effect=lambda name, *args: StubKnob(knob_name=name))


class TestAllNodesInContext(unittest.TestCase):
    """Verify all_nodes_in_context() passes group=nuke.thisGroup()."""

    def test_all_nodes_in_context_passes_group_kwarg(self):
        """all_nodes_in_context() must call nuke.allNodes(group=nuke.thisGroup())."""
        from link import all_nodes_in_context
        nuke.allNodes.reset_mock()
        nuke.allNodes.side_effect = None
        group_sentinel = nuke.thisGroup()
        all_nodes_in_context()
        nuke.allNodes.assert_called_once_with(group=group_sentinel)

    def test_all_nodes_in_context_with_class_filter(self):
        """all_nodes_in_context('BackdropNode') passes both class and group."""
        from link import all_nodes_in_context
        nuke.allNodes.reset_mock()
        nuke.allNodes.side_effect = None
        group_sentinel = nuke.thisGroup()
        all_nodes_in_context('BackdropNode')
        nuke.allNodes.assert_called_once_with('BackdropNode', group=group_sentinel)


class TestFindSmallestContainingBackdropGroupContext(unittest.TestCase):
    """Verify find_smallest_containing_backdrop uses Group-aware scanning."""

    def test_uses_all_nodes_in_context(self):
        """find_smallest_containing_backdrop must not call bare nuke.allNodes()."""
        from link import find_smallest_containing_backdrop
        node = StubNode('TestNode', xpos=50, ypos=50)
        nuke.allNodes.reset_mock()
        nuke.allNodes.side_effect = None
        find_smallest_containing_backdrop(node)
        # Verify group= kwarg was passed
        if nuke.allNodes.called:
            call_kwargs = nuke.allNodes.call_args
            assert 'group' in call_kwargs.kwargs, (
                "find_smallest_containing_backdrop must pass group= to nuke.allNodes"
            )


class TestCopyAnchorsGroupContext(unittest.TestCase):
    """Verify copy_anchors uses Group-aware anchor scanning."""

    def setUp(self):
        _restore_knob_constructors()

    def test_copy_link_source_class_scans_group_context(self):
        """copy_anchors() anchor scan must use all_nodes_in_context(), not bare nuke.allNodes()."""
        import prefs
        prefs.plugin_enabled = True
        prefs.link_classes_paste_mode = 'replace'

        from constants import LINK_SOURCE_CLASSES
        file_class = list(LINK_SOURCE_CLASSES)[0]
        file_node = StubNode('Read1', node_class=file_class, knobs_dict={
            'tile_color': StubKnob(0),
            'label': StubKnob(''),
            'selected': StubKnob(True),
            'hide_input': StubKnob(False),
        })
        nuke.selectedNodes.return_value = [file_node]
        nuke.allNodes.reset_mock()
        nuke.allNodes.side_effect = None
        nuke.allNodes.return_value = []

        from anchors import copy_anchors
        copy_anchors()

        # Verify group= kwarg was passed in the allNodes call
        if nuke.allNodes.called:
            for call in nuke.allNodes.call_args_list:
                if 'recurseGroups' not in (call.kwargs or {}):
                    assert 'group' in (call.kwargs or {}), (
                        "copy_anchors must pass group= to nuke.allNodes"
                    )


class TestLabelPropagationGroupContext(unittest.TestCase):
    """Verify _update_dot_link_labels uses Group-aware scanning."""

    def test_update_dot_link_labels_uses_group_context(self):
        """_update_dot_link_labels must use all_nodes_in_context()."""
        dot_node = StubNode('Anchor_Test', node_class='Dot', knobs_dict={
            'label': StubKnob('Test'),
            'tile_color': StubKnob(0),
            'note_font_size': StubKnob(42),
            'hide_input': StubKnob(False),
        })
        nuke.allNodes.reset_mock()
        nuke.allNodes.side_effect = None
        nuke.allNodes.return_value = []

        root_mock = nuke.root()
        root_mock.name.return_value = 'test.nk'

        from labels import _update_dot_link_labels
        _update_dot_link_labels(dot_node, 'NewLabel')

        # Verify group= kwarg was passed
        if nuke.allNodes.called:
            call_kwargs = nuke.allNodes.call_args
            assert 'group' in call_kwargs.kwargs, (
                "_update_dot_link_labels must pass group= to nuke.allNodes"
            )
