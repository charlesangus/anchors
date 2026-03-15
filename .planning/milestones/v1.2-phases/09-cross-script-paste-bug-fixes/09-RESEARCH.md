# Phase 9: Cross-Script Paste Bug Fixes - Research

**Researched:** 2026-03-12
**Domain:** Python plugin behavior — `paste_hidden.py` cross-script paste paths, tile_color propagation, offline pytest/unittest test patterns
**Confidence:** HIGH

---

## Summary

Phase 9 fixes two bugs in `paste_hidden.py`'s `paste_hidden()` function, both manifesting only in the cross-script paste code paths. The fixes are surgical — each bug is a 1-3 line change in an already-identified location. The bulk of the work is writing regression tests that run under the existing flat-discovery test infrastructure (130 tests, 0 errors, established in Phase 8).

**BUG-01** lives in Path B of `paste_hidden()` (lines 203-213): when a Link Dot (hidden-input Dot backed by an anchor) is pasted cross-script and a matching anchor is found in the destination script, `setup_link_node(destination_anchor, node)` correctly applies the anchor's color, but line 212 then immediately overwrites it with `ANCHOR_DEFAULT_COLOR` (the hardcoded purple `0x6f3399ff`). The fix is to remove or change that overwrite.

**BUG-02** lives in Path A/C of `paste_hidden()` (lines 147-180): when an anchor node is pasted cross-script, the code finds a same-named anchor in the destination and replaces the pasted anchor with a *link node*. An anchor pasted cross-script should remain an anchor — the pasted anchor placeholder should be left in place (same treatment as the "no matching anchor" case), not converted to a link.

Both bugs require regression tests written against the existing stub infrastructure (`tests/stubs.py`, `tests/conftest.py`, `tests/__init__.py`). The test files must remain compatible with flat-discovery pytest and `python3 -m unittest discover -s tests/ -t . -p "test_*.py"`.

**Primary recommendation:** Fix both bugs in `paste_hidden.py` with minimal targeted changes, add regression tests to `tests/test_cross_script_paste.py` (which already covers related cross-script behavior), and verify the full suite stays green.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-01 | Links receive their anchor's tile_color in all code paths (not default purple in any scenario) | Bug traced to line 212 of paste_hidden.py: `node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)` after `setup_link_node()` overwrites the correct color. Removing/changing this line fixes it. |
| BUG-02 | Anchor node pasted cross-script stays an anchor — not converted to a link node | Bug traced to paste_hidden.py lines 155-171: the code path for "is_anchor + cross-script + matching anchor found" creates a link and deletes the anchor placeholder. The fix is to not attempt this replacement (leave the placeholder as-is, same as "no matching anchor" case). |
</phase_requirements>

---

## Bug Analysis

### BUG-01: NoOp Link Gets Wrong Color on Cross-Script Paste

**File:** `paste_hidden.py`
**Function:** `paste_hidden()`
**Path:** Path B (HIDDEN_INPUT_CLASSES), cross-script Link Dot branch (lines 203-213)

**Trace:**

```python
# paste_hidden.py lines 203-213 (current code)
if is_cross_script or not input_node:
    if dot_type == 'link':
        display_name = _extract_display_name_from_fqnn(stored_fqnn)
        if display_name:
            destination_anchor = find_anchor_by_name(display_name)
            if destination_anchor:
                setup_link_node(destination_anchor, node)          # CORRECT: sets anchor's color
                node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)  # BUG: overwrites with purple
```

`setup_link_node()` in `link.py` calls `find_node_color(input_node)` which reads `input_node["tile_color"].value()` (with Preferences fallback) — this is the anchor's actual color. But line 212 immediately overwrites the result with `ANCHOR_DEFAULT_COLOR = 0x6f3399ff` (hardcoded purple), discarding the anchor's color.

**Fix:** Remove line 212 (`node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)`). After `setup_link_node()` runs, the link node already has the correct anchor color. The purple override serves no legitimate purpose here.

**Context note:** In `copy_hidden()` (lines 77-79), a similar override exists but for copy-time, setting Link Dots to purple as their "default" transport color. That copy-time override is by-design (see code comment: "Override tile_color to canonical purple — setup_link_node() may apply a custom anchor color via find_node_color(), which we do not want here."). The paste-time override at line 212 has no corresponding design rationale and produces the reported bug.

---

### BUG-02: Anchor Pasted Cross-Script Becomes a Link Node

