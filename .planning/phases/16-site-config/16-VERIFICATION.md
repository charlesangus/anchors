---
phase: 16-site-config
verified: 2026-03-17T07:30:00Z
status: human_needed
score: 4/4 success criteria verified (automated); 1/1 human checkpoint pending
re_verification: false
human_verification:
  - test: "Open PrefsDialog in Nuke with ANCHORS_SITE_CONFIG unset — confirm all three naming fields are editable, no Override checkbox visible"
    expected: "Regex, Template, Demo Filename all editable; no Override Site Config checkbox in Advanced section"
    why_human: "QWidget.setEnabled() and QWidget.setVisible() require a live Qt application to observe rendered state"
  - test: "Set ANCHORS_SITE_CONFIG to a valid JSON site config, restart plugin, open PrefsDialog Advanced section — confirm naming fields are greyed out, Override Site Config checkbox is visible and unchecked"
    expected: "Three naming fields disabled (grey); Override checkbox visible and unchecked"
    why_human: "UI disable/show state cannot be verified without a live Nuke session"
  - test: "Check the Override Site Config checkbox — confirm all three naming fields become editable"
    expected: "Fields re-enable immediately on checkbox check"
    why_human: "Requires live Qt event loop to confirm toggled signal fires and setEnabled takes effect"
  - test: "Uncheck Override Site Config — confirm fields grey out again"
    expected: "Fields re-disable on uncheck"
    why_human: "Requires live Qt interaction"
  - test: "Click OK with override checked, reopen Preferences — confirm checkbox is still checked and fields remain editable"
    expected: "site_config_override=True persists through save() and reload; checkbox re-checked on dialog reopen"
    why_human: "Requires full Nuke session with disk I/O and UI re-initialization"
  - test: "Confirm greyed-out naming fields show user's own saved values (not site config values)"
    expected: "User's saved regex/template/demo_filename shown in disabled fields, not admin values"
    why_human: "Visual content of disabled QLineEdit widgets requires live UI"
---

# Phase 16: Site Config Verification Report

**Phase Goal:** Implement site config support — a two-layer value system where admin-defined site config (JSON file path from env var) overrides user naming preferences, with UI controls for field locking and override.
**Verified:** 2026-03-17T07:30:00Z
**Status:** human_needed — all automated checks PASS; UI behavior requires human verification in live Nuke session
**Re-verification:** No — initial verification

## Goal Achievement

### Success Criteria (from ROADMAP.md)

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | When `ANCHORS_SITE_CONFIG` env var points to a valid config file, its values are loaded and applied to naming prefs on startup | VERIFIED | `test_site_config_values_applied_as_effective_values` PASSES — `prefs.naming_regex` equals site config value after reload |
| 2 | Fields locked by site config appear disabled in PrefsDialog and cannot be changed without using the override checkbox | HUMAN NEEDED | `_update_naming_fields_lock_state()` calls `setEnabled(False)` on all three QLineEdits when `_site_config` is non-empty — verified in code; visual state requires live Nuke session |
| 3 | Checking "Override Site Config" in PrefsDialog re-enables locked fields so the user can change them for their session | HUMAN NEEDED | `_on_override_site_config_toggled()` sets `_local_site_config_override = True` and calls `_update_naming_fields_lock_state()` which sets `fields_are_editable = True` — verified in code; runtime behavior requires human |
| 4 | When `ANCHORS_SITE_CONFIG` is unset or the path is invalid, the plugin loads normally with no error | VERIFIED | `test_site_config_missing_env_var_is_silent_noop`, `test_site_config_corrupt_file_is_silent_noop`, `test_site_config_missing_file_path_is_silent_noop` all PASS |

**Score:** 4/4 success criteria have implementation evidence; 2 of the 4 also have passing automated tests; 2 require human sign-off for the UI layer.

### Observable Truths (from plan must_haves)

#### Plan 01 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Failing tests exist for site config loading (SITE-01) | VERIFIED | `TestSiteConfigLoading` class at line 534 in tests/test_prefs.py — 8 test methods present and all GREEN after plan 02 |
| 2 | Failing tests exist for field locking and publish naming-only behavior (SITE-02) | VERIFIED | `test_publish_writes_to_given_path` updated with `assertNotIn` checks at lines 473-483; test PASSES |
| 3 | Failing tests exist for override flag persistence and round-trip (SITE-03) | VERIFIED | `test_site_config_override_round_trip` at line 722 PASSES |
| 4 | test_publish_writes_to_given_path updated to expect ONLY naming keys | VERIFIED | Lines 473-483: `assertNotIn('plugin_enabled', data)`, `assertNotIn('link_classes_paste_mode', data)`, `assertNotIn('custom_colors', data)` present |

