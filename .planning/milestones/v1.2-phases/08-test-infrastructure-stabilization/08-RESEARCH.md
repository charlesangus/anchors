# Phase 8: Test Infrastructure Stabilization - Research

**Researched:** 2026-03-12
**Domain:** pytest conftest.py, sys.modules stub ordering, Python test isolation
**Confidence:** HIGH

## Summary

Phase 8 is a pure refactoring phase. The entire test suite already passes when each file
is run in isolation — the problem is pytest's flat discovery ordering. When pytest imports
all test files in a single session, whichever file is imported first wins the `sys.modules`
race for `PySide6`, `nuke`, and related keys. Later files see a partially different stub
than what they installed, causing 4–8 spurious errors under `pytest tests/`.

The fix is authoritative: create `tests/conftest.py` that installs the canonical stub set
at module level before any test file is imported, plus `tests/stubs.py` as the importable
stub library that conftest draws from. All five affected test files then drop their per-file
stub installation blocks entirely.

No new libraries, no pytest plugins, no configuration changes are needed. This is a code
movement and consolidation task. pytest picks up `conftest.py` automatically by convention.

**Primary recommendation:** Write conftest.py as module-level sys.modules assignments (not
session fixtures), synthesize the superset StubKnob/StubNode into stubs.py, and strip all
five affected test files of their per-file stub blocks.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Conftest stub mechanism**
- Use module-level `sys.modules` manipulation at the top of `conftest.py` (not pytest session fixtures)
- Same pattern as existing per-file stubs — just moved to one authoritative location
- Runs before any test file is imported, guaranteeing consistent stub state

**Scope of conftest coverage**
- `conftest.py` covers ALL stubs: Qt (PySide6 + sub-modules), tabtabtab, nuke, nukescripts
- Inconsistent nuke stubs across files are a bug, not a feature — centralize everything
- All 5 affected test files (test_anchor_color_system, test_anchor_navigation, test_cross_script_paste, test_dot_anchor_name_sync, test_dot_type_distinction) drop their per-file stub code entirely

**Stub file location**
- `StubNode`, `StubKnob`, and the nuke stub assembly live in `tests/stubs.py` (new file)
- `conftest.py` imports from `stubs.py` and installs into `sys.modules`
- Test files can also import from `stubs.py` directly if needed (e.g., to construct nodes in tests)
- Separating stubs into their own module makes it possible to write tests for the stubs themselves ("test the test")

**Nuke stub richness**
- `stubs.py` provides the full, richest nuke stub: `StubNode`, `StubKnob`, plus all nuke API surface currently used across test files (`nuke.allNodes()`, `nuke.root()`, `nuke.NUKE_VERSION_MAJOR`, etc.)
- This is the superset of what all 5 test files currently define independently

**Per-test customization**
- Individual tests continue to use `unittest.mock.patch()` for per-test nuke behavior overrides (e.g., `nuke.allNodes()` returning a specific list)
- `stubs.py` stub state is not designed to be mutated directly between tests — patch() is the right tool

**Per-file stub cleanup**
- Remove all per-file Qt/tabtabtab/nuke stub blocks from all affected test files completely (clean removal)
- Keeping them would defeat the purpose — they overwrite conftest stubs on import

### Claude's Discretion
- Exact `StubNode`/`StubKnob` API surface (synthesize the superset from all 5 current definitions)
- Whether `test_prefs.py` needs any changes (it has a minimal nuke stub but no Qt stubs — may already work once conftest runs first)
- Internal structure of `stubs.py` beyond the above constraints

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-03 | `tests/conftest.py` created with shared stubs — fixes pytest flat-discovery Qt stub ordering conflicts (4–8 spurious errors) | Confirmed root cause via code audit; conftest.py + stubs.py pattern directly addresses this |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | system (not installed — see Wave 0) | Test runner and conftest.py loader | De-facto Python test standard; conftest.py is a pytest convention |
| unittest.mock | stdlib | MagicMock and patch() for per-test overrides | Already used throughout all 5 test files |
| types | stdlib | types.ModuleType for stub module construction | Already used throughout all 5 test files |
| sys | stdlib | sys.modules injection for offline stubs | Already established pattern in all test files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| importlib | stdlib | importlib.reload() in setUp() when module needs re-import with fresh stubs | test_anchor_color_system.py uses this pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Module-level sys.modules in conftest | pytest session fixture with autouse=True | Fixtures run after module-level code in conftest — wrong ordering; module-level is correct |
| Separate stubs.py | Inline classes in conftest.py | stubs.py makes "test the test" possible; also reduces conftest size |

