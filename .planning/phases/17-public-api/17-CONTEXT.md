# Phase 17: Public API - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose a stable, documented public API module (`api.py`) so that external Nuke modules (e.g. templating systems) can programmatically create anchor nodes with specified name, color, and source node. All public functions are documented with docstrings including inline usage examples.

This phase does NOT add link node creation or downstream anchor consumption — that is a separate concern. Creating the anchor (with its input wired) is the primary operation.

</domain>

<decisions>
## Implementation Decisions

### API module location
- New `api.py` file at the project root (alongside `anchor.py`, `prefs.py`, etc.)
- External callers import from `api.py` directly: `from api import create_anchor`
- `api.py` is a thin wrapper — it imports and delegates to internal `anchor.py` functions
- No logic is duplicated; internal implementation can evolve freely as long as public signatures stay stable

### Wire function semantics (API-02)
- API-02 ("wire an existing node to an anchor by anchor name") is fully satisfied by the `input_node=` parameter on `create_anchor()`
- No separate post-creation wiring function is needed
- "Wiring" = passing the source node as `input_node` at creation time — the anchor's input is set and the anchor is positioned below the source node

### Error handling contract
- Invalid name (sanitizes to empty string): raise `ValueError` with a descriptive message — consistent with existing `create_anchor_named()` behavior
- Called outside a running Nuke session (`nuke` module unavailable): raise `RuntimeError('anchors API requires a running Nuke session')`
- No silent failures or None returns for error conditions

### Documentation format
- Docstrings only — no separate markdown file or README section
- Each public function's docstring follows the NumPy/Google-style pattern already established in `anchor.py`: Parameters, Returns, Raises, Examples sections
- Every function includes an `Examples` block with a realistic templating-style call to make the API immediately usable without reading other files

### Claude's Discretion
- Exact public function signature names (e.g. `create_anchor` vs `make_anchor`) — follow the clearest naming
- Whether to expose `find_anchor_by_name` as a public helper or keep it internal
- Module-level docstring content for `api.py`

</decisions>

<specifics>
## Specific Ideas

- Primary use case is a **templating system** — external scripts that set up a node graph programmatically with pre-named, pre-colored anchors connected to specific source nodes
- The API should feel like a clean, intentional public surface — not just raw internal functions exposed

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in REQUIREMENTS.md and the decisions above.

### Requirements
- `.planning/REQUIREMENTS.md` §API-01, API-02, API-03 — the three public API requirements this phase must satisfy

### Existing implementation (read before planning)
- `anchor.py` — `create_anchor_named()` (lines ~397–438), `create_link_for_anchor_named()` (lines ~452–463), `find_anchor_by_name()` (lines ~174–181), `sanitize_anchor_name()` (lines ~48–50) — these are the internal functions `api.py` will wrap
- `anchor.py` — existing docstring style to follow (Parameters/Returns blocks already present)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `anchor.create_anchor_named(name, input_node=None, color=None)` — already does everything API-01/API-02 require; `api.py` thin-wraps this
- `anchor.sanitize_anchor_name(name)` — name validation already implemented; ValueError is already raised by `create_anchor_named` when sanitized name is empty
- `anchor.find_anchor_by_name(display_name)` — finds anchor by display name; may be worth exposing as a public helper

### Established Patterns
- Internal functions use NumPy-style docstrings (Parameters/Returns sections) — `api.py` extends this pattern with added Raises and Examples sections
- Module-level `import nuke` is always at the top — no lazy import pattern exists; the RuntimeError guard for missing nuke needs to be explicit in each public function or at module load time

### Integration Points
- `api.py` imports from `anchor.py` only — no other internal module imports needed for the initial surface
- Callers of `api.py` will `import api` from their own `.nuke` scripts or plugin modules alongside `import anchors`

</code_context>

<deferred>
## Deferred Ideas

- Exposing link node creation (PostageStamp/NoOp) via the public API — not needed for the templating use case; separate phase if ever required
- Post-creation wiring (connecting a source to an already-existing anchor) — not needed; user confirmed `input_node=` at creation time is sufficient

</deferred>

---

*Phase: 17-public-api*
*Context gathered: 2026-03-18*