**File:** `paste_hidden.py`
**Function:** `paste_hidden()`
**Path:** Path A/C (LINK_SOURCE_CLASSES or is_anchor), cross-script branch (lines 147-172)

**Trace:**

```python
# paste_hidden.py lines 147-172 (current code)
if node.Class() in LINK_SOURCE_CLASSES or is_anchor(node):
    if not input_node:   # cross-script: find_anchor_node() returned None
        if is_anchor(node) and node.Class() != 'Dot':
            display_name = _extract_display_name_from_fqnn(node[KNOB_NAME].getText())
            if display_name:
                destination_anchor = find_anchor_by_name(display_name)
                if destination_anchor:
                    # Creates a link and deletes the pasted anchor — BUG
                    link_node = nuke.createNode(get_link_class_for_source(destination_anchor))
                    setup_link_node(destination_anchor, link_node)
                    link_node.setXYpos(node.xpos(), node.ypos())
                    selected_nodes.remove(node)
                    selected_nodes.append(link_node)
                    nuke.delete(node)
                    continue
        continue
```

When an anchor is pasted cross-script and a same-named anchor exists in the destination, the code was designed to "reconnect" by replacing the pasted anchor with a link to the destination anchor. But the requirement is that **an anchor pasted cross-script stays an anchor**. This means the cross-script anchor path should always `continue` without any replacement, just like when no matching anchor is found.

**Fix:** Remove the inner `if display_name: ... destination_anchor` replacement block. The correct behavior is to `continue` unconditionally when `is_anchor(node) and node.Class() != 'Dot'` in the cross-script case — leaving the pasted anchor node in place as a new independent anchor in the destination script.

