---
phase: 15-anchor-naming
verified: 2026-03-16T14:00:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification: false
human_verification:
  - test: "Open PrefsDialog in Nuke and confirm the Anchor Naming section appears below the two checkboxes and above the Custom Colors separator"
    expected: "Section label 'Anchor Naming' visible, followed by Regex row, Template row, and Test filename row with pre-filled 'plate_v003.exr'"
    why_human: "Qt widget rendering requires a running Nuke or Qt runtime — not available in headless environment"
  - test: "Type '(?P<shot>.+)_v\\d+' in the Regex field while Test filename shows 'plate_v003.exr'"
    expected: "Validity indicator turns green and reads 'Match'"
    why_human: "textChanged signal behavior requires a live Qt event loop"
  - test: "Change Test filename to 'render_0001.exr' (no _v\\d+ pattern)"
    expected: "Validity indicator turns red and reads 'No match'"
    why_human: "Live indicator update requires Qt event loop"
  - test: "Type '[invalid(' in the Regex field"
    expected: "Validity indicator turns red and reads 'Invalid regex'"
    why_human: "Live indicator update requires Qt event loop"
  - test: "Clear the Regex field"
    expected: "Validity indicator goes blank"
    why_human: "Live indicator update requires Qt event loop"
  - test: "Type a valid regex and template, then click Reset"
    expected: "Regex and Template fields clear; Test filename field is unchanged"
    why_human: "Button click requires Qt event loop"
  - test: "Set regex='(?P<shot>.+)_v\\d+', template='{shot}_anchor', click OK; reopen Preferences"
    expected: "Both fields still show the values entered before OK"
    why_human: "Persistence across dialog open/close requires live Nuke prefs file I/O and a running session"
  - test: "Set regex + template values, then click Cancel; reopen Preferences"
    expected: "Fields show the values from before Cancel was clicked — Cancel does not save"
    why_human: "Cancel behavior requires live dialog interaction"
---

# Phase 15: Anchor Naming Verification Report

**Phase Goal:** Users can configure a custom regex + template for anchor name suggestions, making the naming convention configurable per-studio instead of hardcoded.
**Verified:** 2026-03-16T14:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `prefs.naming_regex` and `prefs.naming_template` are available as module-level vars defaulting to `""` | VERIFIED | `prefs.py` lines 23-24: `naming_regex = ""` / `naming_template = ""` |
| 2  | Both fields survive a save()/reload cycle through anchors_prefs.json | VERIFIED | `prefs.py` lines 86-89: type-guarded load; lines 107-108: written in `save()` json.dump |
| 3  | `suggest_anchor_name()` applies user regex to the frame-token-stripped basename when `prefs.naming_regex` is non-empty | VERIFIED | `anchor.py` lines 189-222: `_FRAME_TOKEN_PATTERN.sub()` then `prefs.naming_regex` branch |
| 4  | Template `{group_name}` substitution produces the formatted suggestion | VERIFIED | `anchor.py` lines 210-213: `naming_template.format_map(regex_match.groupdict())` |
| 5  | Any `re.error`, no-match, or template error silently falls through to the hardcoded `_v\d+` path | VERIFIED | `anchor.py` lines 217-222: `except re.error: pass`, `if not suggestion:` hardcoded fallback |
| 6  | When no user regex is configured, existing hardcoded behavior is entirely unchanged | VERIFIED | `anchor.py` lines 203, 220-222: hardcoded path fires when `user_regex` is falsy |
| 7  | All 13 anchor naming unit tests pass GREEN | VERIFIED | 87 tests run; 86 pass; 1 failure is pre-existing unrelated `test_anchor_color_system.py` import error |
| 8  | All 4 naming prefs round-trip tests pass GREEN | VERIFIED | `TestNamingPrefsRoundTrip` confirmed passing in test run output |
| 9  | PrefsDialog seeds local working copies of `naming_regex` and `naming_template` in `__init__` | VERIFIED | `colors.py` lines 555-556: `self._local_naming_regex = prefs_module.naming_regex` etc. |
| 10 | PrefsDialog flushes `naming_regex` and `naming_template` to prefs module on OK | VERIFIED | `colors.py` lines 898-899 (read from fields), 904-905 (assign to `prefs_module`) |
| 11 | `_update_naming_validity_indicator` is wired to `textChanged` on both Regex and Test filename fields | VERIFIED | `colors.py` lines 619-620: both `.textChanged.connect(self._update_naming_validity_indicator)` |

