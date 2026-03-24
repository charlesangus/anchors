"""Tests for Phase 4 anchor navigation features (NAV-01, NAV-02, NAV-03, FIND-01).

Covers:
- NAV-01: _save_dag_position() captures zoom+center into anchor._back_position
- NAV-01: AnchorNavigatePlugin.invoke() calls _save_dag_position() before navigating
- NAV-02: navigate_back() calls nuke.zoom(saved_zoom, saved_center) and clears the slot
- NAV-02: navigate_back() is a silent no-op when _back_position is None
- FIND-01: AnchorNavigatePlugin.get_items() includes labelled BackdropNodes prefixed with Backdrops/
- FIND-01: unlabelled BackdropNodes are excluded from get_items()
- FIND-01: picker launches when only labelled Backdrops exist (no anchors)
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call



# ---------------------------------------------------------------------------
# Now import anchor — functions referenced by Phase 4 tests do not exist yet.
# Tests will be RED (AttributeError) until Plans 01/02 implement them.
# ---------------------------------------------------------------------------

def _ensure_qt_stubs_support_mock_attributes():
    """Ensure Qt stub modules support auto-attribute access for the anchor tests.

    When the full test suite is discovered, earlier test files may replace
    Qt sub-module stubs with plain types.ModuleType objects that don't
    auto-create attributes on access. This helper patches them back to
    MagicMock-based stubs and ensures NUKE_VERSION_MAJOR is set.
    """
    import nuke as current_nuke
    if not hasattr(current_nuke, 'NUKE_VERSION_MAJOR'):
        current_nuke.NUKE_VERSION_MAJOR = 16

    # Ensure Phase 4 viewport stubs are present on whatever nuke stub is active
    if not hasattr(current_nuke, 'zoom') or not callable(getattr(current_nuke.zoom, 'return_value', None)):
        current_nuke.zoom = MagicMock(return_value=1.0)
    if not hasattr(current_nuke, 'center') or not isinstance(current_nuke.center, MagicMock):
        current_nuke.center = MagicMock(return_value=[0.0, 0.0])
    if not hasattr(current_nuke, 'zoomToFitSelected'):
        current_nuke.zoomToFitSelected = MagicMock()
    if not hasattr(current_nuke, 'lastHitGroup'):
        current_nuke.lastHitGroup = MagicMock(return_value=MagicMock())

    for module_key in ('PySide6.QtGui', 'PySide6.QtWidgets', 'PySide6.QtCore'):
        existing = sys.modules.get(module_key)
        if existing is not None and not isinstance(existing, MagicMock):
            mock_replacement = MagicMock()
            sys.modules[module_key] = mock_replacement
            parent_key = 'PySide6'
            attr_name = module_key.split('.')[-1]
            parent_stub = sys.modules.get(parent_key)
            if parent_stub is not None:
                setattr(parent_stub, attr_name, mock_replacement)


import importlib
import anchor


# ---------------------------------------------------------------------------
# NAV-01: _save_dag_position()
# ---------------------------------------------------------------------------

class TestSaveDagPosition(unittest.TestCase):
    """NAV-01: _save_dag_position() captures zoom and center into _back_position."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        anchor._back_position = None
        import nuke as nuke_stub
        nuke_stub.zoom.reset_mock()
        nuke_stub.zoom.return_value = 1.0
        nuke_stub.center.reset_mock()
        nuke_stub.center.return_value = [0.0, 0.0]

    def test_save_stores_zoom_and_center(self):
        """_save_dag_position() stores (zoom, center) tuple from nuke.zoom() and nuke.center()."""
        anchor._save_dag_position()
        self.assertEqual(anchor._back_position, (1.0, [0.0, 0.0]))

    def test_save_overwrites_previous_slot(self):
        """_save_dag_position() replaces any previously saved position."""
        anchor._back_position = (2.0, [1.0, 1.0])
        anchor._save_dag_position()
        self.assertEqual(anchor._back_position, (1.0, [0.0, 0.0]))


# ---------------------------------------------------------------------------
# NAV-02: navigate_back()
# ---------------------------------------------------------------------------

