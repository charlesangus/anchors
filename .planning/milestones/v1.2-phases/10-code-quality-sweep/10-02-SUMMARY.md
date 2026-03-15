---
phase: 10-code-quality-sweep
plan: "02"
subsystem: source-quality
tags: [ruff, linting, code-quality, F401, SIM105, SIM108, B007, C901, E501]
dependency_graph:
  requires: [10-01]
  provides: [anchor.py-clean, link.py-clean, colors.py-clean, labels.py-clean]
  affects: [anchor.py, link.py, colors.py, labels.py]
tech_stack:
  added: []
  patterns: [contextlib.suppress, ternary-operators, underscore-loop-vars, noqa-C901]
key_files:
  created: []
  modified:
    - anchor.py
    - link.py
    - colors.py
decisions:
  - "anchor.py SIM108: two ternary collapses applied (suggest_anchor_name and pre_color assignment)"
  - "anchor.py F401: add_input_knob import removed — confirmed not used anywhere in file after removing from import list"
  - "colors.py C901: eventFilter and keyPressEvent suppressed with noqa: C901 — complexity is inherent to Qt event dispatch"
  - "colors.py B007: all 4 unused loop variables renamed with _ prefix — none captured in lambdas or inner functions"
  - "labels.py: already clean — no violations to fix (E501 was resolved in Plan 01)"
metrics:
  duration: "4 min"
  completed: "2026-03-13"
  tasks_completed: 2
  files_modified: 3
---

# Phase 10 Plan 02: Core File Ruff Violations Summary

Fix all ruff violations in anchor.py, link.py, colors.py, and labels.py — zero violations across all four files after removing unused imports, replacing try-except-pass with contextlib.suppress, collapsing if/else to ternary, and renaming unused loop variables.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix anchor.py and link.py violations (F401, SIM105, SIM108, E501) | 2fe8379 | anchor.py, link.py |
| 2 | Fix colors.py and labels.py violations (B007, C901, E501) | 8d0775b | colors.py |

## Violations Fixed Per File

### anchor.py

| Rule | Count | Fix Applied |
|------|-------|-------------|
| F401 | 1 | Removed `add_input_knob` import — confirmed unused in file |
| SIM105 | 3 | Replaced try-except-pass with `contextlib.suppress(ValueError)`; added `import contextlib` |
| SIM108 | 2 | Collapsed two if/else blocks to ternary (suggest_anchor_name result, pre_color assignment) |
| E501 | 1 | Wrapped long ternary in `rename_anchor()` across two lines |

Note: The plan estimated 1 SIM108 but ruff found 2. Both were collapsed cleanly — no logic change.

### link.py

| Rule | Count | Fix Applied |
|------|-------|-------------|
| F401 | 2 | Removed `nukescripts` and `HIDDEN_INPUT_CLASSES` imports — both confirmed unused |
| SIM105 | 3 | Replaced try-except-pass in `add_input_knob()` with `contextlib.suppress(Exception)`; added `import contextlib` |
| E501 | 4 | Reformatted `find_node_default_color` list comprehensions; wrapped long `is_anchor()` condition |

### colors.py

| Rule | Count | Fix Applied |
|------|-------|-------------|
| B007 | 4 | Renamed unused loop variables: `group_col`→`_group_col` (×2), `logical_row`→`_logical_row` (×2), `color_int`→`_color_int` (×1); verified none captured in lambdas/inner functions |
| C901 | 2 | Added `# noqa: C901  # complexity is inherent to Qt event dispatch logic` on `eventFilter`; `# noqa: C901  # complexity is inherent to Qt swatch rendering logic` on `keyPressEvent` |
| E501 | 8 | Wrapped docstrings, lambda connect call, cell tuple assignment, inline comments |

### labels.py

Already clean — no violations present after Plan 01's line-length=100 fix. No changes needed.

## B007 Variables NOT Renamed

None — all 4 flagged variables were confirmed unused in their loop bodies and not captured in any lambda or inner function.

## Surprises

- **anchor.py has 2 SIM108, not 1:** The plan estimated one ternary simplification, but ruff found two. Both (`suggest_anchor_name` result in `rename_anchor()` and `pre_color` assignment in `create_anchor()`) were clean collapses with no logic change.
- **labels.py already clean:** The plan expected ~1 E501 violation, but Plan 01's line-length=100 setting already resolved it. No edits needed.

## Deviations from Plan

None — plan executed as written with only the SIM108 count difference (2 instead of estimated 1), which was auto-fixed inline as a standard SIM108 fix.

## Verification

- `ruff check anchor.py link.py colors.py labels.py` — All checks passed
- Full test suite: 132 tests, 0 errors, 0 failures

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/10-code-quality-sweep/10-02-SUMMARY.md
- Commit 2fe8379: FOUND (fix anchor.py and link.py)
- Commit 8d0775b: FOUND (fix colors.py and labels.py)
