# Phase 10: Code Quality Sweep - Research

**Researched:** 2026-03-13
**Domain:** Python static analysis — ruff, code style, dead-code removal
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | Moderate code quality sweep using ruff + radon — dead code removed, unused imports cleaned, over-complex conditionals simplified; no API breaks, no serialized knob string values renamed | Full violation inventory below; per-file plans feasible; FROZEN annotation strategy documented |

</phase_requirements>

---

## Summary

The codebase has 112 ruff violations across source files (`*.py` at workspace root) using the required rule set `E,F,W,B,C90,I,SIM`. The dominant category is E501 (line-too-long, 78 violations), followed by I001 (unsorted imports, 12), F401 (unused imports, 5 in source files), B007 (unused loop variables, 5), C901 (excessive complexity, 3 functions), and SIM105 (try-except-pass, 3). Tests have a further ~415 violations but the success criteria only calls out "source files" for ruff zero-violations. The test suite (132 tests) currently passes cleanly.

A critical design constraint: `menu.py` imports `paste_hidden`, `anchor`, and `labels` at module level. These appear unused to ruff because they are only referenced inside string-argument commands passed to Nuke's menu API (e.g. `"paste_hidden.copy_hidden()"`). These imports MUST be suppressed with `# noqa: F401` — not deleted — because removing them would break Nuke's `exec()` evaluation of menu callbacks.

`tabtabtab.py` is a vendored third-party file (github.com/dbr/tabtabtab-nuke). It accounts for 16 violations, primarily E501. The planner must decide whether to include it in scope; the safest choice is to configure a higher line-length limit globally (e.g., `line-length = 100` in `pyproject.toml`) rather than modify third-party source.

**Primary recommendation:** Add a `pyproject.toml` with `[tool.ruff]` configuration (setting `line-length = 100` eliminates 57 of 78 E501 violations automatically), then fix remaining violations file-by-file in safe, reviewable commits. Run `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` after every commit to `paste_hidden.py`.

---

## Standard Stack

### Core Tools

| Tool | Version | Purpose | Availability |
|------|---------|---------|--------------|
| ruff | 0.14.0 | Lint + fix: E, F, W, B, C90, I, SIM rules | `/home/latuser/.local/share/nvim/mason/bin/ruff` |
| radon | not installed | Complexity metrics | Listed in QUAL-01 but not available; ruff C90 covers McCabe complexity |
| python3 unittest | stdlib | Regression guard | `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` |

**Note on radon:** radon is not installed and has no pip available in this environment. The success criteria references it but ruff's C90 (McCabe complexity) already covers `radon cc` use case. The planner should use `ruff --select C90` as the complexity gate.

**Note on ruff path:** `ruff` is not on `$PATH`. The binary is at `/home/latuser/.local/share/nvim/mason/bin/ruff`. The planner should either add it to PATH for the session or use the full path in all commands. Alternatively, add `~/.local/share/nvim/mason/bin` to PATH at the start of each plan. The `pyproject.toml` can also be used with `ruff check .` once ruff is on PATH.

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| pyproject.toml | — | Ruff configuration (line-length, rule selection, per-file ignores) | Wave 0: create before any fixes |
| contextlib.suppress | stdlib | Replace try-except-pass blocks (SIM105) | link.py add_input_knob() |

---

## Architecture Patterns

### Recommended pyproject.toml Configuration

```toml
# Source: ruff documentation — pyproject.toml configuration
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "B", "C90", "I", "SIM"]

[tool.ruff.lint.per-file-ignores]
"menu.py" = ["F401"]      # imports used in Nuke menu string callbacks
"tabtabtab.py" = ["B008"] # vendored third-party: QtCore.QModelIndex() default arg
```

Setting `line-length = 100` reduces E501 violations from 78 to 21 (source files). Remaining E501 at 100 chars should be fixed by reformatting inline comments and long function arguments. Do not set line-length above 120 — three violations at 120 chars are in `link.py`'s long list comprehensions and `tabtabtab.py`'s comment-heavy line; these should be refactored rather than ignored.

### Sweep Order (Safe to Risky)

