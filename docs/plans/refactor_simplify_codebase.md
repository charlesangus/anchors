# Anchors plugin — refactor plan

## Context

The `anchors` Nuke plugin started life as `paste_hidden` (a Copy/Paste replacement) and grew into a full anchor-and-link system. The README still narrates that history; the codebase still carries fossils from it: knob names spelled `copy_hidden_*` and `paste_hidden_*`, two prefs/palette migrators, an orphaned `util.py`, a deprecated helper marked "do not call", repeated branching in copy/paste, and two near-identical TabTabTab plugin classes.

Functionality is correct today. The cost is readability and maintenance: `copy_anchors` and `paste_anchors` are explicitly `# noqa: C901`; renaming logic is duplicated for Dot vs NoOp anchors; copy/paste contains three near-identical "restore Local Dot appearance" blocks; and the FROZEN constants span three naming eras.

This plan delivers a behaviour-preserving refactor in five tranches that can each be reviewed and committed independently. Two small bugs are bundled in (user-confirmed). The previously-suspected "two anchors with the same name" reconnection bug is **not** a bug — Nuke guarantees `fullName` is unique per scope; the current code is correct.

## Codebase facts that anchor the plan

- `anchor.py` (1032), `anchors.py` (456), `colors.py` (1237), `tabtabtab_anchors.py` (749), `link.py` (239), `prefs.py` (202), `api.py` (135), `menu.py` (109), `labels.py` (107), `constants.py` (40), `util.py` (30).
- `tabtabtab_anchors.py` is **upstream library code** (forked from dbr/tabtabtab-nuke, Unlicense) — leave alone.
- `colors.py` is large because it is two genuine UI dialogs (`ColorPaletteDialog` ~500 lines, `PrefsDialog` ~590 lines). Not bloat — keep as-is structurally.
- 8 FROZEN constants are all written into user `.nk` files (verified via knob add/remove sites in `link.py`, `anchor.py`, `anchors.py`).
- Existing migrators: `prefs._migrate_from_old_prefs_file`, `prefs._migrate_from_old_palette`, `anchors.migrate_script` (auto-runs via `addOnScriptLoad`), `anchors.migrate_to_stemless_names` (manual, menu-exposed).

---

## Tranche 1 — Dead-code removal (smallest diff, zero behaviour change)

**Goal:** delete code that has no callers, then re-run the test suite.

1. **Delete `util.py`** (entire file, 30 lines).
   - Contains `upstream_ignoring_hidden()` and `select_upstream_ignoring_hidden()`.
   - Confirmed orphan: zero callers in `anchor.py`, `anchors.py`, `link.py`, `colors.py`, `labels.py`, `menu.py`, `prefs.py`, `tabtabtab_anchors.py`, or any test.
2. **Delete `_offer_make_dot_anchor`** in `anchor.py:694–711`.
   - Header comment says "Retained for reference only — do not call". Verified: zero callers.
3. **Run** `pytest tests/` — must stay green.

Files touched: `util.py` (delete), `anchor.py`.

---

## Tranche 2 — Consolidate copy/paste duplication in `anchors.py`

**Goal:** strip the two `# noqa: C901` markers by extracting the repeated blocks. No behaviour change.

Targets in `anchors.py`:

1. **Local Dot restoration block** appears 3× (lines ~77–86, ~104–114, ~311–317). Extract:
   ```python
   def _restore_local_dot_appearance(node, source_label):
       # Local Dot label/colour stamp
   ```
   Call from all three sites.
2. **Legacy stem-prefixed FQNN construction** (`f"{script_stem}.{get_fully_qualified_node_name(input_node)}"`) appears 3× in `copy_anchors`. Extract `_legacy_stem_fqnn(input_node)`.
3. **Source-label extraction** (`source_label = (node['label'].getText() if 'label' in node.knobs() else '') or node.name()`) appears 3×. Extract `_source_label_for(node)`.
4. **Split `paste_anchors`** along its existing branch comments:
   - `_handle_pasted_anchor_as_link(node, ...)` — Path D (pasted anchor → link replacement, current lines 228–258).
   - `_handle_pasted_hidden_input(node, ...)` — Path B (hidden-input dot → resolve & reconnect, current lines 260–317).
   - `_restamp_orphan_anchor_label(node)` — pre-loop label fix-up (lines 210–221).
   - `paste_anchors` becomes the orchestrator: snapshot selection, dispatch by predicate, restore selection.
