"""Tests for Issue #35 — pasted anchor label re-stamp after name collision.

When nuke.nodePaste() renames an anchor to avoid a collision
(e.g. Anchor_Foo → Anchor_Foo1), the label knob retains the old serialised
value ("Foo"). paste_anchors() must re-derive the label from the post-collision
node name and call rename_anchor_to() to keep label and name in sync.

Covers:
- Test 1: NoOp anchor — label re-stamped after name collision
- Test 2: NoOp anchor — no collision, label already correct (idempotent)
- Test 3: Dot anchor — node name re-synced to label after collision
- Test 4: Path D stamped anchor (has KNOB_NAME) is NOT re-stamped
- Test 5: Regular link node (has KNOB_NAME) is NOT re-stamped
"""

import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_noop_anchor_node(node_name, label_value, knobs_dict_extra=None):
    """Return a stub NoOp anchor node with the given name and label, no KNOB_NAME."""
    import nuke as _nuke
    from constants import ANCHOR_PREFIX
    knobs = {
        'label': _nuke.StubKnob(label_value),
        'selected': _nuke.StubKnob(False),
    }
    if knobs_dict_extra:
        knobs.update(knobs_dict_extra)
    return _nuke.StubNode(
        name=node_name,
        node_class='NoOp',
        knobs_dict=knobs,
    )


def _make_dot_anchor_node(node_name, label_value, knobs_dict_extra=None):
    """Return a stub Dot anchor node with the given name and label, no KNOB_NAME."""
    import nuke as _nuke
    knobs = {
        'label': _nuke.StubKnob(label_value),
        'tile_color': _nuke.StubKnob(0),
        'selected': _nuke.StubKnob(False),
    }
    if knobs_dict_extra:
        knobs.update(knobs_dict_extra)
    return _nuke.StubNode(
        name=node_name,
        node_class='Dot',
        knobs_dict=knobs,
    )


def _make_stamped_anchor_node(node_name, label_value, stored_fqnn, dot_type_value=None):
    """Return a stub anchor node that has KNOB_NAME set (Path D stamped copy)."""
    import nuke as _nuke
    from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME
    knobs = {
        'label': _nuke.StubKnob(label_value),
        'selected': _nuke.StubKnob(False),
        KNOB_NAME: _nuke.StubKnob(stored_fqnn),
    }
    if dot_type_value is not None:
        knobs[DOT_TYPE_KNOB_NAME] = _nuke.StubKnob(dot_type_value)
    return _nuke.StubNode(
        name=node_name,
        node_class='Dot',
        knobs_dict=knobs,
    )


def _make_link_node_with_knob(node_name, stored_fqnn):
    """Return a stub link NoOp node with KNOB_NAME set (not an anchor)."""
    import nuke as _nuke
    from constants import KNOB_NAME
    knobs = {
        'label': _nuke.StubKnob('Link: Foo'),
        'selected': _nuke.StubKnob(False),
        KNOB_NAME: _nuke.StubKnob(stored_fqnn),
    }
    return _nuke.StubNode(
        name=node_name,
        node_class='NoOp',
        knobs_dict=knobs,
    )


# ---------------------------------------------------------------------------
# Test 1 — NoOp anchor: label re-stamped after name collision
# ---------------------------------------------------------------------------

class TestNoOpAnchorLabelRestampAfterCollision(unittest.TestCase):
    """After paste collision (Anchor_Foo → Anchor_Foo1), the label must be updated."""

    def test_noop_anchor_label_updated_to_reflect_renamed_node_after_collision(self):
        """paste_anchors() must re-stamp the label to 'Foo1' when the pasted
        NoOp anchor was renamed from Anchor_Foo to Anchor_Foo1 by Nuke."""
        import nuke as _nuke
        from constants import ANCHOR_PREFIX

        # Post-collision: node name is Anchor_Foo1 but label still says "Foo"
        pasted_node = _make_noop_anchor_node(
            node_name=ANCHOR_PREFIX + 'Foo1',
            label_value='Foo',
        )

        def is_anchor_side_effect(node):
            return node is pasted_node

        def anchor_display_name_side_effect(node):
            # For a NoOp anchor: derived from the current node name
            from constants import ANCHOR_PREFIX
            return node.name()[len(ANCHOR_PREFIX):]

        def rename_anchor_to_side_effect(anchor_node, display_name, color=None):
            # Mirror the real rename_anchor_to: update the label knob
            anchor_node['label'].setValue(display_name)

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_anchor', side_effect=is_anchor_side_effect), \
             patch('anchors.anchor_display_name', side_effect=anchor_display_name_side_effect), \
             patch('anchors.rename_anchor_to', side_effect=rename_anchor_to_side_effect) as mock_rename:

            mock_nuke.nodePaste.return_value = pasted_node
            mock_nuke.selectedNodes.return_value = [pasted_node]
            mock_nuke.root.return_value.name.return_value = 'myScript.nk'

            from anchors import paste_anchors
            paste_anchors()

        # rename_anchor_to must have been called with the new display name
        mock_rename.assert_called_once_with(pasted_node, 'Foo1')
        # The label must now reflect the collided name
        self.assertEqual(pasted_node['label'].getValue(), 'Foo1')