**Installation:**
```bash
# pytest is not currently installed in this environment.
# Nuke ships Python 3.11 at /usr/local/Nuke16.0v6/python3.11
# Network is unreachable — pytest must be installed from a local wheel or
# be present in a virtual environment. Wave 0 must address this before tests can run.
/usr/local/Nuke16.0v6/python3.11 -m pip install pytest  # requires network or local wheel
```

**Note on pytest availability:** The current environment has no pytest binary. The project
uses `/usr/local/Nuke16.0v6/python3.11` as the Python interpreter (Nuke 16.0v6 ships Python
3.11). Pytest is not in its site-packages. A Wave 0 task must establish how `pytest tests/`
is run — either by installing pytest into that interpreter or by confirming an alternative
invocation. All test files use only stdlib (unittest, types, sys, importlib), so the tests
themselves are environment-agnostic once pytest is available.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── __init__.py          # already exists (empty, no changes needed)
├── conftest.py          # NEW: module-level stub installation, imports from stubs.py
├── stubs.py             # NEW: StubKnob, StubNode, make_stub_nuke_module(), make_stub_nukescripts_module()
├── test_anchor_color_system.py     # MODIFIED: remove per-file stub block
├── test_anchor_navigation.py       # MODIFIED: remove per-file stub block
├── test_cross_script_paste.py      # MODIFIED: remove per-file stub block
├── test_dot_anchor_name_sync.py    # MODIFIED: remove per-file stub block
├── test_dot_type_distinction.py    # MODIFIED: remove per-file stub block
└── test_prefs.py                   # REVIEW: may need minor change (see pitfalls)
```

### Pattern 1: Module-Level sys.modules in conftest.py

**What:** Top-level Python statements in conftest.py that run before pytest imports any
test file in the directory.

**When to use:** When test files need stubs pre-installed before their own import-time
code runs (which is the case here — the five test files `import anchor` at module level
after their stub blocks).

**Example:**
```python
# tests/conftest.py
# IMPORTANT: module-level code, NOT a pytest fixture.
# This runs before any test file in tests/ is collected.

import sys
import types
from stubs import make_stub_nuke_module, make_stub_nukescripts_module

from unittest.mock import MagicMock

# --- PySide6 stubs (MagicMock-based so attribute access auto-creates attrs) ---
_pyside6_stub = MagicMock(name='PySide6')
_pyside6_stub.QtCore = MagicMock(name='PySide6.QtCore')
_pyside6_stub.QtGui = MagicMock(name='PySide6.QtGui')
_pyside6_stub.QtWidgets = MagicMock(name='PySide6.QtWidgets')
_pyside6_stub.QtCore.Qt = MagicMock()

sys.modules['PySide6'] = _pyside6_stub
sys.modules['PySide6.QtCore'] = _pyside6_stub.QtCore
sys.modules['PySide6.QtGui'] = _pyside6_stub.QtGui
sys.modules['PySide6.QtWidgets'] = _pyside6_stub.QtWidgets

# --- tabtabtab stub ---
_tabtabtab_stub = types.ModuleType('tabtabtab')
_tabtabtab_stub.TabTabTabPlugin = MagicMock
_tabtabtab_stub.TabTabTabWidget = MagicMock
sys.modules['tabtabtab'] = _tabtabtab_stub

