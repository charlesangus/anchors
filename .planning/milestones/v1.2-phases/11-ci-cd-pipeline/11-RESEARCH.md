# Phase 11: CI/CD Pipeline - Research

**Researched:** 2026-03-14
**Domain:** GitHub Actions — tag-triggered release workflow with Python pytest gate and ZIP artifact
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- ZIP contains a `paste_hidden/` subdirectory at root — artist unzips into `~/.nuke/` and gets `~/.nuke/paste_hidden/`
- ZIP filename: `paste_hidden-{tag}.zip` (e.g. `paste_hidden-v1.2.0.zip`), derived from the git tag
- Explicit file manifest — include only `.py` source files: `anchor.py`, `colors.py`, `constants.py`, `labels.py`, `link.py`, `menu.py`, `paste_hidden.py`, `prefs.py`, `tabtabtab.py`, `util.py`
- Excluded from ZIP: `tests/`, `validation/`, `.planning/`, `__pycache__/`, `pyproject.toml`, `LICENSE`, `README.md`, `__init__.py`
- Inside the ZIP the files sit under `paste_hidden/` (not at root)
- Trigger: `v*` tag pattern (any v-prefixed tag, including pre-release like `v1.2.0-rc1`)
- Workflow runs on tag push only — no separate CI job for non-tag pushes or PRs
- If tests fail: workflow fails, no release is created
- GitHub's built-in auto-generated release notes (lists commits since the last tag)
- Release published live immediately — no draft step
- Release title: the tag name (e.g. `v1.2.0`)
- Test command: `pytest tests/`
- Python version: 3.11
- Runner OS: ubuntu-24.04
- No additional pip dependencies needed — plain `pip install pytest` is fine

### Claude's Discretion
- Exact workflow job/step names and YAML formatting
- Whether to `pip install pytest` or use `pip install -e .[dev]` (plain `pip install pytest` is fine)
- ZIP creation implementation (zip CLI vs Python zipfile module in the workflow)
- Exact permissions block in the workflow YAML

### Deferred Ideas (OUT OF SCOPE)
- Self-hosted Rocky Linux runner — would require adding a runner and updating `runs-on`
- Separate test-on-push CI job (not tag-triggered)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CI-01 | Tag push to GitHub triggers a workflow that runs offline tests, packages plugin source files into a versioned ZIP, and creates a GitHub Release | `on: push: tags: ['v*']` trigger; pytest step as gate; `gh release create` or `softprops/action-gh-release` with file attachment |
| CI-02 | ZIP release artifact uses an explicit file manifest — excludes `tests/`, `validation/`, `.planning/`, `__pycache__` | Explicit file list in ZIP construction step (zip CLI or Python); no glob that captures dev dirs |
</phase_requirements>

---

## Summary

This phase creates a single GitHub Actions workflow file (`.github/workflows/release.yml`) with no changes to existing source files. The workflow has one job: check out the repo, install pytest, run `pytest tests/`, build the ZIP from an explicit file manifest, and publish a GitHub Release with the ZIP attached.

The two main tool choices are: (1) using the `zip` CLI already available on ubuntu-24.04 runners, or (2) building the ZIP with Python's `zipfile` module in a run step. Both work; the `zip` CLI approach is more readable for a simple flat manifest. The release publishing is handled by either `softprops/action-gh-release@v2` (recommended — clean YAML, `generate_release_notes: true` support) or the `gh` CLI (also available on all GitHub-hosted runners, no third-party action required). Either approach produces identical output.

The most important constraint is the internal ZIP structure: files must live at `paste_hidden/` inside the archive, not at the archive root. This requires staging files into a temporary directory named `paste_hidden/` before zipping, or using `zip` with path manipulation.

**Primary recommendation:** Single-job workflow using `softprops/action-gh-release@v2` with `generate_release_notes: true` and `files:` pointing at the pre-built ZIP. ZIP built with the `zip` CLI by staging files into a `paste_hidden/` subdirectory and running `zip -r paste_hidden-${GITHUB_REF_NAME}.zip paste_hidden/`.

---

## Standard Stack

