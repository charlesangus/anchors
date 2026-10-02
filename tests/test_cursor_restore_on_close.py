"""Tests for the popup forcing the arrow cursor back when it closes (issue #90).

The popup opens with the pointer over its QLineEdit, so the IBeam cursor is
showing when it is hidden. TabTabTabWidget.close() pushes an arrow override
cursor and schedules its restore so the IBeam cannot linger over the DAG.
"""

import unittest
from unittest.mock import MagicMock, patch

from tests.test_picker_scroll import _load_core


class TestCursorRestoreOnClose(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.core = _load_core()

    def _closed_widget(self, close_count=1):
        """Close a bare widget *close_count* times under recording Qt mocks and
        return (application_mock, scheduled_callbacks)."""
        widget = object.__new__(self.core.TabTabTabWidget)
        widget.weights = MagicMock()
        widget.plugin = MagicMock()

        application = MagicMock(name='QApplication')
        scheduled_callbacks = []

        def record_single_shot(delay_ms, callback):
            scheduled_callbacks.append((delay_ms, callback))

        timer = type('QTimer', (), {'singleShot': staticmethod(record_single_shot)})
        dialog_close = MagicMock(name='QDialog.close')

        with patch.object(self.core.QtWidgets, 'QApplication', application), \
                patch.object(self.core.QtCore, 'QTimer', timer), \
                patch.object(self.core.QtWidgets.QDialog, 'close', dialog_close, create=True):
            for _ in range(close_count):
                widget.close()

        return application, scheduled_callbacks

    def test_close_forces_arrow_cursor(self):
        application, _ = self._closed_widget()

        application.setOverrideCursor.assert_called_once_with(self.core.Qt.ArrowCursor)

    def test_close_schedules_override_restore_on_next_tick(self):
        """The override must be popped again, or the arrow would stick forever."""
        application, scheduled_callbacks = self._closed_widget()

        self.assertIn((0, application.restoreOverrideCursor), scheduled_callbacks)
        application.restoreOverrideCursor.assert_not_called()

    def test_repeated_closes_keep_push_and_restore_paired(self):
        """The popup is reused across opens, so every close must schedule exactly
        one restore per push and the override stack never grows."""
        application, scheduled_callbacks = self._closed_widget(close_count=3)

        restore_count = sum(
            1 for _, callback in scheduled_callbacks
            if callback is application.restoreOverrideCursor
        )
        self.assertEqual(application.setOverrideCursor.call_count, 3)
        self.assertEqual(restore_count, 3)


if __name__ == '__main__':
    unittest.main()
