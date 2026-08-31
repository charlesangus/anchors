"""Tests for the space-prefix search mode preference (issue #80).

Covers:
- prefs.py: defaults, validation, persistence of the user's own mode order
- prefs.py: following a tabtabtab-nuke install's space_mode_order
- colors.py PrefsDialog: the greying and validation rules around the mapping
- anchor.py: the pickers are actually handed the effective mode order
"""

import ast
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

if 'nuke' not in sys.modules:
    nuke_stub = types.ModuleType('nuke')
    nuke_stub.NUKE_VERSION_MAJOR = 14
    sys.modules['nuke'] = nuke_stub

ANCHORED = 'anchored_fuzzy'
NON_ANCHORED = 'non_anchored_fuzzy'
CONSECUTIVE = 'consecutive'


class _SpaceModePrefsTestCase(unittest.TestCase):
    """Shared reload helper — every test gets a pristine prefs module."""

    def setUp(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def tearDown(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def _reload_prefs(self, temp_dir, tabtabtab_prefs_path=None):
        """Import a fresh prefs module pointed at throwaway files.

        tabtabtab_prefs_path defaults to a path inside temp_dir that does not
        exist, so tests start out with no tabtabtab-nuke install in sight.
        """
        import constants
        if tabtabtab_prefs_path is None:
            tabtabtab_prefs_path = os.path.join(temp_dir, 'tabtabtab_prefs.json')
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
            constants.TABTABTAB_PREFS_PATH = tabtabtab_prefs_path
            if 'prefs' in sys.modules:
                del sys.modules['prefs']
            # An unrelated tabtabtab_prefs module on the developer's sys.path
            # would otherwise make install detection machine-dependent. The
            # block has to be in sys.modules rather than a patch of
            # prefs._tabtabtab_prefs_module: patch() imports prefs to find its
            # target, so prefs' own import-time detection has already run by the
            # time such a patch takes effect. A None entry makes the import
            # raise, which _tabtabtab_prefs_module() reads as "not installed".
            with patch.dict(sys.modules, {'tabtabtab_prefs': None}):
                import prefs as reloaded_prefs
                reloaded_prefs.PREFS_PATH = constants.PREFS_PATH
                reloaded_prefs.TABTABTAB_PREFS_PATH = tabtabtab_prefs_path
                reloaded_prefs.refresh_tabtabtab_prefs()
            return reloaded_prefs
        finally:
            (constants.PREFS_PATH,
             constants.USER_PALETTE_PATH,
             constants.OLD_PREFS_PATH,
             constants.TABTABTAB_PREFS_PATH) = original_paths

    def _refresh_without_installed_module(self, prefs_module):
        """Refresh with module-based detection suppressed (file detection only)."""
        with patch.object(prefs_module, '_tabtabtab_prefs_module', return_value=None):
            prefs_module.refresh_tabtabtab_prefs()


class TestSpaceModeOrderPersistence(_SpaceModePrefsTestCase):
    """The user's own space-prefix mapping round-trips through anchors_prefs.json."""

    def test_default_order_matches_historic_behaviour(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            self.assertEqual(
                prefs_module.space_mode_order,
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "0 spaces must stay anchored fuzzy, 1 space non-anchored, 2 spaces consecutive",
            )
            self.assertFalse(prefs_module.use_tabtabtab_prefs)

    def test_order_round_trips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            prefs_module._user_space_mode_order = [CONSECUTIVE, ANCHORED, NON_ANCHORED]
            prefs_module.save()

            with open(os.path.join(temp_dir, 'anchors_prefs.json')) as file_handle:
                data = json.load(file_handle)
            self.assertEqual(data['space_mode_order'], [CONSECUTIVE, ANCHORED, NON_ANCHORED])

            reloaded = self._reload_prefs(temp_dir)
            self.assertEqual(
                reloaded.space_mode_order,
                [CONSECUTIVE, ANCHORED, NON_ANCHORED],
                "saved order must come back as the effective order",
            )

    def test_use_tabtabtab_prefs_flag_round_trips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            prefs_module.use_tabtabtab_prefs = True
            prefs_module.save()

            reloaded = self._reload_prefs(temp_dir)
            self.assertTrue(reloaded.use_tabtabtab_prefs)

    def test_missing_key_keeps_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, 'anchors_prefs.json'), 'w') as file_handle:
                json.dump({'plugin_enabled': True, 'custom_colors': []}, file_handle)

            prefs_module = self._reload_prefs(temp_dir)

            self.assertEqual(prefs_module.space_mode_order,
                             [ANCHORED, NON_ANCHORED, CONSECUTIVE])


class TestSpaceModeOrderValidation(_SpaceModePrefsTestCase):
    """A corrupt mapping must never reach the picker."""

    def test_validator_accepts_every_permutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            import itertools
            for candidate_order in itertools.permutations([ANCHORED, NON_ANCHORED, CONSECUTIVE]):
                self.assertTrue(
                    prefs_module.is_valid_space_mode_order(list(candidate_order)),
                    "{} is a valid mapping".format(candidate_order),
                )

    def test_validator_rejects_malformed_orders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            rejected_orders = [
                None,
                'anchored_fuzzy',
                [],
                [ANCHORED, NON_ANCHORED],                      # too short
                [ANCHORED, NON_ANCHORED, CONSECUTIVE, ANCHORED],  # too long
                [ANCHORED, ANCHORED, CONSECUTIVE],             # duplicate mode
                [ANCHORED, NON_ANCHORED, 'regex'],             # unknown mode
                {'0': ANCHORED},
                [{'mode': ANCHORED}, NON_ANCHORED, CONSECUTIVE],  # unhashable entry
                [[ANCHORED], NON_ANCHORED, CONSECUTIVE],       # unhashable entry
            ]
            for candidate_order in rejected_orders:
                self.assertFalse(
                    prefs_module.is_valid_space_mode_order(candidate_order),
                    "{!r} must be rejected".format(candidate_order),
                )

    def test_unhashable_order_in_prefs_file_is_ignored(self):
        """A nested object on disk must be rejected, not crash the import."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, 'anchors_prefs.json'), 'w') as file_handle:
                json.dump(
                    {
                        'plugin_enabled': True,
                        'custom_colors': [],
                        'space_mode_order': [{'mode': ANCHORED}, [NON_ANCHORED], 3],
                    },
                    file_handle,
                )

            prefs_module = self._reload_prefs(temp_dir)

            self.assertEqual(
                prefs_module.space_mode_order,
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "unhashable entries on disk must fall back to the default",
            )

    def test_invalid_order_in_prefs_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, 'anchors_prefs.json'), 'w') as file_handle:
                json.dump(
                    {
                        'plugin_enabled': True,
                        'custom_colors': [],
                        'space_mode_order': [ANCHORED, ANCHORED, ANCHORED],
                    },
                    file_handle,
                )

            prefs_module = self._reload_prefs(temp_dir)

            self.assertEqual(
                prefs_module.space_mode_order,
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "a duplicate-mode order on disk must fall back to the default",
            )


class TestFollowingTabtabtabPrefs(_SpaceModePrefsTestCase):
    """use_tabtabtab_prefs makes anchors read tabtabtab-nuke's own setting."""

    def _write_tabtabtab_prefs(self, path, space_mode_order):
        with open(path, 'w') as file_handle:
            json.dump(
                {'tabtabtab_enabled': True, 'space_mode_order': space_mode_order},
                file_handle,
            )

    def test_no_install_found_when_nothing_is_installed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            self.assertFalse(prefs_module.tabtabtab_prefs_available())
            self.assertEqual(
                prefs_module.tabtabtab_space_mode_order(),
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "with no install to follow, the offered order is the anchors default",
            )

    def test_tabtabtab_order_becomes_effective_when_followed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tabtabtab_path = os.path.join(temp_dir, 'tabtabtab_prefs.json')
            self._write_tabtabtab_prefs(tabtabtab_path, [CONSECUTIVE, ANCHORED, NON_ANCHORED])

            prefs_module = self._reload_prefs(temp_dir, tabtabtab_prefs_path=tabtabtab_path)

            self.assertTrue(prefs_module.tabtabtab_prefs_available())
            self.assertEqual(
                prefs_module.space_mode_order,
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "an install is not followed until the user asks for it",
            )

            prefs_module.use_tabtabtab_prefs = True
            self._refresh_without_installed_module(prefs_module)

            self.assertEqual(prefs_module.space_mode_order,
                             [CONSECUTIVE, ANCHORED, NON_ANCHORED])

    def test_user_order_is_preserved_while_following(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tabtabtab_path = os.path.join(temp_dir, 'tabtabtab_prefs.json')
            self._write_tabtabtab_prefs(tabtabtab_path, [CONSECUTIVE, ANCHORED, NON_ANCHORED])
            prefs_module = self._reload_prefs(temp_dir, tabtabtab_prefs_path=tabtabtab_path)

            prefs_module._user_space_mode_order = [NON_ANCHORED, CONSECUTIVE, ANCHORED]
            prefs_module.use_tabtabtab_prefs = True
            self._refresh_without_installed_module(prefs_module)
            prefs_module.save()

            self.assertEqual(prefs_module.space_mode_order,
                             [CONSECUTIVE, ANCHORED, NON_ANCHORED])
            with open(os.path.join(temp_dir, 'anchors_prefs.json')) as file_handle:
                data = json.load(file_handle)
            self.assertEqual(
                data['space_mode_order'],
                [NON_ANCHORED, CONSECUTIVE, ANCHORED],
                "the user's own mapping must survive being temporarily overridden",
            )

            prefs_module.use_tabtabtab_prefs = False
            self._refresh_without_installed_module(prefs_module)
            self.assertEqual(
                prefs_module.space_mode_order,
                [NON_ANCHORED, CONSECUTIVE, ANCHORED],
                "unfollowing must restore the user's own mapping",
            )

    def test_following_a_missing_install_falls_back_to_user_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)

            prefs_module._user_space_mode_order = [NON_ANCHORED, CONSECUTIVE, ANCHORED]
            prefs_module.use_tabtabtab_prefs = True
            self._refresh_without_installed_module(prefs_module)

            self.assertFalse(prefs_module.tabtabtab_prefs_available())
            self.assertEqual(prefs_module.space_mode_order,
                             [NON_ANCHORED, CONSECUTIVE, ANCHORED])

    def test_corrupt_tabtabtab_file_is_treated_as_an_install_on_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tabtabtab_path = os.path.join(temp_dir, 'tabtabtab_prefs.json')
            with open(tabtabtab_path, 'w') as file_handle:
                file_handle.write('{not json')

            prefs_module = self._reload_prefs(temp_dir, tabtabtab_prefs_path=tabtabtab_path)
            prefs_module.use_tabtabtab_prefs = True
            self._refresh_without_installed_module(prefs_module)

            self.assertEqual(
                prefs_module.space_mode_order,
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "an unreadable tabtabtab prefs file must not crash or corrupt the mapping",
            )

    def test_unhashable_tabtabtab_order_is_treated_as_defaults(self):
        """A nested object in tabtabtab's file must not crash the refresh."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tabtabtab_path = os.path.join(temp_dir, 'tabtabtab_prefs.json')
            self._write_tabtabtab_prefs(tabtabtab_path, [{'mode': ANCHORED}, [], 2])

            prefs_module = self._reload_prefs(temp_dir, tabtabtab_prefs_path=tabtabtab_path)
            prefs_module.use_tabtabtab_prefs = True
            self._refresh_without_installed_module(prefs_module)

            self.assertEqual(
                prefs_module.space_mode_order,
                [ANCHORED, NON_ANCHORED, CONSECUTIVE],
                "an unusable order in tabtabtab's file must fall back to the defaults",
            )

    def test_refresh_picks_up_a_change_made_in_tabtabtab(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tabtabtab_path = os.path.join(temp_dir, 'tabtabtab_prefs.json')
            self._write_tabtabtab_prefs(tabtabtab_path, [CONSECUTIVE, ANCHORED, NON_ANCHORED])
            prefs_module = self._reload_prefs(temp_dir, tabtabtab_prefs_path=tabtabtab_path)
            prefs_module.use_tabtabtab_prefs = True
            self._refresh_without_installed_module(prefs_module)

            # The user changes the mapping in tabtabtab's own dialog mid-session
            self._write_tabtabtab_prefs(tabtabtab_path, [NON_ANCHORED, CONSECUTIVE, ANCHORED])
            self._refresh_without_installed_module(prefs_module)

            self.assertEqual(prefs_module.space_mode_order,
                             [NON_ANCHORED, CONSECUTIVE, ANCHORED])

    def test_installed_module_without_a_prefs_file_is_still_an_install(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prefs_module = self._reload_prefs(temp_dir)
            installed_module = types.SimpleNamespace(
                PREFS_FILE=os.path.join(temp_dir, 'never_written.json'),
            )

            with patch.object(prefs_module, '_tabtabtab_prefs_module',
                              return_value=installed_module):
                prefs_module.refresh_tabtabtab_prefs()

            self.assertTrue(
                prefs_module.tabtabtab_prefs_available(),
                "tabtabtab-nuke installed but never configured still runs on its defaults",
            )
            self.assertEqual(prefs_module.tabtabtab_space_mode_order(),
                             [ANCHORED, NON_ANCHORED, CONSECUTIVE])

    def test_installed_module_prefs_file_location_is_honoured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            relocated_path = os.path.join(temp_dir, 'elsewhere', 'tabtabtab_prefs.json')
            os.makedirs(os.path.dirname(relocated_path))
            self._write_tabtabtab_prefs(relocated_path, [CONSECUTIVE, NON_ANCHORED, ANCHORED])
            prefs_module = self._reload_prefs(temp_dir)
            installed_module = types.SimpleNamespace(PREFS_FILE=relocated_path)

            prefs_module.use_tabtabtab_prefs = True
            with patch.object(prefs_module, '_tabtabtab_prefs_module',
                              return_value=installed_module):
                prefs_module.refresh_tabtabtab_prefs()

            self.assertEqual(prefs_module.space_mode_order,
                             [CONSECUTIVE, NON_ANCHORED, ANCHORED])


# ---------------------------------------------------------------------------
# PrefsDialog behaviour — Qt is a MagicMock in tests, so the dialog methods are
# extracted from source and run against a stand-in dialog object.
# ---------------------------------------------------------------------------

def _extract_prefs_dialog_method(method_name, namespace):
    """Compile a PrefsDialog method from colors.py inside *namespace*.

    Mirrors the extraction helper in test_anchor_color_system.py: the real Qt
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


class _StubComboBox:
    """Minimal QComboBox stand-in: item data, current index, enabled state."""

    def __init__(self, mode_ids):
        self._mode_ids = list(mode_ids)
        self._current_index = 0
        self.enabled = True

    def findData(self, mode_id):
        try:
            return self._mode_ids.index(mode_id)
        except ValueError:
            return -1

    def setCurrentIndex(self, index):
        self._current_index = index

    def currentData(self):
        return self._mode_ids[self._current_index]

    def setEnabled(self, is_enabled):
        self.enabled = is_enabled


class _StubCheckBox:
    def __init__(self):
        self.enabled = True
        self.tooltip = ''

    def setEnabled(self, is_enabled):
        self.enabled = is_enabled

    def setToolTip(self, tooltip_text):
        self.tooltip = tooltip_text


class _StubPrefsDialog:
    """Stand-in dialog carrying just the state the space-mode methods touch."""

    MODE_IDS = (ANCHORED, NON_ANCHORED, CONSECUTIVE)

    def __init__(self, local_order, use_tabtabtab_prefs):
        self._local_space_mode_order = list(local_order)
        self._local_use_tabtabtab_prefs = use_tabtabtab_prefs
        self._space_mode_comboboxes = [_StubComboBox(self.MODE_IDS) for _ in range(3)]
        self._use_tabtabtab_prefs_checkbox = _StubCheckBox()
        for space_level, combobox in enumerate(self._space_mode_comboboxes):
            combobox.setCurrentIndex(combobox.findData(local_order[space_level]))

    def __getattr__(self, attribute_name):
        # Any widget the method touches beyond the space-mode ones is irrelevant
        # here; hand back a mock so the method body can run to completion.
        if attribute_name.startswith('__'):
            raise AttributeError(attribute_name)
        stand_in = MagicMock(name=attribute_name)
        setattr(self, attribute_name, stand_in)
        return stand_in

    def bind(self, method_name, namespace=None):
        """Attach a PrefsDialog method to this stand-in and return it."""
        method = _extract_prefs_dialog_method(method_name, namespace or {})
        assert method is not None, "PrefsDialog.{} not found".format(method_name)
        bound_method = method.__get__(self, type(self))
        setattr(self, method_name, bound_method)
        return bound_method


class TestPrefsDialogSpaceModeWidgets(_SpaceModePrefsTestCase):
    """The dialog greys the mapping out exactly when tabtabtab is being followed."""

    def _prefs_stub(self, tabtabtab_available, tabtabtab_order=None):
        """Install a stub prefs module so the dialog methods import it."""
        prefs_stub = types.ModuleType('prefs')
        prefs_stub.tabtabtab_prefs_available = lambda: tabtabtab_available
        prefs_stub.tabtabtab_space_mode_order = lambda: list(
            tabtabtab_order or [ANCHORED, NON_ANCHORED, CONSECUTIVE]
        )
        prefs_stub.is_valid_space_mode_order = lambda order: (
            isinstance(order, list)
            and sorted(order) == sorted([ANCHORED, NON_ANCHORED, CONSECUTIVE])
        )
        sys.modules['prefs'] = prefs_stub
        self.addCleanup(lambda: sys.modules.pop('prefs', None))
        return prefs_stub

    def test_combo_boxes_are_greyed_out_while_following_tabtabtab(self):
        self._prefs_stub(tabtabtab_available=True)
        dialog = _StubPrefsDialog([ANCHORED, NON_ANCHORED, CONSECUTIVE],
                                  use_tabtabtab_prefs=True)
        dialog.bind('_is_following_tabtabtab_prefs')
        dialog.bind('_update_space_mode_fields_lock_state')()

        self.assertTrue(dialog._use_tabtabtab_prefs_checkbox.enabled)
        for combobox in dialog._space_mode_comboboxes:
            self.assertFalse(combobox.enabled,
                             "the mapping must be greyed out while tabtabtab is followed")

    def test_combo_boxes_are_editable_when_not_following(self):
        self._prefs_stub(tabtabtab_available=True)
        dialog = _StubPrefsDialog([ANCHORED, NON_ANCHORED, CONSECUTIVE],
                                  use_tabtabtab_prefs=False)
        dialog.bind('_is_following_tabtabtab_prefs')
        dialog.bind('_update_space_mode_fields_lock_state')()

        for combobox in dialog._space_mode_comboboxes:
            self.assertTrue(combobox.enabled)

    def test_checkbox_is_greyed_out_without_a_tabtabtab_install(self):
        self._prefs_stub(tabtabtab_available=False)
        dialog = _StubPrefsDialog([ANCHORED, NON_ANCHORED, CONSECUTIVE],
                                  use_tabtabtab_prefs=False)
        dialog.bind('_is_following_tabtabtab_prefs')
        dialog.bind('_update_space_mode_fields_lock_state')()

        self.assertFalse(dialog._use_tabtabtab_prefs_checkbox.enabled)
        self.assertIn('tabtabtab', dialog._use_tabtabtab_prefs_checkbox.tooltip)
        for combobox in dialog._space_mode_comboboxes:
            self.assertTrue(combobox.enabled,
                            "with nothing to follow, the user's own mapping stays editable")

    def test_a_saved_follow_choice_is_inert_without_an_install(self):
        """Ticked but nothing installed: the boxes must show what is really in force."""
        self._prefs_stub(tabtabtab_available=False)
        dialog = _StubPrefsDialog([NON_ANCHORED, CONSECUTIVE, ANCHORED],
                                  use_tabtabtab_prefs=True)
        dialog.bind('_is_following_tabtabtab_prefs')
        dialog.bind('_selected_space_mode_order')
        dialog.bind('_displayed_space_mode_order')
        dialog.bind('_populate_space_mode_comboboxes')()
        dialog.bind('_update_space_mode_fields_lock_state')()

        self.assertEqual(dialog._selected_space_mode_order(),
                         [NON_ANCHORED, CONSECUTIVE, ANCHORED],
                         "prefs falls back to the user's mapping, so the dialog must show it")
        for combobox in dialog._space_mode_comboboxes:
            self.assertTrue(combobox.enabled,
                            "nothing is enforcing the mapping, so it stays editable")

    def test_toggling_on_shows_tabtabtab_order_and_keeps_the_user_mapping(self):
        self._prefs_stub(tabtabtab_available=True,
                         tabtabtab_order=[CONSECUTIVE, ANCHORED, NON_ANCHORED])
        dialog = _StubPrefsDialog([NON_ANCHORED, CONSECUTIVE, ANCHORED],
                                  use_tabtabtab_prefs=False)
        dialog.bind('_selected_space_mode_order')
        dialog.bind('_is_following_tabtabtab_prefs')
        dialog.bind('_displayed_space_mode_order')
        dialog.bind('_populate_space_mode_comboboxes')
        dialog.bind('_update_space_mode_fields_lock_state')
        toggle = dialog.bind('_on_use_tabtabtab_prefs_toggled')

        toggle(True)

        self.assertEqual(dialog._selected_space_mode_order(),
                         [CONSECUTIVE, ANCHORED, NON_ANCHORED],
                         "the greyed boxes must show what tabtabtab is enforcing")
        self.assertEqual(dialog._local_space_mode_order,
                         [NON_ANCHORED, CONSECUTIVE, ANCHORED],
                         "the user's own mapping must be kept for when they untick")

        toggle(False)

        self.assertEqual(dialog._selected_space_mode_order(),
                         [NON_ANCHORED, CONSECUTIVE, ANCHORED])
        for combobox in dialog._space_mode_comboboxes:
            self.assertTrue(combobox.enabled)


class TestPrefsDialogAcceptValidation(unittest.TestCase):
    """OK must refuse a mapping that assigns one mode to two space levels."""

    def _run_on_accept(self, selected_order, use_tabtabtab_prefs=False):
        """Run PrefsDialog._on_accept against stand-in widgets and a mock prefs."""
        namespace = {'QtWidgets': MagicMock()}
        prefs_mock = MagicMock(name='prefs')
        prefs_mock.is_valid_space_mode_order.side_effect = lambda order: (
            isinstance(order, list)
            and sorted(order) == sorted([ANCHORED, NON_ANCHORED, CONSECUTIVE])
        )
        prefs_mock.tabtabtab_prefs_available.return_value = True
        original_prefs_module = sys.modules.get('prefs')
        sys.modules['prefs'] = prefs_mock
        try:
            dialog = _StubPrefsDialog([ANCHORED, NON_ANCHORED, CONSECUTIVE],
                                      use_tabtabtab_prefs=use_tabtabtab_prefs)
            for space_level, mode_id in enumerate(selected_order):
                combobox = dialog._space_mode_comboboxes[space_level]
                combobox.setCurrentIndex(combobox.findData(mode_id))
            dialog.bind('_selected_space_mode_order')
            dialog.bind('_is_following_tabtabtab_prefs')
            on_accept = dialog.bind('_on_accept', namespace)
            on_accept()
        finally:
            if original_prefs_module is not None:
                sys.modules['prefs'] = original_prefs_module
            else:
                sys.modules.pop('prefs', None)
        return dialog, prefs_mock, namespace['QtWidgets']

    def test_duplicate_mapping_is_rejected_before_anything_is_flushed(self):
        dialog, prefs_mock, qt_widgets = self._run_on_accept(
            [ANCHORED, ANCHORED, CONSECUTIVE])

        qt_widgets.QMessageBox.warning.assert_called_once()
        prefs_mock.save.assert_not_called()
        dialog.accept.assert_not_called()

    def test_valid_mapping_is_flushed_and_accepted(self):
        dialog, prefs_mock, qt_widgets = self._run_on_accept(
            [CONSECUTIVE, ANCHORED, NON_ANCHORED])

        qt_widgets.QMessageBox.warning.assert_not_called()
        self.assertEqual(prefs_mock._user_space_mode_order,
                         [CONSECUTIVE, ANCHORED, NON_ANCHORED])
        self.assertFalse(prefs_mock.use_tabtabtab_prefs)
        prefs_mock.refresh_tabtabtab_prefs.assert_called_once()
        prefs_mock.save.assert_called_once()
        dialog.accept.assert_called_once()

    def test_following_tabtabtab_leaves_the_user_mapping_alone(self):
        """The greyed boxes mirror tabtabtab — they must not overwrite the user's own."""
        dialog, prefs_mock, qt_widgets = self._run_on_accept(
            [CONSECUTIVE, ANCHORED, NON_ANCHORED], use_tabtabtab_prefs=True)

        prefs_mock.is_valid_space_mode_order.assert_not_called()
        prefs_mock.save.assert_called_once()
        self.assertEqual(prefs_mock._user_space_mode_order,
                         [ANCHORED, NON_ANCHORED, CONSECUTIVE])
        self.assertTrue(prefs_mock.use_tabtabtab_prefs)


class TestPickersReceiveSpaceModeOrder(unittest.TestCase):
    """The pickers must actually be handed the effective mapping."""

    def test_every_picker_construction_passes_space_mode_order(self):
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
                'space_mode_order', keyword_names,
                "TabTabTabWidget at anchor.py:{} must be given the mode order".format(
                    call_node.lineno),
            )

    def test_cached_pickers_have_the_order_reapplied(self):
        import anchor as anchor_module

        picker_widget = MagicMock()
        with patch.object(anchor_module.prefs, 'use_tabtabtab_prefs', False), \
                patch.object(anchor_module.prefs, 'space_mode_order',
                             [CONSECUTIVE, ANCHORED, NON_ANCHORED]):
            anchor_module._apply_space_mode_order(picker_widget)

        self.assertEqual(picker_widget.things_model._space_mode_order,
                         [CONSECUTIVE, ANCHORED, NON_ANCHORED])


if __name__ == '__main__':
    unittest.main()
