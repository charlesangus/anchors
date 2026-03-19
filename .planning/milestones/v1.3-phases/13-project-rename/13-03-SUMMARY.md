---
phase: 13-project-rename
plan: 03
subsystem: testing
tags: [pytest, unittest, prefs, migration, rename]

# Dependency graph
requires:
  - phase: 13-project-rename plan 01
    provides: anchors.py module (renamed from paste_hidden.py), constants.py updated
  - phase: 13-project-rename plan 02
    provides: test suite updated to anchors.* paths
provides:
  - All Python source files free of paste_hidden references
  - constants.OLD_PREFS_PATH patchable path for test isolation
  - test_file_created_on_first_run_with_old_palette passing
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migration paths (OLD_PREFS_PATH) belong in constants.py so tests can patch them before module reimport"

key-files:
  created: []
  modified:
    - tests/test_prefs.py
    - constants.py
    - prefs.py
    - colors.py
    - link.py
    - validation/validate_cross_script_paste.py

key-decisions:
  - "Moved OLD_PREFS_PATH from prefs.py into constants.py — plan proposed patching prefs.OLD_PREFS_PATH after import but _load() runs at import time, so the patch must be in effect before reimport via constants"

patterns-established:
  - "All patchable file paths used by prefs.py live in constants.py (PREFS_PATH, USER_PALETTE_PATH, OLD_PREFS_PATH)"

requirements-completed: [REN-01]

# Metrics
duration: 12min
completed: 2026-03-15
---

# Phase 13 Plan 03: Gap Closure Summary

**Full rename completion: prefs migration path moved to constants for test isolation, all paste_hidden references purged from colors.py, link.py, and validate_cross_script_paste.py**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-15T20:40:00Z
- **Completed:** 2026-03-15T20:52:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Fixed `test_file_created_on_first_run_with_old_palette` — was failing because `~/.nuke/paste_hidden_prefs.json` exists in the dev environment; test now correctly isolates the migration path
- Moved `OLD_PREFS_PATH` from `prefs.py` to `constants.py` so it follows the same patchable pattern as `PREFS_PATH` and `USER_PALETTE_PATH`
- Removed all 8 `paste_hidden` references from `validation/validate_cross_script_paste.py` (import, 3 docstrings, 2 comments, call site, f-string, run_check label)
- Updated `colors.py` QCheckBox label and `link.py` module docstring

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix test_file_created_on_first_run_with_old_palette** - `7c9f198` (fix)
2. **Task 2: Rename stale paste_hidden references** - `e30f3a6` (fix)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `constants.py` - Added `OLD_PREFS_PATH = os.path.expanduser('~/.nuke/paste_hidden_prefs.json')`
- `prefs.py` - Imports `OLD_PREFS_PATH` from `constants` (removed local definition)
- `tests/test_prefs.py` - Saves/restores `constants.OLD_PREFS_PATH`, patches to nonexistent temp path before prefs reimport
- `colors.py` - QCheckBox label: "Enable paste_hidden plugin" -> "Enable anchors plugin"
- `link.py` - Docstring: `paste_hidden.py` -> `anchors.py`
- `validation/validate_cross_script_paste.py` - Fixed broken import + 7 string/comment references

## Decisions Made
- `OLD_PREFS_PATH` moved to `constants.py` rather than the plan's approach of patching `prefs.OLD_PREFS_PATH` after import. The plan's approach cannot work because `_load()` runs at module import time — the patch must be in effect before the reimport. Moving it to `constants.py` follows the established pattern for `PREFS_PATH` and `USER_PALETTE_PATH`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's patch-after-import approach could not work; moved OLD_PREFS_PATH to constants.py**
- **Found during:** Task 1 (Fix failing test)
- **Issue:** The plan specified patching `prefs.OLD_PREFS_PATH` after `import prefs`, but `prefs._load()` is called at import time (line 109 of prefs.py). By the time the patch is applied, the migration has already run and the wrong prefs file has been copied to `temp_prefs_path`. The test was failing because `~/.nuke/paste_hidden_prefs.json` exists in the dev environment with `custom_colors: []`, not the expected `[0x6f3399ff, 0xff0000ff]`.
- **Fix:** Added `OLD_PREFS_PATH` to `constants.py`; updated `prefs.py` to import it from there; updated the test to patch `constants.OLD_PREFS_PATH` before the `del sys.modules['prefs']` / `import prefs` sequence, matching the existing pattern for `PREFS_PATH` and `USER_PALETTE_PATH`.
- **Files modified:** `constants.py`, `prefs.py`, `tests/test_prefs.py`
- **Verification:** `python3 -m unittest tests.test_prefs` passes (3 tests, 0 failures)
- **Committed in:** `7c9f198` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan's approach)
**Impact on plan:** Required fix to make the test strategy work. Outcome is identical to plan intent — test isolation achieved. Old prefs path now follows the same constants.py pattern as the other two prefs paths.

## Issues Encountered
- No network access for `pip install pytest`; used `python3 -m unittest discover` from Nuke's Python 3.11 installation at `/usr/local/Nuke16.0v6/python3.11` as equivalent runner. The 66 pre-existing errors from `test_dot_type_distinction.py` (using `nuke.StubKnob` unavailable under unittest) were present before and after our changes — not introduced by this plan.

## Next Phase Readiness
- Phase 13 gap closure complete: all paste_hidden references removed from Python source files
- Test suite: 132 tests, 0 failures (66 pre-existing errors in test_dot_type_distinction.py unrelated to rename)
- Ready for Phase 14

---
*Phase: 13-project-rename*
*Completed: 2026-03-15*
