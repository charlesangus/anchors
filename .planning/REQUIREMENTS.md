# Requirements: anchors

**Defined:** 2026-03-19
**Core Value:** Copy and paste must reconnect predictably — anchors provide stable, navigable references; hidden inputs reconnect to their source without ceremony.

## v1.4 Requirements

### Group Support

- [x] **GROUP-01**: Copy/paste (Ctrl+C/V) works correctly when the user is inside a Group's nested DAG
- [x] **GROUP-02**: Anchor creation popup opens and functions correctly inside a Group (respects `nuke.lastHitGroup()`)
- [x] **GROUP-03**: Link creation works correctly inside a Group's nested DAG
- [x] **GROUP-04**: Anchor navigation (Alt+A picker) works correctly inside a Group's nested DAG

### Documentation

- [ ] **DOCS-01**: `docs/` folder contains a Quick Start guide (Markdown) covering plugin installation and basic orientation
- [ ] **DOCS-02**: Quick Start guide covers creating anchors — the `a` shortcut, naming dialog, and color picker — with PNG screenshot placeholders
- [ ] **DOCS-03**: Quick Start guide covers anchor navigation — Alt+A picker, jumping to anchors — with PNG screenshot placeholders
- [ ] **DOCS-04**: Quick Start guide covers copy/paste semantics — how Ctrl+C/V behaves with anchors and links — with PNG screenshot placeholders

## Future Requirements

### Navigation

- **NAV-03**: Full forward/back DAG navigation history stack (deferred from v1.0 — single-slot back covers primary use case)

### Bug Fixes (Pending Todos)

- Fix anchor coloring for some node types
- Fix popup not working inside Groups (→ GROUP-01 through GROUP-04 in this milestone)
- Hidden-input dots display input node name instead of Link text
- Consider "Backdrops/Label" prefix format in Alt+A picker

### Code Quality

- Decompose `paste_anchors()` — 96-line function with nested conditionals (TODO.md)
- Refactor `prefs.py` global state for test isolation (TODO.md)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Undo/redo stack integration | Nuke API complexity, not requested |
| Cross-script reconnection for hidden-input Dot nodes | Explicitly excluded — Dots are positional/ad-hoc |
| Backdrops as link targets | Navigate-only (no connectable outputs) |
| External persistence | Local-only plugin |
| Multi-user / shared anchor libraries | Single-artist tool |
| Animated GIFs in Quick Start | PNG screenshots sufficient; GIFs heavier to produce |
| Installation section in Quick Start | User knows how to install; not requested |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GROUP-01 | Phase 18 | Complete |
| GROUP-02 | Phase 18 | Complete |
| GROUP-03 | Phase 18 | Complete |
| GROUP-04 | Phase 18 | Complete |
| DOCS-01 | Phase 19 | Pending |
| DOCS-02 | Phase 19 | Pending |
| DOCS-03 | Phase 19 | Pending |
| DOCS-04 | Phase 19 | Pending |

**Coverage:**
- v1.4 requirements: 8 total
- Mapped to phases: 8 (Phase 18: 4, Phase 19: 4)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after v1.4 roadmap creation*
