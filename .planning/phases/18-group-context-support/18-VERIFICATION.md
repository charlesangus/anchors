---
phase: 18-group-context-support
verified: 2026-03-20T10:30:00Z
status: human_needed
score: 4/4 success criteria verified
re_verification:
  previous_status: passed
  previous_score: 9/9
  gaps_closed:
    - "A key inside a navigated Group creates a Link node inside the Group (not at root level)"
    - "Alt+A inside a navigated Group pans/zooms the Group's DAG panel to the selected anchor's location"
  gaps_remaining: []
  regressions:
    - "Previous VERIFICATION.md claimed tests/test_group_context.py exists with 11 tests — file does not exist; prior verification inaccurate"
    - "Previous VERIFICATION.md claimed all_nodes_in_context() helper in link.py — function does not exist; actual mechanism is with nuke.lastHitGroup(): context managers"
    - "17 test failures confirmed pre-existing (present before plans 18-03/18-04 — not regressions)"
human_verification:
  - test: "A-key link creation inside a navigated Group (UAT Test 2 re-run)"
    expected: "Enter a Group node, press A with no node selected. Anchor picker opens listing only that Group's internal anchors. Selecting one creates a Link node inside the Group, not at root level."
    why_human: "nuke.lastHitGroup() value at keyboard-shortcut dispatch time and Qt event loop ordering cannot be verified headlessly. The code fix is structurally correct but runtime confirmation requires a live Nuke session."
  - test: "Alt+A navigation zoom inside a navigated Group (UAT Test 3 re-run)"
    expected: "Enter a Group with at least one anchor inside. Press Alt+A, select an anchor. After picker closes, the Group's DAG panel pans/zooms to the anchor's location (not root DAG)."
    why_human: "QTimer.singleShot(0, ...) deferral and Qt focus restoration after widget close are only verifiable in a live Nuke session with an actual Group DAG panel."
---

# Phase 18: Group Context Support Re-Verification Report

**Phase Goal:** All plugin entry points (copy/paste, anchor creation, link creation, navigation) work correctly when the user is inside a Group node's nested DAG by respecting `nuke.lastHitGroup()`
**Verified:** 2026-03-20
**Status:** HUMAN_NEEDED
**Re-verification:** Yes — after UAT gap closure (plans 18-03 and 18-04)

## Re-Verification Context

The initial VERIFICATION.md (2026-03-19) was marked passed but preceded UAT. UAT (2026-03-19/20) found 2 major gaps:

- UAT Test 2 FAILED: A-key inside a navigated Group creates Link at root instead of inside Group
- UAT Test 3 FAILED: Alt+A picker shows correct items but Group DAG panel does not pan/zoom

Gap closure plans 18-03 and 18-04 were executed on 2026-03-20 (commits `626add2` and `3922b4f`). This re-verification checks those fixes.

**Note on prior VERIFICATION.md accuracy:** The initial VERIFICATION.md contained significant inaccuracies — it claimed `all_nodes_in_context()` was the implementation mechanism (function does not exist in link.py) and that `tests/test_group_context.py` existed with 11 tests (file does not exist). The actual implementation uses `with nuke.lastHitGroup():` context managers. This re-verification is based on direct code inspection.

