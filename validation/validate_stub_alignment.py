"""Validate that StubNode/StubKnob assumptions in tests/ match real Nuke API.

Run with:
    nuke -t /path/to/repo/validation/validate_stub_alignment.py

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
    2 — not running under nuke -t (ImportError on nuke)
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

print(f"INFO: NUKE_VERSION_MAJOR = {nuke.NUKE_VERSION_MAJOR}")
if nuke.NUKE_VERSION_MAJOR < 14:
    print("WARN: Nuke version below 14 — some API surface may differ from stub assumptions")

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
# Group: nuke module-level API
# ---------------------------------------------------------------------------

print("\n--- nuke module-level API ---")


def check_root_name_is_str():
    root_name = nuke.root().name()
    print(f"  INFO: nuke.root().name() in headless = {repr(root_name)}")
    assert isinstance(root_name, str), f"expected str, got {type(root_name)}"


run_check("nuke.root().name() returns a string", check_root_name_is_str)


def check_all_nodes_returns_list():
    result = nuke.allNodes()
    assert isinstance(result, list), f"expected list, got {type(result)}"


run_check("nuke.allNodes() returns a list", check_all_nodes_returns_list)


def check_to_node_nonexistent_returns_none():
    result = nuke.toNode("nonexistent_node_xyz")
    assert result is None, f"expected None for nonexistent node, got {result!r}"


run_check("nuke.toNode('nonexistent_node_xyz') returns None", check_to_node_nonexistent_returns_none)


def check_to_node_preferences_is_not_none():
    result = nuke.toNode("preferences")
    print(f"  INFO: nuke.toNode('preferences') = {result!r}")
    assert result is not None, (
        "nuke.toNode('preferences') returned None — HIGH-RISK: stub returns None but "
        "real Nuke always has a preferences node. Fix tests/stubs.py if this fails."
    )


run_check(
    "nuke.toNode('preferences') is not None [HIGH-RISK: stub returns None]",
    check_to_node_preferences_is_not_none,
)


def check_create_node_returns_node():
    node = nuke.createNode("NoOp")
    try:
        assert node is not None, "nuke.createNode('NoOp') returned None"
    finally:
        if node is not None:
            nuke.delete(node)


run_check("nuke.createNode('NoOp') returns a non-None node object", check_create_node_returns_node)


def check_nuke_version_major_is_int():
    result = nuke.NUKE_VERSION_MAJOR
    assert isinstance(result, int), f"expected int, got {type(result)}: {result!r}"


run_check("nuke.NUKE_VERSION_MAJOR is an int", check_nuke_version_major_is_int)


def check_nuke_invisible_is_int():
    result = nuke.INVISIBLE
    assert isinstance(result, int), f"expected int, got {type(result)}: {result!r}"


run_check("nuke.INVISIBLE is an int", check_nuke_invisible_is_int)


# ---------------------------------------------------------------------------
# Group: StubKnob alignment — tile_color knob
# ---------------------------------------------------------------------------

print("\n--- StubKnob alignment: tile_color knob ---")


def check_tile_color_value_returns_int_or_float():
    node = nuke.createNode("NoOp")
    try:
        knob = node["tile_color"]
        result = knob.value()
        print(f"  INFO: tile_color.value() type = {type(result).__name__}, value = {result!r}")
        assert isinstance(result, (int, float)), (
            f"tile_color.value() returned unexpected type {type(result).__name__}: {result!r}"
        )
    finally:
        nuke.delete(node)


run_check(
    "StubKnob: tile_color.value() returns int or float (not str, not None)",
    check_tile_color_value_returns_int_or_float,
)


def check_tile_color_set_and_read():
    node = nuke.createNode("NoOp")
    try:
        knob = node["tile_color"]
        knob.setValue(0xff0000ff)
        result = knob.value()
        print(f"  INFO: tile_color.value() after setValue(0xff0000ff) = {result!r} (type={type(result).__name__})")
        assert int(result) == 0xff0000ff, (
            f"tile_color.value() after setValue(0xff0000ff): expected {0xff0000ff}, "
            f"got {result!r} (int={int(result)})"
        )
    finally:
        nuke.delete(node)


run_check(
    "StubKnob: tile_color.setValue(0xff0000ff) then value() == 0xff0000ff (int coercion accepted)",
    check_tile_color_set_and_read,
)


def check_tile_color_get_value_equals_value():
    node = nuke.createNode("NoOp")
    try:
        knob = node["tile_color"]
        knob.setValue(0xff0000ff)
        result_value = knob.value()
        result_get_value = knob.getValue()
        print(
            f"  INFO: tile_color.value()={result_value!r} getValue()={result_get_value!r} "
            f"(types: value={type(result_value).__name__}, getValue={type(result_get_value).__name__})"
        )
        assert int(result_value) == int(result_get_value), (
            f"tile_color.getValue()={result_get_value!r} differs from .value()={result_value!r}"
        )
    finally:
        nuke.delete(node)


run_check(
    "StubKnob: tile_color.getValue() matches tile_color.value() (same value after int coercion)",
    check_tile_color_get_value_equals_value,
)


# ---------------------------------------------------------------------------
# Group: StubKnob alignment — string knob
# ---------------------------------------------------------------------------

print("\n--- StubKnob alignment: string knob ---")


def check_string_knob_set_value_get_text():
    node = nuke.createNode("NoOp")
    try:
        knob = nuke.String_Knob("test_str_knob_validation", "Test String Knob")
        node.addKnob(knob)
        knob.setValue("hello")
        result = knob.getText()
        assert result == "hello", f"getText() expected 'hello', got {result!r}"
    finally:
        nuke.delete(node)


run_check(
    "StubKnob: String_Knob.setValue('hello') then getText() == 'hello'",
    check_string_knob_set_value_get_text,
)


def check_string_knob_value_and_get_value():
    node = nuke.createNode("NoOp")
    try:
        knob = nuke.String_Knob("test_str_knob_validation2", "Test String Knob 2")
        node.addKnob(knob)
        knob.setValue("hello")
        result_value = knob.value()
        result_get_value = knob.getValue()
        print(
            f"  INFO: String_Knob.value()={result_value!r} getValue()={result_get_value!r}"
        )
        assert result_value == "hello", f"value() expected 'hello', got {result_value!r}"
        assert result_get_value == "hello", f"getValue() expected 'hello', got {result_get_value!r}"
    finally:
        nuke.delete(node)


run_check(
    "StubKnob: String_Knob.value() == 'hello' and getValue() == 'hello' after setValue",
    check_string_knob_value_and_get_value,
)


# ---------------------------------------------------------------------------
# Group: StubNode alignment — core methods
# ---------------------------------------------------------------------------

print("\n--- StubNode alignment: core methods ---")


def check_node_name_is_str():
    node = nuke.createNode("NoOp")
    try:
        result = node.name()
        print(f"  INFO: NoOp node.name() = {result!r}")
        assert isinstance(result, str), f"name() expected str, got {type(result)}: {result!r}"
    finally:
        nuke.delete(node)


run_check("StubNode: node.name() returns a str", check_node_name_is_str)


def check_node_full_name_is_str():
    node = nuke.createNode("NoOp")
    try:
        result = node.fullName()
        print(f"  INFO: NoOp node.fullName() = {result!r}")
        assert isinstance(result, str), f"fullName() expected str, got {type(result)}: {result!r}"
    finally:
        nuke.delete(node)


run_check("StubNode: node.fullName() returns a str", check_node_full_name_is_str)


def check_node_class_returns_noop():
    node = nuke.createNode("NoOp")
    try:
        result = node.Class()
        assert result == "NoOp", f"Class() expected 'NoOp', got {result!r}"
    finally:
        nuke.delete(node)


run_check("StubNode: NoOp node.Class() returns 'NoOp'", check_node_class_returns_noop)


def check_node_xpos_ypos_returns_numeric():
    node = nuke.createNode("NoOp")
    try:
        xpos_result = node.xpos()
        ypos_result = node.ypos()
        print(f"  INFO: node.xpos()={xpos_result!r} (type={type(xpos_result).__name__}), "
              f"node.ypos()={ypos_result!r} (type={type(ypos_result).__name__})")
        assert isinstance(xpos_result, (int, float)), (
            f"xpos() expected int or float, got {type(xpos_result)}: {xpos_result!r}"
        )
        assert isinstance(ypos_result, (int, float)), (
            f"ypos() expected int or float, got {type(ypos_result)}: {ypos_result!r}"
        )
    finally:
        nuke.delete(node)


run_check(
    "StubNode: node.xpos() and node.ypos() return int or float",
    check_node_xpos_ypos_returns_numeric,
)


def check_node_knobs_returns_dict():
    node = nuke.createNode("NoOp")
    try:
        result = node.knobs()
        assert isinstance(result, dict), f"knobs() expected dict, got {type(result)}: {result!r}"
    finally:
        nuke.delete(node)


run_check("StubNode: node.knobs() returns a dict", check_node_knobs_returns_dict)


def check_node_screen_width_is_positive_numeric():
    node = nuke.createNode("NoOp")
    try:
        result = node.screenWidth()
        print(f"  INFO: node.screenWidth() = {result!r} (type={type(result).__name__})")
        assert isinstance(result, (int, float)), (
            f"screenWidth() expected int or float, got {type(result)}: {result!r}"
        )
        assert result > 0, f"screenWidth() expected positive value, got {result!r}"
    finally:
        nuke.delete(node)


run_check(
    "StubNode: node.screenWidth() returns a positive int or float",
    check_node_screen_width_is_positive_numeric,
)


# ---------------------------------------------------------------------------
# Group: StubNode alignment — knob access
# ---------------------------------------------------------------------------

print("\n--- StubNode alignment: knob access ---")


def check_tile_color_knob_is_not_none():
    node = nuke.createNode("NoOp")
    try:
        knob = node["tile_color"]
        assert knob is not None, "node['tile_color'] returned None — expected a knob object"
    finally:
        nuke.delete(node)


run_check(
    "StubNode: node['tile_color'] returns a knob object (not None)",
    check_tile_color_knob_is_not_none,
)


def check_missing_knob_raises_key_error():
    node = nuke.createNode("NoOp")
    try:
        raised_key_error = False
        try:
            _ = node["does_not_exist_knob_xyz"]
        except KeyError:
            raised_key_error = True
        assert raised_key_error, (
            "node['does_not_exist_knob_xyz'] did not raise KeyError — "
            "[HIGH-RISK: stub raises KeyError, must match real Nuke]"
        )
    finally:
        nuke.delete(node)


run_check(
    "StubNode: node['does_not_exist_knob_xyz'] raises KeyError [HIGH-RISK]",
    check_missing_knob_raises_key_error,
)


# ---------------------------------------------------------------------------
# Group: StubNode alignment — node manipulation
# ---------------------------------------------------------------------------

print("\n--- StubNode alignment: node manipulation ---")


def check_set_name_updates_name():
    node = nuke.createNode("NoOp")
    try:
        node.setName("TestNode_ValidateAlign")
        result = node.name()
        assert result == "TestNode_ValidateAlign", (
            f"After setName('TestNode_ValidateAlign'), name() returned {result!r}"
        )
    finally:
        # Re-fetch by name in case node object reference broke after setName
        surviving = nuke.toNode("TestNode_ValidateAlign")
        if surviving is not None:
            nuke.delete(surviving)
        else:
            try:
                nuke.delete(node)
            except Exception:
                pass


run_check(
    "StubNode: setName('TestNode_ValidateAlign') then name() returns new name",
    check_set_name_updates_name,
)


def check_set_xy_pos_updates_pos():
    node = nuke.createNode("NoOp")
    try:
        node.setXYpos(10, 20)
        xpos_result = node.xpos()
        ypos_result = node.ypos()
        assert xpos_result == 10, f"xpos() expected 10 after setXYpos(10, 20), got {xpos_result!r}"
        assert ypos_result == 20, f"ypos() expected 20 after setXYpos(10, 20), got {ypos_result!r}"
    finally:
        nuke.delete(node)


run_check(
    "StubNode: setXYpos(10, 20) then xpos() == 10 and ypos() == 20",
    check_set_xy_pos_updates_pos,
)


def check_set_input_does_not_raise():
    node = nuke.createNode("NoOp")
    try:
        node.setInput(0, None)  # should not raise
    finally:
        nuke.delete(node)


run_check("StubNode: setInput(0, None) does not raise", check_set_input_does_not_raise)


# ---------------------------------------------------------------------------
# Group: nuke knob factories
# ---------------------------------------------------------------------------

print("\n--- nuke knob factories ---")


def check_string_knob_factory_name_method():
    node = nuke.createNode("NoOp")
    try:
        knob = nuke.String_Knob("test_str_knob", "label")
        node.addKnob(knob)
        result = knob.name()
        print(f"  INFO: String_Knob('test_str_knob').name() = {result!r}")
        assert result == "test_str_knob", (
            f"String_Knob name() expected 'test_str_knob', got {result!r}"
        )
    finally:
        nuke.delete(node)


run_check(
    "nuke.String_Knob('test_str_knob', 'label').name() returns 'test_str_knob'",
    check_string_knob_factory_name_method,
)


def check_boolean_knob_factory_has_name_method():
    node = nuke.createNode("NoOp")
    try:
        knob = nuke.Boolean_Knob("test_bool_knob", "label")
        node.addKnob(knob)
        result = knob.name()
        print(f"  INFO: Boolean_Knob('test_bool_knob').name() = {result!r}")
        assert hasattr(knob, "name"), "Boolean_Knob object has no .name() method"
        # name() must return something — real Nuke knobs always have a name
        assert result is not None, "Boolean_Knob.name() returned None"
    finally:
        nuke.delete(node)


run_check(
    "nuke.Boolean_Knob('test_bool_knob', 'label') returns object with .name() method",
    check_boolean_knob_factory_has_name_method,
)


# ---------------------------------------------------------------------------
# Final summary and exit
# ---------------------------------------------------------------------------

print(f"\nSummary: {_total_checks - _failures}/{_total_checks} checks passed")
if _failures > 0:
    sys.exit(1)
sys.exit(0)
