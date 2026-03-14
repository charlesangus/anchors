# Roadmap: paste_hidden

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-03-10)
- ✅ **v1.1 Polish** — Phases 6-7 (shipped 2026-03-12)
- 🚧 **v1.2 Hardening** — Phases 8-12 (in progress)

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

### 🚧 v1.2 Hardening (In Progress)

**Milestone Goal:** Fix cross-script paste regressions, stabilize test infrastructure, sweep code quality, and add CI/CD packaging pipeline.

- [x] **Phase 8: Test Infrastructure Stabilization** - Fix flat-discovery Qt stub ordering conflicts so the test suite is a reliable feedback mechanism
- [x] **Phase 9: Cross-Script Paste Bug Fixes** - Fix BUG-01 and BUG-02 in paste_hidden.py with regression tests (completed 2026-03-13)
- [x] **Phase 10: Code Quality Sweep** - Dead code removal, unused import cleanup, complex conditional simplification (completed 2026-03-13)
- [x] **Phase 11: CI/CD Pipeline** - Tag-triggered GitHub Actions workflow: offline tests, versioned ZIP, GitHub Release (completed 2026-03-14)
- [ ] **Phase 12: Nuke -t Validation Scripts** - Manual developer validation confirming stub behavior matches real Nuke runtime

## Phase Details

### Phase 8: Test Infrastructure Stabilization
**Goal**: The test suite passes cleanly under flat discovery so it can serve as a reliable regression gate for all subsequent work
**Depends on**: Nothing (first v1.2 phase)
**Requirements**: TEST-03
**Success Criteria** (what must be TRUE):
  1. `pytest tests/` (flat discovery) completes with zero errors and zero failures
  2. `tests/conftest.py` exists and provides the authoritative shared Qt and tabtabtab stubs for all test files
  3. All individual test files continue to pass when run in isolation
  4. No per-file stub installation remains that could conflict with conftest stubs
**Plans**: 1 plan

Plans:
- [x] 08-01-PLAN.md — Create tests/stubs.py + tests/conftest.py, strip per-file stub blocks from 5 test files

### Phase 9: Cross-Script Paste Bug Fixes
**Goal**: Anchors pasted cross-script stay anchors, and NoOp links pasted cross-script receive the correct anchor tile_color — both with regression test coverage that guards the subsequent quality sweep
**Depends on**: Phase 8
**Requirements**: BUG-01, BUG-02
**Success Criteria** (what must be TRUE):
  1. A NoOp link pasted into a different script shows the anchor's tile_color, not the default purple
  2. An anchor node pasted into a different script remains an anchor node, not a link node
  3. Regression tests for both bugs exist in `tests/` and pass under flat discovery
  4. `pytest tests/` remains green after both fixes are applied
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md — Write failing regression tests (TestBugRegressions class with BUG-01 and BUG-02 tests — RED phase)
- [ ] 09-02-PLAN.md — Apply BUG-01 and BUG-02 fixes to paste_hidden.py; confirm full suite green

### Phase 10: Code Quality Sweep
**Goal**: The source files are cleaner — dead code removed, unused imports eliminated, overly complex conditionals simplified — with no API breaks, no behavior changes, and no serialized knob string values altered
**Depends on**: Phase 9
**Requirements**: QUAL-01
**Success Criteria** (what must be TRUE):
  1. `ruff check` (rules E, F, W, B, C90, I, SIM) reports zero violations across all source files
  2. All serialized knob name constants in `constants.py` are annotated as FROZEN and none have been renamed
  3. `pytest tests/` remains green after every sweep commit touching `paste_hidden.py`
  4. No public function or class API is changed (no callers broken)
**Plans**: 3 plans

Plans:
- [ ] 10-01-PLAN.md — Create pyproject.toml with ruff config; auto-fix import sort order (I001) across all source files
- [ ] 10-02-PLAN.md — Fix anchor.py and link.py (F401, SIM105, SIM108, E501); fix colors.py and labels.py (B007, C901 noqa, E501)
- [ ] 10-03-PLAN.md — Fix paste_hidden.py (E501, C901 noqa), menu.py and prefs.py (E501); add FROZEN annotations to constants.py; global zero-violation verify

### Phase 11: CI/CD Pipeline
**Goal**: A tag push to GitHub triggers offline tests, packages plugin source into a versioned ZIP, and publishes a GitHub Release — with the ZIP containing only end-user files and no dev artifacts
**Depends on**: Phase 10
**Requirements**: CI-01, CI-02
**Success Criteria** (what must be TRUE):
  1. Pushing a version tag (e.g., `v1.2.0`) to GitHub triggers the workflow and produces a GitHub Release
  2. The GitHub Release contains a ZIP artifact with only the plugin source files (no `tests/`, `validation/`, `.planning/`, `__pycache__`)
  3. The workflow runs offline tests (`pytest tests/`) and fails the release if tests fail
  4. A locally unzipped copy of the release artifact contains exactly the expected files and no extras
**Plans**: 1 plan

Plans:
- [ ] 11-01-PLAN.md — Create .github/workflows/release.yml — tag-triggered test gate, ZIP packaging, GitHub Release publication

### Phase 12: Nuke -t Validation Scripts
**Goal**: A developer running the validation scripts against a local licensed Nuke install can confirm that StubNode/StubKnob assumptions in `tests/` match real Nuke API behavior, and that the BUG-01 and BUG-02 fixed code paths work correctly under a real runtime
**Depends on**: Phase 11
**Requirements**: TEST-01, TEST-02
**Success Criteria** (what must be TRUE):
  1. `validation/validate_stub_alignment.py` exists and runs to completion under `nuke -t` without errors
  2. `validation/validate_cross_script_paste.py` exists and smoke-tests the BUG-01 and BUG-02 fixed paths under `nuke -t`
  3. Any stub or mock inconsistencies found by the scripts are corrected in `tests/` and `pytest tests/` remains green
  4. Validation scripts never import `menu.py` and never reach Qt dialog code paths in headless mode
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
| 9. Cross-Script Paste Bug Fixes | 2/2 | Complete   | 2026-03-13 | - |
| 10. Code Quality Sweep | 3/3 | Complete    | 2026-03-13 | - |
| 11. CI/CD Pipeline | 1/1 | Complete    | 2026-03-14 | - |
| 12. Nuke -t Validation Scripts | v1.2 | 0/? | Not started | - |
