---
phase: 18-group-context-support
plan: "03"
subsystem: core
tags: [group-context, nuke-api, anchor, link-creation, tabtabtab]

requires:
  - phase: 18-02
    provides: Group-context call sites updated in anchor.py, all_nodes_in_context() helper

provides:
  - Pre-captured lastHitGroup() context flows from anchor_shortcut() through to AnchorPlugin.invoke()/create_from_anchor()
  - AnchorPlugin._hit_group is set before TabTabTabWidget.show() calls get_items()
  - AnchorNavigatePlugin._hit_group is set before TabTabTabWidget.show() calls get_items()
  - Link node created inside Group's nested DAG when A-key pressed inside navigated Group

affects: [anchor.py, UAT-test-2-link-creation-in-group]

tech-stack:
  added: []
  patterns:
    - "Pre-capture pattern: capture lastHitGroup() once at entry point, pass down call chain, set on plugin before show()"
    - "Plugin._hit_group read-not-write in get_items(): set externally before show(), never overwritten inside get_items()"

key-files:
  created: []
  modified: [anchor.py]

key-decisions:
  - "Capture lastHitGroup() once at anchor_shortcut() top as hit_group before any with-block — prevents context drift when Qt event loop runs between callback and get_items()"
  - "select_anchor_and_create(hit_group=None) accepts hit_group param with fallback — allows direct calls to still work without context"
  - "plugin._hit_group = hit_group set before TabTabTabWidget construction and before show() — covers both __init__ and cached-widget show() paths"
  - "AnchorNavigatePlugin.get_items() fixed with same pattern as AnchorPlugin — select_anchor_and_navigate() pre-sets hit_group on plugin"
  - "get_items() falls back to nuke.root() if _hit_group is None — safety net for direct instantiation in tests"

patterns-established:
  - "Pre-capture pattern for group context: capture at entry point, pass explicitly, set on plugin before widget show"

requirements-completed: [GROUP-02]

duration: 6min
completed: "2026-03-20"
---

# Phase 18 Plan 03: Fix A-key Link Creation Inside Group Nodes Summary

**Pre-captured lastHitGroup() context flows from anchor_shortcut() through plugin._hit_group to create_from_anchor(), so pressing A inside a navigated Group creates the Link node inside the Group's DAG instead of at root level.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-20T09:34:00Z
- **Completed:** 2026-03-20T09:39:34Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Fixed the root cause of UAT Test 2 failure: AnchorPlugin.get_items() was overwriting _hit_group with the result of nuke.lastHitGroup() at a point when the Group context had already reset to root
- anchor_shortcut() now captures lastHitGroup() once as hit_group before any with-block and passes it to select_anchor_and_create(hit_group)
- select_anchor_and_create() sets plugin._hit_group = hit_group before TabTabTabWidget is constructed (covering the __init__ call to get_items()) and before show() is called (covering the cached-widget path)
- AnchorPlugin.get_items() reads self._hit_group (set externally) instead of overwriting it, with nuke.root() fallback
- Applied the same fix pattern symmetrically to AnchorNavigatePlugin and select_anchor_and_navigate() for consistency and to satisfy the verification grep

## Task Commits

Each task was committed atomically:

1. **Task 1: Capture lastHitGroup() once at anchor_shortcut() top and pass to AnchorPlugin** - `626add2` (feat)

## Files Created/Modified

- `/workspace/anchor.py` - anchor_shortcut(), select_anchor_and_create(), AnchorPlugin.get_items(), AnchorNavigatePlugin.get_items(), select_anchor_and_navigate() all updated

## Decisions Made

- Used `hit_group = nuke.lastHitGroup()` (local variable, not `self._hit_group`) at entry point to keep capture explicit and traceable through the call chain
- `select_anchor_and_create(hit_group=None)` defaults to None so existing call sites without arguments (direct calls) still work via the fallback `hit_group = nuke.lastHitGroup()`
- Extended fix to AnchorNavigatePlugin even though UAT Test 2 is specifically about AnchorPlugin — the plan's verification grep required no matches of `self._hit_group = nuke.lastHitGroup` anywhere in anchor.py, and the bug pattern was identical

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Applied pre-capture fix to AnchorNavigatePlugin and select_anchor_and_navigate()**
- **Found during:** Task 1 (verification step)
- **Issue:** The plan's verification grep `grep -n 'self._hit_group = nuke.lastHitGroup' anchor.py | grep -v '#'` requires zero matches. AnchorNavigatePlugin.get_items() had the identical bug pattern (self._hit_group = nuke.lastHitGroup() inside get_items()). The plan's scope was AnchorPlugin, but the verification check is file-wide.
- **Fix:** Applied the same three-part fix to AnchorNavigatePlugin.get_items() (reads _hit_group instead of writing it) and select_anchor_and_navigate() (captures hit_group at top, sets plugin._hit_group before show()).
- **Files modified:** anchor.py
- **Verification:** grep confirms zero remaining direct self._hit_group = nuke.lastHitGroup() assignments in the file.
- **Committed in:** 626add2 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical, same pattern applied to navigation plugin)
**Impact on plan:** Extension was required for the verification check to pass and also happens to fix the Alt+A navigation context issue consistently. No unrelated scope added.

## Issues Encountered

- The test suite has 17 pre-existing failures unrelated to this plan (test infrastructure issue where AnchorPlugin() and AnchorNavigatePlugin() instantiation fails when the test reloads the anchor module — the `self._hit_group = None` in `__init__` triggers a MagicMock AttributeError). Confirmed pre-existing: same 17 failures before and after our changes, 182 tests pass throughout.
- ruff check shows 4 pre-existing violations (C901 complexity, E501 line length, 2x SIM117 nested with). None introduced by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UAT Test 2 (A-key link creation inside navigated Group) should now pass — Link node will be created inside the Group's DAG
- UAT Test 5 (Alt+A inside navigated Group) also benefits from AnchorNavigatePlugin fix
- Ready for UAT re-run to verify both gaps are closed

---
*Phase: 18-group-context-support*
*Completed: 2026-03-20*
