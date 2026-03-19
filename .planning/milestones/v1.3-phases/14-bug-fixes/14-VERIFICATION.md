---
phase: 14-bug-fixes
verified: 2026-03-16T12:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 14: Bug Fixes Verification Report

**Phase Goal:** Two anchor creation bugs are eliminated — the creation dialog name reliably lands on the node, and pressing "a" on a Dot produces a NoOp anchor
**Verified:** 2026-03-16T12:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                      | Status     | Evidence                                                                                                    |
|----|------------------------------------------------------------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------------------|
| 1  | Name typed in the anchor creation dialog is the name of the created anchor node on all acceptance paths    | VERIFIED   | `ColorPaletteDialog.accept()` at colors.py:258 reads `_name_edit.text()` into `chosen_name` before super() |
| 2  | `accept()` does not crash when `_name_edit` is None (no name field shown)                                  | VERIFIED   | Guard `if self._name_edit is not None` present at colors.py:259                                             |
| 3  | No scattered `chosen_name = self._name_edit.text()` blocks remain in `keyPressEvent` or `eventFilter`     | VERIFIED   | `grep` finds exactly 1 occurrence of that assignment — inside `accept()` only                               |
| 4  | `anchor.py create_anchor()` reads `dialog.chosen_name` after `dialog.exec_()` on both call sites          | VERIFIED   | anchor.py:291 and anchor.py:355 both read `chosen_name = dialog.chosen_name` after `exec_()`               |
| 5  | Pressing "a" on a selected Dot node calls `create_anchor()` (NoOp path), not `_offer_make_dot_anchor()`   | VERIFIED   | `anchor_shortcut()` at anchor.py:504-514 has no `elif` branch for Dot; Dot falls through to `elif selected` |
| 6  | `_offer_make_dot_anchor()` still exists but is marked deprecated                                          | VERIFIED   | anchor.py:482-484 — two-line deprecation comment before `def _offer_make_dot_anchor(dot_node):`            |
| 7  | All non-Dot dispatch paths in `anchor_shortcut()` behave identically to before (anchor→rename, none→pick) | VERIFIED   | `TestAnchorShortcutDotRouting` covers anchor, non-Dot, no-selection, multiple-nodes paths — all pass        |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact                                  | Expected                                                                                           | Status   | Details                                                                               |
|-------------------------------------------|----------------------------------------------------------------------------------------------------|----------|---------------------------------------------------------------------------------------|
| `colors.py`                               | `ColorPaletteDialog.accept()` override that reads `_name_edit.text()` into `chosen_name`          | VERIFIED | `def accept(self)` at line 258; guard + assignment + `super().accept()` present       |
| `tests/test_anchor_color_system.py`       | `TestColorPaletteDialogChosenNameCapturedOnAccept` class with at least two test methods            | VERIFIED | Class at line 1981; two methods at lines 1993 and 2015                                |
| `anchor.py`                               | `anchor_shortcut()` without Dot elif branch; `_offer_make_dot_anchor()` marked deprecated         | VERIFIED | Dot elif removed; deprecation comment at line 482; function retained at line 484      |
| `tests/test_dot_type_distinction.py`      | `TestAnchorShortcutDotRouting` class with tests for all five dispatch paths                        | VERIFIED | Class at line 914; five test methods at lines 935, 951, 964, 979, 989                |

### Key Link Verification

| From                                          | To                                   | Via                                                             | Status     | Details                                                                                  |
|-----------------------------------------------|--------------------------------------|-----------------------------------------------------------------|------------|------------------------------------------------------------------------------------------|
| `colors.py ColorPaletteDialog.accept()`       | `self.chosen_name`                   | `self._name_edit.text()` with `_name_edit is not None` guard   | WIRED      | colors.py:258-261 — assignment inside `accept()` body                                   |
| `anchor.py create_anchor()`                   | `colors.py ColorPaletteDialog.chosen_name` | `dialog.chosen_name` read after `dialog.exec_()`          | WIRED      | anchor.py:291 and :355 — both `create_anchor` call sites read `dialog.chosen_name`      |
| `anchor.py anchor_shortcut()` Dot path        | `anchor.py create_anchor()`          | `elif selected:` branch fires for Dot nodes after Dot elif removal | WIRED  | anchor.py:511 — `elif selected: create_anchor()` is now the Dot-node path               |
| `anchor.py anchor_shortcut()`                 | `_offer_make_dot_anchor()` (negated) | Branch removed — NOT called                                     | VERIFIED   | No reference to `_offer_make_dot_anchor` inside `anchor_shortcut()` body                |

### Requirements Coverage

| Requirement | Source Plan | Description                                                              | Status    | Evidence                                                                                      |
|-------------|-------------|--------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------------------------------|
| BUG-03      | 14-01-PLAN  | Name typed in anchor creation dialog reliably applied as anchor node's name | SATISFIED | `accept()` override captures name on all paths; 2 regression tests pass; anchor.py reads `chosen_name` |
| BUG-04      | 14-02-PLAN  | Pressing "a" on a Dot node creates a NoOp-based anchor                  | SATISFIED | Dot elif branch removed from `anchor_shortcut()`; 5 regression tests pass                    |

No orphaned requirements — only BUG-03 and BUG-04 are mapped to Phase 14 in REQUIREMENTS.md.

### Anti-Patterns Found

| File   | Line | Pattern                                | Severity | Impact                                                              |
|--------|------|----------------------------------------|----------|---------------------------------------------------------------------|
| anchor.py | 482 | Deprecation comment on live function | INFO     | Intentional — locked Phase 14 decision to retain `_offer_make_dot_anchor()` for reference |

No stubs, empty implementations, or TODO/FIXME/PLACEHOLDER patterns found in modified files.

### Test Suite Results

Full suite run using package-qualified imports (required by the project's stub-injection pattern in `tests/__init__.py`):

```
python3.11 -m unittest tests.test_anchor_color_system tests.test_dot_type_distinction \
    tests.test_anchor_navigation tests.test_cross_script_paste \
    tests.test_dot_anchor_name_sync tests.test_prefs

Ran 139 tests in 0.363s — OK
```

BUG-03 regression tests (2 tests): PASS
BUG-04 regression tests (5 tests): PASS
Full suite (139 tests): PASS

### Human Verification Required

None. All behaviors can be verified programmatically via unit tests and static analysis:

- The `accept()` chokepoint is structurally verified (code exists, guard present, calls `super()`)
- The `anchor_shortcut()` dispatch is verified by the five-branch `TestAnchorShortcutDotRouting` tests
- The wiring from `accept()` through `dialog.chosen_name` to anchor node naming is verified by static grep

The one area that cannot be tested without a live Nuke environment is the actual UI interaction (clicking a swatch, pressing Enter in the dialog). However, the unit tests use the same `accept()` code path that real UI interactions invoke, so structural coverage is complete.

### Commits Verified

| Commit    | Description                                                          |
|-----------|----------------------------------------------------------------------|
| `dd0aed6` | test(14-01): add failing tests for BUG-03 chosen_name capture on accept |
| `5c3f190` | feat(14-01): fix BUG-03 by adding ColorPaletteDialog.accept() override  |
| `0f05b24` | test(14-02): add failing test for anchor_shortcut() Dot routing          |
| `29343d5` | fix(14-02): remove Dot elif branch from anchor_shortcut() (BUG-04)       |

---

_Verified: 2026-03-16T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
