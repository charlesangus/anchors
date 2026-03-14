---
phase: 12
slug: nuke-t-validation-scripts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (offline suite) + manual `nuke -t` (validation scripts) |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `python3 -m pytest tests/ -x -q` |
| **Full suite command** | `python3 -m pytest tests/` |
| **Estimated runtime** | ~10 seconds (pytest); nuke -t scripts: manual only |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | TEST-01 | manual | `nuke -t validation/validate_stub_alignment.py` | ❌ Wave 0 | ⬜ pending |
| 12-01-02 | 01 | 1 | TEST-01 | manual | `nuke -t validation/validate_cross_script_paste.py` | ❌ Wave 0 | ⬜ pending |
| 12-01-03 | 01 | 2 | TEST-02 | automated | `python3 -m pytest tests/ -x -q` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `validation/` directory created
- [ ] `validation/validate_stub_alignment.py` — covers TEST-01 (StubNode/StubKnob alignment probes)
- [ ] `validation/validate_cross_script_paste.py` — covers TEST-01 (BUG-01 and BUG-02 smoke tests)

*Existing `pytest tests/` infrastructure covers TEST-02 (stub correction verification) — no new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `validate_stub_alignment.py` runs to completion under `nuke -t` | TEST-01 | Requires commercial Nuke license; not available on CI runners (REQUIREMENTS.md Out of Scope) | Run `nuke -t validation/validate_stub_alignment.py`; verify final line shows `Summary: N/M checks passed` with exit code 0 |
| `validate_cross_script_paste.py` runs to completion under `nuke -t` | TEST-01 | Requires commercial Nuke license; not available on CI runners | Run `nuke -t validation/validate_cross_script_paste.py`; verify BUG-01 and BUG-02 checks show PASS |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
