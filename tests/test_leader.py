"""Tests for leader.py — dispatch routing.

The Qt event filter itself is not under test here (it requires a real
QApplication and a stubbed PySide6 cannot exercise QEvent properly).
Instead, we exercise leader.dispatch_key, which mirrors the eventFilter
routing logic and is what the overlay's click cells call — so covering
dispatch_key covers the routing decisions for both keyboard and mouse paths.

What we verify:
  - Single-shot keys (Q/W/E/R/F/J/Z/X/comma) disarm leader mode first, then
    invoke their entry in _DISPATCH_TABLE.
  - The chaining key L hides the overlay through _hide_overlay_for_chaining
    (so hideEvent does not re-disarm) and stays armed.
  - Pressing a disabled binding (per _is_binding_enabled) silently disarms
    without invoking the dispatcher.
  - The selection-aware enable gates for J / L / Z behave as documented.
  - Unknown letters are silently ignored.
  - The keyboard-layout remap rewrites the Qt.Key codes in the dispatch
    tables so the user's physical-key muscle memory is preserved.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from tests.stubs import make_stub_nuke_module

if 'nuke' not in sys.modules:
    sys.modules['nuke'] = make_stub_nuke_module()

leader = None


def setUpModule():
    """Import leader against a stable in-memory prefs stub for this test file."""
    prefs_stub = types.ModuleType('prefs')
    prefs_stub.keyboard_layout = 'qwerty'
    prefs_stub.plugin_enabled = True
    sys.modules['prefs'] = prefs_stub
    global leader
    import leader as leader_module
    leader = leader_module


def tearDownModule():
    sys.modules.pop('prefs', None)
    sys.modules.pop('leader', None)


class TestLeaderDispatchKey(unittest.TestCase):
    """dispatch_key routes single-shot vs chaining vs dynamic-R correctly."""

    def setUp(self):
        # leader uses module-level state for arm/disarm; reset between tests.
        leader._leader_active = True
        leader._overlay = MagicMock()
        # Routing tests assume the binding is enabled — the enable gate has its
        # own dedicated TestIsBindingEnabled class below.
        self._enable_patcher = patch('leader._is_binding_enabled', return_value=True)
        self._enable_patcher.start()

    def tearDown(self):
        self._enable_patcher.stop()
        leader._leader_active = False
        leader._overlay = None

    # ----- table structure -----

    def test_q_table_entry_is_set_input_to_b(self):
        from PySide6.QtCore import Qt
        self.assertIs(leader._DISPATCH_TABLE[Qt.Key.Key_Q], leader._dispatch_set_input_to_b)

    def test_w_table_entry_is_set_input_to_a(self):
        from PySide6.QtCore import Qt
        self.assertIs(leader._DISPATCH_TABLE[Qt.Key.Key_W], leader._dispatch_set_input_to_a)

    def test_e_table_entry_is_set_input_to_mask(self):
        from PySide6.QtCore import Qt
        self.assertIs(leader._DISPATCH_TABLE[Qt.Key.Key_E], leader._dispatch_set_input_to_mask)

    def test_l_is_chaining_not_single_shot(self):
        from PySide6.QtCore import Qt
        self.assertIn(Qt.Key.Key_L, leader._CHAINING_DISPATCH_TABLE)
        self.assertNotIn(Qt.Key.Key_L, leader._DISPATCH_TABLE)

    def test_r_default_is_single_shot(self):
        from PySide6.QtCore import Qt
        # R defaults to single-shot; chaining is decided at dispatch time.
        self.assertIn(Qt.Key.Key_R, leader._DISPATCH_TABLE)

    # ----- chaining vs single-shot routing -----

    def test_q_disarms_and_runs_table_entry(self):
        from PySide6.QtCore import Qt
        sentinel = MagicMock(name='dispatch_q')
        with patch.dict(leader._DISPATCH_TABLE, {Qt.Key.Key_Q: sentinel}), \
             patch('leader._disarm') as mock_disarm:
            leader.dispatch_key('Q')
            mock_disarm.assert_called_once()
            sentinel.assert_called_once()

    def test_l_keypress_chains_without_disarm(self):
        from PySide6.QtCore import Qt
        sentinel = MagicMock(name='dispatch_l')
        with patch.dict(leader._CHAINING_DISPATCH_TABLE, {Qt.Key.Key_L: sentinel}), \
             patch('leader._disarm') as mock_disarm:
            leader.dispatch_key('L')
            mock_disarm.assert_not_called()
            sentinel.assert_called_once()
            leader._overlay.hide.assert_called_once()

    def test_comma_keypress_opens_prefs_after_disarm(self):
        from PySide6.QtCore import Qt
        sentinel = MagicMock(name='dispatch_comma')
        with patch.dict(leader._DISPATCH_TABLE, {Qt.Key.Key_Comma: sentinel}), \
             patch('leader._disarm') as mock_disarm:
            leader.dispatch_key(',')
            mock_disarm.assert_called_once()
            sentinel.assert_called_once()

    def test_chaining_hides_overlay_with_suppression_flag_set(self):
        """The overlay hide during chaining must be marked so hideEvent skips _disarm."""
        from PySide6.QtCore import Qt
        captured_flag = []

        def _record_flag():
            captured_flag.append(leader._suppress_disarm_on_hide)

        leader._overlay.hide.side_effect = _record_flag
        sentinel = MagicMock(name='dispatch_l')
        with patch.dict(leader._CHAINING_DISPATCH_TABLE, {Qt.Key.Key_L: sentinel}):
            leader.dispatch_key('L')
        self.assertEqual(captured_flag, [True],
                         "overlay.hide() must be called with _suppress_disarm_on_hide=True")
        # Flag must be reset after the hide returns so subsequent click-outside
        # hides still route through _disarm.
        self.assertFalse(leader._suppress_disarm_on_hide)

    # ----- R is now a plain single-shot picker -----

    def test_r_opens_picker_via_dispatch_table(self):
        from PySide6.QtCore import Qt
        sentinel = MagicMock(name='dispatch_r')
        with patch.dict(leader._DISPATCH_TABLE, {Qt.Key.Key_R: sentinel}), \
             patch('leader._disarm') as mock_disarm:
            leader.dispatch_key('R')
            mock_disarm.assert_called_once()
            sentinel.assert_called_once()

    # ----- enable gate -----

    def test_disabled_binding_disarms_silently(self):
        """Pressing W when can_set_input_a is False must not fire the picker."""
        from PySide6.QtCore import Qt
        sentinel = MagicMock(name='dispatch_w')
        with patch('leader._is_binding_enabled', return_value=False), \
             patch.dict(leader._DISPATCH_TABLE, {Qt.Key.Key_W: sentinel}), \
             patch('leader._disarm') as mock_disarm:
            leader.dispatch_key('W')
            mock_disarm.assert_called_once()
            sentinel.assert_not_called()

    def test_disabled_r_does_not_open_picker(self):
        with patch('leader._is_binding_enabled', return_value=False), \
             patch('leader._disarm') as mock_disarm, \
             patch('leader._dispatch_set_input_first_available') as mock_picker:
            leader.dispatch_key('R')
            mock_disarm.assert_called_once()
            mock_picker.assert_not_called()

    # ----- bad input -----

    def test_unknown_letter_is_ignored(self):
        with patch('leader._disarm') as mock_disarm:
            leader.dispatch_key('K')
            mock_disarm.assert_not_called()


class TestLayoutRemap(unittest.TestCase):
    """_build_dispatch_tables honours the keyboard-layout remap."""

    def test_qwerty_identity_when_no_remap(self):
        original_remap = leader.LAYOUT_REMAP
        leader.LAYOUT_REMAP = {}
        try:
            single, chaining, qt_to_letter = leader._build_dispatch_tables()
        finally:
            leader.LAYOUT_REMAP = original_remap
        from PySide6.QtCore import Qt
        self.assertIn(Qt.Key.Key_Q, single)
        self.assertIn(Qt.Key.Key_L, chaining)
        self.assertEqual(qt_to_letter[Qt.Key.Key_Q], 'Q')
        self.assertEqual(qt_to_letter[Qt.Key.Key_L], 'L')

    def test_azerty_remaps_q_to_physical_a(self):
        original_remap = leader.LAYOUT_REMAP
        leader.LAYOUT_REMAP = {"Q": "A", "W": "Z", "A": "Q", "Z": "W"}
        try:
            single, _chaining, qt_to_letter = leader._build_dispatch_tables()
        finally:
            leader.LAYOUT_REMAP = original_remap
        from PySide6.QtCore import Qt
        # On AZERTY, the physical key at QWERTY's Q position types 'A',
        # so the dispatcher for 'Q' must be reachable via Qt.Key.Key_A.
        self.assertIs(single[Qt.Key.Key_A], leader._dispatch_set_input_to_b)
        # The reverse lookup maps physical Key_A back to canonical 'Q'.
        self.assertEqual(qt_to_letter[Qt.Key.Key_A], 'Q')
        # Qwerty 'Q' (physically at A position on AZERTY) must NOT still
        # carry the Q binding.
        self.assertNotIn(Qt.Key.Key_Q, single)

    def test_physical_letter_for_passthrough(self):
        original_remap = leader.LAYOUT_REMAP
        leader.LAYOUT_REMAP = {}
        try:
            self.assertEqual(leader.physical_letter_for('F'), 'F')
            self.assertEqual(leader.physical_letter_for(','), ',')
        finally:
            leader.LAYOUT_REMAP = original_remap

    def test_physical_letter_for_azerty(self):
        original_remap = leader.LAYOUT_REMAP
        leader.LAYOUT_REMAP = {"Q": "A", "W": "Z"}
        try:
            self.assertEqual(leader.physical_letter_for('Q'), 'A')
            self.assertEqual(leader.physical_letter_for('W'), 'Z')
            self.assertEqual(leader.physical_letter_for('F'), 'F')
        finally:
            leader.LAYOUT_REMAP = original_remap


class TestRemapFromPrefs(unittest.TestCase):
    """_remap_from_prefs reads the layout pref and returns the right table."""

    def test_qwerty_returns_empty_dict(self):
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='qwerty')}):
            self.assertEqual(leader._remap_from_prefs(), {})

    def test_azerty_returns_azerty_table(self):
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='azerty')}):
            self.assertEqual(leader._remap_from_prefs(), leader._AZERTY_REMAP)

    def test_qwertz_returns_qwertz_table(self):
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='qwertz')}):
            self.assertEqual(leader._remap_from_prefs(), leader._QWERTZ_REMAP)

    def test_unknown_value_returns_empty_dict(self):
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='dvorak')}):
            self.assertEqual(leader._remap_from_prefs(), {})

    def test_prefs_import_failure_returns_empty_dict(self):
        # Force the import inside _remap_from_prefs to fail by injecting a sentinel
        # that raises on attribute access.
        class RaisingModule:
            def __getattr__(self, _name):
                raise RuntimeError("simulated prefs failure")
        with patch.dict(sys.modules, {'prefs': RaisingModule()}):
            self.assertEqual(leader._remap_from_prefs(), {})


class TestRebuildLayout(unittest.TestCase):
    """rebuild_layout re-derives LAYOUT_REMAP and dispatch tables from prefs."""

    def setUp(self):
        self._original_remap = leader.LAYOUT_REMAP
        self._original_dispatch = leader._DISPATCH_TABLE
        self._original_chaining = leader._CHAINING_DISPATCH_TABLE
        self._original_qt_to_letter = leader._QT_KEY_TO_LETTER

    def tearDown(self):
        leader.LAYOUT_REMAP = self._original_remap
        leader._DISPATCH_TABLE = self._original_dispatch
        leader._CHAINING_DISPATCH_TABLE = self._original_chaining
        leader._QT_KEY_TO_LETTER = self._original_qt_to_letter

    def test_rebuild_applies_azerty(self):
        from PySide6.QtCore import Qt
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='azerty')}):
            leader.rebuild_layout()
        # On AZERTY, Q's binding moves to the physical A key.
        self.assertIs(leader._DISPATCH_TABLE[Qt.Key.Key_A], leader._dispatch_set_input_to_b)
        self.assertEqual(leader._QT_KEY_TO_LETTER[Qt.Key.Key_A], 'Q')
        self.assertEqual(leader.LAYOUT_REMAP, leader._AZERTY_REMAP)

    def test_rebuild_back_to_qwerty(self):
        from PySide6.QtCore import Qt
        # First switch to azerty, then back to qwerty.
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='azerty')}):
            leader.rebuild_layout()
        with patch.dict(sys.modules, {'prefs': MagicMock(keyboard_layout='qwerty')}):
            leader.rebuild_layout()
        self.assertIs(leader._DISPATCH_TABLE[Qt.Key.Key_Q], leader._dispatch_set_input_to_b)
        self.assertEqual(leader.LAYOUT_REMAP, {})


class TestIsBindingEnabled(unittest.TestCase):
    """_is_binding_enabled gates dispatch and overlay grey-out."""

    def test_comma_always_enabled_even_when_plugin_disabled(self):
        with patch.dict(sys.modules, {'prefs': MagicMock(plugin_enabled=False)}):
            self.assertTrue(leader._is_binding_enabled(','))

    def test_other_bindings_disabled_when_plugin_disabled(self):
        with patch.dict(sys.modules, {'prefs': MagicMock(plugin_enabled=False)}):
            self.assertFalse(leader._is_binding_enabled('Q'))
            self.assertFalse(leader._is_binding_enabled('F'))

    def test_w_disabled_when_target_has_only_one_input(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        fake_input_sets = MagicMock()
        fake_input_sets.can_set_input_a.return_value = False
        with patch.dict(sys.modules, {
            'prefs': fake_prefs,
            'input_sets': fake_input_sets,
        }), patch('leader._selected_non_link_target', return_value=MagicMock()):
            self.assertFalse(leader._is_binding_enabled('W'))

    def test_e_disabled_when_no_mask_input(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        fake_input_sets = MagicMock()
        fake_input_sets.can_set_input_mask.return_value = False
        with patch.dict(sys.modules, {
            'prefs': fake_prefs,
            'input_sets': fake_input_sets,
        }), patch('leader._selected_non_link_target', return_value=MagicMock()):
            self.assertFalse(leader._is_binding_enabled('E'))

    def test_r_disabled_when_no_free_input(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        fake_input_sets = MagicMock()
        fake_input_sets.can_set_input_first_available.return_value = False
        with patch.dict(sys.modules, {
            'prefs': fake_prefs,
            'input_sets': fake_input_sets,
        }), patch('leader._selected_non_link_target', return_value=MagicMock()):
            self.assertFalse(leader._is_binding_enabled('R'))

    def test_r_enabled_when_free_input_available(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        fake_input_sets = MagicMock()
        fake_input_sets.can_set_input_first_available.return_value = True
        with patch.dict(sys.modules, {
            'prefs': fake_prefs,
            'input_sets': fake_input_sets,
        }), patch('leader._selected_non_link_target', return_value=MagicMock()):
            self.assertTrue(leader._is_binding_enabled('R'))

    # ----- selection-aware gates for J / L / Z -----

    def test_j_disabled_when_no_selection(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        with patch.dict(sys.modules, {'prefs': fake_prefs}), \
             patch('leader._selected_single_node', return_value=None):
            self.assertFalse(leader._is_binding_enabled('J'))

    def test_j_disabled_when_selected_is_not_link(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        node = MagicMock()
        with patch.dict(sys.modules, {'prefs': fake_prefs}), \
             patch('leader._selected_single_node', return_value=node), \
             patch('link.is_link', return_value=False):
            self.assertFalse(leader._is_binding_enabled('J'))

    def test_j_enabled_when_selected_is_link(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        node = MagicMock()
        with patch.dict(sys.modules, {'prefs': fake_prefs}), \
             patch('leader._selected_single_node', return_value=node), \
             patch('link.is_link', return_value=True):
            self.assertTrue(leader._is_binding_enabled('J'))

    def test_l_disabled_when_no_selection(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        with patch.dict(sys.modules, {'prefs': fake_prefs}), \
             patch('leader._selected_single_node', return_value=None):
            self.assertFalse(leader._is_binding_enabled('L'))

    def test_l_disabled_when_selected_is_not_anchor(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        node = MagicMock()
        with patch.dict(sys.modules, {'prefs': fake_prefs}), \
             patch('leader._selected_single_node', return_value=node), \
             patch('link.is_anchor', return_value=False):
            self.assertFalse(leader._is_binding_enabled('L'))

    def test_l_enabled_when_selected_is_anchor(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        node = MagicMock()
        with patch.dict(sys.modules, {'prefs': fake_prefs}), \
             patch('leader._selected_single_node', return_value=node), \
             patch('link.is_anchor', return_value=True):
            self.assertTrue(leader._is_binding_enabled('L'))

    def test_z_disabled_when_no_back_position(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        fake_anchor = MagicMock()
        fake_anchor._back_position = None
        with patch.dict(sys.modules, {'prefs': fake_prefs, 'anchor': fake_anchor}):
            self.assertFalse(leader._is_binding_enabled('Z'))

    def test_z_enabled_when_back_position_saved(self):
        fake_prefs = MagicMock(plugin_enabled=True)
        fake_anchor = MagicMock()
        fake_anchor._back_position = (1.0, [0.0, 0.0])
        with patch.dict(sys.modules, {'prefs': fake_prefs, 'anchor': fake_anchor}):
            self.assertTrue(leader._is_binding_enabled('Z'))


class TestLeaderArmDisarm(unittest.TestCase):
    """arm() is idempotent and disarm() is safe to call when inactive."""

    def setUp(self):
        leader._leader_active = False
        leader._filter = None
        leader._overlay = None
        leader._overlay_timer = None

    def tearDown(self):
        leader._leader_active = False

    def test_disarm_is_noop_when_not_active(self):
        # No exception, no state changes.
        leader._disarm()
        self.assertFalse(leader._leader_active)

    def test_arm_sets_active_and_installs_filter(self):
        fake_app = MagicMock()
        with patch('leader.QApplication.instance', return_value=fake_app), \
             patch('leader.LeaderKeyFilter') as fake_filter_class:
            fake_filter_class.return_value = MagicMock()
            # Patch the overlay import so arm() doesn't reach into PySide6 widget land.
            with patch.dict(sys.modules, {'leader_overlay': MagicMock()}):
                leader.arm()
        self.assertTrue(leader._leader_active)
        fake_app.installEventFilter.assert_called_once()

    def test_arm_when_already_active_is_noop(self):
        leader._leader_active = True
        with patch('leader.QApplication.instance') as mock_instance:
            leader.arm()
            mock_instance.assert_not_called()


if __name__ == '__main__':
    unittest.main()