class TestNavigateBack(unittest.TestCase):
    """NAV-02: navigate_back() restores saved position and clears the slot."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        anchor._back_position = None
        import nuke as nuke_stub
        nuke_stub.zoom.reset_mock()
        nuke_stub.zoom.return_value = 1.0
        nuke_stub.center.reset_mock()
        nuke_stub.center.return_value = [0.0, 0.0]
        import nukescripts
        nukescripts.clear_selection_recursive.reset_mock()

    def test_navigate_back_restores_zoom_and_center(self):
        """navigate_back() calls nuke.zoom(saved_zoom, saved_center)."""
        anchor._back_position = (2.5, [10.0, 20.0])
        anchor.navigate_back()
        import nuke as nuke_stub
        nuke_stub.zoom.assert_called_with(2.5, [10.0, 20.0])

    def test_navigate_back_clears_slot(self):
        """navigate_back() sets _back_position to None after restoring."""
        anchor._back_position = (2.5, [10.0, 20.0])
        anchor.navigate_back()
        self.assertIsNone(anchor._back_position)

    def test_navigate_back_noop_when_no_position(self):
        """navigate_back() does not call nuke.zoom when _back_position is None."""
        anchor._back_position = None
        anchor.navigate_back()
        import nuke as nuke_stub
        self.assertEqual(nuke_stub.zoom.call_count, 0)

    def test_navigate_back_calls_clear_selection(self):
        """navigate_back() calls nukescripts.clear_selection_recursive."""
        anchor._back_position = (1.0, [0.0, 0.0])
        anchor.navigate_back()
        import nukescripts
        nukescripts.clear_selection_recursive.assert_called()


# ---------------------------------------------------------------------------
# NAV-01: AnchorNavigatePlugin.invoke() saves position before navigating
# ---------------------------------------------------------------------------

class TestInvokeSavesPosition(unittest.TestCase):
    """NAV-01: AnchorNavigatePlugin.invoke() calls _save_dag_position() before navigating."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        anchor._back_position = None
        import nuke as nuke_stub
        nuke_stub.zoom.reset_mock()
        nuke_stub.zoom.return_value = 1.0
        nuke_stub.center.reset_mock()
        nuke_stub.center.return_value = [0.0, 0.0]
        nuke_stub.exists.reset_mock()
        nuke_stub.exists.return_value = True
        # Execute QTimer.singleShot callbacks synchronously so tests can assert on deferred calls.
        anchor.QtCore.QTimer.singleShot.side_effect = lambda delay, func: func()

    def test_invoke_saves_position_before_navigating_anchor(self):
        """invoke() calls _save_dag_position before navigate_to_anchor for non-BackdropNode."""
        call_order = []

        stub_anchor_node = MagicMock()
        stub_anchor_node.name.return_value = 'Anchor_Foo'
        stub_anchor_node.Class.return_value = 'NoOp'

        plugin = anchor.AnchorNavigatePlugin()

        with patch.object(anchor, '_save_dag_position', side_effect=lambda: call_order.append('save')) as mock_save, \
             patch.object(anchor, 'navigate_to_anchor', side_effect=lambda node: call_order.append('navigate')) as mock_navigate:
            plugin.invoke({'menuobj': stub_anchor_node})

        mock_save.assert_called_once()
        mock_navigate.assert_called_once_with(stub_anchor_node)
        self.assertLess(call_order.index('save'), call_order.index('navigate'),
                        "_save_dag_position must be called before navigate_to_anchor")

    def test_invoke_saves_position_before_navigating_backdrop(self):
        """invoke() calls _save_dag_position and then navigate_to_backdrop for BackdropNode."""
        call_order = []

        stub_backdrop_node = MagicMock()
        stub_backdrop_node.name.return_value = 'BackdropNode1'
        stub_backdrop_node.Class.return_value = 'BackdropNode'

        plugin = anchor.AnchorNavigatePlugin()

        with patch.object(anchor, '_save_dag_position', side_effect=lambda: call_order.append('save')) as mock_save, \
             patch.object(anchor, 'navigate_to_backdrop', side_effect=lambda node: call_order.append('navigate_bd')) as mock_navigate_bd:
            plugin.invoke({'menuobj': stub_backdrop_node})

        mock_save.assert_called_once()
        mock_navigate_bd.assert_called_once_with(stub_backdrop_node)
        self.assertLess(call_order.index('save'), call_order.index('navigate_bd'),
                        "_save_dag_position must be called before navigate_to_backdrop")