#### Plan 02 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | prefs._load() reads ANCHORS_SITE_CONFIG and populates _site_config dict | VERIFIED | `_load_site_config()` called from `_load()` at line 114; reads `os.environ.get("ANCHORS_SITE_CONFIG")` |
| 2 | Site config values override effective naming vars when override is off | VERIFIED | `_apply_effective_naming_values()` at line 140: `naming_regex = _site_config.get('naming_regex', _user_naming_regex)` when `not site_config_override` |
| 3 | User's own naming values are preserved in _user_naming_* shadow vars | VERIFIED | Lines 111-113: shadow vars copied from loaded values before `_load_site_config()` runs; `test_site_config_locks_fields_user_values_preserved_in_shadow_vars` PASSES |
| 4 | prefs.save() writes _user_naming_* values (never site config values) | VERIFIED | Lines 170-172: `'naming_regex': _user_naming_regex`, `'naming_template': _user_naming_template`, `'naming_demo_filename': _user_naming_demo_filename` |
| 5 | prefs.publish() writes ONLY naming fields (not plugin_enabled etc.) | VERIFIED | Lines 192-198: json.dump contains only `naming_regex`, `naming_template`, `naming_demo_filename`; `test_publish_writes_to_given_path` PASSES |
| 6 | Unset/missing/corrupt ANCHORS_SITE_CONFIG is a silent no-op | VERIFIED | `_load_site_config()` catches `OSError, ValueError, json.JSONDecodeError` and returns silently; 3 noop tests PASS |

