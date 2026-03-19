# Phase 18: Attempt 1 Findings — `nuke.thisGroup()` Approach

**Date:** 2026-03-19
**Approach tried:** Replace all `nuke.allNodes()` call sites with a helper `all_nodes_in_context()` that passes `group=nuke.thisGroup()`.
**Result:** Reverted — did not fix the core issues.

---

## What Was Built

Created `all_nodes_in_context(node_class=None)` in `link.py`:

```python
def all_nodes_in_context(node_class=None):
    current_group = nuke.thisGroup()
    if node_class is not None:
        return nuke.allNodes(node_class, group=current_group)
    return nuke.allNodes(group=current_group)
```

Replaced bare `nuke.allNodes()` calls in:
- `link.py` — `find_smallest_containing_backdrop()`
- `anchors.py` — `copy_anchors()`
- `labels.py` — `_update_dot_link_labels()`
- `anchor.py` — all 8 call sites: `all_anchors()`, `get_links_for_anchor()`, `rename_anchor_to()` (x2), `reconnect_anchor_node()`, `reconnect_all_links()`, `AnchorNavigatePlugin.get_items()`, `select_anchor_and_navigate()`

Added `tests/test_group_context.py` with 11 test classes, 210 tests total passing.

---

## UAT Results (Live Nuke Session)

### ✗ Link creation inside a Group — NOT FIXED
- Pressing the link-creation menu item inside a Group still does not work.
- Same behaviour as before the change.

### ✓ Copy-paste inside a Group — WORKED BEFORE, STILL WORKS
- Ctrl+C/V in a Group works. But this already worked before Phase 18.

### ✗ Copy-paste inside Group *view* — STILL BROKEN
- Copy-paste inside the Group view (i.e. the Group's own panel/viewer context) does not work.

### ~ Alt+A picker — PARTIAL / INCONSISTENT
- The Alt+A picker *does* list Group anchors when the user is inside a Group node. Partial improvement.
- But: selecting an anchor does nothing — it does not navigate the Group's DAG view to the anchor.
- The anchors surfaced in the menu are inconsistent (sometimes shows the right ones, sometimes not).

---

## Root Cause Analysis

The approach used `nuke.thisGroup()`. This is the wrong API for this use case.

**`nuke.thisGroup()`** — Returns the Group node that the *currently-executing script* belongs to. This is relevant when a callback or knob script is literally running inside a Group's scope. In our menu callbacks, which are registered at the root level, `nuke.thisGroup()` returns `nuke.root()`, i.e. the root DAG — not the Group the user is visually inside.

**`nuke.lastHitGroup()`** — Returns the last Group node the user *clicked in* the node graph. This is what the goal statement referenced. This is the correct mechanism to detect "what Group context is the user currently operating in?" at the moment a menu item fires.

The original roadmap goal statement explicitly said "respecting `nuke.lastHitGroup()`". The planner chose `nuke.thisGroup()` because it appeared in the Nuke Python docs as the standard "current group context" API — but that's only correct for code running *inside* a Group as a panel/script, not for root-level menu callbacks responding to user interaction.

---

## What to Try Next

1. **Use `nuke.lastHitGroup()`** as the context source instead of `nuke.thisGroup()`.
   - `nuke.lastHitGroup()` returns `None` when user is at root, and returns the Group node when user last clicked inside one.
   - Helper should be: `current_group = nuke.lastHitGroup() or nuke.root()`

2. **Navigation (select_anchor_and_navigate)** may need to call `nuke.show(group_node)` or use `group_node.begin()` / `group_node.end()` context managers to actually switch the DAG view to the Group before calling the navigate logic.

3. **The link-creation issue** may be separate — needs investigation of which specific call path fails and what error (if any) occurs. Possibly `nuke.lastHitGroup()` alone doesn't fix it; the link creation code may need to set `nuke.thisGroup()` context via `group.begin()` before running.

4. **Test the `nuke.lastHitGroup()` hypothesis first** in a scratch script before writing a full plan:
   ```python
   import nuke
   grp = nuke.lastHitGroup()
   print("lastHitGroup:", grp)
   print("allNodes in context:", nuke.allNodes(group=grp) if grp else nuke.allNodes())
   ```

---

## Commits in This Attempt (All Reverted)

| Hash | Message |
|------|---------|
| `03a3632` | feat(18-01): add all_nodes_in_context() helper in link.py and thisGroup stub |
| `e3ca26a` | feat(18-01): update anchors.py and labels.py to use all_nodes_in_context() |
| `0e5ca2e` | test(18-01): add Group-context unit tests for all_nodes_in_context and call sites |
| `ddc8daf` | feat(18-02): replace all nuke.allNodes() in anchor.py with all_nodes_in_context() |
| `28c6e97` | test(18-02): add Group-context tests for anchor operations |
