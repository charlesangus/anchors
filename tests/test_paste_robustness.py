"""Tests for paste robustness crash-guard fixes (issue #38).

Covers:
- TEST-38-01: final_selection.remove() does not raise when node appears twice
- TEST-38-02: find_node_default_color() returns 0 when prefs node is None
- TEST-38-03: paste_multiple_anchors() completes without error (smoke test)
- TEST-38-04: _get_script_stem() returns '' for unsaved scripts
- TEST-38-05: setup_link_node() does not raise when input_node lacks a 'label' knob
"""

import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# TEST-38-01: final_selection.remove() guard in paste_anchors() Path D
# ---------------------------------------------------------------------------

class TestFinalSelectionRemoveGuard(unittest.TestCase):
    """CRASH-01: final_selection.remove() must not raise ValueError when the
    same node appears twice in the pasted selection (or is already absent)."""

    def _make_stamped_anchor_node(self, anchor_name, stored_fqnn):
        """Return a stub anchor node stamped with DOT_TYPE='link' (Path D trigger)."""
        import nuke as _nuke
        from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME, ANCHOR_PREFIX
        return _nuke.StubNode(
            name=ANCHOR_PREFIX + anchor_name,
            node_class='NoOp',
            xpos=100,
            ypos=200,
            knobs_dict={
                KNOB_NAME: _nuke.StubKnob(stored_fqnn),
                DOT_TYPE_KNOB_NAME: _nuke.StubKnob('link'),
                'selected': _nuke.StubKnob(False),
            },
        )

    def test_duplicate_node_in_pasted_selection_does_not_raise(self):
        """When the same node object appears twice in nuke.selectedNodes(), the
        guarded final_selection.remove() must not raise ValueError."""
        import nuke as _nuke
        from constants import KNOB_NAME

        anchor_node = self._make_stamped_anchor_node(
            anchor_name='MyFootage',
            stored_fqnn='Anchor_MyFootage',
        )

        # Simulate Nuke returning the same node object twice in the pasted selection.
        duplicate_selection = [anchor_node, anchor_node]

        resolved_original = _nuke.StubNode(
            name='Anchor_MyFootage',
            node_class='NoOp',
            knobs_dict={
                'tile_color': _nuke.StubKnob(0),
                'label': _nuke.StubKnob(''),
                'hide_input': _nuke.StubKnob(False),
            },
        )

        created_link_nodes = []

        def fake_create_node(node_class):
            link_node = _nuke.StubNode(
                name=f'NoOp_link_{len(created_link_nodes)}',
                node_class=node_class,
                knobs_dict={'selected': _nuke.StubKnob(False)},
            )
            created_link_nodes.append(link_node)
            return link_node

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.find_anchor_node', return_value=resolved_original), \
             patch('anchors.is_anchor', return_value=True), \
             patch('anchors.get_link_class_for_source', return_value='NoOp'), \
             patch('anchors.setup_link_node'):

            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = duplicate_selection
            mock_nuke.createNode.side_effect = fake_create_node
            mock_nuke.delete = MagicMock()

            from anchors import paste_anchors

            # Must not raise ValueError
            try:
                paste_anchors()
            except ValueError as exc:
                self.fail(
                    f"paste_anchors() raised ValueError when node appeared twice "
                    f"in selection: {exc}"
                )

    def test_node_already_absent_from_final_selection_does_not_raise(self):
        """If a node was already removed from final_selection by a prior iteration,
        the guard must silently skip the second remove() instead of raising."""
        # Build a list and manually test the guarded pattern to confirm no ValueError.
        final_selection = ['node_a', 'node_b']
        node_to_remove = 'node_a'

        # First removal — succeeds
        if node_to_remove in final_selection:
            final_selection.remove(node_to_remove)

        # Second removal attempt — guarded, must not raise
        try:
            if node_to_remove in final_selection:
                final_selection.remove(node_to_remove)
        except ValueError as exc:
            self.fail(f"Guarded remove raised ValueError: {exc}")

        self.assertEqual(final_selection, ['node_b'])


# ---------------------------------------------------------------------------
# TEST-38-02: find_node_default_color() returns 0 when preferences is None
# ---------------------------------------------------------------------------

