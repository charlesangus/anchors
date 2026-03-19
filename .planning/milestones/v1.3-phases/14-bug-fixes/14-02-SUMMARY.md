---
phase: 14-bug-fixes
plan: 02
subsystem: testing
tags: [anchor, tdd, bug-fix, anchor_shortcut, dot-node]

requires:
  - phase: 14-bug-fixes-01
    provides: Phase 14 context established

provides:
  - anchor_shortcut() with Dot elif branch removed — Dot nodes use create_anchor() via NoOp path
  - _offer_make_dot_anchor() marked deprecated with comment, retained for reference
  - TestAnchorShortcutDotRouting class with five regression tests covering all dispatch paths

affects: []

tech-stack:
  added: []
  patterns:
    - "TDD: RED/GREEN pattern with unittest — write failing tests first, then fix production code"

key-files:
  created: []
  modified:
    - anchor.py
    - tests/test_dot_type_distinction.py

key-decisions:
  - "BUG-04 fix: remove Dot elif branch from anchor_shortcut() so Dot nodes fall through to elif selected: → create_anchor() — consistent NoOp-based anchor creation for all node types"
  - "_offer_make_dot_anchor() retained with deprecation comment, not deleted — preserved for reference per locked Phase 14 decision"

patterns-established:
  - "Regression tests for anchor_shortcut() dispatch paths live in TestAnchorShortcutDotRouting in test_dot_type_distinction.py"

requirements-completed: [BUG-04]

duration: 3min
completed: 2026-03-16
---

# Phase 14 Plan 02: Fix BUG-04 Anchor Shortcut Dot Routing Summary

**Removed Dot-intercept elif branch from anchor_shortcut() so pressing 'a' on a Dot node calls create_anchor() (NoOp path) instead of _offer_make_dot_anchor() (Dot-class anchor path)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-16T11:12:08Z
- **Completed:** 2026-03-16T11:15:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `TestAnchorShortcutDotRouting` class with five regression tests covering all `anchor_shortcut()` dispatch paths (Dot-selected, non-Dot selected, anchor selected, no selection, multiple nodes selected)
- Confirmed RED: `test_dot_selected_calls_create_anchor_not_offer_make_dot_anchor` failed because the Dot elif branch still existed
- Removed the two-line Dot elif branch from `anchor_shortcut()` and added deprecation comment to `_offer_make_dot_anchor()`
- All 5 new tests pass (GREEN); full 139-test suite passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add regression tests for BUG-04 (RED)** - `0f05b24` (test)
2. **Task 2: Fix BUG-04 in anchor.py (GREEN)** - `5c3f190` (fix)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks have two commits — test (RED) then fix (GREEN)_

## Files Created/Modified

- `anchor.py` — Removed Dot elif branch from `anchor_shortcut()`; added deprecation comment to `_offer_make_dot_anchor()`
- `tests/test_dot_type_distinction.py` — Added `_ensure_qt_stubs_support_mock_attributes()` helper and `TestAnchorShortcutDotRouting` class (5 tests)

## Decisions Made

- `_offer_make_dot_anchor()` is retained with a deprecation comment — not deleted. This matches the locked Phase 14 decision that deprecated functions are marked but kept for reference.
- Added `_ensure_qt_stubs_support_mock_attributes()` helper to `test_dot_type_distinction.py` since the new test class reloads `anchor` (which needs Qt stubs as MagicMock, not plain ModuleType) — consistent with the pattern established in `test_anchor_color_system.py` and `test_anchor_navigation.py`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

pytest is not installed in this environment; tests were run with `python3.11 -m unittest` using the package-qualified import pattern (`tests.test_*`), which properly invokes `tests/__init__.py` to install stubs before test discovery.

## Next Phase Readiness

- BUG-04 is fixed and regression-tested
- Phase 14 Plan 02 complete; ready for next Phase 14 plan

## Self-Check: PASSED

All files present. Both task commits verified: 0f05b24 (RED), 5c3f190 (GREEN).

---
*Phase: 14-bug-fixes*
*Completed: 2026-03-16*
