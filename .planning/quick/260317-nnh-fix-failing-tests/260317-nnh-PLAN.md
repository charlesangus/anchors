---
phase: quick
plan: 260317-nnh
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_anchor_color_system.py
  - colors.py
autonomous: true
must_haves:
  truths:
    - "All tests in test_anchor_color_system.py pass"
    - "Button order test asserts OK appears before Cancel (matching production code)"
    - "Menu callback fires even when naming fields are not present on harness"
  artifacts:
    - path: "tests/test_anchor_color_system.py"
      provides: "Corrected button order assertion"
      contains: "assertLess(ok_button_add_line, cancel_button_add_line"
    - path: "colors.py"
      provides: "Reordered _on_accept with menu callback before naming field reads"
  key_links:
    - from: "colors.py _on_accept"
      to: "prefs_module.set_anchors_menu_enabled"
      via: "getattr call placed before naming field reads"
      pattern: "plugin_enabled.*set_anchors_menu_enabled.*_naming_regex_edit"
---

<objective>
Fix 2 failing pytest tests in tests/test_anchor_color_system.py.

Purpose: Restore green test suite by fixing a wrong test assertion and reordering production code to prevent a crash in the test harness.
Output: Both tests pass; no behavioral change to the application.
</objective>

<execution_context>
@/home/latuser/.claude/get-shit-done/workflows/execute-plan.md
@/home/latuser/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@tests/test_anchor_color_system.py
@colors.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix button order test assertion and reorder _on_accept menu callback</name>
  <files>tests/test_anchor_color_system.py, colors.py</files>
  <action>
Two changes:

1. **tests/test_anchor_color_system.py** — In class `TestPrefsDialogButtonOrderCancelLeft`, method `test_cancel_button_added_before_ok_in_layout` (around line 1848):
   - Change `self.assertLess(cancel_button_add_line, ok_button_add_line, ...)` to `self.assertLess(ok_button_add_line, cancel_button_add_line, ...)`
   - Update the failure message to say OK button must be added before Cancel button (OK on left, Cancel on right) — per user decision, the production code is correct with OK added first
   - Update the class docstring and method docstring to reflect that OK is added BEFORE Cancel (not the other way around)

2. **colors.py** — In `PrefsDialog._on_accept` (line 1068):
   - Move the `set_anchors_menu_enabled` call block (lines 1092-1097: the comment + getattr + if-call) to immediately after `prefs_module.plugin_enabled = self._local_plugin_enabled` (after line 1080)
   - This places the menu callback BEFORE the `_naming_regex_edit.text()` call at line 1076, so the test harness (which does not mock naming fields) can invoke the callback before the exception
   - Keep the existing comment explaining why getattr is used
   - Do NOT change any other logic or ordering in the method
  </action>
  <verify>
    <automated>python3 -m pytest tests/test_anchor_color_system.py::TestPrefsDialogButtonOrderCancelLeft tests/test_anchor_color_system.py::TestMenuCallbackStoredOnPrefsModule -x -q</automated>
  </verify>
  <done>Both previously-failing tests pass. Full test suite has no regressions: python3 -m pytest tests/test_anchor_color_system.py -q</done>
</task>

</tasks>

<verification>
python3 -m pytest tests/test_anchor_color_system.py -q
All tests pass with 0 failures.
</verification>

<success_criteria>
- TestPrefsDialogButtonOrderCancelLeft::test_cancel_button_added_before_ok_in_layout passes
- TestMenuCallbackStoredOnPrefsModule::test_on_accept_calls_set_menu_enabled_when_attribute_present passes
- Full test suite (python3 -m pytest tests/test_anchor_color_system.py) shows 0 failures
</success_criteria>

<output>
After completion, create `.planning/quick/260317-nnh-fix-failing-tests/260317-nnh-SUMMARY.md`
</output>