class TestFindNodeDefaultColorNullPrefs(unittest.TestCase):
    """CRASH-02: find_node_default_color() must return 0 gracefully when
    nuke.toNode('preferences') returns None (headless / degraded session)."""

    def test_returns_zero_when_preferences_node_is_none(self):
        """find_node_default_color() must return 0 when prefs_node is None."""
        import nuke as _nuke
        from tests.stubs import make_stub_nuke_module

        stub_nuke = make_stub_nuke_module()
        stub_nuke.toNode = MagicMock(return_value=None)

        input_node = _nuke.StubNode(
            name='Read1',
            node_class='Read',
            knobs_dict={
                'tile_color': _nuke.StubKnob(0),
            },
        )

        with patch('link.nuke', stub_nuke):
            from link import find_node_default_color
            result = find_node_default_color(input_node)

        self.assertEqual(
            result,
            0,
            f"Expected 0 when preferences is None, got {result!r}",
        )

    def test_does_not_raise_when_preferences_node_is_none(self):
        """find_node_default_color() must not raise AttributeError when prefs is None."""
        import nuke as _nuke
        from tests.stubs import make_stub_nuke_module

        stub_nuke = make_stub_nuke_module()
        stub_nuke.toNode = MagicMock(return_value=None)

        input_node = _nuke.StubNode(name='Camera1', node_class='Camera')

        with patch('link.nuke', stub_nuke):
            from link import find_node_default_color
            try:
                find_node_default_color(input_node)
            except AttributeError as exc:
                self.fail(
                    f"find_node_default_color() raised AttributeError with None prefs: {exc}"
                )


# ---------------------------------------------------------------------------
# TEST-38-03: paste_multiple_anchors() smoke test
# ---------------------------------------------------------------------------

class TestPasteMultipleAnchorsSmoke(unittest.TestCase):
    """CRASH-03: paste_multiple_anchors() must complete without error and must
    operate inside a nuke.lastHitGroup() context."""

    def test_paste_multiple_anchors_completes_without_error(self):
        """Basic smoke test: paste_multiple_anchors() with two selected nodes
        must run to completion without raising any exception."""
        import nuke as _nuke

        node_a = _nuke.StubNode(
            name='NoOp1',
            node_class='NoOp',
            knobs_dict={'selected': _nuke.StubKnob(False)},
        )
        node_b = _nuke.StubNode(
            name='NoOp2',
            node_class='NoOp',
            knobs_dict={'selected': _nuke.StubKnob(False)},
        )

        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.paste_anchors') as mock_paste_anchors:

            mock_nuke.selectedNodes.return_value = [node_a, node_b]
            mock_paste_anchors.return_value = None

            # lastHitGroup must return a context manager
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=None)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_nuke.lastHitGroup.return_value = mock_context

            from anchors import paste_multiple_anchors

            try:
                paste_multiple_anchors()
            except Exception as exc:
                self.fail(f"paste_multiple_anchors() raised unexpectedly: {exc}")

    def test_paste_multiple_anchors_uses_last_hit_group_context(self):
        """paste_multiple_anchors() must call nuke.lastHitGroup() so that
        selectedNodes() operates in the user's last-active group context."""
        with patch('anchors.nuke') as mock_nuke, \
             patch('anchors.nukescripts'), \
             patch('anchors.paste_anchors'):

            mock_nuke.selectedNodes.return_value = []

            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=None)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_nuke.lastHitGroup.return_value = mock_context

            from anchors import paste_multiple_anchors
            paste_multiple_anchors()

            mock_nuke.lastHitGroup.assert_called_once()


# ---------------------------------------------------------------------------
# TEST-38-04: _get_script_stem() returns '' for unsaved scripts
# ---------------------------------------------------------------------------

class TestGetScriptStemUnsaved(unittest.TestCase):
    """CRASH-04: _get_script_stem() must return '' when nuke.root().name() is ''
    (script has never been saved)."""

    def test_returns_empty_string_for_unsaved_script(self):
        """_get_script_stem() must return '' when nuke.root().name() returns ''."""
        with patch('anchors.nuke') as mock_nuke:
            mock_nuke.root.return_value.name.return_value = ''

            from anchors import _get_script_stem
            result = _get_script_stem()

        self.assertEqual(
            result,
            '',
            f"Expected '' for unsaved script, got {result!r}",
        )

    def test_returns_stem_for_saved_script(self):
        """_get_script_stem() must return the bare filename stem for a saved script."""
        with patch('anchors.nuke') as mock_nuke:
            mock_nuke.root.return_value.name.return_value = '/path/to/myScript.nk'

            from anchors import _get_script_stem
            result = _get_script_stem()

        self.assertEqual(result, 'myScript')

    def test_returns_multi_dot_stem_correctly(self):
        """_get_script_stem() must preserve all segments before the final extension
        for multi-dot filenames like 'project.shotA.nk'."""
        with patch('anchors.nuke') as mock_nuke:
            mock_nuke.root.return_value.name.return_value = '/path/to/project.shotA.nk'

            from anchors import _get_script_stem
            result = _get_script_stem()

        self.assertEqual(result, 'project.shotA')


