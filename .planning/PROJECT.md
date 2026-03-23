# anchors

## What This Is

`anchors` (formerly `paste_hidden`) is a Foundry Nuke plugin that replaces Nuke's native clipboard system with one that intelligently handles hidden inputs, and adds a named anchor/link reference system for navigating and reusing node graph connections. It is used by a single VFX artist to manage complex compositing node graphs.

**v1.0 shipped:** Clear paste semantics for all node types, cross-script anchor reconnection, anchor color system with palette dialog, DAG navigation history (Alt+Z back), backdrop navigation inclusion, DOT_TYPE-gated Dot subtype distinction, 74+ offline unit tests.

**v1.1 shipped:** JSON-backed prefs singleton (plugin_enabled, link_classes_paste_mode, custom_colors), plugin-wide enable/disable gating, LINK_CLASSES passthrough mode, click-to-select ColorPaletteDialog, PrefsDialog with full custom color CRUD, and Preferences... menu entry.

**v1.2 shipped:** 132-test suite with centralized stub infrastructure (tests/stubs.py + conftest.py), BUG-01/BUG-02 cross-script paste fixes with regression tests, zero ruff violations across all 10 source files, tag-triggered GitHub Actions CI/CD (pytest gate + versioned ZIP + GitHub Release), and nuke -t validation scripts confirming stub alignment to real Nuke 16.0v6.

**v1.3 shipped:** Project renamed to `anchors`. Configurable regex+template anchor naming with live preview. Site-level config (`ANCHORS_SITE_CONFIG`) with per-field lock/override. Anchor creation bug fixes (dialog name reliability, Dot→NoOp dispatch). Public `api.py` module for external script integration. PrefsDialog Anchor Naming fully polished with collapsible Advanced section, undoable Reset, and always-available Publish button with file save dialog.

**v1.4 shipped:** All plugin operations work correctly inside Nuke Group nodes via `all_nodes_in_context()` helper and `lastHitGroup()` pre-capture pattern. Alt+A navigation inside Groups deferred via `QTimer.singleShot(0, ...)` to zoom the correct DAG panel. Quick Start guide at `docs/quick-start.md` covering anchor creation, navigation, and copy/paste workflows with screenshot placeholders.

## Core Value

Copy and paste must reconnect predictably — anchors provide stable, navigable references; hidden inputs reconnect to their source without ceremony.

## Requirements

### Validated