# ---------------------------------------------------------------------------
# FIND-01: AnchorNavigatePlugin.get_items() includes labelled BackdropNodes
# ---------------------------------------------------------------------------

class TestGetItemsIncludesBackdrops(unittest.TestCase):
    """FIND-01: get_items() includes labelled BackdropNodes with Backdrops/ prefix."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        import nuke as nuke_stub
        nuke_stub.allNodes.reset_mock()
        nuke_stub.allNodes.return_value = []

    def _make_stub_backdrop(self, label_value):
        """Return a StubNode acting as BackdropNode with the given label."""
        import nuke as nuke_stub
        label_knob = nuke_stub.StubKnob(label_value)
        knobs = {'label': label_knob}
        return nuke_stub.StubNode(name='BackdropNode1', node_class='BackdropNode', knobs_dict=knobs)

    def _make_stub_anchor(self, name):
        """Return a StubNode acting as a NoOp anchor with the ANCHOR_PREFIX."""
        import nuke as nuke_stub
        from constants import ANCHOR_PREFIX
        full_name = ANCHOR_PREFIX + name
        knobs = {
            'label': nuke_stub.StubKnob(name),
            'anchor': nuke_stub.StubKnob('anchor'),
        }
        return nuke_stub.StubNode(name=full_name, node_class='NoOp', knobs_dict=knobs)

    def test_get_items_includes_labelled_backdrop(self):
        """get_items() includes an item with menupath 'Backdrops/GradeStack' for labelled backdrop."""
        labelled_backdrop = self._make_stub_backdrop('GradeStack')

        def _allNodes_side_effect(class_name=None):
            if class_name == 'BackdropNode':
                return [labelled_backdrop]
            return []

        import nuke as nuke_stub
        nuke_stub.allNodes.side_effect = _allNodes_side_effect

        plugin = anchor.AnchorNavigatePlugin()
        items = plugin.get_items()

        menupaths = [item['menupath'] for item in items]
        self.assertIn('Backdrops/GradeStack', menupaths)

    def test_get_items_excludes_unlabelled_backdrop(self):
        """get_items() excludes BackdropNodes with an empty label."""
        unlabelled_backdrop = self._make_stub_backdrop('')

        def _allNodes_side_effect(class_name=None):
            if class_name == 'BackdropNode':
                return [unlabelled_backdrop]
            return []

        import nuke as nuke_stub
        nuke_stub.allNodes.side_effect = _allNodes_side_effect

        plugin = anchor.AnchorNavigatePlugin()
        items = plugin.get_items()

        backdrop_items = [item for item in items if item['menupath'].startswith('Backdrops/')]
        self.assertEqual(backdrop_items, [])

    def test_get_items_excludes_whitespace_only_label(self):
        """get_items() excludes BackdropNodes whose label is whitespace only."""
        whitespace_backdrop = self._make_stub_backdrop('   ')

        def _allNodes_side_effect(class_name=None):
            if class_name == 'BackdropNode':
                return [whitespace_backdrop]
            return []

        import nuke as nuke_stub
        nuke_stub.allNodes.side_effect = _allNodes_side_effect

        plugin = anchor.AnchorNavigatePlugin()
        items = plugin.get_items()

        backdrop_items = [item for item in items if item['menupath'].startswith('Backdrops/')]
        self.assertEqual(backdrop_items, [])

    def test_get_items_includes_anchors_bare(self):
        """get_items() includes anchor nodes with Anchors/ prefix."""
        stub_anchor_node = self._make_stub_anchor('Foo')

        def _allNodes_side_effect(class_name=None):
            if class_name == 'BackdropNode':
                return []
            return [stub_anchor_node]

        import nuke as nuke_stub
        nuke_stub.allNodes.side_effect = _allNodes_side_effect

        plugin = anchor.AnchorNavigatePlugin()
        items = plugin.get_items()

        anchor_items = [item for item in items if item['menupath'].startswith('Anchors/')]
        self.assertTrue(len(anchor_items) >= 1,
                        f"Expected at least one Anchors/ item but got: {[i['menupath'] for i in items]}")


# ---------------------------------------------------------------------------
# FIND-01: navigate_to_backdrop()
# ---------------------------------------------------------------------------

class TestNavigateToBackdrop(unittest.TestCase):
    """FIND-01: navigate_to_backdrop() selects the BackdropNode and zooms to fit."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        import nuke as nuke_stub
        nuke_stub.zoomToFitSelected.reset_mock()
        import nukescripts
        nukescripts.clear_selection_recursive.reset_mock()

    def test_navigate_to_backdrop_selects_and_zooms(self):
        """navigate_to_backdrop() calls backdrop['selected'].setValue(True) and nuke.zoom()."""
        selected_knob = MagicMock()
        stub_backdrop = MagicMock()
        stub_backdrop.__getitem__ = MagicMock(return_value=selected_knob)

        anchor.navigate_to_backdrop(stub_backdrop)

        selected_knob.setValue.assert_called_with(True)
        import nuke as nuke_stub
        nuke_stub.zoom.assert_called()

    def test_navigate_to_backdrop_clears_selection_before_and_after(self):
        """navigate_to_backdrop() calls nukescripts.clear_selection_recursive at least twice."""
        stub_backdrop = MagicMock()
        stub_backdrop.__getitem__ = MagicMock(return_value=MagicMock())

        anchor.navigate_to_backdrop(stub_backdrop)

        import nukescripts
        self.assertGreaterEqual(nukescripts.clear_selection_recursive.call_count, 2,
                                "clear_selection_recursive must be called before and after zoom")


