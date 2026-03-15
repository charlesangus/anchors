# paste_hidden

## What This Is

`paste_hidden` is a Foundry Nuke plugin that replaces Nuke's native clipboard system with one that intelligently handles hidden inputs, and adds a named anchor/link reference system for navigating and reusing node graph connections. It is used by a single VFX artist to manage complex compositing node graphs.

**v1.0 shipped:** Clear paste semantics for all node types, cross-script anchor reconnection, anchor color system with palette dialog, DAG navigation history (Alt+Z back), backdrop navigation inclusion, DOT_TYPE-gated Dot subtype distinction, 74+ offline unit tests.

**v1.1 shipped:** JSON-backed prefs singleton (plugin_enabled, link_classes_paste_mode, custom_colors), plugin-wide enable/disable gating, LINK_CLASSES passthrough mode, click-to-select ColorPaletteDialog, PrefsDialog with full custom color CRUD, and Preferences... menu entry.

**v1.2 shipped:** 132-test suite with centralized stub infrastructure (tests/stubs.py + conftest.py), BUG-01/BUG-02 cross-script paste fixes with regression tests, zero ruff violations across all 10 source files, tag-triggered GitHub Actions CI/CD (pytest gate + versioned ZIP + GitHub Release), and nuke -t validation scripts confirming stub alignment to real Nuke 16.0v6.

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

### Active

- [ ] Full browser-style forward/back navigation history stack (NAV-03)
- [ ] Manual `tile_color` changes by user propagate to link nodes (COLOR-V2-01)

### Future

- [ ] Undo/redo stack integration (out of scope; Nuke API complexity)

### Out of Scope

- Undo/redo stack integration — Nuke API complexity, not requested
- Cross-script reconnection for hidden-input Dot nodes — explicitly excluded (Dots are positional/ad-hoc)
- Backdrops as link targets — navigate-only (no connectable outputs)
- External persistence (database, remote API) — local-only plugin
- Multi-user / shared anchor libraries — single-artist tool

## Context

**v1.2 shipped 2026-03-15.** Codebase: ~3,089 LOC Python (10 source files), plus `tests/` (132 unit tests across 6 test files), `validation/` (2 nuke -t scripts), `.github/workflows/release.yml` (CI/CD pipeline).

Tech stack: Python 3 (Nuke embedded), PySide2/PySide6 (Qt guard for headless), ruff for linting (zero violations), GitHub Actions for CI/CD. No external runtime dependencies.

Architecture: Two systems unified under clear semantics — hidden-input Dots (positional, local-only reconnect) and named Link nodes (FQNN-tracked, cross-script reconnect by anchor name). DOT_TYPE knob stamps distinction at copy time. Link class determined once at anchor creation via canSetInput probe, cached on hidden knob. Prefs module is a module-level singleton loaded at import; `PrefsDialog` owns the persistence lifecycle (save() called only on OK).

TDD infrastructure: `tests/stubs.py` (StubNode/StubKnob/make_stub_nuke_module), `tests/conftest.py` (shared stub installation for pytest flat discovery), `tests/__init__.py` (idempotent stub installation for unittest discover). 132 tests pass under both `pytest tests/` and `python3 -m unittest discover -s tests/ -t .`.

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

---
*Last updated: 2026-03-15 after v1.2 milestone*