- ✓ Ctrl+C/X/V replaced with hidden-input-aware clipboard system — existing
- ✓ Anchor nodes (NoOp with `Anchor_` prefix, or marked Dot) created and named — existing
- ✓ Link nodes (PostageStamp/NoOp/Dot) wire to anchors via FQNN — existing
- ✓ Tabtabtab fuzzy-search picker for anchor creation and navigation — existing
- ✓ Anchor navigation (Alt+A) zooms DAG to anchor location — existing
- ✓ Anchor renaming propagates label to all linked nodes — existing
- ✓ Label utilities (large/medium/append) with font sizing — existing
- ✓ Anchor color inherits from backdrop → input node → default purple on creation — existing
- ✓ File nodes (LINK_CLASSES) with an existing anchor → copy creates a link to that anchor — v1.0
- ✓ 2D stream nodes use PostageStamp links; Deep/3D stream nodes use NoOp links (canSetInput probe) — v1.0
- ✓ Camera links no longer produce PostageStamp when pasted — v1.0
- ✓ Link nodes reconnect to an anchor of the same name when pasted into another script — v1.0
- ✓ Hidden-input Dot nodes do not reconnect cross-script (leave disconnected cleanly) — v1.0
- ✓ DAG position saved when navigate-to-anchor (Alt+A) invoked; Alt+Z returns to that position — v1.0
- ✓ Tabtabtab reads actual `tile_color` knob value — not re-derived from backdrop/input logic — v1.0
- ✓ Anchor creation and rename dialogs include color picker (ColorPaletteDialog) — v1.0
- ✓ Color picker button/knob on anchor node itself — v1.0
- ✓ Anchor color change via picker propagates to all linked nodes — v1.0
- ✓ Anchor navigation picker (Alt+A) includes labelled BackdropNodes as navigable targets — v1.0
- ✓ DOT_TYPE knob stamps Link Dots (anchor-backed) vs Local Dots (plain-node-backed) at copy time — v1.0
- ✓ Dot anchor node names carry Anchor_ prefix; rename syncs node name and link FQNNs — v1.0
- ✓ Preferences persisted to `~/.nuke/paste_hidden_prefs.json` (plugin_enabled, link_classes_paste_mode, custom_colors); first-run file materialization — v1.1
- ✓ One-way migration from legacy `paste_hidden_user_palette.json` into new prefs file — v1.1
- ✓ Plugin-enabled gating: clipboard/anchor/label entry points pass through to Nuke defaults when disabled — v1.1
- ✓ LINK_CLASSES passthrough mode: plain Nuke copy with no FQNN stamp when link_classes_paste_mode is passthrough — v1.1
- ✓ Preferences... dialog in Anchors menu; plugin toggle and paste-mode toggle persist across sessions — v1.1
- ✓ Custom color CRUD (Add/Edit/Remove) in PrefsDialog; custom colors in picker swatch group — v1.1
- ✓ Click-to-select ColorPaletteDialog: swatch highlight without closing, OK/Enter confirms, groups ordered custom→backdrop→defaults, initial color pre-highlighted — v1.1
- ✓ Test suite centralized stub library (`tests/stubs.py` + `conftest.py`) — 132 tests green under flat discovery — v1.2
- ✓ BUG-01: NoOp links pasted cross-script receive anchor's `tile_color` (not default purple) — v1.2
- ✓ BUG-02: Anchor pasted cross-script stays as anchor node — v1.2
- ✓ Zero ruff violations (E, F, W, B, C90, I, SIM) across all 10 source files; FROZEN annotations on 8 serialized knob constants — v1.2
- ✓ Tag-triggered GitHub Actions CI/CD: pytest gate → versioned ZIP (explicit manifest) → GitHub Release — v1.2
- ✓ `nuke -t` validation scripts probing stub alignment and cross-script paste behavior; two divergences corrected — v1.2
- ✓ Project renamed from `paste_hidden` to `anchors` across all source, tests, CI, and GitHub repo — v1.3
- ✓ BUG-03: Anchor creation dialog name reliably applied to node every time — v1.3
- ✓ BUG-04: "a" on Dot node creates NoOp-based anchor (not Dot anchor) — v1.3
- ✓ Configurable regex + template for default anchor name derived from file knob, with live validity indicator and fallback — v1.3
- ✓ PrefsDialog Anchor Naming fully polished: collapsible Advanced section, live preview, undoable Reset, Publish button — v1.3
- ✓ Site-level config via `ANCHORS_SITE_CONFIG` env var: two-layer prefs system with per-field lock/override checkbox — v1.3
- ✓ Always-enabled Publish button with file save dialog; `last_publish_path` persists across sessions — v1.3
- ✓ Public `api.py` module: `create_anchor()`, `find_anchor_by_name()` with NumPy docstrings and `__all__` stable surface — v1.3
- ✓ All plugin operations (copy/paste, anchor creation, link creation, navigation) work correctly inside Group nodes via `all_nodes_in_context()` helper — v1.4
- ✓ A-key link creation inside Group nodes uses pre-captured `lastHitGroup()` context — v1.4
- ✓ Alt+A navigation inside Group nodes pans/zooms the correct Group DAG panel via `QTimer.singleShot(0, ...)` — v1.4
- ✓ Quick Start guide at `docs/quick-start.md` covering anchor creation, navigation, and copy/paste with screenshot placeholders — v1.4

### Active

(None — v1.4 complete. Next milestone requirements TBD via `/gsd:new-milestone`.)

### Out of Scope

- Undo/redo stack integration — Nuke API complexity, not requested
- Cross-script reconnection for hidden-input Dot nodes — explicitly excluded (Dots are positional/ad-hoc)
- Backdrops as link targets — navigate-only (no connectable outputs)
- External persistence (database, remote API) — local-only plugin
- Multi-user / shared anchor libraries — single-artist tool

## Context

