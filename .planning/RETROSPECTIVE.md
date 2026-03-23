# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-10
**Phases:** 5 | **Plans:** 13

### What Was Built
- Stream-type detection via canSetInput probe — arbitrary node classes classified correctly; Camera/3D → NoOp, 2D → PostageStamp
- Cross-script paste reconnection — Link nodes reconnect by anchor name in destination scripts; Local Dots leave disconnected cleanly
- Anchor color system — ColorPaletteDialog (PySide2/6) wired into creation and rename dialogs, anchor node knob button, and propagation to all linked nodes
- DAG navigation history — single-slot back (Alt+Z) restoring exact zoom+center; BackdropNodes included in Alt+A picker
- DOT_TYPE knob distinction — formal stamp at copy time eliminates cross-script false positives between Link Dots and Local Dots

### What Worked
- **TDD-first approach** worked extremely well: 74+ offline unit tests caught all integration bugs before they reached the Nuke session. Plans with RED/GREEN cycles had zero regressions from prior phases.
- **canSetInput probe pattern** was more reliable than channel-prefix heuristic. Writing a probe against Nuke's own API eliminated the brittleness of string-matching channel names.
- **Phase SUMMARY.md structure** with dependency graph, key decisions, and patterns-established made Phase 5 bug-tracing fast — DOT_TYPE bugs were found in 01-02-SUMMARY decisions within 30 seconds.
- **Yolo mode** allowed rapid plan execution with human checkpoints only where UAT required a Nuke session. Plans averaged 3–5 min each.
- **Offline nuke stub pattern** (StubNode/StubKnob with configurable dict) enabled full paste logic testing without Nuke. Established early in Phase 1, reused through Phase 5 with incremental extensions.

### What Was Inefficient
- **Phase 3 ROADMAP.md checkbox stayed unchecked** — the progress table showed "Not started" for Phase 3 even after it completed. Minor but added a gap-closure doc plan (04-03) that could have been avoided with a doc discipline habit.
- **Qt stub ordering conflict in test discovery** — when running the full suite with `python3 -m unittest discover`, cross-test Qt stub interference caused 4–8 errors. Individual files pass. Fix deferred, but cost time in Phase 3 and 4 diagnoses. Should be fixed once rather than documented as "known" each time.
- **Phase 5 was Phase 2 rework** — Phase 5 fixed two bugs confirmed in Phase 2 UAT that weren't caught by Phase 2's offline tests. Adding a "same-stem false positive" test scenario in Phase 2 would have caught this earlier and eliminated Phase 5.

### Patterns Established
- **Offline nuke stub**: `make_stub_nuke_module()` with StubNode/StubKnob + Qt/tabtabtab module stubs before local imports. Extend per-plan with domain methods (zoom, center, setName, etc.).
- **allNodes side_effect dispatch**: `def _side(class_name=None): return backdrops if class_name == 'BackdropNode' else anchors` — discriminates multi-class queries in a single mock.
- **Detect-once-at-creation pattern**: expensive detection results cached on hidden knob at creation; cheap knob reads at paste time.
- **saved_xxx pattern**: read knob value before a stripping call, re-stamp after. Used for DOT_TYPE preservation across setup_link_node().
- **Backward compat inference fallback**: nodes lacking a typed knob infer type from FQNN structure (anchor-prefix → link type; plain → local type).
- **FQNN stem comparison for cross-script gate**: comparing stored FQNN stem against current script name rather than trusting find_anchor_node() return value, prevents same-stem false positives.

### Key Lessons
1. **Phase 5 could have been avoided**: when UAT found cross-script Dot bugs, they were architectural — Local vs Link Dot — not implementation bugs. Including a "same-stem cross-script paste" test in Phase 2 would have caught this at the plan level.
2. **Test discovery ordering is a real problem**: Qt stub ordering conflicts in flat discovery are not "acceptable known issues" — they obscure real failures. Fix with a conftest.py or test infrastructure plan before v1.1.
3. **Planning document discipline**: update ROADMAP.md checkboxes and progress table immediately when a phase completes, not retroactively. A 5-second update prevents a correction plan.
4. **Yolo mode + TDD is fast**: the combination of automated plan execution and RED/GREEN TDD cycles produced reliable, well-tested code with minimal rework.

### Cost Observations
- Model: claude-sonnet-4-6 (100%)
- Sessions: multiple (separated by phase)
- Notable: Plans with TDD RED/GREEN cycles averaged 3–5 min. Plans without tests (doc-only) averaged 1 min. canSetInput probe (01-03) took 4 min and replaced a fragile heuristic permanently.

