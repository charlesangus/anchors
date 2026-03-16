# Phase 14: Bug Fixes - Research

**Researched:** 2026-03-16
**Domain:** Python/Qt dialog state capture, Nuke node class dispatch
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### BUG-04: Dot → NoOp anchor (anchor_shortcut)

- When "a" is pressed on a selected Dot node, treat it exactly like any other selected node: route to `create_anchor()` so a NoOp anchor is created with the Dot as its input
- The Dot becomes `input_node` passed to `create_anchor_named()` — the NoOp anchor is placed below the Dot in the DAG (standard positioning logic)
- Remove the `elif selected[0].Class() == 'Dot' and not is_link(selected[0]): _offer_make_dot_anchor(...)` branch from `anchor_shortcut()`
- `_offer_make_dot_anchor()` is kept but marked deprecated — not removed yet

#### BUG-03: Dialog name not captured (ColorPaletteDialog)

- Root cause: swatch click (`_on_swatch_clicked`) and the OK button both call `self.accept()` without first updating `self.chosen_name` from `self._name_edit.text()`
- Fix: override `accept()` on `ColorPaletteDialog` — read `self._name_edit.text()` and assign `self.chosen_name` there before calling `super().accept()`, guarded with `if self._name_edit is not None`
- Clean up: remove all scattered `self.chosen_name = self._name_edit.text()` lines from `keyPressEvent` and `eventFilter` — they are superseded by the `accept()` override and add noise

#### Regression Tests

- BUG-03 tests: unit-test `chosen_name` logic without real Qt — mock `QDialog.accept` and verify `chosen_name` reflects `_name_edit.text()` after `accept()` is called. Add to `test_anchor_color_system.py`
- BUG-04 tests: test `anchor_shortcut()` comprehensively — Dot selected (NoOp path), non-Dot selected (existing behavior), no selection, multiple nodes, existing anchor selected (rename path). Add to `test_dot_type_distinction.py`

### Claude's Discretion

- Exact deprecation comment wording on `_offer_make_dot_anchor()`
- Whether to add `# deprecated` to the function or a full docstring note

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-03 | Name typed in anchor creation dialog is reliably applied as the anchor node's name | `ColorPaletteDialog.accept()` override is the single chokepoint all accept paths flow through; all scattered `chosen_name` assignments in `keyPressEvent` and `eventFilter` are superseded and removed |
| BUG-04 | Pressing "a" on a Dot node creates a regular NoOp-based anchor instead of a Dot anchor | `anchor_shortcut()` line 509 Dot branch (`elif ... Class() == 'Dot' and not is_link(...)`) is removed; the existing `elif selected:` branch at line 511 already calls `create_anchor()` which handles Dot nodes correctly as `input_node` |
</phase_requirements>

## Summary

Phase 14 fixes two isolated bugs in anchor creation, each confined to a single file and a handful of lines. No new dependencies are required; both fixes use patterns already established in the codebase.

BUG-03 is a Qt dialog state-capture bug: `ColorPaletteDialog.chosen_name` is only updated on certain code paths before `self.accept()` is called, so the swatch-click path and the OK-button path leave `chosen_name` stale. The fix is a single `accept()` override on `ColorPaletteDialog` that reads `self._name_edit.text()` once, at the one place all accept paths converge, then calls `super().accept()`. After this override is in place, all eight `self.chosen_name = self._name_edit.text()` copies scattered across `keyPressEvent` and `eventFilter` become dead code and are removed.

BUG-04 is a dispatch bug in `anchor_shortcut()`: a special `elif` branch intercepts Dot-selected nodes and routes them to `_offer_make_dot_anchor()`, which creates a Dot-class anchor instead of a NoOp anchor. Removing that branch lets Dot nodes fall through to the existing `elif selected:` branch, which calls `create_anchor()` — the standard NoOp creation path that already accepts any node as `input_node`. `_offer_make_dot_anchor()` is retained but marked deprecated.