**v1.4 shipped 2026-03-23.** Codebase: ~10,800 LOC Python total (source + tests). v1.4 touched 52 files (32 commits over 2 days). `docs/quick-start.md` added as first end-user documentation.

**Source files:** `anchors.py`, `anchor.py`, `api.py`, `colors.py`, `constants.py`, `menu.py`, `prefs.py` (7 source files). `api.py` added in v1.3 as stable public surface.

**Tests:** Extended to cover anchor naming, site config, prefs round-trips, and public API. `tests/test_prefs.py` is now 700+ lines (primary prefs + naming + site config + publish coverage).

**Tech stack:** Python 3 (Nuke embedded), PySide2/PySide6 (Qt guard for headless), ruff for linting (zero violations), GitHub Actions for CI/CD. No external runtime dependencies.

**Architecture:** Source files now under `anchors` namespace. Two-layer prefs system: effective vars (what plugin uses) and shadow vars (what user set; diverge when site config is active). Site config loaded from `ANCHORS_SITE_CONFIG` env var at import. `api.py` is a thin delegation layer over `anchor.py` with no logic duplication; `__all__` declares stable public surface.

**TDD infrastructure:** `tests/stubs.py` (StubNode/StubKnob/make_stub_nuke_module), `tests/conftest.py` (shared stub installation for pytest flat discovery), `tests/__init__.py` (idempotent stub installation for unittest discover). Tests pass under both `pytest tests/` and `python3 -m unittest discover -s tests/ -t .`.

## Constraints

