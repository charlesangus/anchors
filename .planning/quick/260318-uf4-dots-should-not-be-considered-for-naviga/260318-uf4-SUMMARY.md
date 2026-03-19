---
phase: quick
plan: 260318-uf4
subsystem: anchor-navigation
tags: [dot-anchor, font-size-gate, label-commands, is_anchor, constants]

requires:
  - phase: dot-anchor-detection
    provides: is_anchor() predicate and mark_dot_as_anchor() in link.py

provides:
  - Font size gate on Dot anchor detection (note_font_size < 33 = not an anchor)
  - DOT_ANCHOR_MIN_FONT_SIZE=33 and DOT_LABEL_FONT_SIZE_SMALL=33 constants
  - create_small_label() function for Dot font size 33 labels
  - Label (Small) menu command with +B shortcut

affects: [anchor-navigation, label-creation, dot-classification]

tech-stack:
  added: []
  patterns:
    - "Font size gate: check note_font_size < DOT_ANCHOR_MIN_FONT_SIZE before any Dot anchor checks"
    - "TDD: RED (failing tests) committed before GREEN (implementation)"

key-files:
  created:
    - tests/test_anchor_navigation.py (TestDotFontSizeAnchorGate class — 8 new tests)
  modified:
    - constants.py
    - link.py
    - labels.py
    - menu.py

key-decisions:
  - "Font size gate is applied FIRST in is_anchor() Dot path — returns False immediately if note_font_size < 33, regardless of anchor knob or label content"
  - "mark_dot_as_anchor() and _update_dot_link_labels() in _apply_label() are gated: only called when dot_font_size >= DOT_ANCHOR_MIN_FONT_SIZE"
  - "DOT_ANCHOR_MIN_FONT_SIZE = 33 equals DOT_LABEL_FONT_SIZE_SMALL — smallest qualifying anchor label size"
  - "Label (Small) shortcut is +B (Shift+B), following +M (Large) and +N (Medium)"

patterns-established:
  - "is_anchor() Dot path: font size gate before knob and legacy label checks"
  - "_apply_label(): font-size-gated anchor marking — only anchor-sized labels trigger mark_dot_as_anchor()"

requirements-completed: [DOT-FONT-GATE, DOT-SMALL-LABEL-CMD]

duration: 15min
completed: 2026-03-18
---

# Quick Task 260318-uf4: Dots Should Not Be Considered for Navigation Summary

**Font size gate added to is_anchor() so Dot nodes with note_font_size < 33 are excluded from anchor navigation, plus a new Label (Small) menu command at font size 33**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-19T04:45:00Z
- **Completed:** 2026-03-19T05:00:20Z
- **Tasks:** 2
- **Files modified:** 5 (constants.py, link.py, labels.py, menu.py, tests/test_anchor_navigation.py)

## Accomplishments

- `is_anchor()` in link.py now gates ALL Dot paths on `note_font_size >= DOT_ANCHOR_MIN_FONT_SIZE (33)` — small-labelled Dots no longer appear in navigation
- `_apply_label()` in labels.py only calls `mark_dot_as_anchor()` and `_update_dot_link_labels()` when the applied font size qualifies
- New `DOT_LABEL_FONT_SIZE_SMALL = 33` and `DOT_ANCHOR_MIN_FONT_SIZE = 33` constants in constants.py
- New `create_small_label()` function and "Label (Small)" menu entry (Shift+B) for font size 33 Dot labels
- 8 new tests in `TestDotFontSizeAnchorGate`, all 199 suite tests passing

## Task Commits

1. **Task 1 RED: Failing tests for font size gate** — `fd03856` (test)
2. **Task 1 GREEN: Font size gate implementation** — `66b0fbb` (feat)
3. **Task 2: Label (Small) command** — `605a4a3` (feat)

_TDD tasks have separate RED and GREEN commits._

## Files Created/Modified

- `constants.py` — Added `DOT_LABEL_FONT_SIZE_SMALL = 33` and `DOT_ANCHOR_MIN_FONT_SIZE = 33`
- `link.py` — `is_anchor()` Dot path: early-return False when `note_font_size < DOT_ANCHOR_MIN_FONT_SIZE`; import added
- `labels.py` — `_apply_label()` gates `mark_dot_as_anchor()` and `_update_dot_link_labels()` on font size; added `DOT_LABEL_FONT_SIZE_SMALL` import; added `create_small_label()` function
- `menu.py` — Added `Label (Small)` entry with `+B` shortcut between Medium and Append Label
- `tests/test_anchor_navigation.py` — Added `TestDotFontSizeAnchorGate` class with 8 tests

## Decisions Made

- Font size gate placed as the FIRST check inside the `if node.Class() == 'Dot':` block in `is_anchor()`, before the explicit anchor knob and legacy label checks. This ensures no path bypasses it.
- The `_update_dot_link_labels()` call in `_apply_label()` is also gated — it only applies to anchor dots (those with a qualifying font size), so link label propagation is correctly suppressed for small-labelled Dots.
- Both new constants equal 33, which is also `NODE_LABEL_FONT_SIZE_LARGE` and `DOT_LINK_LABEL_FONT_SIZE`. The explicit named constants make intent clear without magic numbers.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Dot anchor navigation is now correctly filtered by font size
- Large (111), Medium (66), and Small (33) labelled Dots all qualify as anchors
- Dots with default/unlabelled font sizes (typically 11) are excluded from navigation
- No regressions in any existing anchor creation, renaming, copy/paste, or link flows

---
*Quick task: 260318-uf4*
*Completed: 2026-03-18*