**Score:** 11/11 truths verified (automated)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_anchor_naming.py` | 6 test classes, 13 tests for suggest_anchor_name() naming contract | VERIFIED | All 6 classes present: `TestSuggestAnchorNameUserRegex`, `TestFrameTokenStripping`, `TestTemplateSubstitution`, `TestTemplateSubstitutionFallback`, `TestNoFileKnobFallback`, `TestRegexNoMatchFallback` |
| `tests/test_prefs.py` | `TestNamingPrefsRoundTrip` with 4 round-trip tests | VERIFIED | Class present with 4 methods: `test_naming_fields_written_to_prefs_file`, `test_naming_fields_loaded_from_prefs_file`, `test_naming_fields_default_to_empty_string`, `test_naming_fields_type_validation` |
| `prefs.py` | `naming_regex` and `naming_template` module vars with load/save support | VERIFIED | Lines 23-24 (defaults), 67 (global decl), 86-89 (load), 107-108 (save) |
| `anchor.py` | `_FRAME_TOKEN_PATTERN` constant and user-regex branch in `suggest_anchor_name()` | VERIFIED | Line 189: `_FRAME_TOKEN_PATTERN = re.compile(...)`, lines 192-230: full implementation |
| `colors.py` | `PrefsDialog` with Anchor Naming section (all required attributes and methods) | VERIFIED | `_local_naming_regex`, `_local_naming_template`, `_naming_regex_edit`, `_naming_template_edit`, `_naming_test_filename_edit`, `_naming_validity_label`, `_on_reset_naming`, `_update_naming_validity_indicator` all present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `anchor.suggest_anchor_name` | `prefs.naming_regex` | `import prefs` inside function body; read at call time | VERIFIED | `anchor.py` line 194: `import prefs`, line 202: `user_regex = prefs.naming_regex` |
| `anchor.suggest_anchor_name` | `prefs.naming_template` | `import prefs` inside function body; read at call time | VERIFIED | `anchor.py` line 208: `naming_template = prefs.naming_template` |
| `PrefsDialog._on_accept` | `prefs_module.naming_regex` | `self._local_naming_regex` flushed on OK | VERIFIED | `colors.py` line 898: read from field; line 904: `prefs_module.naming_regex = self._local_naming_regex` |
| `PrefsDialog._on_accept` | `prefs_module.naming_template` | `self._local_naming_template` flushed on OK | VERIFIED | `colors.py` line 899: read from field; line 905: `prefs_module.naming_template = self._local_naming_template` |
| `_update_naming_validity_indicator` | `_naming_regex_edit.textChanged` | Signal connection in `_build_ui` | VERIFIED | `colors.py` line 619: `self._naming_regex_edit.textChanged.connect(self._update_naming_validity_indicator)` |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| NAME-01 | 15-01, 15-02, 15-03 | User can configure a regex (applied to node's file knob, if present) with named capture groups to derive a default anchor name suggestion | SATISFIED | `prefs.naming_regex` configurable via `PrefsDialog`; `suggest_anchor_name()` reads it at call time and applies it to the file knob basename |
| NAME-02 | 15-01, 15-02, 15-03 | User can configure a template string that substitutes named capture groups from the regex into the suggested name | SATISFIED | `prefs.naming_template` configurable via `PrefsDialog`; `format_map(regex_match.groupdict())` applied in `suggest_anchor_name()` when template is non-empty |
| NAME-03 | 15-01, 15-02, 15-03 | When no file knob is present or regex does not match, anchor naming falls back to existing behavior | SATISFIED | `suggest_anchor_name()`: empty `user_regex` skips new branch entirely; no-match and `re.error` both fall through to hardcoded `_v\d+` path; node without `file` knob returns `""` — all three cases confirmed by passing tests |

No orphaned requirements: all NAME-0x IDs that REQUIREMENTS.md maps to Phase 15 were claimed by all three plans.

---

### Anti-Patterns Found

None. No `TODO`, `FIXME`, `PLACEHOLDER`, stub returns, or empty handler bodies found in any Phase 15 modified files.

---

### Human Verification Required

The automated checks confirm all backend logic and wiring is correct. One gate remains: the PrefsDialog UI changes in `colors.py` were auto-approved during execution because no Nuke/Qt runtime is available in this environment. Human verification is required to confirm the live UI behaviors.

**Note on pre-existing test failure:** `tests/test_anchor_color_system.py` fails with `ModuleNotFoundError: No module named 'nuke'` on collection. This failure predates Phase 15, was logged to `deferred-items.md` in Plan 01, and is not caused by Phase 15 changes.

#### 1. Anchor Naming section layout

**Test:** Open the Anchors plugin Preferences dialog in Nuke.
**Expected:** An "Anchor Naming" label appears directly below the two existing checkboxes ("Enable anchors plugin" and "Input nodes paste as links") and above the horizontal separator line that precedes the Custom Colors section. Three field rows appear: "Regex:", "Template:", and "Test filename:" (pre-filled with "plate_v003.exr"). A validity label and "Reset" button appear to the right of the Test filename field.
**Why human:** Qt widget layout requires a running Nuke or Qt application instance.

#### 2. Live validity indicator — green Match

**Test:** Type `(?P<shot>.+)_v\d+` into the Regex field while the Test filename field shows `plate_v003.exr`.
**Expected:** The validity label immediately turns green and reads "Match".
**Why human:** Requires live Qt event loop for `textChanged` signal propagation.

#### 3. Live validity indicator — red No match

**Test:** With the regex from above still in place, change the Test filename to `render_0001.exr`.
**Expected:** The validity label immediately turns red and reads "No match".
**Why human:** Same as above.

#### 4. Live validity indicator — red Invalid regex

**Test:** Clear the Regex field and type `[invalid(`.
**Expected:** The validity label immediately turns red and reads "Invalid regex".
**Why human:** Same as above.

#### 5. Live validity indicator — blank when empty

**Test:** Clear the Regex field completely.
**Expected:** The validity label goes blank (no text, no color).
**Why human:** Same as above.

#### 6. Reset button behavior

**Test:** Enter any valid text in both the Regex and Template fields, then click "Reset".
**Expected:** Both Regex and Template fields are cleared to empty. The Test filename field retains its current value unchanged.
**Why human:** Button click requires a live Qt event loop.

#### 7. OK persists values

**Test:** Enter `(?P<shot>.+)_v\d+` in Regex and `{shot}_anchor` in Template, click OK. Then reopen Preferences.
**Expected:** Both fields still show the entered values.
**Why human:** Persistence requires Nuke to write and reload `~/.nuke/anchors_prefs.json` during a live session.

#### 8. Cancel discards values

**Test:** Note the current Regex and Template values. Change them to something different, then click Cancel. Reopen Preferences.
**Expected:** The fields show the values that were present when the dialog was opened, not the changed values.
**Why human:** Cancel behavior requires live dialog round-trip.

---

### Gaps Summary

No automated gaps. All 11 truths verified, all 5 artifacts substantive and wired, all 5 key links confirmed, all 3 requirements satisfied.

The only open items are 8 human-verification tests covering live Qt UI behavior (validity indicator reactivity, Reset button, OK persistence, Cancel discard). These were auto-approved during execution because no Nuke/Qt runtime was available.

---

_Verified: 2026-03-16T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