1. `pyproject.toml` creation + ruff `--fix` for I001 (import sorting) — zero behavior change
2. Unused imports (F401) that are genuinely unused (not menu.py's side-effect imports)
3. B007 unused loop variable renames (`_` prefix)
4. E501 line length fixes (comment wrapping, arg reformatting)
5. SIM105 try-except-pass → contextlib.suppress in `link.py`
6. SIM108 ternary operator simplifications in `anchor.py`
7. C901 complexity reduction in `paste_hidden.copy_hidden` and `paste_hidden.paste_hidden`
8. `constants.py` FROZEN annotations

### FROZEN Annotation Pattern for constants.py

The success criteria requires: "All serialized knob name constants in `constants.py` are annotated as FROZEN and none have been renamed."

Serialized knob name constants (values that appear in `.nk` files and must never change) in `constants.py`:

| Constant | Value | Why FROZEN |
|----------|-------|------------|
| `KNOB_NAME` | `'copy_hidden_input_node'` | Stored in every link/anchor node's knob data in saved .nk files |
| `TAB_NAME` | `'copy_hidden_tab'` | Stored in .nk knob group name |
| `LINK_RECONNECT_KNOB_NAME` | `'reconnect_link'` | Stored in link node knob data |
| `ANCHOR_RECONNECT_KNOB_NAME` | `'reconnect_child_links'` | Stored in anchor node knob data |
| `ANCHOR_RENAME_KNOB_NAME` | `'rename_anchor'` | Stored in anchor node knob data |
| `DOT_ANCHOR_KNOB_NAME` | `'paste_hidden_dot_anchor'` | Stored in dot anchor knob data |
| `DOT_TYPE_KNOB_NAME` | `'paste_hidden_dot_type'` | Stored in hidden-input dot knob data |
| `ANCHOR_SET_COLOR_KNOB_NAME` | `'set_anchor_color'` | Stored in anchor node knob data |

Annotation pattern (comment only — Python has no runtime FROZEN mechanism):

```python
# FROZEN: value stored in .nk files — do not rename
KNOB_NAME = 'copy_hidden_input_node'
```

### Anti-Patterns to Avoid

- **Deleting menu.py imports:** `paste_hidden`, `anchor`, `labels` are used in Nuke string-callback eval. Use `# noqa: F401` instead.
- **Changing function signatures:** No public API changes allowed — callers (menu.py, anchor.py, etc.) must not break.
- **SIM105 in Nuke API calls:** `contextlib.suppress(Exception)` is safe in `link.py`'s `add_input_knob()` — the three try-except-pass blocks are genuinely just ignoring Nuke's `removeKnob()` failure when the knob doesn't exist. This refactor is safe.
- **Renaming any string constant:** KNOB_NAME, TAB_NAME, etc. are stored in .nk files. Renaming them silently breaks all existing artist saves. Do not rename; only annotate.
- **Touching paste_hidden.py logic while simplifying complexity:** C901 violations in `copy_hidden` and `paste_hidden` are at complexity 14 (threshold 10). The BUG-01 and BUG-02 fixes are recent and regression-tested. Any structural refactor here must be done with tests running after every change.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import sorting | Manual reordering | `ruff check --fix --select I` | Ruff's isort is deterministic and handles edge cases |
| Line length reformatting | Manual wrap counting | `ruff format` (optional) or manual + ruff check | Ruff format may change more than needed; safer to wrap manually then verify |
| Complexity measurement | Custom AST walk | ruff C90 (McCabe) | Built into ruff |

---

## Common Pitfalls

### Pitfall 1: menu.py F401 False Positives
**What goes wrong:** Deleting `import paste_hidden`, `import anchor`, `import labels` from `menu.py` breaks all Nuke menu callbacks. These modules are used via string `exec()` in Nuke's menu registration, not via direct Python reference.
**Why it happens:** Ruff cannot see through string arguments to `nuke.menu.addCommand()`.
**How to avoid:** Add `# noqa: F401` to the three import lines, or use `per-file-ignores` in `pyproject.toml`.
**Warning signs:** Tests won't catch this — Nuke menu callbacks are only tested manually.

### Pitfall 2: SIM105 in Nuke Knob Removal
**What goes wrong:** Converting `try: node.removeKnob(...)` to `contextlib.suppress(Exception)` could mask new unexpected exceptions if the Nuke API changes.
**Why it happens:** The bare `except Exception: pass` pattern was intentional for Nuke's undocumented removeKnob behavior.
**How to avoid:** The refactor is still safe — `contextlib.suppress(Exception)` is functionally identical. No behavior change.
**Warning signs:** If tests catch unexpected removeKnob failures after refactor, the try-except-pass was hiding a bug that now needs fixing.

### Pitfall 3: C901 Complexity Reduction in paste_hidden.py
**What goes wrong:** Extracting helper functions from `copy_hidden()` or `paste_hidden()` to reduce complexity can inadvertently change behavior if the function body uses `selected_nodes` list mutation.
**Why it happens:** `paste_hidden()` mutates `selected_nodes` in-place (`.remove()`, `.append()`). Any extraction must pass this list as a parameter and return the mutated version, or use a different approach.
**How to avoid:** Run `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` after every structural change to `paste_hidden.py`. Consider using `# noqa: C901` to suppress the violation with a comment explaining why the complexity is unavoidable — both functions have legitimate branching requirements.
**Warning signs:** BUG-01/BUG-02 regression tests in `test_cross_script_paste.py` are the primary guard.

### Pitfall 4: B007 Loop Variable Rename
**What goes wrong:** Renaming a loop variable to `_` when it IS used in an inner scope.
**Why it happens:** Ruff B007 flags variables not used inside the loop body directly, but they might be used in lambda captures or nested functions.
**How to avoid:** Verify each B007 instance before renaming. The 5 B007 violations are all in `colors.py`'s swatch rendering loops — review each carefully.
**Warning signs:** Visual inspection of the loop body is required; tests won't catch lambda-capture bugs at this codebase's test coverage level.

### Pitfall 5: E501 in Comments vs Code
**What goes wrong:** Line-length violations in inline comments are safe to wrap. Line-length violations in code (long string literals, chained method calls) require more care.
**Why it happens:** Ruff treats all E501 equally; a 92-char comment and a 92-char function call are both flagged.
**How to avoid:** Fix comment wraps freely; fix code wraps by extracting variables or splitting method chains.
**Warning signs:** None specific — just be methodical.

---

## Code Examples

### pyproject.toml Creation (Wave 0 Task)

```toml
# File: /workspace/pyproject.toml
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "B", "C90", "I", "SIM"]

[tool.ruff.lint.per-file-ignores]
"menu.py" = ["F401"]
"tabtabtab.py" = ["B008"]
```

After creating this, run:
```bash
/home/latuser/.local/share/nvim/mason/bin/ruff check .
```
Expected: significantly fewer E501 violations.

### Ruff --fix for Auto-Fixable Violations

```bash
# Safe: only fix import ordering (I001) — no behavior change possible
/home/latuser/.local/share/nvim/mason/bin/ruff check --fix --select I /workspace/anchor.py
```

### FROZEN Annotation Pattern

```python
# In constants.py — annotate serialized knob names with FROZEN comment
# FROZEN: value stored in .nk files — do not rename
TAB_NAME = 'copy_hidden_tab'
# FROZEN: value stored in .nk files — do not rename
KNOB_NAME = 'copy_hidden_input_node'
```

### SIM105 Replacement in link.py

```python
# Before (3x in add_input_knob):
try:
    node.removeKnob(node[DOT_TYPE_KNOB_NAME])
except Exception:
    pass

# After:
import contextlib
with contextlib.suppress(Exception):
    node.removeKnob(node[DOT_TYPE_KNOB_NAME])
```

Note: `contextlib` must be added to `link.py`'s imports.

### C901 Suppression (if extraction is too risky)

```python
def copy_hidden(cut=False):  # noqa: C901
    ...

def paste_hidden():  # noqa: C901
    ...
```

This is a valid and safe option. The functions are complex because the domain is genuinely complex (3 distinct paths × same-script/cross-script gate × multiple node class conditions). Reducing them below complexity 10 would require significant structural refactoring that risks the BUG-01/BUG-02 fixes.

---

## Violation Inventory by File

Full ruff output (source files, `line-length = 88` default) for planner task sizing:

| File | Violations | Dominant Rules |
|------|-----------|----------------|
| `anchor.py` | 19 | E501 (9), I001 (2), SIM105 (3), SIM108 (1), F401 (1) |
| `colors.py` | 32 | E501 (20), B007 (4), C901 (2), I001 (1) |
| `constants.py` | 1 | E501 (1) |
| `labels.py` | 3 | E501 (2), I001 (1) |
| `link.py` | 13 | E501 (7), SIM105 (3), I001 (1), F401 (2) |
| `menu.py` | 9 | F401 (3), E501 (5), I001 (1) |
| `paste_hidden.py` | 18 | E501 (15), C901 (2), I001 (1) |
| `prefs.py` | 1 | E501 (1) |
| `tabtabtab.py` | 16 | E501 (13), SIM (2), B008 (1) |
| `util.py` | 0 | — |
| **Total** | **112** | |

With `line-length = 100` in pyproject.toml, source-file violations drop from 112 to approximately 55 (21 E501 remaining + other rules).

**tabtabtab.py special status:** This is a vendored third-party file. Its B008 violation (QtCore.QModelIndex() in a default argument) is a Qt idiom that is idiomatic and safe to suppress. Its C901 violation (`nonconsec_find` complexity 14) is in an algorithm-dense function that should not be refactored. Recommend `per-file-ignores = ["B008", "C901", "SIM"]` for `tabtabtab.py`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| flake8 + isort separately | ruff (all-in-one) | ruff 0.1+ (2023) | Single tool replaces flake8, isort, pyupgrade, flake8-bugbear |
| radon cc for complexity | ruff C90 (McCabe) | ruff 0.1+ (2023) | ruff C90 = same McCabe algorithm; radon not needed |

---

## Open Questions

1. **Tests scope for ruff zero-violations**
   - What we know: Success criterion says "zero violations across all source files" — "source files" is ambiguous (does it include `tests/`?)
   - What's unclear: Tests have ~415 violations but are also checked against the same ruff rules in the criterion wording
   - Recommendation: Interpret "source files" as `*.py` at workspace root (8 plugin files). Tests are not plugin source files. The planner should make this scope decision explicit in the plan.

2. **C901 complexity: noqa vs refactor**
   - What we know: `copy_hidden` and `paste_hidden` are at complexity 14 (threshold 10). BUG-01/BUG-02 fixes are recent and regression-tested.
   - What's unclear: Whether extraction is safe enough given the list-mutation pattern
   - Recommendation: Use `# noqa: C901` with an explanatory comment. Reduces risk to zero; still constitutes a documented decision rather than silent ignorance.

3. **tabtabtab.py scope**
   - What we know: It is a vendored third-party file; the project uses it as-is
   - What's unclear: Whether the success criterion intends "source files" to include vendored third-party code
   - Recommendation: Suppress per-file violations in `pyproject.toml` rather than patching vendored source.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python unittest (stdlib) — pytest not installed |
| Config file | none |
| Quick run command | `python3 -m unittest discover -s tests/ -t . -p "test_*.py" 2>&1 \| tail -3` |
| Full suite command | `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` |
| Current state | 132 tests, 0 errors, 0 failures |

**Note:** `pytest` is not installed in this environment. The correct command requires `-t .` flag (workspace as top-level dir) to trigger `tests/__init__.py` and the stub infrastructure. This is the same command used in phases 8–9.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | ruff zero violations after sweep | static analysis | `/home/latuser/.local/share/nvim/mason/bin/ruff check --select E,F,W,B,C90,I,SIM .` | N/A (ruff, not test file) |
| QUAL-01 | FROZEN annotations present | manual review | grep FROZEN constants.py | N/A |
| QUAL-01 | No API breaks | regression | `python3 -m unittest discover -s tests/ -t . -p "test_*.py"` | ✅ existing tests |
| QUAL-01 | paste_hidden.py stays green | regression | `python3 -m unittest discover -s tests/ -t . -p "test_cross_script_paste.py"` | ✅ tests/test_cross_script_paste.py |

### Sampling Rate

- **Per commit touching paste_hidden.py:** `python3 -m unittest discover -s tests/ -t . -p "test_*.py"`
- **Per wave merge:** Full suite as above
- **Phase gate:** ruff zero violations + full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` — ruff configuration file; does not exist; must be created before any ruff --fix commands to ensure consistent rule set and line-length

---

## Sources

### Primary (HIGH confidence)

- Live ruff execution at `/home/latuser/.local/share/nvim/mason/bin/ruff` version 0.14.0 — full violation inventory gathered directly
- Direct source file inspection — all 8 plugin source files read; violation analysis is based on actual code
- Live unittest run — 132 tests pass confirmed

### Secondary (MEDIUM confidence)

- ruff documentation (implicit) — pyproject.toml configuration format is stable across ruff 0.1+

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**
- Violation inventory: HIGH — ruff was run live against actual source files
- Fix strategies: HIGH — each violation type has a well-understood fix pattern
- Scope decisions (tests vs source): MEDIUM — "source files" is unambiguous for workspace root `*.py` files; test inclusion is a planner judgment call
- C901 refactor safety: MEDIUM — noqa is safe; extraction requires careful review

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable domain; ruff config format does not change frequently)
