"""Superset stub library for offline testing of anchor.py and related modules.

This module defines shared stub classes and factory functions used by all
test files in this suite. It does NOT install anything into sys.modules — that
is the responsibility of conftest.py (pytest) and tests/__init__.py (unittest).

Exports:
    StubKnob                   — superset knob stub covering all five test files
    StubNode                   — superset node stub covering all five test files
    make_stub_nuke_module()    — builds a types.ModuleType('nuke') with all needed attributes
    make_stub_nukescripts_module() — builds a types.ModuleType('nukescripts')
"""

import types
from unittest.mock import MagicMock


class StubKnob:
    """Minimal superset knob stub covering all five per-file StubKnob variants.

    The knob_name parameter supports node.addKnob() lookups via knob.name().
    It defaults to '' so that existing StubKnob(value) calls remain unchanged.
    """

    def __init__(self, value='', knob_name=''):
        self._value = value
        self._visible = True
        self._knob_name = knob_name

    def name(self):
        return self._knob_name

    def getText(self):
        return str(self._value)

    def setValue(self, value):
        self._value = value

    def getValue(self):
        return self._value

    def value(self):
        return self._value

    def setVisible(self, visible):
        self._visible = visible

    def setFlag(self, flag):
        pass

    def setText(self, value):
        self._value = value


class StubNode:
    """Minimal superset node stub covering all five per-file StubNode variants."""

    def __init__(self, name='Node', node_class='NoOp', xpos=0, ypos=0, knobs_dict=None):
        self._name = name
        self._class = node_class
        self._xpos = xpos
        self._ypos = ypos
        self._knobs = knobs_dict or {}
        self._input = None
        self._selected = False
        self._set_name_calls = []

    def name(self):
        return self._name

    def fullName(self):
        return self._name

    def Class(self):
        return self._class

    def xpos(self):
        return self._xpos

    def ypos(self):
        return self._ypos

    def knobs(self):
        return self._knobs

    def screenWidth(self):
        return 100

    def screenHeight(self):
        return 50

    def input(self, index):
        return self._input

    def setInput(self, index, node):
        self._input = node

    def setXYpos(self, x, y):
        self._xpos = x
        self._ypos = y

    def setName(self, new_name):
        self._name = new_name
        self._set_name_calls.append(new_name)

    def addKnob(self, knob):
        self._knobs[knob.name()] = knob

    def removeKnob(self, knob):
        pass

    def __getitem__(self, knob_name):
        if knob_name not in self._knobs:
            raise NameError(f"knob {knob_name} does not exist")
        return self._knobs[knob_name]

    def __setitem__(self, knob_name, value):
        self._knobs[knob_name] = value


def make_stub_nuke_module():
    """Build and return a types.ModuleType('nuke') with all attributes needed by tests.

    NUKE_VERSION_MAJOR is set to 16 to force the PySide6 import path in anchor.py.
    """
    stub = types.ModuleType('nuke')

    stub.StubNode = StubNode
    stub.StubKnob = StubKnob

    root_obj = MagicMock()
    root_obj.name.return_value = 'destScript.nk'
    stub.root = MagicMock(return_value=root_obj)

    stub.allNodes = MagicMock(return_value=[])
    stub.toNode = MagicMock(return_value=None)
    stub.createNode = MagicMock()
    stub.selectedNodes = MagicMock(return_value=[])
    stub.nodeCopy = MagicMock()
    stub.nodePaste = MagicMock(return_value=None)
    stub.exists = MagicMock(return_value=False)
    stub.delete = MagicMock()
    stub.INVISIBLE = 0
    stub.NUKE_VERSION_MAJOR = 16  # critical: forces PySide6 path in anchor.py; do NOT use 14
    stub.PyScript_Knob = MagicMock()
    stub.String_Knob = MagicMock(side_effect=lambda name, *args: StubKnob(knob_name=name))
    stub.Tab_Knob = MagicMock(side_effect=lambda name, *args: StubKnob(knob_name=name))
    stub.Boolean_Knob = MagicMock(side_effect=lambda name, *args: StubKnob(knob_name=name))
    stub.zoom = MagicMock(return_value=1.0)
    stub.center = MagicMock(return_value=[0.0, 0.0])
    stub.zoomToFitSelected = MagicMock()
    stub.getColor = MagicMock(return_value=0)

    return stub


def make_stub_nukescripts_module():
    """Build and return a types.ModuleType('nukescripts') with all attributes needed by tests."""
    stub = types.ModuleType('nukescripts')
    stub.cut_paste_file = lambda: '/tmp/nuke_stub_clipboard.nk'
    stub.clear_selection_recursive = MagicMock()
    return stub
