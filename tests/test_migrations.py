"""Tests for migrations.py — knob renames, prefs migration, palette migration.

Covers:
- migrate_script() rewrites every entry in LEGACY_TO_NEW_KNOB_NAMES.
- PyScript_Knob renames preserve the canonical button label and python body.
- Idempotent re-runs are no-ops.
- Mixed state (old AND new both present) leaves both untouched.
- migrate_prefs_files() copies legacy prefs file when new one absent.
- migrate_palette_file() loads legacy palette into prefs.custom_colors.
- migrate_to_stemless_names() is reachable as anchors.migrate_to_stemless_names()
  (the public-API path) and as migrations.migrate_to_stemless_names() (internal).
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Stub knob/factory helpers — modelled on tests/stubs.py StubKnob / StubNode.
#
# We use richer ad-hoc stubs here because migrate_script() needs to
# re-create knobs of three different kinds (Tab, String, PyScript) and the
# resulting knob must remember the constructor args (label, python body) so
# the tests can assert byte-for-byte preservation.
# ---------------------------------------------------------------------------


class FakeKnob:
    def __init__(self, knob_name, value=''):
        self._knob_name = knob_name
        self._value = value
        self.label = None
        self.body = None
        self.kind = None

    def name(self):
        return self._knob_name

    def setFlag(self, flag):
        pass

    def setVisible(self, visible):
        pass

    def setValue(self, value):
        self._value = value

    def getValue(self):
        return self._value

    def getText(self):
        return str(self._value)


def make_tab_knob(name, *args, **kwargs):
    knob = FakeKnob(name)
    knob.kind = 'tab'
    return knob


def make_string_knob(name, *args, **kwargs):
    knob = FakeKnob(name)
    knob.kind = 'string'
    return knob


def make_pyscript_knob(name, label, body, *args, **kwargs):
    knob = FakeKnob(name)
    knob.kind = 'pyscript'
    knob.label = label
    knob.body = body
    return knob


class FakeNode:
    def __init__(self, name='Node', knobs_dict=None):
        self._name = name
        self._knobs = dict(knobs_dict) if knobs_dict else {}
        self.removed_knob_names = []

    def name(self):
        return self._name

    def knobs(self):
        return self._knobs

    def addKnob(self, knob):
        self._knobs[knob.name()] = knob

    def removeKnob(self, knob):
        self.removed_knob_names.append(knob.name())
        self._knobs.pop(knob.name(), None)

    def __getitem__(self, knob_name):
        return self._knobs[knob_name]


def _patched_nuke_for_migrations(nodes_to_iterate, to_node_side_effect=None):
    """Return a context manager that patches migrations.nuke with stub factories.

    The patch is active for the duration of the `with` block.  Pass nodes
    that ``nuke.allNodes(recurseGroups=True)`` should return.
    """
    fake_nuke = MagicMock()
    fake_nuke.allNodes = MagicMock(return_value=list(nodes_to_iterate))
    fake_nuke.toNode = MagicMock(
        side_effect=(to_node_side_effect or (lambda name: None))
    )
    fake_nuke.Tab_Knob = MagicMock(side_effect=make_tab_knob)
    fake_nuke.String_Knob = MagicMock(side_effect=make_string_knob)
    fake_nuke.PyScript_Knob = MagicMock(side_effect=make_pyscript_knob)
    fake_nuke.INVISIBLE = 0
    return patch('migrations.nuke', fake_nuke)


# ---------------------------------------------------------------------------
# Knob-rename tests
# ---------------------------------------------------------------------------


class TestMigrateScriptKnobRenames(unittest.TestCase):
    """Each entry in LEGACY_TO_NEW_KNOB_NAMES must be renamed end-to-end."""

    def test_each_legacy_knob_is_renamed(self):
        import migrations
        from migrations import LEGACY_TO_NEW_KNOB_NAMES

        for old_name, spec in LEGACY_TO_NEW_KNOB_NAMES.items():
            new_name = spec['new_name']
            with self.subTest(old_name=old_name):
                old_knob = FakeKnob(old_name, value='stored_value')
                node = FakeNode(name='SomeNode', knobs_dict={old_name: old_knob})

                with _patched_nuke_for_migrations([node]):
                    migrations.migrate_script()

                self.assertNotIn(
                    old_name, node.knobs(),
                    f"old knob {old_name!r} must be removed after migration",
                )
                self.assertIn(
                    new_name, node.knobs(),
                    f"new knob {new_name!r} must be present after migration",
                )

    def test_string_knob_value_is_preserved(self):
        import migrations
        from constants import KNOB_NAME

        old_knob = FakeKnob('copy_hidden_input_node', value='Group1.Anchor_Foo')
        node = FakeNode(knobs_dict={'copy_hidden_input_node': old_knob})

        with _patched_nuke_for_migrations([node]):
            migrations.migrate_script()

        self.assertEqual(node[KNOB_NAME].getValue(), 'Group1.Anchor_Foo')

    def test_dot_anchor_string_knob_value_is_preserved(self):
        import migrations
        from constants import DOT_ANCHOR_KNOB_NAME

        old_knob = FakeKnob('paste_hidden_dot_anchor', value='Anchor_Bar')
        node = FakeNode(knobs_dict={'paste_hidden_dot_anchor': old_knob})

        with _patched_nuke_for_migrations([node]):
            migrations.migrate_script()

        self.assertEqual(node[DOT_ANCHOR_KNOB_NAME].getValue(), 'Anchor_Bar')


class TestMigrateScriptPyScriptBodyPreservation(unittest.TestCase):
    """PyScript_Knob renames must produce knobs with the canonical button body."""

    EXPECTED_PYSCRIPT_BODIES = {
        'reconnect_link': (
            'Reconnect',
            'import link\nlink.reconnect_link_node(nuke.thisNode())',
        ),
        'reconnect_child_links': (
            'Reconnect Child Links',
            'import anchor\nanchor.reconnect_anchor_node(nuke.thisNode())',
        ),
        'rename_anchor': (
            'Rename',
            'import anchor\nanchor.rename_anchor(nuke.thisNode())',
        ),
        'set_anchor_color': (
            'Set Color',
            'import anchor\nanchor.set_anchor_color(nuke.thisNode())',
        ),
    }

    def test_each_pyscript_knob_body_is_preserved(self):
        import migrations
        from migrations import LEGACY_TO_NEW_KNOB_NAMES

        for old_name, (expected_label, expected_body) in self.EXPECTED_PYSCRIPT_BODIES.items():
            with self.subTest(old_name=old_name):
                spec = LEGACY_TO_NEW_KNOB_NAMES[old_name]
                self.assertEqual(spec['kind'], 'pyscript')
                new_name = spec['new_name']

                old_knob = FakeKnob(old_name, value='stale')
                node = FakeNode(knobs_dict={old_name: old_knob})

                with _patched_nuke_for_migrations([node]):
                    migrations.migrate_script()

                new_knob = node[new_name]
                self.assertEqual(new_knob.kind, 'pyscript')
                self.assertEqual(new_knob.label, expected_label)
                self.assertEqual(new_knob.body, expected_body)


class TestMigrateScriptIdempotency(unittest.TestCase):
    """Repeated calls must be no-ops once migration has happened."""

    def test_second_call_does_not_re_migrate(self):
        import migrations
        from constants import TAB_NAME, KNOB_NAME

        node = FakeNode(knobs_dict={
            'copy_hidden_tab': FakeKnob('copy_hidden_tab'),
            'copy_hidden_input_node': FakeKnob('copy_hidden_input_node', value='Anchor_Baz'),
        })

        with _patched_nuke_for_migrations([node]):
            migrations.migrate_script()
            knobs_after_first = dict(node.knobs())
            removed_after_first = list(node.removed_knob_names)

            migrations.migrate_script()
            knobs_after_second = dict(node.knobs())
            removed_after_second = list(node.removed_knob_names)

        self.assertIn(TAB_NAME, knobs_after_first)
        self.assertIn(KNOB_NAME, knobs_after_first)
        self.assertEqual(
            knobs_after_first.keys(), knobs_after_second.keys(),
            "second migrate_script() must not change the knob set",
        )
        self.assertEqual(
            removed_after_first, removed_after_second,
            "second migrate_script() must not remove additional knobs",
        )


class TestMigrateScriptAlreadyMigratedNoOp(unittest.TestCase):
    """A node carrying ONLY new knob names must be left untouched."""

    def test_node_with_only_new_knobs_is_untouched(self):
        import migrations
        from constants import (
            ANCHOR_RECONNECT_KNOB_NAME,
            DOT_TYPE_KNOB_NAME,
            KNOB_NAME,
            TAB_NAME,
        )

        node = FakeNode(knobs_dict={
            TAB_NAME: FakeKnob(TAB_NAME),
            KNOB_NAME: FakeKnob(KNOB_NAME, value='Anchor_Foo'),
            DOT_TYPE_KNOB_NAME: FakeKnob(DOT_TYPE_KNOB_NAME, value='link'),
            ANCHOR_RECONNECT_KNOB_NAME: FakeKnob(ANCHOR_RECONNECT_KNOB_NAME),
        })
        original_knob_names = set(node.knobs().keys())

        with _patched_nuke_for_migrations([node]):
            migrations.migrate_script()

        self.assertEqual(
            set(node.knobs().keys()), original_knob_names,
            "node carrying only new-namespace knobs must not be modified",
        )
        self.assertEqual(node.removed_knob_names, [],
                         "no knobs should be removed from an already-migrated node")


class TestMigrateScriptMixedState(unittest.TestCase):
    """When a node has BOTH the old and the new knob, leave both untouched."""

    def test_mixed_state_leaves_both_knobs(self):
        import migrations
        from constants import KNOB_NAME

        old_knob = FakeKnob('copy_hidden_input_node', value='OLD_VALUE')
        new_knob = FakeKnob(KNOB_NAME, value='NEW_VALUE')
        node = FakeNode(knobs_dict={
            'copy_hidden_input_node': old_knob,
            KNOB_NAME: new_knob,
        })

        with _patched_nuke_for_migrations([node]):
            migrations.migrate_script()

        # Both knobs must still be present.
        self.assertIn('copy_hidden_input_node', node.knobs())
        self.assertIn(KNOB_NAME, node.knobs())
        # Neither value was touched.
        self.assertEqual(node['copy_hidden_input_node'].getValue(), 'OLD_VALUE')
        self.assertEqual(node[KNOB_NAME].getValue(), 'NEW_VALUE')


# ---------------------------------------------------------------------------
# Prefs migration tests
# ---------------------------------------------------------------------------


class TestMigratePrefsFiles(unittest.TestCase):
    """migrate_prefs_files() copies legacy prefs file when new one absent."""

    def setUp(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def tearDown(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def test_copies_old_prefs_when_present(self):
        import constants
        import migrations
        original_old_path = constants.OLD_PREFS_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                old_path = os.path.join(temp_dir, 'paste_hidden_prefs.json')
                new_path = os.path.join(temp_dir, 'anchors_prefs.json')
                payload = {'plugin_enabled': False, 'custom_colors': [123]}
                with open(old_path, 'w') as file_handle:
                    json.dump(payload, file_handle)

                constants.OLD_PREFS_PATH = old_path
                constants.PREFS_PATH = new_path

                migrations.migrate_prefs_files()

                self.assertTrue(os.path.exists(new_path),
                                "new prefs file must be created from the legacy file")
                with open(new_path) as file_handle:
                    self.assertEqual(json.load(file_handle), payload)
        finally:
            constants.OLD_PREFS_PATH = original_old_path
            constants.PREFS_PATH = original_new_path

    def test_silent_noop_when_old_prefs_absent(self):
        import constants
        import migrations
        original_old_path = constants.OLD_PREFS_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                old_path = os.path.join(temp_dir, 'does_not_exist.json')
                new_path = os.path.join(temp_dir, 'also_should_not_exist.json')
                constants.OLD_PREFS_PATH = old_path
                constants.PREFS_PATH = new_path

                # Must not raise, must not create the new file.
                migrations.migrate_prefs_files()

                self.assertFalse(os.path.exists(new_path))
        finally:
            constants.OLD_PREFS_PATH = original_old_path
            constants.PREFS_PATH = original_new_path

    def test_does_not_overwrite_when_new_prefs_already_exists(self):
        """Guard against clobbering an existing anchors_prefs.json."""
        import constants
        import migrations
        original_old_path = constants.OLD_PREFS_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                old_path = os.path.join(temp_dir, 'paste_hidden_prefs.json')
                new_path = os.path.join(temp_dir, 'anchors_prefs.json')
                with open(old_path, 'w') as file_handle:
                    json.dump({'plugin_enabled': False}, file_handle)
                existing_payload = {'plugin_enabled': True, 'custom_colors': [42]}
                with open(new_path, 'w') as file_handle:
                    json.dump(existing_payload, file_handle)

                constants.OLD_PREFS_PATH = old_path
                constants.PREFS_PATH = new_path
                migrations.migrate_prefs_files()

                with open(new_path) as file_handle:
                    self.assertEqual(json.load(file_handle), existing_payload,
                                     "must not overwrite an existing anchors_prefs.json")
        finally:
            constants.OLD_PREFS_PATH = original_old_path
            constants.PREFS_PATH = original_new_path


class TestMigratePaletteFile(unittest.TestCase):
    """migrate_palette_file() loads legacy palette JSON into prefs.custom_colors."""

    def setUp(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def tearDown(self):
        if 'prefs' in sys.modules:
            del sys.modules['prefs']

    def test_loads_palette_into_custom_colors(self):
        import constants
        import migrations
        import prefs as prefs_module
        original_palette_path = constants.USER_PALETTE_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                palette_path = os.path.join(temp_dir, 'paste_hidden_user_palette.json')
                legacy_colors = [0x6f3399ff, 0xff0000ff]
                with open(palette_path, 'w') as file_handle:
                    json.dump(legacy_colors, file_handle)

                constants.USER_PALETTE_PATH = palette_path
                constants.PREFS_PATH = os.path.join(temp_dir, 'anchors_prefs.json')
                migrations.migrate_palette_file()

                self.assertEqual(prefs_module.custom_colors, legacy_colors)
        finally:
            constants.USER_PALETTE_PATH = original_palette_path
            constants.PREFS_PATH = original_new_path

    def test_silent_noop_on_missing_palette_file(self):
        import constants
        import migrations
        import prefs as prefs_module
        original_palette_path = constants.USER_PALETTE_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                palette_path = os.path.join(temp_dir, 'does_not_exist.json')
                constants.USER_PALETTE_PATH = palette_path
                constants.PREFS_PATH = os.path.join(temp_dir, 'anchors_prefs.json')
                migrations.migrate_palette_file()
                self.assertEqual(prefs_module.custom_colors, [])
        finally:
            constants.USER_PALETTE_PATH = original_palette_path
            constants.PREFS_PATH = original_new_path

    def test_silent_noop_on_corrupt_palette_file(self):
        import constants
        import migrations
        import prefs as prefs_module
        original_palette_path = constants.USER_PALETTE_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                palette_path = os.path.join(temp_dir, 'corrupt.json')
                with open(palette_path, 'w') as file_handle:
                    file_handle.write('{ this is not json !!!')
                constants.USER_PALETTE_PATH = palette_path
                constants.PREFS_PATH = os.path.join(temp_dir, 'anchors_prefs.json')
                migrations.migrate_palette_file()
                self.assertEqual(prefs_module.custom_colors, [])
        finally:
            constants.USER_PALETTE_PATH = original_palette_path
            constants.PREFS_PATH = original_new_path

    def test_silent_noop_when_new_prefs_file_already_exists(self):
        """Guard against clobbering custom_colors when anchors_prefs.json exists."""
        import constants
        import migrations
        import prefs as prefs_module
        original_palette_path = constants.USER_PALETTE_PATH
        original_new_path = constants.PREFS_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                palette_path = os.path.join(temp_dir, 'paste_hidden_user_palette.json')
                with open(palette_path, 'w') as file_handle:
                    json.dump([0x123456ff], file_handle)
                new_path = os.path.join(temp_dir, 'anchors_prefs.json')
                with open(new_path, 'w') as file_handle:
                    file_handle.write('{}')

                constants.USER_PALETTE_PATH = palette_path
                constants.PREFS_PATH = new_path
                prefs_module.custom_colors = [0xabcdef00]
                migrations.migrate_palette_file()

                self.assertEqual(prefs_module.custom_colors, [0xabcdef00],
                                 "must not overwrite custom_colors when new prefs file exists")
        finally:
            constants.USER_PALETTE_PATH = original_palette_path
            constants.PREFS_PATH = original_new_path


# ---------------------------------------------------------------------------
# Stemless reachability — ensure the public API still works.
# ---------------------------------------------------------------------------


class TestStemlessReachability(unittest.TestCase):
    """migrate_to_stemless_names is reachable both as anchors.* and migrations.*."""

    def test_anchors_module_re_exports_migrators(self):
        import anchors
        import migrations
        self.assertTrue(callable(anchors.migrate_script))
        self.assertTrue(callable(anchors.migrate_to_stemless_names))
        self.assertIs(anchors.migrate_script, migrations.migrate_script)
        self.assertIs(anchors.migrate_to_stemless_names,
                      migrations.migrate_to_stemless_names)


if __name__ == '__main__':
    unittest.main()
