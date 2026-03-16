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


if __name__ == '__main__':
    unittest.main()
