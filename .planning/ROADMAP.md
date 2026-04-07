# Roadmap: anchors

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-03-10)
- ✅ **v1.1 Polish** — Phases 6-7 (shipped 2026-03-12)
- ✅ **v1.2 Hardening** — Phases 8-12 (shipped 2026-03-15)
- ✅ **v1.3 Foundations** — Phases 13-17 (shipped 2026-03-18)
- ✅ **v1.4 Group Support** — Phases 18-19 (shipped 2026-03-23)

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

<details>
<summary>✅ v1.4 Group Support (Phases 18-19) — SHIPPED 2026-03-23</summary>

- [x] Phase 18: Group Context Support (4/4 plans) — completed 2026-03-20
- [x] Phase 19: Quick Start Documentation (1/1 plans) — completed 2026-03-20

Full archive: `.planning/milestones/v1.4-ROADMAP.md`

</details>

## v1.5 Bug Fixes

- [ ] Phase 20: Fix Issue #6 — Alt-J/Alt-L Navigation Reliability

### Phase 20: Fix Issue #6 — Alt-J/Alt-L Navigation Reliability

**Goal:** Make `jump_to_selected_anchor` (Alt+J) and `cycle_next_link` (Alt+L) work reliably in production scripts by applying QTimer deferral (same pattern as Alt+A) and fixing `get_links_for_anchor` to find links inside Group nodes.

**Scope:**
- Add QTimer deferral to `jump_to_selected_anchor`, the inline zoom in `cycle_next_link`, and `navigate_back` in `anchor.py` — mirrors the fix already applied to `AnchorNavigatePlugin.invoke()`
- Fix `get_links_for_anchor` in `anchor.py` to use `recurseGroups=True` so Alt+L finds links inside Groups
- Add/update tests for deferred navigation and recurse-group link discovery

**Out of scope:** Navigating into a Group's internal DAG to show a link (that's a separate feature; for now cycle_next_link will skip links inside Groups or navigate to the enclosing Group node)

**Plans:** 1 plan

Plans:
- [ ] 20-01-PLAN.md — QTimer deferral for Alt+J/Alt+L/Alt+Z and recurseGroups fix for get_links_for_anchor

**Requirements:**
- REQ-20-01: `jump_to_selected_anchor` defers DAG viewport operations via `QTimer.singleShot(0, ...)`
- REQ-20-02: `cycle_next_link` defers DAG viewport operations via `QTimer.singleShot(0, ...)`
- REQ-20-03: `navigate_back` defers DAG viewport operations via `QTimer.singleShot(0, ...)`
- REQ-20-04: `get_links_for_anchor` finds link nodes inside Group nodes

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
| 19. Quick Start Documentation | v1.4 | 1/1 | Complete | 2026-03-20 |
| 20. Fix Issue #6 — Alt-J/Alt-L Navigation Reliability | v1.5 | 0/1 | Planned | — |