# --- nuke and nukescripts stubs ---
sys.modules['nuke'] = make_stub_nuke_module()
sys.modules['nukescripts'] = make_stub_nukescripts_module()
```

### Pattern 2: Superset StubKnob in stubs.py

**What:** The canonical StubKnob must include ALL methods found across any of the five
test file definitions. Missing a method means tests that call it on the conftest-provided
stub will get AttributeError.

**Superset StubKnob API surface (synthesized from all 5 files):**

| Method | Present in | Notes |
|--------|-----------|-------|
| `__init__(value='')` | all | `_visible=True` from dot_anchor_name_sync and dot_type_distinction |
| `getText()` | all | returns `str(self._value)` in color_system, `self._value` elsewhere |
| `setValue(value)` | all | |
| `getValue()` | all | |
| `value()` | color_system, navigation | returns `self._value` |
| `setVisible(visible)` | dot_anchor_name_sync, dot_type_distinction | |
| `setFlag(flag)` | dot_anchor_name_sync, dot_type_distinction | no-op |
| `setText(value)` | dot_anchor_name_sync, dot_type_distinction | alias for setValue |

**Critical getText() discrepancy:** `test_anchor_color_system.py` returns `str(self._value)`
(coerces to string), while `test_cross_script_paste.py` and others return `self._value`
bare. The superset should use `str(self._value)` for getText() since that is the safer and
more consistent behavior.

**Superset StubNode API surface (synthesized from all 5 files):**

| Method | Present in | Notes |
|--------|-----------|-------|
| `__init__(name, node_class, xpos, ypos, knobs_dict)` | all | `_set_name_calls=[]` only in dot_anchor_name_sync |
| `name()` | all | |
| `fullName()` | all except cross_script | cross_script has it; omit check — all have it |
| `Class()` | all | |
| `xpos()` | all | |
| `ypos()` | all | |
| `screenWidth()` | color_system, navigation | returns 100 |
| `screenHeight()` | color_system, navigation | returns 50 |
| `knobs()` | all | |
| `input(index)` | all | |
| `setInput(index, node)` | all | |
| `setXYpos(x, y)` | all | |
| `setName(name)` | all | dot_anchor_name_sync also appends to `_set_name_calls` |
| `addKnob(knob)` | all | color_system and navigation: `self._knobs[knob.name()] = knob`; dot files: no-op `pass` |
| `removeKnob(knob)` | dot_anchor_name_sync, dot_type_distinction | no-op `pass` |
| `__getitem__(knob_name)` | all | raises KeyError if missing |
| `__setitem__(knob_name, value)` | all | |

**Critical addKnob() discrepancy:** color_system and navigation store the knob by
`knob.name()`, while dot_anchor_name_sync and dot_type_distinction use `pass` (no-op).
The superset should store by name (functional behavior wins over no-op), since tests that
exercise `addKnob` in dot files either track it via local monkey-patching or don't check
the internal store.

### Pattern 3: Superset nuke stub API in stubs.py

**Full nuke stub API surface (superset across all 5 files):**

```python
stub.StubNode = StubNode          # class reference
stub.StubKnob = StubKnob          # class reference
stub.root = MagicMock(return_value=root_obj)   # root_obj.name() returns 'destScript.nk'
stub.allNodes = MagicMock(return_value=[])
stub.toNode = MagicMock(return_value=None)
stub.createNode = MagicMock()
stub.selectedNodes = MagicMock(return_value=[])
stub.nodeCopy = MagicMock()
stub.nodePaste = MagicMock(return_value=None)
stub.exists = MagicMock(return_value=False)     # nav uses True; conftest uses False (tests override)
stub.delete = MagicMock()
stub.INVISIBLE = 0
stub.NUKE_VERSION_MAJOR = 16      # triggers PySide6 path in anchor.py
stub.PyScript_Knob = MagicMock(...)
stub.String_Knob = MagicMock(side_effect=lambda name, *args: StubKnob())
stub.Tab_Knob = MagicMock(side_effect=lambda name, *args: StubKnob())
stub.Boolean_Knob = MagicMock(side_effect=lambda name, *args: StubKnob())
stub.zoom = MagicMock(return_value=1.0)         # Phase 4 navigation
stub.center = MagicMock(return_value=[0.0, 0.0])
stub.zoomToFitSelected = MagicMock()
stub.getColor = MagicMock(return_value=0)       # used in color picker tests
```

**nukescripts stub:**
```python
stub_nukescripts = types.ModuleType('nukescripts')
stub_nukescripts.cut_paste_file = lambda: '/tmp/nuke_stub_clipboard.nk'
stub_nukescripts.clear_selection_recursive = MagicMock()
```

### Anti-Patterns to Avoid

- **Pytest session fixture for stub installation:** `@pytest.fixture(scope="session", autouse=True)` runs AFTER module-level conftest code but the test file module-level code runs at import time during collection. Use plain module-level code instead.
- **Leaving any per-file stub block intact:** Even one remaining stub block will overwrite conftest stubs when that file is imported, causing the same ordering conflict.
- **Using types.ModuleType for PySide6 sub-modules:** These don't auto-create attributes; MagicMock is required so that `QtWidgets.QDialog` and similar accesses succeed without AttributeError.
- **Installing stubs in a pytest fixture that runs per-test:** The production modules (anchor.py, paste_hidden.py) are imported once at module-level, not re-imported per test. Stub state changes after import do not affect already-imported module-level names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test isolation between files | Custom import hook or importlib patching | conftest.py module-level sys.modules | pytest loads conftest.py before test files by design |
| Stub sharing across test files | Copying stub code into each file (current state) | tests/stubs.py shared module | DRY, single source of truth |
| Per-test nuke state | Mutating global stub state in setUp() | unittest.mock.patch() context manager | patch() restores original state in tearDown automatically |

**Key insight:** conftest.py is loaded by pytest before any test file in its directory.
Module-level code in conftest.py runs at import time, which is earlier than any test file's
module-level code during collection. This ordering guarantee is the mechanism that makes
centralized stub installation work.

## Common Pitfalls

### Pitfall 1: The PySide6 sub-module MagicMock vs ModuleType Split
**What goes wrong:** Some test files use `_make_stub_qt_module()` (returns `types.ModuleType`)
for `PySide6.QtCore/QtGui/QtWidgets`. ModuleType objects do not auto-create attributes,
so `sys.modules['PySide6.QtWidgets'].QDialog` raises `AttributeError` when anchor.py
does `from PySide6.QtWidgets import QDialog`.

**Why it happens:** `test_cross_script_paste.py`, `test_dot_anchor_name_sync.py`, and
`test_dot_type_distinction.py` use `_make_stub_qt_module()` for sub-modules. When one of
these files was imported first, all subsequent files saw plain ModuleType stubs.

**How to avoid:** conftest.py must use `MagicMock()` (not `types.ModuleType`) for all
`PySide6.*` sub-modules. The test_anchor_color_system.py comment (line 37–43) explicitly
explains why: "Use MagicMock for sub-modules so attribute access (e.g. QtWidgets.QDialog)
returns a MagicMock automatically — this allows colors.py to subclass QtWidgets.QDialog
without AttributeError."

**Warning signs:** `AttributeError: module 'PySide6.QtWidgets' has no attribute 'QDialog'`
or similar when running `pytest tests/` but not when running a single file.

### Pitfall 2: NUKE_VERSION_MAJOR Value Matters
**What goes wrong:** `anchor.py` branches on `nuke.NUKE_VERSION_MAJOR` to choose between
PySide6 and PySide2. If conftest installs a nuke stub with `NUKE_VERSION_MAJOR = 14`,
anchor.py tries PySide2 first, fails (stub not present), and leaves Qt globals as None,
causing AttributeError in tests that use Qt.

**Why it happens:** `test_prefs.py` uses version 14. The correct value for test_anchor_*
files is 16 (forces PySide6 path).

**How to avoid:** conftest.py must set `NUKE_VERSION_MAJOR = 16`. `test_prefs.py` currently
guards with `if 'nuke' not in sys.modules:` — once conftest installs nuke stub first,
test_prefs.py's guard will skip its own stub installation entirely. Since test_prefs.py
only needs a minimal nuke stub for import (it does not exercise anchor.py Qt paths), this
is safe — the conftest stub with NUKE_VERSION_MAJOR=16 is strictly richer than test_prefs.py's
minimal stub with version=14.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute '...'` in Qt-related
tests when running the full suite but not in isolation.

