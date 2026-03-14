"""Smoke-test BUG-01 and BUG-02 fixed code paths under real Nuke.

Run with:
    nuke -t /path/to/repo/validation/validate_cross_script_paste.py

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
    2 — not running under nuke -t (ImportError on nuke)

BUG-01: setup_link_node() must propagate the anchor's real tile_color to the link
        node, not overwrite it with ANCHOR_DEFAULT_COLOR afterward.
BUG-02: An anchor node pasted cross-script must stay an anchor — it must not be
        replaced by a link node.
"""

import os
import sys

# Add repo root so production modules are importable without plugin install.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    import nuke
except ImportError:
    print("ERROR: Run this script under nuke -t, not plain Python.")
    sys.exit(2)

import nukescripts

print(f"INFO: NUKE_VERSION_MAJOR = {nuke.NUKE_VERSION_MAJOR}")
if nuke.NUKE_VERSION_MAJOR < 14:
    print("WARN: Nuke version below 14 — some API surface may differ from stub assumptions")

# Production module imports (no menu, colors, or anchor at module level).
from link import setup_link_node, add_input_knob
from paste_hidden import paste_hidden
from constants import ANCHOR_DEFAULT_COLOR, ANCHOR_PREFIX, KNOB_NAME

# ---------------------------------------------------------------------------
# Check runner — captures PASS/FAIL uniformly; collects all failures.
# ---------------------------------------------------------------------------

_failures = 0
_total_checks = 0


def run_check(name, fn):
    """Run fn(); print PASS or FAIL. Increment global failure counter on failure."""
    global _failures, _total_checks
    _total_checks += 1
    try:
        fn()
        print(f"PASS: {name}")
    except AssertionError as exc:
        print(f"FAIL: {name} — {exc}")
        _failures += 1
    except Exception as exc:
        print(f"FAIL: {name} — unexpected exception: {type(exc).__name__}: {exc}")
        _failures += 1


# ---------------------------------------------------------------------------
# Check 3 (informational): nuke.root().name() stem logic
# ---------------------------------------------------------------------------

print("\n--- nuke.root().name() stem (informational) ---")


def check_root_name_is_string():
    root_name = nuke.root().name()
    print(f"  INFO: nuke.root().name() in headless = {repr(root_name)}")
    assert isinstance(root_name, str), f"expected str, got {type(root_name)}"


run_check(
    "nuke.root().name() returns a string (actual value printed above)",
    check_root_name_is_string,
)


# ---------------------------------------------------------------------------
# Check 1 — BUG-01: link receives anchor tile_color via setup_link_node()
# ---------------------------------------------------------------------------

print("\n--- BUG-01: link receives anchor tile_color via setup_link_node() ---")


def check_bug01_link_receives_anchor_color():
    """After setup_link_node(), link tile_color must equal the anchor's real color.

    BUG-01 was: paste_hidden.copy_hidden() called setup_link_node() then overwrote
    link tile_color with ANCHOR_DEFAULT_COLOR (purple). Fixed by removing the overwrite.
    This check exercises the fixed setup_link_node() path directly.
    """
    anchor_color = 0xff0000ff  # red — distinct from ANCHOR_DEFAULT_COLOR purple (0x6f3399ff)
    anchor = nuke.createNode("NoOp")
    link = nuke.createNode("NoOp")
    try:
        anchor["tile_color"].setValue(anchor_color)
        setup_link_node(anchor, link)
        actual = link["tile_color"].value()
        print(
            f"  INFO: anchor tile_color = {hex(anchor_color)}, "
            f"link tile_color after setup_link_node = {hex(int(actual))}, "
            f"ANCHOR_DEFAULT_COLOR = {hex(ANCHOR_DEFAULT_COLOR)}"
        )
        assert int(actual) == anchor_color, (
            f"expected anchor color {hex(anchor_color)}, got {hex(int(actual))} — "
            f"ANCHOR_DEFAULT_COLOR is {hex(ANCHOR_DEFAULT_COLOR)} — BUG-01 regression"
        )
    finally:
        nuke.delete(link)
        nuke.delete(anchor)


