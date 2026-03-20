# Roadmap: anchors

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-03-10)
- ✅ **v1.1 Polish** — Phases 6-7 (shipped 2026-03-12)
- ✅ **v1.2 Hardening** — Phases 8-12 (shipped 2026-03-15)
- ✅ **v1.3 Foundations** — Phases 13-17 (shipped 2026-03-18)
- 🔄 **v1.4 Group Support** — Phases 18-19 (in progress)

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

<details>
<summary>✅ v1.3 Foundations (Phases 13-17) — SHIPPED 2026-03-18</summary>

- [x] Phase 13: Project Rename (3/3 plans) — completed 2026-03-15
- [x] Phase 14: Bug Fixes (2/2 plans) — completed 2026-03-16
- [x] Phase 15: Anchor Naming (3/3 plans) — completed 2026-03-16
- [x] Phase 15.1: Additional Preferences Requirements (3/3 plans) — completed 2026-03-17
- [x] Phase 16: Site Config (3/3 plans) — completed 2026-03-17
- [x] Phase 16.1: Publish Always Available with File Save Dialog (1/1 plans) — completed 2026-03-17
- [x] Phase 17: Public API (2/2 plans) — completed 2026-03-18

Full archive: `.planning/milestones/v1.3-ROADMAP.md`

</details>

### v1.4 Group Support

- [x] **Phase 18: Group Context Support** - All plugin operations work correctly inside Group nested DAGs (UAT gap closure in progress) (completed 2026-03-20)
- [ ] **Phase 19: Quick Start Documentation** - docs/ guide covering anchor creation, navigation, and copy/paste semantics

## Phase Details

### Phase 18: Group Context Support
**Goal**: All plugin entry points (copy/paste, anchor creation, link creation, navigation) work correctly when the user is inside a Group node's nested DAG by respecting `nuke.thisGroup()`
**Depends on**: Nothing (self-contained fix across existing entry points)
**Requirements**: GROUP-01, GROUP-02, GROUP-03, GROUP-04
**Success Criteria** (what must be TRUE):
  1. User inside a Group can Ctrl+C/V nodes and get the same clipboard behavior (hidden-input-aware paste, link stamping) as in the root DAG
  2. User inside a Group can press `a` to open the anchor creation popup, name an anchor, and have it created in the Group's nested graph
  3. User inside a Group can create a link to an anchor and have it wired correctly within the Group's nested graph
  4. User inside a Group can press Alt+A to open the navigation picker and jump to an anchor within the Group context
**Plans:** 4/4 plans complete
Plans:
- [x] 18-01-PLAN.md — Group-context utility helper and foundation module updates (link.py, anchors.py, labels.py)
- [x] 18-02-PLAN.md — Anchor.py Group-aware operations (creation, navigation, rename, reconnection)
- [ ] 18-03-PLAN.md — Gap closure: fix A-key link creation inside Group (pre-capture lastHitGroup)
- [ ] 18-04-PLAN.md — Gap closure: fix Alt+A navigation zoom inside Group (deferred zoom via QTimer)

### Phase 19: Quick Start Documentation
**Goal**: A `docs/` Quick Start guide exists that a new user can read to get productive with the plugin's three primary workflows
**Depends on**: Phase 18 (documents the final, working behavior including Group support)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. A Markdown file exists at `docs/quick-start.md` (or similar) covering plugin orientation and all three primary workflows
  2. Reader can follow the anchor creation section (`a` shortcut, naming dialog, color picker) and know what to expect at each step
  3. Reader can follow the anchor navigation section (Alt+A picker, jumping to anchor location) and know what to expect
  4. Reader can follow the copy/paste semantics section and understand how Ctrl+C/V behaves differently with anchors and links
  5. Each workflow section contains PNG screenshot placeholder markers so screenshots can be added later without restructuring the doc
**Plans:** 1 plan
Plans:
- [ ] 19-01-PLAN.md — Create Quick Start guide with all three workflow sections and screenshot placeholders

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
| 13. Project Rename | v1.3 | 3/3 | Complete | 2026-03-15 |
| 14. Bug Fixes | v1.3 | 2/2 | Complete | 2026-03-16 |
| 15. Anchor Naming | v1.3 | 3/3 | Complete | 2026-03-16 |
| 15.1. Additional Preferences Requirements | v1.3 | 3/3 | Complete | 2026-03-17 |
| 16. Site Config | v1.3 | 3/3 | Complete | 2026-03-17 |
| 16.1. Publish Always Available with File Save Dialog | v1.3 | 1/1 | Complete | 2026-03-17 |
| 17. Public API | v1.3 | 2/2 | Complete | 2026-03-18 |
| 18. Group Context Support | v1.4 | 4/4 | Complete | 2026-03-20 |
| 19. Quick Start Documentation | v1.4 | 0/1 | Not started | - |
