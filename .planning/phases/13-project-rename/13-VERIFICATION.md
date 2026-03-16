---
phase: 13-project-rename
verified: 2026-03-15T21:00:00Z
status: gaps_found
score: 10/13 must-haves verified
gaps:
  - truth: "pytest tests/ passes in full with zero failures or errors"
    status: failed
    reason: "test_file_created_on_first_run_with_old_palette fails because _migrate_from_old_prefs_file() was added in Plan 01 but the test was not updated to patch OLD_PREFS_PATH in prefs.py. The real ~/.nuke/paste_hidden_prefs.json exists on disk and is copied to the temp anchors_prefs.json by the migration, overwriting the test's expected palette colors with defaults. Result: 1 failure, 131 passes."
    artifacts:
      - path: "tests/test_prefs.py"
        issue: "test_file_created_on_first_run_with_old_palette does not patch prefs.OLD_PREFS_PATH — the hardcoded real path ~/ .nuke/paste_hidden_prefs.json is found on disk and its contents (custom_colors=[]) overwrite the expected migrated palette colors"
      - path: "prefs.py"
        issue: "_migrate_from_old_prefs_file() uses a module-level hardcoded OLD_PREFS_PATH constant that is not patchable via constants module; the test only patches constants.PREFS_PATH and constants.USER_PALETTE_PATH"
    missing:
      - "tests/test_prefs.py: patch prefs.OLD_PREFS_PATH (or mock os.path.exists for OLD_PREFS_PATH) in test_file_created_on_first_run_with_old_palette to prevent the real file from being copied"

  - truth: "No unintended paste_hidden references remain in Python source files"
    status: failed
    reason: "Three source files outside the plan's declared scope still contain stale paste_hidden references. Two are functional (colors.py user-visible label; validation/validate_cross_script_paste.py broken import). One is a comment only (link.py)."
    artifacts:
      - path: "colors.py"
        issue: "Line 568: QtWidgets.QCheckBox(\"Enable paste_hidden plugin\") — user-visible UI label still carries old branding"
      - path: "validation/validate_cross_script_paste.py"
        issue: "Line 39: from paste_hidden import paste_hidden — broken import (module no longer exists). Also 7 other references to paste_hidden() function name and paste_hidden.copy_hidden() in docstrings/comments."
      - path: "link.py"
        issue: "Line 3 (module docstring): 'Neither anchor.py nor paste_hidden.py need to import from each other' — stale filename reference in a comment"
    missing:
      - "colors.py line 568: rename checkbox label from 'Enable paste_hidden plugin' to 'Enable anchors plugin'"
      - "validation/validate_cross_script_paste.py: update from paste_hidden import paste_hidden → from anchors import paste_anchors, update all paste_hidden() call sites to paste_anchors(), update comment/docstring references"
      - "link.py line 3: update 'paste_hidden.py' → 'anchors.py' in module docstring"
---

# Phase 13: Project Rename Verification Report

