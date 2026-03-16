# Phase 14: Bug Fixes - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two anchor creation bugs: (1) the anchor creation dialog name reliably lands on the created node, and (2) pressing "a" on a Dot node creates a NoOp-based anchor instead of a Dot anchor. Regression tests cover both behaviors.

</domain>

<decisions>
## Implementation Decisions

### BUG-04: Dot → NoOp anchor (anchor_shortcut)

- When "a" is pressed on a selected Dot node, treat it exactly like any other selected node: route to `create_anchor()` so a NoOp anchor is created with the Dot as its input
- The Dot becomes `input_node` passed to `create_anchor_named()` — the NoOp anchor is placed below the Dot in the DAG (standard positioning logic)
- Remove the `elif selected[0].Class() == 'Dot' and not is_link(selected[0]): _offer_make_dot_anchor(...)` branch from `anchor_shortcut()`
- `_offer_make_dot_anchor()` is kept but marked deprecated — not removed yet

### BUG-03: Dialog name not captured (ColorPaletteDialog)

- Root cause: swatch click (`_on_swatch_clicked`) and the OK button both call `self.accept()` without first updating `self.chosen_name` from `self._name_edit.text()`
- Fix: override `accept()` on `ColorPaletteDialog` — read `self._name_edit.text()` and assign `self.chosen_name` there before calling `super().accept()`, guarded with `if self._name_edit is not None`
- Clean up: remove all scattered `self.chosen_name = self._name_edit.text()` lines from `keyPressEvent` and `eventFilter` — they are superseded by the `accept()` override and add noise

### Regression Tests

- BUG-03 tests: unit-test `chosen_name` logic without real Qt — mock `QDialog.accept` and verify `chosen_name` reflects `_name_edit.text()` after `accept()` is called. Add to `test_anchor_color_system.py`
- BUG-04 tests: test `anchor_shortcut()` comprehensively — Dot selected (NoOp path), non-Dot selected (existing behavior), no selection, multiple nodes, existing anchor selected (rename path). Add to `test_dot_type_distinction.py`

### Claude's Discretion

- Exact deprecation comment wording on `_offer_make_dot_anchor()`
- Whether to add `# deprecated` to the function or a full docstring note

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `create_anchor()` (anchor.py:327): already handles the full dialog + NoOp creation flow — BUG-04 fix just routes Dot-selected case here instead of `_offer_make_dot_anchor()`
- `_offer_make_dot_anchor()` (anchor.py:482): existing Dot-anchor creation; to be deprecated, not deleted
- `ColorPaletteDialog` (colors.py): the dialog class where BUG-03 fix goes — override `accept()` method

### Established Patterns

- All accept paths in `ColorPaletteDialog` call `self.accept()` (swatch click, OK button, Enter key, hint-mode key) — overriding `accept()` is the single-fix-all-paths approach
- `_name_edit` is `None` when `show_name_field=False` — guard required in `accept()` override
- Existing test style: `tests/stubs.py` + `conftest.py` TDD infrastructure; mock-based offline unit tests
- BUG-03 tests go in `test_anchor_color_system.py`; BUG-04 tests go in `test_dot_type_distinction.py`

### Integration Points

- `anchor_shortcut()` (anchor.py:502): where BUG-04 Dot branch is removed
- `ColorPaletteDialog.accept()` (colors.py): new method override for BUG-03 fix
- `create_anchor()` (anchor.py:327): reads `dialog.chosen_name` — must be correct after fix

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for deprecation comment style and test naming.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-bug-fixes*
*Context gathered: 2026-03-16*
