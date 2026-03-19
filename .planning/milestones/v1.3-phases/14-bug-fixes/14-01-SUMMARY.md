---
phase: 14-bug-fixes
plan: 01
subsystem: colors
tags: [bug-fix, tdd, chosen_name, ColorPaletteDialog, accept]
dependency_graph:
  requires: []
  provides: [ColorPaletteDialog.accept() override]
  affects: [anchor.py create_anchor() — reads dialog.chosen_name correctly on all acceptance paths]
tech_stack:
  added: []
  patterns: [single-chokepoint accept() override instead of scattered assignments]
key_files:
  created: []
  modified:
    - colors.py
    - tests/test_anchor_color_system.py
decisions:
  - "accept() override is placed before _on_swatch_clicked to serve as the canonical chokepoint for chosen_name capture"
  - "Test uses _extract_accept_method_from_source() with super() stub to work around __class__ cell not found in extracted method context"
metrics:
  duration: "4 min"
  completed_date: "2026-03-16"
requirements:
  - BUG-03
---

# Phase 14 Plan 01: Fix BUG-03 chosen_name Capture on ColorPaletteDialog Accept Summary

**One-liner:** Single `accept()` override captures `_name_edit.text()` into `chosen_name`, replacing five scattered assignments across eventFilter, keyPressEvent, and _on_custom_color_clicked.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add regression tests for BUG-03 (RED) | dd0aed6 | tests/test_anchor_color_system.py |
| 2 | Fix BUG-03 in colors.py (GREEN) | 5c3f190 | colors.py, tests/test_anchor_color_system.py |

## What Was Built

### colors.py
- Added `accept()` override on `ColorPaletteDialog` (inserted before `_on_swatch_clicked`)
- The override reads `self._name_edit.text()` into `self.chosen_name` when `_name_edit` is not None, then calls `super().accept()`
- Removed all five scattered `if self._name_edit is not None: self.chosen_name = self._name_edit.text()` blocks from:
  - `_on_custom_color_clicked` (was called before `self.accept()`)
  - `eventFilter` Enter/Return handler
  - `eventFilter` hint-mode column key handler
  - `keyPressEvent` Enter/Return handler
  - `keyPressEvent` hint-mode column key handler

### tests/test_anchor_color_system.py
- Added `_extract_accept_method_from_source()` helper that extracts `accept()` from colors.py source with a `super()` stub injected into the exec namespace (avoids `__class__ cell not found` error from AST extraction)
- Added `TestColorPaletteDialogChosenNameCapturedOnAccept` class with two test methods:
  - `test_chosen_name_captured_from_name_edit_on_accept`: asserts `chosen_name == "typed_name"` after `accept()` when `_name_edit` holds that value
  - `test_no_crash_when_name_edit_is_none`: asserts no exception and `chosen_name` unchanged when `_name_edit` is None

## Verification

```
python3.11 -m unittest tests.test_anchor_color_system -v
# Ran 70 tests in 0.325s — OK
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `super()` cell not found in extracted method context**
- **Found during:** Task 2 (GREEN — first test run after adding fix)
- **Issue:** `_extract_method_from_source` compiles methods via `exec()` outside a class body; `super()` without arguments requires a `__class__` cell variable set up by Python's class compilation machinery, which is absent in the extracted context — raising `RuntimeError: super(): __class__ cell not found`
- **Fix:** Added `_extract_accept_method_from_source()` helper that injects `super = MagicMock(return_value=MagicMock())` into the exec namespace, making `super().accept()` a no-op while allowing the `chosen_name` assignment logic to execute normally
- **Files modified:** tests/test_anchor_color_system.py
- **Commit:** 5c3f190

## Decisions Made

1. `accept()` placed before `_on_swatch_clicked` — first natural position after `_build_ui` inside the class body
2. Dedicated `_extract_accept_method_from_source()` rather than modifying the shared `_extract_method_from_source()` helper — avoids disrupting the 15+ existing tests that use that helper and do not have `super()` calls

## Self-Check

- [x] `colors.py` contains `def accept(self)` in `ColorPaletteDialog`
- [x] No `chosen_name = self._name_edit.text()` outside `accept()` in colors.py
- [x] `TestColorPaletteDialogChosenNameCapturedOnAccept` exists in test file
- [x] Commits dd0aed6 and 5c3f190 exist
- [x] 70 tests pass in test_anchor_color_system.py
