---
status: diagnosed
phase: 18-group-context-support
source: 18-01-SUMMARY.md, 18-02-SUMMARY.md
started: 2026-03-19T00:00:00Z
updated: 2026-03-20T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Copy/paste inside a navigated Group
expected: Enter a Group (double-click to navigate inside). Select a node that has an anchor pointing to it. Press Ctrl+C, then Ctrl+V. The pasted node should be replaced by a Link node wired to the anchor — and both the Link and the anchor should be inside the Group's nested DAG, not at root level.
result: pass

### 2. Anchor creation (A key) inside a navigated Group
expected: Navigate inside a Group, click somewhere in the canvas to set focus, then press A with no node selected. The anchor picker opens and lists only anchors inside that Group (not root-level anchors). Selecting one creates a Link node inside the Group wired to that Group-internal anchor.
result: issue
reported: "The Link node is created incorrectly, it is at root level instead of inside the group. Regression, this was working before this round of debugging."
severity: major

### 3. Alt+A navigation inside a navigated Group
expected: Navigate inside a Group that has at least one anchor inside it. Press Alt+A. The picker opens listing the Group's anchors (and any labelled backdrops inside the Group). Selecting an anchor pans/zooms the Group's DAG panel to that anchor's location.
result: issue
reported: "Items appear correctly but Group does not pan/zoom."
severity: major

### 4. Copy/paste from Group View floating panel
expected: Open a Group's internals as a floating Group View panel (right-click → Open in Floating Pane or similar). Select a node inside that panel. Press Ctrl+C then Ctrl+V. Nodes paste inside the Group View (not at root level), and link substitution works correctly.
result: pass

### 5. A key from Group View floating panel
expected: With a Group View floating panel open and focused, press A with no node selected. The anchor picker opens listing only that Group's internal anchors. Selecting one creates a Link node inside the Group (visible in the Group View), not at root level.
result: pass

### 6. Alt+A from Group View floating panel
expected: With a Group View floating panel open and focused, press Alt+A. The picker opens listing the Group's internal anchors and labelled backdrops. Selecting one is accepted (no crash, no silent failure). Note: the Group View panel may not pan/zoom — this is a known limitation of the Group View interface.
result: pass

## Summary

total: 6
passed: 4
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "A key inside a navigated Group creates a Link node inside the Group (not at root level)"
  status: failed
  reason: "User reported: The Link node is created incorrectly, it is at root level instead of inside the group. Regression, this was working before this round of debugging."
  severity: major
  test: 2
  root_cause: "get_items() is called from TabTabTabWidget.show() (tabtabtab.py:667) AFTER all `with nuke.lastHitGroup():` blocks in anchor_shortcut()/select_anchor_and_create() have already exited and lastHitGroup() has reset to root. This overwrites self._hit_group with the root group. When invoke() fires and runs `with self._hit_group: create_from_anchor(anchor)`, it is in root context — so nuke.createNode() creates the Link at root."
  artifacts:
    - path: "anchor.py"
      issue: "anchor_shortcut() captures lastHitGroup() inside `with` blocks that exit before widget construction/show(); select_anchor_and_create() same issue"
    - path: "anchor.py"
      issue: "AnchorPlugin.get_items() (line ~515) sets self._hit_group = nuke.lastHitGroup() — called from show() after context has reset"
    - path: "tabtabtab.py"
      issue: "show() calls self.plugin.get_items() (line 667) which overwrites _hit_group with the now-reset (root) lastHitGroup()"
    - path: "anchor.py"
      issue: "invoke() uses the stale root-level _hit_group, so create_from_anchor() runs at root"
  missing:
    - "Capture nuke.lastHitGroup() once at the very top of anchor_shortcut() before any `with` block opens, store it explicitly"
    - "Pass the pre-captured group to select_anchor_and_create() and set AnchorPlugin._hit_group before calling show() — not inside get_items()"
    - "get_items() must not be responsible for capturing the group context; it should only refresh the items list"

- truth: "Alt+A inside a navigated Group pans/zooms the Group's DAG panel to the selected anchor's location"
  status: failed
  reason: "User reported: Items appear correctly but Group does not pan/zoom."
  severity: major
  test: 3
  root_cause: "nuke.zoom() targets whichever Qt DAG panel currently has focus. The TabTabTabWidget picker steals Qt focus from the Group's DAG panel when shown (tabtabtab.py:674 self.input.setFocus()). When the picker closes, Qt reassigns focus to the root DAG panel (not the nested Group DAG, which shares a window with root). So nuke.zoom() zooms the root panel, not the Group's panel. The `with self._hit_group:` block correctly sets Python node-operation context but has no effect on which DAG panel nuke.zoom() targets — that is governed by Qt focus alone."
  artifacts:
    - path: "anchor.py"
      issue: "navigate_to_anchor() calls nuke.zoom(1.0, [center_x, center_y]) — but nuke.zoom() uses Qt focus, not Python group context"
    - path: "anchor.py"
      issue: "AnchorNavigatePlugin.invoke() wraps navigate_to_anchor() in `with self._hit_group:` which has no effect on nuke.zoom() panel targeting"
    - path: "tabtabtab.py"
      issue: "show() calls self.input.setFocus() (line 674), stealing focus from the Group DAG panel; close() does not restore it to the Group panel"
    - path: "tabtabtab.py"
      issue: "create() calls invoke() at line 702, then self.close() at line 704 — focus not restored before zoom"
  missing:
    - "Before calling nuke.zoom(), programmatically re-focus the correct Group DAG panel widget (requires navigating Qt widget tree to find the embedded Group DAG panel by group context)"
    - "Alternative: use QTimer.singleShot(0, ...) to defer zoom until after picker closes AND after re-focusing the Group panel"
