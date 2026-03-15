---
phase: 10-code-quality-sweep
plan: 03
subsystem: code-quality
tags: [ruff, linting, e501, c901, frozen-constants, paste-hidden]

# Dependency graph
requires:
  - phase: 10-02
    provides: ruff zero-violation baseline on anchor.py, colors.py, labels.py, link.py, util.py
provides:
  - Zero ruff violations across all 10 workspace-root Python source files
  - FROZEN annotations on all 8 serialized knob name constants in constants.py
  - C901 noqa suppression on copy_hidden and paste_hidden with explanatory comments
affects: [11-zip-manifest, 12-nuke-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FROZEN annotation pattern: '# FROZEN: value stored in .nk files — do not rename' above serialized constants"
    - "C901 noqa suppression with explanatory rationale on the def line itself"

key-files:
  created: []
  modified:
    - paste_hidden.py
    - menu.py
    - constants.py

key-decisions:
  - "paste_hidden.copy_hidden and paste_hidden.paste_hidden C901 suppressed with noqa — structural refactoring deferred; BUG-01/BUG-02 fixes are recent and extraction would require passing selected_nodes as parameter"
  - "menu.py E501 fixed by removing alignment padding from two _add_gated_command lines (no functional change)"
  - "constants.py LOCAL_DOT_COLOR inline comment moved to preceding line to fix E501 — the only approach without altering the constant value"

patterns-established:
  - "FROZEN annotation: place comment on the line immediately above the constant, not inline"

requirements-completed: [QUAL-01]

# Metrics
duration: 2min
completed: 2026-03-13
---

# Phase 10 Plan 03: Code Quality Sweep — Final Files Summary

**Zero ruff violations across all 10 workspace-root source files; all 8 serialized knob name constants in constants.py annotated with FROZEN comments; C901 suppressed with rationale on paste_hidden.py def lines**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-13T12:58:10Z
- **Completed:** 2026-03-13T12:59:31Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- paste_hidden.py: 2 E501 violations fixed by moving over-long inline comments to preceding lines; 2 C901 violations suppressed with `# noqa: C901` and explanatory rationale on the def lines
- menu.py: 2 E501 violations fixed by removing alignment whitespace padding from `_add_gated_command` calls
- constants.py: 8 FROZEN annotations added above all serialized knob name constants; 1 E501 fixed by moving inline comment to preceding line
- Full test suite green: 132 tests, 0 errors, 0 failures (including BUG-01 and BUG-02 regression tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix paste_hidden.py E501 and C901; fix menu.py E501** - `b9c57d3` (fix)
2. **Task 2: Add FROZEN annotations to constants.py; fix constants.py E501** - `f77be3a` (feat)

## Files Created/Modified

- `/workspace/paste_hidden.py` - Added `# noqa: C901` to `def copy_hidden` and `def paste_hidden`; wrapped two over-long inline comments to fix E501
- `/workspace/menu.py` - Removed alignment padding from two `_add_gated_command` calls to fix E501
- `/workspace/constants.py` - Added FROZEN annotation above each of 8 serialized knob name constants; moved LOCAL_DOT_COLOR comment to preceding line to fix E501

## Final Ruff Violation Count

**0 violations** across all 10 workspace-root source files:
`anchor.py`, `colors.py`, `constants.py`, `labels.py`, `link.py`, `menu.py`, `paste_hidden.py`, `prefs.py`, `tabtabtab.py`, `util.py`

## FROZEN Constants Annotated

All 8 serialized knob name constants now carry `# FROZEN: value stored in .nk files — do not rename`:

1. `TAB_NAME = 'copy_hidden_tab'`
2. `KNOB_NAME = 'copy_hidden_input_node'`
3. `LINK_RECONNECT_KNOB_NAME = "reconnect_link"`
4. `ANCHOR_RECONNECT_KNOB_NAME = "reconnect_child_links"`
5. `ANCHOR_RENAME_KNOB_NAME = "rename_anchor"`
6. `DOT_ANCHOR_KNOB_NAME = 'paste_hidden_dot_anchor'`
7. `DOT_TYPE_KNOB_NAME = 'paste_hidden_dot_type'`
8. `ANCHOR_SET_COLOR_KNOB_NAME = "set_anchor_color"`

No constant values were renamed or altered. Only comment lines were added.

## C901 Suppression Decision

`copy_hidden` and `paste_hidden` both have cyclomatic complexity 14 (threshold 10). Suppressed with `# noqa: C901` on the def lines rather than structural refactoring because:
- BUG-01 and BUG-02 fixes are recent; `paste_hidden()` mutates `selected_nodes` in-place (`.remove()`, `.append()`) — extraction would require passing the list as a parameter
- The complexity is inherent (3 node-class paths × same/cross-script gate), not accidental

## Decisions Made

- C901 suppressed with noqa (not structural refactoring) — safety-first given recent BUG fixes
- menu.py E501 fixed by removing alignment padding, not by adding per-file-ignores — no per-file-ignores entry needed for E501
- constants.py E501 fixed by moving the LOCAL_DOT_COLOR comment to its own preceding line — value unchanged

## Deviations from Plan

None — plan executed exactly as written. prefs.py had zero violations (already clean from Plan 02), so no edits were needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 complete: zero ruff violations across all 10 source files, FROZEN annotations present, test suite green (132 tests)
- Ready for Phase 11 (ZIP manifest) and Phase 12 (nuke -t validation)
- No blockers

## Self-Check: PASSED

All files present. Both task commits verified: b9c57d3, f77be3a.

---
*Phase: 10-code-quality-sweep*
*Completed: 2026-03-13*