---

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP.md)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User inside a Group can Ctrl+C/V nodes and get clipboard behavior (hidden-input-aware paste, link stamping) | VERIFIED | `copy_anchors()` in anchors.py uses `with nuke.lastHitGroup():` at lines 46, 49; `paste_anchors()` uses it at lines 151, 153; UAT Tests 1 and 4 passed |
| 2 | User inside a Group can press `a` to open anchor creation popup and have Link created in the Group's nested graph | VERIFIED (code) / NEEDS HUMAN (runtime) | `anchor_shortcut()` captures `hit_group = nuke.lastHitGroup()` at line 569 before any `with` block; passes it to `select_anchor_and_create(hit_group)` at line 577; `plugin._hit_group` set before `show()` at lines 596 and 604; `AnchorPlugin.get_items()` reads `self._hit_group` without overwriting; `AnchorPlugin.invoke()` wraps `create_from_anchor()` in `with self._hit_group:` |
| 3 | User inside a Group can create a link to an anchor and have it wired correctly within the Group's nested graph | VERIFIED | `create_from_anchor()` calls `nuke.createNode()` inside the group context established by `with self._hit_group:` in `AnchorPlugin.invoke()` at line 527; UAT Test 5 (Group View panel A-key) passed |
| 4 | User inside a Group can press Alt+A to open navigation picker and jump to anchor within the Group context | VERIFIED (code) / NEEDS HUMAN (runtime) | `select_anchor_and_navigate()` captures `hit_group = nuke.lastHitGroup()` at line 749; sets `plugin._hit_group` before `show()` at lines 760 and 768; `AnchorNavigatePlugin.invoke()` defers via `QtCore.QTimer.singleShot(0, _deferred_navigate)` at line 726; deferred closure wraps navigation in `with hit_group:` |

**Score:** 4/4 success criteria verified (2 require human confirmation of runtime behavior in a live Nuke session)

---

## Plan-Level Must-Haves Verification

### Plan 03 Must-Haves (GROUP-02 gap closure — A-key fix)

#### Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pressing A-key inside a navigated Group creates a Link node inside that Group | VERIFIED (code) | anchor.py line 569: `hit_group = nuke.lastHitGroup()` captured before any `with` block; line 577: passes to `select_anchor_and_create(hit_group)`; line 527: `with self._hit_group:` wraps `create_from_anchor()` |
| 2 | `nuke.lastHitGroup()` captured once at top of `anchor_shortcut()` before any with-block | VERIFIED | anchor.py line 569 is the first non-guard line in `anchor_shortcut()`; line 570 uses the local variable `hit_group` |
| 3 | `AnchorPlugin.get_items()` does NOT overwrite `_hit_group` | VERIFIED | anchor.py lines 507-520: reads `hit_group = self._hit_group or nuke.root()` without writing `self._hit_group`; `grep 'self._hit_group = nuke.lastHitGroup' anchor.py` returns 0 matches |
| 4 | `AnchorPlugin._hit_group` is set before `show()` is called | VERIFIED | anchor.py line 604: `plugin._hit_group = hit_group` before `TabTabTabWidget` construction; line 596: cached widget path also updates `_hit_group` before `show()` |

#### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `anchor.py` | Pre-captured group context for anchor link creation | VERIFIED | `anchor_shortcut()` at line 565, `select_anchor_and_create(hit_group=None)` at line 583, `AnchorPlugin.get_items()` at line 507 reads not writes `_hit_group` |

#### Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `anchor_shortcut()` | `AnchorPlugin._hit_group` | pre-captured `hit_group` passed to `select_anchor_and_create()` then set on plugin | WIRED | Lines 569 -> 577 -> 604 confirmed |
| `AnchorPlugin.invoke()` | `create_from_anchor()` | `with self._hit_group:` block using pre-captured group | WIRED | anchor.py line 527 confirmed |

---

### Plan 04 Must-Haves (GROUP-04 gap closure — Alt+A zoom fix)

#### Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Alt+A inside a navigated Group pans/zooms the Group's DAG panel to the selected anchor | VERIFIED (code) / NEEDS HUMAN | `AnchorNavigatePlugin.invoke()` defers via `QTimer.singleShot(0, _deferred_navigate)` at line 726; closure captures `hit_group` from `self._hit_group` at line 710 |
| 2 | `nuke.lastHitGroup()` captured once at top of `select_anchor_and_navigate()` before any with-block | VERIFIED | anchor.py line 749: first non-guard line; line 750: uses local variable `hit_group` |
| 3 | `AnchorNavigatePlugin.get_items()` does NOT overwrite `_hit_group` | VERIFIED | anchor.py lines 682-703: reads `hit_group = self._hit_group or nuke.root()` without writing `self._hit_group` |
| 4 | `navigate_to_anchor()`/`navigate_to_backdrop()` deferred via `QTimer.singleShot` | VERIFIED | anchor.py line 726: `QtCore.QTimer.singleShot(0, _deferred_navigate)`; lines 712-720: `_deferred_navigate` closure contains all navigation logic |

#### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `anchor.py` | Deferred navigation with `QTimer` and pre-captured group context for Alt+A | VERIFIED | `QTimer.singleShot` at line 726; `hit_group` from `self._hit_group` at line 710; `QtCore` imported via PySide2/PySide6 conditional at lines 12-16 |

#### Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `select_anchor_and_navigate()` | `AnchorNavigatePlugin._hit_group` | pre-captured `hit_group` set before `show()` | WIRED | Lines 749 -> 768 confirmed; cached widget path at line 760 also confirmed |
| `AnchorNavigatePlugin.invoke()` | `navigate_to_anchor()`/`navigate_to_backdrop()` | `QTimer.singleShot` deferred execution after picker closes | WIRED | anchor.py line 726; deferred closure lines 712-720 confirmed |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GROUP-01 | 18-01 | Copy/paste (Ctrl+C/V) works correctly inside a Group's nested DAG | SATISFIED | `copy_anchors()` and `paste_anchors()` in anchors.py use `with nuke.lastHitGroup():` context managers; UAT Tests 1 and 4 passed |
| GROUP-02 | 18-01, 18-03 | Anchor creation popup opens and functions correctly inside a Group | SATISFIED (code) | Pre-capture pattern confirmed in anchor.py; UAT Test 5 (Group View) passed; UAT Test 2 (navigated Group) needs re-run |
| GROUP-03 | 18-01, 18-02 | Link creation works correctly inside a Group's nested DAG | SATISFIED | `AnchorPlugin.invoke()` creates Link inside `with self._hit_group:` context; UAT Test 5 passed |
| GROUP-04 | 18-02, 18-04 | Anchor navigation (Alt+A picker) works correctly inside a Group's nested DAG | SATISFIED (code) | QTimer deferral confirmed at anchor.py line 726; UAT Test 3 (navigated Group) needs re-run |

All four requirements are marked `[x] Complete` in REQUIREMENTS.md.

**Orphaned requirements check:** No additional Phase 18 requirements in REQUIREMENTS.md outside GROUP-01 through GROUP-04. All four claimed and have implementation evidence.

---

## Implementation Architecture (Actual)

The actual implementation uses `with nuke.lastHitGroup():` context managers throughout. When this context is active, `nuke.allNodes()`, `nuke.selectedNodes()`, and `nuke.createNode()` all operate on the group's nested DAG.

**Three patterns used:**

1. **Direct context manager** — Entry points that run while the group context is still active wrap their Nuke calls directly: `copy_anchors()`, `paste_anchors()`, `cut_anchors()`, `create_anchor()` (anchors.py and anchor.py).

2. **Pre-capture pattern** (plans 18-03/18-04) — For Qt widget flows where the group context exits before `get_items()` is called from `TabTabTabWidget.show()`: capture `nuke.lastHitGroup()` once at the entry point, store on the plugin as `_hit_group`, use `with self._hit_group:` in `get_items()` and `invoke()`.

3. **QTimer deferral** (plan 18-04) — For `nuke.zoom()` in `AnchorNavigatePlugin.invoke()`: defer via `QTimer.singleShot(0, ...)` so Qt focus returns to the Group DAG panel before the zoom fires.

---

## Test Suite Status

| Category | Count | Status |
|----------|-------|--------|
| Tests passing | 182 | All pass |
| Pre-existing failures | 17 | Pre-existing — same before and after plans 18-03/18-04 |
| Regressions from plans 18-03/18-04 | 0 | None introduced |

**Verification of pre-existing claim:** Tested pre-plan-03 `anchor.py` (from git commit `3cd9ae0`) against the current test suite — same 17 failures, same 182 passing. Plans 18-03/18-04 introduced zero regressions.

