"""Tests for the public api.py surface — TDD RED phase.

These tests define the contract for api.py before that module exists.
Running this file will fail with ModuleNotFoundError ('api') until Plan 02
creates api.py.

Test classes:
    TestCreateAnchor              — create_anchor() parameter pass-through to anchor internals
    TestCreateAnchorErrorHandling — ValueError on bad names; RuntimeError when nuke is absent
    TestFindAnchorByName          — find_anchor_by_name() delegation and nuke-absent guard
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Install nuke stub before importing anything that touches nuke at module level.
# Use the same guard pattern as test_anchor_naming.py so the stub is only
# installed once when multiple test files are collected in the same process.
# ---------------------------------------------------------------------------

from tests.stubs import make_stub_nuke_module, make_stub_nukescripts_module

if 'nuke' not in sys.modules:
    sys.modules['nuke'] = make_stub_nuke_module()
if 'nukescripts' not in sys.modules:
    sys.modules['nukescripts'] = make_stub_nukescripts_module()

# ---------------------------------------------------------------------------
# api module import — will fail with ModuleNotFoundError until Plan 02 creates
# api.py. That failure is intentional and confirms the RED phase is correct.
# ---------------------------------------------------------------------------

import api  # noqa: E402  (module does not exist yet — RED phase)


class TestCreateAnchor(unittest.TestCase):
    """create_anchor() must delegate all parameters to anchor.create_anchor_named()."""

    def setUp(self):
        self._mock_anchor_node = MagicMock(name='anchor_node')
        self._create_patcher = patch(
            'anchor.create_anchor_named',
            return_value=self._mock_anchor_node,
        )
        self._mock_create_anchor_named = self._create_patcher.start()

    def tearDown(self):
        self._create_patcher.stop()

    def test_create_anchor_with_name_only(self):
        """create_anchor('MyAnchor') delegates to anchor.create_anchor_named with no extras."""
        result = api.create_anchor('MyAnchor')
        self._mock_create_anchor_named.assert_called_once_with('MyAnchor', None, None)
        self.assertIs(result, self._mock_anchor_node)

    def test_create_anchor_passes_input_node_through(self):
        """create_anchor with input_node passes that node to anchor.create_anchor_named."""
        source_node = MagicMock(name='source_node')
        result = api.create_anchor('MyAnchor', input_node=source_node)
        self._mock_create_anchor_named.assert_called_once_with('MyAnchor', source_node, None)
        self.assertIs(result, self._mock_anchor_node)

    def test_create_anchor_passes_color_through(self):
        """create_anchor with color passes that color to anchor.create_anchor_named."""
        result = api.create_anchor('MyAnchor', color=0xFF0000FF)
        self._mock_create_anchor_named.assert_called_once_with('MyAnchor', None, 0xFF0000FF)
        self.assertIs(result, self._mock_anchor_node)

    def test_create_anchor_passes_input_node_and_color_through(self):
        """create_anchor with both input_node and color passes both to anchor.create_anchor_named."""
        source_node = MagicMock(name='source_node')
        result = api.create_anchor('MyAnchor', input_node=source_node, color=0xFF0000FF)
        self._mock_create_anchor_named.assert_called_once_with('MyAnchor', source_node, 0xFF0000FF)
        self.assertIs(result, self._mock_anchor_node)


class TestCreateAnchorErrorHandling(unittest.TestCase):
    """create_anchor() must raise ValueError for bad names and RuntimeError without nuke."""

    def setUp(self):
        # For ValueError tests we let the real anchor.create_anchor_named raise;
        # for the nuke-absent test we need nuke absent from sys.modules.
        self._original_nuke_module = sys.modules.get('nuke')

    def tearDown(self):
        # Restore nuke in sys.modules if it was removed during a test.
        if self._original_nuke_module is not None:
            sys.modules['nuke'] = self._original_nuke_module
        elif 'nuke' in sys.modules:
            del sys.modules['nuke']

    def test_create_anchor_raises_value_error_for_punctuation_only_name(self):
        """create_anchor('!!!') raises ValueError because the name sanitizes to empty."""
        with patch('anchor.create_anchor_named', side_effect=ValueError('empty name')):
            with self.assertRaises(ValueError):
                api.create_anchor('!!!')

    def test_create_anchor_raises_value_error_for_whitespace_only_name(self):
        """create_anchor('   ') raises ValueError because whitespace strips to empty."""
        with patch('anchor.create_anchor_named', side_effect=ValueError('empty name')):
            with self.assertRaises(ValueError):
                api.create_anchor('   ')

    def test_create_anchor_raises_runtime_error_when_nuke_absent(self):
        """create_anchor raises RuntimeError('anchors API requires a running Nuke session') if nuke is not available."""
        del sys.modules['nuke']
        with self.assertRaises(RuntimeError) as raised:
            api.create_anchor('MyAnchor')
        self.assertEqual(str(raised.exception), 'anchors API requires a running Nuke session')


class TestFindAnchorByName(unittest.TestCase):
    """find_anchor_by_name() must delegate to anchor.find_anchor_by_name() and guard nuke absence."""

    def setUp(self):
        self._original_nuke_module = sys.modules.get('nuke')

    def tearDown(self):
        # Restore nuke in sys.modules if it was removed during a test.
        if self._original_nuke_module is not None:
            sys.modules['nuke'] = self._original_nuke_module
        elif 'nuke' in sys.modules:
            del sys.modules['nuke']

    def test_find_anchor_by_name_returns_matching_anchor(self):
        """find_anchor_by_name delegates to anchor.find_anchor_by_name and returns result."""
        mock_anchor_node = MagicMock(name='found_anchor')
        with patch('anchor.find_anchor_by_name', return_value=mock_anchor_node) as mock_find:
            result = api.find_anchor_by_name('MyAnchor')
            mock_find.assert_called_once_with('MyAnchor')
            self.assertIs(result, mock_anchor_node)

    def test_find_anchor_by_name_returns_none_when_not_found(self):
        """find_anchor_by_name returns None when no anchor has the given display name."""
        with patch('anchor.find_anchor_by_name', return_value=None) as mock_find:
            result = api.find_anchor_by_name('NonExistent')
            mock_find.assert_called_once_with('NonExistent')
            self.assertIsNone(result)

    def test_find_anchor_by_name_raises_runtime_error_when_nuke_absent(self):
        """find_anchor_by_name raises RuntimeError('anchors API requires a running Nuke session') if nuke is not available."""
        del sys.modules['nuke']
        with self.assertRaises(RuntimeError) as raised:
            api.find_anchor_by_name('MyAnchor')
        self.assertEqual(str(raised.exception), 'anchors API requires a running Nuke session')


if __name__ == '__main__':
    unittest.main()
