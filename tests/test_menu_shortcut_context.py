"""Tests for menu.py — anchor shortcuts gated to the DAG context (issue #54).

Anchor functions are only meaningful in the Node Graph. Every menu command that
binds a keyboard shortcut must register it with shortcutContext=2 (DAG context)
so the key never fires while the Script Editor, Viewer, or another panel has
focus. These tests import menu.py against a recording nuke stub and assert that
every shortcut-bearing command carries the DAG context, while commands without a
shortcut do not get a spurious context.
"""

import importlib
import sys
import unittest
from unittest.mock import MagicMock

from constants import DAG_SHORTCUT_CONTEXT


class _RecordingMenu:
    """A nuke menu stand-in that records every addCommand call.

    All recorded commands across every menu/submenu created during a menu.py
    import are appended to the shared ``commands`` list so a single import can be
    inspected as a whole.
    """

    def __init__(self, commands):
        self._commands = commands

    def addCommand(self, name, command=None, shortcut=None, **kwargs):
        self._commands.append({
            'name': name,
            'command': command,
            'shortcut': shortcut,
            'shortcutContext': kwargs.get('shortcutContext'),
        })
        # Return an item exposing setEnabled so set_anchors_menu_enabled works.
        item = MagicMock()
        item.setEnabled = MagicMock()
        return item

    def addMenu(self, name, **kwargs):
        return _RecordingMenu(self._commands)

    def findItem(self, name):
        return _RecordingMenu(self._commands)

    def addSeparator(self):
        pass

    def items(self):
        return []


def _import_menu_with_recording_nuke():
    """Import a fresh menu.py against a recording nuke stub; return its commands."""
    recorded_commands = []

    # conftest already installed a nuke stub; augment it with menu recording.
    nuke_stub = sys.modules['nuke']
    nuke_stub.menu = MagicMock(return_value=_RecordingMenu(recorded_commands))
    nuke_stub.addOnScriptLoad = MagicMock()

    sys.modules.pop('menu', None)
    importlib.import_module('menu')
    return recorded_commands


class TestMenuShortcutContext(unittest.TestCase):
    def setUp(self):
        self.commands = _import_menu_with_recording_nuke()
        self.by_shortcut = {
            command['shortcut']: command
            for command in self.commands
            if command['shortcut'] is not None
        }

    def test_every_shortcut_is_dag_gated(self):
        """Every command that binds a shortcut fires only in the DAG context."""
        shortcut_commands = [c for c in self.commands if c['shortcut'] is not None]
        self.assertTrue(shortcut_commands, "expected menu.py to register shortcuts")
        for command in shortcut_commands:
            self.assertEqual(
                command['shortcutContext'],
                DAG_SHORTCUT_CONTEXT,
                f"{command['name']} (shortcut {command['shortcut']!r}) is not gated "
                f"to the DAG context",
            )

    def test_known_shortcuts_are_gated(self):
        """Spot-check the headline anchor shortcuts are present and DAG-gated."""
        for shortcut in ('^C', '^X', '^V', 'A', '+A', 'alt+A', 'alt+J',
                         'alt+L', 'alt+Z', '+M', '+N', '+B', '^M', '+^D'):
            self.assertIn(shortcut, self.by_shortcut,
                          f"shortcut {shortcut!r} was not registered")
            self.assertEqual(
                self.by_shortcut[shortcut]['shortcutContext'],
                DAG_SHORTCUT_CONTEXT,
                f"shortcut {shortcut!r} is not DAG-gated",
            )

    def test_commands_without_shortcuts_have_no_context(self):
        """Commands without a shortcut should not carry a spurious context."""
        for command in self.commands:
            if command['shortcut'] is None:
                self.assertIsNone(
                    command['shortcutContext'],
                    f"{command['name']} has shortcutContext without a shortcut",
                )


if __name__ == '__main__':
    unittest.main()
