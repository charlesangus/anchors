---
phase: 18-group-context-support
verified: 2026-03-19T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 18: Group Context Support Verification Report

**Phase Goal:** All plugin entry points (copy/paste, anchor creation, link creation, navigation) work correctly when the user is inside a Group node's nested DAG by respecting `nuke.thisGroup()`
**Verified:** 2026-03-19
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User inside a Group can Ctrl+C/V nodes and get clipboard behavior (hidden-input-aware paste, link stamping) | VERIFIED | `copy_anchors()` in anchors.py uses `all_nodes_in_context()` at line 61; `_update_dot_link_labels()` in labels.py uses it at line 28; both confirmed by test `TestCopyAnchorsGroupContext` and `TestLabelPropagationGroupContext` |
| 2 | User inside a Group can press `a` to open anchor creation popup and have it created in the Group's nested graph | VERIFIED | `all_anchors()` in anchor.py uses `all_nodes_in_context()` (line 170); `get_links_for_anchor()` uses it (line 186); confirmed by `TestAllAnchorsGroupContext` and `TestGetLinksForAnchorGroupContext` |
| 3 | User inside a Group can create a link to an anchor and have it wired correctly within the Group's nested graph | VERIFIED | `rename_anchor_to()` (Dot + NoOp branches, lines 263 and 278), `reconnect_anchor_node()` (line 344), `reconnect_all_links()` (line 350) all use `all_nodes_in_context()`; confirmed by `TestRenameAnchorGroupContext` and `TestReconnectGroupContext` |
| 4 | User inside a Group can press Alt+A to open the navigation picker and jump to an anchor within the Group context | VERIFIED | `AnchorNavigatePlugin.get_items()` (line 654) and `select_anchor_and_navigate()` (line 698) use `all_nodes_in_context('BackdropNode')`; confirmed by `TestNavigateGroupContext` |

**Score:** 4/4 success criteria verified

---

## Plan-Level Must-Haves Verification

### Plan 01 Must-Haves (GROUP-01, GROUP-03)

#### Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `nuke.allNodes()` calls in link.py, anchors.py, labels.py respect Group context via `nuke.thisGroup()` | VERIFIED | All three files use `all_nodes_in_context()`; only bare `nuke.allNodes()` remaining in anchors.py is `migrate_script()` with `recurseGroups=True` (intentional by design) |
| 2 | Copy/paste inside a Group finds anchors within the Group (not root DAG) for FQNN stamping | VERIFIED | anchors.py line 61: `for candidate in all_nodes_in_context():` |
| 3 | `find_smallest_containing_backdrop()` finds backdrops within the current Group context | VERIFIED | link.py line 83: `for bd in all_nodes_in_context('BackdropNode'):` |
| 4 | Label propagation (`_update_dot_link_labels`) finds link nodes within the current Group context | VERIFIED | labels.py line 28: `for candidate_node in all_nodes_in_context():` |

#### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `link.py` | `all_nodes_in_context()` Group-aware helper | VERIFIED | `def all_nodes_in_context(node_class=None):` at line 25; calls `nuke.thisGroup()` at line 39 |
| `anchors.py` | Group-aware `copy_anchors()` anchor scanning | VERIFIED | Imports `all_nodes_in_context` at line 23; used at line 61 |
| `labels.py` | Group-aware label propagation | VERIFIED | Imports `all_nodes_in_context` at line 16; used at line 28 |
| `tests/test_group_context.py` | Unit tests for Group-context behaviour | VERIFIED | File exists with 9 classes, 11 test methods; all pass |
| `tests/stubs.py` | `thisGroup` stub for Group-context testing | VERIFIED | `stub.thisGroup = MagicMock(return_value=root_group)` at line 136 |

#### Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `link.py` | `nuke.thisGroup()` | `all_nodes_in_context()` helper | WIRED | `nuke.thisGroup()` called at link.py:39 inside `all_nodes_in_context()` |
| `anchors.py` | `link.py` | `import all_nodes_in_context` | WIRED | `from link import (..., all_nodes_in_context, ...)` at anchors.py:21-30 |
| `labels.py` | `link.py` | `import all_nodes_in_context` | WIRED | `from link import (all_nodes_in_context, ...)` at labels.py:15-22 |

---

### Plan 02 Must-Haves (GROUP-02, GROUP-04)

#### Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Anchor creation popup works inside a Group — anchors created in the Group's nested DAG | VERIFIED | `all_anchors()` uses `all_nodes_in_context()` at anchor.py:170 |
| 2 | `all_anchors()` returns anchors within the current Group context, not root-level anchors | VERIFIED | anchor.py:170: `anchors = [n for n in all_nodes_in_context() if is_anchor(n)]` |
| 3 | Anchor navigation (Alt+A picker) lists anchors and backdrops within the current Group context | VERIFIED | `AnchorNavigatePlugin.get_items()` at anchor.py:654 and `select_anchor_and_navigate()` at anchor.py:698 both call `all_nodes_in_context('BackdropNode')` |
| 4 | Anchor rename propagates label changes to link nodes within the current Group context | VERIFIED | `rename_anchor_to()` Dot branch (line 263) and NoOp branch (line 278) both use `all_nodes_in_context()` |
| 5 | Reconnect operations find link nodes within the current Group context | VERIFIED | `reconnect_anchor_node()` (line 344) and `reconnect_all_links()` (line 350) both use `all_nodes_in_context()` |

#### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `anchor.py` | Group-aware anchor operations | VERIFIED | 9 occurrences of `all_nodes_in_context` (1 import + 8 call sites); zero bare `nuke.allNodes()` calls |
| `tests/test_group_context.py` | Tests for anchor creation and navigation in Group context | VERIFIED (with naming note) | File contains `TestAllAnchorsGroupContext` (not `TestAnchorCreationGroupContext` as specified in plan artifact — behavior fully covered but class named differently) |

#### Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `anchor.py` | `link.py` | `import all_nodes_in_context` | WIRED | `from link import (all_nodes_in_context, ...)` at anchor.py:36-46 |
| `anchor.py all_anchors()` | `all_nodes_in_context()` | function call replacing `nuke.allNodes()` | WIRED | anchor.py:170 confirmed; `grep -c 'nuke.allNodes' anchor.py` returns 0 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GROUP-01 | 18-01 | Copy/paste works correctly inside a Group's nested DAG | SATISFIED | `copy_anchors()` uses `all_nodes_in_context()`; `TestCopyAnchorsGroupContext` passes |
| GROUP-02 | 18-02 | Anchor creation popup opens and functions correctly inside a Group | SATISFIED | `all_anchors()` and all anchor.py call sites use `all_nodes_in_context()`; `TestAllAnchorsGroupContext` passes |
| GROUP-03 | 18-01 | Link creation works correctly inside a Group's nested DAG | SATISFIED | `reconnect_anchor_node()`, `reconnect_all_links()`, `rename_anchor_to()` all use `all_nodes_in_context()`; reconnect tests pass |
| GROUP-04 | 18-02 | Anchor navigation (Alt+A picker) works correctly inside a Group's nested DAG | SATISFIED | `AnchorNavigatePlugin.get_items()` and `select_anchor_and_navigate()` use `all_nodes_in_context('BackdropNode')`; `TestNavigateGroupContext` passes |

**Orphaned requirements check:** No requirements mapped to Phase 18 in REQUIREMENTS.md were missing from plans. All four GROUP-01 through GROUP-04 are claimed and satisfied.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| anchors.py | 161, 164 | word "placeholder" in comment | Info | Code comment describing paste behavior — not an implementation stub; no impact |

No blocker or warning anti-patterns found. The "placeholder" occurrences are inline documentation within `paste_anchors()` describing what happens to disconnected nodes during cross-script paste — correct and intentional.

---

## Human Verification Required

### 1. Copy/paste inside a live Group node

**Test:** Enter a Group node in Nuke, select a Read node with an anchor pointing to it, press Ctrl+C, then Ctrl+V.
**Expected:** The pasted node is stamped with the anchor's FQNN and reconnects correctly within the Group's nested DAG (not the root DAG).
**Why human:** Runtime DAG state (which group is "current") cannot be simulated in headless tests. `nuke.thisGroup()` returns the correct group only in a live Nuke session.

### 2. Anchor creation popup inside a Group (press `a`)

**Test:** Enter a Group node in Nuke, click inside the Group's canvas, press `a`.
**Expected:** The anchor creation popup opens, and after naming the anchor it is created inside the Group (visible when inside, not at root level).
**Why human:** Qt popup interaction and `nuke.lastHitGroup()` context detection requires a live Nuke session.

### 3. Alt+A picker inside a Group

**Test:** Enter a Group node with at least one anchor inside it. Press Alt+A.
**Expected:** The picker lists only anchors inside that Group (not root-level anchors). Selecting one navigates within the Group's DAG.
**Why human:** Picker display and navigation behavior requires a running Nuke session with actual DAG context.

---

## Verification Summary

All automated checks pass:

- `all_nodes_in_context()` helper exists in link.py at line 25, correctly wraps `nuke.allNodes()` with `group=nuke.thisGroup()`
- Zero bare `nuke.allNodes()` calls remain in anchor.py or labels.py
- The single remaining `nuke.allNodes()` call in anchors.py (line 276) uses `recurseGroups=True` inside `migrate_script()` — intentionally excluded per design decision
- anchor.py has 9 occurrences of `all_nodes_in_context` (1 import + 8 call sites)
- All 5 commits from plan summaries (03a3632, e3ca26a, 0e5ca2e, ddc8daf, 28c6e97) verified in git log
- Full test suite: 210 tests, 0 failures
- Group-context test file: 11 tests across 9 classes, all pass
- All 4 requirement IDs (GROUP-01 through GROUP-04) satisfied with implementation evidence

One minor artifact naming deviation: plan 02 specified `contains: "TestAnchorCreationGroupContext"` but the delivered class is `TestAllAnchorsGroupContext`. The GROUP-02 behavior (anchor creation in Group context via `all_anchors()`) is fully tested — the class name differs from the plan's specification only. This does not affect goal achievement.

Three items require human verification in a live Nuke session: the actual runtime behavior of `nuke.thisGroup()` returning the correct group when the user is inside a Group node. These cannot be tested headlessly.

---

_Verified: 2026-03-19_
_Verifier: Claude (gsd-verifier)_
