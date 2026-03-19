---
phase: 15-anchor-naming
plan: 01
subsystem: testing
tags: [tdd, unittest, anchor-naming, prefs, regex, wave-0]

# Dependency graph
requires:
  - phase: 14-bug-fixes
    provides: stable anchor.py and prefs.py as a base to extend

provides:
  - Wave 0 test scaffold defining behavioral contract for suggest_anchor_name() naming-regex path
  - Failing RED tests for naming_regex / naming_template in prefs round-trip persistence

affects: [15-02, 15-03, 16-site-config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold: test classes written before implementation exists; tests must fail RED, not ERROR"
    - "Wave-0 pattern: all naming tests in test_anchor_naming.py patch anchor.find_smallest_containing_backdrop to None so backdrop logic never fires in unit tests"
    - "prefs round-trip pattern: patch constants.PREFS_PATH to temp file, delete sys.modules['prefs'], re-import, assert values"

key-files:
  created:
    - tests/test_anchor_naming.py
  modified:
    - tests/test_prefs.py

key-decisions:
  - "Frame token stripping tests verify end-to-end behavior of suggest_anchor_name(), not just the strip helper — StubNode file knob set to raw path with token, assertion on final return value"
  - "TestRegexNoMatchFallback tests (test_user_regex_no_match, test_invalid_regex) pass GREEN even before Plan 02 because current hardcoded path happens to produce the right answer — this is acceptable; those tests still correctly define the contract"
  - "test_anchor_color_system has a pre-existing import error (nuke stub not installed before import); out-of-scope per deviation rules, deferred to deferred-items.md"

patterns-established:
  - "Wave 0 TDD: all test classes for a new feature shipped before any implementation; 9/13 naming tests fail RED"
  - "Prefs round-trip test helper _reload_prefs_with_temp_path() patches all three constants paths to avoid touching production paths"

requirements-completed: [NAME-01, NAME-02, NAME-03]

# Metrics
duration: 3min
completed: 2026-03-16
---

# Phase 15 Plan 01: Anchor Naming Test Scaffold Summary

**Wave 0 TDD scaffold: 13 unit tests across 6 classes define the behavioral contract for suggest_anchor_name() user-regex, frame-token stripping, template substitution, and fallback paths; 4 naming round-trip tests define the prefs persistence contract.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-16T13:32:50Z
- **Completed:** 2026-03-16T13:35:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `tests/test_anchor_naming.py` with 6 test classes and 13 test methods covering every named behavior in the plan
- Extended `tests/test_prefs.py` with `TestNamingPrefsRoundTrip` (4 tests) for naming field persistence
- All existing tests continue to pass; only new naming-contract tests fail RED

## Task Commits

1. **Task 1: Create tests/test_anchor_naming.py** - `6ef7569` (test)
2. **Task 2: Extend tests/test_prefs.py with naming round-trip tests** - `a054f09` (test)

## Files Created/Modified

- `tests/test_anchor_naming.py` - Wave 0 test scaffold; 6 classes × 13 tests for suggest_anchor_name() naming contract
- `tests/test_prefs.py` - Added TestNamingPrefsRoundTrip with 4 prefs persistence tests

## Decisions Made

- Frame token stripping tests are end-to-end (full suggest_anchor_name() call), not unit tests of a strip helper. This is intentional: if the implementation moves the strip helper, tests still verify the outer contract.
- TestRegexNoMatchFallback tests pass GREEN before Plan 02 because the current hardcoded path coincidentally produces the correct fallback result. This is correct behavior — those tests define the *contract*, and the contract is already partially met.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `pytest` not installed in this environment; used `python3 -m unittest discover` instead. Test collection and RED/GREEN status confirmed via unittest output. All 13 anchor naming tests collected; 9 fail RED. All 7 prefs tests collected; 4 new naming tests fail RED.

## Deferred Items

- `tests/test_anchor_color_system.py` has a pre-existing `ModuleNotFoundError: No module named 'nuke'` on import (nuke stub not installed before that file's module-level import). This pre-dates Phase 15 and is out-of-scope. Logged to deferred-items.md.

## Next Phase Readiness

- Wave 0 scaffold complete; Plan 02 can now implement `naming_regex` / `naming_template` in `prefs.py` and extend `suggest_anchor_name()` in `anchor.py`
- Plan 03 can add the prefs dialog UI; Plan 04 can add site-config locking

---
*Phase: 15-anchor-naming*
*Completed: 2026-03-16*