5. **Split `copy_anchors`** the same way: `_stamp_for_link(node)`, `_stamp_for_hidden_dot(node)`, `_stamp_for_anchor(node)`. Removes Path L / Path B / anchor-case interleaving.

Critical files: `anchors.py:46–325`. Tests already cover these paths heavily (`test_copy_link_node.py`, `test_paste_robustness.py`, `test_paste_label_restamp.py`, `test_cross_script_paste.py`, `test_copy_anchor_as_link.py`, `test_dot_type_distinction.py`). No new tests needed; existing suite is the safety net.

---

## Tranche 3 — Dedup in `anchor.py`

**Goal:** collapse the two large duplications without changing observable behaviour.

1. **`rename_anchor_to`** (lines 378–430) has a 16-line FQNN-update loop duplicated for the Dot branch (396–411) and the NoOp branch (412–427). Extract:
   ```python
   def _update_links_for_renamed_anchor(anchor_node, old_fqnn, legacy_fqnn):
       # iterate allNodes, update KNOB_NAME + label on matching links
   ```
   Both branches call it after their branch-specific node rename.
2. **`AnchorPlugin` and `AnchorNavigatePlugin`** (anchor.py:648–1008) are ~150 lines of near-identical TabTabTab subclasses; the only real difference is `invoke()`. Replace with a single `_AnchorPickerPlugin` class parameterised by an `on_select` callable and a `weights_filename`. Two thin module-level instances (one for create-link, one for navigate) preserve current behaviour.
3. **`create_anchor` (interactive)** at lines 493–559 duplicates the colour-derivation portion of `create_anchor_named` at 570–609. Have `create_anchor` call `create_anchor_named` after running the dialog, instead of re-implementing the colour logic.
4. **Exception suppression cleanup**: replace blanket `with contextlib.suppress(ValueError)` (anchor.py:445, 511, 558; anchors.py:220) with narrow guards that check the precondition first (e.g. `if sanitize_anchor_name(name)`) so that genuinely unexpected `ValueError`s aren't swallowed. Behaviour unchanged for valid inputs.

Critical files: `anchor.py`. Tests: `test_anchor_naming.py`, `test_dot_anchor_name_sync.py`, `test_anchor_navigation.py`, `test_anchor_color_system.py`, `test_create_links_from_selected_anchors.py`.

---

## Tranche 4 — `labels.py` boilerplate + missing tests

**Goal:** four label functions share an 8-line preamble; extract it. Add the dedicated test file the module currently lacks.

1. Extract a `_prompt_and_label(prompt, default_callable, applier)` helper that runs the gate / selection / `nuke.getInput` / cancel-check sequence. The four public functions become 1–2 lines each that pass an applier closure.
2. Add `tests/test_labels.py` covering:
   - `create_large_label`, `create_medium_label`, `create_small_label`, `append_to_label` happy paths.
   - User cancels the prompt (returns `None`) → no mutation.
   - Plugin disabled → no mutation.
   - Dot anchor: applying a label propagates to all links via `_update_dot_link_labels`.
3. Existing indirect coverage in `test_dot_anchor_name_sync.py:423` (which imports `_apply_label`) stays as-is; the new test file complements it.

Critical files: `labels.py`, `tests/test_labels.py` (new).

---

## Tranche 5 — Constants migration & consolidation (largest blast radius)

**Goal:** unify the FROZEN knob namespace under `anchors_*` and consolidate all migrators in one place. **Per the user's choice — this is the riskiest tranche; do it last and verify carefully.**

### 5a. Add new knob-name migration to `migrate_script`

