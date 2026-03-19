# Phase 15: Anchor Naming - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

User can configure a regex (applied to the source node's file knob basename) with named capture groups to derive a default anchor name suggestion, plus a template string using {group_name} syntax to format the result. Falls back to existing hardcoded behavior when no regex is configured or when the regex doesn't match.

</domain>

<decisions>
## Implementation Decisions

### Regex behavior

- User regex is applied to the **basename** of the file knob value (not the full path), e.g. `plate_v003.exr` not `/mnt/proj/shots/BG010/plate_v003.exr`
- Frame padding tokens (`%04d`, `####`, `%d`, etc.) are stripped from the basename before applying the user's regex
- When a user regex is configured: it **replaces** the hardcoded version-strip regex entirely — no layering
- When no user regex is configured (blank field): the existing hardcoded behavior is preserved unchanged (NAME-03 satisfied automatically)
- When a user regex is configured but **doesn't match**: fall back to the hardcoded version-strip regex (same as "no regex configured" experience)

### Template substitution syntax

- `{group_name}` curly-brace syntax — maps named capture groups from the regex, e.g. `{shot}_{element}`
- No magic built-in variables — `{anchorname}` in the requirements doc is just an example group name; users name their capture groups `(?P<name>...)` in their regex
- When no template is configured (blank field): the full regex match string is used as-is
- Template substitution errors (missing group name, etc.) fall back to the full match string

### Backdrop prefix behavior

- Backdrop prefix behavior is **unchanged** — the containing backdrop label is always prepended as a prefix when present, regardless of whether a user regex/template is configured
- The backdrop prefix wraps around the file-knob-based suggestion: `{backdrop_label}_{file_suggestion}`
- This applies whether the file suggestion came from user regex+template, the hardcoded fallback, or a bare basename

### PrefsDialog UI

- Naming section placed **below the existing checkboxes** (plugin enabled, link classes mode), **above the custom colors section**
- Three fields in the naming section:
  1. **Regex** — plain text input for the regex string
  2. **Template** — plain text input for the template string (may be blank)
  3. **Test filename** — plain text input pre-filled with a sensible default (e.g. `plate_v003.exr`); user can overwrite to test against their own filenames
- **Red/green validity indicator** — shows whether the regex compiles without error (`re.compile` check) and whether it matches the test filename; updates live as user types
- **Reset button** — blanks both the regex and template fields (restores default hardcoded behavior)
- No live preview output beyond the validity indicator — artist sees the result when they create an anchor

### Persistence

- Two new fields in `prefs.py`: `naming_regex` (str, default `""`) and `naming_template` (str, default `""`)
- Persisted to `anchors_prefs.json` alongside existing fields
- Empty string = "not configured" = use hardcoded fallback

### Claude's Discretion

- Exact regex for frame token stripping (must cover `%04d`, `%d`, `####`, `%V`, `%v` and similar Nuke patterns)
- Exact sensible default test filename shown in PrefsDialog
- Exact wording of section label in PrefsDialog ("Anchor Naming" or similar)
- Whether to show a separate "Result preview" label next to the validity indicator, or just show the indicator color

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `suggest_anchor_name(input_node)` in `anchor.py:188`: the function to modify — currently has hardcoded regex and backdrop prefix logic; user regex becomes a new branch before the hardcoded one
- `prefs.py` module-level singleton: two new module vars (`naming_regex`, `naming_template`) follow the existing pattern
- `PrefsDialog` in `colors.py:535`: existing prefs dialog to extend — add naming section between existing checkboxes and custom colors section
- `_persist_custom_colors_from_dialog()` pattern: working-copy-at-open, flush-on-OK pattern already established; naming fields follow the same pattern

### Established Patterns

- Module-level singleton in `prefs.py`: new fields declared at top, loaded in `_load()` with type validation, serialized in `save()`
- Working-copy pattern in `PrefsDialog.__init__()`: seed `self._local_*` vars from `prefs_module.*` at open; flush to module vars only on `_on_accept()`
- `constants.py` for file paths — no new constants needed for naming (just module vars in prefs.py)
- `_name_edit is not None` guard pattern (from BUG-03 fix) — follow same defensive style

### Integration Points

- `suggest_anchor_name()` in `anchor.py:188`: sole call site for the naming logic; reads `prefs.naming_regex` and `prefs.naming_template` at call time
- `create_anchor()` in `anchor.py:327`: calls `suggest_anchor_name(input_node)` — no change needed here
- `rename_anchor_to()` path in `anchor.py:264`: also calls `suggest_anchor_name()` for the rename pre-fill — naming logic applies there too
- `PrefsDialog._on_accept()` in `colors.py`: flush `self._local_naming_regex` and `self._local_naming_template` to `prefs_module` vars, then call `prefs_module.save()`

</code_context>

<specifics>
## Specific Ideas

- Live validity feedback in PrefsDialog: regex field turns red border (or label turns red) on `re.error`, green on successful compile AND match against the test filename
- The test filename field has a sensible default (e.g. `plate_v003.exr`) so the artist immediately sees whether their regex would match a typical Nuke file knob value
- The artist can paste their own real filename into the test field to verify

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-anchor-naming*
*Context gathered: 2026-03-16*