### Core
| Library / Action | Version | Purpose | Why Standard |
|-----------------|---------|---------|--------------|
| `actions/checkout` | v4 | Checks out the repo at the tag commit | Official GitHub action, required for any workflow that reads source |
| `actions/setup-python` | v5 | Installs Python 3.11 on the runner | Official GitHub action; ubuntu-24.04 ships Python 3.12 by default — explicit pin to 3.11 prevents drift |
| `softprops/action-gh-release` | v2 (latest: v2.5.0 as of 2025-12) | Creates the GitHub Release and attaches assets | Community standard; supports `generate_release_notes: true`, `files:` glob, correct permissions; actively maintained |
| `zip` CLI | 3.0 (pre-installed on ubuntu-24.04) | Builds the release ZIP | Pre-installed on all ubuntu runners; no install step needed |
| `pytest` | latest (pip install) | Runs offline tests | Project standard; no extras needed |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `gh` CLI | pre-installed | Alternative release publisher | When avoiding third-party actions is a priority; identical capability to softprops |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `softprops/action-gh-release@v2` | `gh release create` in a `run:` step | `gh` requires no third-party action but produces slightly more verbose YAML; both are valid |
| `zip` CLI | Python `zipfile` in a `run: python -c` block | Python approach is pure stdlib but more verbose; `zip` CLI is already present and simpler |
| `actions/setup-python@v5` | Skip setup (use runner default) | Runner default is Python 3.12; explicit setup prevents version drift |

**Installation (workflow installs, not local):**
```bash
pip install pytest
```

---

## Architecture Patterns

### Recommended Project Structure (files to create)
```
.github/
└── workflows/
    └── release.yml    # Single workflow file — entire phase is this one file
```

### Pattern 1: Single-Job Sequential Gate

**What:** One job with sequential steps — checkout → setup-python → install pytest → run tests → build ZIP → publish release. If tests fail, later steps never run (GitHub Actions halts the job on non-zero exit).

**When to use:** When test gate must block release — sequential steps in a single job enforce this without `needs:` dependencies.

**Example (complete workflow skeleton):**
```yaml
# Source: GitHub Actions docs + softprops/action-gh-release v2 README
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install pytest
        run: pip install pytest

      - name: Run tests
        run: pytest tests/

      - name: Build release ZIP
        run: |
          mkdir paste_hidden
          cp anchor.py colors.py constants.py labels.py link.py \
             menu.py paste_hidden.py prefs.py tabtabtab.py util.py \
             paste_hidden/
          zip -r "paste_hidden-${GITHUB_REF_NAME}.zip" paste_hidden/

      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          name: ${{ github.ref_name }}
          generate_release_notes: true
          files: paste_hidden-${{ github.ref_name }}.zip
```

### Pattern 2: `gh` CLI release creation (alternative, no third-party action)

**What:** Uses the pre-installed `gh` CLI in a `run:` step instead of `softprops/action-gh-release`.

**When to use:** When the project policy prohibits third-party actions.

```yaml
# Source: GitHub CLI docs (cli.github.com/manual/gh_release_create)
- name: Publish GitHub Release
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    gh release create "${{ github.ref_name }}" \
      --repo "$GITHUB_REPOSITORY" \
      --title "${{ github.ref_name }}" \
      --generate-notes \
      "paste_hidden-${{ github.ref_name }}.zip"
```

### Anti-Patterns to Avoid

- **Zipping from the repo root with a glob:** `zip -r artifact.zip .` captures `tests/`, `.planning/`, `__pycache__/` etc. Always use an explicit file list or a staging directory.
- **Files at ZIP root instead of in subdirectory:** `zip paste_hidden.zip *.py` produces `anchor.py` at root. The artist would get `~/.nuke/anchor.py` instead of `~/.nuke/paste_hidden/anchor.py`. Staging into `paste_hidden/` first is mandatory.
- **Running the release step before tests:** In a single job, step ordering is the gate. Never reorder release above tests.
- **Using `actions/upload-artifact` for release assets:** `upload-artifact` creates workflow-internal artifacts (downloadable from the Actions UI, auto-deleted after 90 days). For GitHub Releases, assets must be attached via `softprops/action-gh-release` or `gh release create`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Release creation with asset upload | Custom `curl` to GitHub Releases API | `softprops/action-gh-release@v2` or `gh release create` | Authentication, multipart upload, error handling, idempotency — all handled |
| Auto-generated release notes | Scripted git log parsing | `generate_release_notes: true` / `--generate-notes` | GitHub's API generates notes from PR titles, labels, and commit history correctly |