**Primary recommendation:** Two targeted edits (colors.py: add `accept()` override + remove scattered assignments; anchor.py: delete the Dot elif branch) plus regression tests in the two named test files.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python unittest / pytest | stdlib / latest | Test framework | Already in CI (`pytest tests/`) |
| unittest.mock | stdlib | Mock QDialog.accept for offline testing | Used throughout existing test suite |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PySide6 / PySide2 | project runtime | Qt dialog base class | Already abstracted — tests use MagicMock stubs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Overriding `accept()` | Patching every accept call site | Override is single-point; patching N sites is error-prone and creates future regressions |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure
```
workspace/
├── colors.py          # ColorPaletteDialog — BUG-03 fix here
├── anchor.py          # anchor_shortcut() — BUG-04 fix here
└── tests/
    ├── conftest.py                    # stub installation (do not modify)
    ├── stubs.py                       # StubNode/StubKnob (do not modify)
    ├── test_anchor_color_system.py    # BUG-03 regression tests go here
    └── test_dot_type_distinction.py   # BUG-04 regression tests go here
```

### Pattern 1: QDialog.accept() override for state capture

**What:** Override `accept()` in the dialog subclass to consolidate all "user confirmed" logic. Every path that calls `self.accept()` (swatch click, OK button, Enter key, hint-mode key) benefits automatically.

**When to use:** Any time a dialog has multiple accept paths that each need to capture widget state before closing.

**Example:**
```python
# colors.py — inside ColorPaletteDialog (inside the `else:` block where Qt is available)
def accept(self):
    if self._name_edit is not None:
        self.chosen_name = self._name_edit.text()
    super().accept()
```

After this override, every `self.chosen_name = self._name_edit.text()` line in `keyPressEvent` (lines 355, 373, 401, 422) and `eventFilter` (lines 307, 355) is redundant and must be removed.

### Pattern 2: Removing an elif branch from a dispatch function

**What:** `anchor_shortcut()` uses an if/elif/elif/else chain to dispatch based on node class. The Dot branch (line 509-510) is simply deleted; no replacement logic is needed because the next branch (`elif selected:`) already handles the case correctly.

**When to use:** When a special-case override is wrong by design, not just mis-implemented, and the general path already works.

**Example (before):**
```python
elif len(selected) == 1 and selected[0].Class() == 'Dot' and not is_link(selected[0]):
    _offer_make_dot_anchor(selected[0])
elif selected:
    create_anchor()
```

**Example (after):**
```python
elif selected:
    create_anchor()
```

When a Dot is the sole selection, `len(selected) == 1` is truthy and `selected` is truthy, so `elif selected:` fires and `create_anchor()` runs. Inside `create_anchor()`, `selected[0]` (the Dot) becomes `input_node`.

### Pattern 3: Deprecation comment style

**What:** `_offer_make_dot_anchor()` is kept but not called. Mark it clearly so future developers know not to reinstate it.

**Example:**
```python
# Deprecated: superseded by create_anchor() for Dot nodes (BUG-04, Phase 14).
# Retained for reference only — do not call.
def _offer_make_dot_anchor(dot_node):
```

A single-line comment at the function top is consistent with the project style (no formal docstring-based deprecation machinery exists in the codebase).

### Anti-Patterns to Avoid

- **Patching individual call sites instead of overriding accept():** The bug exists precisely because there are already too many scattered assignments. Adding more patches would perpetuate the same fragility.
- **Deleting `_offer_make_dot_anchor()` entirely:** The decision locked it as deprecated-not-deleted.
- **Modifying conftest.py or stubs.py:** These are shared infrastructure. Tests for this phase use `patch()` and `MagicMock` directly, as all existing tests do.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Capturing name on dialog close | Custom signal/event machinery | `accept()` override | Qt's normal OOP mechanism; zero complexity |
| Mocking QDialog.accept in tests | Custom fake dialog class | `patch('colors.ColorPaletteDialog.accept', ...)` or `unittest.mock.MagicMock` | Already the pattern in the test suite |

**Key insight:** Both fixes are deletions or minimal additions to existing code. The risk is in adding too much, not too little.

## Common Pitfalls

### Pitfall 1: Forgetting the `_name_edit is not None` guard in `accept()`
**What goes wrong:** `ColorPaletteDialog` is sometimes constructed with `show_name_field=False`, which leaves `self._name_edit = None`. Calling `self._name_edit.text()` without the guard crashes every non-naming use of the dialog (e.g., `set_anchor_color()`).
**Why it happens:** The fix is written in the `show_name_field=True` context and the other mode is forgotten.
**How to avoid:** The override must guard: `if self._name_edit is not None: self.chosen_name = self._name_edit.text()`.
**Warning signs:** Test for `set_anchor_color()` path (no name field) would raise `AttributeError`.

