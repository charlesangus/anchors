"""Tests for the fuzzy-find scrolling preference (issue #82).

Covers:
- tabtabtab_anchors.NodeModel: max_items retention vs. num_items window sizing
- tabtabtab_anchors.TabTabTabWidget: the list view is set up to scroll
- prefs.py: default, persistence, and rejection of a corrupt value
- colors.py PrefsDialog: the checkbox is flushed on OK
- anchor.py: the pickers are actually handed the preference
"""

import ast
import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Loading the real tabtabtab core. conftest.py replaces tabtabtab_anchors with
# a stub for every other test file, and Qt is a MagicMock, so the module is
# loaded here from source under purpose-built Qt stubs. The stubs are swapped
# into sys.modules for the duration of the import only.
# ---------------------------------------------------------------------------

class _StubIndex:
    """Stand-in for QModelIndex; only .row() is exercised."""

    def __init__(self, row=-1):
        self._row = row

    def row(self):
        return self._row


class _StubAbstractListModel:
    """QAbstractListModel stand-in. modelReset is a per-instance recorder so a
    test can tell whether a re-render was emitted."""

    def __init__(self, *args, **kwargs):
        self.modelReset = MagicMock(name='modelReset')

    def index(self, row, column=0, parent=None):
        return _StubIndex(row)


def _build_pyside_stubs():
    """Construct PySide6 stub modules wired to the stand-in list model above."""
    pyside6 = types.ModuleType('PySide6')
    qtcore = types.ModuleType('PySide6.QtCore')
    qtgui = types.ModuleType('PySide6.QtGui')
    qtwidgets = types.ModuleType('PySide6.QtWidgets')

    qtcore.Qt = MagicMock()
    qtcore.QEvent = MagicMock()
    qtcore.QAbstractListModel = _StubAbstractListModel
    qtcore.QModelIndex = lambda: _StubIndex(-1)
    qtcore.QSize = MagicMock
    qtcore.QRect = MagicMock
    qtcore.Signal = MagicMock(return_value=MagicMock())
    qtcore.QTimer = type(
        'QTimer', (), {'singleShot': staticmethod(lambda delay_ms, callback: None)}
    )

    qtgui.QCursor = MagicMock()
    qtgui.QIcon = MagicMock
    qtgui.QColor = MagicMock
    qtgui.QBrush = MagicMock
    qtgui.QPen = MagicMock

    qtwidgets.QDialog = type('QDialog', (), {'__init__': lambda self, *a, **k: None})
    qtwidgets.QLineEdit = type('QLineEdit', (), {'__init__': lambda self, *a, **k: None})
    qtwidgets.QListView = type('QListView', (), {'__init__': lambda self, *a, **k: None})
    qtwidgets.QVBoxLayout = type('QVBoxLayout', (), {'__init__': lambda self, *a, **k: None})
    qtwidgets.QStyledItemDelegate = type(
        'QStyledItemDelegate', (), {'__init__': lambda self, *a, **k: None}
    )
    qtwidgets.QAbstractItemView = MagicMock()
    qtwidgets.QStyle = MagicMock()
    qtwidgets.QMainWindow = type('QMainWindow', (), {'__init__': lambda self, *a, **k: None})
    qtwidgets.QApplication = type(
        'QApplication', (), {'instance': staticmethod(lambda: MagicMock())}
    )

    pyside6.QtCore = qtcore
    pyside6.QtGui = qtgui
    pyside6.QtWidgets = qtwidgets
    return pyside6, qtcore, qtgui, qtwidgets


