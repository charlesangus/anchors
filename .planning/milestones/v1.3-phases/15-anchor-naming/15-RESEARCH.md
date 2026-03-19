# Phase 15: Anchor Naming - Research

**Researched:** 2026-03-16
**Domain:** Python regex, PySide2/6 UI, plugin prefs singleton, anchor name suggestion logic
**Confidence:** HIGH

## Summary

Phase 15 is purely internal Python work on the existing `anchors` plugin codebase. All
decisions are locked by CONTEXT.md. There are no new external libraries to install; the
full standard stack (`re`, `os`, PySide2/6, the prefs singleton, `anchor.py`) is already
present and in production use.

The three changes are tightly scoped:

1. **`anchor.py` — `suggest_anchor_name()`**: Insert a user-regex branch before the
   hardcoded one.  When `prefs.naming_regex` is non-empty, compile it and try to match
   the frame-token-stripped basename; use `prefs.naming_template` (or the full match)
   as the suggestion; on compile error or no-match, fall through to the hardcoded path.

2. **`prefs.py`**: Add two module-level vars (`naming_regex`, `naming_template`) with
   empty-string defaults; load them with type validation in `_load()`; write them in
   `save()`.

3. **`colors.py` — `PrefsDialog`**: Add a "Anchor Naming" section between the existing
   checkboxes and the custom-colors separator.  Three `QLineEdit` fields plus a live
   red/green validity indicator, a Reset button, and the standard working-copy +
   `_on_accept()` flush pattern.

All edge cases (frame-token stripping, fallback on no-match, backdrop prefix unchanged,
template substitution errors) are documented in CONTEXT.md as locked decisions.

**Primary recommendation:** Implement in three self-contained tasks: prefs first (no
downstream dependencies), then `suggest_anchor_name()`, then the PrefsDialog UI. Test
each unit with offline pytest using the established stubs.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Regex behavior
- User regex is applied to the **basename** of the file knob value (not the full path).
- Frame padding tokens (`%04d`, `####`, `%d`, etc.) are stripped from the basename before applying the user's regex.
- When a user regex is configured: it **replaces** the hardcoded version-strip regex entirely — no layering.
- When no user regex is configured (blank field): the existing hardcoded behavior is preserved unchanged (NAME-03 satisfied automatically).
- When a user regex is configured but **doesn't match**: fall back to the hardcoded version-strip regex (same as "no regex configured" experience).

#### Template substitution syntax
- `{group_name}` curly-brace syntax — maps named capture groups from the regex.
- No magic built-in variables.
- When no template is configured (blank field): the full regex match string is used as-is.
- Template substitution errors (missing group name, etc.) fall back to the full match string.

#### Backdrop prefix behavior
- Backdrop prefix is **unchanged** — containing backdrop label always prepended as prefix.
- Format: `{backdrop_label}_{file_suggestion}`

#### PrefsDialog UI
- Naming section placed **below the existing checkboxes**, **above the custom colors section**.
- Three fields: Regex, Template, Test filename (pre-filled default e.g. `plate_v003.exr`).
- Red/green validity indicator: compiles without error AND matches the test filename.
- Reset button: blanks regex and template fields only.

#### Persistence
- Two new fields in `prefs.py`: `naming_regex` (str, default `""`) and `naming_template` (str, default `""`).
- Persisted to `anchors_prefs.json` alongside existing fields.
- Empty string = not configured = use hardcoded fallback.

