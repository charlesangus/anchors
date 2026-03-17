---
phase: 16-site-config
plan: 01
subsystem: testing
tags: [unittest, tdd, prefs, site-config, ANCHORS_SITE_CONFIG]

# Dependency graph
requires:
  - phase: 15.1-additional-preferences-requirements
    provides: naming_regex, naming_template, naming_demo_filename in prefs.py; publish() function; TestPublish class in test_prefs.py
provides:
  - TestSiteConfigLoading class (8 RED test methods) in tests/test_prefs.py
  - Updated test_publish_writes_to_given_path asserting ONLY naming fields in published JSON
  - RED baseline for plan 02 to turn GREEN
affects: 16-site-config plan 02 (prefs.py backend implementation)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Set ANCHORS_SITE_CONFIG in os.environ BEFORE calling _reload_prefs_with_temp_path so _load() reads it at import time"
    - "TDD RED scaffold: write tests against not-yet-existing attributes (_site_config, _user_naming_*, site_config_override) to establish meaningful failure baseline"

key-files:
  created: []
  modified:
    - tests/test_prefs.py

key-decisions:
  - "16-01: Noop tests (missing env var, corrupt file, missing file) pass GREEN even in RED phase — they test existing behavior that stays correct after Plan 02; the meaningful RED tests are the feature assertion tests (4 failing)"
  - "16-01: test_publish_writes_to_given_path updated to remove plugin_enabled/link_classes_paste_mode/custom_colors setup lines and assert their absence with assertNotIn; confirms publish() restriction target for Plan 02"

patterns-established:
  - "Pattern: _write_user_prefs() and _write_site_config() helpers in TestSiteConfigLoading for test fixture creation"
  - "Pattern: tearDown clears ANCHORS_SITE_CONFIG via os.environ.pop() to prevent test bleed-through"

requirements-completed: [SITE-01, SITE-02, SITE-03]

# Metrics
duration: 3min
completed: 2026-03-17
---

# Phase 16 Plan 01: Site Config TDD RED Scaffold Summary

**TDD RED baseline for site config: 8 new TestSiteConfigLoading tests + updated test_publish_writes_to_given_path assert ONLY naming fields — all fail before prefs.py changes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T06:48:26Z
- **Completed:** 2026-03-17T06:51:26Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `TestSiteConfigLoading` class with 8 test methods covering all SITE-01/02/03 behaviors
- Updated `TestPublish.test_publish_writes_to_given_path` to assert naming-only output and reject non-naming keys
- Confirmed 5 failing tests (4 FAIL + 1 ERROR) provide meaningful RED baseline; 12 pre-existing tests remain GREEN

## Task Commits

Each task was committed atomically:

1. **Tasks 1 + 2: TestSiteConfigLoading + updated TestPublish (RED scaffold)** - `98c74ee` (test)

**Plan metadata:** (docs commit to follow)

_Note: TDD tasks — RED phase only; no GREEN commit here._

## Files Created/Modified

- `/workspace/tests/test_prefs.py` - Added `TestSiteConfigLoading` class (8 test methods) after `TestPublish`; updated `test_publish_writes_to_given_path` to assert naming-only output

## Decisions Made

- Noop tests for missing/corrupt/absent env var pass in RED phase — this is correct because prefs.py already ignores ANCHORS_SITE_CONFIG entirely (never reads it), so user values are used by default. These tests will continue to pass after Plan 02 correctly implements silent fallback.
- `test_site_config_override_true_uses_user_values` also passes in RED because prefs currently doesn't apply site config values anyway — user value is always used. This is the expected noop semantics. Plan 02 will make this test exercise the actual override path.
- Combined Task 1 and Task 2 into a single commit as both modify the same file and represent the complete RED scaffold.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `pytest` not available in environment — used `python3.11 -m unittest` instead throughout. Tests run successfully via unittest discover.

## Next Phase Readiness

- RED baseline established: 5 failing tests define exactly what Plan 02 must implement
- Failing tests target: `_site_config` dict, `_user_naming_*` shadow vars, `site_config_override` attr, and publish() naming-only restriction
- Plan 02 (prefs.py backend) can now implement site config loading and turn these 5 tests GREEN

## Self-Check: PASSED

- tests/test_prefs.py: FOUND
- 16-01-SUMMARY.md: FOUND
- Commit 98c74ee: FOUND

---
*Phase: 16-site-config*
*Completed: 2026-03-17*
