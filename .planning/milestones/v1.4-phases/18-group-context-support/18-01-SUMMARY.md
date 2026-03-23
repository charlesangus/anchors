---
phase: 18-group-context-support
plan: "01"
subsystem: core
tags: [group-context, nuke-api, all-nodes, helper-function, tdd]
dependency_graph:
  requires: []
  provides: [all_nodes_in_context helper, Group-aware anchor scanning, Group-aware label propagation]
  affects: [link.py, anchors.py, labels.py, tests/stubs.py, tests/test_group_context.py]
tech_stack:
  added: []
  patterns: [Group-context helper wrapping nuke.thisGroup()]
key_files:
  created: [tests/test_group_context.py]
  modified: [link.py, anchors.py, labels.py, tests/stubs.py]
decisions:
  - "Single all_nodes_in_context() helper in link.py rather than inline nuke.thisGroup() at each call site — consistent, testable, single point of truth"
  - "migrate_script() in anchors.py intentionally excluded from the change — it uses recurseGroups=True to traverse the full script tree, which is correct for migration"
  - "find_anchor_node() intentionally excluded — it uses nuke.toNode() which resolves full paths across Group boundaries correctly"
  - "Added _restore_knob_constructors() helper in test_group_context.py to guard against nuke stub contamination from test_dot_type_distinction.py overriding String_Knob/Tab_Knob side_effects"
metrics:
  duration_seconds: 394
  completed_date: "2026-03-19"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 5
---

# Phase 18 Plan 01: Group Context Support — Core Helper Summary

Group-context-aware `all_nodes_in_context()` helper added to link.py; all bare `nuke.allNodes()` call sites in link.py (backdrop detection), anchors.py (anchor scanning in copy_anchors), and labels.py (label propagation) replaced with the helper that passes `group=nuke.thisGroup()`.

## What Was Built

- `all_nodes_in_context(node_class=None)` in `/workspace/link.py` — wraps `nuke.allNodes()` with `group=nuke.thisGroup()` so all plugin operations target the DAG the user is currently viewing inside a Group node
- Updated `find_smallest_containing_backdrop()` in `link.py` to use `all_nodes_in_context('BackdropNode')`
- Updated `copy_anchors()` in `anchors.py` to use `all_nodes_in_context()` for anchor candidate scanning
- Updated `_update_dot_link_labels()` in `labels.py` to use `all_nodes_in_context()` for link node scanning
- `thisGroup` stub added to `make_stub_nuke_module()` in `tests/stubs.py`
- 5-test suite in `tests/test_group_context.py` verifying Group-context behaviour at all affected call sites

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create all_nodes_in_context() helper in link.py and update stubs | 03a3632 | link.py, tests/stubs.py |
| 2 | Update anchors.py and labels.py to use all_nodes_in_context() | e3ca26a | anchors.py, labels.py |
| 3 | Add Group-context unit tests | 0e5ca2e | tests/test_group_context.py |

## Verification

- `grep -c 'def all_nodes_in_context' link.py` → 1
- No bare `nuke.allNodes()` calls in link.py (code), anchors.py, or labels.py outside of `migrate_script()` (recurseGroups=True) and the helper docstring
- `anchors.py` and `labels.py` both import and use `all_nodes_in_context`
- Full test suite: 204 tests, 0 failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reset nuke.allNodes.side_effect in group context tests**
- **Found during:** Task 3 full-suite test run
- **Issue:** `test_anchor_navigation.py` leaves a `side_effect` on `nuke.allNodes` that only accepts `class_name` positional argument, not `group=` keyword. Tests in isolation passed; full-suite run failed with TypeError.
- **Fix:** Added `nuke.allNodes.side_effect = None` before each `reset_mock()` call in the group context tests.
- **Files modified:** tests/test_group_context.py
- **Commit:** 0e5ca2e

**2. [Rule 1 - Bug] Restore knob constructor side_effects in TestCopyAnchorsGroupContext**
- **Found during:** Task 3 full-suite test run
- **Issue:** `test_dot_type_distinction.py` replaces `nuke.String_Knob` and `nuke.Tab_Knob` with custom MagicMock instances that return `StubKnob(value=name, knob_name='')` — a knob with empty `knob_name`. When `add_input_knob()` later calls `node.addKnob(knob)`, the knob is stored under `''` instead of `'copy_hidden_input_node'`, causing `node[KNOB_NAME]` to raise NameError.
- **Fix:** Added `_restore_knob_constructors()` helper that reinstates the canonical `side_effect=lambda name, *args: StubKnob(knob_name=name)` on all three knob constructors. Called in `TestCopyAnchorsGroupContext.setUp()`.
- **Files modified:** tests/test_group_context.py
- **Commit:** 0e5ca2e

**3. [Rule 3 - Lint] Fix import sort order in test_group_context.py**
- **Found during:** Task 3 ruff check
- **Issue:** `from tests.stubs import StubNode, StubKnob` — symbols not sorted alphabetically (StubNode before StubKnob).
- **Fix:** Reordered to `from tests.stubs import StubKnob, StubNode` and separated stdlib/third-party/local blocks.
- **Files modified:** tests/test_group_context.py
- **Commit:** 0e5ca2e

## Self-Check: PASSED

All key files exist. All three task commits verified in git log. Full test suite: 204 passed, 0 failed.