### Claude's Discretion
- Exact regex for frame token stripping (must cover `%04d`, `%d`, `####`, `%V`, `%v` and similar Nuke patterns).
- Exact sensible default test filename shown in PrefsDialog.
- Exact wording of section label ("Anchor Naming" or similar).
- Whether to show a separate "Result preview" label next to the validity indicator, or just show the indicator color.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAME-01 | User can configure a regex (applied to node's file knob, if present) with named capture groups to derive a default anchor name suggestion | `suggest_anchor_name()` reads `prefs.naming_regex` at call time; `re.match()` with named groups via `(?P<name>...)` syntax |
| NAME-02 | User can configure a template string that substitutes named capture groups into the suggested name | `str.format_map(match.groupdict())` performs `{group_name}` substitution; errors fall back to full match string |
| NAME-03 | When no file knob or regex doesn't match, anchor naming falls back to existing behavior | Existing hardcoded path in `suggest_anchor_name()` preserved unchanged as the fallback branch |
</phase_requirements>

---

## Standard Stack

### Core (all already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | Python 3.x | Regex compile, match, named groups | stdlib — zero install cost |
| `os` (stdlib) | Python 3.x | `os.path.basename()` already used | already imported in `anchor.py` |
| PySide2 / PySide6 | 2.x / 6.x | PrefsDialog widgets (QLineEdit, QLabel, QPushButton, QHBoxLayout) | already in use in `colors.py` |
| `prefs.py` singleton | project | Plugin-wide preferences, JSON persistence | established pattern |

### No new dependencies required
This phase adds zero new `pip install` requirements.

---

## Architecture Patterns

### Recommended Project Structure
No new files needed. Changes are confined to:
```
anchor.py          # suggest_anchor_name() logic change
prefs.py           # two new module vars + load/save
colors.py          # PrefsDialog._build_ui() naming section
tests/
└── test_anchor_naming.py   # new test file (Wave 0 gap)
```

### Pattern 1: Prefs module-level singleton extension
**What:** Add two module-level vars at the top of `prefs.py` with empty-string defaults.
Extend `_load()` to read them with `isinstance(data.get(...), str)` type guard. Extend
`save()` to write them.
**When to use:** Any time a new persistent preference is added.
**Example (follows existing `plugin_enabled` / `custom_colors` pattern):**
```python
# Source: /workspace/prefs.py (lines 20-23, 77-83, 96-102)
# --- new module-level defaults ---
naming_regex = ""
naming_template = ""

# --- in _load() ---
if isinstance(data.get('naming_regex'), str):
    naming_regex = data['naming_regex']
if isinstance(data.get('naming_template'), str):
    naming_template = data['naming_template']

# --- in save() ---
json.dump({
    ...existing keys...,
    'naming_regex': naming_regex,
    'naming_template': naming_template,
}, file_handle)
```

### Pattern 2: suggest_anchor_name() user-regex branch
**What:** Before the hardcoded `re.match(r'^(.+)_v\d+...`, try to apply
`prefs.naming_regex` (if non-empty) to the frame-token-stripped basename.
**When to use:** Called at anchor creation time and rename time.
**Example:**
```python
# Source: /workspace/anchor.py suggest_anchor_name() — to be modified at line 188
import re, os
import prefs

_FRAME_TOKEN_PATTERN = re.compile(r'[._]?(?:%0?\d*d|#{1,}|%[Vv])\b')

def suggest_anchor_name(input_node):
    suggestion = ""
    if 'file' in input_node.knobs():
        filepath = input_node['file'].getValue()
        if filepath:
            filename = os.path.basename(filepath)
            # Strip frame padding tokens before matching
            stripped = _FRAME_TOKEN_PATTERN.sub('', filename)
            user_regex = prefs.naming_regex
            if user_regex:
                try:
                    compiled = re.compile(user_regex)
                    match = compiled.match(stripped)
                    if match:
                        template = prefs.naming_template
                        if template:
                            try:
                                suggestion = template.format_map(match.groupdict())
                            except (KeyError, ValueError):
                                suggestion = match.group(0)
                        else:
                            suggestion = match.group(0)
                    else:
                        # No match — fall through to hardcoded path
                        pass
                except re.error:
                    pass  # bad regex — fall through to hardcoded path
            # Hardcoded fallback (runs when user_regex blank, no match, or re.error)
            if not suggestion:
                m = re.match(r'^(.+)_v\d+(?:\.[^.]+)?\.[^.]+$', stripped)
                suggestion = m.group(1) if m else os.path.splitext(stripped)[0]
    # Backdrop prefix — unchanged
    smallest = find_smallest_containing_backdrop(input_node)
    if smallest is not None:
        label = smallest['label'].getValue().strip()
        if label:
            suggestion = label + '_' + suggestion
    return suggestion
```

### Pattern 3: PrefsDialog naming section (working-copy pattern)
**What:** Seed `self._local_naming_regex` and `self._local_naming_template` from
`prefs_module` in `__init__()`. Build three `QLineEdit` widgets + validity indicator
label + Reset button in `_build_ui()` between checkboxes and the existing separator.
Flush to `prefs_module` in `_on_accept()`.
**When to use:** Any PrefsDialog addition that follows the established working-copy pattern.
**Key detail:** Live validity indicator wired to `textChanged` signal on both the regex
field and the test-filename field.

### Anti-Patterns to Avoid
- **Layering user regex over the hardcoded one:** CONTEXT.md explicitly prohibits this — user regex replaces, not supplements.
- **Stripping frame tokens from the full path:** Strip only from the basename (after `os.path.basename()`).
- **Raising exceptions from suggest_anchor_name():** Any `re.error`, `KeyError`, or `ValueError` must be silently swallowed and fall through to the hardcoded path.
- **Mutating `prefs` module vars directly in `__init__()`:** Always seed local working copies; only flush on `_on_accept()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Named capture groups | Custom group extraction | `match.groupdict()` (stdlib `re`) | Built-in, handles all edge cases |
| Template substitution | Custom `{x}` parser | `str.format_map(match.groupdict())` | Already handles missing keys via try/except |
| Frame token stripping | Manual string splits | Single compiled `re.sub()` with a union pattern | One-pass, readable, testable |
| Prefs persistence | Custom serialization | `json.dump/load` in existing `prefs.save()/_load()` | Pattern already established |

**Key insight:** Python's `re` stdlib handles every aspect of this feature. The total new
logic fits in ~25 lines inside `suggest_anchor_name()`.

---

## Common Pitfalls

### Pitfall 1: Frame token regex under-coverage
**What goes wrong:** `plate_v003.####.exr` or `comp_%04d.exr` passes through with
tokens intact, causing the user's regex to fail to match (or match incorrectly).
**Why it happens:** Nuke supports multiple frame-range token styles: `%d`, `%04d`,
`####`, `%V`, `%v` (stereo views). A naive strip only covers one style.
**How to avoid:** Use a single compiled pattern that covers all common styles:
```
[._]?(?:%0?\d*d|#{1,}|%[Vv])\b
```
This covers: `%d`, `%04d`, `%4d`, `####`, `##`, `%V`, `%v`.
Also handles leading separator (`.` or `_`) before the token.
**Warning signs:** Tests with `plate_v003.####.exr` leave `####` in the stripped name.

### Pitfall 2: `suggest_anchor_name()` called with `input_node=None`
**What goes wrong:** `create_anchor()` passes `input_node` only when exactly one node
is selected; otherwise it passes `None`. The function must guard for a None input_node.
**Why it happens:** Looking at `anchor.py:333` — `suggest_anchor_name(input_node) if input_node is not None else ""` — the guard is already at the call site, but must remain correct after the edit.
**How to avoid:** The function signature and the `if 'file' in input_node.knobs():` guard
at line 192 already handle this — preserve the existing guard, do not remove it.

### Pitfall 3: PrefsDialog validity indicator timing
**What goes wrong:** Indicator shows "valid" while the regex field has a compile error,
because the signal connection fires before the full text is read.
**Why it happens:** Connecting only to the regex `textChanged` signal but not the test
filename `textChanged` signal means the indicator doesn't update when the user changes
only the filename.
**How to avoid:** Connect `_update_naming_validity_indicator()` to `textChanged` on
BOTH the regex QLineEdit and the test filename QLineEdit.

### Pitfall 4: `save()` missing new keys on existing prefs file
**What goes wrong:** Old `anchors_prefs.json` (written before Phase 15) loads fine, but
when the user opens Prefs and clicks OK, the file is overwritten by `save()`. If the
new keys were accidentally omitted from `save()`, they disappear from disk.
**Why it happens:** Forgetting to add `'naming_regex': naming_regex` and
`'naming_template': naming_template` to the `json.dump()` call in `save()`.
**How to avoid:** Add the keys in the same `save()` PR as the `_load()` change; tests
should round-trip through both.

### Pitfall 5: `global` declaration missing in `_load()`
**What goes wrong:** `_load()` assigns to `naming_regex` but without `global naming_regex`
the assignment creates a local variable, leaving the module-level var unchanged.
**Why it happens:** The existing `_load()` already declares `global plugin_enabled,
link_classes_paste_mode, custom_colors` — the new vars must be appended to that
declaration.
**Warning signs:** `prefs.naming_regex` is always `""` even after editing prefs.

---

## Code Examples

### Frame token stripping (Claude's Discretion — recommended pattern)
```python
# Covers %d, %04d, %4d, ####, ##, %V, %v  — compile once at module level
_FRAME_TOKEN_PATTERN = re.compile(r'[._]?(?:%0?\d*d|#{1,}|%[Vv])\b')

def _strip_frame_tokens(filename):
    """Remove Nuke frame-padding tokens from a filename basename."""
    return _FRAME_TOKEN_PATTERN.sub('', filename)
```

Test inputs and expected stripped results:
| Input | Stripped |
|-------|----------|
| `plate_v003.%04d.exr` | `plate_v003.exr` |
| `comp_####.exr` | `comp.exr` |
| `shot_%d.dpx` | `shot_.dpx` → trim trailing `_` separately if desired |
| `left.%V.exr` | `left.exr` |
| `plate_v003.exr` | `plate_v003.exr` (no token, unchanged) |

Note: the Context decisions say strip tokens before regex — if the stripped name has a
trailing `_` or `.` that looks ugly, a secondary `.strip('_.')` on the stripped result
may help, but this is Claude's Discretion.

### Template substitution with graceful fallback
```python
# Source: Python stdlib docs — str.format_map
template = prefs.naming_template
if template:
    try:
        suggestion = template.format_map(match.groupdict())
    except (KeyError, ValueError):
        suggestion = match.group(0)  # fallback to full match
else:
    suggestion = match.group(0)  # no template — use full match
```

### PrefsDialog working-copy seed and flush (follows existing pattern)
```python
# In __init__() — seed local copies
self._local_naming_regex = prefs_module.naming_regex
self._local_naming_template = prefs_module.naming_template

# In _on_accept() — flush to module
prefs_module.naming_regex = self._local_naming_regex
prefs_module.naming_template = self._local_naming_template
prefs_module.save()
```

### Live validity indicator update
```python
def _update_naming_validity_indicator(self):
    regex_text = self._naming_regex_edit.text()
    test_filename = self._naming_test_filename_edit.text()
    if not regex_text:
        self._naming_validity_label.setText("")
        self._naming_validity_label.setStyleSheet("")
        return
    try:
        compiled = re.compile(regex_text)
    except re.error:
        self._naming_validity_label.setText("Invalid regex")
        self._naming_validity_label.setStyleSheet("color: red;")
        return
    if compiled.match(test_filename):
        self._naming_validity_label.setText("Match")
        self._naming_validity_label.setStyleSheet("color: green;")
    else:
        self._naming_validity_label.setText("No match")
        self._naming_validity_label.setStyleSheet("color: red;")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `_v\d+` strip-only | User-configurable regex + template | Phase 15 | Artists can match site naming conventions |
| No frame-token awareness | Strip `%04d`/`####`/`%V` etc. before regex | Phase 15 | Prevents token noise from confusing user regex |

---

## Open Questions

1. **Trailing separator after frame token strip**
   - What we know: Stripping `plate_v003.%04d.exr` → `plate_v003.exr` is clean. Stripping `shot_%d.dpx` → `shot_.dpx` leaves a trailing `_`.
   - What's unclear: Whether `.strip('_.')` is desired after token removal (Claude's Discretion).
   - Recommendation: Apply a secondary `re.sub(r'[_.](?=\.[^.]+$)', '', stripped)` to clean up the extension separator, or simply strip trailing separators before the extension. Planner should decide in the plan.

