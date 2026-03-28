# Quick Task 260328-7uv: Cycle Through Links for Anchor

## What was built

`cycle_next_link()` in `anchor.py` — select an anchor node and press Alt+L to zoom to the first link node referencing it. Press Alt+L again to advance to the next link. After visiting all links, the cycle wraps around. Switching to a different anchor resets the cycle.

## Key decisions

- DAG position saved only on first invocation of a new cycle (Alt+Z returns to pre-cycle position)
- Links sorted by node name for deterministic cycle order
- Cycle state tracked in module-level variables (`_cycle_anchor_name`, `_cycle_links`, `_cycle_link_index`)
- Uses `nuke.zoomToFitSelected()` to frame each individual link node

## Files modified

- `anchor.py` — added `cycle_next_link()` and cycle state variables
- `menu.py` — registered "Cycle Links" command with Alt+L shortcut
- `tests/test_anchor_navigation.py` — 8 new tests (220 total passing)

## Tests

220 passed, 0 failed.