### Pitfall 3: test_anchor_color_system.py Replaces the colors Stub Mid-File
**What goes wrong:** This file installs a placeholder `colors` stub before importing anchor,
then deletes it and imports the real `colors.py` (lines 188–192). This is specific to this
test file's COLOR-* tests and must be preserved after removing only the Qt/tabtabtab/nuke
stub blocks.

**Why it happens:** `anchor.py` does `from colors import ColorPaletteDialog`. Without a
real colors module (which itself needs the nuke stub to be present first), the import fails.
The sequence is: nuke stub → placeholder colors stub → import anchor → delete placeholder →
import real colors.

**How to avoid:** When removing per-file stub code from test_anchor_color_system.py, only
remove the Qt, tabtabtab, and nuke/nukescripts blocks. The `_colors_stub` placeholder and
the subsequent `del sys.modules['colors']` / `import colors as _real_colors_module` sequence
must remain in the file.

**Warning signs:** `ImportError` for colors module, or tests failing because
`ColorPaletteDialog` is None when it should be the real class.

### Pitfall 4: test_anchor_navigation.py's _ensure_qt_stubs_support_mock_attributes()
**What goes wrong:** This helper (defined in both test_anchor_color_system.py and
test_anchor_navigation.py) was a band-aid: it detected if Qt stubs were plain ModuleType
and patched them to MagicMock at setUp time. Once conftest installs MagicMock stubs
authoritatively, this helper becomes a no-op — but it must remain callable (do not delete
it). It is still called from `setUp()` methods and must not be removed from those files
during the stub block cleanup.

