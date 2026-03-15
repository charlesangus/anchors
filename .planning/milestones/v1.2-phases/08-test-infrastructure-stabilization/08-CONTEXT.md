# Phase 8: Test Infrastructure Stabilization - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `tests/conftest.py` (and `tests/stubs.py`) with authoritative shared stubs for Qt, tabtabtab, nuke, and nukescripts — so `pytest tests/` (flat discovery) runs with zero errors, and all test files pass in isolation. Remove per-file stub code from all affected test files.

</domain>

<decisions>
## Implementation Decisions

### Conftest stub mechanism
- Use module-level `sys.modules` manipulation at the top of `conftest.py` (not pytest session fixtures)
- Same pattern as existing per-file stubs — just moved to one authoritative location
- Runs before any test file is imported, guaranteeing consistent stub state

### Scope of conftest coverage
- `conftest.py` covers ALL stubs: Qt (PySide6 + sub-modules), tabtabtab, nuke, nukescripts
- Inconsistent nuke stubs across files are a bug, not a feature — centralize everything
- All 5 affected test files (test_anchor_color_system, test_anchor_navigation, test_cross_script_paste, test_dot_anchor_name_sync, test_dot_type_distinction) drop their per-file stub code entirely

### Stub file location
- `StubNode`, `StubKnob`, and the nuke stub assembly live in `tests/stubs.py` (new file)
- `conftest.py` imports from `stubs.py` and installs into `sys.modules`
- Test files can also import from `stubs.py` directly if needed (e.g., to construct nodes in tests)
- Separating stubs into their own module makes it possible to write tests for the stubs themselves ("test the test")

### Nuke stub richness
- `stubs.py` provides the full, richest nuke stub: `StubNode`, `StubKnob`, plus all nuke API surface currently used across test files (`nuke.allNodes()`, `nuke.root()`, `nuke.NUKE_VERSION_MAJOR`, etc.)
- This is the superset of what all 5 test files currently define independently

### Per-test customization
- Individual tests continue to use `unittest.mock.patch()` for per-test nuke behavior overrides (e.g., `nuke.allNodes()` returning a specific list)
- `stubs.py` stub state is not designed to be mutated directly between tests — patch() is the right tool

### Per-file stub cleanup
- Remove all per-file Qt/tabtabtab/nuke stub blocks from all affected test files completely (clean removal)
- Keeping them would defeat the purpose — they overwrite conftest stubs on import

### Claude's Discretion
- Exact `StubNode`/`StubKnob` API surface (synthesize the superset from all 5 current definitions)
- Whether `test_prefs.py` needs any changes (it has a minimal nuke stub but no Qt stubs — may already work once conftest runs first)
- Internal structure of `stubs.py` beyond the above constraints

</decisions>

<specifics>
## Specific Ideas

- "Test the test" is an explicit goal — `stubs.py` being a separate importable module enables writing a `test_stubs.py` in the future if needed
- `conftest.py` should be kept thin: import from `stubs.py`, install into `sys.modules`, done

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StubKnob` / `StubNode`: currently duplicated across 5 test files — synthesize superset into `stubs.py`
- `_make_stub_qt_module()`: helper pattern repeated in most test files — move to `stubs.py`
- `tests/__init__.py`: currently empty — no changes needed

### Established Patterns
- Per-file stubs use `sys.modules[name] = stub` at module level (top of file, before local imports)
- `conftest.py` must follow the same pattern (module-level, not fixture) to guarantee install-before-import ordering
- `unittest.TestCase` subclasses with `setUp()` for per-test nuke state — this pattern stays unchanged

### Integration Points
- `conftest.py` is picked up automatically by pytest — no pytest.ini or pyproject.toml changes needed
- `tests/stubs.py` is a plain Python module — test files import it with `from stubs import StubNode, StubKnob`
- Flat discovery target: `pytest tests/` (no args beyond directory)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-test-infrastructure-stabilization*
*Context gathered: 2026-03-12*