2. **Default test filename in PrefsDialog**
   - What we know: CONTEXT.md says e.g. `plate_v003.exr`.
   - What's unclear: Exact value (Claude's Discretion).
   - Recommendation: Use `plate_v003.exr` — it exercises the hardcoded fallback and is universally recognizable in VFX pipelines.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (see `tests/` directory) |
| Config file | none detected — pytest discovers via `tests/` convention |
| Quick run command | `python3 -m pytest tests/test_anchor_naming.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NAME-01 | `suggest_anchor_name()` uses user regex on file knob basename | unit | `python3 -m pytest tests/test_anchor_naming.py::TestSuggestAnchorNameUserRegex -x` | ❌ Wave 0 |
| NAME-01 | Frame tokens stripped before regex applied | unit | `python3 -m pytest tests/test_anchor_naming.py::TestFrameTokenStripping -x` | ❌ Wave 0 |
| NAME-02 | Template `{group_name}` substitution populates suggestion | unit | `python3 -m pytest tests/test_anchor_naming.py::TestTemplateSubstitution -x` | ❌ Wave 0 |
| NAME-02 | Template substitution error falls back to full match | unit | `python3 -m pytest tests/test_anchor_naming.py::TestTemplateSubstitutionFallback -x` | ❌ Wave 0 |
| NAME-03 | No file knob → suggestion is empty string (existing behavior) | unit | `python3 -m pytest tests/test_anchor_naming.py::TestNoFileKnobFallback -x` | ❌ Wave 0 |
| NAME-03 | User regex configured but doesn't match → hardcoded fallback fires | unit | `python3 -m pytest tests/test_anchor_naming.py::TestRegexNoMatchFallback -x` | ❌ Wave 0 |
| NAME-01–03 | `prefs.naming_regex` and `prefs.naming_template` round-trip through `save()`/`_load()` | unit | `python3 -m pytest tests/test_prefs.py -x` | ✅ (extend existing) |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_anchor_naming.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_anchor_naming.py` — covers NAME-01, NAME-02, NAME-03 (new file, does not exist)
- [ ] Extend `tests/test_prefs.py` — add round-trip tests for `naming_regex` and `naming_template` keys