**How to avoid:** Remove only the top-of-file stub installation blocks (everything from
`def _make_stub_qt_module` through `sys.modules['nukescripts'] = ...`). Leave the
`_ensure_qt_stubs_support_mock_attributes()` function and all class definitions in place.

### Pitfall 5: addKnob() Behavior Difference
**What goes wrong:** dot_anchor_name_sync and dot_type_distinction use `pass` in addKnob()
(no-op), but their tests locally monkey-patch `node.addKnob` in specific test cases via
a local `tracking_addKnob` function. If the conftest StubNode stores the knob (functional
behavior from color_system/navigation), tests that expected a no-op but do their own
tracking could double-count.

**How to avoid:** Review dot_type_distinction tests at lines 208 and 262 where
`tracking_addKnob` is used. The monkey-patching replaces the method entirely, so the
base implementation does not matter for those tests. Using the functional implementation
(store by knob.name()) in stubs.py is safe.

## Code Examples

Verified patterns from code audit of existing test files:

### conftest.py Structure (canonical)
```python
# tests/conftest.py
# Module-level code — runs before any test file in tests/ is collected by pytest.

import sys
import types
from unittest.mock import MagicMock

from stubs import make_stub_nuke_module, make_stub_nukescripts_module

# PySide6: use MagicMock for sub-modules (not types.ModuleType) so that
# attribute access like QtWidgets.QDialog returns a MagicMock, not AttributeError.
_pyside6 = MagicMock(name='PySide6')
_pyside6.QtCore = MagicMock(name='PySide6.QtCore')
_pyside6.QtGui = MagicMock(name='PySide6.QtGui')
_pyside6.QtWidgets = MagicMock(name='PySide6.QtWidgets')
_pyside6.QtCore.Qt = MagicMock()

sys.modules['PySide6'] = _pyside6
sys.modules['PySide6.QtCore'] = _pyside6.QtCore
sys.modules['PySide6.QtGui'] = _pyside6.QtGui
sys.modules['PySide6.QtWidgets'] = _pyside6.QtWidgets

_tabtabtab = types.ModuleType('tabtabtab')
_tabtabtab.TabTabTabPlugin = MagicMock
_tabtabtab.TabTabTabWidget = MagicMock
sys.modules['tabtabtab'] = _tabtabtab

sys.modules['nuke'] = make_stub_nuke_module()
sys.modules['nukescripts'] = make_stub_nukescripts_module()
```

### Stub Block to Remove from Each Test File
The following pattern appears at the top of each of the 5 affected files and must be
completely removed:
```python
def _make_stub_qt_module(name):
    ...

_pyside6_stub = ...
_pyside6_stub.QtCore = ...
sys.modules['PySide6'] = _pyside6_stub
sys.modules['PySide6.QtCore'] = ...
sys.modules['PySide6.QtGui'] = ...
sys.modules['PySide6.QtWidgets'] = ...

_tabtabtab_stub = ...
sys.modules['tabtabtab'] = _tabtabtab_stub

def make_stub_nuke_module():
    ...

sys.modules['nuke'] = make_stub_nuke_module()
sys.modules['nukescripts'] = ...
```