### Pitfall 2: Leaving scattered `self.chosen_name = self._name_edit.text()` lines in place
**What goes wrong:** The existing assignments in `keyPressEvent` and `eventFilter` become dead code but also create confusion about which line of code is actually responsible for capturing the name. Future maintainers may not understand the override is the canonical path.
**Why it happens:** Conservative partial cleanup — only adding the override without removing the duplicates.
**How to avoid:** The CONTEXT.md decision explicitly requires removing the scattered lines as part of the fix.

### Pitfall 3: The `elif selected:` condition already covers single-Dot selection
**What goes wrong:** A developer might assume the Dot branch needs to be replaced with a different `elif` that re-checks `Dot` class explicitly.
**Why it happens:** Misreading the chain — `elif selected:` fires when `len(selected) >= 1` AND the node is not an anchor, which is exactly the Dot case after removing the earlier branch.
**How to avoid:** Read `create_anchor()`: it already picks `selected[0]` as `input_node` when exactly one node is selected, regardless of class.

### Pitfall 4: BUG-03 test file imports
**What goes wrong:** `test_anchor_color_system.py` has a complex import preamble (it manually stubs and re-imports the real `colors` module). New tests added to this file must respect that preamble — they must not re-import `colors` independently before the preamble completes.
**Why it happens:** The colors module triggers `QtWidgets` import at module level.
**How to avoid:** Add new test classes after the existing class definitions. Use the `_real_colors_module` reference or import `colors` inside test methods where needed.

## Code Examples

Verified patterns from the actual source:

### BUG-03: ColorPaletteDialog accept() override
```python
# colors.py, inside ColorPaletteDialog class body (inside `else:` Qt-available block)
def accept(self):
    if self._name_edit is not None:
        self.chosen_name = self._name_edit.text()
    super().accept()
```

### BUG-03: Lines to remove from keyPressEvent (colors.py)
Lines 355, 373, 401, 422 — all instances of:
```python
if self._name_edit is not None:
    self.chosen_name = self._name_edit.text()
```
(and the equivalent two-liner at eventFilter line 307 and 373)

### BUG-04: anchor_shortcut() after fix (anchor.py lines 502–514)
```python
def anchor_shortcut():
    """If a node is selected, create an anchor from it. Otherwise, pick an anchor to create from."""
    if not prefs.plugin_enabled:
        return
    selected = nuke.selectedNodes()
    if len(selected) == 1 and is_anchor(selected[0]):
        rename_anchor(selected[0])
    elif selected:
        create_anchor()
    else:
        select_anchor_and_create()
```

### BUG-03 regression test pattern (add to test_anchor_color_system.py)
```python
class TestColorPaletteDialogChosenNameCapturedOnAccept(unittest.TestCase):
    """BUG-03: chosen_name is read from _name_edit.text() inside accept()."""

    def setUp(self):
        _ensure_qt_stubs_support_mock_attributes()
        import importlib
        import colors as colors_mod
        importlib.reload(colors_mod)
        self.colors_mod = colors_mod

    def test_chosen_name_set_when_accept_called_directly(self):
        dialog = self.colors_mod.ColorPaletteDialog(
            show_name_field=True, initial_name="old"
        )
        dialog._name_edit.text.return_value = "typed_name"
        with patch.object(self.colors_mod.QtWidgets.QDialog, 'accept'):
            dialog.accept()
        self.assertEqual(dialog.chosen_name, "typed_name")

    def test_chosen_name_not_overwritten_when_name_edit_is_none(self):
        dialog = self.colors_mod.ColorPaletteDialog(show_name_field=False)
        # _name_edit is None; accept() must not crash and must not change chosen_name
        original = dialog.chosen_name
        with patch.object(self.colors_mod.QtWidgets.QDialog, 'accept'):
            dialog.accept()
        self.assertEqual(dialog.chosen_name, original)
```