run_check(
    "BUG-01: link['tile_color'] == anchor['tile_color'] after setup_link_node()",
    check_bug01_link_receives_anchor_color,
)


# ---------------------------------------------------------------------------
# Check 2 — BUG-02: anchor pasted cross-script stays an anchor
# ---------------------------------------------------------------------------

print("\n--- BUG-02: anchor pasted cross-script stays an anchor ---")


def check_bug02_anchor_stays_anchor_cross_script():
    """Anchor pasted cross-script must not be replaced by a link node.

    BUG-02 was: paste_hidden() would replace a pasted anchor with a link node
    when find_anchor_node() returned an anchor in the destination with the same name.
    Fixed by: unconditional `continue` for cross-script anchor case — anchor stays.

    Strategy:
    - Create an anchor NoOp (name = ANCHOR_PREFIX + 'TestAnchor')
    - Stamp it with a cross-script FQNN (sourceScript.Anchor_TestAnchor) via KNOB_NAME
    - Set root name to 'destScript.nk' so stem is 'destScript' — mismatch triggers cross-script
    - Copy the anchor to the clipboard, then call paste_hidden()
    - Assert the anchor is not deleted and not replaced by a link node
    """
    anchor_name = ANCHOR_PREFIX + "TestAnchor"

    # Save original root name so we can restore it (best effort)
    original_root_name = nuke.root().name()

    anchor = nuke.createNode("NoOp")
    anchor.setName(anchor_name)

    # Stamp the KNOB_NAME with a cross-script FQNN (sourceScript != destScript)
    add_input_knob(anchor)
    anchor[KNOB_NAME].setValue("sourceScript." + anchor_name)

    # Set root name so stem is 'destScript' — cross-script condition is met
    nuke.root()["name"].setValue("destScript.nk")

    # Copy the anchor to the Nuke clipboard file
    nuke.nodeCopy(nukescripts.cut_paste_file())

    pasted_node = None
    try:
        # paste_hidden() calls nuke.nodePaste() internally then processes selected nodes.
        # After the call, the anchor must still exist and must not have been replaced.
        paste_hidden()

        found_original = nuke.toNode(anchor_name)
        print(
            f"  INFO: after paste_hidden(), nuke.toNode('{anchor_name}') = {found_original!r}"
        )

        # The anchor must still be present — BUG-02 would have deleted it
        assert found_original is not None, (
            f"anchor '{anchor_name}' was deleted after cross-script paste — BUG-02 regression"
        )

        # The surviving node's Class() must still be NoOp, not a link class (e.g. 'BackdropNode')
        assert found_original.Class() == "NoOp", (
            f"anchor was replaced by a node of class '{found_original.Class()}' — "
            "expected 'NoOp' (anchor must stay as anchor)"
        )
    finally:
        # Restore root name
        try:
            nuke.root()["name"].setValue(original_root_name)
        except Exception:
            pass

        # Clean up the original anchor
        surviving_original = nuke.toNode(anchor_name)
        if surviving_original is not None:
            nuke.delete(surviving_original)

        # Clean up any pasted copy (nuke may auto-rename it, find by looking for new nodes)
        # The pasted node may have been renamed to avoid clash — clean up all NoOps with
        # Anchor_ prefix that may have been created during this check.
        for candidate in list(nuke.allNodes("NoOp")):
            if candidate.name().startswith(ANCHOR_PREFIX + "TestAnchor"):
                try:
                    nuke.delete(candidate)
                except Exception:
                    pass


run_check(
    "BUG-02: anchor stays as anchor (not replaced by link) after cross-script paste_hidden()",
    check_bug02_anchor_stays_anchor_cross_script,
)


# ---------------------------------------------------------------------------
# Final summary and exit
# ---------------------------------------------------------------------------

print(f"\nSummary: {_total_checks - _failures}/{_total_checks} checks passed")
if _failures > 0:
    sys.exit(1)
sys.exit(0)
