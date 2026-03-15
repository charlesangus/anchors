# Requirements: anchors (paste_hidden → v1.3)

**Defined:** 2026-03-15
**Core Value:** Copy and paste must reconnect predictably — anchors provide stable, navigable references; hidden inputs reconnect to their source without ceremony.

## v1.3 Requirements

### Rename

- [x] **REN-01**: Project renamed from `paste_hidden` to `anchors` across all source files, tests, CI, and config in one atomic commit
- [x] **REN-02**: GitHub repo renamed from `paste_hidden` to `anchors` via `gh`

### Anchor Naming

- [ ] **NAME-01**: User can configure a regex (applied to node's file knob, if present) with named capture groups to derive a default anchor name suggestion
- [ ] **NAME-02**: User can configure a template string (e.g. `Anchor_{anchorname}`) that substitutes named capture groups from the regex into the suggested name pre-filled in the anchor creation dialog
- [ ] **NAME-03**: When no file knob is present or regex doesn't match, anchor naming falls back to existing behavior

### Site Config

- [ ] **SITE-01**: Site-level config file path resolved from `ANCHORS_SITE_CONFIG` env var
- [ ] **SITE-02**: Site config can set and lock user-configurable settings (naming regex, template, and any other prefs)
- [ ] **SITE-03**: "Override Site Config" checkbox in PrefsDialog re-enables individual locked fields for the user

### Bug Fixes

- [ ] **BUG-03**: Name typed in anchor creation dialog is reliably applied as the anchor node's name
- [ ] **BUG-04**: Pressing "a" on a Dot node creates a regular NoOp-based anchor instead of a Dot anchor

### Public API

- [ ] **API-01**: Public `anchors` API module exposes a function to create an anchor with specified name, color, and source node
- [ ] **API-02**: Public API exposes a function to wire an existing node to an anchor by anchor name
- [ ] **API-03**: All public API functions are documented with docstrings (parameters, return values, exceptions)

## Future Requirements

### Navigation

- **NAV-03**: Full browser-style forward/back navigation history stack (deferred — single-slot back covers primary use case)

### Color

- **COLOR-V2-01**: Manual `tile_color` changes by user propagate to link nodes (deferred — low priority, accepted by design)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Undo/redo stack integration | Nuke API complexity, not requested |
| Cross-script reconnection for hidden-input Dot nodes | Dots are positional/ad-hoc — explicitly excluded |
| Backdrops as link targets | Navigate-only (no connectable outputs) |
| External persistence (database, remote API) | Local-only plugin |
| Multi-user / shared anchor libraries | Single-artist tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REN-01 | Phase 13 | Complete |
| REN-02 | Phase 13 | Complete |
| BUG-03 | Phase 14 | Pending |
| BUG-04 | Phase 14 | Pending |
| NAME-01 | Phase 15 | Pending |
| NAME-02 | Phase 15 | Pending |
| NAME-03 | Phase 15 | Pending |
| SITE-01 | Phase 16 | Pending |
| SITE-02 | Phase 16 | Pending |
| SITE-03 | Phase 16 | Pending |
| API-01 | Phase 17 | Pending |
| API-02 | Phase 17 | Pending |
| API-03 | Phase 17 | Pending |

**Coverage:**
- v1.3 requirements: 13 total
- Mapped to phases: 13 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 — traceability mapped after v1.3 roadmap creation*
