---
phase: quick-260328-6mn
plan: "01"
subsystem: navigation
tags: [navigation, anchor, jump, shortcut, menu]
dependency_graph:
  requires: []
  provides: [jump_to_selected_anchor]
  affects: [anchor.py, menu.py, tests/test_anchor_navigation.py]
tech_stack:
  added: []
  patterns: [TDD red-green, gated menu command, _save_dag_position before navigate]
key_files:
  modified:
    - anchor.py
    - menu.py
    - tests/test_anchor_navigation.py
decisions:
  - No Qt deferred timer needed — user already has DAG focus when selecting a node
  - Alt+J chosen as shortcut (mnemonic for Jump, not already taken, follows Alt+key pattern)
  - Function placed after navigate_back() and before navigate_to_backdrop() in anchor.py
metrics:
  duration: ~10 minutes
  completed: "2026-03-28T11:50:44Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase quick-260328-6mn Plan 01: Jump-to-Selected-Anchor Command Summary

**One-liner:** Direct DAG jump to a selected anchor's upstream tree via Alt+J, saving position for navigate_back.

## What Was Built

Added `jump_to_selected_anchor()` to `anchor.py` — a zero-popup navigation function for when the user already has a target anchor selected in the DAG. Pressing Alt+J navigates directly to that anchor's upstream tree (reusing `navigate_to_anchor()`), having first saved the viewport so Alt+Z (navigate_back) returns to the previous position.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 (RED) | Failing tests for jump_to_selected_anchor | a2fd1cd | tests/test_anchor_navigation.py |
| 1 (GREEN) | Implement jump_to_selected_anchor | f796461 | anchor.py |
| 2 | Add Anchor Jump menu entry (Alt+J) | 050e7e3 | menu.py |

## Implementation Details

### anchor.py — jump_to_selected_anchor()

```python
def jump_to_selected_anchor():
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    first_selected_node = selected_nodes[0]
    if not is_anchor(first_selected_node):
        return
    _save_dag_position()
    navigate_to_anchor(first_selected_node)
```

### menu.py — new gated menu entry

```python
_add_gated_command(anchors_menu, "Anchor Jump", "anchor.jump_to_selected_anchor()", "alt+J")
```

Placed between Anchor Find (Alt+A) and Anchor Back (Alt+Z).

## Test Results

- 5 new tests added to `TestJumpToSelectedAnchor` in `tests/test_anchor_navigation.py`
- All 5 pass (saves-position-then-navigates, no-op on empty selection, no-op on non-anchor, no-op when disabled, integration back-navigation)
- Full suite: **211 tests pass** (up from 208)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `anchor.jump_to_selected_anchor` exists in anchor.py: FOUND
- `Anchor Jump` entry with `alt+J` in menu.py: FOUND
- Commits a2fd1cd, f796461, 050e7e3: FOUND
