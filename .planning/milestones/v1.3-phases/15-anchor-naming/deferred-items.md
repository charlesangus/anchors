# Deferred Items — Phase 15: Anchor Naming

## Pre-existing Issues (Out-of-Scope)

### tests/test_anchor_color_system.py — import error

- **Discovered during:** Phase 15 Plan 01, overall test suite run
- **Error:** `ModuleNotFoundError: No module named 'nuke'` at module import time
- **Root cause:** `test_anchor_color_system.py` imports `colors.py` at module level before any nuke stub is installed in `sys.modules`. Unlike other test files, it does not use `conftest.py`'s stub setup (pytest conftest is session-scoped, but this file's import runs before session fixture). This is a pre-existing issue from before Phase 15.
- **Impact:** 1 test collection ERROR when running `python3 -m unittest discover -s tests -v`; does NOT affect pytest runs (conftest.py handles it there)
- **Action required:** Fix test_anchor_color_system.py to install nuke stub before importing colors, mirroring the pattern in other test files
- **Priority:** Low — does not block Phase 15 plans
