---
phase: 9
slug: cross-script-paste-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` (stdlib) + `pytest` (flat-discovery compatible) |
| **Config file** | `tests/conftest.py` (pytest) / `tests/__init__.py` (unittest) |
| **Quick run command** | `python3 -m unittest tests.test_cross_script_paste -v` |
| **Full suite command** | `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m unittest tests.test_cross_script_paste -v`
- **After every plan wave:** Run `python3 -m unittest discover -s tests/ -t . -p "test_*.py"`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 0 | BUG-01 | unit/regression | `python3 -m unittest tests.test_cross_script_paste.TestBugRegressions.test_bug01_link_dot_cross_script_color -v` | ❌ Wave 0 | ⬜ pending |
| 9-01-02 | 01 | 0 | BUG-02 | unit/regression | `python3 -m unittest tests.test_cross_script_paste.TestBugRegressions.test_bug02_anchor_stays_anchor_cross_script -v` | ❌ Wave 0 | ⬜ pending |
| 9-01-03 | 01 | 1 | BUG-01 | unit/regression | `python3 -m unittest tests.test_cross_script_paste.TestBugRegressions.test_bug01_link_dot_cross_script_color -v` | ✅ Wave 0 | ⬜ pending |
| 9-01-04 | 01 | 1 | BUG-02 | unit/regression | `python3 -m unittest tests.test_cross_script_paste.TestBugRegressions.test_bug02_anchor_stays_anchor_cross_script -v` | ✅ Wave 0 | ⬜ pending |
| 9-01-05 | 01 | 1 | BUG-01, BUG-02 | full suite | `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cross_script_paste.py` — add `TestBugRegressions` class with `test_bug01_link_dot_cross_script_color` and `test_bug02_anchor_stays_anchor_cross_script` tests (file exists; add new class)
- [ ] No new framework installs needed — `unittest` is stdlib; `pytest` already present

*Wave 0 adds the failing regression tests first (red), then fixes are applied (green).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
