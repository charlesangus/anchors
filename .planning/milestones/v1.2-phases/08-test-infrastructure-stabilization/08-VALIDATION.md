---
phase: 8
slug: test-infrastructure-stabilization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — `tests/conftest.py` picked up automatically by pytest convention |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 0 | TEST-03 | smoke | `pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 0 | TEST-03 | smoke | `pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 8-01-03 | 01 | 1 | TEST-03 | smoke | `pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 8-01-04 | 01 | 1 | TEST-03 | smoke | `pytest tests/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — installs canonical stubs before any test file is imported; covers TEST-03 flat discovery requirement
- [ ] `tests/stubs.py` — provides StubKnob, StubNode, make_stub_nuke_module(), make_stub_nukescripts_module() as superset of all per-file stubs
- [ ] pytest installation — determine correct invocation command for this machine's environment (pytest not installed in Nuke Python env)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Individual file isolation | TEST-03 | Verifying no regressions from conftest | Run each file alone: `pytest tests/test_anchor_color_system.py -q`, repeat for each file |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