**Key insight:** The `gh` CLI is pre-installed on all GitHub-hosted ubuntu runners. There is no need for custom API calls.

---

## Common Pitfalls

### Pitfall 1: ZIP internal path — files at root instead of under `paste_hidden/`
**What goes wrong:** `zip paste_hidden.zip *.py` produces an archive where `anchor.py` lives at the ZIP root. Unzipping into `~/.nuke/` places files directly in `~/.nuke/`, not `~/.nuke/paste_hidden/`. `import paste_hidden` fails.
**Why it happens:** `zip` uses the path as given. Running from the repo root with `*.py` gives bare filenames.
**How to avoid:** Stage files into a `paste_hidden/` subdirectory first, then zip that directory. The archive will contain `paste_hidden/anchor.py` etc.
**Warning signs:** `unzip -l paste_hidden-v1.0.0.zip` shows `anchor.py` at top level instead of `paste_hidden/anchor.py`.

### Pitfall 2: `GITHUB_REF_NAME` vs `github.ref_name` in mixed contexts
**What goes wrong:** In `run:` steps, use the env var `$GITHUB_REF_NAME` (shell). In `with:` and expression contexts, use `${{ github.ref_name }}` (Actions expression). Mixing them causes empty strings.
**How to avoid:** Use `$GITHUB_REF_NAME` in shell commands (`run:` blocks), use `${{ github.ref_name }}` in action `with:` inputs.

### Pitfall 3: Missing `permissions: contents: write`
**What goes wrong:** `softprops/action-gh-release` fails with a 403 error because the default token only has read permissions in repositories with restricted token permissions.
**How to avoid:** Add `permissions: contents: write` at the job or workflow level. It is safe to be explicit even if the repo uses permissive defaults.

### Pitfall 4: `__pycache__` directories captured if staging directory is inside the repo
**What goes wrong:** If `paste_hidden/` staging directory is created inside the workspace and `zip -r` recurses into it while `__pycache__` exists inside `paste_hidden/` subdirs, cached bytecode is included.
**How to avoid:** Since only `.py` files are explicitly copied (no subdirectories), `__pycache__` cannot exist inside the staging dir. The staging step copies flat `.py` files only — this is naturally safe with the explicit file manifest approach.

### Pitfall 5: pytest import errors due to test discovery without conftest
**What goes wrong:** `pytest tests/` on a fresh CI runner may fail with import errors for `nuke`, `PySide6`, etc. if conftest.py stubs are not activated.
**Why it doesn't apply here:** The project's `tests/conftest.py` installs all stubs automatically at session start (Phase 8 work). `pytest tests/` picks up conftest.py by default. No additional configuration needed.
**Warning signs:** If this ever surfaces — `ModuleNotFoundError: No module named 'nuke'` — the fix is confirming `conftest.py` is present and that pytest is invoked from the workspace root (not from inside `tests/`).

---

## Code Examples

### Complete workflow (verified pattern)
```yaml
# Source: GitHub Actions push trigger docs + softprops/action-gh-release v2 README
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-24.04

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install pytest
        run: pip install pytest

      - name: Run offline tests
        run: pytest tests/

      - name: Build release ZIP
        run: |
          mkdir paste_hidden
          cp anchor.py colors.py constants.py labels.py link.py \
             menu.py paste_hidden.py prefs.py tabtabtab.py util.py \
             paste_hidden/
          zip -r "paste_hidden-${GITHUB_REF_NAME}.zip" paste_hidden/

      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          name: ${{ github.ref_name }}
          generate_release_notes: true
          files: paste_hidden-${{ github.ref_name }}.zip
```