- **Runtime**: Nuke 14+ embedded Python (2.7+/3.x); no external package manager
- **UI**: PySide2/PySide6 conditional — all Qt code must degrade gracefully if Qt unavailable
- **Dependencies**: No dependencies beyond Nuke bundled runtime (`nuke`, `nukescripts`, Qt)
- **State**: Node state via knobs; user preferences via `~/.nuke/paste_hidden_prefs.json` only
- **Compatibility**: Changes must not break existing anchors/links in saved `.nk` scripts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hidden-input Dots and Links are distinct systems with different semantics | Dots are ad-hoc; Links are named references. Conflating them causes inconsistent reconnection | ✓ Good — DOT_TYPE knob at copy time gates all paste behavior |
| PostageStamp preferred for 2D links; NoOp as fallback for all | PostageStamp doesn't work for Deep/3D streams; NoOp always works | ✓ Good — canSetInput probe correctly classifies arbitrary node types |
| Color propagation only from our color picker, not raw tile_color changes | Low-stakes; user who bypasses the picker accepts stale link colors | ✓ Good — accepted by design |
| Backdrop anchors are navigate-only, not link targets | Backdrops don't have connectable outputs | ✓ Good |
| Cross-script reconnection for Links (by name), not for Dots | Dots are positional/ad-hoc; Links are intentional named references | ✓ Good — FQNN stem comparison prevents same-stem false positives |
| Detect link class once at anchor creation time, cache on hidden knob | Avoids repeated channel inspection overhead at paste time | ✓ Good |
| canSetInput probe replaces channel-prefix heuristic | Nuke API answers definitively for any node class; heuristic was fragile | ✓ Good — generically correct for all future node types |
| NAV-03 (full forward/back history stack) deferred to v2 | Single-slot back covers primary use case; full stack adds complexity | — Pending v2 decision |
| FQNN stem comparison as cross-script gate for Dot paste | Prevents same-stem false positives (Bug 2) that find_anchor_node() misses | ✓ Good |
| Module-level prefs singleton loaded at import; save() owned by PrefsDialog | No class needed; downstream consumers import prefs directly; save() not auto-called inside prefs.py | ✓ Good — circular import prevented via constructor injection and local imports |
| Constructor injection for custom_colors into ColorPaletteDialog | Colors.py has zero knowledge of prefs.py; callers pass prefs.custom_colors at call time | ✓ Good — no circular import |
| link_classes_paste_mode gate in copy_hidden() with continue (not return) | Passthrough allows plain nuke.nodeCopy() at end of function to handle the node | ✓ Good — correct passthrough semantics |
| QPalette.Highlight for swatch selection border | Theme-aware; hardcoded white would be invisible on light themes | ✓ Good |
| _persist_custom_colors_from_dialog() helper consolidates all three ColorPaletteDialog call sites | Prevents duplication; only saves when staged colors differ from prefs | ✓ Good |
| Working-copy pattern in PrefsDialog: seed locals at open, flush to module vars only on OK | Cancel leaves prefs unchanged; no accidental writes | ✓ Good |
| Centralized stub library pattern: stubs.py + conftest.py + __init__.py (idempotent) | Flat discovery required single installation point; conftest for pytest, __init__ for unittest | ✓ Good |
| StubNode.__getitem__ raises NameError (not KeyError) for missing knobs | Real Nuke 16.0v6 raises NameError('knob X does not exist') — stub must match exception type | ✓ Good |
| toNode('preferences') returns MagicMock in stubs (side_effect lambda) | Real Nuke always has a preferences node; None caused test divergence | ✓ Good |
| BUG-02 clipboard SKIP (not FAIL) in nuke -t validation | nuke.nodeCopy raises RuntimeError in headless mode; BUG-02 covered by offline pytest | ✓ Good |
| softprops/action-gh-release@v2 for GitHub Release publication | native generate_release_notes support; cleaner YAML than gh CLI alternative | ✓ Good |
| Explicit 10-file cp manifest in CI ZIP step (not wildcard) | Prevents stubs/__init__.py and dev artifacts from entering release artifact | ✓ Good |
| FROZEN annotation pattern on serialized knob constants | Documents that renaming these would break existing artist .nk files; zero-cost guardrail | ✓ Good |
| paste_hidden() / copy_hidden() C901 complexity deferred with noqa | Structural refactoring too risky immediately after BUG-01/BUG-02 fixes; accept technical debt | ⚠️ Revisit |
| Migration path (OLD_PREFS_PATH) in constants.py for test patching | Tests can patch the constant before reimport; avoids hardcoded path in prefs.py | ✓ Good |
| BUG-03 fix: ColorPaletteDialog.accept() override + remove scattered chosen_name assignments | Dialog name was overwritten by post-accept code; single accept() override is canonical | ✓ Good |
| BUG-04 fix: remove Dot elif branch from anchor_shortcut() | Dot nodes fall through to elif selected: → create_anchor(), consistent NoOp-based creation | ✓ Good |
| Working-copy naming pattern: seed _local_naming_* in __init__, flush on _on_accept | Consistent with existing PrefsDialog working-copy pattern; cancel leaves prefs unchanged | ✓ Good |
| Collapsible Advanced section via QPushButton + QWidget.setVisible() | Flat button with triangle arrows; no custom widget needed; compatible with lock/unlock UI | ✓ Good |
| Two-layer prefs system: effective vars + _user_naming_* shadow vars | Separates what site config locked from what the user set; both layers preserved correctly | ✓ Good |
| path-priority chain: env var > last_publish_path > '/' for dialog pre-fill | Respects explicit env var config while remembering last used path for convenience | ✓ Good |
| api.py as thin delegation layer over anchor.py with sys.modules guard | No logic duplication; guard raises RuntimeError early in non-Nuke sessions without try/import | ✓ Good |
| __all__ at module bottom declares stable public surface of api.py | Explicit exports prevent internal symbols leaking into callers' namespaces | ✓ Good |
| Single `all_nodes_in_context()` helper in link.py replaces all bare `nuke.allNodes()` calls | Consistent, testable, single point of truth for Group-context node scanning across link.py, anchor.py, labels.py | ✓ Good |
| Pre-capture `lastHitGroup()` once at entry point (`anchor_shortcut()`), pass down call chain, set on plugin before `show()` | Prevents context drift when Qt event loop runs between callback and `get_items()`; stale root context was root cause of A-key failure | ✓ Good |
| `AnchorPlugin/AnchorNavigatePlugin.get_items()` reads `self._hit_group` (set externally), never overwrites it | Plugin reads context set before show(); overwriting inside get_items() was the original bug | ✓ Good |
| `QTimer.singleShot(0, _deferred_navigate)` defers `nuke.zoom()` until after picker closes and Qt restores DAG panel focus | Synchronous zoom fired while picker had focus, targeting the root DAG instead of the Group DAG panel | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-23 after v1.4 Group Support milestone complete*
