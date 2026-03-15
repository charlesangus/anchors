# Phase 11: CI/CD Pipeline - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `.github/workflows/release.yml` — a GitHub Actions workflow triggered by version tag pushes that runs offline tests, packages plugin source into a versioned ZIP, and publishes a GitHub Release. No Nuke runtime in CI (nuke -t is explicitly out of scope — requires commercial license).

</domain>

<decisions>
## Implementation Decisions

### ZIP artifact structure
- ZIP contains a `paste_hidden/` subdirectory at root — artist unzips into `~/.nuke/` and gets `~/.nuke/paste_hidden/`
- ZIP filename: `paste_hidden-{tag}.zip` (e.g. `paste_hidden-v1.2.0.zip`), derived from the git tag
- Explicit file manifest — include only `.py` source files in the project root:
  - `anchor.py`, `colors.py`, `constants.py`, `labels.py`, `link.py`, `menu.py`, `paste_hidden.py`, `prefs.py`, `tabtabtab.py`, `util.py`
- Excluded from ZIP: `tests/`, `validation/`, `.planning/`, `__pycache__/`, `pyproject.toml`, `LICENSE`, `README.md`, `__init__.py`
- Inside the ZIP the files sit under `paste_hidden/` (not at root)

### Tag pattern & workflow scope
- Trigger: `v*` tag pattern (any v-prefixed tag, including pre-release like `v1.2.0-rc1`)
- Workflow runs on tag push only — no separate CI job for non-tag pushes or PRs
- If tests fail: workflow fails, no release is created (standard gate behaviour)

### Release notes
- GitHub's built-in auto-generated release notes (lists commits since the last tag)
- Release published live immediately — no draft step
- Release title: the tag name (e.g. `v1.2.0`)

### Test runner & environment
- Test command: `pytest tests/`
- Python version: 3.11
- Runner OS: ubuntu-24.04 (user's preference; Rocky Linux not available on GitHub-hosted runners)
- No additional pip dependencies needed — tests use stdlib + project source only

### Claude's Discretion
- Exact workflow job/step names and YAML formatting
- Whether to `pip install pytest` or use `pip install -e .[dev]` (no setup.py/pyproject test extras exist yet — plain `pip install pytest` is fine)
- ZIP creation implementation (zip CLI vs Python zipfile module in the workflow)
- Exact permissions block in the workflow YAML

</decisions>

<specifics>
## Specific Ideas

- Artist installs by downloading the ZIP from the GitHub Release, unzipping into `~/.nuke/` — the `paste_hidden/` subdirectory structure must be correct for `import paste_hidden` to work
- User expressed preference for RHEL-like environment; ubuntu-24.04 is the CI stand-in (self-hosted Rocky Linux runner could be added later by updating the `runs-on` field)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml`: exists for ruff config only — no test extras or build config; workflow installs pytest directly
- `tests/conftest.py` + `tests/stubs.py`: centralised stub infrastructure from Phase 8; `pytest tests/` picks up conftest automatically

### Established Patterns
- `pytest tests/` is the canonical test command (Phase 8 CONTEXT.md)
- No `.github/` directory exists yet — workflow file is a new creation

### Integration Points
- New files: `.github/workflows/release.yml`
- No changes to existing source files required

</code_context>

<deferred>
## Deferred Ideas

- Self-hosted Rocky Linux runner — would require adding a runner and updating `runs-on`; not in scope for this phase
- Separate test-on-push CI job (not tag-triggered) — user chose tags-only for simplicity

</deferred>

---

*Phase: 11-ci-cd-pipeline*
*Context gathered: 2026-03-14*
