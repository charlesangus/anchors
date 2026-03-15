---
phase: 09-cross-script-paste-bug-fixes
plan: 02
subsystem: core
tags: [paste_hidden, bug-fix, tile-color, anchor, cross-script, unittest]

requires:
  - phase: 09-cross-script-paste-bug-fixes
    provides: TestBugRegressions class with two failing regression tests for BUG-01 and BUG-02

provides:
  - BUG-01 fixed in paste_hidden.py: cross-script Link Dot displays anchor's real tile_color (not hardcoded purple)
  - BUG-02 fixed in paste_hidden.py: anchor pasted cross-script stays as anchor (not replaced by link node)
  - Both TestBugRegressions tests green; full suite 132 tests, 0 failures, 0 errors

affects:
  - 10-qual-01 (code quality sweep — these fixes are now guarded by regression tests)

tech-stack:
  added: []
  patterns:
    - "Minimal targeted fix: remove single-line overwrite (BUG-01) or replace block with continue (BUG-02)"
    - "Update tests that were testing buggy behavior when the bug is fixed"

key-files:
  created: []
  modified:
    - paste_hidden.py
    - tests/test_cross_script_paste.py
    - tests/test_dot_type_distinction.py

key-decisions:
  - "BUG-01 fix: removed node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR) after setup_link_node() in cross-script Link Dot branch — setup_link_node() already applies the anchor's real color via find_node_color()"
  - "BUG-02 fix: replaced entire anchor-to-link replacement block (is_anchor, createNode, delete) with unconditional continue — anchor placeholder stays in place regardless of whether same-named anchor exists in destination"
  - "Updated test_cross_script_anchor_with_matching_anchor_stays_as_anchor_placeholder to assert createNode/delete NOT called (was testing old buggy replacement behavior)"
  - "Removed ANCHOR_DEFAULT_COLOR assertion from test_link_dot_pasted_cross_script test (was asserting old BUG-01 behavior)"

patterns-established:
  - "Pattern: when fixing bugs, update existing tests that were testing the buggy behavior to assert the new correct behavior"

requirements-completed: [BUG-01, BUG-02]

duration: 8min
completed: 2026-03-13
---

# Phase 9 Plan 02: Cross-Script Paste Bug Fixes Summary

**BUG-01 and BUG-02 fixed in paste_hidden.py with two targeted changes; both regression tests green, 132 tests pass with 0 failures**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-13T12:05:00Z
- **Completed:** 2026-03-13T12:13:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- BUG-01 fixed: removed `node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)` from `paste_hidden()` cross-script Link Dot branch; `setup_link_node()` already sets the anchor's real color and no longer gets overwritten
- BUG-02 fixed: replaced the anchor-to-link replacement block (`is_anchor`, createNode, setup_link_node, delete) with an unconditional `continue`; anchor pasted cross-script now stays as an anchor
- Updated two tests that were asserting the old buggy behaviors to assert the new correct behaviors
- Full suite: 132 tests, 0 failures, 0 errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Apply BUG-01 fix — remove ANCHOR_DEFAULT_COLOR overwrite in paste_hidden()** - `46a17fa` (fix)
2. **Task 2: Apply BUG-02 fix — remove anchor-to-link replacement block; full suite green** - `67e1b2b` (fix)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `paste_hidden.py` - BUG-01: removed ANCHOR_DEFAULT_COLOR overwrite line; BUG-02: replaced anchor replacement block with `continue`
- `tests/test_cross_script_paste.py` - Renamed and updated test that was testing old buggy BUG-02 behavior (was asserting createNode/delete called; now asserts they are NOT called)
- `tests/test_dot_type_distinction.py` - Removed ANCHOR_DEFAULT_COLOR assertion from Link Dot cross-script test (was asserting old BUG-01 behavior)

## Decisions Made

- BUG-01: removed `node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)` after `setup_link_node()` in the cross-script Link Dot branch. The copy_hidden() override at line 79 is intentional (sets canonical purple at copy-time) and was left untouched.
- BUG-02: replaced entire `if is_anchor(node) and node.Class() != 'Dot':` block with an unconditional `continue`. Investigated `is_link()` being True for the pasted anchor (it has KNOB_NAME from copy): the paste_hidden() code checks `is_anchor(node)` (line 147) before any is_link() call, so the pasted anchor enters Path A/C correctly and is not misclassified. No downstream issue; KNOB_NAME cleanup deferred to QUAL-01 per plan.
- Updated existing tests that were testing old buggy behaviors to now assert correct behaviors (Rule 1 auto-fix — tests were broken by the bug fix and needed correction).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test asserting old BUG-02 behavior to assert new correct behavior**
- **Found during:** Task 2 (BUG-02 fix)
- **Issue:** `test_cross_script_reconnect_with_matching_anchor_creates_link_and_deletes_placeholder` was asserting createNode and delete were called for cross-script anchor paste — that was the buggy behavior. After BUG-02 fix the test failed.
- **Fix:** Renamed test to `test_cross_script_anchor_with_matching_anchor_stays_as_anchor_placeholder`; updated docstring and assertions to assert createNode/delete are NOT called.
- **Files modified:** tests/test_cross_script_paste.py
- **Verification:** Full suite passes 132 tests, 0 failures
- **Committed in:** 67e1b2b (Task 2 commit)

**2. [Rule 1 - Bug] Removed ANCHOR_DEFAULT_COLOR assertion from Link Dot cross-script test**
- **Found during:** Task 2 (full suite run)
- **Issue:** `test_link_dot_pasted_cross_script_with_matching_anchor_calls_setup_link_node` in `test_dot_type_distinction.py` asserted `tile_color == ANCHOR_DEFAULT_COLOR` — that was the old BUG-01 behavior. After BUG-01 fix the test failed.
- **Fix:** Removed the `assertEqual(tile_color, ANCHOR_DEFAULT_COLOR)` assertion and updated the docstring to reflect correct behavior.
- **Files modified:** tests/test_dot_type_distinction.py
- **Verification:** Full suite passes 132 tests, 0 failures
- **Committed in:** 67e1b2b (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both auto-fixes were necessary to keep the full test suite green after applying the bug fixes. No scope creep — the tests were corrected to assert the intended behavior, not the buggy behavior.

## Issues Encountered

- Two existing tests in `TestCrossScriptReconnect` and `TestPasteHiddenCrossScriptDotTypeBehavior` were asserting the old buggy behaviors (BUG-01 and BUG-02 respectively). These needed updating after the fixes. The plan did not mention this, but it was a straightforward Rule 1 correction.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BUG-01 and BUG-02 are fixed and guarded by two green regression tests in `TestBugRegressions`
- Full suite: 132 tests, 0 failures, 0 errors — ready for Phase 10 (QUAL-01 code quality sweep)
- Phase 10 can safely sweep paste_hidden.py knowing the regression tests will catch any accidental reversion

---
*Phase: 09-cross-script-paste-bug-fixes*
*Completed: 2026-03-13*