In `anchors.py:migrate_script`, extend the existing renames so it covers the **full** old → new mapping in one pass:

| Old name | New name | Constant |
|---|---|---|
| `copy_hidden_tab` | `anchors_tab` | `TAB_NAME` |
| `copy_hidden_input_node` | `anchors_input_node` | `KNOB_NAME` |
| `paste_hidden_dot_anchor` | `anchors_dot_anchor` | `DOT_ANCHOR_KNOB_NAME` (already done) |
| `paste_hidden_dot_type` | `anchors_dot_type` | `DOT_TYPE_KNOB_NAME` (already done) |
| `reconnect_link` | `anchors_reconnect_link` | `LINK_RECONNECT_KNOB_NAME` |
| `reconnect_child_links` | `anchors_reconnect_child_links` | `ANCHOR_RECONNECT_KNOB_NAME` |
| `rename_anchor` | `anchors_rename_anchor` | `ANCHOR_RENAME_KNOB_NAME` |
| `set_anchor_color` | `anchors_set_anchor_color` | `ANCHOR_SET_COLOR_KNOB_NAME` |

Same idempotent pattern already used for the dot knobs: only act when old name present AND new name absent; copy value, drop old knob.

### 5b. Consolidate the migrators

Create `migrations.py` (new file) housing:

- `migrate_prefs_files()` — replaces `prefs._migrate_from_old_prefs_file` + `prefs._migrate_from_old_palette`. Called from `prefs._load` first-run path (signature stays the same, `prefs.py` just imports from `migrations`).
- `migrate_script()` — moves the consolidated knob-rename pass out of `anchors.py`. Re-exported as `anchors.migrate_script` so `nuke.addOnScriptLoad(anchors.migrate_script)` and the documented public API still work.
- `migrate_to_stemless_names()` — moved from `anchors.py`, re-exported the same way.
- All four become callable as `anchors.<name>()` for the documented public API and from menu items, so the README and `Edit > Anchors > Migrate Stored Names` menu item keep working.

### 5c. Update `constants.py` with new values + clean grouping

Once 5a is in place and `migrate_script` rewrites old `.nk` files at load time, change the FROZEN constants to their new values. Reorganise `constants.py` into commented sections:

```python
# === Hidden knob names (written to .nk files). Renaming requires a migrator. ===
# === Anchor lifecycle constants (node-name prefixes, defaults). ===
# === Font sizes and colours. ===
# === On-disk preferences paths. ===
```

**Risk acknowledgement:** every existing `.nk` file in the wild will be rewritten the first time it is loaded after this lands. This is exactly what `migrate_script` already does for the dot knobs, so the mechanism is proven, but the surface area is larger. Mitigations:

- Land 5a (extended migrator) and ship/test it for a release cycle before 5c (constant value flip), so users get the migrator in place before any new code starts looking for the new names. *Or*, if shipping in one release, ensure `migrate_script` is registered via `addOnScriptLoad` before any code path that reads the new knob names — `menu.py:84` already does this.
- Add a regression test: open a fixture `.nk` (or a stubbed allNodes fixture) carrying every old knob name; run `migrate_script`; assert all renamed correctly and that `is_anchor`/`is_link` predicates still resolve.

### 5d. Update tests

`test_prefs.py` (865 lines) currently tests the prefs migration path. Update where it patches `prefs._migrate_from_*` to instead patch `migrations.migrate_prefs_files`. Existing assertions about behaviour stay identical.

Add `tests/test_migrations.py` consolidating:
- Old prefs file copy.
- Old palette read.
- Old knob rename for every entry in the table above (parametrised).
- Idempotency: calling twice does not double-rename.
- `migrate_to_stemless_names` reachability via the new module path.

Critical files: `migrations.py` (new), `anchors.py` (delete migrate_*, re-export), `prefs.py` (delete `_migrate_from_*`, call `migrations`), `constants.py` (regroup + flip values), `tests/test_migrations.py` (new), `tests/test_prefs.py` (patch path update).

---

## Bugs being fixed (small, user-confirmed)

