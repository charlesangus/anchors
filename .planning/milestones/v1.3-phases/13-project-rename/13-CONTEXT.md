# Phase 13: Project Rename - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Rename the project from `paste_hidden` to `anchors` across all source files, tests, CI config, and GitHub repo. This is a mechanical rename + migration phase. No new features, no behavior changes beyond the rename itself.

</domain>

<decisions>
## Implementation Decisions

### Knob names (serialized in .nk files)
- Rename `paste_hidden_dot_anchor` → `anchors_dot_anchor`
- Rename `paste_hidden_dot_type` → `anchors_dot_type`
- Add `anchors.migrate_script()` function: reads old knob values, writes to new knob names, removes old knobs from all nodes in the current script
- Migration exposed via Python console only (documented in README) — no menu entry
- Artists call `import anchors; anchors.migrate_script()` once per old script

### Prefs file migration
- New path: `~/.nuke/anchors_prefs.json`
- Auto-migrate on plugin load: if `anchors_prefs.json` missing but `paste_hidden_prefs.json` exists, copy it (same pattern as v1.1 palette migration already in prefs.py)
- No manual step needed — transparent to user

### Weight/cache files
- Rename `paste_hidden_anchor_weights.json` → `anchors_anchor_weights.json`
- Rename `paste_hidden_anchor_navigate_weights.json` → `anchors_anchor_navigate_weights.json`
- No migration — these are tabtabtab frequency weights; losing them just resets learned ordering

### Package structure
- Stay flat: rename `paste_hidden.py` → `anchors.py`, all other files remain in repo root
- No package directory restructure — artists install by dropping files into `~/.nuke/`
- CI ZIP artifact: `anchors/` folder containing all .py files (was `paste_hidden/`)
- ZIP filename: `anchors-{version}.zip` (was `paste_hidden-{version}.zip`)

### Function names
- `paste_hidden()` → `paste_anchors()`
- `copy_hidden()` → `copy_anchors()`
- All internal callers (menu.py and any self-referential call in anchors.py) updated accordingly

### Claude's Discretion
- Exact README wording for migration instructions
- Whether constants.py docstring/module docstring updates are needed beyond the rename
- How to handle `constants.py` module docstring ("Shared constants for the paste_hidden package" → anchors)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prefs.py` legacy migration pattern: already does one-way `paste_hidden_user_palette.json` → `paste_hidden_prefs.json` migration at import time — use same pattern for prefs file rename

### Established Patterns
- FROZEN annotation: knob constants that are serialized in .nk files are annotated with FROZEN in constants.py — new knob names should carry the same annotation
- `constants.py` owns all file paths and knob name strings — rename goes through here, not scattered across files

### Integration Points
- `menu.py` binds `copy_hidden()` / `paste_hidden()` to Ctrl+X/C/V — must update to `copy_anchors()` / `paste_anchors()`
- `anchors.py` (renamed from `paste_hidden.py`) contains the `paste_hidden()` self-call at line 245 — update to `paste_anchors()`
- CI `release.yml` build step: `mkdir paste_hidden` → `mkdir anchors`, cp list includes `paste_hidden.py` → `anchors.py`, ZIP name updated
- GitHub repo rename: `gh repo rename anchors` (REN-02)

</code_context>

<specifics>
## Specific Ideas

- `migrate_script()` should print a summary of what it changed (nodes affected, knobs renamed) so the artist can verify
- The function should be importable as `import anchors; anchors.migrate_script()` — expose it at module level in `anchors.py`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-project-rename*
*Context gathered: 2026-03-15*
