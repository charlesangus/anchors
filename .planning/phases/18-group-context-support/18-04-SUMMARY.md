---
phase: 18-group-context-support
plan: 04
subsystem: ui
tags: [nuke, qtimer, deferred-execution, group-context, dag-navigation, pyside2, pyside6]

# Dependency graph
requires:
  - phase: 18-group-context-support
    plan: 03
    provides: "Pre-capture lastHitGroup() pattern applied to AnchorNavigatePlugin.get_items() and select_anchor_and_navigate()"
provides:
  - "AnchorNavigatePlugin.invoke() defers navigation via QTimer.singleShot(0, ...) so zoom fires after picker closes and Qt restores DAG panel focus"
  - "Alt+A anchor navigation correctly targets the Group's DAG panel (not root DAG) when invoked inside a Group node"
affects: [UAT, Group Context Support, Alt+A navigation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QTimer.singleShot(0, closure) for deferring operations that depend on Qt focus returning after widget close"
    - "Pre-captured group context (hit_group local) closed over in deferred callback to avoid stale lastHitGroup()"

key-files:
  created: []
  modified:
    - anchor.py

key-decisions:
  - "QTimer.singleShot(0, _deferred_navigate) defers nuke.zoom() until after picker widget closes and Qt restores DAG panel focus — eliminates the zoom-wrong-panel bug inside Group nodes"
  - "hit_group captured from self._hit_group (pre-set by select_anchor_and_navigate) and closed over in the deferred callback — avoids any further lastHitGroup() calls that would return stale root context"

patterns-established:
  - "Deferred Qt callback pattern: wrap operations that need correct Qt focus in QTimer.singleShot(0, closure) when invoked from within a widget that has focus"

requirements-completed: [GROUP-04]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 18 Plan 04: Deferred Navigation via QTimer Summary

**AnchorNavigatePlugin.invoke() now defers nuke.zoom() via QTimer.singleShot(0, ...) so Group DAG panel focus is restored before navigation fires**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-20T09:42:00Z
- **Completed:** 2026-03-20T09:47:31Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Wrapped `navigate_to_anchor()` and `navigate_to_backdrop()` calls in a `_deferred_navigate` closure
- Closure captures `hit_group` from the pre-set `self._hit_group` value (set by `select_anchor_and_navigate()` before show)
- `QtCore.QTimer.singleShot(0, _deferred_navigate)` fires on the next event loop iteration — after `self.close()` in `TabTabTabWidget.create()` and Qt's focus restoration to the Group DAG panel
- Alt+A navigation inside Group nodes now pans/zooms the correct Group DAG panel, not the root DAG

## Task Commits

Each task was committed atomically:

1. **Task 1: Pre-capture group context for AnchorNavigatePlugin and defer zoom via QTimer** - `3922b4f` (fix)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `/workspace/anchor.py` - `AnchorNavigatePlugin.invoke()` now uses `QTimer.singleShot(0, _deferred_navigate)` for deferred navigation

## Decisions Made

- Used `self._hit_group or nuke.root()` as the fallback in `invoke()` — consistent with the same pattern already used in `get_items()`. This keeps the deferred closure safe even if somehow `_hit_group` was never set.
- No new imports required — `QtCore` was already imported at the top of anchor.py via the PySide2/PySide6 conditional block.

## Deviations from Plan

None — plan executed exactly as written. Per the context note, Parts A and B (select_anchor_and_navigate and get_items changes) were already applied by plan 18-03. Only Part C (invoke deferred navigation) remained and was applied here.

## Issues Encountered

Pre-existing ruff violations (C901, E501, SIM117) and pre-existing test failure in `test_anchor_color_system.py` were present before this change and not caused by it. Verified by git stash comparison.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GROUP-04 requirement satisfied: Alt+A inside a Group node pans/zooms the Group's DAG panel to the selected anchor
- Phase 18 all 4 plans complete — ready for UAT validation and phase transition
- Pre-existing ruff/test failures deferred (out of scope for this plan)

---
*Phase: 18-group-context-support*
*Completed: 2026-03-20*
