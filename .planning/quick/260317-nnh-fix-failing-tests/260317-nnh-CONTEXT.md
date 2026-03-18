# Quick Task 260317-nnh: fix failing tests - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Task Boundary

Fix 2 failing pytest tests in tests/test_anchor_color_system.py.

</domain>

<decisions>
## Implementation Decisions

### Button order test (TestPrefsDialogButtonOrderCancelLeft)
- The production code in colors.py is correct: OK is added before Cancel (`[OK] [Cancel]`)
- Fix the test to match the code — update the assertion so it expects OK before Cancel (not Cancel before OK)

### Menu callback timing (TestMenuCallbackStoredOnPrefsModule)
- Reorder `_on_accept` in colors.py: move the `set_anchors_menu_enabled` call to immediately after `prefs_module.plugin_enabled` is assigned, before the naming field reads (`_naming_regex_edit.text()` etc.)
- Do NOT expand the test harness
- Production code change only in that method's operation order

### Claude's Discretion
- Exact placement of the reordered call within the flush block

</decisions>

<specifics>
## Specific Ideas

- `_on_accept` line 1076 is where the crash happens (`_naming_regex_edit.text()`) — menu callback must be moved above this line
- Button test fix: change `assertLess(cancel_button_add_line, ok_button_add_line, ...)` to `assertLess(ok_button_add_line, cancel_button_add_line, ...)` and update the failure message

</specifics>
