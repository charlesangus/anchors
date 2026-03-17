---
phase: 16-site-config
plan: 02
subsystem: prefs
tags: [prefs, site-config, tdd, ANCHORS_SITE_CONFIG, shadow-vars]

# Dependency graph
requires:
  - phase: 16-site-config
    plan: 01
    provides: TestSiteConfigLoading RED scaffold; updated test_publish_writes_to_given_path
provides:
  - _site_config dict in prefs.py
  - _user_naming_* shadow vars in prefs.py
  - site_config_override bool in prefs.py
  - _load_site_config() function in prefs.py
  - _apply_effective_naming_values() function in prefs.py
  - save() writing shadow vars (not effective vars)
  - publish() writing only naming fields (sparse site config format)
affects:
  - Any caller that reads prefs.naming_regex/template/demo_filename — now receives effective (admin-merged) value
  - colors.py PrefsDialog (Phase 16 Plan 03 will add override checkbox UI)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-layer prefs value system: _site_config (admin layer) + _user_naming_* (user layer) + naming_* (merged effective layer)"
    - "Shadow var pattern: save() reads _user_naming_* to preserve user values even when site config overrides effective vars"
    - "_load_site_config() called in all _load() code paths including early-return path (before save(); return)"

key-files:
  created: []
  modified:
    - prefs.py

key-decisions:
  - "16-02: save() uses _user_naming_* shadow vars — effective naming_* vars are never written to anchors_prefs.json when site config is active"
  - "16-02: _load_site_config() called before early return in _load() to ensure site config applies even on first run (no prefs file)"
  - "16-02: Pre-existing naming round-trip tests updated to set _user_naming_* shadow vars (not effective vars) since save() now reads shadows; this is the correct behavior after Plan 02"
  - "16-02: test_publish_creates_parent_directories updated to assertIn naming_regex (not plugin_enabled) — consistent with plan-defined publish() naming-only restriction"

requirements-completed: [SITE-01, SITE-02]

# Metrics
duration: 3min
completed: 2026-03-17
---

# Phase 16 Plan 02: Site Config Backend Implementation Summary

**Two-layer prefs value system implemented: _site_config admin dict, _user_naming_* shadow vars, _load_site_config() + _apply_effective_naming_values() functions — all 21 TestSiteConfigLoading + TestPublish tests GREEN**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T06:54:11Z
- **Completed:** 2026-03-17T06:56:48Z
- **Tasks:** 2
- **Files modified:** 2 (prefs.py, tests/test_prefs.py)

## Accomplishments

- Added `site_config_override`, `_site_config`, `_user_naming_*` shadow vars, `_LOCKABLE_NAMING_FIELDS` to prefs.py module level
- Implemented `_load_site_config()`: reads `ANCHORS_SITE_CONFIG` env var, parses JSON, populates `_site_config` dict, silent no-op on all failure modes
- Implemented `_apply_effective_naming_values()`: applies site config or user values to effective module-level naming vars based on `site_config_override` state
- Extended `_load()`: declares new globals, loads `site_config_override` from JSON, copies naming values to shadow vars, calls `_load_site_config()` in all code paths (including early-return path)
- Updated `save()`: writes `_user_naming_*` shadow vars (not effective `naming_*` vars), adds `site_config_override` field
- Updated `publish()`: writes only `naming_regex`, `naming_template`, `naming_demo_filename` — sparse site config format
- Fixed 3 pre-existing tests whose assertions reflected old save()/publish() behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add site config infrastructure + GREEN tests** — `1549b69` (feat)
2. **Task 2: Full suite verification** — no files changed (pure verification)

## Files Created/Modified

- `/workspace/prefs.py` — two-layer value system: site config dict, shadow vars, _load_site_config(), _apply_effective_naming_values(), save() + publish() updated

## Decisions Made

- `save()` reads `_user_naming_*` shadow vars — effective `naming_*` vars are never persisted when site config is active; this is the invariant that prevents user prefs poisoning
- `_load_site_config()` called before the early-return `return` in `_load()` (first-run path with no prefs file) to ensure site config applies even before a prefs file is written
- Three pre-existing naming round-trip tests updated to set `_user_naming_*` shadow vars rather than effective `naming_*` vars — they previously tested that save() persisted what was in `naming_regex` directly, which is now the shadow var's job
- `test_publish_creates_parent_directories` assertion changed from `plugin_enabled` to `naming_regex` to match the plan-mandated naming-only publish() output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing naming round-trip tests used wrong var after save() refactor**
- **Found during:** Task 1 verification
- **Issue:** `test_naming_fields_written_to_prefs_file` and `test_naming_demo_filename_round_trip` set `prefs_module.naming_regex = ...` then checked the saved JSON; after Plan 02 `save()` reads `_user_naming_regex` not `naming_regex`, so the tests always saw the default value
- **Fix:** Updated both tests to set `prefs_module._user_naming_regex` (and `_user_naming_demo_filename`) — the shadow vars that `save()` now reads
- **Files modified:** tests/test_prefs.py
- **Commit:** 1549b69

**2. [Rule 1 - Bug] test_publish_creates_parent_directories asserted plugin_enabled in sparse output**
- **Found during:** Task 1 verification
- **Issue:** Test asserted `assertIn('plugin_enabled', data)` but `publish()` now writes naming-only fields per plan requirement
- **Fix:** Changed assertion to `assertIn('naming_regex', data)` — correct for sparse site config format
- **Files modified:** tests/test_prefs.py
- **Commit:** 1549b69

## Issues Encountered

- `pytest` not available in environment — used `python3.11 -m unittest` throughout (same as Plan 01)
- Pre-existing `test_anchor_color_system` fails with `ImportError: No module named 'nuke'` — this failure exists before Plan 02 changes and is out of scope (colors.py imports nuke at module level; no nuke stub in that test file)

## Full Test Suite Results

- **tests/test_prefs.py**: 21/21 PASS
- **tests/test_anchor_naming.py**: 13/13 PASS
- **tests/test_anchor_color_system.py**: 1 pre-existing ImportError (out of scope — nuke not available)
- **Total**: 101 tests run, 0 failures, 1 pre-existing error (unrelated to this plan)

## Self-Check: PASSED

- prefs.py: FOUND with _site_config, _user_naming_*, site_config_override, _load_site_config(), _apply_effective_naming_values()
- 16-02-SUMMARY.md: FOUND
- Commit 1549b69: FOUND

---
*Phase: 16-site-config*
*Completed: 2026-03-17*
