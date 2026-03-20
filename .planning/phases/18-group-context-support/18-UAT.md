---
status: complete
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
  artifacts: []
  missing: []

- truth: "Alt+A inside a navigated Group pans/zooms the Group's DAG panel to the selected anchor's location"
  status: failed
  reason: "User reported: Items appear correctly but Group does not pan/zoom."
  severity: major
  test: 3
  artifacts: []
  missing: []
