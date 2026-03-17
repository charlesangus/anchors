# Phase 16: Site Config - Research

**Researched:** 2026-03-16
**Domain:** Python module-level singleton extension, PySide2/PyQt UI state management
**Confidence:** HIGH

## Summary

Phase 16 extends two already-established patterns in this codebase: the `prefs.py`
module-level singleton and the `PrefsDialog` local-working-copy pattern. No new
libraries are required. The implementation is entirely internal to the plugin.

The core design is a two-layer value system: `prefs.py` holds *effective* values
(what callers like `suggest_anchor_name()` see), while the dialog holds the user's
*own* saved values for the three naming fields separately. When site config is active
and override is off, effective values come from the site config file. When override
is on (or no site config exists), effective values equal the user's own saved values.

The critical invariant is that `prefs.save()` must always write the user's own values,
never the site config values — even while the site config is in effect. This preserves
the user's configuration so they can restore it by enabling override.

**Primary recommendation:** Store site config values in a private dict (`_site_config`)
inside `prefs.py`, expose effective values via module-level vars (as today), and add a
`site_config_override` bool. The dialog seeds its `_local_naming_*` fields from the
user prefs file's values (not the effective module vars) so locked fields display what
the user would get on override.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Lockable fields:** Only `naming_regex`, `naming_template`, `naming_demo_filename` are
lockable by site config. `plugin_enabled`, `link_classes_paste_mode`, `custom_colors`
are never locked.

**Lock format:** Presence in site config JSON = locked. Site config is sparse. Fields
absent from site config are not locked.

**Publish button update:** `publish()` must be updated to write ONLY the three naming
fields (not all prefs fields). Either update in-place or add `publish_site_config()` —
planner decides which.

**Runtime behavior (no override):** Plugin uses site config values for naming at
runtime. User's own values are preserved in `anchors_prefs.json` but bypassed.
Greyed-out fields in PrefsDialog show the USER'S OWN saved values (not site config values).

**Override UX:** Single "Override Site Config" checkbox inside the Advanced collapsible
section. When checked: all locked naming fields become editable (user-saved values
used). No indicator on the collapsed Advanced button.

**Override persistence:** `site_config_override` boolean added to `anchors_prefs.json`,
default `false`. Override state survives restart. To re-apply site config after admin
update, user unchecks override and clicks OK.

**Env var:** `ANCHORS_SITE_CONFIG` already established. `prefs._load()` reads it on
startup. Silent no-op when unset, empty, missing, or corrupt.

**Loading timing:** Site config loaded once at import time (same as user prefs).

### Claude's Discretion

- Exact internal architecture for storing user values vs effective values (e.g.,
  `_user_naming_regex` shadow vars vs a `_site_config` dict — planner decides)
- Whether `prefs.publish()` is modified in-place or a new `prefs.publish_site_config()`
  is added
- Exact wording/label of the override checkbox

### Deferred Ideas (OUT OF SCOPE)