---

## Milestone: v1.1 — Polish

**Shipped:** 2026-03-12
**Phases:** 2 | **Plans:** 8

### What Was Built
- JSON-backed prefs singleton (`prefs.py`) — module-level vars loaded at import, `save()` owned by PrefsDialog; first-run file materialization via `save()` call in `_load()` absent branch
- One-way migration from legacy `paste_hidden_user_palette.json` into new prefs file; old file never written again
- Plugin-enabled gating on all clipboard, anchor, and label entry points; LINK_CLASSES passthrough mode (`continue` in Path A loop)
- `ColorPaletteDialog` redesign: click-to-select, OK button, group reordering (custom→backdrop→defaults), custom color staging via `chosen_custom_colors()`, QPalette.Highlight for selection border
- `PrefsDialog` with plugin toggle, paste-mode toggle, custom color CRUD (Add/Edit/Remove), working-copy pattern on open/accept
- `Preferences...` menu entry (ungated); `_persist_custom_colors_from_dialog()` helper consolidates custom color persistence across all 3 ColorPaletteDialog call sites

### What Worked
- **Constructor injection for custom_colors** cleanly prevented circular import between `colors.py` and `prefs.py` — `colors.py` has zero knowledge of `prefs.py`. Established early in 06-02, paid off through all Phase 7 work.
- **Working-copy pattern in PrefsDialog** (seed locals at open, flush only on OK) kept the state model simple and correct. No accidental writes to `prefs.*` on cancel.
- **UAT-driven bug-fix cycle in Phase 7-03** was thorough — 5 bugs found and fixed in a single structured UAT pass, each with a regression test. The regression tests caught real issues before they reached the next session.
- **AST method extraction pattern** (`_extract_method_from_source`) worked well for testing Qt-stubbed class methods offline — avoided MagicMock return value ambiguity.
- **Gap closure plan (06-05)** addressed a real UAT finding cleanly with TDD: one RED commit, one GREEN commit, three tests. Minimal scope.

### What Was Inefficient
- **PrefsDialog initialization order bug** (AttributeError on `_edit_button`) should have been caught by unit test at plan time, not UAT. The plan had explicit success criteria about opening the dialog without crashes; an offline test for `_update_edit_remove_buttons()` attribute references would have caught this in 06-04's write.
- **PANEL-01 checkbox** was not ticked in REQUIREMENTS.md after Phase 7-03 implemented the menu entry. A 5-second update prevents a gap at milestone completion — same lesson as v1.0's Phase 3 checkbox.
- **`QDialogButtonBox` replaced entirely** with explicit OK/Cancel buttons after UAT showed `QDialogButtonBox` didn't respond as expected to Tab in Nuke's event filter environment. Would have been faster to use explicit buttons from the start for a Nuke plugin context.

### Patterns Established
- **Module-level prefs singleton**: `import prefs` at module level; `prefs.plugin_enabled` etc. read directly. No class needed. `save()` never auto-called inside `prefs.py` — only on explicit accept.
- **Local import for circular import prevention**: `from paste_hidden import menu` inside `_on_accept` (not at module top) prevents `colors.py → prefs.py → menu.py` chain. Document in method-level comment.
- **`_persist_custom_colors_from_dialog()` helper**: consolidate caller-side custom color save at all `ColorPaletteDialog.exec()` accept sites — read `chosen_custom_colors()`, compare to `prefs.custom_colors`, call `prefs.save()` only if different.
- **QPalette.Highlight for theme-aware selection**: use `self.palette().color(QtGui.QPalette.Highlight).name()` for selection borders — hardcoded colors are invisible on non-default themes.
- **Buttons before populate**: in any dialog where `_update_*_buttons()` is called inside `_populate_*()`, always create button widgets before calling `_populate_*()` in `_build_ui()`. Enforce with an AST line-number test.

### Key Lessons
1. **Plan-time tests for initialization order**: any dialog method that calls another method which references `self._widget_attr` must have a test verifying the attribute exists at that call time. Catches `AttributeError` at write time, not UAT.
2. **Prefer explicit buttons over QDialogButtonBox in Nuke context**: Nuke's event filter intercepts Tab and Enter in ways QDialogButtonBox doesn't handle predictably. Explicit QPushButton with `setAutoDefault(False)` is more reliable.
3. **REQUIREMENTS.md checkbox discipline**: tick the checkbox the moment the feature passes UAT. Pre-archive gap review should be a 30-second scan, not a forensic investigation.
4. **Test discovery ordering still unresolved**: 4–8 errors in flat discovery persist from v1.0. This is now two milestones old — should be the first plan in the next milestone if tests are a priority.

