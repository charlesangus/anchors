---
phase: quick
plan: 260327-d2z
subsystem: paste
tags: [anchors, fqnn, cross-script, paste, tdd]

# Dependency graph
requires:
  - phase: 18-group-context-support
    provides: cross-script paste reconnect logic in anchors.py paste_anchors()
provides:
  - FQNN update on cross-script anchor paste (GitHub issue #5 fix)
  - Regression tests for FQNN update behavior
affects: [cross-script paste workflows, link dot reconnect after anchor paste]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD red-green for bug regressions, inline stem replacement using nuke.root().name()]

key-files:
  created: []
  modified:
    - anchors.py
    - tests/test_cross_script_paste.py

key-decisions:
  - "Use inline stem replacement (nuke.root().name().split('.')[0] + node.fullName()) rather than get_fully_qualified_node_name() — get_fully_qualified_node_name() reads link.nuke which is not patched in these tests; inline approach reads anchors.nuke which is correctly mocked"
  - "Guard FQNN rewrite with is_anchor(node) check to avoid rewriting FQNN on file nodes (LINK_SOURCE_CLASSES) in the cross-script branch — file nodes should not have their FQNN rewritten"
  - "Dot anchor test sets node._name to 'Group1.Anchor_CamMain' to simulate Nuke's fullName() for a Group-nested Dot, matching real Nuke behavior"

patterns-established: []

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-03-27
---

# Quick Task 260327-d2z: Fix Cross-Script Anchor FQNN Update (GitHub #5)

**Anchor FQNN rewritten to destination script stem on cross-script paste, fixing stale-stem mismatch that blocked Link Dot reconnection**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-03-27
- **Tasks:** 2 (TDD: RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- Added `TestCrossScriptFqnnUpdate` with 3 regression tests covering NoOp anchor, Group-nested Dot anchor, and auto-renamed node cases
- Fixed `paste_anchors()` Path A/C cross-script branch: after BUG-02 fix left anchor in place, FQNN is now rewritten to `{destStem}.{node.fullName()}` so the anchor reads as local in the destination script
- Zero regressions: 202 tests pass (199 pre-existing + 3 new)

## Task Commits

1. **Task 1: Add regression tests (RED)** - `f336793` (test)
2. **Task 2: Fix paste_anchors() + refine test (GREEN)** - `98de072` (fix)

## Files Created/Modified

- `/home/latuser/git/nuke_layout_project/paste_hidden/.claude/worktrees/agent-a8ec4350/anchors.py` - Added FQNN rewrite in paste_anchors() cross-script anchor branch
- `/home/latuser/git/nuke_layout_project/paste_hidden/.claude/worktrees/agent-a8ec4350/tests/test_cross_script_paste.py` - Added TestCrossScriptFqnnUpdate (3 tests)

## Decisions Made

- Used inline `nuke.root().name().split('.')[0]` + `node.fullName()` rather than `get_fully_qualified_node_name()` so the patched `anchors.nuke` is used in tests (link.nuke would bypass the mock)
- Guarded FQNN rewrite with `is_anchor(node)` so file nodes in the same Path A/C branch are not affected (file nodes pasted cross-script should remain as-is)
- Adjusted the Dot anchor test to set `node._name = 'Group1.Anchor_CamMain'` to accurately reflect the fullName() Nuke returns for a Group-nested node

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected Dot anchor test stub to match Nuke fullName() behavior**
- **Found during:** Task 2 (GREEN phase — test_dot_anchor_fqnn_updated_after_cross_script_paste was still failing)
- **Issue:** The stub node used `name='Dot1'` while the test expected `'Group1.Anchor_CamMain'` as the fullName portion. In real Nuke, `fullName()` for a Group-nested node includes the Group prefix; the stub must reflect this.
- **Fix:** Added `pasted_dot_anchor_node._name = 'Group1.Anchor_CamMain'` in the test and added a clarifying docstring.
- **Files modified:** tests/test_cross_script_paste.py
- **Verification:** All 3 new tests pass; 202 total pass
- **Committed in:** 98de072

---

**Total deviations:** 1 auto-fixed (Rule 1 - test stub accuracy)
**Impact on plan:** Minor test correctness fix. No scope creep.

## Issues Encountered

None — the fix path was clear from the plan. The one adjustment was in the test stub accuracy (documented above).

## Next Phase Readiness

GitHub issue #5 is resolved. The fix is minimal (5 lines in paste_anchors) and targeted. No follow-up work required.

---
*Quick task: 260327-d2z*
*Completed: 2026-03-27*