### Verifying ZIP structure locally before pushing tag
```bash
# Build and inspect locally
mkdir paste_hidden
cp anchor.py colors.py constants.py labels.py link.py \
   menu.py paste_hidden.py prefs.py tabtabtab.py util.py \
   paste_hidden/
zip -r paste_hidden-v1.2.0.zip paste_hidden/
unzip -l paste_hidden-v1.2.0.zip
# Expected output: paste_hidden/anchor.py, paste_hidden/colors.py, ...
rm -rf paste_hidden paste_hidden-v1.2.0.zip
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `actions/create-release` + `actions/upload-release-asset` (two separate actions) | `softprops/action-gh-release@v2` (single action, or `gh release create`) | ~2021, widely adopted by 2023 | Single step; simpler YAML |
| `softprops/action-gh-release@v1` | `softprops/action-gh-release@v2` (v2.5.0 latest as of Dec 2025) | v2 released 2024 | v2 is actively maintained; v1 receives only critical fixes |
| `ubuntu-latest` (was 22.04) | `ubuntu-24.04` (explicit pin, also now the `ubuntu-latest` default since Jan 2025) | Jan 2025 | Explicit pin preferred; ubuntu-24.04 ships Python 3.12 by default |

**Deprecated/outdated:**
- `actions/create-release@v1`: Archived/unmaintained. Do not use.
- `actions/upload-release-asset@v1`: Archived/unmaintained. Do not use.
- `softprops/action-gh-release@v1`: Maintenance-only. Use v2.

---

## Open Questions

1. **SHA pinning for actions**
   - What we know: Security best practice is to pin actions to commit SHAs (e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4`). This prevents supply-chain attacks via mutable tags.
   - What's unclear: The user has not expressed a pinning preference. SHA pinning adds maintenance overhead (Dependabot updates).
   - Recommendation: Use tag pinning (`@v4`, `@v5`, `@v2`) for this internal plugin project. The risk profile of a small Nuke plugin workflow is low. SHA pinning can be added later via Dependabot if desired.

2. **Cleanup of staging directory in the ZIP step**
   - What we know: The `paste_hidden/` staging directory is created inside the workspace during the CI run.
   - What's unclear: Whether the staging directory could accidentally be picked up by pytest if the test step ran after it (it doesn't — tests run before the ZIP step).
   - Recommendation: Build ZIP after tests pass. The staged `paste_hidden/` directory exists only in the CI runner's temporary workspace and is discarded when the job ends.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest via pip) |
| Config file | `pyproject.toml` (ruff config only; pytest uses defaults) |
| Quick run command | `pytest tests/` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CI-01 | Tag push triggers workflow, runs tests, publishes release | manual-only | N/A — requires pushing a real tag to GitHub | N/A |
| CI-02 | ZIP contains only explicit manifest files | manual-only | Inspect `unzip -l paste_hidden-vX.Y.Z.zip` output | N/A |

**Manual-only justification:** CI-01 and CI-02 are infrastructure concerns. There is no application logic to unit-test. The workflow itself IS the test artifact. Verification is performed by:
1. Pushing a test tag and observing the Actions run succeed
2. Downloading the release ZIP and confirming its contents with `unzip -l`

### Sampling Rate
- **Per task commit:** Not applicable (single file creation task)
- **Per wave merge:** `pytest tests/` — confirm existing suite still passes (workflow does not alter source files)
- **Phase gate:** Push a `v*` tag, confirm release appears on GitHub with correct ZIP before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure (`tests/conftest.py`, `tests/stubs.py`) covers all offline tests. No new test files required for this phase.

---

## Sources

### Primary (HIGH confidence)
- `softprops/action-gh-release` GitHub repo (v2, v2.5.0) — inputs, `generate_release_notes`, `files:`, permissions requirement
- GitHub CLI manual (`cli.github.com/manual/gh_release_create`) — `--generate-notes`, `--title`, file attachment syntax
- GitHub Actions docs (push trigger, `on.push.tags`, `github.ref_name`, `GITHUB_REF_NAME`) — trigger patterns and context variables

### Secondary (MEDIUM confidence)
- [ubuntu-24.04 runner image readme](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md) — confirms `zip` 3.0 pre-installed; Python 3.12 default (confirms need for `actions/setup-python`)
- [WebSearch: ubuntu-latest now ubuntu-24.04 since Jan 2025](https://github.com/actions/runner-images/issues/10636) — runner version timeline confirmed

### Tertiary (LOW confidence — no direct verification needed; decisions already locked)
- Multiple blog posts (2024-2025) showing `softprops/action-gh-release@v1/v2` patterns — used to triangulate YAML structure only

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — actions confirmed via official repos and docs; zip CLI presence confirmed via runner image readme
- Architecture: HIGH — sequential single-job pattern is well-established; complete YAML example synthesized from official sources
- Pitfalls: HIGH — ZIP path structure and permissions pitfalls verified against action docs and common failure reports

**Research date:** 2026-03-14
**Valid until:** 2026-09-14 (stable domain; GitHub Actions action versions may update, but v2/v4/v5 tags are maintained)
