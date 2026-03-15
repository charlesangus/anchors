---
phase: 12-nuke-t-validation-scripts
plan: 01
subsystem: testing
tags: [nuke, validation, stubs, headless, nuke-t, smoke-test]

# Dependency graph
requires:
  - phase: 08-test-infrastructure-stabilization
    provides: centralized StubNode/StubKnob in tests/stubs.py — the authoritative list of assumptions to probe
  - phase: 09-cross-script-paste-bug-fixes
    provides: BUG-01 and BUG-02 fixes in link.py and paste_hidden.py that these scripts validate
provides:
  - validation/validate_stub_alignment.py — probes all StubNode/StubKnob methods and nuke module-level API surfaces against real Nuke under nuke -t
  - validation/validate_cross_script_paste.py — smoke-tests BUG-01 and BUG-02 fixed code paths via real nuke.createNode / nuke.nodePaste / nuke.delete
affects:
  - any future stub updates in tests/stubs.py (these scripts define the regression check)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - run_check() helper pattern: one PASS/FAIL line per check, collect-all-failures, Summary N/M, sys.exit(1)
    - sys.path bootstrap at script top: adds repo root before any production imports
    - nuke -t import guard: sys.exit(2) with clear error message when not running under nuke -t
    - finally-block node cleanup: every nuke.createNode() call paired with nuke.delete() in finally

key-files:
  created:
    - validation/validate_stub_alignment.py
    - validation/validate_cross_script_paste.py
  modified: []

key-decisions:
  - "Scripts are fully standalone — no __init__.py in validation/ directory; each is run independently via nuke -t"
  - "nuke.toNode('preferences') HIGH-RISK check included with explicit note: stub returns None but real Nuke always has a preferences node — a FAIL here means tests/stubs.py needs fixing"
  - "tile_color value comparison uses int() coercion (int(actual) == 0xff0000ff) to handle real Nuke returning float for color knobs"
  - "BUG-02 check uses nuke.root()['name'].setValue('destScript.nk') + KNOB_NAME = 'sourceScript.Anchor_TestAnchor' to create stem mismatch without switching scripts"
  - "validate_cross_script_paste.py imports prefs indirectly via paste_hidden (prefs.plugin_enabled defaults to True); no direct prefs import; no Qt imports"

patterns-established:
  - "Pattern: run_check(name, fn) — PASS/FAIL output, failure accumulation, continued execution on failure"
  - "Pattern: sys.path bootstrap before any production imports — validation scripts usable from any working directory"
  - "Pattern: Informational prints (INFO:) inside check functions before assertions — developer sees actual values even on pass"

requirements-completed: [TEST-01]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 12 Plan 01: Nuke -t Validation Scripts Summary

**Two standalone nuke -t validation scripts covering all StubNode/StubKnob method alignment probes and BUG-01/BUG-02 smoke tests via real nuke.createNode/nodePaste/delete in 22 checks across 8 check groups**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T17:29:10Z
- **Completed:** 2026-03-14T17:32:04Z
- **Tasks:** 2
- **Files created:** 2

## Accomplishments
- Created `validation/validate_stub_alignment.py` with 22 checks across 8 check groups probing every StubNode/StubKnob method and the highest-risk nuke module-level surfaces against real Nuke API
- Created `validation/validate_cross_script_paste.py` with BUG-01 and BUG-02 smoke tests using real nuke.createNode, nuke.nodeCopy/nodePaste via nukescripts.cut_paste_file(), and nuke.delete cleanup
- Both scripts use the run_check() helper pattern, sys.path bootstrap, sys.exit(2) nuke -t guard, and Summary: N/M exit structure
- 132 existing tests remain green (unittest discover); no source files modified

## Task Commits

Each task was committed atomically:

1. **Task 1: Create validation/validate_stub_alignment.py** - `f6f58e3` (feat)
2. **Task 2: Create validation/validate_cross_script_paste.py** - `45e7c3d` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `validation/validate_stub_alignment.py` — StubNode/StubKnob alignment probes against real Nuke API (22 checks, 8 groups, 506 lines)
- `validation/validate_cross_script_paste.py` — BUG-01 and BUG-02 smoke tests using real .nk write + nodePaste mechanism (221 lines)

## Decisions Made
- Scripts are fully standalone (no `validation/__init__.py`) — each run independently via `nuke -t`
- `nuke.toNode('preferences')` check marked HIGH-RISK with explicit note: the stub returns `None` unconditionally but real Nuke always has a preferences node; a FAIL here means `tests/stubs.py` needs updating
- `tile_color` value comparison uses `int()` coercion to tolerate real Nuke returning float for color knobs
- BUG-02 check seeds stem mismatch via `nuke.root()['name'].setValue('destScript.nk')` and stamps `KNOB_NAME = 'sourceScript.Anchor_TestAnchor'` — does not switch scripts
- `validate_cross_script_paste.py` imports `prefs` only indirectly through `paste_hidden` (which checks `prefs.plugin_enabled`); no direct prefs import; no Qt imports in either script

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 12 Plan 01 complete: both validation scripts exist with valid Python syntax and correct structure
- Scripts require a local licensed Nuke install to run (`nuke -t`) — manual developer verification only; not a CI gate
- Phase 12 is now complete (this was the only plan in the phase)
- Run `nuke -t /path/to/repo/validation/validate_stub_alignment.py` and `nuke -t /path/to/repo/validation/validate_cross_script_paste.py` against a local Nuke install to confirm stub alignment and BUG-01/BUG-02 fixes

---
*Phase: 12-nuke-t-validation-scripts*
*Completed: 2026-03-14*
