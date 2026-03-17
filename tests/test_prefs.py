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
        """save() writes naming_regex and naming_template keys to the JSON file.

        Phase 16: save() reads from _user_naming_* shadow vars (not effective naming_* vars)
        so user values are preserved even when site config overrides the effective values.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            # Set shadow vars (user's own values) — save() reads these
            prefs_module._user_naming_regex = r'(?P<shot>.+)_v\d+'
            prefs_module._user_naming_template = '{shot}'
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


class TestNamingDemoFilenameRoundTrip(unittest.TestCase):
    """Round-trip tests for naming_demo_filename preference field (PREF-03).

    Verifies that naming_demo_filename defaults to 'plate_v003.exr', survives
    a save/load cycle, and rejects non-string values from JSON.
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

    def test_naming_demo_filename_default(self):
        """On fresh import with no prefs file, naming_demo_filename == 'plate_v003.exr'."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            # Do NOT create the prefs file — simulate fresh install
            self.assertFalse(os.path.exists(temp_prefs_path))

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_demo_filename,
                'plate_v003.exr',
                "naming_demo_filename must default to 'plate_v003.exr' when no prefs file exists",
            )

    def test_naming_demo_filename_round_trip(self):
        """save() writes 'naming_demo_filename' key; _load() reads it back into module var.

        Phase 16: save() reads from _user_naming_demo_filename shadow var (not effective
        naming_demo_filename var) to preserve user values under site config.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            # Set shadow var — save() reads _user_naming_demo_filename
            prefs_module._user_naming_demo_filename = 'shot_v007.dpx'
            prefs_module.save()

            # Verify the JSON file contains the key
            with open(temp_prefs_path) as file_handle:
                data = json.load(file_handle)
            self.assertIn('naming_demo_filename', data,
                          "save() must write naming_demo_filename key to JSON")
            self.assertEqual(data['naming_demo_filename'], 'shot_v007.dpx')

            # Reload from the written file and verify the value is restored
            prefs_module2 = self._reload_prefs_with_temp_path(temp_prefs_path)
            self.assertEqual(
                prefs_module2.naming_demo_filename,
                'shot_v007.dpx',
                "naming_demo_filename must survive a save/load round-trip",
            )

    def test_naming_demo_filename_type_validation(self):
        """Non-string value in JSON ('naming_demo_filename': 42) is ignored; module var stays at default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')

            prefs_data = {
                'plugin_enabled': True,
                'link_classes_paste_mode': 'create_link',
                'custom_colors': [],
                'naming_regex': '',
                'naming_template': '',
                'naming_demo_filename': 42,  # int — not a string, must be ignored
            }
            with open(temp_prefs_path, 'w') as file_handle:
                json.dump(prefs_data, file_handle)

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_demo_filename,
                'plate_v003.exr',
                "non-string naming_demo_filename must be ignored; module var stays at default",
            )


class TestPublish(unittest.TestCase):
    """Unit tests for prefs.publish(destination_path) (PREF-05/06).

    publish() writes all current prefs to a caller-supplied path without
    touching the default PREFS_PATH file or any module-level variables.
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

    def test_publish_writes_to_given_path(self):
        """publish(path) creates a sparse site config JSON containing ONLY naming fields.

        Phase 16: publish() must write only naming_regex, naming_template,
        naming_demo_filename. Non-naming fields (plugin_enabled,
        link_classes_paste_mode, custom_colors) must be absent.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            default_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            alt_publish_path = os.path.join(temp_dir, 'published_prefs.json')

            prefs_module = self._reload_prefs_with_temp_path(default_prefs_path)

            # Set recognisable values on the naming fields
            prefs_module.naming_regex = r'(?P<shot>.+)'
            prefs_module.naming_template = '{shot}'
            prefs_module.naming_demo_filename = 'clip_v001.exr'

            prefs_module.publish(alt_publish_path)

            self.assertTrue(
                os.path.exists(alt_publish_path),
                "publish() must create a file at the given destination path",
            )
            with open(alt_publish_path) as file_handle:
                data = json.load(file_handle)

            # Naming fields must be present with correct values
            self.assertEqual(data.get('naming_regex'), r'(?P<shot>.+)')
            self.assertEqual(data.get('naming_template'), '{shot}')
            self.assertEqual(data.get('naming_demo_filename'), 'clip_v001.exr')

            # Non-naming fields must be absent from the published site config
            self.assertNotIn(
                'plugin_enabled', data,
                "publish() must NOT write plugin_enabled — site config must be naming-only",
            )
            self.assertNotIn(
                'link_classes_paste_mode', data,
                "publish() must NOT write link_classes_paste_mode — site config must be naming-only",
            )
            self.assertNotIn(
                'custom_colors', data,
                "publish() must NOT write custom_colors — site config must be naming-only",
            )

    def test_publish_does_not_modify_default_prefs_file(self):
        """After publish(alt_path), the default PREFS_PATH file is unchanged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            default_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            alt_publish_path = os.path.join(temp_dir, 'site_config.json')

            prefs_module = self._reload_prefs_with_temp_path(default_prefs_path)
            # Force the default prefs file to exist (save() writes it on first run)
            prefs_module.save()

            default_mtime_before = os.path.getmtime(default_prefs_path)

            prefs_module.publish(alt_publish_path)

            default_mtime_after = os.path.getmtime(default_prefs_path)
            self.assertEqual(
                default_mtime_before,
                default_mtime_after,
                "publish() must not touch the default PREFS_PATH file",
            )
            self.assertFalse(
                os.path.exists(default_prefs_path + '_backup'),
                "publish() must not create backup or side-effect files",
            )

    def test_publish_creates_parent_directories(self):
        """If the parent directory does not exist, publish() creates it."""
        with tempfile.TemporaryDirectory() as temp_dir:
            default_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            nested_publish_path = os.path.join(temp_dir, 'subdir', 'deep', 'site_config.json')

            prefs_module = self._reload_prefs_with_temp_path(default_prefs_path)

            # Parent directories do not exist yet
            self.assertFalse(os.path.exists(os.path.dirname(nested_publish_path)))

            prefs_module.publish(nested_publish_path)

            self.assertTrue(
                os.path.exists(nested_publish_path),
                "publish() must create parent directories and the destination file",
            )
            with open(nested_publish_path) as file_handle:
                data = json.load(file_handle)
            # Phase 16: publish() writes only naming fields (sparse site config format)
            self.assertIn('naming_regex', data)


