"""Test package init: install all module stubs before any test file is imported.

This module-level code runs once when the tests package is first imported,
which happens before any test module is loaded during `python3 -m unittest
discover`. It ensures that PySide6, tabtabtab_anchors, nuke, and nukescripts are
all stubbed out in sys.modules so that test file imports never race each
other for sys.modules ownership.

An idempotency guard prevents double-installation when pytest has already
loaded conftest.py before importing this package.
"""

import sys
import types
from unittest.mock import MagicMock

if 'nuke' not in sys.modules:
    from tests.stubs import make_stub_nuke_module, make_stub_nukescripts_module

    # -------------------------------------------------------------------------
    # PySide6 stubs — use MagicMock (NOT types.ModuleType) for sub-modules so
    # attribute access (e.g. QtWidgets.QDialog) returns a MagicMock automatically.
    # -------------------------------------------------------------------------

    _pyside6 = MagicMock(name='PySide6')
    _pyside6.QtCore = MagicMock(name='PySide6.QtCore')
    _pyside6.QtGui = MagicMock(name='PySide6.QtGui')
    _pyside6.QtWidgets = MagicMock(name='PySide6.QtWidgets')
    _pyside6.QtCore.Qt = MagicMock()
    sys.modules['PySide6'] = _pyside6
    sys.modules['PySide6.QtCore'] = _pyside6.QtCore
    sys.modules['PySide6.QtGui'] = _pyside6.QtGui
    sys.modules['PySide6.QtWidgets'] = _pyside6.QtWidgets

    # -------------------------------------------------------------------------
    # tabtabtab stub
    # -------------------------------------------------------------------------

    _tabtabtab = types.ModuleType('tabtabtab_anchors')
    _tabtabtab.TabTabTabPlugin = MagicMock
    _tabtabtab.TabTabTabWidget = MagicMock
    sys.modules['tabtabtab_anchors'] = _tabtabtab

    # -------------------------------------------------------------------------
    # nuke and nukescripts stubs
    # -------------------------------------------------------------------------

    sys.modules['nuke'] = make_stub_nuke_module()
    sys.modules['nukescripts'] = make_stub_nukescripts_module()
