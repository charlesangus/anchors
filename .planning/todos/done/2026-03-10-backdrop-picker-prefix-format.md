---
created: 2026-03-10T00:00:00Z
title: Consider "Backdrops/Label" prefix format in Alt+A picker
area: navigation
files:
  - anchor.py
---

# Backdrop picker prefix format

**Observation (Phase 04 UAT):** Backdrop entries in the Alt+A picker currently display as `"BG Comp [Backdrop]"` rather than `"Backdrops/BG Comp"`.

**Suggestion:** Using a `Backdrops/` prefix (tabtabtab category-style) would allow users to filter backdrops by typing "ba", consistent with how anchor filtering works. Current `[Backdrop]` suffix format works but doesn't enable prefix-based filtering.

**Decision:** Deferred — current format is acceptable. Revisit if navigation UX becomes a pain point.