### Cost Observations
- Model: claude-sonnet-4-6 (100%)
- Sessions: multiple (separated by phase)
- Notable: Phase 7-03 took 35 min (longest plan across both milestones) due to the 5-UAT-bug fix cycle. All other plans averaged 2–8 min. UAT bug fix cycles are worth the time — zero regressions after.

---

## Milestone: v1.2 — Hardening

**Shipped:** 2026-03-15
**Phases:** 5 | **Plans:** 9

### What Was Built
- Centralized test stub library (`tests/stubs.py` + `conftest.py` + idempotent `__init__.py`) — eliminated Qt ordering conflicts, 132 tests green under both pytest flat discovery and unittest discover
- BUG-01 fix: removed ANCHOR_DEFAULT_COLOR overwrite after `setup_link_node()` in cross-script link paste — `setup_link_node()` already sets anchor's real color
- BUG-02 fix: replaced anchor-to-link replacement block with `continue` — anchor pasted cross-script stays as anchor, no link substitution
- Zero ruff violations (E, F, W, B, C90, I, SIM) across all 10 source files via `pyproject.toml`; FROZEN annotations on 8 serialized knob constants
- GitHub Actions release workflow: tag-triggered pytest gate → explicit 10-file ZIP manifest → GitHub Release via softprops/action-gh-release@v2
- `nuke -t` validation scripts: 25 stub alignment checks + 3 cross-script paste smoke tests; two divergences corrected (NameError, preferences MagicMock)

### What Worked
- **Fixing the test discovery ordering first (Phase 8)** paid immediate dividends — all subsequent phases had a reliable 130-test green baseline as a regression gate. The v1.0/v1.1 deferred fix was the right call to make first in v1.2.
- **Explicit toNode side_effect lambda** (`lambda name: MagicMock() if name == 'preferences' else None`) was a clean pattern for discriminated stub returns — no conditional logic in production code, just stub precision.
- **SKIP (not FAIL) for headless clipboard** in validation scripts was the correct design decision — documented why, and BUG-02 coverage is maintained by offline pytest independently.
- **Audit-before-archive** (`/gsd:audit-milestone`) produced a well-structured audit report that made the completion steps straightforward — gaps were pre-categorized as tech_debt vs blocking.

### What Was Inefficient
- **Phase 9 plan checkbox state in ROADMAP.md** was already wrong at phase creation — checkboxes left as `[ ]` when plans were already complete. Same ROADMAP.md discipline issue from v1.0 and v1.1: three milestones in a row.
- **Nyquist validation was drafted but not executed** for any of the 5 phases. VALIDATION.md files exist in draft state. Either run Nyquist or don't create the file — a draft VALIDATION.md creates false confidence that validation happened.
- **Progress table rows 9–12** had malformed columns (Milestone column used for Plans Complete count). Minor formatting debt in ROADMAP.md that propagated to archive.

### Patterns Established
- **Centralized stub installation**: `conftest.py` (pytest session scope) + `__init__.py` (idempotent, unittest -t .) — never per-file. One canonical place to add stub methods.
- **NameError (not KeyError) for missing knob access**: real Nuke raises `NameError('knob X does not exist')` — stubs must match exception type, not generic Python defaults.
- **Validation script resilience pattern**: `try/except RuntimeError: SKIP` for clipboard/GUI-dependent operations in headless nuke -t; separate offline pytest covers behavior correctness.
- **per-file-ignores in pyproject.toml for vendored code**: `tabtabtab.py` and `menu.py` (string-eval callbacks) need targeted suppression; never apply project-wide noqa to accommodate vendored/special-case files.
- **FROZEN annotation above serialized constants**: `# FROZEN: value stored in .nk files — do not rename` — zero-cost guardrail against casual renaming.