**Alternative considered:** Instead of leaving the placeholder, we could strip the KNOB_NAME stamp from the pasted anchor to make it a clean new anchor. This would be slightly cleaner (the node won't have a stale FQNN knob pointing to a different script), but it risks scope creep. The minimal fix (just `continue`) is safer for Phase 9; knob cleanup can be addressed in QUAL-01 if needed.

---

## Standard Stack

### Core (no new dependencies — all work is in existing files)

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python 3 (Nuke embedded) | 3.x | Plugin language | Runtime constraint — no choice |
| `unittest` stdlib | 3.x stdlib | Offline testing framework | Already used in test suite; no pytest install in Nuke env |
| `unittest.mock` | 3.x stdlib | Patching nuke/nukescripts in tests | Already used across all test files |
| `tests/stubs.py` | project | Shared StubNode/StubKnob/make_stub_nuke_module | Established in Phase 8 — must use, not re-implement |
| `tests/conftest.py` | project | Stub installation for pytest flat-discovery | Established in Phase 8 — must not modify unless adding to it |

### No New Packages

This phase requires zero new library installations. All code changes are in `paste_hidden.py` and regression tests added to `tests/test_cross_script_paste.py`.

---

## Architecture Patterns

### Recommended Project Structure (unchanged)

```
paste_hidden/
├── paste_hidden.py      # BUG-01 and BUG-02 fixes go here
├── link.py              # No changes expected
├── anchor.py            # No changes expected
├── constants.py         # No changes expected
└── tests/
    ├── conftest.py          # No changes (unless stub gaps found)
    ├── stubs.py             # No changes (unless stub gaps found)
    ├── __init__.py          # No changes
    └── test_cross_script_paste.py   # Regression tests added here
```

### Pattern 1: Minimal Targeted Fix

**What:** Change only the exact lines causing the bug. Do not refactor surrounding code.
**When to use:** Bug fixes with clear root-cause traces. Wider refactoring belongs in QUAL-01.
**Rationale:** Phase 9 must not introduce regressions; Phase 10 (QUAL-01) is the quality sweep.

### Pattern 2: Regression Tests Before Fix

**What:** Write the failing test first, verify it fails, apply the fix, verify it passes.
**When to use:** All bug fixes in this phase.
**Rationale:** Confirms the test actually exercises the bug path; prevents false-green tests.

### Pattern 3: Test Structure — unittest + patch, same as existing tests

**What:** Tests in `test_cross_script_paste.py` use `unittest.TestCase` with `patch()` context managers to mock `paste_hidden.nuke`, `paste_hidden.nukescripts`, and specific callables.
**When to use:** All new tests in this phase.
**Example (existing pattern from test_cross_script_paste.py):**

```python
class TestCrossScriptReconnect(unittest.TestCase):
    def test_some_behavior(self):
        with patch('paste_hidden.nuke') as mock_nuke, \
             patch('paste_hidden.nukescripts') as mock_nukescripts, \
             patch('paste_hidden.find_anchor_node', return_value=None), \
             patch('paste_hidden.find_anchor_by_name', return_value=destination_anchor), \
             patch('paste_hidden.setup_link_node') as mock_setup_link_node, \
             patch('paste_hidden.is_anchor', return_value=True):
            mock_nuke.nodePaste.return_value = None
            mock_nuke.selectedNodes.return_value = [pasted_node]
            from paste_hidden import paste_hidden
            paste_hidden()
            # assertions...
```

**Critical:** Tests must NOT import `paste_hidden` at module level — import inside test methods or setUp to allow patching to work correctly with the module cache.

### Anti-Patterns to Avoid

- **Touching copy_hidden() for BUG-01:** The purple override in `copy_hidden()` at line 79 is intentional (copy-time canonical color). Only the paste-time override at line 212 is the bug.
- **Rebuilding stubs:** Do not create local StubNode/StubKnob in new test classes — use `import nuke as _nuke` after stubs are installed, or use `from tests.stubs import StubNode, StubKnob` directly.
- **Global module imports in test files:** All `from paste_hidden import ...` calls must be inside test methods (not at file top level) to avoid module-cache staleness across patch boundaries.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stub nuke module | New per-test stub dict | `tests/stubs.make_stub_nuke_module()` | Established superset; Phase 8 centralized this specifically |
| Stub StubNode/StubKnob | Per-test anonymous objects | `StubNode`, `StubKnob` from `tests/stubs` | Already covers all five test files' needs |
| Cross-script detection | New helper function | Existing FQNN stem comparison in `paste_hidden()` | Logic already correct; bugs are in what happens AFTER detection |
| find_anchor_by_name mock | Manual scan loop | `patch('paste_hidden.find_anchor_by_name', return_value=...)` | Cleanest isolation; already used in existing tests |

---

## Common Pitfalls

### Pitfall 1: Patching `is_anchor` Globally Across All Nodes

**What goes wrong:** `patch('paste_hidden.is_anchor', return_value=True)` makes `is_anchor` return True for ALL nodes in the test, including the newly created link node. This can cause unexpected behavior if the test checks properties of the new link node.
**Why it happens:** `unittest.mock.patch` replaces the function reference; `return_value=True` applies unconditionally.
**How to avoid:** Use `side_effect` instead of `return_value` when multiple nodes need different `is_anchor` results. Or structure the test so only the anchor node goes through `is_anchor` before the deletion.
**Warning signs:** Test passes but asserts on wrong node behavior.

### Pitfall 2: tile_color Assert After setup_link_node (BUG-01 test)

**What goes wrong:** After the BUG-01 fix, `setup_link_node` is patched with `patch(...) as mock_setup_link_node`. The test wants to assert that `node['tile_color']` is NOT `ANCHOR_DEFAULT_COLOR`. But if `setup_link_node` is mocked, it won't actually set `tile_color` either.
**How to avoid:** Either: (a) use a real StubNode with a real knob and DON'T patch setup_link_node (let it run), or (b) assert that `node['tile_color'].setValue` was NOT called with `ANCHOR_DEFAULT_COLOR` after `setup_link_node` returns.
**Recommended approach:** Let `setup_link_node` run (don't mock it) for the BUG-01 regression test. Mock only `find_anchor_by_name` and `find_node_color` so color is controllable.

### Pitfall 3: nuke.root().name() Returns Wrong Stem

**What goes wrong:** Cross-script detection (`is_cross_script`) depends on comparing `stored_fqnn.split('.')[0]` against `nuke.root().name().split('.')[0]`. If the stub `root.name()` returns `'destScript.nk'` (as configured in `make_stub_nuke_module()`), stored FQNNs must use a DIFFERENT stem (e.g., `'sourceScript.Anchor_Foo'`) to trigger the cross-script path.
**Why it happens:** If both stems match, `is_cross_script` is False and the test exercises the wrong code path.
**How to avoid:** Always use `'sourceScript.Anchor_Foo'` (or similar non-`destScript` stem) as stored_fqnn in cross-script tests. The stub `nuke.root().name()` returns `'destScript.nk'`, so `destScript != sourceScript` triggers cross-script correctly.

### Pitfall 4: DOT_TYPE_KNOB_NAME Must Be in Node Knobs for BUG-01 Path

**What goes wrong:** In `paste_hidden()` Path B, `dot_type` is read from `node[DOT_TYPE_KNOB_NAME]` if present, else inferred from FQNN. If the test node doesn't have `DOT_TYPE_KNOB_NAME` in its knobs dict, the fallback inference runs. For a Link Dot with an anchor-prefix FQNN, inference produces `'link'` — which is correct. But tests are cleaner when the knob is explicit.
**How to avoid:** Include `DOT_TYPE_KNOB_NAME: StubKnob('link')` in the test node's `knobs_dict`.

### Pitfall 5: paste_hidden Module Cache After Fix

**What goes wrong:** Importing `paste_hidden` in one test, then patching its internals in a later test, may use the cached module with the old code path.
**How to avoid:** Import `paste_hidden.paste_hidden` function inside the `with patch(...)` block, as already done in existing `TestCrossScriptReconnect` tests.

---

## Code Examples

### Existing Cross-Script Test Pattern (Source: tests/test_cross_script_paste.py)

```python
# This pattern is already established — new tests MUST follow it
def test_cross_script_reconnect_with_matching_anchor_creates_link_and_deletes_placeholder(self):
    import nuke as _nuke
    from constants import KNOB_NAME

    pasted_anchor_node = self._make_noop_anchor_node(
        anchor_name='MyFootage',
        stored_fqnn='sourceScript.Anchor_MyFootage',  # different stem = cross-script
        xpos=100, ypos=200,
    )
    destination_anchor = _nuke.StubNode(name='Anchor_MyFootage', node_class='NoOp')

    with patch('paste_hidden.nuke') as mock_nuke, \
         patch('paste_hidden.nukescripts') as mock_nukescripts, \
         patch('paste_hidden.find_anchor_node', return_value=None), \
         patch('paste_hidden.find_anchor_by_name', return_value=destination_anchor), \
         patch('paste_hidden.setup_link_node') as mock_setup_link_node, \
         patch('paste_hidden.is_anchor', return_value=True):

        mock_nuke.nodePaste.return_value = None
        mock_nuke.selectedNodes.return_value = [pasted_anchor_node]
        mock_nuke.createNode.return_value = created_link_node

        from paste_hidden import paste_hidden
        paste_hidden()
        # assertions...
```

### BUG-02 Regression Test Skeleton (what the new test must verify)

```python
def test_anchor_pasted_cross_script_stays_anchor_not_converted_to_link(self):
    """BUG-02 regression: anchor pasted cross-script must NOT be replaced by a link node,
    even when a same-named anchor exists in the destination script."""
    # Setup: a NoOp anchor node with a cross-script FQNN
    # Arrange: find_anchor_node returns None (cross-script), find_anchor_by_name returns a match
    # Act: call paste_hidden()
    # Assert: nuke.createNode NOT called, nuke.delete NOT called
    #         (anchor placeholder left in place)
```

### BUG-01 Regression Test Skeleton (what the new test must verify)

```python
def test_link_dot_pasted_cross_script_receives_anchor_tile_color_not_purple(self):
    """BUG-01 regression: a Link Dot pasted cross-script must display the anchor's
    tile_color, not ANCHOR_DEFAULT_COLOR (purple)."""
    # Setup: a hidden-input Dot node stamped as dot_type='link', cross-script FQNN
    # Arrange: find_anchor_by_name returns an anchor with a specific non-purple tile_color
    # Act: call paste_hidden() — letting setup_link_node run (don't mock it)
    # Assert: node['tile_color'].getValue() == anchor_color (NOT ANCHOR_DEFAULT_COLOR)
```

### StubNode for Hidden-Input Dot (Path B test node)

```python
def _make_link_dot_node(self, stored_fqnn):
    import nuke as _nuke
    from constants import KNOB_NAME, DOT_TYPE_KNOB_NAME
    return _nuke.StubNode(
        name='Dot1',
        node_class='Dot',
        knobs_dict={
            KNOB_NAME: _nuke.StubKnob(stored_fqnn),
            DOT_TYPE_KNOB_NAME: _nuke.StubKnob('link'),
            'selected': _nuke.StubKnob(False),
            'hide_input': _nuke.StubKnob(True),
            'tile_color': _nuke.StubKnob(0),
            'label': _nuke.StubKnob(''),
            'note_font_size': _nuke.StubKnob(0),
        },
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-file StubNode/StubKnob definitions | Centralized `tests/stubs.py` superset | Phase 8 (2026-03-13) | Tests now use shared stubs; no per-file conflicts |
| Flat-discovery Qt ordering conflicts (5 errors) | `conftest.py` + `tests/__init__.py` with idempotency guard | Phase 8 (2026-03-13) | 130 tests, 0 errors; safe to add regression tests |
| FQNN stem comparison as cross-script gate | Same — this was already the correct design | Phase 5 | Prevents same-stem false positives |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib) + `pytest` (optional, same tests) |
| Config file | `tests/conftest.py` (pytest) / `tests/__init__.py` (unittest) |
| Quick run command | `python3 -m unittest tests.test_cross_script_paste -v` |
| Full suite command | `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-01 | Link Dot pasted cross-script shows anchor tile_color, not purple | unit/regression | `python3 -m unittest tests.test_cross_script_paste.TestBugRegressions.test_bug01_link_dot_cross_script_color -v` | ❌ Wave 0 |
| BUG-02 | Anchor pasted cross-script stays anchor (not converted to link) | unit/regression | `python3 -m unittest tests.test_cross_script_paste.TestBugRegressions.test_bug02_anchor_stays_anchor_cross_script -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m unittest tests.test_cross_script_paste -v`
- **Per wave merge:** `python3 -m unittest discover -s tests/ -t . -p "test_*.py"`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cross_script_paste.py` — add `TestBugRegressions` class with BUG-01 and BUG-02 regression tests (file exists; add new class to it)
- [ ] No new framework installs needed — `unittest` is stdlib

---

## Open Questions

1. **Should the pasted anchor placeholder be cleaned up (KNOB_NAME knob stripped) after BUG-02 fix?**
   - What we know: The pasted anchor has `KNOB_NAME` set to a cross-script FQNN. `is_link()` checks for `KNOB_NAME` presence, so the pasted anchor would incorrectly be classified as a link by `is_link()`.
   - What's unclear: Whether this causes downstream issues (e.g., anchor color propagation skipping it, or reconnect logic treating it as a link).
   - Recommendation: Investigate `is_link()` usage. If the pasted anchor would be misclassified, add a minimal cleanup (strip KNOB_NAME) as part of the BUG-02 fix. This is Phase 9 scope if it's needed for correct behavior; defer to QUAL-01 only if it's purely cosmetic.

2. **BUG-01: Does the copy-time purple override in copy_hidden() (line 79) also need adjustment?**
   - What we know: `copy_hidden()` deliberately sets Link Dots to `ANCHOR_DEFAULT_COLOR` at copy time (purple as transport color). This is documented with a comment as intentional.
   - What's unclear: Whether the intent was for the pasted copy to also show purple (and thus line 212 in paste_hidden was added intentionally but incorrectly), or whether paste should restore the anchor's real color.
   - Recommendation: BUG-01 description says "Links receive their anchor's tile_color in all code paths." The paste-time fix (removing line 212) is unambiguously correct. The copy-time behavior is separate and intentional.

---

## Sources

### Primary (HIGH confidence)

- Direct code read of `/workspace/paste_hidden.py` — full function trace for both bug paths
- Direct code read of `/workspace/link.py` — `setup_link_node()`, `find_node_color()`, `find_anchor_node()` confirmed
- Direct code read of `/workspace/tests/stubs.py` — StubNode/StubKnob interface confirmed; `nuke.root().name()` returns `'destScript.nk'`
- Direct code read of `/workspace/tests/conftest.py` and `tests/__init__.py` — stub installation pattern confirmed
- Direct code read of `/workspace/tests/test_cross_script_paste.py` — existing test patterns confirmed
- `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` — 130 tests, 0 errors (baseline confirmed 2026-03-13)

### Secondary (MEDIUM confidence)

- REQUIREMENTS.md BUG-01/BUG-02 definitions — aligned with code traces above
- STATE.md accumulated context — confirmed Phase 8 complete, stubs centralized

### Tertiary (LOW confidence)

- None — all findings are from direct code inspection of the live codebase.

---

## Metadata

**Confidence breakdown:**
- Bug root causes: HIGH — traced line-by-line in source, no ambiguity
- Fix approach: HIGH — minimal targeted changes with clear before/after
- Test patterns: HIGH — existing tests in test_cross_script_paste.py show exact pattern to follow
- Open question on pasted anchor cleanup: MEDIUM — needs brief investigation during implementation

**Research date:** 2026-03-12
**Valid until:** Indefinite (code is stable; bugs are in specific lines that won't change without a commit)
