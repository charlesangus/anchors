"""Tests for prefs.py — preferences singleton for the anchors plugin.

Covers:
- PREFS-01: _load() creates the prefs file on first run (file-absent branch calls save())
- PREFS-01: File written contains all three required keys
- PREFS-01: Legacy migration path still creates file with colors from old palette
"""

import json
import os
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Stub nuke module — prefs.py imports constants which may trigger nuke stubs
# in other modules. Provide a minimal stub so imports succeed.
# ---------------------------------------------------------------------------
if 'nuke' not in sys.modules:
    nuke_stub = types.ModuleType('nuke')
    nuke_stub.NUKE_VERSION_MAJOR = 14
    sys.modules['nuke'] = nuke_stub


class TestPrefsFirstRunCreatesFile(unittest.TestCase):
    """PREFS-01: prefs file is created on disk when it does not exist."""

    def _reload_prefs(self, temp_prefs_path, temp_palette_path):
        """Remove cached prefs module and reload with patched paths."""
        if 'prefs' in sys.modules:
            del sys.modules['prefs']
        with patch('constants.PREFS_PATH', temp_prefs_path), \
             patch('constants.USER_PALETTE_PATH', temp_palette_path):
            import prefs as prefs_module
            # Re-patch the module-level names that were captured at import
            prefs_module.PREFS_PATH = temp_prefs_path  # noqa: used for save() path inspection
        return prefs_module

    def setUp(self):
        # Remove cached prefs module before each test so _load() runs fresh
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def tearDown(self):
        # Remove cached prefs module after each test to avoid bleed-through
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def test_file_created_on_first_run_no_old_palette(self):
        """When prefs file absent and no old palette, importing prefs creates the file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            temp_palette_path = os.path.join(temp_dir, 'paste_hidden_user_palette.json')
            # Neither file exists
            self.assertFalse(os.path.exists(temp_prefs_path))
            self.assertFalse(os.path.exists(temp_palette_path))

            with patch('constants.PREFS_PATH', temp_prefs_path), \
                 patch('constants.USER_PALETTE_PATH', temp_palette_path):
                import prefs
                # Patch the PREFS_PATH constant in prefs module so save() writes to temp location
                prefs.PREFS_PATH = temp_prefs_path  # noqa: direct attribute patch
                # Re-run _load() with patched paths to simulate fresh import
                del sys.modules['prefs']

            # Re-import with both constants patched at the source
            with patch.dict('sys.modules', {}):
                pass  # clean up handled in tearDown

            # Direct approach: patch at the constants module level
            import constants
            original_prefs_path = constants.PREFS_PATH
            original_palette_path = constants.USER_PALETTE_PATH
            try:
                constants.PREFS_PATH = temp_prefs_path
                constants.USER_PALETTE_PATH = temp_palette_path
                if 'prefs' in sys.modules:
                    del sys.modules['prefs']
                import prefs
                self.assertTrue(
                    os.path.exists(temp_prefs_path),
                    "prefs file should be created on first run when it does not exist",
                )
                with open(temp_prefs_path) as file_handle:
                    data = json.load(file_handle)
                self.assertIn('plugin_enabled', data, "prefs file must contain plugin_enabled key")
                self.assertIn('link_classes_paste_mode', data,
                              "prefs file must contain link_classes_paste_mode key")
                self.assertIn('custom_colors', data, "prefs file must contain custom_colors key")
                self.assertEqual(data['plugin_enabled'], True)
                self.assertEqual(data['link_classes_paste_mode'], 'create_link')
                self.assertEqual(data['custom_colors'], [])
            finally:
                constants.PREFS_PATH = original_prefs_path
                constants.USER_PALETTE_PATH = original_palette_path
                if 'prefs' in sys.modules:
                    del sys.modules['prefs']

    def test_file_created_on_first_run_with_old_palette(self):
        """When prefs file absent but old palette exists, file is created with migrated colors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            temp_palette_path = os.path.join(temp_dir, 'paste_hidden_user_palette.json')
            # Write old palette file with some colors
            legacy_colors = [0x6f3399ff, 0xff0000ff]
            with open(temp_palette_path, 'w') as file_handle:
                json.dump(legacy_colors, file_handle)
            self.assertFalse(os.path.exists(temp_prefs_path))

            import constants
            original_prefs_path = constants.PREFS_PATH
            original_palette_path = constants.USER_PALETTE_PATH
            original_old_prefs_path = constants.OLD_PREFS_PATH
            try:
                constants.PREFS_PATH = temp_prefs_path
                constants.USER_PALETTE_PATH = temp_palette_path
                constants.OLD_PREFS_PATH = os.path.join(temp_dir, 'nonexistent_old_prefs.json')
                if 'prefs' in sys.modules:
                    del sys.modules['prefs']
                import prefs
                self.assertTrue(
                    os.path.exists(temp_prefs_path),
                    "prefs file should be created on first run when old palette exists",
                )
                with open(temp_prefs_path) as file_handle:
                    data = json.load(file_handle)
                self.assertIn('custom_colors', data, "prefs file must contain custom_colors key")
                self.assertEqual(data['custom_colors'], legacy_colors,
                                 "migrated colors should be written to new prefs file")
            finally:
                constants.OLD_PREFS_PATH = original_old_prefs_path
                constants.PREFS_PATH = original_prefs_path
                constants.USER_PALETTE_PATH = original_palette_path
                if 'prefs' in sys.modules:
                    del sys.modules['prefs']

    def test_save_not_called_when_file_already_exists(self):
        """When prefs file already exists, _load() does NOT overwrite it."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            temp_palette_path = os.path.join(temp_dir, 'paste_hidden_user_palette.json')
            # Pre-create the prefs file with non-default values
            existing_data = {
                'plugin_enabled': False,
                'link_classes_paste_mode': 'passthrough',
                'custom_colors': [0xdeadbeef],
            }
            with open(temp_prefs_path, 'w') as file_handle:
                json.dump(existing_data, file_handle)
            original_mtime = os.path.getmtime(temp_prefs_path)

            import constants
            original_prefs_path = constants.PREFS_PATH
            original_palette_path = constants.USER_PALETTE_PATH
            try:
                constants.PREFS_PATH = temp_prefs_path
                constants.USER_PALETTE_PATH = temp_palette_path
                if 'prefs' in sys.modules:
                    del sys.modules['prefs']
                import prefs
                # File should still exist and content should be unchanged (not overwritten)
                with open(temp_prefs_path) as file_handle:
                    data = json.load(file_handle)
                self.assertEqual(data['plugin_enabled'], False,
                                 "existing prefs should not be overwritten on load")
                self.assertEqual(data['link_classes_paste_mode'], 'passthrough')
            finally:
                constants.PREFS_PATH = original_prefs_path
                constants.USER_PALETTE_PATH = original_palette_path
                if 'prefs' in sys.modules:
                    del sys.modules['prefs']


class TestNamingPrefsRoundTrip(unittest.TestCase):
    """Round-trip tests for naming_regex and naming_template persistence.

    These tests are Wave 0 (TDD RED): they will fail with AttributeError until
    Plan 02 adds naming_regex and naming_template to prefs.py.

    Pattern mirrors TestPrefsFirstRunCreatesFile: patch constants.PREFS_PATH
    to a temp file, delete and re-import the prefs module, then assert values.
    """

    def setUp(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def tearDown(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def _reload_prefs_with_temp_path(self, temp_prefs_path):
        """Helper: reload prefs with PREFS_PATH pointing at temp_prefs_path."""
        import constants
        original_prefs_path = constants.PREFS_PATH
        original_palette_path = constants.USER_PALETTE_PATH
        original_old_prefs_path = constants.OLD_PREFS_PATH
        try:
            constants.PREFS_PATH = temp_prefs_path
            constants.USER_PALETTE_PATH = temp_prefs_path + '.palette_unused'
            constants.OLD_PREFS_PATH = temp_prefs_path + '.old_unused'
            if 'prefs' in sys.modules:
                del sys.modules['prefs']
            import prefs as reloaded_prefs
            reloaded_prefs.PREFS_PATH = temp_prefs_path
            return reloaded_prefs
        finally:
            constants.PREFS_PATH = original_prefs_path
            constants.USER_PALETTE_PATH = original_palette_path
            constants.OLD_PREFS_PATH = original_old_prefs_path

    def test_naming_fields_written_to_prefs_file(self):
        """save() writes naming_regex and naming_template keys to the JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            prefs_module.naming_regex = r'(?P<shot>.+)_v\d+'
            prefs_module.naming_template = '{shot}'
            prefs_module.save()

            with open(temp_prefs_path) as file_handle:
                data = json.load(file_handle)

            self.assertIn('naming_regex', data,
                          "save() must write naming_regex key to JSON")
            self.assertIn('naming_template', data,
                          "save() must write naming_template key to JSON")
            self.assertEqual(data['naming_regex'], r'(?P<shot>.+)_v\d+')
            self.assertEqual(data['naming_template'], '{shot}')

    def test_naming_fields_loaded_from_prefs_file(self):
        """_load() reads naming_regex and naming_template from JSON into module vars."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')

            # Write a prefs file with naming fields pre-populated
            prefs_data = {
                'plugin_enabled': True,
                'link_classes_paste_mode': 'create_link',
                'custom_colors': [],
                'naming_regex': r'(?P<name>\w+)',
                'naming_template': '{name}_anchor',
            }
            with open(temp_prefs_path, 'w') as file_handle:
                json.dump(prefs_data, file_handle)

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(prefs_module.naming_regex, r'(?P<name>\w+)',
                             "_load() must read naming_regex from JSON")
            self.assertEqual(prefs_module.naming_template, '{name}_anchor',
                             "_load() must read naming_template from JSON")

    def test_naming_fields_default_to_empty_string(self):
        """On fresh import with no prefs file, naming_regex and naming_template default to ''."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            # Do NOT create the prefs file — simulate fresh install
            self.assertFalse(os.path.exists(temp_prefs_path))

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(prefs_module.naming_regex, '',
                             "naming_regex must default to '' when no prefs file exists")
            self.assertEqual(prefs_module.naming_template, '',
                             "naming_template must default to '' when no prefs file exists")

    def test_naming_fields_type_validation(self):
        """Non-string values for naming_regex or naming_template in JSON are ignored (stay '')."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')

            # Write a prefs file with invalid types for naming fields
            prefs_data = {
                'plugin_enabled': True,
                'link_classes_paste_mode': 'create_link',
                'custom_colors': [],
                'naming_regex': 42,          # int — not a string
                'naming_template': ['list'], # list — not a string
            }
            with open(temp_prefs_path, 'w') as file_handle:
                json.dump(prefs_data, file_handle)

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(prefs_module.naming_regex, '',
                             "non-string naming_regex must be ignored; module var stays ''")
            self.assertEqual(prefs_module.naming_template, '',
                             "non-string naming_template must be ignored; module var stays ''")


if __name__ == '__main__':
    unittest.main()