### Key Lessons
1. **Fix deferred infrastructure debt at the start of the milestone**: Phase 8 (test centralization) was the correct first phase — it made every subsequent phase more reliable. Deferred infrastructure debt compounds.
2. **Nyquist validation: run it or skip it** — don't create draft VALIDATION.md files. A draft signals "someone planned to validate" not "this was validated." Either execute Nyquist or leave the file absent.
3. **ROADMAP.md progress table discipline**: the milestone/plans column confusion in rows 9–12 happened because the table was copied without updating column alignment. Template should enforce column order.
4. **Explicit file manifests beat wildcards**: the CI ZIP step's 10-file `cp` manifest prevented test artifacts from entering the release. Wildcards are convenient but dangerous for release artifacts.

### Cost Observations
- Model: claude-sonnet-4-6 (100%)
- Sessions: multiple (separated by phase)
- Notable: Phase 12 (nuke -t validation) required a real Nuke 16.0v6 session — two divergences found and corrected. Plans requiring live runtime validation take longer but produce high-confidence stub alignment.

---

## Milestone: v1.3 — Foundations

**Shipped:** 2026-03-18
**Phases:** 7 (13, 14, 15, 15.1, 16, 16.1, 17) | **Plans:** 17

### What Was Built
- Project renamed from `paste_hidden` to `anchors` across all source, tests, CI, and GitHub repo; migration path for old prefs file via `OLD_PREFS_PATH` in `constants.py`
- BUG-03: anchor creation dialog name reliably applied via `ColorPaletteDialog.accept()` override; scattered `chosen_name` assignments removed
- BUG-04: Dot→NoOp anchor dispatch fixed by removing `elif Dot` branch from `anchor_shortcut()`; five regression tests
- Configurable regex + template anchor naming: `suggest_anchor_name()` backend with named capture groups; live validity indicator and Reset button in PrefsDialog
- PrefsDialog Anchor Naming polished: live preview label, undoable Reset, `naming_demo_filename` persistence, Publish button, collapsible Advanced section (QPushButton + QWidget.setVisible())
- Site-level config system: `ANCHORS_SITE_CONFIG` env var, two-layer prefs (effective vars + `_user_naming_*` shadow vars), lock/unlock UI with override checkbox in PrefsDialog
- Always-enabled Publish button with `QFileDialog.getSaveFileName` flow; `last_publish_path` persists to prefs for first-time site config creation
- `api.py` public module: `create_anchor()`, `find_anchor_by_name()`, `sys.modules` guard, `__all__` stable surface, NumPy-style docstrings

### What Worked
- **Two inserted decimal phases (15.1, 16.1)** handled cleanly — the decimal phase pattern is fully proven. No disruption to phase 16 or 17 numbering.
- **Two-layer prefs system** (shadow vars + effective vars) was the right design for site config — PrefsDialog seeds from shadow vars, flushes to shadow vars on OK, then calls `_apply_effective_naming_values()`. Clear separation prevents shadow/effective confusion.
- **Collapsible Advanced section pattern** (flat QPushButton with triangle arrows + `QWidget.setVisible()`) added no custom widget overhead and integrates cleanly with the lock/unlock pattern from Phase 16.
- **api.py thin delegation** with `sys.modules` guard was correct — no logic duplication with `anchor.py`; `__all__` makes the public surface explicit at a glance.
- **path-priority chain** for Publish dialog (env var → last_publish_path → '/') covered all cases without branching logic in the UI.

### What Was Inefficient
- **Phase 16.1 revert cycle**: two commits were needed for the `DontConfirmOverwrite` fix — the initial diagnosis was wrong (thought the flag prevented overwrite confirmation, but Qt was returning empty path). A QFileDialog.result() check would have caught this faster. The revert + rediagnosis added one iteration.
- **No milestone audit (v1.3-MILESTONE-AUDIT.md)** — milestone completed without the pre-archive audit step. All requirements were 13/13 checked off, so it was safe to proceed, but the audit would have caught any integration gaps between api.py and the public surface.
- **ROADMAP.md plan checkboxes still `[ ]` at phase completion** — same discipline failure as v1.0, v1.1, v1.2. The plans were complete (SUMMARY.md existed) but the ROADMAP.md plan list kept `[ ]`. Four milestones of the same issue.