# ---------------------------------------------------------------------------
# TEST-38-05: setup_link_node() does not raise when input_node lacks 'label'
# ---------------------------------------------------------------------------

class TestSetupLinkNodeNoLabelKnob(unittest.TestCase):
    """CRASH-05: setup_link_node() must not raise when input_node has no 'label'
    knob (custom Gizmo or TCL node that omits the standard label knob)."""

    def _make_node_without_label(self, name='Gizmo1', node_class='NoOp'):
        """Return a stub node that deliberately has no 'label' knob."""
        import nuke as _nuke
        return _nuke.StubNode(
            name=name,
            node_class=node_class,
            knobs_dict={
                'tile_color': _nuke.StubKnob(0),
                'hide_input': _nuke.StubKnob(False),
                # Intentionally NO 'label' knob
            },
        )

    def _make_link_node(self, name='NoOp_link', node_class='NoOp'):
        """Return a stub node that will serve as the link node."""
        import nuke as _nuke
        from constants import KNOB_NAME
        return _nuke.StubNode(
            name=name,
            node_class=node_class,
            knobs_dict={
                'tile_color': _nuke.StubKnob(0),
                'hide_input': _nuke.StubKnob(False),
                'label': _nuke.StubKnob(''),
                'note_font_size': _nuke.StubKnob(0),
                KNOB_NAME: _nuke.StubKnob(''),
            },
        )

    def test_does_not_raise_when_input_node_has_no_label_knob(self):
        """setup_link_node() must not raise NameError when input_node lacks 'label'."""
        from tests.stubs import make_stub_nuke_module

        input_node = self._make_node_without_label()
        link_node = self._make_link_node()

        stub_nuke = make_stub_nuke_module()

        with patch('link.nuke', stub_nuke), \
             patch('link.find_node_color', return_value=0):
            from link import setup_link_node

            try:
                setup_link_node(input_node, link_node)
            except (NameError, KeyError) as exc:
                self.fail(
                    f"setup_link_node() raised {type(exc).__name__} when input_node "
                    f"had no 'label' knob: {exc}"
                )

    def test_uses_node_name_as_label_when_input_has_no_label_knob(self):
        """When input_node has no 'label' knob, the link label must fall back to
        'Link: <input_node.name()>'."""
        from tests.stubs import make_stub_nuke_module

        input_node = self._make_node_without_label(name='MyCustomGizmo')
        link_node = self._make_link_node()

        stub_nuke = make_stub_nuke_module()

        with patch('link.nuke', stub_nuke), \
             patch('link.find_node_color', return_value=0):
            from link import setup_link_node
            setup_link_node(input_node, link_node)

        self.assertEqual(
            link_node['label'].getValue(),
            'Link: MyCustomGizmo',
        )

    def test_uses_label_text_when_input_has_label_knob_with_value(self):
        """When input_node has a 'label' knob with a non-empty value, the link label
        must be 'Link: <label_text>'."""
        import nuke as _nuke
        from tests.stubs import make_stub_nuke_module

        input_node = _nuke.StubNode(
            name='Read1',
            node_class='Read',
            knobs_dict={
                'tile_color': _nuke.StubKnob(0),
                'hide_input': _nuke.StubKnob(False),
                'label': _nuke.StubKnob('my footage'),
            },
        )
        link_node = self._make_link_node()

        stub_nuke = make_stub_nuke_module()

        with patch('link.nuke', stub_nuke), \
             patch('link.find_node_color', return_value=0):
            from link import setup_link_node
            setup_link_node(input_node, link_node)

        self.assertEqual(
            link_node['label'].getValue(),
            'Link: my footage',
        )


if __name__ == '__main__':
    unittest.main()
