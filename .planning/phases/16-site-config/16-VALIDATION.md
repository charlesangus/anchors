---
phase: 16
slug: site-config
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (unittest stdlib) |
| **Config file** | none — existing test infrastructure |
| **Quick run command** | `python -m pytest tests/test_prefs.py tests/test_anchor_naming.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_prefs.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 0 | SITE-01 | unit | `python -m pytest tests/test_prefs.py -k "site_config" -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | SITE-01 | unit | `python -m pytest tests/test_prefs.py -k "site_config_missing" -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | SITE-02 | unit | `python -m pytest tests/test_prefs.py -k "site_config_locks" -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | SITE-02 | unit | `python -m pytest tests/test_prefs.py -k "publish_naming_only" -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | SITE-03 | unit | `python -m pytest tests/test_prefs.py -k "override" -x -q` | ❌ W0 | ⬜ pending |
| TBD | 01 | 0 | SITE-03 | unit | `python -m pytest tests/test_prefs.py -k "override_round_trip" -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_prefs.py` — new test class `TestSiteConfigLoading` covering SITE-01/02/03 prefs behavior
- [ ] `tests/test_prefs.py` — update `TestPublish.test_publish_writes_to_given_path` to assert ONLY naming keys present (no `plugin_enabled`, `link_classes_paste_mode`, `custom_colors`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Locked fields appear visually greyed-out in PrefsDialog | SITE-02 | Requires visual UI inspection; headless tests can verify setEnabled state but not visual rendering | Open PrefsDialog with ANCHORS_SITE_CONFIG set; confirm naming fields are greyed out |
| Override checkbox hidden when no site config active | SITE-03 | Requires visual UI inspection | Open PrefsDialog without ANCHORS_SITE_CONFIG; confirm no "Override Site Config" checkbox visible |
| Override checkbox visible and toggles fields when site config active | SITE-03 | Requires visual UI interaction | Open PrefsDialog with ANCHORS_SITE_CONFIG set; check Override checkbox; confirm fields become editable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