# ---------------------------------------------------------------------------
# FIND-01: select_anchor_and_navigate() picker launch guard
# ---------------------------------------------------------------------------

class TestPickerLaunchGuard(unittest.TestCase):
    """FIND-01: select_anchor_and_navigate() uses updated guard including labelled backdrops."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        import nuke as nuke_stub
        nuke_stub.allNodes.reset_mock()
        nuke_stub.allNodes.side_effect = None
        nuke_stub.allNodes.return_value = []

    def _make_stub_backdrop(self, label_value):
        """Return a MagicMock BackdropNode with the given label knob value."""
        backdrop = MagicMock()
        label_knob = MagicMock()
        label_knob.value.return_value = label_value
        backdrop.__getitem__ = MagicMock(side_effect=lambda key: label_knob if key == 'label' else MagicMock())
        return backdrop

    def test_picker_launches_when_only_backdrops_exist(self):
        """select_anchor_and_navigate() launches picker when no anchors but labelled backdrops exist."""
        labelled_backdrop = self._make_stub_backdrop('GradeStack')

        def _allNodes_side_effect(class_name=None):
            if class_name == 'BackdropNode':
                return [labelled_backdrop]
            return []

        import nuke as nuke_stub
        nuke_stub.allNodes.side_effect = _allNodes_side_effect

        # Reset any cached widget
        anchor._anchor_navigate_widget = None

        widget_mock = MagicMock()
        with patch.object(sys.modules['tabtabtab'], 'TabTabTabWidget', return_value=widget_mock) as mock_widget_cls:
            anchor.select_anchor_and_navigate()
            mock_widget_cls.assert_called_once()

    def test_picker_suppressed_when_no_anchors_and_no_labelled_backdrops(self):
        """select_anchor_and_navigate() returns without creating widget when nothing to show."""
        def _allNodes_side_effect(class_name=None):
            return []

        import nuke as nuke_stub
        nuke_stub.allNodes.side_effect = _allNodes_side_effect

        anchor._anchor_navigate_widget = None

        with patch.object(sys.modules['tabtabtab'], 'TabTabTabWidget') as mock_widget_cls:
            anchor.select_anchor_and_navigate()
            mock_widget_cls.assert_not_called()


# ---------------------------------------------------------------------------
# DOT-FONT-GATE: TestDotFontSizeAnchorGate
# ---------------------------------------------------------------------------

class TestDotFontSizeAnchorGate(unittest.TestCase):
    """Tests for font size gating of Dot anchor detection in is_anchor().

    A Dot with label font size < 33 must NOT be treated as an anchor.
    A Dot with label font size >= 33 and a non-empty label MUST be an anchor.
    NoOp anchors prefixed with ANCHOR_PREFIX are completely unaffected.
    """

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        importlib.reload(anchor)
        import link as link_module
        importlib.reload(link_module)

    def _make_dot_node(self, label_value, note_font_size, extra_knobs=None):
        """Return a StubNode acting as a Dot with the given label and note_font_size."""
        import nuke as nuke_stub
        from constants import DOT_ANCHOR_KNOB_NAME
        knobs = {
            'label': nuke_stub.StubKnob(label_value),
            'note_font_size': nuke_stub.StubKnob(note_font_size),
            'hide_input': nuke_stub.StubKnob(False),
        }
        if extra_knobs:
            knobs.update(extra_knobs)
        return nuke_stub.StubNode(name='Dot1', node_class='Dot', knobs_dict=knobs)

    def test_dot_with_small_font_is_not_anchor(self):
        """Dot with label and note_font_size=11 (default/small) is NOT an anchor."""
        from link import is_anchor
        dot_node = self._make_dot_node('Foo', 11)
        self.assertFalse(is_anchor(dot_node))

    def test_dot_with_font_size_33_is_anchor(self):
        """Dot with label and note_font_size=33 IS an anchor."""
        from link import is_anchor
        dot_node = self._make_dot_node('Foo', 33)
        self.assertTrue(is_anchor(dot_node))

    def test_dot_with_font_size_66_is_anchor(self):
        """Dot with label and note_font_size=66 IS an anchor."""
        from link import is_anchor
        dot_node = self._make_dot_node('Foo', 66)
        self.assertTrue(is_anchor(dot_node))

    def test_dot_with_font_size_111_is_anchor(self):
        """Dot with label and note_font_size=111 IS an anchor."""
        from link import is_anchor
        dot_node = self._make_dot_node('Foo', 111)
        self.assertTrue(is_anchor(dot_node))

    def test_dot_with_anchor_knob_and_small_font_is_not_anchor(self):
        """Dot with DOT_ANCHOR_KNOB_NAME knob but note_font_size=11 is NOT an anchor."""
        from link import is_anchor
        from constants import DOT_ANCHOR_KNOB_NAME
        import nuke as nuke_stub
        anchor_knob = nuke_stub.StubKnob(True, knob_name=DOT_ANCHOR_KNOB_NAME)
        dot_node = self._make_dot_node('Foo', 11, extra_knobs={DOT_ANCHOR_KNOB_NAME: anchor_knob})
        self.assertFalse(is_anchor(dot_node))

    def test_dot_with_anchor_knob_and_qualifying_font_is_anchor(self):
        """Dot with DOT_ANCHOR_KNOB_NAME knob and note_font_size=33 IS an anchor."""
        from link import is_anchor
        from constants import DOT_ANCHOR_KNOB_NAME
        import nuke as nuke_stub
        anchor_knob = nuke_stub.StubKnob(True, knob_name=DOT_ANCHOR_KNOB_NAME)
        dot_node = self._make_dot_node('Foo', 33, extra_knobs={DOT_ANCHOR_KNOB_NAME: anchor_knob})
        self.assertTrue(is_anchor(dot_node))

    def test_dot_with_qualifying_font_and_empty_label_is_not_anchor(self):
        """Dot with note_font_size=33 but empty label is NOT an anchor."""
        from link import is_anchor
        dot_node = self._make_dot_node('', 33)
        self.assertFalse(is_anchor(dot_node))

    def test_noop_anchor_prefix_unaffected_by_font_gate(self):
        """NoOp node named Anchor_Foo is still an anchor regardless of font gating."""
        import nuke as nuke_stub
        from anchor import is_anchor as anchor_is_anchor
        knobs = {
            'label': nuke_stub.StubKnob('Foo'),
        }
        noop_node = nuke_stub.StubNode(name='Anchor_Foo', node_class='NoOp', knobs_dict=knobs)
        self.assertTrue(anchor_is_anchor(noop_node))


if __name__ == '__main__':
    unittest.main()
