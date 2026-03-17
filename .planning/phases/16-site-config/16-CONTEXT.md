# Phase 16: Site Config - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

A site administrator can provide a JSON config file (path from `ANCHORS_SITE_CONFIG` env var) that sets and locks the three naming fields (`naming_regex`, `naming_template`, `naming_demo_filename`). When site config is active, those fields are applied at runtime and locked in PrefsDialog. Users can override the lock via a checkbox in the Advanced collapsible section, restoring their own saved values. When `ANCHORS_SITE_CONFIG` is unset or points to a missing/corrupt file, the plugin loads normally.

</domain>

<decisions>
## Implementation Decisions

### Lockable fields

- Only the three naming fields are lockable by site config: `naming_regex`, `naming_template`, `naming_demo_filename`
- `plugin_enabled`, `link_classes_paste_mode`, `custom_colors` are never locked — always user-controlled

### Lock format in config file

- Presence = locked: any naming field present in the site config JSON is both applied and locked
- Site config is intentionally sparse — only includes the fields the site admin wants to lock/set
- Fields absent from the site config file are not locked and remain fully user-controlled
- Example: `{"naming_regex": "(?P<name>.+)_v\\d+", "naming_template": "{name}"}` — locks regex and template, leaves demo_filename user-controlled

### Publish button update

- The existing Publish button (Phase 15.1) currently writes ALL prefs fields to the site config path
- Phase 16 updates Publish to write ONLY the naming fields (`naming_regex`, `naming_template`, `naming_demo_filename`)
- This keeps site config sparse and prevents accidentally locking non-naming fields
- `prefs.publish(path)` should be updated (or a new `prefs.publish_site_config(path)` added) to write only the naming fields

### Runtime behavior — site config active (no override)

- Plugin USES the site config values for naming_regex/template/demo_filename at runtime
- User's own values are preserved in `anchors_prefs.json` but bypassed
- The greyed-out fields in PrefsDialog show the USER'S own saved values (not the site config values)
  - Rationale: the user can see what they would get if they enabled override
- Callers of naming logic (e.g., `suggest_anchor_name()`) receive the effective (site config) values

### Override — scope and UX

- A single "Override Site Config" checkbox inside the Advanced collapsible section
- When checked: all locked naming fields become editable (their user-saved values are used)
- No indicator on the collapsed Advanced button when site config is active — state only visible when expanded

### Override — persistence

- The override state IS persisted to `anchors_prefs.json` (a new `site_config_override` boolean field, default `false`)
- When override=true is saved and user restarts Nuke: site config changes have no effect — user's saved values win
- To re-apply site config after a site admin update, user must uncheck override and click OK
- Initial state when first encountering site config with no saved override preference: unchecked (site config enforced by default)

### Env var and file loading

- `ANCHORS_SITE_CONFIG` env var is already established (used by Publish button in Phase 15.1)
- On startup, `prefs._load()` reads `ANCHORS_SITE_CONFIG` to find the site config file
- If env var is unset, empty, or the file path is missing/corrupt: silent no-op, plugin loads normally
- Site config is loaded once at import time (same as user prefs) — not re-checked dynamically

### Claude's Discretion

- Exact internal architecture for storing user values vs effective values (e.g., `_user_naming_regex` shadow vars vs a `_site_config` dict — planner decides)
- Whether `prefs.publish()` is modified in-place or a new `prefs.publish_site_config()` is added
- Exact wording/label of the override checkbox

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `prefs._load()` in `prefs.py`: extend to also read `ANCHORS_SITE_CONFIG` and populate locked field state; already called once at import time
- `prefs.publish(path)` in `prefs.py`: update to write only naming fields (currently writes all prefs fields)
- `PrefsDialog.__init__()` in `colors.py:560`: already reads `os.environ.get("ANCHORS_SITE_CONFIG", "")` for `self._publish_path`; extend to also determine lock state from the env var path
- Advanced collapsible section in `PrefsDialog`: already exists from Phase 15.1 — override checkbox lives inside it
- Working-copy pattern: `_local_naming_regex`, `_local_naming_template`, `_local_naming_demo_filename` — already in place; extend with `_local_site_config_override`

### Established Patterns

- Module-level singleton in `prefs.py`: new `site_config_override` field follows `plugin_enabled` boolean pattern
- Silent error handling in `_load()`: existing `except (OSError, ValueError, json.JSONDecodeError): pass` pattern applies to site config loading too
- `setEnabled(bool(...))` pattern: already used for the Publish button; apply same pattern to lock the three naming fields when site config is active and override is unchecked

### Integration Points

- `suggest_anchor_name()` in `anchor.py:188`: reads `prefs.naming_regex` and `prefs.naming_template` — these module vars must reflect the effective values (site config values when locked and no override, user values otherwise)
- `prefs.save()`: must NOT save site config values into user's prefs; must save user's own values for the naming fields regardless of whether they're currently being overridden
- `PrefsDialog._on_accept()`: flush `_local_site_config_override` to `prefs_module.site_config_override`; save user's naming field values (not site config values) to prefs

</code_context>

<specifics>
## Specific Ideas

- The greyed-out naming fields in PrefsDialog display the user's OWN saved values (not site config values) — so if the user has ever configured their own regex, they can see it and know it will be restored on override
- The live preview and validity indicator in Advanced remain functional even when fields are greyed-out (read-only preview is still useful for the artist to understand what the site config does)
- Actually, the live preview can remain active when override is unchecked (display only) — but the fields themselves are non-editable

</specifics>

<deferred>
## Deferred Ideas

- Per-field override checkboxes (instead of a single checkbox) — discussed but not chosen; keep for future if single-checkbox model proves limiting
- Dynamic re-check of ANCHORS_SITE_CONFIG during dialog lifetime
- Site config locking of non-naming fields (plugin_enabled, custom_colors) — out of scope for this phase

</deferred>

---

*Phase: 16-site-config*
*Context gathered: 2026-03-16*