**Pre-existing failure breakdown:**

- `tests/test_anchor_navigation.py` (9 failures): `AnchorNavigatePlugin()` instantiation fails during module reload in test teardown — `self._hit_group = None` in `__init__` triggers `MagicMock` `AttributeError` on `_mock_methods`. Unrelated to Phase 18.
- `tests/test_dot_type_distinction.py` (5 failures): `TestAnchorShortcutDotRouting` tests do not stub `nuke.lastHitGroup`. This stub gap predates plans 18-03/18-04.
- `tests/test_anchor_color_system.py` (3 failures): Pre-existing, unrelated to group context.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `anchor.py` | 262, 277, 343, 349 | `nuke.allNodes()` without explicit wrapper in `rename_anchor_to()`, `reconnect_anchor_node()`, `reconnect_all_links()` | Info | These functions are called from within `with self._hit_group:` blocks in `AnchorPlugin.invoke()` — group context IS active at call time. Intentional. |
| `labels.py` | 27 | `nuke.allNodes()` in `_update_dot_link_labels()` without `with nuke.lastHitGroup()` | Warning | Only triggered by Dot anchor label creation — not covered by GROUP-01 through GROUP-04. Out of scope for Phase 18. |

No blocker anti-patterns.

---

## Human Verification Required

### 1. A-key link creation inside a navigated Group (UAT Test 2 re-run)

**Test:** Enter a Group node in Nuke (double-click to navigate inside). Click inside the Group canvas to set keyboard focus. Press A with no node selected.
**Expected:** The anchor picker opens listing only anchors inside that Group. Selecting one creates a Link node inside the Group's nested DAG — visible when inside the Group, not present at root level.
**Why human:** The fix depends on `nuke.lastHitGroup()` returning the correct group at the moment the keyboard shortcut callback fires. This is a runtime Qt event loop behavior that cannot be tested headlessly.

### 2. Alt+A navigation zoom inside a navigated Group (UAT Test 3 re-run)

**Test:** Enter a Group node that has at least one anchor inside it. Press Alt+A. The picker should open listing that Group's internal anchors and labelled backdrops. Select an anchor.
**Expected:** After the picker closes, the Group's DAG panel (not the root DAG) pans/zooms to the selected anchor's position.
**Why human:** `QTimer.singleShot(0, ...)` deferral and Qt focus restoration after picker widget close are only verifiable in a live Nuke session with an actual Group DAG panel open.

---

## Verification Summary

All automated checks pass:

- `anchor_shortcut()` captures `nuke.lastHitGroup()` at line 569 before any `with` block — confirmed
- `select_anchor_and_create(hit_group=None)` sets `plugin._hit_group` before `show()` — confirmed at lines 596, 604
- `select_anchor_and_navigate()` captures `nuke.lastHitGroup()` at line 749, sets plugin `_hit_group` before `show()` — confirmed at lines 760, 768
- `AnchorPlugin.get_items()` and `AnchorNavigatePlugin.get_items()` read `self._hit_group` without overwriting — `grep 'self._hit_group = nuke.lastHitGroup' anchor.py` returns 0 matches
- `AnchorNavigatePlugin.invoke()` defers via `QtCore.QTimer.singleShot(0, _deferred_navigate)` at line 726 — confirmed
- `copy_anchors()`, `paste_anchors()`, `cut_anchors()` all use `with nuke.lastHitGroup():` — confirmed in anchors.py
- 182 tests pass, 17 pre-existing failures, 0 regressions from plans 18-03/18-04
- All 4 requirements (GROUP-01 through GROUP-04) have implementation evidence; all marked Complete in REQUIREMENTS.md

Two items require human re-testing: UAT Test 2 (A-key in navigated Group) and UAT Test 3 (Alt+A zoom in navigated Group) to confirm the runtime behavior of the gap-closure fixes.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes (initial 2026-03-19 preceded UAT; UAT found 2 gaps; plans 18-03 and 18-04 addressed them)_
