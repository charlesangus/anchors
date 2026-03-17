---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Foundations
status: executing
stopped_at: Completed 16-site-config-02-PLAN.md
last_updated: "2026-03-17T06:58:03.706Z"
last_activity: 2026-03-16 — Phase 14 Plan 02 complete; BUG-04 fixed, Dot elif removed from anchor_shortcut()
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 14
  completed_plans: 13
  percent: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Copy and paste must reconnect predictably — anchors provide stable, navigable references; hidden inputs reconnect to their source without ceremony.
**Current focus:** Phase 13 — Project Rename

## Current Position

Phase: 14 of 17 (Bug Fixes)
Plan: 02 complete — Phase 14 Plan 02 done
Status: In progress, Plan 02 complete
Last activity: 2026-03-16 — Phase 14 Plan 02 complete; BUG-04 fixed, Dot elif removed from anchor_shortcut()

Progress: [█░░░░░░░░░] 5%

## Performance Metrics

**Velocity:**
- Total plans completed: 1 (this milestone)
- Average duration: 4 min
- Total execution time: 4 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 13-project-rename | 1 | 4 min | 4 min |

*Updated after each plan completion*
| Phase 13-project-rename P02 | 15 | 2 tasks | 7 files |
| Phase 13-project-rename P03 | 12 | 2 tasks | 6 files |
| Phase 14-bug-fixes P01 | 4 | 2 tasks | 2 files |
| Phase 14-bug-fixes P02 | 3 | 2 tasks | 2 files |
| Phase 15-anchor-naming P01 | 3 | 2 tasks | 2 files |
| Phase 15-anchor-naming P02 | 4 | 2 tasks | 3 files |
| Phase 15-anchor-naming P03 | 4 | 2 tasks | 1 files |
| Phase 15.1-additional-preferences-requirements P01 | 2 | 2 tasks | 2 files |
| Phase 15.1-additional-preferences-requirements P02 | 2 | 2 tasks | 1 files |
| Phase 15.1-additional-preferences-requirements P03 | 3 | 2 tasks | 1 files |
| Phase 16-site-config P01 | 3 | 2 tasks | 1 files |
| Phase 16-site-config P02 | 3 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

All decisions logged in PROJECT.md Key Decisions table.

Recent decisions relevant to v1.3:
- Phase 13 first: rename is foundational — all subsequent file references use `anchors`
- Phase 17 depends on Phase 13 (not 16): public API is independent of site config; only needs rename to land
- Phase 16 depends on Phase 15: site config locks naming fields, so naming prefs must exist first
- 13-01: USER_PALETTE_PATH left as paste_hidden_user_palette.json — legacy source path for old-palette migration, not a primary path
- 13-01: migrate_script() hardcodes old knob name strings as literals so it works before and after constants.py rename
- 13-01: DOT_ANCHOR_KNOB_NAME and DOT_TYPE_KNOB_NAME values changed to anchors_* — existing .nk files require migrate_script()
- [Phase 13-project-rename]: 13-02: test patches updated to anchors.* module paths; paste_hidden_user_palette.json kept in tests (legacy palette source)
- [Phase 13-project-rename]: 13-03: OLD_PREFS_PATH moved to constants.py — plan's patch-after-import approach cannot work because _load() runs at import time; all patchable file paths now live in constants.py
- [Phase 14-bug-fixes]: accept() override is single chokepoint for chosen_name capture in ColorPaletteDialog
- [Phase 14-bug-fixes]: BUG-04: removed Dot elif branch from anchor_shortcut() — _offer_make_dot_anchor() deprecated, Dot nodes now use create_anchor() via NoOp path
- [Phase 15-anchor-naming]: 15-01: Wave 0 TDD scaffold — frame-token stripping tests verify end-to-end suggest_anchor_name() behavior; prefs round-trip tests use temp-path reload pattern
- [Phase 15-anchor-naming]: 15-02: _FRAME_TOKEN_PATTERN \b word boundary removed — # is non-word char so \b after #{1,} never fires; natural token delimiters suffice
- [Phase 15-anchor-naming]: 15-02: test_strips_percent04d and test_no_token_unchanged expected values corrected from plate_v003 to plate — {name} group from (?P<name>.+)_v\d+ yields 'plate'; Wave 0 scaffold had incorrect assertions
- [Phase 15-anchor-naming]: 15-03: auto_advance=true — Task 2 human-verify checkpoint auto-approved; no UI runtime available in this environment
- [Phase 15.1-additional-preferences-requirements]: publish() guards os.path.dirname result before os.makedirs — bare filenames return '' which would fail
- [Phase 15.1-additional-preferences-requirements]: naming_demo_filename defaults to 'plate_v003.exr' — concrete example that exercises frame-token stripping in suggest_anchor_name()
- [Phase 15.1-additional-preferences-requirements]: QShortcut Ctrl+Z scoped to dialog for Reset undo — QLineEdit handles per-keystroke undo natively
- [Phase 15.1-additional-preferences-requirements]: _publish_path read from ANCHORS_SITE_CONFIG at __init__ time, not re-checked dynamically
- [Phase 15.1-additional-preferences-requirements]: _on_publish_naming flushes current field values before calling publish() so published file reflects live UI state
- [Phase 15.1-additional-preferences-requirements]: auto_advance=true — Task 2 human-verify checkpoint auto-approved; no UI runtime available in this environment
- [Phase 15.1-additional-preferences-requirements]: Collapsible Advanced section: flat QPushButton + QWidget.setVisible(False) default; _on_toggle_advanced_naming flips visibility and swaps triangle in button text
- [Phase 16-site-config]: 16-01: Noop tests pass GREEN in RED phase — prefs doesn't read ANCHORS_SITE_CONFIG yet so user values used by default; meaningful RED tests are the feature assertion tests (4 failing)
- [Phase 16-site-config]: 16-01: test_publish_writes_to_given_path updated to remove non-naming field setup and add assertNotIn for plugin_enabled/link_classes_paste_mode/custom_colors — defines publish() naming-only restriction target for Plan 02
- [Phase 16-site-config]: 16-02: save() uses _user_naming_* shadow vars — effective naming_* vars are never written to anchors_prefs.json when site config is active
- [Phase 16-site-config]: 16-02: _load_site_config() called before early return in _load() to ensure site config applies even on first run (no prefs file)

### Roadmap Evolution

- Phase 15.1 inserted after Phase 15: additional preferences requirements (URGENT)

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-17T06:57:57.956Z
Stopped at: Completed 16-site-config-02-PLAN.md
Resume file: None
