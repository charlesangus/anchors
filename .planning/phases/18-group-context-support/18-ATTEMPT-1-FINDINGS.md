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

## Corrected Understanding of `nuke.allNodes()` Behaviour

**`nuke.allNodes()` already returns nodes in the current context.** It is context-sensitive. The `with group_node:` pattern confirms this:

```python
with group_node:
    all_nodes = nuke.allNodes()  # returns nodes inside group_node
```

When a menu item fires inside a Group, `nuke.allNodes()` already returns that Group's nodes — no `group=` parameter needed. This means **Attempt 1's `all_nodes_in_context()` helper was redundant** for menu callbacks; the bare calls already did the right thing in that context.

**`nuke.lastHitGroup()` behaviour — confirmed by UAT:**
- ✓ Works in **Group View** (floating panel: Group internals exposed at root level)
- ✗ Does NOT work **inside a Group** (navigated main DAG) — returns root node

**Menu item context — confirmed:** Menu items are invoked with the context of the current DAG/group. `nuke.thisGroup()` and `nuke.allNodes()` from a menu callback correctly reflect the active Group context. The Script Editor is always root context and cannot be used to test this.

---

## Revised Root Cause Analysis

Given the above, the actual bugs are elsewhere. Current hypotheses (unconfirmed):

### 1. `nuke.exists(node.name())` fails in Qt signal context

`AnchorPlugin.invoke()` and `AnchorNavigatePlugin.invoke()` are called from a Qt signal (`clicked` / `returnPressed`), which fires **outside** the original menu-callback context. At that point `nuke.exists(node.name())` checks the local node name (e.g. `"Anchor_Foo"`) in whatever context is active — which may be root. A Group-internal node named `"Anchor_Foo"` would not be found at root → early return → no link created / no navigation.

Fix candidate: use `node.fullName()` (returns the full dotted path, e.g. `"MyGroup.Anchor_Foo"`) which `nuke.exists()` accepts regardless of context.

### 2. Scope mismatch for link creation

Before Attempt 1, bare `nuke.allNodes()` in a menu callback inside a Group returned **Group-internal nodes** (correct context). If the Group contains no anchors, `all_anchors()` returns empty → `select_anchor_and_create()` returns early → picker never opens. This is the "same behaviour as before" the user describes.

The question this raises: **what should the anchor search scope be for link creation inside a Group?** Options:
- Only Group-internal anchors (current behaviour — correct if anchor and link are both inside the Group)
- Root-level anchors (useful if you want to reference a root-level anchor from inside a Group)
- All anchors recursively (broadest)

This needs a design decision before coding.

### 3. Copy-paste in Group View broken

`anchors.copy_anchors()` and `paste_anchors()` are triggered via `menu.addCommand("Edit/Copy", ...)`. In Group View (floating panel), the copy/paste context may not be the Group. `nuke.allNodes()` there may return root nodes. `find_anchor_node()` uses `nuke.toNode()` with a full path — this may or may not cross group boundaries correctly.

Needs investigation of what `nuke.allNodes()` and `nuke.toNode()` return in the Group View floating panel context.

---

## Open Questions for Attempt 2

1. What should the anchor search scope be for **link creation** inside a Group? (Group-only vs root vs recursive)
2. Does `nuke.exists(node.fullName())` fix the invoke() early-return in the Qt signal context?
3. In **Group View** (floating panel), what context does the menu callback see? Does `nuke.allNodes()` return Group nodes or root nodes there?
4. Does `nuke.zoomToFitSelected()` correctly zoom the active Group DAG after navigation, or does it operate on the wrong panel?

---

## Commits in This Attempt (All Reverted)

| Hash | Message |
|------|---------|
| `03a3632` | feat(18-01): add all_nodes_in_context() helper in link.py and thisGroup stub |
| `e3ca26a` | feat(18-01): update anchors.py and labels.py to use all_nodes_in_context() |
| `0e5ca2e` | test(18-01): add Group-context unit tests for all_nodes_in_context and call sites |
| `ddc8daf` | feat(18-02): replace all nuke.allNodes() in anchor.py with all_nodes_in_context() |
| `28c6e97` | test(18-02): add Group-context tests for anchor operations |