### Patterns Established
- **Migration path in constants.py**: `OLD_PREFS_PATH = ...` gives tests a patchable constant before reimport — avoids hardcoded paths in `prefs.py`.
- **Collapsible section via QPushButton + QWidget**: `▶`/`▼` flat button toggles a plain `QWidget` container; no custom widget; rows moved to inner `QVBoxLayout` with zero margins.
- **Two-layer prefs for site config**: effective vars (`naming_regex`, `naming_template`) are what the plugin uses; `_user_naming_*` shadow vars are what the user set. Flush shadow → effective via `_apply_effective_naming_values()` on every accept.
- **sys.modules guard over try/import**: `_assert_nuke_session` checks `sys.modules['nuke']` rather than `try: import nuke` — cleaner, no side effects.
- **NumPy-style docstrings + __all__**: Parameters, Returns, Raises, Examples in all public functions; `__all__` at module bottom declares the stable surface explicitly.

### Key Lessons
1. **QFileDialog.getSaveFileName returns empty string on cancel or overwrite-declined** — always check the returned path before calling downstream publish logic. `DontConfirmOverwrite` is not the right fix for overwrite handling; just let Qt's default dialog handle it.
2. **Run the milestone audit**: even with 13/13 requirements checked, the audit would have verified cross-phase integration (api.py → anchor.py wiring, site config → prefs dialog interactions). Missing it is a gap in the completion ritual.
3. **ROADMAP.md plan checkbox discipline: still unresolved after 4 milestones.** Either automate the checkbox update when SUMMARY.md is created, or accept that ROADMAP.md plan lists are decorative (not a progress gate) and stop flagging it as an issue.
4. **Decimal phase insertion works well for mid-stream scope additions** — 15.1 and 16.1 both had clear scope boundaries and didn't create confusion about their relationship to the parent phases.

### Cost Observations
- Model: claude-sonnet-4-6 (100%)
- Sessions: multiple (separated by phase)
- Notable: Phase 16.1 required a revert + rediagnosis cycle (2 extra commits). Phases 15–16 were the most complex UI work in any milestone — PrefsDialog has significant accumulated surface area. Phase 17 (public API) was the fastest in the milestone (~2 plans, thin delegation pattern).

---

## Milestone: v1.4 — Group Support

**Shipped:** 2026-03-23
**Phases:** 2 (18, 19) | **Plans:** 5

### What Was Built
- `all_nodes_in_context()` helper in `link.py` — single Group-context-aware `nuke.allNodes()` wrapper; all bare calls replaced across link.py, anchor.py (8 sites), and labels.py
- Pre-capture `lastHitGroup()` pattern: capture once at entry point (`anchor_shortcut()`), pass down call chain, set on plugin before `show()` — fixes A-key link creation inside Group nodes (GROUP-02)
- `QTimer.singleShot(0, _deferred_navigate)` in `AnchorNavigatePlugin.invoke()` — defers `nuke.zoom()` until Qt restores DAG panel focus after picker closes (GROUP-04)
- Quick Start guide at `docs/quick-start.md`: concept intro, anchor creation (5 sub-workflows), Alt+A navigation (picker, zoom, Alt+Z back), copy/paste semantics; 7 PNG screenshot placeholders

### What Worked
- **`all_nodes_in_context()` single helper pattern** was the right call — one change in `link.py`, propagated cleanly through imports in `anchor.py` and `labels.py`. Avoided 8 scattered context-passing decisions.
- **Pre-capture pattern for Group context** (capture at entry point, pass explicitly) was clean and traceable through the call chain. Debugging was straightforward because the group context flows visibly through function signatures.
- **Symmetrical fix applied to both plugins**: applying the same pre-capture fix to both `AnchorPlugin` and `AnchorNavigatePlugin` in plan 18-03 was correct — the verification grep caught the second instance before it would have shown up in UAT.
- **QTimer deferred navigation** was simple and correct — zero-delay timer fires on the next event loop tick, which is sufficient for Qt to restore DAG panel focus. No custom signal plumbing needed.
- **Phase 19 (documentation) completed in ~1 min** — small, focused scope with clear success criteria. Documentation phases don't need TDD overhead.

### What Was Inefficient
- **UAT found 2 gaps after plan 18-02** (A-key Group context + Alt+A navigation zoom), requiring 2 additional gap-closure plans (18-03, 18-04). The root causes were predictable — `get_items()` was called before Qt restored context, and `invoke()` fired `nuke.zoom()` while picker still had focus. A more thorough initial analysis of Qt event loop timing would have caught these.
- **No milestone audit run** — proceeded without `v1.4-MILESTONE-AUDIT.md`. All 8/8 requirements were checked off and the milestone was small, but the audit would have verified that Group context is tested E2E across all entry points.
- **ROADMAP.md plan checkboxes 18-03 and 18-04** were `[ ]` even though they completed — same checkbox discipline failure as v1.0–v1.3. Five milestones in a row. The ROADMAP.md plan list is effectively decorative.

