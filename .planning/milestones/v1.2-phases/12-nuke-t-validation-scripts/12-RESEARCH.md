# Phase 12: Nuke -t Validation Scripts - Research

**Researched:** 2026-03-14
**Domain:** Nuke headless scripting (`nuke -t`), stub alignment verification, cross-script paste smoke testing
**Confidence:** HIGH (project code fully readable; all constraints from CONTEXT.md are locked and specific)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Output format**
- One line per check, always printed: `PASS: <check name>` or `FAIL: <check> — expected X, got Y`
- On failure: print and continue — collect all failures, don't stop at first
- Final line: `Summary: N/M checks passed` followed by `sys.exit(1)` if any failed
- Exit code is CI-friendly (0 = all passed, 1 = any failed)

**Stub assumptions scope (validate_stub_alignment.py)**
- Exhaustive: probe all StubNode and StubKnob methods against their real Nuke counterparts
- Also validate nuke module-level API return types and signatures: `allNodes()` returns a list, `toNode()` returns None when node not found, `createNode()` returns a real node object
- Print `nuke.NUKE_VERSION_MAJOR` for informational context; warn (but don't fail) if below 14
- Highest-risk probes (flagged in STATE.md): `nuke.root().name()` in headless, node `['knob_name']` access pattern (KeyError on miss), `tile_color` knob read/write, `StubKnob.getValue()` vs `.value()` equivalence

**Cross-script smoke test design (validate_cross_script_paste.py)**
- Use real `.nk` file write + `nuke.nodePaste()` as the primary mechanism — most realistic
- BUG-01 assertion: after `setup_link_node()`, assert `link_node['tile_color'].value() == anchor_node['tile_color'].value()` (link receives the anchor's real color, not ANCHOR_DEFAULT_COLOR / purple)
- BUG-02 assertion: fake the FQNN stem mismatch by controlling `nuke.root().name()` so its stem differs from the anchor's FQNN stem; call the relevant paste path; assert the node stays an anchor (not converted to a link)
- Clean up all created nodes with `nuke.delete()` after each check to keep the session clean

**Correction policy**
- If a stub method diverges from real Nuke: fix `tests/stubs.py` to match real behavior
- If that fix causes `pytest tests/` to go red: fix the production source files (`paste_hidden.py`, `link.py`, `anchor.py`) — the test going red means the stub was papering over a production bug
- Only fix test assertions as a last resort (when real behavior is confirmed correct but the test was testing the wrong thing)
- No CORRECTIONS.md — git commit message documents what was found and fixed

### Claude's Discretion
- Exact helper structure within each validation script (a `run_check()` helper or inline try/except pattern)
- Whether to use a shared `validation/` `__init__.py` or keep scripts standalone
- Exact set of nuke module-level API surfaces to probe beyond the ones named above
- Whether to add a `validation/README.md` with usage instructions

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | `nuke -t` validation scripts written covering StubNode/StubKnob assumptions and cross-script paste behavior | Architecture Patterns section defines both script structures; Code Examples section provides scaffolding patterns |
| TEST-02 | Any stub/mock inconsistencies found by validation scripts corrected in `tests/` | Correction Policy section defines the three-tier correction priority; pitfalls section documents highest-risk stub divergence points |
</phase_requirements>

---

## Summary

Phase 12 creates two standalone Python scripts in a new `validation/` directory. They are never run by pytest or CI — a developer with a local licensed Nuke install runs them with `nuke -t`. `validate_stub_alignment.py` probes every StubNode and StubKnob method against the real Nuke API and also validates nuke module-level function return types. `validate_cross_script_paste.py` smoke-tests the BUG-01 and BUG-02 fixed code paths using a real `.nk` file write + `nuke.nodePaste()` mechanism.

The correction policy is strict: any stub divergence found goes into `tests/stubs.py` first. If that correction causes `pytest tests/` to redden, the production source is what gets fixed — a newly-red test reveals that the stub was papering over a real production bug. Test assertion corrections are the last resort only.

Both scripts must never import `menu.py` and must never reach Qt dialog code paths. They run in headless mode (`nuke -t`), where there is no display server and no interactive UI.

**Primary recommendation:** Implement a `run_check(name, callable)` helper at the top of each script that captures `PASS`/`FAIL` output uniformly and accumulates a failure count, then call `sys.exit(1)` at the end if failures > 0. Keep scripts fully standalone — no shared `__init__.py` needed.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `nuke` (real) | ≥14 (warn if below) | Provides the actual API surface being validated | This IS the system under test |
| `sys` (stdlib) | any | `sys.exit()` for CI-friendly exit code | Standard Python exit signaling |
| `os` (stdlib) | any | `os.path.join()` for .nk temp file path | Safe cross-platform path handling |
| `tempfile` (stdlib) | any | Temporary .nk file for nodePaste smoke test | Cleaner than hardcoding `/tmp/` paths |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `nukescripts` (real) | bundled with Nuke | `nukescripts.cut_paste_file()` returns the clipboard temp path | validate_cross_script_paste.py needs this for .nk write destination |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tempfile.mkstemp()` for .nk path | hardcoded `/tmp/test.nk` | `nukescripts.cut_paste_file()` is already what the production code uses; use it for maximum realism |
| inline try/except per check | `run_check()` helper | Helper avoids 50+ duplicated try/except blocks; chosen for readability |

**Installation:** No additional packages required. Scripts run in the Nuke Python environment.

---

## Architecture Patterns

### Recommended Project Structure
```
validation/
├── validate_stub_alignment.py    # StubNode/StubKnob alignment checks
└── validate_cross_script_paste.py  # BUG-01 and BUG-02 smoke tests
```

No `__init__.py` — scripts are standalone, invoked as:
```
nuke -t /path/to/repo/validation/validate_stub_alignment.py
nuke -t /path/to/repo/validation/validate_cross_script_paste.py
```

Nuke's `nuke -t` interpreter sets up `nuke` and `nukescripts` in the Python environment automatically. The scripts must add the repo root to `sys.path` (via `os.path.dirname(__file__)`) so they can import production modules without needing the plugin installed.

### Pattern 1: Check Runner Helper
**What:** A single function that wraps each probe, catches exceptions, formats `PASS`/`FAIL` output, and increments a failure counter.
**When to use:** Use for every probe in both scripts — keeps output format consistent.
**Example:**
```python
import sys

_failures = 0

def run_check(name, fn):
    """Run fn(); print PASS or FAIL. Increment global failure counter on failure."""
    global _failures
    try:
        fn()
        print(f"PASS: {name}")
    except AssertionError as exc:
        print(f"FAIL: {name} — {exc}")
        _failures += 1
    except Exception as exc:
        print(f"FAIL: {name} — unexpected exception: {type(exc).__name__}: {exc}")
        _failures += 1
```

### Pattern 2: sys.path Bootstrap (Required for Standalone Scripts)
**What:** Add the repo root to `sys.path` before importing production modules.
**When to use:** At the very top of both scripts, before any import of `link`, `anchor`, `paste_hidden`, or `constants`.
**Example:**
```python
import os
import sys

# Add repo root so production modules are importable without plugin install.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
```

### Pattern 3: BUG-02 Headless Stem Control
**What:** Temporarily override `nuke.root().name()` to return a value whose stem differs from the anchor's FQNN stem, simulating a cross-script paste without actually switching scripts.
**When to use:** In `validate_cross_script_paste.py` for the BUG-02 check.
**Example:**
```python
# Real Nuke allows mutating the script name knob directly in headless
# to control what nuke.root().name() returns:
nuke.root()['name'].setValue('destScript.nk')
# anchor's stored FQNN was stamped as 'sourceScript.Anchor_Name'
# so fqnn_stem ('sourceScript') != current_stem ('destScript') => is_cross_script = True
```

### Pattern 4: .nk File Write + nodePaste (BUG-01/BUG-02 Primary Mechanism)
**What:** Write node state to a real `.nk` file then paste it back — exactly what production code does.
**When to use:** For BUG-01 and BUG-02 smoke tests where the cross-script detection logic in `paste_hidden()` must be exercised via the actual `nuke.nodePaste()` API.
**Example:**
```python
# Copy an anchor node to the clipboard file:
nuke.nodeCopy(nukescripts.cut_paste_file())
# Paste it back — this is what paste_hidden() calls internally:
nuke.nodePaste(nukescripts.cut_paste_file())
```

### Pattern 5: Node Cleanup After Each Check
**What:** Call `nuke.delete(node)` for every node created during a check, even on failure.
**When to use:** Mandatory after every check in `validate_cross_script_paste.py` to keep the session clean.
**Example:**
```python
def check_bug01_color():
    anchor = nuke.createNode('NoOp')
    link = nuke.createNode('NoOp')
    try:
        anchor['tile_color'].setValue(0xff0000ff)  # red
        setup_link_node(anchor, link)
        actual = link['tile_color'].value()
        assert actual == 0xff0000ff, f"expected 0xff0000ff, got {hex(actual)}"
    finally:
        nuke.delete(link)
        nuke.delete(anchor)
```

### Anti-Patterns to Avoid
- **Importing `menu.py` in validation scripts:** `menu.py` calls `nuke.menu()` at module level; in headless mode this may succeed but also invokes Qt menu construction that can fail or produce spurious output. Import `paste_hidden`, `link`, `anchor`, `constants` directly.
- **Importing `colors.py` in validation scripts:** `colors.py` subclasses `QtWidgets.QDialog`; real Qt is present in GUI mode but headless `nuke -t` has no display. This will raise.
- **Importing `anchor.py` at module level without care:** `anchor.py` imports `from colors import ColorPaletteDialog` at the top, which triggers `QtWidgets` import. In headless, the Qt import guard (`try/except ImportError`) handles this — `ColorPaletteDialog` ends up `None`. This is safe as long as no dialog code is called.
- **Calling `nuke.selectedNodes()` and mutating the list:** `paste_hidden()` mutates the list returned by `nuke.selectedNodes()` in-place in a loop; validation scripts must exercise the actual public API path, not replicate production internals.
- **Using `assert` outside `run_check()`:** An uncaught `AssertionError` will terminate the script with a traceback instead of collecting the failure and continuing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CI-friendly exit | Custom exit code logic | `sys.exit(0)` / `sys.exit(1)` | Standard, recognized by all CI runners |
| .nk temp path | Hardcoded `/tmp/nuke_test.nk` | `nukescripts.cut_paste_file()` | Matches what production code uses; guaranteed to be writable by Nuke |
| Color value comparison | Bit-shifting hex arithmetic | Direct integer compare `== 0xff0000ff` | Color ints in Nuke are already plain Python ints |
| Node Class detection | String parsing on node names | `node.Class()` | The real Nuke API; stubs already implement this |

---

## Common Pitfalls

### Pitfall 1: `nuke.root().name()` Returns Empty String in Fresh Headless Session
**What goes wrong:** In a freshly started `nuke -t` session with no script loaded, `nuke.root().name()` may return `''` or `'Root'` (not a `'scriptname.nk'` string). The stub returns `'destScript.nk'` but the real value in headless is unknown until verified.
**Why it happens:** STATE.md explicitly marks this as MEDIUM confidence. The stub assumes a file-like name, but headless Nuke may not have initialized the root name.
**How to avoid:** In `validate_stub_alignment.py`, probe `nuke.root().name()` and assert it is a string (not necessarily filename-shaped). Document the actual value. In `validate_cross_script_paste.py`, explicitly call `nuke.root()['name'].setValue('destScript.nk')` before any cross-script stem comparison — don't rely on the default.
**Warning signs:** Stem-comparison logic yields `current_stem = ''` which would make `fqnn_stem != current_stem` vacuously true for any non-empty FQNN, always triggering cross-script path.

### Pitfall 2: `StubKnob.getValue()` vs `.value()` Divergence
**What goes wrong:** The stub implements both `getValue()` and `value()` as synonyms returning `self._value`. Real Nuke knobs may return different Python types: `value()` may return `int` for color knobs, `float` for numeric knobs, `str` for string knobs; `getValue()` may return `float` regardless. A stub returning the value-as-stored could mask a type coercion the production code depends on.
**Why it happens:** The stub was built from test needs, not from reading Nuke's actual API contracts.
**How to avoid:** In `validate_stub_alignment.py`, check `type(nuke.createNode('NoOp')['tile_color'].value())` is `int` (or at minimum not an unexpected type), and ditto for `getValue()`. If there is a discrepancy, the stub must match real behavior.
**Warning signs:** Production code that compares `tile_color.value() == 0` may behave differently if real Nuke returns a float `0.0` instead of int `0`.

### Pitfall 3: `node['knob_name']` KeyError Behavior
**What goes wrong:** The stub raises `KeyError` when a knob is not present (matches real Nuke). However, the stub implementation uses a plain dict — real Nuke may raise a different exception type or provide a different message format.
**Why it happens:** The stub intentionally matches the KeyError behavior, but exception type must be verified.
**How to avoid:** Probe `node['does_not_exist']` and assert `KeyError` is raised. This is already in the highest-risk list from CONTEXT.md.

### Pitfall 4: `nuke -t` Invocation Path
**What goes wrong:** Developer may run `python3 validation/validate_stub_alignment.py` directly. This will fail because `nuke` is not importable outside the Nuke Python environment.
**Why it happens:** Scripts target `nuke -t` specifically; plain Python doesn't have the `nuke` module.
**How to avoid:** Add a guard at the top of each script:
```python
try:
    import nuke
except ImportError:
    print("ERROR: This script must be run under nuke -t, not plain Python.")
    sys.exit(2)
```

### Pitfall 5: Importing `anchor.py` Triggers `colors.py` Qt Import
**What goes wrong:** `anchor.py` imports `from colors import ColorPaletteDialog` at module level. `colors.py` subclasses `QtWidgets.QDialog`. In headless `nuke -t`, PySide6/PySide2 IS available (Nuke bundles it), but opening a display-dependent dialog crashes.
**Why it happens:** The try/except guard in `anchor.py` only handles `ImportError` at the PySide6 import line — if PySide6 imports successfully but no display is present, dialog `.exec_()` crashes at runtime.
**How to avoid:** Import only `link`, `paste_hidden`, and `constants` in validation scripts. If `anchor.py` functions are needed (e.g., `find_anchor_by_name`), import the specific function only after confirming no Qt dialog code is triggered. Never call any function that leads to `ColorPaletteDialog()` instantiation.

### Pitfall 6: `find_node_default_color()` Calls `nuke.toNode("preferences")`
**What goes wrong:** `link.find_node_default_color()` calls `nuke.toNode("preferences")` to look up per-class color slots. In headless, `nuke.toNode("preferences")` may return a real preferences node or may return `None`. If it returns `None`, the subsequent `None["NodeColourSlot..."]` access raises `TypeError`.
**Why it happens:** The stub returns `None` for `toNode()` unconditionally. Real Nuke has a built-in preferences node that is always present.
**How to avoid:** In `validate_stub_alignment.py`, probe `nuke.toNode("preferences")` and assert it is not None. The stub's `toNode = MagicMock(return_value=None)` is the stub assumption most likely to diverge from real Nuke. Document the actual return value. If the stub is wrong, fix it to return an appropriate object (or update `find_node_default_color` to guard for None).

---

## Code Examples

### validate_stub_alignment.py — Script Skeleton
```python
"""Validate that StubNode/StubKnob assumptions in tests/ match real Nuke API.

Run with:
    nuke -t /path/to/repo/validation/validate_stub_alignment.py
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    import nuke
except ImportError:
    print("ERROR: Run this script under nuke -t, not plain Python.")
    sys.exit(2)

print(f"INFO: NUKE_VERSION_MAJOR = {nuke.NUKE_VERSION_MAJOR}")
if nuke.NUKE_VERSION_MAJOR < 14:
    print("WARN: Nuke version below 14 — some API surface may differ from stub assumptions")

_failures = 0

def run_check(name, fn):
    global _failures
    try:
        fn()
        print(f"PASS: {name}")
    except AssertionError as exc:
        print(f"FAIL: {name} — {exc}")
        _failures += 1
    except Exception as exc:
        print(f"FAIL: {name} — unexpected exception: {type(exc).__name__}: {exc}")
        _failures += 1

# --- StubKnob alignment checks ---

def check_knob_value_returns_correct_type():
    node = nuke.createNode('NoOp')
    try:
        knob = node['tile_color']
        result = knob.value()
        assert isinstance(result, (int, float)), f"tile_color.value() type: {type(result)}"
    finally:
        nuke.delete(node)

run_check("StubKnob: tile_color.value() returns int or float", check_knob_value_returns_correct_type)

# ... (additional checks follow same pattern)

total = _failures  # total checks run can be tracked separately if desired
print(f"\nSummary: {total} failure(s)")  # replace with N/M pattern in implementation
if _failures > 0:
    sys.exit(1)
sys.exit(0)
```

### validate_cross_script_paste.py — BUG-01 Check Pattern
```python
def check_bug01_link_receives_anchor_color():
    """After setup_link_node(), link tile_color must equal anchor tile_color."""
    from link import setup_link_node
    anchor_color = 0xff0000ff  # red — distinct from ANCHOR_DEFAULT_COLOR purple
    anchor = nuke.createNode('NoOp')
    link = nuke.createNode('NoOp')
    try:
        anchor['tile_color'].setValue(anchor_color)
        setup_link_node(anchor, link)
        actual = link['tile_color'].value()
        assert actual == anchor_color, (
            f"expected anchor color {hex(anchor_color)}, got {hex(int(actual))} — "
            f"ANCHOR_DEFAULT_COLOR is {hex(ANCHOR_DEFAULT_COLOR)}"
        )
    finally:
        nuke.delete(link)
        nuke.delete(anchor)

run_check("BUG-01: link receives anchor tile_color via setup_link_node()", check_bug01_link_receives_anchor_color)
```

### validate_cross_script_paste.py — BUG-02 Check Pattern
```python
def check_bug02_anchor_stays_anchor_cross_script():
    """Anchor pasted cross-script must not be replaced by a link node."""
    from paste_hidden import paste_hidden
    from constants import KNOB_NAME, ANCHOR_PREFIX

    # Create an anchor node and stamp it with a cross-script FQNN
    anchor = nuke.createNode('NoOp')
    anchor.setName(ANCHOR_PREFIX + 'TestAnchor')
    # Set root name to dest script; stamp FQNN from source script
    nuke.root()['name'].setValue('destScript.nk')
    from link import add_input_knob
    add_input_knob(anchor)
    anchor[KNOB_NAME].setValue('sourceScript.Anchor_TestAnchor')  # cross-script

    # Paste via real .nk file mechanism
    nuke.nodeCopy(nukescripts.cut_paste_file())
    try:
        # After paste_hidden(), the pasted anchor must remain as anchor (not replaced)
        # paste_hidden() checks is_anchor() + find_anchor_node() returns None -> continue
        # This verifies BUG-02 fix: unconditional continue for cross-script anchor path
        paste_hidden()
        # If we reach here without createNode/delete being called on the anchor, BUG-02 is fixed
        # Verification: anchor node with that name still exists in the session
        found = nuke.toNode(ANCHOR_PREFIX + 'TestAnchor')
        assert found is not None, "anchor was deleted — BUG-02 regression"
    finally:
        surviving = nuke.toNode(ANCHOR_PREFIX + 'TestAnchor')
        if surviving is not None:
            nuke.delete(surviving)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-test StubKnob/StubNode in each test file | Centralized `tests/stubs.py` with superset stubs | Phase 8 | All stubs to validate are in one file: `tests/stubs.py` |
| No headless validation | `nuke -t` validation scripts | Phase 12 (this phase) | Confirms stub assumptions against real runtime |
| `nuke.toNode` returns None unconditionally in stub | Unknown — needs verification against real Nuke | Phase 12 probe | `find_node_default_color()` calls `toNode("preferences")` — this is the highest-risk stub |

**Deprecated/outdated:**
- Per-file stub variants: Each test file previously defined its own StubKnob/StubNode. Removed in Phase 8 — all tests now use `tests/stubs.py`.

---

## Open Questions

1. **`nuke.root().name()` default value in fresh headless session**
   - What we know: STATE.md marks this MEDIUM confidence; stub returns `'destScript.nk'`
   - What's unclear: Real Nuke headless may return `''`, `'Root'`, or something else before any script is loaded
   - Recommendation: The `validate_stub_alignment.py` check should probe and PRINT the actual value (not assert a specific value), then document the finding to decide whether the stub needs updating

2. **`nuke.toNode("preferences")` in headless**
   - What we know: `link.find_node_default_color()` calls this; stub returns `None`; real Nuke always has a preferences node
   - What's unclear: Whether headless `nuke -t` exposes the same preferences node as GUI mode
   - Recommendation: This is priority check #2 after `nuke.root().name()`. If `toNode("preferences")` returns a real node, the stub `MagicMock(return_value=None)` is wrong and must be updated to something that doesn't break `find_node_default_color()`.

3. **`tile_color.value()` integer vs float type in real Nuke**
   - What we know: Stub stores and returns whatever type was set. In tests, integer hex literals are used (`0x6f3399ff`).
   - What's unclear: Real Nuke knobs may coerce integer tile_color values to float upon storage/retrieval.
   - Recommendation: Probe `type(node['tile_color'].value())` after setting an int. If float is returned, update stub's `getValue()` and `value()` to coerce, and fix any production comparison `== 0` to `== 0.0` or `not value`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) + pytest for offline suite |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | `validation/validate_stub_alignment.py` runs to completion under `nuke -t` without errors | manual-only (requires licensed Nuke install) | `nuke -t validation/validate_stub_alignment.py` | ❌ Wave 0 |
| TEST-01 | `validation/validate_cross_script_paste.py` runs to completion under `nuke -t` without errors | manual-only (requires licensed Nuke install) | `nuke -t validation/validate_cross_script_paste.py` | ❌ Wave 0 |
| TEST-02 | `pytest tests/` remains green after any stub corrections | automated | `python3 -m pytest tests/ -x -q` | ✅ exists |

**Manual-only justification for TEST-01:** Nuke requires a commercial license and is not available on GitHub-hosted CI runners (explicitly Out of Scope in REQUIREMENTS.md). Validation scripts are developer-run tools, not CI gates.

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/`
- **Phase gate:** Full `pytest tests/` green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `validation/validate_stub_alignment.py` — covers TEST-01 (StubNode/StubKnob alignment)
- [ ] `validation/validate_cross_script_paste.py` — covers TEST-01 (BUG-01 and BUG-02 smoke tests)
- [ ] `validation/` directory must be created (does not exist yet)

*(All gaps are the deliverables of this phase — no existing test infrastructure needed; offline `pytest tests/` suite is already green.)*

---

## Sources

### Primary (HIGH confidence)
- `/workspace/tests/stubs.py` — authoritative list of all stub methods and assumptions to probe
- `/workspace/tests/conftest.py` — shows sys.modules keys being stubbed; validation scripts must NOT stub these
- `/workspace/paste_hidden.py` — production BUG-01 and BUG-02 code paths, `nuke.root().name().split('.')[0]` stem logic
- `/workspace/link.py` — `setup_link_node()`, `find_node_color()`, `find_node_default_color()` (calls `toNode("preferences")`), `get_fully_qualified_node_name()`
- `/workspace/anchor.py` — `find_anchor_by_name()`, Qt import guard pattern
- `/workspace/constants.py` — `ANCHOR_DEFAULT_COLOR = 0x6f3399ff`, `KNOB_NAME`, `ANCHOR_PREFIX`
- `/workspace/.planning/phases/12-nuke-t-validation-scripts/12-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- `/workspace/.planning/STATE.md` — MEDIUM confidence flag on `nuke.root().name()` in headless; `nuke -t` invocation pattern `nuke -t script.py`
- `/workspace/REQUIREMENTS.md` — confirms TEST-01/TEST-02 scope; `nuke -t in CI` explicitly Out of Scope

### Tertiary (LOW confidence)
- General Nuke developer knowledge (training data): `nuke -t` runs Nuke in terminal/headless mode without a display; Nuke's Python environment includes both `nuke` and `nukescripts` natively; `nuke.toNode("preferences")` typically returns a real node in headless

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external packages needed; stdlib only
- Architecture: HIGH — all code paths readable in full; no guesswork
- Pitfalls: HIGH for code-derived pitfalls (toNode("preferences"), Qt import, root().name()), MEDIUM for headless Nuke runtime behavior (per STATE.md flag)
- Correction policy: HIGH — fully specified in CONTEXT.md

**Research date:** 2026-03-14
**Valid until:** 2026-06-14 (stable domain; Nuke API does not change frequently)
