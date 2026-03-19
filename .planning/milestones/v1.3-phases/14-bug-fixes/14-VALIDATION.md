---
phase: 14
slug: bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — pytest discovers `tests/` by default |
| **Quick run command** | `pytest tests/test_anchor_color_system.py tests/test_dot_type_distinction.py -x` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_anchor_color_system.py tests/test_dot_type_distinction.py -x`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | BUG-03 | unit | `pytest tests/test_anchor_color_system.py -x -k "chosen_name"` | ✅ | ⬜ pending |
| 14-01-02 | 01 | 1 | BUG-03 | unit | `pytest tests/test_anchor_color_system.py -x -k "name_edit_none"` | ✅ | ⬜ pending |
| 14-02-01 | 02 | 1 | BUG-04 | unit | `pytest tests/test_dot_type_distinction.py -x -k "dot_routing"` | ✅ | ⬜ pending |
| 14-02-02 | 02 | 1 | BUG-04 | unit | `pytest tests/test_dot_type_distinction.py -x -k "non_dot"` | ✅ | ⬜ pending |
| 14-02-03 | 02 | 1 | BUG-04 | unit | `pytest tests/test_dot_type_distinction.py -x -k "anchor_selected"` | ✅ | ⬜ pending |
| 14-02-04 | 02 | 1 | BUG-04 | unit | `pytest tests/test_dot_type_distinction.py -x -k "no_selection"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Both target test files exist and use the same conftest.py/stubs.py infrastructure. No new fixtures or framework installs are needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