*(No new framework install needed — pytest is already the established test runner)*

---

## Sources

### Primary (HIGH confidence)
- `/workspace/anchor.py` lines 188–205 — `suggest_anchor_name()` current implementation; read directly
- `/workspace/prefs.py` — full module; module-level singleton pattern, `_load()`, `save()`; read directly
- `/workspace/colors.py` lines 535–864 — `PrefsDialog` full implementation; working-copy pattern; read directly
- `/workspace/tests/stubs.py` — `StubNode`, `StubKnob`, `make_stub_nuke_module()`; test infrastructure
- `/workspace/tests/conftest.py` — Qt stub installation; pytest session setup
- `/workspace/.planning/phases/15-anchor-naming/15-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- Python stdlib `re` docs — `re.compile`, `match.groupdict()`, `(?P<name>...)` named groups, `re.error` — standard, unchanged since Python 3.0
- PySide2/PySide6 `QLineEdit.textChanged` signal — standard Qt signal, consistent across versions

### Tertiary (LOW confidence)
- Nuke frame token formats (`%V`, `%v` stereo) — based on Nuke documentation knowledge, not verified against live instance

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in production use in this repo
- Architecture: HIGH — all patterns verified by reading live source files
- Pitfalls: HIGH (global declaration, missing save keys) / MEDIUM (frame token edge cases)
- Test infrastructure: HIGH — pytest + stubs pattern verified in `tests/`

**Research date:** 2026-03-16
**Valid until:** 2026-05-16 (stable domain — no fast-moving dependencies)
