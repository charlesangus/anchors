# Phase 12: Nuke -t Validation Scripts - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Write `validation/validate_stub_alignment.py` and `validation/validate_cross_script_paste.py` — two scripts a developer runs under `nuke -t` against a local licensed Nuke install. The scripts confirm that StubNode/StubKnob assumptions in `tests/` match real Nuke API behavior, and that the BUG-01 and BUG-02 fixed code paths work correctly under the real runtime. Any divergences found are corrected in source, stubs, and/or tests.

Scripts never import `menu.py` and never reach Qt dialog code paths.

</domain>

<decisions>
## Implementation Decisions

### Output format
- One line per check, always printed: `PASS: <check name>` or `FAIL: <check> — expected X, got Y`
- On failure: print and continue — collect all failures, don't stop at first
- Final line: `Summary: N/M checks passed` followed by `sys.exit(1)` if any failed
- Exit code is CI-friendly (0 = all passed, 1 = any failed)

### Stub assumptions scope (validate_stub_alignment.py)
- Exhaustive: probe all StubNode and StubKnob methods against their real Nuke counterparts
- Also validate nuke module-level API return types and signatures: `allNodes()` returns a list, `toNode()` returns None when node not found, `createNode()` returns a real node object
- Print `nuke.NUKE_VERSION_MAJOR` for informational context; warn (but don't fail) if below 14
- Highest-risk probes to include (flagged in STATE.md): `nuke.root().name()` in headless, node `['knob_name']` access pattern (KeyError on miss), `tile_color` knob read/write, `StubKnob.getValue()` vs `.value()` equivalence

### Cross-script smoke test design (validate_cross_script_paste.py)
- Use real `.nk` file write + `nuke.nodePaste()` as the primary mechanism — most realistic
- BUG-01 assertion: after `setup_link_node()`, assert `link_node['tile_color'].value() == anchor_node['tile_color'].value()` (link receives the anchor's real color, not ANCHOR_DEFAULT_COLOR / purple)
- BUG-02 assertion: fake the FQNN stem mismatch by controlling `nuke.root().name()` so its stem differs from the anchor's FQNN stem; call the relevant paste path; assert the node stays an anchor (not converted to a link)
- Clean up all created nodes with `nuke.delete()` after each check to keep the session clean

### Correction policy
- If a stub method diverges from real Nuke: fix `tests/stubs.py` to match real behavior
- If that fix causes `pytest tests/` to go red: fix the production source files (`paste_hidden.py`, `link.py`, `anchor.py`) — the test going red means the stub was papering over a production bug
- Only fix test assertions as a last resort (when real behavior is confirmed correct but the test was testing the wrong thing)
- No CORRECTIONS.md — git commit message documents what was found and fixed

### Claude's Discretion
- Exact helper structure within each validation script (a `run_check()` helper or inline try/except pattern)
- Whether to use a shared `validation/` `__init__.py` or keep scripts standalone
- Exact set of nuke module-level API surfaces to probe beyond the ones named above
- Whether to add a `validation/README.md` with usage instructions

</decisions>

<specifics>
## Specific Ideas

- The key principle: if validation reveals that the production code behaves incorrectly under real Nuke (not just a stub inaccuracy), the production code is what gets fixed — not just the stubs
- `nuke.root().name()` in headless is explicitly flagged as medium-confidence (STATE.md) — this is priority check #1 in validate_stub_alignment.py
- BUG-02 headless simulation: set `nuke.root()` name so its stem is different from the anchor FQNN stem (e.g., script is `destScript.nk`, anchor FQNN is `sourceScript.AnchorName`)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/stubs.py`: StubNode, StubKnob, make_stub_nuke_module() — the authoritative list of stub assumptions to probe
- `tests/conftest.py`: shows which sys.modules keys are stubbed (PySide6, tabtabtab, nuke, nukescripts) — validation scripts must import without these stubs
- `constants.py`: ANCHOR_DEFAULT_COLOR (purple, 0x6f3399ff) — referenced in BUG-01 assertion
- `link.py`: `setup_link_node()`, `find_node_color()`, `get_link_class_for_source()` — functions exercised by BUG-01 path
- `paste_hidden.py`: cross-script branch uses `nuke.root().name().split('.')[0]` to get stem — BUG-02 path

### Established Patterns
- Validation scripts run standalone under `nuke -t validation/validate_*.py` — no pytest, no conftest
- All existing tests use `unittest.TestCase` with `patch()` for per-test overrides — validation scripts use real Nuke, no patching
- `nukescripts.cut_paste_file()` returns the clipboard temp file path — needed for .nk file write approach

### Integration Points
- `validation/` directory must be created (does not exist yet)
- Validation scripts explicitly excluded from ZIP release artifact (Phase 11 decision)
- `pytest tests/` must remain green after any corrections — this is the regression gate

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-nuke-t-validation-scripts*
*Context gathered: 2026-03-14*