### test_prefs.py Guard — No Change Needed
```python
# test_prefs.py (current, keep as-is)
if 'nuke' not in sys.modules:
    nuke_stub = types.ModuleType('nuke')
    nuke_stub.NUKE_VERSION_MAJOR = 14
    sys.modules['nuke'] = nuke_stub
```
Once conftest installs nuke first, this guard evaluates False and skips. The richer
conftest stub (NUKE_VERSION_MAJOR=16) is a superset of what test_prefs.py needs.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-file stub blocks (5 duplicates) | conftest.py + stubs.py (single source) | Phase 8 | Eliminates 4–8 spurious flat-discovery errors |
| Band-aid `_ensure_qt_stubs_support_mock_attributes()` | Unnecessary (conftest provides MagicMock stubs) | Phase 8 | Function can remain but becomes permanently a no-op |

**Deprecated/outdated after this phase:**
- Per-file `make_stub_nuke_module()` functions in all 5 test files
- Per-file `_make_stub_qt_module()` helper functions
- Per-file `sys.modules` assignment blocks for Qt, tabtabtab, nuke, nukescripts

## Open Questions

1. **pytest installation**
   - What we know: pytest is not installed in the Nuke Python environment; network is unreachable; all tests use only stdlib
   - What's unclear: Is there a virtual environment or local wheel available? Is there another Python (e.g., system Python 3.x) with pytest?
   - Recommendation: Wave 0 task must determine how `pytest tests/` is actually invoked on this machine. If no pytest is available, the phase cannot be validated. Check for a venv, a Makefile, or project-specific documentation for the test runner command.

2. **test_anchor_color_system.py colors stub sequence**
   - What we know: This file does placeholder colors stub → import anchor → real colors import
   - What's unclear: If conftest also pre-installs colors (or does not), does the test file's sequence still work?
   - Recommendation: conftest.py should NOT pre-install a colors stub. Let test_anchor_color_system.py manage its own colors stub sequence, which is test-file-specific logic unrelated to the Qt/nuke stub ordering problem.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version unknown — not currently installed) |
| Config file | none — conftest.py is picked up automatically by pytest from `tests/` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/` |

**Note:** pytest must be installed before any command can run. See Open Questions above.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-03 | `pytest tests/` completes with zero errors and zero failures | smoke | `pytest tests/ -q` | ❌ Wave 0 (conftest.py and stubs.py must be created) |
| TEST-03 | All individual test files pass in isolation | smoke | `pytest tests/test_anchor_color_system.py tests/test_anchor_navigation.py tests/test_cross_script_paste.py tests/test_dot_anchor_name_sync.py tests/test_dot_type_distinction.py tests/test_prefs.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (stop on first failure)
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — installs canonical stubs; covers TEST-03 (flat discovery)
- [ ] `tests/stubs.py` — provides StubKnob, StubNode, make_stub_nuke_module(), make_stub_nukescripts_module()
- [ ] pytest installation — `pytest` must be available to run `pytest tests/`; determine invocation method for this machine

## Sources

### Primary (HIGH confidence)
- Direct code audit of `/workspace/tests/test_anchor_color_system.py` — StubKnob/StubNode API, MagicMock sub-module rationale, colors stub sequence
- Direct code audit of `/workspace/tests/test_anchor_navigation.py` — Phase 4 viewport stubs, _ensure_qt_stubs_support_mock_attributes rationale
- Direct code audit of `/workspace/tests/test_cross_script_paste.py` — ModuleType sub-module difference (root cause of conflict)
- Direct code audit of `/workspace/tests/test_dot_anchor_name_sync.py` — StubKnob.setVisible/setFlag/setText additions, addKnob no-op
- Direct code audit of `/workspace/tests/test_dot_type_distinction.py` — knob factory stubs (String_Knob, Tab_Knob, Boolean_Knob)
- Direct code audit of `/workspace/tests/test_prefs.py` — conditional guard pattern, NUKE_VERSION_MAJOR=14
- `/workspace/.planning/phases/08-test-infrastructure-stabilization/08-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- pytest documentation (from training knowledge, current as of pytest 7–8): conftest.py module-level code runs before test collection; this is stable pytest behavior since pytest 3.x

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or pytest (well-established)
- Architecture: HIGH — based on direct code audit of all 6 test files; no guesswork
- Pitfalls: HIGH — root causes identified from comments in test_anchor_color_system.py (lines 204–226) and _ensure_qt_stubs_support_mock_attributes() implementation
- Stub superset: HIGH — synthesized by reading all method definitions across all 5 files

**Research date:** 2026-03-12
**Valid until:** This research is based on static code audit and does not depend on
external libraries evolving — valid indefinitely for this codebase.
