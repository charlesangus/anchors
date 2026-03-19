# Roadmap: paste_hidden → anchors

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-03-10)
- ✅ **v1.1 Polish** — Phases 6-7 (shipped 2026-03-12)
- ✅ **v1.2 Hardening** — Phases 8-12 (shipped 2026-03-15)
- 🚧 **v1.3 Foundations** — Phases 13-17 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-03-10</summary>

- [x] Phase 1: Copy-Paste Semantics (3/3 plans) — completed 2026-03-04
- [x] Phase 2: Cross-Script Paste (1/1 plans) — completed 2026-03-05
- [x] Phase 3: Anchor Color System (2/2 plans) — completed 2026-03-07
- [x] Phase 4: Anchor Navigation (4/4 plans) — completed 2026-03-10
- [x] Phase 5: Refactor cross-script paste logic / DOT_TYPE distinction (3/3 plans) — completed 2026-03-05

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Polish (Phases 6-7) — SHIPPED 2026-03-12</summary>

- [x] Phase 6: Preferences Infrastructure (5/5 plans) — completed 2026-03-11
- [x] Phase 7: Color Picker Redesign and Preferences Panel (3/3 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Hardening (Phases 8-12) — SHIPPED 2026-03-15</summary>

- [x] Phase 8: Test Infrastructure Stabilization (1/1 plans) — completed 2026-03-13
- [x] Phase 9: Cross-Script Paste Bug Fixes (2/2 plans) — completed 2026-03-13
- [x] Phase 10: Code Quality Sweep (3/3 plans) — completed 2026-03-13
- [x] Phase 11: CI/CD Pipeline (1/1 plans) — completed 2026-03-14
- [x] Phase 12: Nuke -t Validation Scripts (2/2 plans) — completed 2026-03-14

Full archive: `.planning/milestones/v1.2-ROADMAP.md`

</details>

### 🚧 v1.3 Foundations (In Progress)

**Milestone Goal:** Rename the project to `anchors`, expose a public API for external templating systems, add configurable regex-based anchor naming with site-level config override, and fix anchor creation reliability bugs.

- [x] **Phase 13: Project Rename** - Rename all source, tests, CI, and GitHub repo from `paste_hidden` to `anchors` (completed 2026-03-15)
- [x] **Phase 14: Bug Fixes** - Fix anchor creation dialog name application and "a"-on-Dot anchor type (completed 2026-03-16)
- [x] **Phase 15: Anchor Naming** - Configurable regex and template for default anchor name suggestions from file knob (completed 2026-03-16)
- [x] **Phase 15.1: Additional Preferences Requirements** - Live preview, collapsible Advanced section, demo filename persistence, undoable Reset, and Publish button for site admins (completed 2026-03-17)
- [x] **Phase 16: Site Config** - Site-level config via env var with per-field lock and user override in PrefsDialog (completed 2026-03-17)
- [x] **Phase 17: Public API** - Public `anchors` API module for external modules to create and wire anchors (completed 2026-03-18)

## Phase Details

### Phase 13: Project Rename
**Goal**: All project references use `anchors` — source code, imports, tests, CI, and GitHub repo are consistent and working under the new name
**Depends on**: Nothing (first phase of milestone)
**Requirements**: REN-01, REN-02
**Success Criteria** (what must be TRUE):
  1. All Python source files import from `anchors` (not `paste_hidden`); no remaining `paste_hidden` import references
  2. The test suite passes in full under the renamed module structure
  3. The CI/CD workflow file references the new repo/package name correctly
  4. The GitHub repository is accessible at the new `anchors` URL
**Plans**: 2 plans

Plans:
- [x] 13-01-PLAN.md — Core source rename: paste_hidden.py → anchors.py, constants, prefs, menu, anchor.py, migrate_script()
- [x] 13-02-PLAN.md — Tests, CI, README update + GitHub repo rename

### Phase 14: Bug Fixes
**Goal**: Two anchor creation bugs are eliminated — the creation dialog name reliably lands on the node, and pressing "a" on a Dot produces a NoOp anchor
**Depends on**: Phase 13
**Requirements**: BUG-03, BUG-04
**Success Criteria** (what must be TRUE):
  1. Name typed in the anchor creation dialog is the name of the created anchor node every time, with no silent fallback to a generated name
  2. Pressing "a" on a selected Dot node creates a NoOp-based anchor node, not a Dot anchor
  3. Regression tests cover both behaviors and pass
**Plans**: 2 plans

Plans:
- [ ] 14-01-PLAN.md — Fix BUG-03: ColorPaletteDialog.accept() override + remove scattered chosen_name assignments + regression tests
- [ ] 14-02-PLAN.md — Fix BUG-04: remove Dot elif branch from anchor_shortcut(), deprecate _offer_make_dot_anchor() + regression tests

### Phase 15: Anchor Naming
**Goal**: Users can configure a regex and template so that the anchor creation dialog pre-fills a suggested name derived from the upstream node's file knob
**Depends on**: Phase 14
**Requirements**: NAME-01, NAME-02, NAME-03
**Success Criteria** (what must be TRUE):
  1. User can set a regex (with named capture groups) in preferences that is applied to the file knob of the source node when creating an anchor
  2. User can set a template string that substitutes regex capture groups into a pre-filled name in the anchor creation dialog
  3. When the source node has no file knob, or the regex does not match, the anchor creation dialog falls back to the existing naming behavior with no error
  4. Naming config (regex and template) persists across Nuke sessions via the prefs file
**Plans**: 3 plans

Plans:
- [ ] 15-01-PLAN.md — Wave 0 test scaffold: test_anchor_naming.py (new) + extend test_prefs.py with naming round-trip tests
- [ ] 15-02-PLAN.md — Backend: extend prefs.py with naming_regex/naming_template + rewrite suggest_anchor_name() with user-regex branch
- [ ] 15-03-PLAN.md — UI: PrefsDialog Anchor Naming section with live validity indicator + human checkpoint

### Phase 15.1: Additional Preferences Requirements (INSERTED)

**Goal**: The Anchor Naming section in PrefsDialog is complete: live rendered preview, collapsible Advanced section, demo filename persistence, undoable Reset, and a Publish button for site admins
**Depends on**: Phase 15
**Requirements**: PREF-01, PREF-02, PREF-03, PREF-04, PREF-05, PREF-06
**Plans**: 3 plans

Plans:
- [ ] 15.1-01-PLAN.md — Backend: add naming_demo_filename to prefs.py + publish(path) function + tests
- [ ] 15.1-02-PLAN.md — UI extensions: live preview label, demo filename seeding, undoable Reset, Publish button wiring
- [ ] 15.1-03-PLAN.md — UI restructure: collapsible Advanced section + human verification checkpoint

### Phase 16: Site Config
**Goal**: A site administrator can provide a config file that sets and locks user-configurable prefs fields, while users can selectively override locked fields from within PrefsDialog
**Depends on**: Phase 15
**Requirements**: SITE-01, SITE-02, SITE-03
**Success Criteria** (what must be TRUE):
  1. When `ANCHORS_SITE_CONFIG` env var points to a valid config file, its values are loaded and applied to the relevant prefs fields on startup
  2. Fields locked by site config appear disabled in PrefsDialog and cannot be changed without using the override checkbox
  3. Checking "Override Site Config" in PrefsDialog re-enables locked fields so the user can change them for their session
  4. When `ANCHORS_SITE_CONFIG` is unset or the path is invalid, the plugin loads normally with no error
**Plans**: 3 plans

Plans:
- [ ] 16-01-PLAN.md — TDD scaffold: TestSiteConfigLoading tests + update TestPublish to assert naming-only output
- [ ] 16-02-PLAN.md — Backend: _site_config dict, _user_naming_* shadow vars, _load_site_config(), _apply_effective_naming_values(), save()/publish() updates
- [ ] 16-03-PLAN.md — UI: PrefsDialog override checkbox, _update_naming_fields_lock_state(), _on_accept() shadow var flush + human verification checkpoint

### Phase 16.1: Publish always available with file save dialog (INSERTED)

**Goal:** Publish button is always enabled and always opens a file save dialog; last-used path persists to prefs so site admins can create the site config file even before ANCHORS_SITE_CONFIG is set
**Requirements**: none (inserted phase)
**Depends on:** Phase 16
**Plans:** 1/1 plans complete

Plans:
- [ ] 16.1-01-PLAN.md — Add last_publish_path to prefs.py; always-enable Publish button; open QFileDialog on click; persist chosen path

### Phase 17: Public API
**Goal**: External Nuke modules can programmatically create anchors and wire nodes to them via a stable, documented public API
**Depends on**: Phase 13
**Requirements**: API-01, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. Calling the public API function to create an anchor with a specified name, color, and source node produces a correctly configured anchor node in the DAG
  2. Calling the public API function to wire a node to an anchor by name connects the node as a link to that anchor
  3. All public API functions have docstrings covering parameters, return values, and exceptions raised
  4. The public API module can be imported by an external script without importing private internals
**Plans**: 2 plans

Plans:
- [ ] 17-01-PLAN.md — TDD RED: test_api.py test scaffold (create_anchor, find_anchor_by_name, error contracts)
- [ ] 17-02-PLAN.md — Implement api.py thin wrapper + ruff clean + full test suite green

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Copy-Paste Semantics | v1.0 | 3/3 | Complete | 2026-03-04 |
| 2. Cross-Script Paste | v1.0 | 1/1 | Complete | 2026-03-05 |
| 3. Anchor Color System | v1.0 | 2/2 | Complete | 2026-03-07 |
| 4. Anchor Navigation | v1.0 | 4/4 | Complete | 2026-03-10 |
| 5. DOT_TYPE Distinction | v1.0 | 3/3 | Complete | 2026-03-05 |
| 6. Preferences Infrastructure | v1.1 | 5/5 | Complete | 2026-03-11 |
| 7. Color Picker Redesign and Preferences Panel | v1.1 | 3/3 | Complete | 2026-03-12 |
| 8. Test Infrastructure Stabilization | v1.2 | 1/1 | Complete | 2026-03-13 |
| 9. Cross-Script Paste Bug Fixes | v1.2 | 2/2 | Complete | 2026-03-13 |
| 10. Code Quality Sweep | v1.2 | 3/3 | Complete | 2026-03-13 |
| 11. CI/CD Pipeline | v1.2 | 1/1 | Complete | 2026-03-14 |
| 12. Nuke -t Validation Scripts | v1.2 | 2/2 | Complete | 2026-03-14 |
| 13. Project Rename | 3/3 | Complete    | 2026-03-16 | - |
| 14. Bug Fixes | 2/2 | Complete    | 2026-03-16 | - |
| 15. Anchor Naming | 3/3 | Complete    | 2026-03-17 | - |
| 15.1. Additional Preferences Requirements | 3/3 | Complete    | 2026-03-17 | - |
| 16. Site Config | 3/3 | Complete    | 2026-03-17 | - |
| 17. Public API | 2/2 | Complete    | 2026-03-18 | - |