# ---------------------------------------------------------------------------
# Test 2 — NoOp anchor: no collision, label already correct (idempotent)
# ---------------------------------------------------------------------------

class TestNoOpAnchorLabelAlreadyCorrectIsIdempotent(unittest.TestCase):
    """When there is no collision the label is already correct; re-stamping is a no-op."""

    def test_noop_anchor_label_unchanged_when_no_collision_occurred(self):
        """paste_anchors() must leave the label 'Bar' unchanged when the node
        name is Anchor_Bar and the label already reads 'Bar'."""
        from constants import ANCHOR_PREFIX

        pasted_node = _make_noop_anchor_node(
            node_name=ANCHOR_PREFIX + 'Bar',
            label_value='Bar',
        )

        def is_anchor_side_effect(node):
            return node is pasted_node

        def anchor_display_name_side_effect(node):
            from constants import ANCHOR_PREFIX
            return node.name()[len(ANCHOR_PREFIX):]

        rename_call_count = []

        def rename_anchor_to_side_effect(anchor_node, display_name, color=None):
            rename_call_count.append(display_name)
            # Still update label (matches real implementation)
            anchor_node['label'].setValue(display_name)

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_anchor', side_effect=is_anchor_side_effect), \
             patch('anchors.anchor_display_name', side_effect=anchor_display_name_side_effect), \
             patch('anchors.rename_anchor_to', side_effect=rename_anchor_to_side_effect):

            mock_nuke.nodePaste.return_value = pasted_node
            mock_nuke.selectedNodes.return_value = [pasted_node]
            mock_nuke.root.return_value.name.return_value = 'myScript.nk'

            from anchors import paste_anchors
            paste_anchors()

        # rename_anchor_to was called (it's always called for plain anchors),
        # but the net result is that the label stays 'Bar'
        self.assertEqual(pasted_node['label'].getValue(), 'Bar')


# ---------------------------------------------------------------------------
# Test 3 — Dot anchor: node name re-synced to label after collision
# ---------------------------------------------------------------------------

class TestDotAnchorNodeNameResyncedAfterCollision(unittest.TestCase):
    """For a Dot anchor, anchor_display_name reads from the label, so rename_anchor_to
    is called with the label value and setName restores the invariant."""

    def test_dot_anchor_setname_called_with_anchor_prefix_plus_label_after_collision(self):
        """When a Dot anchor is pasted and Nuke renames it to Anchor_Plates1 (collision),
        the label still says 'Plates'. rename_anchor_to('Plates') must call
        setName('Anchor_Plates'), restoring the Dot anchor name invariant."""
        import nuke as _nuke
        from constants import ANCHOR_PREFIX

        # Post-collision node name: Anchor_Plates1; label: "Plates" (unchanged)
        pasted_dot = _make_dot_anchor_node(
            node_name=ANCHOR_PREFIX + 'Plates1',
            label_value='Plates',
        )

        def is_anchor_side_effect(node):
            return node is pasted_dot

        def anchor_display_name_side_effect(node):
            # For a Dot anchor: reads from label
            return node['label'].getValue().strip()

        def rename_anchor_to_side_effect(anchor_node, display_name, color=None):
            # Mirror real Dot branch: setName then setValue label
            from constants import ANCHOR_PREFIX
            import re
            sanitized = re.sub(r'[^A-Za-z0-9_]', '_', display_name.strip())
            if not sanitized:
                raise ValueError(f"empty sanitized name")
            anchor_node.setName(ANCHOR_PREFIX + sanitized)
            anchor_node['label'].setValue(display_name.strip())

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_anchor', side_effect=is_anchor_side_effect), \
             patch('anchors.anchor_display_name', side_effect=anchor_display_name_side_effect), \
             patch('anchors.rename_anchor_to', side_effect=rename_anchor_to_side_effect) as mock_rename:

            mock_nuke.nodePaste.return_value = pasted_dot
            mock_nuke.selectedNodes.return_value = [pasted_dot]
            mock_nuke.root.return_value.name.return_value = 'myScript.nk'

            from anchors import paste_anchors
            paste_anchors()

        # rename_anchor_to must be called with the label value as the display name
        mock_rename.assert_called_once_with(pasted_dot, 'Plates')
        # setName must have been called with 'Anchor_Plates' (the invariant name)
        self.assertIn(ANCHOR_PREFIX + 'Plates', pasted_dot._set_name_calls)
        # Label must be unchanged at 'Plates'
        self.assertEqual(pasted_dot['label'].getValue(), 'Plates')


