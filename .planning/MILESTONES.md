# Milestones

## v1.3 Foundations (Shipped: 2026-03-18)

**Phases completed:** 7 phases (Phases 13–17 incl. 15.1, 16.1), 17 plans

**Timeline:** 2026-03-15 → 2026-03-18 (3 days)
**LOC:** ~10,212 Python total
**Git range:** `e80ab07` → `4865e6e`

**Key accomplishments:**
- Renamed project from `paste_hidden` to `anchors` across all source, tests, CI, and GitHub repo with migration path for old prefs (REN-01, REN-02)
- Fixed anchor creation dialog name reliability (BUG-03) and Dot→NoOp anchor dispatch (BUG-04) with regression coverage
- Configurable regex + template anchor naming with live validity indicator in PrefsDialog (NAME-01–03)
- PrefsDialog Anchor Naming polish: collapsible Advanced section, live preview label, undoable Reset, Publish button (PREF-01–06)
- Site-level config via `ANCHORS_SITE_CONFIG` env var with two-layer prefs system and per-field lock/override checkbox in PrefsDialog (SITE-01–03)
- Always-enabled Publish button with file save dialog and `last_publish_path` persistence for first-time site config creation
- Public `api.py` module exposing `create_anchor()` and `find_anchor_by_name()` with NumPy-style docstrings and `__all__` stable surface (API-01–03)

**Requirements:** 13/13 v1.3 requirements satisfied

**Archive:** `.planning/milestones/v1.3-ROADMAP.md`, `.planning/milestones/v1.3-REQUIREMENTS.md`

---

## v1.2 Hardening (Shipped: 2026-03-15)

**Phases completed:** 5 phases (Phases 8-12), 9 plans

**Timeline:** 2026-03-12 → 2026-03-14 (3 days)
**LOC:** ~3,089 Python (source)
**Git range:** `feat(08-01)` → `feat(12-01)`

**Key accomplishments:**
- Centralized test stub library (`tests/stubs.py` + `conftest.py`) — eliminated Qt stub ordering conflicts; 132 tests green under flat discovery (TEST-03)
- Fixed BUG-01 (cross-script NoOp link receives anchor's `tile_color`, not default purple) and BUG-02 (anchor stays anchor when pasted cross-script) with regression test coverage (BUG-01, BUG-02)
- Zero ruff violations across all 10 source files; FROZEN annotations on all 8 serialized knob constants; C901 complexity deferred appropriately (QUAL-01)
- Tag-triggered GitHub Actions CI/CD: `pytest` test gate → versioned ZIP artifact (explicit 10-file manifest) → GitHub Release via `softprops/action-gh-release@v2` (CI-01, CI-02)
- `nuke -t` validation scripts probing stub alignment against real Nuke 16.0v6; two divergences corrected — `StubNode.__getitem__` raises `NameError` (not `KeyError`), `toNode('preferences')` returns `MagicMock` node (TEST-01, TEST-02)

**Requirements:** 8/8 v1.2 requirements satisfied
**Tech debt:** Live CI tag push pending; Nuke runtime menu callback smoke test pending; Nyquist validation draft

**Archive:** `.planning/milestones/v1.2-ROADMAP.md`, `.planning/milestones/v1.2-REQUIREMENTS.md`

---

## v1.1 Polish (Shipped: 2026-03-12)

**Phases completed:** 2 phases, 8 plans (Phases 6-7)

**Timeline:** 2026-03-11 → 2026-03-12 (2 days)
**LOC:** ~3,064 Python (source)
**Git range:** `408443f feat(06-01)` → `7495ce9 chore(07)`

**Key accomplishments:**
- JSON-backed prefs singleton (`prefs.py`) with `plugin_enabled`, `link_classes_paste_mode`, `custom_colors` — persists across Nuke sessions
- One-way migration from legacy `paste_hidden_user_palette.json` into new prefs file on first run
- Plugin-enabled gating on all clipboard, anchor, and label entry points; LINK_CLASSES passthrough mode
- Click-to-select `ColorPaletteDialog` with OK button, group ordering (custom→backdrop→defaults), and custom color staging
- `PrefsDialog` with plugin toggle, paste-mode toggle, and full custom color CRUD (Add/Edit/Remove)
- `Preferences...` menu entry wired into Anchors menu; custom colors persist across sessions via `_persist_custom_colors_from_dialog` helper

**Requirements:** 16/17 v1.1 requirements explicitly checked off; PANEL-01 delivered via Phase 7-03 (checkbox missed before archive)

**Archive:** `.planning/milestones/v1.1-ROADMAP.md`, `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## v1.0 MVP (Shipped: 2026-03-10)

**Phases completed:** 5 phases, 13 plans

**Timeline:** 2026-03-03 → 2026-03-10 (7 days)
**LOC:** ~5,500 Python
**Git range:** `d13aebf feat(01-01)` → `588dc04 feat(04-02)`

**Key accomplishments:**
- canSetInput stream-type probe — Camera anchors produce NoOp links; Read produces PostageStamp (LINK-03 fix)
- Cross-script paste reconnection — Link nodes reconnect by anchor name in destination scripts (XSCRIPT-01)
- Anchor color system — ColorPaletteDialog wired into creation/rename dialogs and anchor node; propagates to all linked nodes (COLOR-01–05)
- DAG navigation history — Alt+A saves position, Alt+Z jumps back; labelled BackdropNodes in picker (NAV-01, NAV-02, FIND-01)
- DOT_TYPE knob distinction — formal Link Dot / Local Dot separation eliminates cross-script false positives (XSCRIPT-01/02 robustness)
- TDD infrastructure — 74+ offline unit tests covering all paste, anchor, color, and navigation logic

**Requirements:** 17/18 v1 requirements shipped; NAV-03 (full forward/back history stack) deferred to v2 as planned stretch goal

**Archive:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`

---