#### Plan 03 Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PrefsDialog seeds _local_naming_* from _user_naming_* shadow vars, not effective vars | VERIFIED | Line 555: `self._local_naming_regex = prefs_module._user_naming_regex`; line 556: `_user_naming_template`; line 557: `_user_naming_demo_filename` |
| 2 | Naming fields are disabled when site config is active and override is off | CODE VERIFIED | `_update_naming_fields_lock_state()` lines 763-766: `fields_are_editable = (not site_config_is_active) or self._local_site_config_override`; calls `setEnabled(fields_are_editable)` on all three fields |
| 3 | Override Site Config checkbox appears only when site config is active | CODE VERIFIED | Line 768: `self._override_site_config_checkbox.setVisible(site_config_is_active)` |
| 4 | Checking override re-enables the three naming fields | CODE VERIFIED | `_on_override_site_config_toggled()` line 776: sets `_local_site_config_override = is_checked`; calls `_update_naming_fields_lock_state()` which recomputes `fields_are_editable` |
| 5 | Unchecking override re-disables the three naming fields | CODE VERIFIED | Same `_on_override_site_config_toggled()` path — `is_checked=False` causes `fields_are_editable = False` when site config active |
| 6 | _on_accept() updates _user_naming_* shadow vars and calls _apply_effective_naming_values() | VERIFIED | Lines 1061-1066: flushes `_user_naming_regex/template/demo_filename`, sets `site_config_override`, calls `_apply_effective_naming_values()` |
| 7 | _on_publish_naming() flushes editable field values before publishing | VERIFIED | Lines 825-829: flushes `_user_naming_*`, calls `_apply_effective_naming_values()`, then `publish()` |
| 8 | Live preview and validity indicator remain functional even when fields are disabled | CODE VERIFIED | `_update_naming_validity_indicator()` reads `.text()` from QLineEdit — `QLineEdit.text()` works regardless of `setEnabled` state; no changes needed and none made |

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `tests/test_prefs.py` | `TestSiteConfigLoading` class (8 tests) + updated `TestPublish.test_publish_writes_to_given_path` | VERIFIED | Class at line 534; 8 methods confirmed; 21/21 test_prefs tests GREEN |
| `prefs.py` | `_site_config`, `_user_naming_*`, `site_config_override`, `_load_site_config()`, `_apply_effective_naming_values()`, `_LOCKABLE_NAMING_FIELDS` | VERIFIED | All vars at lines 26-34; functions at lines 117 and 140; save() and publish() correct |
| `colors.py` | `PrefsDialog` with `_override_site_config_checkbox`, `_update_naming_fields_lock_state()`, `_on_override_site_config_toggled()` | VERIFIED | `_override_site_config_checkbox` at line 651; `_update_naming_fields_lock_state()` at line 753; `_on_override_site_config_toggled()` at line 770 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_prefs.py` | `prefs._site_config` | `prefs_module._site_config after reload` | VERIFIED | Test at line 677 reads `prefs_module._site_config` indirectly through effective var assertion; attribute exists on live module |
| `tests/test_prefs.py` | `prefs._user_naming_regex` | `shadow var isolation test` | VERIFIED | Line 695: `prefs_module._user_naming_regex` directly asserted |
| `prefs._load()` | `prefs._load_site_config()` | `called at end of _load()` | VERIFIED | Line 114: `_load_site_config()` called; also called at line 87 before early-return path |
| `prefs._apply_effective_naming_values()` | `prefs.naming_regex` | `global assignment based on override state` | VERIFIED | Line 148: `naming_regex = _site_config.get('naming_regex', _user_naming_regex)` |
| `prefs.save()` | `prefs._user_naming_regex` | `JSON key written from shadow var` | VERIFIED | Line 170: `'naming_regex': _user_naming_regex` |
| `PrefsDialog.__init__()` | `prefs._user_naming_regex` | `self._local_naming_regex = prefs_module._user_naming_regex` | VERIFIED | Line 555 confirmed |
| `_on_override_site_config_toggled()` | `_update_naming_fields_lock_state()` | `toggled signal connect + direct call` | VERIFIED | Line 653: signal connected; line 777: direct call |
| `_on_accept()` | `prefs._apply_effective_naming_values()` | `direct call after flushing shadow vars` | VERIFIED | Line 1066 confirmed |

### Critical Path Verification: _load_site_config() Called in All Code Paths

The plan noted a critical pitfall: early-return path in `_load()` must also call `_load_site_config()`.

- **Normal path** (prefs file exists): `_load_site_config()` called at line 114 — the final statement of `_load()` after the try/except block.
- **Early-return path** (no prefs file, no old prefs either): `_load_site_config()` called at line 87, immediately before `return`.

Both paths confirmed. The pitfall was handled correctly.

### Requirements Coverage

| Requirement | Description | Plans | Status | Evidence |
|-------------|-------------|-------|--------|----------|
| SITE-01 | Site-level config file path resolved from `ANCHORS_SITE_CONFIG` env var | 16-01, 16-02 | SATISFIED | `_load_site_config()` reads `os.environ.get("ANCHORS_SITE_CONFIG")`; 4 noop + 4 feature tests PASS |
| SITE-02 | Site config can set and lock user-configurable settings (naming fields) | 16-01, 16-02, 16-03 | SATISFIED (automated) + HUMAN NEEDED (UI layer) | Backend: `_apply_effective_naming_values()` locks effective vars; UI: `setEnabled(False)` on fields when locked — requires human confirmation |
| SITE-03 | "Override Site Config" checkbox in PrefsDialog re-enables individual locked fields | 16-02, 16-03 | SATISFIED (automated) + HUMAN NEEDED (UI layer) | `site_config_override` round-trip test PASSES; UI toggle behavior requires human confirmation |

No orphaned requirements — all three SITE-0x IDs appear in plan frontmatter and are accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `colors.py` | 29 | `return []` | INFO | Not a stub — legitimate guard for `nuke.toNode("preferences") is None` when running outside Nuke; pre-existing code, not Phase 16 |

No blockers or warnings found in Phase 16 modified files.

### Test Suite Results

All tests run via `python3.11 -m unittest`:

- **tests/test_prefs.py**: 21/21 PASS (includes all 8 `TestSiteConfigLoading` methods + updated `test_publish_writes_to_given_path`)
- **tests/test_anchor_naming.py**: 13/13 PASS (no regression in naming layer)

Pre-existing known issue (not caused by Phase 16): `test_anchor_color_system.py` fails with `ImportError: No module named 'nuke'` — colors.py imports nuke at module level; no nuke stub available in the test environment. This failure pre-dates Phase 16 and is out of scope.

### Human Verification Required

The plan 03 human checkpoint (Task 2) was auto-approved by the executor due to no live Nuke UI being available in the CI environment. The following scenarios require human confirmation in an actual Nuke session:

#### 1. Normal Operation (No Site Config)

**Test:** Ensure `ANCHORS_SITE_CONFIG` is not set. Open Preferences dialog. Expand "Advanced" section.
**Expected:** All three naming fields (Regex, Template, Demo Filename) are editable (white background, not greyed). No "Override Site Config" checkbox is visible anywhere in the dialog.
**Why human:** `QWidget.setVisible(False)` and `QWidget.setEnabled(True)` require a live Qt application to confirm rendered appearance.

#### 2. Fields Lock When Site Config Active

**Test:** Create a temp JSON: `{"naming_regex": "(?P<shot>.+)_v\\d+", "naming_template": "{shot}"}`. Set `ANCHORS_SITE_CONFIG=/path/to/temp.json` and restart. Open Preferences → expand Advanced.
**Expected:** Regex and Template fields are greyed out (disabled). Demo Filename field is also greyed out. "Override Site Config" checkbox is visible and unchecked. The greyed fields show the user's own saved values (not the admin values).
**Why human:** Visual disabled state, checkbox visibility, and field content need live UI observation.

#### 3. Override Checkbox Re-enables Fields

**Test:** With site config active, click the "Override Site Config" checkbox.
**Expected:** All three naming fields immediately become editable (no longer greyed).
**Why human:** Requires live Qt event loop to confirm `toggled` signal fires and `setEnabled(True)` takes visual effect.

#### 4. Unchecking Override Re-locks Fields

**Test:** Uncheck the "Override Site Config" checkbox.
**Expected:** All three naming fields grey out again.
**Why human:** Live Qt interaction required.

#### 5. Override Persists After OK

**Test:** With site config active, check "Override Site Config", click OK. Reopen Preferences → expand Advanced.
**Expected:** "Override Site Config" checkbox is still checked. Fields are editable.
**Why human:** Requires full Nuke session with disk I/O (`save()`) and fresh dialog initialization confirming `_local_site_config_override` seeds from `prefs.site_config_override = True`.

### Gaps Summary

No gaps found. All automated checks pass. The only remaining items are the six human verification scenarios listed above, which require a live Nuke session with a Qt environment. The underlying code implementing each behavior has been confirmed present, substantive, and correctly wired.

---

_Verified: 2026-03-17T07:30:00Z_
_Verifier: Claude (gsd-verifier)_