### Patterns Established
- **Group-context helper pattern**: `all_nodes_in_context(node_class=None)` wrapping `nuke.allNodes()` with `group=nuke.thisGroup()` — one import, replaces all bare call sites.
- **Pre-capture pattern for Group context**: `hit_group = nuke.lastHitGroup()` at entry point, before any `with`-blocks or Qt event loop calls; pass explicitly down call chain; set `plugin._hit_group = hit_group` before widget `show()`.
- **Plugin reads context, never writes it in get_items()**: `get_items()` reads `self._hit_group` (pre-set externally), never calls `nuke.lastHitGroup()` inside — the capture belongs at the entry point.
- **Deferred Qt operation pattern**: `QTimer.singleShot(0, closure)` for operations that need correct Qt focus state after a widget closes — zero-delay is sufficient for post-event-loop restoration.
- **Screenshot placeholder format**: `![Descriptive alt text of what screenshot should show](img/filename.png)` — lightweight, restruct-free; add real screenshots by replacing the file without editing the Markdown.

### Key Lessons
1. **Qt event loop timing for Group context**: any operation that relies on `nuke.lastHitGroup()` or `nuke.zoom()` after a widget interaction must account for the event loop restoring focus. Pre-capture before `show()` and post-defer after `close()` are the two patterns.
2. **Symmetrical fixes**: when fixing a bug pattern in one class, grep for the same pattern in sibling classes before closing the plan. Caught the `AnchorNavigatePlugin` case before UAT would have found it.
3. **Documentation phases are fast**: with clear success criteria and no runtime logic, a documentation phase completes in 1–2 min. No need to plan for TDD or infrastructure overhead.
4. **ROADMAP.md plan checkboxes: accept as decorative.** Five milestones without fixing this is signal — the SUMMARY.md is the authoritative completion record, not the ROADMAP.md plan list. Stop tracking it as an issue.

### Cost Observations
- Model: claude-sonnet-4-6 (100%)
- Sessions: multiple (separated by phase)
- Notable: Phase 18 required 4 plans instead of the planned 2 due to UAT gap closure. Plans 18-03 and 18-04 were each ~5 min — root causes were isolated by the time they were planned. Phase 19 (docs) was ~1 min.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 13 | Initial milestone — established TDD stub pattern, yolo mode, DOT_TYPE architecture |
| v1.1 | 2 | 8 | Prefs system, UI dialogs, UAT-driven bug fix cycle; constructor injection prevents circular import |
| v1.2 | 5 | 9 | Infrastructure hardening — test centralization, bug fixes with regression tests, CI/CD, stub alignment |
| v1.3 | 7 | 17 | Project rename, configurable naming, site config, public API; decimal phase insertions × 2 |
| v1.4 | 2 | 5 | Group context support via helper pattern + pre-capture; QTimer deferred navigation; Quick Start docs |

### Cumulative Quality

| Milestone | Tests | Zero-Dep Additions |
|-----------|-------|--------------------|
| v1.0 | 74+ | 0 (no new external deps) |
| v1.1 | 100+ | 0 (no new external deps) |
| v1.2 | 132 | 0 (ruff dev-only; no runtime deps) |
| v1.3 | 150+ | 0 (no new external deps) |
| v1.4 | 210+ | 0 (no new external deps) |

### Top Lessons (Verified Across Milestones)

1. TDD offline stubs pay for themselves — caught architectural issues before Nuke sessions
2. Fix deferred infrastructure debt at the start of the milestone — test stability unlocks all subsequent phases
3. UAT-driven fix cycles with regression tests (v1.1 Phase 7-03, v1.2 Phase 9) produce zero post-merge regressions
4. REQUIREMENTS.md checkbox discipline: tick on UAT pass, not at archive time (failed 3 milestones in a row — automate or ritualize)
5. Explicit file manifests beat wildcards for release artifacts — prevents accidental inclusion of dev artifacts
6. Run the milestone audit before archiving — even with all requirements checked, cross-phase integration gaps may exist
7. Decimal phase insertions (15.1, 16.1) work cleanly — use them for mid-stream scope additions without disrupting numbering
8. Qt event loop timing matters for Group context: pre-capture `lastHitGroup()` at entry point before any `with`-blocks; defer `nuke.zoom()` via `QTimer.singleShot(0, ...)` after widget closes
