---
phase: 18-group-context-support
plan: "02"
subsystem: core
tags: [group-context, nuke-api, all-nodes, anchor, navigation, reconnect, rename]
dependency_graph:
  requires: [18-01]
  provides: [Group-aware anchor operations, Group-context anchor tests]
  affects: [anchor.py, tests/test_group_context.py, tests/test_anchor_navigation.py]
tech_stack:
  added: []
  patterns: [Group-context helper at all anchor.py call sites]
key_files:
  created: []
  modified: [anchor.py, tests/test_group_context.py, tests/test_anchor_navigation.py]
decisions:
  - "Auto-fixed _allNodes_side_effect signatures in test_anchor_navigation.py to accept **kwargs — pre-existing test helpers broke when all_nodes_in_context() started passing group= kwarg"
metrics:
  duration_seconds: 197
  completed_date: "2026-03-19"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 18 Plan 02: Group Context Support — anchor.py Call Sites Summary

All 8 bare `nuke.allNodes()` call sites in anchor.py replaced with `all_nodes_in_context()` from link.py; 6 new group-context unit tests appended to test_group_context.py verifying anchor creation, navigation, rename, and reconnection all use Group-context-aware scanning.

## What Was Built

- Updated `anchor.py` to import `all_nodes_in_context` from link and replaced 8 `nuke.allNodes()` call sites:
  - `all_anchors()` — scans anchors in current Group context
  - `get_links_for_anchor()` — scans link nodes in current Group context
  - `rename_anchor_to()` Dot branch — updates link FQNNs in current Group context
  - `rename_anchor_to()` NoOp branch — updates link FQNNs in current Group context
  - `reconnect_anchor_node()` — finds link nodes to reconnect in current Group context
  - `reconnect_all_links()` — reconnects all links in current Group context
  - `AnchorNavigatePlugin.get_items()` — scans BackdropNodes in current Group context
  - `select_anchor_and_navigate()` — scans BackdropNodes for picker guard in current Group context
- Extended `tests/test_group_context.py` with 6 new test classes:
  - `TestAllAnchorsGroupContext` — verifies `all_anchors()` passes `group=` kwarg
  - `TestGetLinksForAnchorGroupContext` — verifies `get_links_for_anchor()` passes `group=` kwarg
  - `TestRenameAnchorGroupContext` — verifies `rename_anchor_to()` NoOp branch passes `group=` kwarg
  - `TestReconnectGroupContext` — verifies `reconnect_anchor_node()` and `reconnect_all_links()` pass `group=` kwarg
  - `TestNavigateGroupContext` — verifies `AnchorNavigatePlugin.get_items()` passes `group=` kwarg for backdrop scan

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update all nuke.allNodes() calls in anchor.py to use all_nodes_in_context() | ddc8daf | anchor.py, tests/test_anchor_navigation.py |
| 2 | Add Group-context tests for anchor creation, navigation, rename, and reconnection | 28c6e97 | tests/test_group_context.py |

## Verification

- `grep -c 'nuke\.allNodes' anchor.py` → 0 (no bare calls remain)
- `grep -c 'all_nodes_in_context' anchor.py` → 9 (1 import + 8 call sites)
- `pytest tests/test_group_context.py -v` → 11 passed
- `pytest tests/ -q` → 210 passed, 0 failed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _allNodes_side_effect signatures in test_anchor_navigation.py**
- **Found during:** Task 1 pytest run
- **Issue:** Six `_allNodes_side_effect` helper functions in `tests/test_anchor_navigation.py` were defined as `def _allNodes_side_effect(class_name=None)` without accepting keyword arguments. After `AnchorNavigatePlugin.get_items()` and `select_anchor_and_navigate()` were updated to use `all_nodes_in_context()`, the helpers received an unexpected `group=` kwarg and raised `TypeError`.
- **Fix:** Added `**kwargs` to all six `_allNodes_side_effect` signatures so they accept the `group=` kwarg passed by `all_nodes_in_context()`.
- **Files modified:** tests/test_anchor_navigation.py
- **Commit:** ddc8daf

## Self-Check: PASSED

All key files exist and were modified as planned. Both task commits verified in git log. Full test suite: 210 passed, 0 failed.
