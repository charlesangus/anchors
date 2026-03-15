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

- [ ] **Phase 13: Project Rename** - Rename all source, tests, CI, and GitHub repo from `paste_hidden` to `anchors`
- [ ] **Phase 14: Bug Fixes** - Fix anchor creation dialog name application and "a"-on-Dot anchor type
- [ ] **Phase 15: Anchor Naming** - Configurable regex and template for default anchor name suggestions from file knob
- [ ] **Phase 16: Site Config** - Site-level config via env var with per-field lock and user override in PrefsDialog
- [ ] **Phase 17: Public API** - Public `anchors` API module for external modules to create and wire anchors

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
- [ ] 13-01-PLAN.md — Core source rename: paste_hidden.py → anchors.py, constants, prefs, menu, anchor.py, migrate_script()
- [ ] 13-02-PLAN.md — Tests, CI, README update + GitHub repo rename

### Phase 14: Bug Fixes
**Goal**: Two anchor creation bugs are eliminated — the creation dialog name reliably lands on the node, and pressing "a" on a Dot produces a NoOp anchor
**Depends on**: Phase 13
**Requirements**: BUG-03, BUG-04
**Success Criteria** (what must be TRUE):
  1. Name typed in the anchor creation dialog is the name of the created anchor node every time, with no silent fallback to a generated name
  2. Pressing "a" on a selected Dot node creates a NoOp-based anchor node, not a Dot anchor
  3. Regression tests cover both behaviors and pass
**Plans**: TBD

### Phase 15: Anchor Naming
**Goal**: Users can configure a regex and template so that the anchor creation dialog pre-fills a suggested name derived from the upstream node's file knob
**Depends on**: Phase 14
**Requirements**: NAME-01, NAME-02, NAME-03
**Success Criteria** (what must be TRUE):
  1. User can set a regex (with named capture groups) in preferences that is applied to the file knob of the source node when creating an anchor
  2. User can set a template string that substitutes regex capture groups into a pre-filled name in the anchor creation dialog
  3. When the source node has no file knob, or the regex does not match, the anchor creation dialog falls back to the existing naming behavior with no error
  4. Naming config (regex and template) persists across Nuke sessions via the prefs file
**Plans**: TBD

### Phase 16: Site Config
**Goal**: A site administrator can provide a config file that sets and locks user-configurable prefs fields, while users can selectively override locked fields from within PrefsDialog
**Depends on**: Phase 15
**Requirements**: SITE-01, SITE-02, SITE-03
**Success Criteria** (what must be TRUE):
  1. When `ANCHORS_SITE_CONFIG` env var points to a valid config file, its values are loaded and applied to the relevant prefs fields on startup
  2. Fields locked by site config appear disabled in PrefsDialog and cannot be changed without using the override checkbox
  3. Checking "Override Site Config" in PrefsDialog re-enables locked fields so the user can change them for their session
  4. When `ANCHORS_SITE_CONFIG` is unset or the path is invalid, the plugin loads normally with no error
**Plans**: TBD

### Phase 17: Public API
**Goal**: External Nuke modules can programmatically create anchors and wire nodes to them via a stable, documented public API
**Depends on**: Phase 13
**Requirements**: API-01, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. Calling the public API function to create an anchor with a specified name, color, and source node produces a correctly configured anchor node in the DAG
  2. Calling the public API function to wire a node to an anchor by name connects the node as a link to that anchor
  3. All public API functions have docstrings covering parameters, return values, and exceptions raised
  4. The public API module can be imported by an external script without importing private internals
**Plans**: TBD

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
| 13. Project Rename | v1.3 | 0/2 | Not started | - |
| 14. Bug Fixes | v1.3 | 0/? | Not started | - |
| 15. Anchor Naming | v1.3 | 0/? | Not started | - |
| 16. Site Config | v1.3 | 0/? | Not started | - |
| 17. Public API | v1.3 | 0/? | Not started | - |