1. **Pure black treated as cancel in custom-colour picker** — `colors.py:411` (`if result == 0: return`). `nuke.getColor()` returns `0` both for cancel and for selecting `0x000000FF`; users can pick black via palette swatches but not via "Custom Color…". Fix: use a sentinel (e.g. capture pre-call value or use `nuke.getColor(default=...)` and compare to default), or detect cancel by other means. Land this as part of Tranche 1 or 2 since it is a one-line change.

## Bugs/risks investigated and **not** fixed

- **Two anchors with the same name** — not a bug. Nuke guarantees `fullName()` is unique per scope, so `find_anchor_node()` cannot ambiguously match.
- **`cycle_next_link` mutates selection** — intentional (the user confirmed cycling moves the selection).
- **`copy_old`/`cut_old`/`paste_old`** — kept; tested by `test_old_paste_anchor.py` and exposed via `Edit > Anchors > Paste (old)`/`Ctrl+Shift+D`.
- **`OLD_PREFS_PATH` / `paste_hidden_user_palette.json` migrators** — kept; idempotent first-run-only paths that help users upgrading from very old versions.

## Behaviour changes that need explicit user sign-off

None proposed. All bugs above are either fixed (one-liner) or confirmed-as-intended.

## Things this refactor explicitly does NOT touch

- `tabtabtab_anchors.py` — upstream code, untouched.
- `colors.py` UI dialogs — large, but the size is justified by genuine UI surface.
- The on-disk schema of `anchors_prefs.json` — unchanged.
- Public API in `api.py` — surface unchanged; internals may change.

---

## Critical files (for execution)

**Modify:** `anchors.py`, `anchor.py`, `labels.py`, `prefs.py`, `constants.py`, `colors.py` (one-line bug fix only), `menu.py` (only if a new menu item for stemless migration moves location).

**Create:** `migrations.py`, `tests/test_labels.py`, `tests/test_migrations.py`.

**Delete:** `util.py`.

**Helpers to reuse (no need to recreate):** `link.get_fully_qualified_node_name`, `link.is_anchor`, `link.is_link`, `link.setup_link_node`, `link.add_input_knob`, `link.find_anchor_node`, `anchor.sanitize_anchor_name`, `anchor.anchor_display_name`, `anchor.find_anchor_color`, `prefs.plugin_enabled`, the existing idempotent shape of `migrate_script`.

---

## Verification

Per-tranche verification — each tranche must pass before the next begins:

1. **Tranche 1** — `pytest tests/` green.
2. **Tranche 2** — `pytest tests/test_copy_*.py tests/test_paste_*.py tests/test_cross_script_paste.py tests/test_dot_type_distinction.py` green; full `pytest tests/` green; `# noqa: C901` markers removed and lint passes (`.githooks` runs the same checks).
3. **Tranche 3** — `pytest tests/test_anchor_naming.py tests/test_dot_anchor_name_sync.py tests/test_anchor_navigation.py tests/test_anchor_color_system.py tests/test_create_links_from_selected_anchors.py` green; full suite green.
4. **Tranche 4** — new `tests/test_labels.py` green; full suite green.
5. **Tranche 5** — full suite green; new `tests/test_migrations.py` covers every old→new knob rename; manual smoke test in real Nuke: open a script that pre-dates the rename, confirm `migrate_script` (auto on script load) rewrites silently and the script behaves identically (anchors visible in picker, links reconnect, copy/paste re-pipes correctly).

Final UAT (per project CLAUDE.md):

- Open Nuke; load a known-good script; copy a Read with `Ctrl+C`, paste in a different position, confirm hidden-input re-pipe.
- Create an anchor with `A`, create a link with `A` (no selection), navigate with `Alt+A`.
- Open the Custom Color dialog; pick black; confirm it is accepted (post-bugfix).
- Load a fixture script carrying old `paste_hidden_*` and `copy_hidden_*` knobs; confirm silent migration and unchanged behaviour.

After full verification: per project CLAUDE.md, ask the user before pushing to remote.