class TestSiteConfigLoading(unittest.TestCase):
    """Tests for ANCHORS_SITE_CONFIG env var loading and field locking behavior.

    These are Wave 0 TDD tests — they FAIL (RED) before Plan 02 adds site config
    support to prefs.py. Attributes _site_config, _user_naming_regex,
    _user_naming_template, _user_naming_demo_filename, and site_config_override
    do not exist on the prefs module until Plan 02.

    Each test uses _reload_prefs_with_temp_path to reload the prefs module with
    ANCHORS_SITE_CONFIG set in the environment before the import so _load() reads it.
    """

    def setUp(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']
        # Clear the env var before each test so tests start from a clean state
        os.environ.pop('ANCHORS_SITE_CONFIG', None)

    def tearDown(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']
        # Remove the env var after each test to avoid bleed-through
        os.environ.pop('ANCHORS_SITE_CONFIG', None)

    def _reload_prefs_with_temp_path(self, temp_prefs_path):
        """Helper: reload prefs with PREFS_PATH pointing at temp_prefs_path.

        ANCHORS_SITE_CONFIG must be set in os.environ BEFORE calling this helper
        so that _load() reads it during module import. The caller is responsible
        for setting and clearing ANCHORS_SITE_CONFIG.
        """
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

    def _write_user_prefs(self, temp_prefs_path, **overrides):
        """Write a minimal user prefs JSON file with optional field overrides."""
        user_prefs_data = {
            'plugin_enabled': True,
            'link_classes_paste_mode': 'create_link',
            'custom_colors': [],
            'naming_regex': 'user_regex',
            'naming_template': 'user_template',
            'naming_demo_filename': 'user_demo.exr',
        }
        user_prefs_data.update(overrides)
        with open(temp_prefs_path, 'w') as file_handle:
            json.dump(user_prefs_data, file_handle)

    def _write_site_config(self, site_config_path, **fields):
        """Write a site config JSON file with the given naming fields."""
        with open(site_config_path, 'w') as file_handle:
            json.dump(fields, file_handle)

    def test_site_config_values_applied_as_effective_values(self):
        """When ANCHORS_SITE_CONFIG points to a valid file, its values become effective values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            site_config_path = os.path.join(temp_dir, 'site_config.json')

            self._write_user_prefs(temp_prefs_path, naming_regex='user_regex')
            self._write_site_config(
                site_config_path,
                naming_regex=r'(?P<shot>.+)_v\d+',
            )

            os.environ['ANCHORS_SITE_CONFIG'] = site_config_path
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                r'(?P<shot>.+)_v\d+',
                "Site config value must override user prefs value as the effective value",
            )

    def test_site_config_missing_env_var_is_silent_noop(self):
        """When ANCHORS_SITE_CONFIG is not set, prefs loads normally from user prefs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')

            self._write_user_prefs(temp_prefs_path, naming_regex='user_regex')
            # ANCHORS_SITE_CONFIG is already cleared in setUp — do not set it

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                'user_regex',
                "Without ANCHORS_SITE_CONFIG, naming_regex must equal the user prefs value",
            )

    def test_site_config_corrupt_file_is_silent_noop(self):
        """When ANCHORS_SITE_CONFIG points to a corrupt JSON file, prefs loads from user prefs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            corrupt_site_config_path = os.path.join(temp_dir, 'corrupt_site_config.json')

            self._write_user_prefs(temp_prefs_path, naming_regex='user_regex')
            # Write a corrupt (non-JSON) file
            with open(corrupt_site_config_path, 'w') as file_handle:
                file_handle.write('{ this is not valid JSON !!!}')

            os.environ['ANCHORS_SITE_CONFIG'] = corrupt_site_config_path
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                'user_regex',
                "Corrupt site config must be silently ignored; naming_regex must equal user prefs value",
            )

    def test_site_config_missing_file_path_is_silent_noop(self):
        """When ANCHORS_SITE_CONFIG points to a non-existent file, prefs loads from user prefs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            nonexistent_path = os.path.join(temp_dir, 'does_not_exist.json')

            self._write_user_prefs(temp_prefs_path, naming_regex='user_regex')
            self.assertFalse(os.path.exists(nonexistent_path))

            os.environ['ANCHORS_SITE_CONFIG'] = nonexistent_path
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                'user_regex',
                "Missing site config file must be silently ignored; naming_regex must equal user prefs value",
            )

    def test_site_config_locks_fields_user_values_preserved_in_shadow_vars(self):
        """When site config sets naming_regex, effective value is admin's; shadow var holds user's."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            site_config_path = os.path.join(temp_dir, 'site_config.json')

            self._write_user_prefs(temp_prefs_path, naming_regex='user_regex')
            self._write_site_config(site_config_path, naming_regex='admin_regex')

            os.environ['ANCHORS_SITE_CONFIG'] = site_config_path
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                'admin_regex',
                "Effective naming_regex must be the site config (admin) value",
            )
            self.assertEqual(
                prefs_module._user_naming_regex,
                'user_regex',
                "_user_naming_regex shadow var must hold the user's own saved value",
            )

    def test_site_config_override_true_uses_user_values(self):
        """When site_config_override=True in user prefs, user's values win over site config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            site_config_path = os.path.join(temp_dir, 'site_config.json')

            self._write_user_prefs(
                temp_prefs_path,
                naming_regex='user_regex',
                site_config_override=True,
            )
            self._write_site_config(site_config_path, naming_regex='admin_regex')

            os.environ['ANCHORS_SITE_CONFIG'] = site_config_path
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                'user_regex',
                "When site_config_override=True, user's naming_regex must win over site config",
            )

    def test_site_config_override_round_trip(self):
        """site_config_override=True persists through save() and is restored on reload."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')

            self._write_user_prefs(temp_prefs_path, site_config_override=True)

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertIs(
                prefs_module.site_config_override,
                True,
                "site_config_override must be True after loading prefs with site_config_override=True",
            )

            prefs_module.save()

            prefs_module2 = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertIs(
                prefs_module2.site_config_override,
                True,
                "site_config_override must still be True after save() and reload",
            )

    def test_site_config_absent_fields_not_locked(self):
        """Fields absent from site config are not locked — they use the user's own values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            site_config_path = os.path.join(temp_dir, 'site_config.json')

            self._write_user_prefs(
                temp_prefs_path,
                naming_regex='user_regex',
                naming_template='user_template',
            )
            # Site config only sets naming_regex — naming_template is absent
            self._write_site_config(site_config_path, naming_regex='admin_regex')

            os.environ['ANCHORS_SITE_CONFIG'] = site_config_path
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.naming_regex,
                'admin_regex',
                "naming_regex must be the site config value (it is present in site config)",
            )
            self.assertEqual(
                prefs_module.naming_template,
                'user_template',
                "naming_template must be the user's value (it is absent from site config)",
            )


