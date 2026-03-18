---
phase: quick
plan: 260317-nnh
subsystem: tests, colors
tags: [test-fix, bugfix, _on_accept, button-order]
dependency_graph:
  requires: []
  provides: [green-test-suite]
  affects: [colors.py, tests/test_anchor_color_system.py]
tech_stack:
  added: []
  patterns: [test-harness-isolation]
key_files:
  created: []
  modified:
    - tests/test_anchor_color_system.py
    - colors.py
decisions:
  - "OK button is added before Cancel in PrefsDialog (test was wrong, production was right)"
  - "menu callback moved above naming field reads so harness without naming widgets still triggers it"
metrics:
  duration: "~5 minutes"
  completed: "2026-03-17"
  tasks_completed: 1
  files_modified: 2
---

# Quick Task 260317-nnh: Fix Failing Tests Summary

**One-liner:** Fixed wrong button-order assertion and moved _on_accept menu callback above naming-field reads so both tests pass without harness expansion.

## What Was Done

Restored a green test suite for `tests/test_anchor_color_system.py` by fixing two independent failures:

### Task 1: Fix button order test assertion and reorder _on_accept menu callback

**Change 1 — tests/test_anchor_color_system.py**

`TestPrefsDialogButtonOrderCancelLeft::test_cancel_button_added_before_ok_in_layout` had its `assertLess` arguments reversed: it asserted that the Cancel button's `addWidget` call appeared before the OK button's, but the production code correctly adds OK first (left side). The assertion arguments were swapped to `assertLess(ok_button_add_line, cancel_button_add_line, ...)`. The class and method docstrings were updated to reflect that OK is added before Cancel.

**Change 2 — colors.py `PrefsDialog._on_accept`**

`TestMenuCallbackStoredOnPrefsModule::test_on_accept_calls_set_menu_enabled_when_attribute_present` provides a minimal harness that intentionally omits `_naming_regex_edit`, `_naming_template_edit`, and `_naming_test_filename_edit`. The method crashed on `self._naming_regex_edit.text()` before reaching the `set_anchors_menu_enabled` callback block. The fix moves the callback to immediately after `prefs_module.plugin_enabled` and `prefs_module.link_classes_paste_mode` are set, before the naming field reads. Functional behavior in production is unchanged — the menu enable/disable just fires slightly earlier in the flush sequence.

## Deviations from Plan

None — plan executed exactly as written, with one minor structural clarification: the plan said "move the block to after `prefs_module.plugin_enabled`" which placed it after the link-mode line as well (logical grouping). The intent from CONTEXT.md was that the call must precede `_naming_regex_edit.text()`, which is satisfied.

## Commits

| Hash | Message |
|------|---------|
| 1deabad | fix(260317-nnh): fix button order assertion and reorder _on_accept menu callback |

## Self-Check: PASSED

- tests/test_anchor_color_system.py: FOUND
- colors.py: FOUND
- SUMMARY.md: FOUND
- Commit 1deabad: FOUND
- All 70 tests pass: CONFIRMED
