---
phase: 10-code-quality-sweep
plan: "01"
subsystem: code-quality
tags: [ruff, linting, import-sorting, pyproject]

requires:
  - phase: 09-cross-script-paste-bug-fixes
    provides: "passing 132-test suite that all code quality changes must keep green"

provides:
  - "pyproject.toml with ruff rule set (E,F,W,B,C90,I,SIM) at line-length=100"
  - "Zero I001 import sort violations across all 6 affected source files"
  - "Baseline violation count: 37 (down from 112) for Plans 02+ to resolve"

affects:
  - 10-02
  - 10-03
  - 10-04

tech-stack:
  added: [ruff 0.14.0 via pyproject.toml configuration]
  patterns:
    - "per-file-ignores in pyproject.toml for vendored (tabtabtab.py) and Nuke-callback (menu.py) files"
    - "ruff --fix --select I for zero-behavior-change import sort automation"

key-files:
  created:
    - pyproject.toml
  modified:
    - anchor.py
    - colors.py
    - labels.py
    - link.py
    - menu.py
    - paste_hidden.py

key-decisions:
  - "tabtabtab.py per-file-ignores: B008, C901, SIM, E501 all suppressed — vendored third-party code must not be modified"
  - "menu.py F401 suppressed via per-file-ignores — imports used in Nuke string-eval menu callbacks, ruff cannot see through string arguments"
  - "line-length=100 chosen over 88: reduces E501 from 78 to 21 violations in source files without touching any code"

requirements-completed: [QUAL-01]

duration: 1min
completed: 2026-03-13
---

# Phase 10 Plan 01: Code Quality Sweep Baseline Summary

**pyproject.toml with ruff rule set at line-length=100 established; import sort order (I001) auto-fixed across 6 source files; violation count drops from 112 to 37**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-13T12:09:39Z
- **Completed:** 2026-03-13T12:10:35Z
- **Tasks:** 2
- **Files modified:** 7 (1 created: pyproject.toml; 6 modified: source .py files)

## Accomplishments

- Created `/workspace/pyproject.toml` with ruff configuration: line-length=100, rule set E/F/W/B/C90/I/SIM, per-file-ignores for menu.py and tabtabtab.py
- Auto-fixed all 7 I001 import sort violations (2 in anchor.py, 1 each in colors.py/labels.py/link.py/menu.py/paste_hidden.py)
- Total source-file violations reduced from 112 (at line-length=88) to 37 (at line-length=100, after import sort fixes)
- tabtabtab.py: zero violations (all vendored-code rules suppressed via per-file-ignores)
- All 132 tests pass green after import reordering

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pyproject.toml with ruff configuration** - `960e105` (chore)
2. **Task 2: Auto-fix import sort order (I001) across source files** - `1235eea` (chore)

## Files Created/Modified

- `pyproject.toml` - ruff configuration: line-length=100, rule selection, per-file-ignores for menu.py (F401) and tabtabtab.py (B008/C901/SIM/E501)
- `anchor.py` - import block sorted (2 I001 violations resolved)
- `colors.py` - import block sorted (1 I001 violation resolved)
- `labels.py` - import block sorted (1 I001 violation resolved)
- `link.py` - import block sorted (1 I001 violation resolved)
- `menu.py` - import block sorted (1 I001 violation resolved)
- `paste_hidden.py` - import block sorted (1 I001 violation resolved)

## Violation Count Before/After

| Metric | Before (line-length=88) | After Plan 01 |
|--------|------------------------|---------------|
| Total source violations | 112 | 37 |
| E501 (line too long) | 78 | 21 |
| I001 (import sort) | 7 | 0 |
| tabtabtab.py violations | 16 | 0 |
| F401 (unused imports) | 5 | 5 (unchanged — addressed in later plans) |
| B007, C901, SIM* | remaining | remaining (addressed in later plans) |

## Decisions Made

- `tabtabtab.py` B008/C901/SIM/E501 all suppressed: vendored third-party code from github.com/dbr/tabtabtab-nuke must not be modified
- `menu.py` F401 suppressed via pyproject.toml per-file-ignores (not noqa comments): cleaner and applies project-wide; imports are used inside Nuke's string-eval menu callbacks which ruff cannot see through
- `line-length=100` chosen: reduces 57 of 78 E501 violations automatically without touching any source code

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Baseline established; Plans 02+ can address remaining 37 violations (E501, F401, B007, C901, SIM105, SIM108)
- Import sort is complete; no further I001 violations will appear in this sweep
- 132 tests remain green — regression guard intact for subsequent plans

---
*Phase: 10-code-quality-sweep*
*Completed: 2026-03-13*
