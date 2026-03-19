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

**`nuke.thisGroup()`** — Returns the Group node that the *currently-executing script* belongs to. For root-level menu callbacks this is always `nuke.root()`. Confirmed: does not work.

**`nuke.lastHitGroup()`** — Confirmed by UAT:
- ✓ Works in **Group View** (floating panel: user opened Group internals in a separate panel while main DAG stays at root)
- ✗ Does NOT work **inside a Group** (main DAG navigated into the Group) — returns root node in that case

So there are **two distinct contexts** we need to handle, and no single API covers both:

| Context | Description | `nuke.lastHitGroup()` | `nuke.thisGroup()` |
|---------|-------------|----------------------|-------------------|
| Root DAG | User is at top-level script | root | root |
| Group View (floating) | Group panel open alongside root DAG | ✓ returns the Group | root |
| Inside a Group (navigated) | Main DAG view shows Group contents | root | root |

---

## Open Questions for Attempt 2

The fundamental problem: **there is no confirmed Nuke Python API that reliably returns "the Group whose DAG is currently displayed in the main panel."**

Candidates to investigate:

1. **`nuke.selectedNodes()`** — When inside a Group, selected nodes belong to that Group. `nuke.selectedNodes()[0].parent()` might give the current Group. But fails if nothing is selected.

2. **`nuke.activeViewer().node().dependencies()`** — The viewer is inside the current DAG; traversing its graph might identify the Group container. Fragile.

3. **TCL bridge** — `nuke.tcl('nuke currentGroup')` or similar. Nuke's TCL layer may expose the current DAG context that Python doesn't surface directly.

4. **`nuke.zoom()` / `nuke.center()` context** — These operate on the current DAG view; they may have a companion API to identify which group that view belongs to.

5. **Combining both APIs** — Use `nuke.lastHitGroup()` for Group View cases (where it works), and a fallback for the navigated-inside case.

6. **Node creation as a probe** — Create a temporary node, check its `.parent()`, delete it. Hacky but definitive.

**Before writing Attempt 2:** Investigate these in a live Nuke session to find what actually returns the correct Group in the "navigated inside" case.

---

## Commits in This Attempt (All Reverted)

| Hash | Message |
|------|---------|
| `03a3632` | feat(18-01): add all_nodes_in_context() helper in link.py and thisGroup stub |
| `e3ca26a` | feat(18-01): update anchors.py and labels.py to use all_nodes_in_context() |
| `0e5ca2e` | test(18-01): add Group-context unit tests for all_nodes_in_context and call sites |
| `ddc8daf` | feat(18-02): replace all nuke.allNodes() in anchor.py with all_nodes_in_context() |
| `28c6e97` | test(18-02): add Group-context tests for anchor operations |
