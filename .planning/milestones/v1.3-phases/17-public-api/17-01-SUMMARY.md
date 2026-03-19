---
phase: 17-public-api
plan: 01
subsystem: testing
tags: [tdd, api, unittest, mock, nuke]

# Dependency graph
requires: []
provides:
  - RED phase test suite for api.py public surface (tests/test_api.py)
  - Contract tests for create_anchor() parameter pass-through
  - Contract tests for find_anchor_by_name() delegation
  - Contract tests for RuntimeError guard when nuke is absent
affects:
  - 17-02 (implements api.py against these tests)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED phase: test file written before implementation exists, fails with ModuleNotFoundError"
    - "sys.modules guard for stub installation (if 'nuke' not in sys.modules)"
    - "unittest.mock.patch used to mock anchor internals without calling real implementation"
    - "nuke-absent tests: del sys.modules['nuke'] in test body, restore in tearDown"

key-files:
  created:
    - tests/test_api.py
  modified: []

key-decisions:
  - "Tests mock anchor.create_anchor_named and anchor.find_anchor_by_name — real anchor.py implementation is never called in this test suite"
  - "nuke-absent RuntimeError tests delete sys.modules['nuke'] temporarily in each test body; setUp/tearDown restore the original module"
  - "find_anchor_by_name is exposed as a public helper in api.py (confirmed by plan interfaces)"

patterns-established:
  - "TDD RED: import the not-yet-existing module at module level so pytest fails at collection time with ModuleNotFoundError, confirming correct test targeting"

requirements-completed:
  - API-01
  - API-02
  - API-03

# Metrics
duration: 1min
completed: 2026-03-18
---

# Phase 17 Plan 01: Public API RED Phase Summary

**Failing test suite for api.py covering create_anchor() and find_anchor_by_name() with parameter pass-through, ValueError/RuntimeError guards, and nuke-absent detection**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-18T13:18:05Z
- **Completed:** 2026-03-18T13:18:52Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/test_api.py with 10 test methods across 3 test classes
- Tests correctly fail with `ModuleNotFoundError: No module named 'api'` (not a syntax error)
- All behavioral contracts for the public api.py surface are precisely defined in test form

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing test suite (RED phase)** - `7fb0714` (test)

## Files Created/Modified

- `/workspace/tests/test_api.py` - RED phase test suite: TestCreateAnchor, TestCreateAnchorErrorHandling, TestFindAnchorByName

## Decisions Made

- Mocked anchor internals rather than calling them: keeps tests focused on api.py's delegation behavior, not anchor.py's implementation details
- Used `del sys.modules['nuke']` pattern (consistent with what was already established) to simulate missing nuke session for RuntimeError guard tests
- Installed nuke stub with `if 'nuke' not in sys.modules` guard so module-level import in api.py will succeed once api.py exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- tests/test_api.py is ready for Plan 02 to implement api.py against
- All test class names (TestCreateAnchor, TestCreateAnchorErrorHandling, TestFindAnchorByName) match the plan's must_haves.artifacts.exports exactly
- 10 test methods (exceeds the minimum 8 required by success criteria)

---
*Phase: 17-public-api*
*Completed: 2026-03-18*
