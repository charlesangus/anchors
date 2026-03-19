---
phase: 13-project-rename
plan: 01
subsystem: rename
tags: [nuke-plugin, paste-hidden, anchors, refactoring]

# Dependency graph
requires: []
provides:
  - anchors.py module with copy_anchors, cut_anchors, paste_anchors, paste_multiple_anchors, migrate_script
  - constants.py with anchors_dot_anchor, anchors_dot_type knob names and anchors_prefs.json path
  - prefs.py with _migrate_from_old_prefs_file() for one-way migration from paste_hidden_prefs.json
  - menu.py importing anchors module and using anchors.* function names
  - anchor.py with anchors_anchor_weights.json weight file paths
affects: [14-tests-rename, 15-site-config, 17-public-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rename-then-migrate: frozen knob constants renamed in source but migrate_script() provides backward migration for existing .nk files"
    - "One-way file migration: new prefs path checked first, old path copied if new is absent"

key-files:
  created:
    - anchors.py
  modified:
    - constants.py
    - prefs.py
    - menu.py
    - anchor.py

key-decisions:
  - "USER_PALETTE_PATH in constants.py left as paste_hidden_user_palette.json — it is the legacy source read during old-palette migration, not a primary path"
  - "migrate_script() hardcodes old knob name strings as literals so it works both before and after the constants.py rename"
  - "DOT_ANCHOR_KNOB_NAME and DOT_TYPE_KNOB_NAME values changed to anchors_* — existing .nk files use migrate_script() to update"

patterns-established:
  - "Module-level migration pattern: check new path, copy old path if missing, fall through to load — established in prefs._load()"

requirements-completed: [REN-01]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 13 Plan 01: Source-Level Rename Summary

**paste_hidden.py renamed to anchors.py with all internal functions renamed, migrate_script() added for .nk file migration, and constants/prefs/menu/anchor updated throughout**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-15T19:59:28Z
- **Completed:** 2026-03-15T20:02:48Z
- **Tasks:** 2
- **Files modified:** 5 (1 renamed + 4 updated)

## Accomplishments

- paste_hidden.py git-renamed to anchors.py; copy_hidden/cut_hidden/paste_hidden/paste_multiple_hidden functions renamed to copy_anchors/cut_anchors/paste_anchors/paste_multiple_anchors
- migrate_script() added to anchors.py to rename FROZEN knobs (paste_hidden_dot_anchor/type → anchors_dot_anchor/type) in existing .nk files
- constants.py updated: DOT_ANCHOR_KNOB_NAME = 'anchors_dot_anchor', DOT_TYPE_KNOB_NAME = 'anchors_dot_type', PREFS_PATH = anchors_prefs.json
- prefs.py updated with _migrate_from_old_prefs_file() for one-way copy from paste_hidden_prefs.json on first load
- menu.py updated: import anchors, all command strings use anchors.copy_anchors / anchors.cut_anchors / anchors.paste_anchors / anchors.paste_multiple_anchors
- anchor.py updated: weight file paths use anchors_anchor_weights.json and anchors_anchor_navigate_weights.json

## Task Commits

1. **Task 1: Rename paste_hidden.py to anchors.py with internal function renames and migrate_script()** - `19a475d` (feat)
2. **Task 2: Update constants.py, prefs.py, menu.py, and anchor.py for new names** - `a50b1bf` (feat)

## Files Created/Modified

- `/workspace/anchors.py` - Renamed from paste_hidden.py; functions renamed; migrate_script() added
- `/workspace/constants.py` - Docstring updated; DOT_ANCHOR_KNOB_NAME, DOT_TYPE_KNOB_NAME, PREFS_PATH renamed to anchors_* values
- `/workspace/prefs.py` - Docstring updated; OLD_PREFS_PATH constant and _migrate_from_old_prefs_file() added; _load() updated to call prefs migration before palette migration
- `/workspace/menu.py` - import anchors; all paste_hidden.* command strings updated to anchors.*
- `/workspace/anchor.py` - Both get_weights_file() methods updated to anchors_anchor_weights.json / anchors_anchor_navigate_weights.json

## Decisions Made

- USER_PALETTE_PATH in constants.py left as paste_hidden_user_palette.json — it is the legacy source read during old-palette migration, not a primary path that requires renaming
- migrate_script() hardcodes old knob name strings as literals (not importing OLD_* constants) so it works correctly regardless of what DOT_ANCHOR_KNOB_NAME/DOT_TYPE_KNOB_NAME currently resolve to
- DOT_ANCHOR_KNOB_NAME and DOT_TYPE_KNOB_NAME values changed to anchors_* — existing .nk files that have paste_hidden_dot_* knobs require migrate_script() to update

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

pytest not available in execution environment — syntax verification performed via `ast.parse()` for all modified files. The plan notes tests will have failures until Plan 02 updates test patches; no test runner needed at this stage.

## Next Phase Readiness

- anchors.py module available at the new name; all callers updated
- Plan 02 (tests rename) can now update test patches from 'paste_hidden.*' to 'anchors.*'
- No blockers

---
*Phase: 13-project-rename*
*Completed: 2026-03-15*
