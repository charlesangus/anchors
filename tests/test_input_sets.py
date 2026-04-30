"""Tests for input_sets.py — Set B/A/Mask/First-Free Input To...

Scope:
  - Mask-input resolution heuristic (>100 maxInputs -> 2; else last input).
  - First-free-input lookup.
  - End-to-end set_input_to_b / a / mask / first_available with picker stubbed.
  - Q/W/E replace whatever was previously wired; R only fills empty slots.
  - Per-input horizontal offset so sibling links don't overlap.

The picker (anchor.pick_anchor) is patched to invoke the on_pick callback
synchronously with a stub anchor node, so tests exercise the wire-up path
without spinning up Qt or tabtabtab.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from tests.stubs import StubKnob, StubNode, make_stub_nuke_module

if 'nuke' not in sys.modules:
    sys.modules['nuke'] = make_stub_nuke_module()

import input_sets


def _make_target_node(node_class='Merge2', max_inputs=3, inputs=None, name=None):
    """Return a StubNode that mimics a Merge-style multi-input node.

    *inputs* is an optional list of length max_inputs; entries are the live
    input nodes for each slot (None means empty).
    """
    target_name = name or f'{node_class}1'
    target = StubNode(name=target_name, node_class=node_class)
    target.maxInputs = lambda: max_inputs
    target._inputs = list(inputs) if inputs is not None else [None] * max_inputs

    def _input(index):
        if 0 <= index < len(target._inputs):
            return target._inputs[index]
        return None

    def _set_input(index, node):
        while len(target._inputs) <= index:
            target._inputs.append(None)
        target._inputs[index] = node

    target.input = _input
    target.setInput = _set_input
    return target


def _make_anchor_node(name='Anchor_Foo'):
    label_knob = StubKnob(value='Foo', knob_name='label')
    return StubNode(name=name, node_class='NoOp', knobs_dict={'label': label_knob})


def _make_link_node(name='LinkNode'):
    """Stub link node that records setXYpos calls so tests can assert positioning."""
    link = StubNode(name=name, node_class='NoOp')
    # StubNode.setXYpos already records into _xpos/_ypos via setXYpos override.
    # Append the (x, y) tuple to a history list so push-up repositioning can be checked.
    link._xy_history = []
    original_set_xypos = link.setXYpos

    def _record_set_xypos(x, y):
        link._xy_history.append((x, y))
        original_set_xypos(x, y)

    link.setXYpos = _record_set_xypos
    return link


class TestResolveMaskInputIndex(unittest.TestCase):
    """Mask-input resolution: >100 maxInputs -> 2; else last input; <=1 -> None."""

    def test_merge_uses_input_2(self):
        target = _make_target_node(node_class='Merge2', max_inputs=999)
        self.assertEqual(input_sets.resolve_mask_input_index(target), 2)

    def test_two_input_node_uses_last(self):
        target = _make_target_node(node_class='Keymix', max_inputs=3)
        self.assertEqual(input_sets.resolve_mask_input_index(target), 2)

    def test_blur_with_mask_uses_last(self):
        target = _make_target_node(node_class='Blur', max_inputs=2)
        self.assertEqual(input_sets.resolve_mask_input_index(target), 1)

    def test_single_input_node_returns_none(self):
        target = _make_target_node(node_class='Roto', max_inputs=1)
        self.assertIsNone(input_sets.resolve_mask_input_index(target))

    def test_zero_input_node_returns_none(self):
        target = _make_target_node(node_class='Constant', max_inputs=0)
        self.assertIsNone(input_sets.resolve_mask_input_index(target))


class TestFirstFreeInputIndex(unittest.TestCase):
    def test_returns_zero_when_all_empty(self):
        target = _make_target_node(max_inputs=3, inputs=[None, None, None])
        self.assertEqual(input_sets._first_free_input_index(target), 0)

    def test_returns_first_gap(self):
        existing = StubNode(name='X')
        target = _make_target_node(max_inputs=3, inputs=[existing, None, None])
        self.assertEqual(input_sets._first_free_input_index(target), 1)

    def test_returns_none_when_full(self):
        existing = StubNode(name='X')
        target = _make_target_node(max_inputs=3, inputs=[existing, existing, existing])
        self.assertIsNone(input_sets._first_free_input_index(target))


class TestSetInputTo(unittest.TestCase):
    """End-to-end Set Input To B/A/Mask/First-Free with picker stubbed."""

    def setUp(self):
        self._anchor_node = _make_anchor_node()
        self._link_node = _make_link_node()

        # The picker normally calls on_pick(anchor_node, hit_group) where
        # hit_group is a Nuke group used as a context manager (`with hit_group:`).
        # MagicMock supports the context-manager protocol natively.
        self._fake_hit_group = MagicMock(name='hit_group')
        self._pick_patcher = patch(
            'input_sets.anchor.pick_anchor',
            side_effect=lambda on_pick, hit_group=None: on_pick(
                self._anchor_node, self._fake_hit_group
            ),
        )
        self._pick_patcher.start()

        # Patch create_from_anchor to return the stub link without touching nuke.
        self._create_patcher = patch(
            'input_sets.anchor.create_from_anchor',
            return_value=self._link_node,
        )
        self._create_patcher.start()

        # Plugin must be enabled for the entry points to do anything.
        self._prefs_patcher = patch('input_sets.prefs.plugin_enabled', True)
        self._prefs_patcher.start()

    def tearDown(self):
        self._pick_patcher.stop()
        self._create_patcher.stop()
        self._prefs_patcher.stop()

    def _patch_selected(self, target):
        """Patch nuke.selectedNodes() to return [target]."""
        return patch('input_sets.nuke.selectedNodes', return_value=[target])

    def test_set_input_to_b_wires_input_zero(self):
        target = _make_target_node(max_inputs=3, inputs=[None, None, None])
        with self._patch_selected(target):
            input_sets.set_input_to_b()
        self.assertIs(target.input(0), self._link_node)
        self.assertIsNone(target.input(1))
        self.assertIsNone(target.input(2))

    def test_set_input_to_a_wires_input_one(self):
        target = _make_target_node(max_inputs=3, inputs=[None, None, None])
        with self._patch_selected(target):
            input_sets.set_input_to_a()
        self.assertIsNone(target.input(0))
        self.assertIs(target.input(1), self._link_node)
        self.assertIsNone(target.input(2))

    def test_link_position_offset_scales_with_input_index(self):
        """Each subsequent input shifts the link 150px to the right."""
        target = _make_target_node(max_inputs=3, inputs=[None, None, None])
        target._xpos = 0
        target._ypos = 0
        # _xy_history starts empty.
        with self._patch_selected(target):
            input_sets.set_input_to_b()
        x_b = self._link_node._xy_history[-1][0]

        # Reset the link node so set_input_to_a uses the same starting point.
        self._link_node._xy_history.clear()
        target._inputs = [None, None, None]
        with self._patch_selected(target):
            input_sets.set_input_to_a()
        x_a = self._link_node._xy_history[-1][0]

        self.assertEqual(x_a - x_b, 150)

    def test_set_input_to_mask_uses_index_2_for_merge(self):
        target = _make_target_node(node_class='Merge2', max_inputs=999, inputs=[None, None, None])
        with self._patch_selected(target):
            input_sets.set_input_to_mask()
        self.assertIs(target.input(2), self._link_node)

    def test_set_input_to_mask_uses_last_for_blur(self):
        target = _make_target_node(node_class='Blur', max_inputs=2, inputs=[None, None])
        with self._patch_selected(target):
            input_sets.set_input_to_mask()
        self.assertIs(target.input(1), self._link_node)

    def test_set_input_to_mask_noop_for_single_input(self):
        target = _make_target_node(node_class='Roto', max_inputs=1, inputs=[None])
        with self._patch_selected(target):
            input_sets.set_input_to_mask()
        self.assertIsNone(target.input(0))

    def test_set_input_to_first_available_skips_filled_slots(self):
        existing = StubNode(name='Existing')
        target = _make_target_node(max_inputs=3, inputs=[existing, None, None])
        with self._patch_selected(target):
            input_sets.set_input_to_first_available()
        self.assertIs(target.input(0), existing)
        self.assertIs(target.input(1), self._link_node)

    def test_set_input_to_b_replaces_existing_input(self):
        """Q on a Merge whose B is already wired must REPLACE the existing input."""
        existing = StubNode(name='OldRead')
        target = _make_target_node(max_inputs=3, inputs=[existing, None, None])
        with self._patch_selected(target):
            input_sets.set_input_to_b()
        self.assertIs(target.input(0), self._link_node)
        self.assertIsNot(target.input(0), existing)

    def test_set_input_to_a_replaces_existing_input(self):
        existing = StubNode(name='OldRead')
        target = _make_target_node(max_inputs=3, inputs=[None, existing, None])
        with self._patch_selected(target):
            input_sets.set_input_to_a()
        self.assertIs(target.input(1), self._link_node)

    def test_set_input_to_mask_replaces_existing_input(self):
        existing = StubNode(name='OldMask')
        target = _make_target_node(node_class='Merge2', max_inputs=999,
                                   inputs=[None, None, existing])
        with self._patch_selected(target):
            input_sets.set_input_to_mask()
        self.assertIs(target.input(2), self._link_node)

    def test_set_input_skipped_when_no_selection(self):
        target = _make_target_node(max_inputs=3, inputs=[None, None, None])
        with patch('input_sets.nuke.selectedNodes', return_value=[]):
            input_sets.set_input_to_b()
        self.assertIsNone(target.input(0))

    def test_set_input_skipped_when_plugin_disabled(self):
        target = _make_target_node(max_inputs=3, inputs=[None, None, None])
        with patch('input_sets.prefs.plugin_enabled', False), self._patch_selected(target):
            input_sets.set_input_to_b()
        self.assertIsNone(target.input(0))




if __name__ == '__main__':
    unittest.main()
