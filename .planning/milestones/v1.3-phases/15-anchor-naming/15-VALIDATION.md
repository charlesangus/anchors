---
phase: 15
slug: anchor-naming
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — pytest discovers via `tests/` convention |
| **Quick run command** | `python3 -m pytest tests/test_anchor_naming.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_anchor_naming.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | NAME-01, NAME-02, NAME-03 | unit | `python3 -m pytest tests/test_anchor_naming.py -x -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | NAME-01, NAME-02, NAME-03 | unit | `python3 -m pytest tests/test_anchor_naming.py -x -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | NAME-01, NAME-02, NAME-03 | unit | `python3 -m pytest tests/test_anchor_naming.py::TestSuggestAnchorNameUserRegex tests/test_anchor_naming.py::TestFrameTokenStripping tests/test_anchor_naming.py::TestTemplateSubstitution tests/test_anchor_naming.py::TestTemplateSubstitutionFallback tests/test_anchor_naming.py::TestNoFileKnobFallback tests/test_anchor_naming.py::TestRegexNoMatchFallback -x -q` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 1 | NAME-01, NAME-02, NAME-03 | unit | `python3 -m pytest tests/test_prefs.py -x -q` | ✅ | ⬜ pending |
| 15-04-01 | 04 | 2 | NAME-01, NAME-02, NAME-03 | unit | `python3 -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_anchor_naming.py` — new file covering NAME-01 (`TestSuggestAnchorNameUserRegex`, `TestFrameTokenStripping`), NAME-02 (`TestTemplateSubstitution`, `TestTemplateSubstitutionFallback`), NAME-03 (`TestNoFileKnobFallback`, `TestRegexNoMatchFallback`)
- [ ] Extend `tests/test_prefs.py` — add round-trip tests for `naming_regex` and `naming_template` keys

*Existing pytest infrastructure (stubs, conftest) covers all phase requirements — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PrefsDialog validity indicator turns green/red live | NAME-01 | Requires live Qt widget interaction | Open Prefs, type a valid regex matching the test filename, verify label turns green; type invalid regex, verify it turns red |
| Naming config persists across Nuke sessions | NAME-01, NAME-02 | Requires Nuke process restart | Set regex + template in Prefs, save, restart Nuke, open Prefs again, verify fields are populated |
| Anchor creation dialog pre-fills suggested name | NAME-01, NAME-02 | Requires live Nuke + Read node with file knob | Connect Read node with `plate_v003.exr`, configure regex `(?P<shot>.+)_v\d+`, create anchor, verify dialog pre-fills `plate` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