# ---------------------------------------------------------------------------
# Test 4 — Path D stamped anchor (has KNOB_NAME) is NOT re-stamped
# ---------------------------------------------------------------------------

class TestPathDStampedAnchorIsNotRestamped(unittest.TestCase):
    """An anchor that carries KNOB_NAME (Path D stamped copy) must be skipped
    by the Issue #35 re-stamp loop — the KNOB_NAME condition gates it out."""

    def test_anchor_with_knob_name_is_not_passed_to_rename_anchor_to(self):
        """paste_anchors() must NOT call rename_anchor_to for an anchor that
        has KNOB_NAME set (it is a link-stamped copy, not a plain pasted anchor)."""
        import nuke as _nuke
        from constants import ANCHOR_PREFIX

        # Stamped anchor: has KNOB_NAME + DOT_TYPE_KNOB_NAME == 'link' (Path D)
        stamped_anchor = _make_stamped_anchor_node(
            node_name=ANCHOR_PREFIX + 'Foo',
            label_value='Foo',
            stored_fqnn='Anchor_Foo',
            dot_type_value='link',
        )

        def is_anchor_side_effect(node):
            return node is stamped_anchor

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_anchor', side_effect=is_anchor_side_effect), \
             patch('anchors.anchor_display_name') as mock_display_name, \
             patch('anchors.rename_anchor_to') as mock_rename, \
             patch('anchors.find_anchor_node', return_value=None):

            mock_nuke.nodePaste.return_value = stamped_anchor
            mock_nuke.selectedNodes.return_value = [stamped_anchor]
            mock_nuke.root.return_value.name.return_value = 'myScript.nk'

            from anchors import paste_anchors
            paste_anchors()

        # The re-stamp loop must not touch this node
        mock_rename.assert_not_called()
        mock_display_name.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — Regular link node (has KNOB_NAME) is NOT re-stamped
# ---------------------------------------------------------------------------

class TestRegularLinkNodeIsNotRestamped(unittest.TestCase):
    """A regular link node (is_anchor returns False, has KNOB_NAME) must not
    be touched by the re-stamp loop."""

    def test_link_node_with_knob_name_label_is_not_modified_by_restamp_loop(self):
        """The re-stamp loop condition requires both is_anchor(node) == True
        AND KNOB_NAME not in node.knobs(). A link node fails the KNOB_NAME check,
        so rename_anchor_to is never called."""
        import nuke as _nuke

        link_node = _make_link_node_with_knob(
            node_name='NoOp_link1',
            stored_fqnn='Anchor_Foo',
        )
        original_label = link_node['label'].getValue()

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts') as mock_nukescripts, \
             patch('anchors.is_anchor', return_value=False), \
             patch('anchors.rename_anchor_to') as mock_rename, \
             patch('anchors.find_anchor_node', return_value=None):

            mock_nuke.nodePaste.return_value = link_node
            mock_nuke.selectedNodes.return_value = [link_node]
            mock_nuke.root.return_value.name.return_value = 'myScript.nk'

            from anchors import paste_anchors
            paste_anchors()

        # rename_anchor_to must never be called for a non-anchor link node
        mock_rename.assert_not_called()
        # Label must be unchanged
        self.assertEqual(link_node['label'].getValue(), original_label)


if __name__ == '__main__':
    unittest.main()
