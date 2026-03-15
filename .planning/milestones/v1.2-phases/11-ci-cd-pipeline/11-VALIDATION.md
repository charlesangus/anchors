---
phase: 11
slug: ci-cd-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest via pip) |
| **Config file** | `pyproject.toml` (ruff config only; pytest uses defaults) |
| **Quick run command** | `pytest tests/` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green + push a `v*` tag and confirm release on GitHub
- **Max feedback latency:** ~5 seconds (automated); manual ZIP inspection before phase close

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | CI-01, CI-02 | manual | N/A — push tag, inspect release | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

*No new test files needed — `tests/conftest.py` and existing stubs handle all offline test requirements. The workflow file itself is the artifact under test.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tag push triggers workflow, runs tests, publishes GitHub Release | CI-01 | Requires a real GitHub Actions run triggered by a `v*` tag push | 1. Push `git tag v0.0.1-test && git push origin v0.0.1-test`; 2. Observe workflow run in GitHub Actions UI succeeds; 3. Confirm GitHub Release appears at the repo's Releases page |
| ZIP contains only explicit file manifest under `paste_hidden/` subdirectory | CI-02 | Requires downloading and inspecting the release asset | 1. Download ZIP from GitHub Release; 2. Run `unzip -l paste_hidden-v0.0.1-test.zip`; 3. Confirm exactly 10 `.py` files listed under `paste_hidden/` — no `tests/`, `validation/`, `.planning/`, `__pycache__`, `pyproject.toml`, `LICENSE`, `README.md`, `__init__.py` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (manual phase gate via tag push is expected and documented)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
