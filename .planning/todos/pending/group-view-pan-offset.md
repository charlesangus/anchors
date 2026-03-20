---
id: group-view-pan-offset
created: 2026-03-20
source: phase-18-uat
status: pending
---

# Group View pan/zoom via offset calculation

When Alt+A is invoked from a Group View floating panel, we accept the selection but don't pan/zoom the panel to the anchor's location. It may be possible to implement this.

**Hypothesis:** The Group View panel is a tight bounding box around the nodes inside the group. We know where the group is positioned on the parent DAG, so we can potentially calculate the node's offset within the group and use that to pan the Group View panel.

**Approach to investigate:**
- Determine Group View panel position/bounds relative to the group's position in the parent DAG
- Calculate anchor node position relative to the group's origin
- Use that offset to call nuke.zoom() or equivalent to pan the Group View to the right location

**Context:** Currently accepted as a known limitation (no public Nuke API to pan a specific floating panel). But coordinate math may allow us to reverse-engineer the location.