def _load_core():
    """Load the real tabtabtab_anchors module under a fresh test-only name."""
    pyside6, qtcore, qtgui, qtwidgets = _build_pyside_stubs()
    stub_names = ['PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']
    previous = {name: sys.modules.get(name) for name in stub_names}

    sys.modules['PySide6'] = pyside6
    sys.modules['PySide6.QtCore'] = qtcore
    sys.modules['PySide6.QtGui'] = qtgui
    sys.modules['PySide6.QtWidgets'] = qtwidgets
    sys.modules.setdefault('PySide2', types.ModuleType('PySide2'))

    core_path = os.path.join(os.path.dirname(__file__), '..', 'tabtabtab_anchors.py')
    spec = importlib.util.spec_from_file_location('tabtabtab_anchors_scroll_test', core_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for name in stub_names:
            if previous[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous[name]
    return module


class _StubWeights:
    """NodeWeights stand-in: every item scores the same, so ordering falls back
    to the alphabetical tie-break and the retained set is predictable."""

    def get(self, key, default=0):
        return 0


def _menu_items(count):
    """Build *count* plugin items whose names all share a common prefix, so a
    single filter string matches every one of them."""
    return [
        {'menupath': 'Anchors/anchor_{:03d}'.format(i), 'menuobj': object()}
        for i in range(count)
    ]


class TestNodeModelRetention(unittest.TestCase):
    """max_items decides how many matches survive; num_items only sizes the popup."""

    @classmethod
    def setUpClass(cls):
        cls.core = _load_core()

    def _model(self, item_count, **kwargs):
        return self.core.NodeModel(
            _menu_items(item_count), weights=_StubWeights(), **kwargs
        )

    def test_scrolling_off_keeps_only_a_windowful(self):
        """The historic behaviour: matches past the visible rows are discarded."""
        model = self._model(50, num_items=18, scroll_enabled=False)

        self.assertEqual(model.max_items, 18)
        self.assertEqual(model.rowCount(), 18)

    def test_scrolling_on_keeps_every_match(self):
        model = self._model(50, num_items=18, scroll_enabled=True)

        self.assertEqual(model.rowCount(), 50,
                         "every match must be reachable once scrolling is on")

    def test_retention_is_still_bounded_when_scrolling(self):
        """Scrolling raises the cap, it does not remove it."""
        model = self._model(
            40, num_items=18, scroll_enabled=True, scroll_max_items=25)

        self.assertEqual(model.max_items, 25)
        self.assertEqual(model.rowCount(), 25)

    def test_scrolling_default_is_off_for_the_core(self):
        """The vendored core stays conservative; anchors' own preference,
        which defaults to on, is what turns scrolling on in practice."""
        model = self._model(50, num_items=18)

        self.assertEqual(model.rowCount(), 18)

    def test_fewer_matches_than_the_window_are_all_kept(self):
        for scroll_enabled in (False, True):
            with self.subTest(scroll_enabled=scroll_enabled):
                model = self._model(5, num_items=18, scroll_enabled=scroll_enabled)

                self.assertEqual(model.rowCount(), 5)

    def test_num_items_still_sizes_the_window(self):
        """Raising the retention cap must not change what the popup is sized to
        show — _resize_list_to_contents reads num_items, not max_items."""
        model = self._model(50, num_items=18, scroll_enabled=True)

        self.assertEqual(model.num_items, 18)

    def test_retained_rows_are_the_top_ranked_ones(self):
        """The cap trims the tail of the ranked list, so the rows that survive
        under a tighter cap are a prefix of the ones that survive under it."""
        scrolling = self._model(40, num_items=18, scroll_enabled=True)
        capped = self._model(40, num_items=18, scroll_enabled=False)

        scrolling_paths = [item['menupath'] for item in scrolling._items]
        capped_paths = [item['menupath'] for item in capped._items]
        self.assertEqual(scrolling_paths[:len(capped_paths)], capped_paths)

    def test_set_scroll_enabled_re_renders(self):
        """A cached picker picks the preference up without being rebuilt."""
        model = self._model(50, num_items=18, scroll_enabled=False)
        model.modelReset.reset_mock()

        model.set_scroll_enabled(True)

        self.assertEqual(model.rowCount(), 50)
        model.modelReset.emit.assert_called_once()

    def test_set_scroll_enabled_can_turn_scrolling_back_off(self):
        model = self._model(50, num_items=18, scroll_enabled=True)

        model.set_scroll_enabled(False)

        self.assertEqual(model.max_items, 18)
        self.assertEqual(model.rowCount(), 18)

    def test_set_scroll_enabled_is_a_no_op_when_unchanged(self):
        """Every picker open re-applies the preference; an unchanged one must
        not cost a re-render (and the reset it would do to the selection)."""
        model = self._model(50, num_items=18, scroll_enabled=True)
        model.modelReset.reset_mock()

        model.set_scroll_enabled(True)

        model.modelReset.emit.assert_not_called()

    def test_filtering_still_applies_under_the_raised_cap(self):
        """A raised retention cap must not turn into "retain everything"."""
        model = self._model(50, num_items=18, scroll_enabled=True)

        model.set_filter('anchor_042')

        self.assertEqual([item['menupath'] for item in model._items],
                         ['Anchors/anchor_042'])


class TestWidgetScrollSetup(unittest.TestCase):
    """The list view has to be told to scroll, and the popup to stay put."""

    def setUp(self):
        source_text = (_REPO_ROOT / 'tabtabtab_anchors.py').read_text()
        tree = ast.parse(source_text)
        widget_class = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == 'TabTabTabWidget'
        )
        self._init_source = ast.get_source_segment(
            source_text,
            next(item for item in widget_class.body
                 if isinstance(item, ast.FunctionDef) and item.name == '__init__'),
        )
        self._resize_source = ast.get_source_segment(
            source_text,
            next(item for item in widget_class.body
                 if isinstance(item, ast.FunctionDef)
                 and item.name == '_resize_list_to_contents'),
        )

    def test_vertical_scrolling_is_enabled_on_the_list(self):
        self.assertIn('setVerticalScrollBarPolicy', self._init_source)
        self.assertIn('ScrollBarAsNeeded', self._init_source)

    def test_horizontal_scrolling_stays_off(self):
        self.assertIn('ScrollBarAlwaysOff', self._init_source)

    def test_the_popup_is_sized_from_num_items_not_the_row_count(self):
        """The window must not grow with the number of retained rows."""
        self.assertIn('self.things_model.num_items', self._resize_source)
        self.assertNotIn('self.things_model.max_items', self._resize_source)
        self.assertNotIn('rowCount', self._resize_source)


class TestScrollPrefPersistence(unittest.TestCase):
    """picker_scroll_enabled round-trips through anchors_prefs.json."""

    def setUp(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def tearDown(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def _reload_prefs(self, temp_dir):
        """Import a fresh prefs module pointed at throwaway files."""
        import constants
        original_paths = (
            constants.PREFS_PATH,
            constants.USER_PALETTE_PATH,
            constants.OLD_PREFS_PATH,
            constants.TABTABTAB_PREFS_PATH,
        )
        try:
            constants.PREFS_PATH = os.path.join(temp_dir, 'anchors_prefs.json')
            constants.USER_PALETTE_PATH = os.path.join(temp_dir, 'palette_unused.json')
            constants.OLD_PREFS_PATH = os.path.join(temp_dir, 'old_prefs_unused.json')
            constants.TABTABTAB_PREFS_PATH = os.path.join(temp_dir, 'tabtabtab_prefs.json')
            if 'prefs' in sys.modules:
                del sys.modules['prefs']
            # See test_space_mode_prefs: a stray tabtabtab_prefs module on the
            # developer's sys.path would make install detection machine-dependent.
            with patch.dict(sys.modules, {'tabtabtab_prefs': None}):
                import prefs as reloaded_prefs
                reloaded_prefs.PREFS_PATH = constants.PREFS_PATH
            return reloaded_prefs
        finally:
            (constants.PREFS_PATH,
             constants.USER_PALETTE_PATH,
             constants.OLD_PREFS_PATH,
             constants.TABTABTAB_PREFS_PATH) = original_paths

    def test_default_is_on(self):
        """Out of the box the pickers show every match — the point of the issue."""
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            self.assertTrue(prefs_module.picker_scroll_enabled)

    def test_value_round_trips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)
            prefs_module.picker_scroll_enabled = False
            prefs_module.save()

            with open(prefs_module.PREFS_PATH) as file_handle:
                saved = json.load(file_handle)
            self.assertIs(saved['picker_scroll_enabled'], False)

            reloaded = self._reload_prefs(temp_dir)
            self.assertFalse(reloaded.picker_scroll_enabled)

    def test_missing_key_keeps_the_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            with open(prefs_path, 'w') as file_handle:
                json.dump({'plugin_enabled': True}, file_handle)

            prefs_module = self._reload_prefs(temp_dir)

            self.assertTrue(prefs_module.picker_scroll_enabled)

    def test_non_boolean_value_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            with open(prefs_path, 'w') as file_handle:
                json.dump({'picker_scroll_enabled': 'yes please'}, file_handle)

            prefs_module = self._reload_prefs(temp_dir)

            self.assertTrue(prefs_module.picker_scroll_enabled)


def _extract_prefs_dialog_method(method_name, namespace):
    """Compile a PrefsDialog method from colors.py inside *namespace*.

    Mirrors the extraction helper in test_space_mode_prefs.py: the real Qt
    classes are unavailable under test, so the method body is run directly
    against a stand-in object rather than a constructed dialog.
    """
    source_text = (_REPO_ROOT / 'colors.py').read_text()
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'PrefsDialog':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    source_lines = source_text.splitlines()
                    method_source = textwrap.dedent(
                        '\n'.join(source_lines[item.lineno - 1:item.end_lineno])
                    )
                    exec(compile(method_source, '<colors_prefs_method>', 'exec'), namespace)
                    return namespace[method_name]
    return None


class _StubCheckBox:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class TestPrefsDialogFlushesTheCheckbox(unittest.TestCase):
    """OK has to carry the checkbox state into the prefs module."""

    def _run_on_accept(self, checkbox_state):
        namespace = {'QtWidgets': MagicMock()}
        prefs_mock = MagicMock(name='prefs')
        prefs_mock.is_valid_space_mode_order.return_value = True
        original_prefs_module = sys.modules.get('prefs')
        sys.modules['prefs'] = prefs_mock
        try:
            dialog = MagicMock(name='PrefsDialog')
            dialog._is_following_tabtabtab_prefs.return_value = True  # skip mapping validation
            dialog._picker_scroll_enabled_checkbox = _StubCheckBox(checkbox_state)
            on_accept = _extract_prefs_dialog_method('_on_accept', namespace)
            self.assertIsNotNone(on_accept, 'PrefsDialog._on_accept not found')
            on_accept(dialog)
        finally:
            if original_prefs_module is not None:
                sys.modules['prefs'] = original_prefs_module
            else:
                sys.modules.pop('prefs', None)
        return dialog, prefs_mock

    def test_checked_box_is_flushed_and_saved(self):
        dialog, prefs_mock = self._run_on_accept(True)

        self.assertIs(prefs_mock.picker_scroll_enabled, True)
        prefs_mock.save.assert_called_once()
        dialog.accept.assert_called_once()

    def test_unchecked_box_is_flushed(self):
        _, prefs_mock = self._run_on_accept(False)

        self.assertIs(prefs_mock.picker_scroll_enabled, False)

    def test_the_checkbox_is_seeded_from_prefs(self):
        """__init__ must read the saved value, or OK would flush a stale one."""
        source_text = (_REPO_ROOT / 'colors.py').read_text()

        self.assertIn(
            'self._local_picker_scroll_enabled = prefs_module.picker_scroll_enabled',
            source_text,
        )


class TestPickersReceiveScrollPreference(unittest.TestCase):
    """The pickers must actually be handed the preference."""

    def test_every_picker_construction_passes_scroll_enabled(self):
        source_text = (_REPO_ROOT / 'anchor.py').read_text()
        tree = ast.parse(source_text)

        construction_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'TabTabTabWidget'
        ]

        self.assertEqual(len(construction_calls), 3,
                         "expected the link, pick and navigate pickers")
        for call_node in construction_calls:
            keyword_names = [keyword.arg for keyword in call_node.keywords]
            self.assertIn(
                'scroll_enabled', keyword_names,
                "TabTabTabWidget at anchor.py:{} must be given the preference".format(
                    call_node.lineno),
            )

    def test_cached_pickers_have_the_preference_reapplied(self):
        import anchor as anchor_module

        picker_widget = MagicMock()
        with patch.object(anchor_module.prefs, 'picker_scroll_enabled', False):
            anchor_module._apply_scroll_enabled(picker_widget)

        picker_widget.things_model.set_scroll_enabled.assert_called_once_with(False)

    def test_both_cached_pickers_are_covered(self):
        """Both reuse paths — the link picker and the navigate picker — have to
        re-apply the preference, or one of them would stay stale."""
        source_text = (_REPO_ROOT / 'anchor.py').read_text()

        self.assertIn('_apply_scroll_enabled(_anchor_picker_widget)', source_text)
        self.assertIn('_apply_scroll_enabled(_anchor_navigate_widget)', source_text)


if __name__ == '__main__':
    unittest.main()
