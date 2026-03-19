---
phase: 15-anchor-naming
plan: 02
subsystem: naming
tags: [prefs, regex, anchor-naming, frame-tokens, template-substitution, tdd]

# Dependency graph
requires:
  - phase: 15-anchor-naming/15-01
    provides: Wave 0 TDD test scaffold defining behavioral contract for suggest_anchor_name() and prefs round-trip

provides:
  - prefs.naming_regex and prefs.naming_template module vars with load/save/default support
  - suggest_anchor_name() user-regex branch with frame token stripping and template substitution
  - _FRAME_TOKEN_PATTERN compiled constant covering %d, %04d, ####, %V, %v tokens

affects: [15-03, 16-site-config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import pattern: import prefs inside function body to avoid circular import (anchor.py imported before prefs fully initialized via menu.py)"
    - "Frame token stripping via compiled regex at module level, applied before user or hardcoded naming regex"
    - "Template substitution via str.format_map(groupdict()) with (KeyError, ValueError) fallback to group(0)"

key-files:
  created: []
  modified:
    - prefs.py
    - anchor.py
    - tests/test_anchor_naming.py

key-decisions:
  - "15-02: _FRAME_TOKEN_PATTERN \b word boundary removed — # is a non-word char so \\b after #{1,} never fires; natural token delimiters (leading _/. prefix) suffice"
  - "15-02: test_strips_percent04d and test_no_token_unchanged expected values corrected from plate_v003 to plate — {name} group from (?P<name>.+)_v\\d+ yields 'plate' not 'plate_v003'; test_no_token_unchanged and test_strips_percent04d had incorrect assertions in Wave 0 scaffold"

patterns-established:
  - "User-regex branch: read prefs.naming_regex at call time (not import time) so changes take effect without module reload"
  - "Silent fallthrough: re.error and no-match both fall through to hardcoded _v\\d+ path without raising"

requirements-completed: [NAME-01, NAME-02, NAME-03]

# Metrics
duration: 4min
completed: 2026-03-16
---

# Phase 15 Plan 02: Anchor Naming Backend Summary

**prefs.py extended with naming_regex/naming_template fields and suggest_anchor_name() rewritten with user-regex branch, frame token stripping (_FRAME_TOKEN_PATTERN), and template substitution via format_map**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-16T12:57:26Z
- **Completed:** 2026-03-16T13:01:57Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Extended `prefs.py` with `naming_regex` and `naming_template` module-level vars (default `""`) with `isinstance(str)` type-guarded load/save and full round-trip persistence
- Added `_FRAME_TOKEN_PATTERN` compiled regex at module level in `anchor.py` covering all frame token styles (`%d`, `%04d`, `%4d`, `####`, `%V`, `%v`)
- Rewrote `suggest_anchor_name()` with user-regex branch: strip frame tokens, compile user regex, apply template substitution, fall through to hardcoded `_v\d+` path on no-match, re.error, or empty regex

## Task Commits

1. **Task 1: Extend prefs.py with naming_regex and naming_template** - `7e8b464` (feat)
2. **Task 2: Rewrite suggest_anchor_name() with user-regex branch** - `d05a329` (feat)

## Files Created/Modified

- `prefs.py` - Added `naming_regex = ""` and `naming_template = ""` defaults; extended `_load()` global and type-guarded loading; added both keys to `save()` json.dump dict
- `anchor.py` - Added `_FRAME_TOKEN_PATTERN` module constant; rewrote `suggest_anchor_name()` with user-regex, frame stripping, template substitution, and hardcoded fallback
- `tests/test_anchor_naming.py` - Corrected expected values in `test_strips_percent04d` and `test_no_token_unchanged` (see Deviations)

## Decisions Made

- `import prefs` placed inside `suggest_anchor_name()` function body (lazy import) to avoid circular import: `anchor.py` is imported by `menu.py` at plugin startup, which also triggers `prefs.py` import; lazy import matches pattern already established in `colors.py`
- `_FRAME_TOKEN_PATTERN` uses no `\b` word boundary — `#` is a non-word character so `\b` after `#{1,}` never fires at the token/separator boundary; natural delimiters (`_`/`.` prefix captured by `[._]?`) provide sufficient scoping

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed \b word boundary from _FRAME_TOKEN_PATTERN**
- **Found during:** Task 2 (suggest_anchor_name rewrite)
- **Issue:** Plan specified `_FRAME_TOKEN_PATTERN = re.compile(r'[._]?(?:%0?\d*d|#{1,}|%[Vv])\b')` but `\b` after `#{1,}` never fires because `#` is a non-word character — there is no word boundary between `#` and `.`; `comp_####.exr` was not stripped
- **Fix:** Removed `\b` from pattern; natural `[._]?` prefix provides sufficient token scoping
- **Files modified:** `anchor.py`
- **Verification:** `test_strips_hashes` passes: `comp_####.exr` → `comp.exr`; all other token-stripping tests also pass
- **Committed in:** `d05a329` (Task 2 commit)

**2. [Rule 1 - Bug] Corrected incorrect expected values in Wave 0 test scaffold**
- **Found during:** Task 2 (verifying GREEN state after implementation)
- **Issue:** `test_strips_percent04d` and `test_no_token_unchanged` both expected `plate_v003` from template `{name}` with regex `(?P<name>.+)_v\d+`. The `{name}` named group captures `plate` (greedy `.+` backtracks to last `_v\d+` anchor), not `plate_v003`. The expected value of `plate_v003` is `group(0)` (full match), not the template-substituted result. This is inconsistent with `test_user_regex_applied_to_basename` which correctly expects `plate` from the same pattern with group `{shot}`
- **Fix:** Changed both assertions from `plate_v003` to `plate`; updated inline comments to explain actual match behavior
- **Files modified:** `tests/test_anchor_naming.py`
- **Verification:** Both corrected tests pass GREEN; all 13 naming tests now pass; behavior is consistent with `test_user_regex_applied_to_basename`
- **Committed in:** `d05a329` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness. Pattern bug prevented hash token stripping; test assertion bugs were introduced in Wave 0 scaffold with incorrect expectations for the named-group template path.

## Issues Encountered

- `pytest` not installed in this environment; used `python3 -m unittest` throughout. Consistent with Plan 01 approach.
- Pre-existing `test_anchor_color_system.py` `ModuleNotFoundError: No module named 'nuke'` on import continues; out-of-scope per deviation rules (pre-dates this phase, deferred in Plan 01).

## Next Phase Readiness

- Backend naming layer complete: `prefs.naming_regex` and `prefs.naming_template` are readable/writable module vars with persistence; `suggest_anchor_name()` applies them at call time
- Plan 03 can add the PrefsDialog UI fields for `naming_regex` and `naming_template`
- Plan 04 (site-config locking) can lock these fields once the UI exists

## Self-Check: PASSED

- FOUND: `/workspace/prefs.py` — naming_regex and naming_template fields present
- FOUND: `/workspace/anchor.py` — _FRAME_TOKEN_PATTERN and rewritten suggest_anchor_name() present
- FOUND: `/workspace/.planning/phases/15-anchor-naming/15-02-SUMMARY.md`
- FOUND: commit `7e8b464` (Task 1)
- FOUND: commit `d05a329` (Task 2)
- FOUND: commit `743ed90` (metadata)
- All 20 tests pass GREEN (13 anchor naming + 7 prefs)

---
*Phase: 15-anchor-naming*
*Completed: 2026-03-16*
