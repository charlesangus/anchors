# Phase 19: Quick Start Documentation - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `docs/quick-start.md` — a workflow-focused guide for a new user to get productive with the plugin's three primary workflows: anchor creation, anchor navigation, and copy/paste semantics. Installation is out of scope. This is not an API reference; that's the README.

</domain>

<decisions>
## Implementation Decisions

### Guide entry point
- Open with a brief concept intro: 2–3 sentences covering all three systems (anchors, links, copy/paste) as a single tight paragraph
- Example framing: "An anchor is a named reference node. A link points to it. Ctrl+C/V are context-aware replacements for Nuke's built-in clipboard."
- Then go straight into the first workflow — no further preamble

### Tone and depth
- Assume full Nuke fluency — reader knows PostageStamp, NoOp, Dot, DAG, knobs. No Nuke basics explained.
- Writing style: numbered steps with outcome notes (e.g. "3. Name the anchor — the dialog pre-fills from the file path.")
- Describe *what* happens, not *why* — no rationale or design explanations

### Workflow coverage scope

**Anchor creation (full A-key coverage):**
- Happy path: select a node → press A → name → done
- Nothing selected → A opens the link-creation fuzzy picker
- Anchor already selected → A opens the rename dialog
- Unanchored Dot selected → A promotes it to a Dot anchor (size picker first, then label)
- Color picker available in the creation and rename dialogs

**Anchor navigation:**
- Alt+A opens fuzzy picker → select anchor → DAG zooms to it
- Alt+Z returns to the previous DAG position (complete the navigation loop)

**Copy/paste semantics:**
- Happy path: Ctrl+C/V with smarter reconnection — input nodes become hidden-input proxies, auto-reconnected on paste
- Mention that the behavior can be disabled via Preferences (plugin-enabled toggle)
- No edge cases (cross-script, old-style paste, LINK_CLASSES passthrough) — those are in README

### Screenshot placeholders
- Format: img tag with descriptive alt text showing exactly what the screenshot should capture
  - Example: `![Anchor naming dialog with 'Footage_Beauty' pre-filled](img/anchor-naming-dialog.png)`
- Screenshot folder: `docs/img/` — all doc assets live alongside the guide
- One placeholder per meaningful UI moment in each workflow section

### Claude's Discretion
- Exact section heading names and document structure
- Number of screenshot placeholders per workflow (judgment call per step)
- Whether to use a top-level keyboard shortcut reference table at the end

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DOCS-01 through DOCS-04 define the acceptance criteria; out-of-scope items listed (no installation section, no animated GIFs)
- `.planning/ROADMAP.md` — Phase 19 success criteria (5 items), including the PNG placeholder requirement

### Feature reference
- `README.md` — comprehensive technical reference for all plugin behavior; Quick Start should complement this, not duplicate it

No external specs — requirements fully captured in decisions above and referenced files.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md`: Complete feature reference covering all workflows — use as source of truth for behavior descriptions; Quick Start should be the "getting started" entry point that links back to README for depth
- No `docs/` folder exists — must be created with `docs/quick-start.md` and `docs/img/` subfolder

### Established Patterns
- No existing docs infrastructure — Claude's discretion on Markdown conventions
- README uses tables for keyboard shortcuts — the Quick Start may reference these or include a summary table

### Integration Points
- `docs/quick-start.md` is a standalone file; no build system, no site generator needed
- `docs/img/` holds PNG placeholder references that will be populated with real screenshots later

</code_context>

<specifics>
## Specific Ideas

- No specific reference examples given — standard technical Quick Start conventions apply
- The concept intro should be tight enough to read in under 10 seconds

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 19-quick-start-documentation*
*Context gathered: 2026-03-20*