**Phase Goal:** All project references use `anchors` — source code, imports, tests, CI, and GitHub repo are consistent and working under the new name
**Verified:** 2026-03-15T21:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | paste_hidden.py no longer exists; anchors.py exists in its place | VERIFIED | `ls /workspace/paste_hidden.py` → not found; `ls /workspace/anchors.py` → exists |
| 2 | copy_hidden/paste_hidden functions renamed to copy_anchors/paste_anchors in anchors.py | VERIFIED | `grep def` confirms copy_anchors, cut_anchors, paste_anchors, paste_multiple_anchors, migrate_script all defined |
| 3 | constants.py uses anchors_* names for knobs and prefs path | VERIFIED | DOT_ANCHOR_KNOB_NAME='anchors_dot_anchor', DOT_TYPE_KNOB_NAME='anchors_dot_type', PREFS_PATH=anchors_prefs.json; USER_PALETTE_PATH intentionally unchanged |
| 4 | prefs.py auto-migrates paste_hidden_prefs.json to anchors_prefs.json on first load | VERIFIED | OLD_PREFS_PATH constant and _migrate_from_old_prefs_file() present; called in _load() before palette migration |
| 5 | menu.py imports anchors and calls anchors.copy_anchors / anchors.paste_anchors | VERIFIED | Line 5: import anchors; lines 11-13: addCommand uses anchors.copy_anchors, anchors.cut_anchors, anchors.paste_anchors |
| 6 | anchor.py weight file paths use anchors_ prefix | VERIFIED | Lines 463, 618: anchors_anchor_weights.json and anchors_anchor_navigate_weights.json |
| 7 | anchors.py exports migrate_script() at module level | VERIFIED | def migrate_script() at line 254 |
| 8 | pytest tests/ passes in full with zero failures or errors | FAILED | 131 pass, 1 failure: test_file_created_on_first_run_with_old_palette — test not updated to patch prefs.OLD_PREFS_PATH |
| 9 | release.yml builds anchors/ folder and produces anchors-{version}.zip | VERIFIED | mkdir anchors, zip produces anchors-${GITHUB_REF_NAME}.zip, files: anchors-${{ github.ref_name }}.zip |
| 10 | README.md installation references anchors folder and anchors_prefs filename | VERIFIED | "Copy the anchors folder", nuke.pluginAddPath('anchors'), migrate_script() documented |
| 11 | README.md Python API section documents migrate_script() under anchors module | VERIFIED | Lines 287-288: import anchors; anchors.migrate_script() with full migration section |
| 12 | GitHub repository accessible at anchors URL | VERIFIED | git remote: https://github.com/charlesangus/anchors.git |
| 13 | No unintended paste_hidden references remain in Python source, tests, CI, or README | FAILED | 3 files with stale references: colors.py (UI label), validation/validate_cross_script_paste.py (broken import + 7 stale references), link.py (comment) |

**Score:** 10/13 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `anchors.py` | Copy/paste logic under new module name | VERIFIED | All 5 exports present: copy_anchors, cut_anchors, paste_anchors, paste_multiple_anchors, migrate_script |
| `constants.py` | All renamed file paths and knob name constants | VERIFIED | anchors_prefs.json, anchors_dot_anchor, anchors_dot_type all present |
| `prefs.py` | Auto-migration from old prefs file name | VERIFIED | _migrate_from_old_prefs_file() defined and wired into _load() |
| `menu.py` | Updated imports and function references | VERIFIED | import anchors; all 5 command strings use anchors.* |
| `anchor.py` | Renamed weight file paths | VERIFIED | Both get_weights_file() methods use anchors_anchor_weights.json paths |

#### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_cross_script_paste.py` | Updated patch paths for anchors module | VERIFIED | from anchors import, patch('anchors.*') throughout; no paste_hidden references |
| `tests/test_dot_type_distinction.py` | Updated patch paths for anchors module | VERIFIED | patch('anchors.*') throughout; no paste_hidden references |
| `tests/test_anchor_color_system.py` | Updated string checks for import anchors pattern | VERIFIED | Checks assertNotIn('import anchors.menu', ...) as expected |
| `tests/test_prefs.py` | Updated file path strings for anchors_prefs.json | PARTIAL | anchors_prefs.json used correctly; but test_file_created_on_first_run_with_old_palette fails because OLD_PREFS_PATH is not patched |
| `.github/workflows/release.yml` | CI that builds anchors/ folder and anchors-{version}.zip | VERIFIED | mkdir anchors; cp anchors.py into anchors/; zip -r anchors-${GITHUB_REF_NAME}.zip |
| `README.md` | Updated installation and API documentation | VERIFIED | anchors folder, pluginAddPath('anchors'), migrate_script() section present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `menu.py` | `anchors.py` | import anchors | WIRED | Line 5: import anchors |
| `menu.py` | `anchors.copy_anchors / anchors.paste_anchors` | menu command strings | WIRED | Lines 11-13: addCommand calls reference anchors.copy_anchors, anchors.cut_anchors, anchors.paste_anchors |
| `prefs.py` | `constants.PREFS_PATH` | _load() / _migrate_from_old_prefs_file() | WIRED | anchors_prefs.json in PREFS_PATH; _migrate_from_old_prefs_file() checks OLD_PREFS_PATH and copies to PREFS_PATH |
| `tests/test_cross_script_paste.py` | `anchors module` | from anchors import / patch('anchors.*') | WIRED | from anchors import paste_anchors, _extract_display_name_from_fqnn; patch('anchors.nuke') etc. |
| `.github/workflows/release.yml` | `anchors.py` | cp anchors.py into anchors/ | WIRED | anchors.py appears in cp list; anchors/ is the build folder |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REN-01 | 13-01, 13-02 | Project renamed from paste_hidden to anchors across all source files, tests, CI, and config | PARTIAL | Source, tests, CI, README all updated. Three source files not in plan scope still contain stale references: colors.py (UI label), validation/validate_cross_script_paste.py (broken import), link.py (comment). Test suite has 1 failure introduced by the rename. |
| REN-02 | 13-02 | GitHub repo renamed from paste_hidden to anchors via gh | SATISFIED | git remote origin is https://github.com/charlesangus/anchors.git |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_prefs.py` | 102-135 | Test does not patch `prefs.OLD_PREFS_PATH` — real file on dev machine interferes | Blocker | 1 test failure; test_file_created_on_first_run_with_old_palette fails on any machine that has the real paste_hidden_prefs.json |
| `colors.py` | 568 | `"Enable paste_hidden plugin"` — old branding in user-visible UI | Warning | Users see old name in Preferences dialog; not a code error but inconsistent |
| `validation/validate_cross_script_paste.py` | 39 | `from paste_hidden import paste_hidden` — broken import to deleted module | Warning | Script non-functional; validation/ is not part of CI so does not block tests, but documents stale state |
| `link.py` | 3 | Module docstring references `paste_hidden.py` by old filename | Info | Documentation only, no functional impact |

---

### Human Verification Required

#### 1. GitHub Repository Accessibility

**Test:** Navigate to https://github.com/charlesangus/anchors
**Expected:** Repository loads under the anchors name with the anchors README
**Why human:** Cannot verify GitHub web UI programmatically; git remote URL is confirmed correct but HTTP redirect behavior is not verifiable here

#### 2. Preferences Dialog UI Label

**Test:** Launch Nuke with the anchors plugin installed; open Preferences via the anchors menu
**Expected:** Checkbox reads "Enable anchors plugin" (not "Enable paste_hidden plugin")
**Why human:** The colors.py label is a visual/runtime element; the stale text at line 568 is confirmed in code, but user confirmation of the scope decision (fix it or accept it) is needed

---

### Gaps Summary

Two gaps block full goal achievement:

**Gap 1 — Test failure (test_prefs.py):** The addition of `_migrate_from_old_prefs_file()` in Plan 01 introduced a new migration step that fires before `_migrate_from_old_palette()`. The test `test_file_created_on_first_run_with_old_palette` patches `constants.PREFS_PATH` and `constants.USER_PALETTE_PATH` but not `prefs.OLD_PREFS_PATH`. Because `~/.nuke/paste_hidden_prefs.json` actually exists on the developer's machine, the migration copies that file (which has `custom_colors: []`) to the temp prefs path before `_migrate_from_old_palette()` runs. The test then loads defaults instead of the expected palette colors. Fix: patch `prefs.OLD_PREFS_PATH` to a nonexistent path (or an empty temp file) in the test setup.

**Gap 2 — Stale source references (REN-01 scope):** Three files were not listed in either plan's `files_modified` and were not updated:
- `colors.py` line 568: user-visible UI checkbox label reads "Enable paste_hidden plugin" — user-facing string with old branding
- `validation/validate_cross_script_paste.py`: functional broken import `from paste_hidden import paste_hidden` plus 7 docstring/comment references to old function names — the script cannot run
- `link.py` line 3: comment only, lowest severity

The `validation/` directory is only run manually under Nuke so the broken import does not affect automated tests. The `colors.py` label is user-visible. Both were missed because the plans enumerated specific files and these were not included.

---

_Verified: 2026-03-15T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