class TestLastPublishPath(unittest.TestCase):
    """Round-trip tests for the last_publish_path preference field.

    last_publish_path records the most recently chosen publish destination so
    that the next publish dialog can pre-fill the same path.
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

    def test_last_publish_path_round_trips(self):
        """last_publish_path persists through save() and is restored on reload."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            prefs_module.last_publish_path = '/tmp/myconfig.json'
            prefs_module.save()

            prefs_module2 = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module2.last_publish_path,
                '/tmp/myconfig.json',
                "last_publish_path must survive a save/load round-trip",
            )

    def test_last_publish_path_defaults_to_empty_string(self):
        """On fresh import with no prefs file, last_publish_path defaults to ''."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')
            # Do NOT create the prefs file — simulate fresh install
            self.assertFalse(os.path.exists(temp_prefs_path))

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.last_publish_path,
                '',
                "last_publish_path must default to '' when no prefs file exists",
            )

    def test_last_publish_path_non_string_in_json_is_ignored(self):
        """Non-string value for last_publish_path in JSON is ignored; module var stays ''."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_prefs_path = os.path.join(temp_dir, 'anchors_prefs.json')

            prefs_data = {
                'plugin_enabled': True,
                'link_classes_paste_mode': 'create_link',
                'custom_colors': [],
                'naming_regex': '',
                'naming_template': '',
                'naming_demo_filename': 'plate_v003.exr',
                'site_config_override': False,
                'last_publish_path': 42,  # int — not a string, must be ignored
            }
            with open(temp_prefs_path, 'w') as file_handle:
                json.dump(prefs_data, file_handle)

            prefs_module = self._reload_prefs_with_temp_path(temp_prefs_path)

            self.assertEqual(
                prefs_module.last_publish_path,
                '',
                "non-string last_publish_path must be ignored; module var stays ''",
            )


if __name__ == '__main__':
    unittest.main()