- Per-field override checkboxes
- Dynamic re-check of ANCHORS_SITE_CONFIG during dialog lifetime
- Site config locking of non-naming fields (`plugin_enabled`, `custom_colors`)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SITE-01 | Site-level config file path resolved from `ANCHORS_SITE_CONFIG` env var | `prefs._load()` already reads env var in PrefsDialog init; extend `_load()` to also read and apply the site config file |
| SITE-02 | Site config can set and lock user-configurable settings (naming regex, template, demo_filename) | Presence-means-locked pattern; `setEnabled(False)` on the three QLineEdit widgets; effective module vars reflect site config values when override is off |
| SITE-03 | "Override Site Config" checkbox in PrefsDialog re-enables individual locked fields for the user | New QCheckBox inside `_advanced_container_widget`; toggling it calls `setEnabled()` on the three naming fields; override flag persisted in `anchors_prefs.json` |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | stdlib | Parse site config JSON file | Already used in `prefs._load()` |
| Python stdlib `os` | stdlib | Read `ANCHORS_SITE_CONFIG` env var | Already used throughout prefs.py |
| PySide2 `QCheckBox` | existing dep | Override Site Config toggle | Already used for plugin_enabled and link_mode checkboxes |
| PySide2 `QLineEdit.setEnabled(bool)` | existing dep | Lock/unlock naming fields | Already used for Publish button (`self._publish_button.setEnabled(bool(...))`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `unittest` | stdlib | Test site config loading and dialog behavior | All new prefs tests follow the `_reload_prefs_with_temp_path` pattern already established |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `_site_config` dict in prefs.py | `_user_naming_regex` shadow vars | Dict is cleaner: one structure, easy to check `field in _site_config` for lock state; shadow vars require 3 extra module-level names |
| `setEnabled(False)` on QLineEdit | Read-only mode (`setReadOnly(True)`) | `setEnabled(False)` gives the standard greyed-out visual; `setReadOnly` keeps text selectable but doesn't visually communicate "locked by admin" |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. Changes span:

```
prefs.py          — add _site_config dict, site_config_override bool, extend _load(), update publish()
colors.py         — extend PrefsDialog.__init__(), _build_ui(), _on_accept()
tests/test_prefs.py          — new test classes for site config loading, save/load override flag
tests/test_site_config_ui.py — new test module for dialog lock/unlock behavior (headless-safe)
```

### Pattern 1: Presence-means-locked dict in prefs.py

**What:** `_site_config` is a module-level dict. After loading user prefs,
`_load_site_config()` (called at the end of `_load()`) reads `ANCHORS_SITE_CONFIG`.
For each of the three naming fields present in the site config JSON, the value is stored
in `_site_config`. Module-level vars (`naming_regex` etc.) are then set to effective
values: site config value if present AND override is off, user's own value otherwise.

**When to use:** This is the recommended approach. It separates concerns cleanly:
`_site_config` is the admin layer, user prefs file is the user layer, module-level vars
are the merged effective layer.

```python
# Source: prefs.py pattern
_LOCKABLE_NAMING_FIELDS = ('naming_regex', 'naming_template', 'naming_demo_filename')

# Module-level vars (existing + new)
naming_regex = ""
naming_template = ""
naming_demo_filename = "plate_v003.exr"
site_config_override = False

# Private — populated by _load_site_config(), never written to user prefs
_site_config = {}   # keys are field names present in site config file
# Private — the user's own saved values for the three lockable fields
_user_naming_regex = ""
_user_naming_template = ""
_user_naming_demo_filename = "plate_v003.exr"
```

**Loading sequence in `_load()`:**
1. Load user prefs as today — sets `naming_regex`, `naming_template`, `naming_demo_filename`,
   `site_config_override` from JSON
2. Copy user values into `_user_naming_*` shadow vars (for dialog display)
3. Call `_load_site_config()` — reads env var + file, populates `_site_config`
4. Call `_apply_effective_values()` — sets module-level naming vars to either site config
   values (when locked and no override) or user values

### Pattern 2: Shadow user vars approach (alternative)

**What:** Instead of a dict, three explicit `_user_naming_*` module-level vars shadow the
lockable fields. Lock state is `bool(_site_config)` (any key present means at least one
field is locked).

**When to use:** Only if the planner finds this cleaner. The dict approach is preferred
because `field_name in _site_config` is a clean per-field lock check.

### Pattern 3: Dialog seeding from user values, not effective values

**What:** In `PrefsDialog.__init__()`, the three local naming vars are seeded from
`prefs_module._user_naming_*` (the saved user values), NOT from `prefs_module.naming_*`
(the effective values which may be site config values). This ensures the greyed-out
fields show what the user would get on override.

```python
# In PrefsDialog.__init__():
self._local_naming_regex = prefs_module._user_naming_regex
self._local_naming_template = prefs_module._user_naming_template
self._local_naming_demo_filename = prefs_module._user_naming_demo_filename
self._local_site_config_override = prefs_module.site_config_override
```

### Pattern 4: setEnabled pattern for locked fields

**What:** Three QLineEdit fields are disabled when site config is active and override is
unchecked. The override checkbox toggles them. This mirrors the existing Publish button
pattern exactly.

```python
# In _build_ui() — after creating the three QLineEdit widgets:
self._update_naming_fields_lock_state()

def _update_naming_fields_lock_state(self):
    """Enable or disable naming fields based on site config lock state."""
    import prefs as prefs_module
    site_config_locks_fields = bool(prefs_module._site_config)
    fields_are_editable = (not site_config_locks_fields) or self._local_site_config_override
    self._naming_regex_edit.setEnabled(fields_are_editable)
    self._naming_template_edit.setEnabled(fields_are_editable)
    self._naming_test_filename_edit.setEnabled(fields_are_editable)
    if hasattr(self, '_override_site_config_checkbox'):
        self._override_site_config_checkbox.setVisible(site_config_locks_fields)
```

### Pattern 5: _on_accept correctly saves user values, not effective values

**What:** On OK, `_on_accept()` must flush `_local_naming_*` (user's own values) to
`prefs_module._user_naming_*` AND to `prefs_module.naming_*` (if override is active).
Then `save()` writes the user's own values (via `_user_naming_*`), never the site config
values.

```python
# In prefs.save():
json.dump({
    ...
    'naming_regex': _user_naming_regex,       # always user's own values
    'naming_template': _user_naming_template,
    'naming_demo_filename': _user_naming_demo_filename,
    'site_config_override': site_config_override,
}, file_handle)
```

### Pattern 6: publish() writes only naming fields

**What:** `publish()` is updated to write ONLY `naming_regex`, `naming_template`,
`naming_demo_filename` (the site config sparse format). It writes the EFFECTIVE values
(what site admins want to distribute), which when override is off means the current
module-level `naming_*` vars (already reflecting site config if loaded). When the
Publish button is clicked from within the dialog, `_on_publish_naming()` should flush
the current field values to `prefs_module._user_naming_*` first, then call `publish()`.

```python
def publish(destination_path):
    """Write only naming fields to destination_path (sparse site config format)."""
    parent_directory = os.path.dirname(destination_path)
    if parent_directory:
        os.makedirs(parent_directory, exist_ok=True)
    with open(destination_path, 'w') as file_handle:
        json.dump(
            {
                'naming_regex': naming_regex,
                'naming_template': naming_template,
                'naming_demo_filename': naming_demo_filename,
            },
            file_handle,
        )
```

### Anti-Patterns to Avoid

- **Reading effective module vars into dialog fields:** `_local_naming_regex = prefs_module.naming_regex`
  when site config is active will show the admin's value in the greyed-out field, not the
  user's own value. Always seed from `_user_naming_*`.
- **Saving site config values in save():** If `_on_accept()` flushes site config values into
  `naming_regex` etc. before calling `save()`, the user's file gets poisoned with admin values.
  The save path must use `_user_naming_*` shadow vars.
- **Re-checking ANCHORS_SITE_CONFIG at dialog open time:** Context says load is once at import
  time. Don't add env var reads in `PrefsDialog.__init__()` for site config loading beyond what
  was already there for `_publish_path`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON config file parsing | Custom file format parser | `json.load()` with `except (OSError, ValueError, json.JSONDecodeError)` | Existing pattern already handles all failure modes silently |
| Field disabling | Custom read-only overlay | `QLineEdit.setEnabled(False)` | Qt's standard greyed-out appearance; already used for Publish button |
| Override persistence | Custom flag file | New `site_config_override` key in existing `anchors_prefs.json` | Same file, same load path, no extra I/O |

**Key insight:** Every mechanism this phase needs already exists in the codebase. This
phase is purely additive — no new frameworks, no new UI patterns.

---

## Common Pitfalls

### Pitfall 1: Dialog seeds from effective vars instead of user vars
**What goes wrong:** Greyed-out fields show site config values. User cannot see their own
saved values. Override feels useless ("it's the same").
**Why it happens:** Naively copying the existing `_local_naming_* = prefs_module.naming_*`
pattern without distinguishing effective vs user values.
**How to avoid:** Introduce `_user_naming_*` shadow vars in `prefs.py`. Seed dialog from these.
**Warning signs:** Test: after loading site config, open dialog, check that `_local_naming_regex`
equals the user prefs file value, not the site config value.

### Pitfall 2: save() writes effective values (poisoning user prefs)
**What goes wrong:** After one OK click while site config is active (no override), the user's
`anchors_prefs.json` gets overwritten with site config values. User's own values are lost.
**Why it happens:** `_on_accept()` sets `prefs_module.naming_regex = self._local_naming_regex`
and then `save()` uses `naming_regex`. If `_local_naming_regex` was seeded wrong (pitfall 1
above), `save()` persists the wrong value.
**How to avoid:** `save()` must reference `_user_naming_regex` (the shadow var), not `naming_regex`
(the effective var). Alternatively, `_on_accept()` updates `_user_naming_*` separately from the
effective `naming_*` vars.
**Warning signs:** Test: load site config, open dialog, click OK without override, reload prefs —
`naming_regex` in JSON file should still equal the user's original value.

### Pitfall 3: Override checkbox visible when no site config is active
**What goes wrong:** Artists without site config see a confusing "Override Site Config" checkbox
that does nothing meaningful.
**How to avoid:** Override checkbox visibility is conditional on `bool(prefs_module._site_config)`.
Show only when at least one naming field is locked.

### Pitfall 4: Publish button writes all fields (Phase 15.1 state)
**What goes wrong:** Published site config contains `plugin_enabled`, `link_classes_paste_mode`,
`custom_colors` — fields that site config must never lock. A downstream studio artist loads this
config and has their plugin disabled.
**How to avoid:** This phase MUST update `publish()` to write only the three naming fields. This
is a locked decision; the test for `test_publish_writes_to_given_path` in `test_prefs.py` will
need updating to assert only the naming keys are present.
**Warning signs:** Existing `test_publish_writes_to_given_path` asserts `plugin_enabled` in
published output — that test must be updated to expect ONLY naming fields.

### Pitfall 5: Live preview broken when fields are disabled
**What goes wrong:** `_update_naming_validity_indicator()` reads `.text()` from disabled fields —
this still works (disabled QLineEdit returns text normally), but the preview should still render
correctly when fields are read-only.
**How to avoid:** No code change needed — `QLineEdit.text()` works regardless of enabled state.
The context doc confirms: "The live preview can remain active when override is unchecked (display
only)."

### Pitfall 6: `_site_config` and `_user_naming_*` not reset on module reload in tests
**What goes wrong:** Test isolation fails because module-level private vars persist between test
classes that each delete and re-import `prefs`.
**How to avoid:** The existing `_reload_prefs_with_temp_path` helper already handles this by
deleting `sys.modules['prefs']` before re-importing. The new private vars will reinitialize at
module level on each import. Confirm the helper patches `constants.PREFS_PATH` before import so
`_load()` reads the test file.

---

## Code Examples

### Loading site config in prefs._load()

```python
# Source: prefs.py — extend existing _load() function

_LOCKABLE_NAMING_FIELDS = ('naming_regex', 'naming_template', 'naming_demo_filename')

# Private module-level vars — populated by _load(), never written to user prefs file directly
_site_config = {}         # keys: field names locked by site config; values: admin values
_user_naming_regex = ""
_user_naming_template = ""
_user_naming_demo_filename = "plate_v003.exr"

def _load_site_config():
    """Read ANCHORS_SITE_CONFIG env var and load the site config file.

    Populates _site_config with field names present in the JSON file.
    Sets effective module-level naming vars based on site config + override state.
    Silent no-op when env var unset, file missing, or file corrupt.
    """
    global _site_config, naming_regex, naming_template, naming_demo_filename
    _site_config = {}
    site_config_path = os.environ.get("ANCHORS_SITE_CONFIG", "")
    if not site_config_path:
        return
    try:
        with open(site_config_path) as file_handle:
            data = json.load(file_handle)
        for field_name in _LOCKABLE_NAMING_FIELDS:
            if isinstance(data.get(field_name), str):
                _site_config[field_name] = data[field_name]
    except (OSError, ValueError, json.JSONDecodeError):
        return  # silent fallback — _site_config stays empty
    _apply_effective_naming_values()


def _apply_effective_naming_values():
    """Set module-level naming vars to effective values.

    When a field is locked by site config AND override is off: use site config value.
    Otherwise: use user's own saved value.
    """
    global naming_regex, naming_template, naming_demo_filename
    if not site_config_override:
        naming_regex = _site_config.get('naming_regex', _user_naming_regex)
        naming_template = _site_config.get('naming_template', _user_naming_template)
        naming_demo_filename = _site_config.get('naming_demo_filename', _user_naming_demo_filename)
    else:
        naming_regex = _user_naming_regex
        naming_template = _user_naming_template
        naming_demo_filename = _user_naming_demo_filename
```

### Saving — always write user values

```python
# Source: prefs.py — updated save()
def save():
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    with open(PREFS_PATH, 'w') as file_handle:
        json.dump(
            {
                'plugin_enabled': plugin_enabled,
                'link_classes_paste_mode': link_classes_paste_mode,
                'custom_colors': custom_colors,
                'naming_regex': _user_naming_regex,           # user's own value
                'naming_template': _user_naming_template,
                'naming_demo_filename': _user_naming_demo_filename,
                'site_config_override': site_config_override,
            },
            file_handle,
        )
```

### Dialog init seeding from user vars

```python
# Source: colors.py PrefsDialog.__init__()
import prefs as prefs_module
# Seed naming fields from USER values (not effective values)
self._local_naming_regex = prefs_module._user_naming_regex
self._local_naming_template = prefs_module._user_naming_template
self._local_naming_demo_filename = prefs_module._user_naming_demo_filename
self._local_site_config_override = prefs_module.site_config_override
```

### Override checkbox in _build_ui()

```python
# Source: colors.py PrefsDialog._build_ui() — inside advanced_container_layout
import prefs as prefs_module
site_config_is_active = bool(prefs_module._site_config)

self._override_site_config_checkbox = QtWidgets.QCheckBox("Override Site Config")
self._override_site_config_checkbox.setChecked(self._local_site_config_override)
self._override_site_config_checkbox.setVisible(site_config_is_active)
self._override_site_config_checkbox.toggled.connect(self._on_override_site_config_toggled)
advanced_container_layout.addWidget(self._override_site_config_checkbox)

def _on_override_site_config_toggled(self, is_checked):
    self._local_site_config_override = is_checked
    self._update_naming_fields_lock_state()

def _update_naming_fields_lock_state(self):
    import prefs as prefs_module
    fields_are_editable = (
        not bool(prefs_module._site_config)
        or self._local_site_config_override
    )
    self._naming_regex_edit.setEnabled(fields_are_editable)
    self._naming_template_edit.setEnabled(fields_are_editable)
    self._naming_test_filename_edit.setEnabled(fields_are_editable)
```

### _on_accept() — flush user values and override flag

```python
# Source: colors.py PrefsDialog._on_accept()
# Capture user-edited values (only meaningful when override is on or no site config)
self._local_naming_regex = self._naming_regex_edit.text()
self._local_naming_template = self._naming_template_edit.text()
self._local_naming_demo_filename = self._naming_test_filename_edit.text()
# Flush to prefs module — update user shadow vars and override flag
prefs_module._user_naming_regex = self._local_naming_regex
prefs_module._user_naming_template = self._local_naming_template
prefs_module._user_naming_demo_filename = self._local_naming_demo_filename
prefs_module.site_config_override = self._local_site_config_override
# Re-apply effective values so module vars reflect new override state immediately
prefs_module._apply_effective_naming_values()
# Persist to disk (save() writes _user_naming_* not effective vars)
prefs_module.save()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `publish()` writes all prefs fields | `publish()` writes only naming fields | Phase 16 | Prevents accidentally locking non-naming fields via site config |
| No site config concept | Site config via `ANCHORS_SITE_CONFIG` | Phase 16 | Adds admin layer over user prefs |

**Deprecated/outdated after this phase:**
- `publish()` writing `plugin_enabled`, `link_classes_paste_mode`, `custom_colors` — Phase 16
  restricts it to naming fields only. Existing test `test_publish_writes_to_given_path` asserts
  those keys; that test must be updated.

---

## Open Questions

1. **Whether `_on_publish_naming()` should publish user values or effective values**
   - What we know: Publish writes to the site config file for admins. Context says `_on_publish_naming`
     "flushes current field values before calling publish()".
   - What's unclear: If override is active and the user has changed the naming fields, should Publish
     write the user's new values (what they just typed) or the original site config values?
   - Recommendation: Always publish what the user sees in the currently-editable fields (`_naming_*_edit.text()`).
     This is the most intuitive behavior — "publish what I configured."

2. **Initial `_user_naming_*` values before first `_load()` completes**
   - What we know: `_load()` sets `naming_regex` from JSON, then should copy to `_user_naming_regex`.
   - What's unclear: The module-level defaults for `_user_naming_*` must match the defaults for
     `naming_*` so that a fresh install (no prefs file) still works.
   - Recommendation: Initialize both sets to the same defaults; `_load()` sets both together.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) |
| Config file | none — run via `python -m pytest tests/` or `python -m unittest discover` |
| Quick run command | `python -m pytest tests/test_prefs.py tests/test_anchor_naming.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SITE-01 | `ANCHORS_SITE_CONFIG` path is read; values loaded into effective naming vars | unit | `python -m pytest tests/test_prefs.py -k "site_config" -x -q` | Wave 0 |
| SITE-01 | Unset/missing/corrupt env var is a silent no-op | unit | `python -m pytest tests/test_prefs.py -k "site_config_missing" -x -q` | Wave 0 |
| SITE-02 | Fields present in site config overwrite effective values; user values preserved in JSON | unit | `python -m pytest tests/test_prefs.py -k "site_config_locks" -x -q` | Wave 0 |
| SITE-02 | `publish()` writes only naming fields (not plugin_enabled etc.) | unit | `python -m pytest tests/test_prefs.py -k "publish_naming_only" -x -q` | Wave 0 |
| SITE-03 | `site_config_override=True` causes user values to be used as effective values | unit | `python -m pytest tests/test_prefs.py -k "override" -x -q` | Wave 0 |
| SITE-03 | `site_config_override` persists across save/reload cycle | unit | `python -m pytest tests/test_prefs.py -k "override_round_trip" -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_prefs.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_prefs.py` — new test class `TestSiteConfigLoading` covering SITE-01/02/03 prefs behavior
- [ ] `tests/test_prefs.py` — update `TestPublish.test_publish_writes_to_given_path` to assert ONLY naming keys present (no `plugin_enabled`, `link_classes_paste_mode`, `custom_colors`)

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `/workspace/prefs.py` — full content; all patterns confirmed from source
- Direct code read: `/workspace/colors.py` lines 540-1057 — PrefsDialog __init__, _build_ui,
  _on_accept, _on_publish_naming confirmed from source
- Direct code read: `/workspace/tests/test_prefs.py` — test patterns, `_reload_prefs_with_temp_path`
  helper confirmed from source
- Direct code read: `/workspace/constants.py` — PREFS_PATH, existing constants confirmed

### Secondary (MEDIUM confidence)
- Qt documentation pattern: `QWidget.setEnabled(False)` for greyed-out locked fields — standard
  Qt pattern, consistent with existing use of `self._publish_button.setEnabled(bool(...))` in codebase

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all patterns verified from source
- Architecture: HIGH — patterns derived directly from existing code in prefs.py and colors.py
- Pitfalls: HIGH — derived from careful reading of the two-layer value invariant and existing test patterns

**Research date:** 2026-03-16
**Valid until:** This phase is self-contained; research valid for the duration of Phase 16 work.
