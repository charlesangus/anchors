---
phase: 09-cross-script-paste-bug-fixes
plan: 01
subsystem: testing
tags: [unittest, regression-tests, cross-script, tile-color, anchor]

requires:
  - phase: 08-test-infrastructure-stabilization
    provides: centralized StubNode/StubKnob in tests/stubs.py; conftest.py+__init__.py stub installation; 130-test green baseline

provides:
  - TestBugRegressions class in tests/test_cross_script_paste.py with two failing regression tests
  - test_bug01_link_dot_cross_script_color — confirms BUG-01 (tile_color overwritten with purple) exists
  - test_bug02_anchor_stays_anchor_cross_script — confirms BUG-02 (anchor replaced by link on cross-script paste) exists

affects:
  - 09-02 (BUG-01 and BUG-02 fixes — these tests will turn green after fix)

tech-stack:
  added: []
  patterns:
    - "Patch link.find_node_color (not paste_hidden.find_node_color) for BUG-01 — find_node_color lives in link.py"
    - "Patch paste_hidden.setup_link_node in BUG-02 test to avoid nuke.toNode preferences error while confirming createNode/delete behavior"
    - "Use side_effect on is_anchor patch to return True only for the specific pasted node, preventing misclassification of newly created nodes"

key-files:
  created: []
  modified:
    - tests/test_cross_script_paste.py

key-decisions:
  - "Patched link.find_node_color (not paste_hidden.find_node_color) — find_node_color is imported into link.py, not paste_hidden.py; patch must target the module that owns the name"
  - "Patched paste_hidden.setup_link_node in BUG-02 test — BUG-02 asserts createNode/delete not called; mocking setup_link_node avoids nuke.toNode(preferences) error from the buggy code path without hiding the createNode/delete calls under test"

patterns-established:
  - "Pattern: import paste_hidden.paste_hidden inside with patch() block (not at module top) to avoid module cache staleness"
  - "Pattern: patch link.find_node_color for color-related Link Dot tests; link.nuke for link.py's nuke calls"

requirements-completed: [BUG-01, BUG-02]

duration: 1min
completed: 2026-03-13
---

# Phase 9 Plan 01: Cross-Script Paste Bug Regression Tests Summary

**Two failing regression tests for BUG-01 (tile_color overwritten with purple) and BUG-02 (anchor replaced by link) added to TestBugRegressions class; 132 tests total, 2 failures, 0 errors**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-13T11:59:53Z
- **Completed:** 2026-03-13T12:01:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `TestBugRegressions` class to `tests/test_cross_script_paste.py` with two failing tests
- `test_bug01_link_dot_cross_script_color` fails with AssertionError: `0x6f3399ff` (purple) instead of `0xff0000ff` (anchor color) — confirms BUG-01 is live
- `test_bug02_anchor_stays_anchor_cross_script` fails with AssertionError: `createNode` was called when it should not have been — confirms BUG-02 is live
- All 130 pre-existing tests remain green (132 total, 2 failures, 0 errors)

## Task Commits

1. **Task 1: Write failing regression tests — TestBugRegressions class** - `1e35aad` (test)

## Files Created/Modified

- `tests/test_cross_script_paste.py` - Added TestBugRegressions class (145 lines inserted, no existing tests changed)

## Decisions Made

- Patched `link.find_node_color` (not `paste_hidden.find_node_color`) — `find_node_color` is defined in `link.py` and imported into `link.py`'s namespace; patch must target the module owning the name.
- Patched `paste_hidden.setup_link_node` in the BUG-02 test — the buggy path calls `setup_link_node` before `createNode`/`delete`; mocking it avoids a `nuke.toNode(preferences)` error while still allowing the `createNode`/`delete` mock assertions to trigger correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect patch target for find_node_color in BUG-01 test**
- **Found during:** Task 1 (TestBugRegressions implementation)
- **Issue:** Plan specified `patch('paste_hidden.find_node_color', ...)` but `find_node_color` is not imported into `paste_hidden`'s namespace — it lives in `link.py`
- **Fix:** Changed to `patch('link.find_node_color', return_value=anchor_color)`
- **Files modified:** tests/test_cross_script_paste.py
- **Verification:** AttributeError resolved; test now runs and fails with AssertionError as expected
- **Committed in:** 1e35aad (Task 1 commit)

**2. [Rule 1 - Bug] Added setup_link_node mock in BUG-02 test to prevent nuke.toNode error**
- **Found during:** Task 1 (TestBugRegressions implementation)
- **Issue:** BUG-02 buggy path calls `setup_link_node(destination_anchor, link_node)` before the `nuke.delete` call; `setup_link_node` internally calls `nuke.toNode("preferences")` which returns None, causing AttributeError
- **Fix:** Added `patch('paste_hidden.setup_link_node')` to the BUG-02 test patch stack; this doesn't hide the createNode/delete assertions since those are on the mock_nuke object directly
- **Files modified:** tests/test_cross_script_paste.py
- **Verification:** Test now runs and fails with AssertionError on createNode as expected
- **Committed in:** 1e35aad (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both auto-fixes corrected the test setup to match the actual codebase structure. No scope creep; the tests still exercise the exact buggy code paths as designed.

## Issues Encountered

- `paste_hidden.find_node_color` does not exist as an attribute on `paste_hidden` — `find_node_color` is defined in `link.py`. The plan's interface table was slightly misleading on patch location. Resolved by patching `link.find_node_color`.
- BUG-02 buggy code path calls `setup_link_node` before `nuke.delete`, which hits `nuke.toNode("preferences")` returning None. Resolved by mocking `paste_hidden.setup_link_node` in the BUG-02 test.

## Next Phase Readiness

- BUG-01 and BUG-02 regression tests are in place and confirmed failing
- Phase 9 Plan 02 can now apply the fixes and confirm both tests turn green
- The fix locations are already known from research: line 212 of paste_hidden.py (BUG-01) and lines 160-171 (BUG-02)

## Self-Check: PASSED

- `tests/test_cross_script_paste.py` — FOUND
- `09-01-SUMMARY.md` — FOUND
- Commit `1e35aad` — FOUND

---
*Phase: 09-cross-script-paste-bug-fixes*
*Completed: 2026-03-13*