### BUG-04 regression test pattern (add to test_dot_type_distinction.py)
```python
class TestAnchorShortcutDotRouting(unittest.TestCase):
    """BUG-04: anchor_shortcut() routes Dot-selected to create_anchor(), not _offer_make_dot_anchor()."""

    def _import_anchor(self):
        import importlib
        import anchor as anchor_mod
        importlib.reload(anchor_mod)
        return anchor_mod

    def test_dot_selected_calls_create_anchor_not_offer_make_dot_anchor(self):
        anchor_mod = self._import_anchor()
        import nuke as _nuke
        dot_node = _nuke.StubNode(name='Dot1', node_class='Dot')
        _nuke._selected_nodes = [dot_node]
        with patch.object(anchor_mod, 'create_anchor') as mock_create, \
             patch.object(anchor_mod, '_offer_make_dot_anchor') as mock_offer, \
             patch.object(anchor_mod.prefs, 'plugin_enabled', True), \
             patch('anchor.is_anchor', return_value=False), \
             patch('anchor.is_link', return_value=False):
            anchor_mod.anchor_shortcut()
        mock_create.assert_called_once()
        mock_offer.assert_not_called()

    def test_non_dot_selected_calls_create_anchor(self):
        anchor_mod = self._import_anchor()
        import nuke as _nuke
        read_node = _nuke.StubNode(name='Read1', node_class='Read')
        _nuke._selected_nodes = [read_node]
        with patch.object(anchor_mod, 'create_anchor') as mock_create, \
             patch.object(anchor_mod.prefs, 'plugin_enabled', True), \
             patch('anchor.is_anchor', return_value=False):
            anchor_mod.anchor_shortcut()
        mock_create.assert_called_once()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Scattered `chosen_name` updates at every accept path | Single `accept()` override captures name once | Phase 14 (this phase) | Eliminates silent fallback to initial_name |
| Special Dot dispatch to `_offer_make_dot_anchor()` | Dot falls through to standard `create_anchor()` | Phase 14 (this phase) | Dot → NoOp anchor, consistent with all other node types |

**Deprecated/outdated:**
- `_offer_make_dot_anchor()`: Still present after this phase but deprecated — it created a Dot-class anchor, which is no longer the intended behavior when "a" is pressed on a Dot.

## Open Questions

None — all implementation decisions are locked in CONTEXT.md. Both fixes are well-scoped with clear before/after states.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed via `pip install pytest` in CI) |
| Config file | none — pytest discovers `tests/` by default |
| Quick run command | `pytest tests/test_anchor_color_system.py tests/test_dot_type_distinction.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-03 | `chosen_name` reflects `_name_edit.text()` after `accept()` regardless of accept path | unit | `pytest tests/test_anchor_color_system.py -x -k "chosen_name"` | ✅ (class to be added) |
| BUG-03 | `accept()` with `_name_edit=None` does not crash | unit | `pytest tests/test_anchor_color_system.py -x -k "name_edit_none"` | ✅ (class to be added) |
| BUG-04 | Dot selected → `create_anchor()` called, `_offer_make_dot_anchor()` not called | unit | `pytest tests/test_dot_type_distinction.py -x -k "dot_routing"` | ✅ (class to be added) |
| BUG-04 | Non-Dot selected → existing `create_anchor()` behavior unchanged | unit | `pytest tests/test_dot_type_distinction.py -x -k "non_dot"` | ✅ (class to be added) |
| BUG-04 | Anchor selected → `rename_anchor()` path unchanged | unit | `pytest tests/test_dot_type_distinction.py -x -k "anchor_selected"` | ✅ (class to be added) |
| BUG-04 | No selection → `select_anchor_and_create()` path unchanged | unit | `pytest tests/test_dot_type_distinction.py -x -k "no_selection"` | ✅ (class to be added) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_anchor_color_system.py tests/test_dot_type_distinction.py -x`
- **Per wave merge:** `pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. Both target test files exist and use the same conftest.py/stubs.py infrastructure. No new fixtures or framework installs are needed.

## Sources

### Primary (HIGH confidence)
- `/workspace/colors.py` — Full source read; all accept paths enumerated, `_name_edit` guard pattern confirmed
- `/workspace/anchor.py` — Full source read; `anchor_shortcut()` dispatch chain confirmed at lines 502–514
- `/workspace/tests/conftest.py` — Test infrastructure confirmed: MagicMock PySide6 stubs, StubNode/StubKnob available
- `/workspace/tests/test_anchor_color_system.py` — Import preamble and `_ensure_qt_stubs_support_mock_attributes` pattern confirmed
- `/workspace/tests/test_dot_type_distinction.py` — Test class and helper factory patterns confirmed

### Secondary (MEDIUM confidence)
- `.planning/phases/14-bug-fixes/14-CONTEXT.md` — All locked decisions confirmed against source code; root causes and fixes verified by direct code inspection

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing pytest + unittest.mock confirmed in CI
- Architecture: HIGH — both fix locations verified by reading the actual source lines
- Pitfalls: HIGH — all pitfalls derived from direct code inspection (guard pattern, scattered assignments, elif chain logic)

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable codebase — no external dependencies added)
