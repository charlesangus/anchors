"""Set Input To... commands for issue #50.

Each entry point opens the anchor picker, and on selection creates a link node
above the currently-selected target node and wires it into a specific input
slot:

    set_input_to_b()              -> input 0
    set_input_to_a()              -> input 1
    set_input_to_mask()           -> the target node's mask input (resolved by
                                     the >100-maxInputs heuristic, see
                                     resolve_mask_input_index)
    set_input_to_first_available() -> the lowest free input on the target node

Q/W/E/mask replace whatever was previously wired to the target slot via
nuke.Node.setInput.  R only fills empty slots so it never silently clobbers
existing wiring.
"""

import nuke

import anchor
import prefs
from link import is_link


# ---------------------------------------------------------------------------
# Selected-target helpers
# ---------------------------------------------------------------------------

def _selected_target_node():
    """Return the single selected non-link node, or None.

    A link node is excluded so that pressing Q/W/E/R after creating a link
    (when the new link is now selected) does not re-target the link itself.
    """
    selected = nuke.selectedNodes()
    if len(selected) != 1:
        return None
    target = selected[0]
    if is_link(target):
        return None
    return target


def resolve_mask_input_index(target_node):
    """Return the input index to treat as the mask input for *target_node*, or None.

    Heuristic (per the locked plan):
      - If maxInputs() > 100 (e.g. Merge2, Dissolve, Switch) -> input 2.
      - Otherwise -> the last input slot (maxInputs() - 1).
      - Single-input nodes (maxInputs() <= 1) have no mask input -> None.
    """
    try:
        max_inputs = target_node.maxInputs()
    except (AttributeError, TypeError):
        return None
    if max_inputs is None or max_inputs <= 1:
        return None
    if max_inputs > 100:
        return 2
    return max_inputs - 1


def _first_free_input_index(target_node):
    """Return the lowest input index on *target_node* that is currently empty, or None.

    Walks 0..maxInputs()-1 and returns the first slot whose input(i) is None.
    Returns None if every slot is filled.
    """
    try:
        max_inputs = target_node.maxInputs()
    except (AttributeError, TypeError):
        return None
    if max_inputs is None or max_inputs <= 0:
        return None
    for input_index in range(max_inputs):
        if target_node.input(input_index) is None:
            return input_index
    return None


# ---------------------------------------------------------------------------
# Predicates used by leader_overlay to grey-out unavailable bindings.
# ---------------------------------------------------------------------------

def can_set_input_b(target_node):
    """True when target has at least input 0."""
    if target_node is None:
        return False
    try:
        return target_node.maxInputs() >= 1
    except (AttributeError, TypeError):
        return False


def can_set_input_a(target_node):
    """True when target has at least input 1."""
    if target_node is None:
        return False
    try:
        return target_node.maxInputs() >= 2
    except (AttributeError, TypeError):
        return False


def can_set_input_mask(target_node):
    """True when target has more than 1 input (resolve_mask_input_index returns a slot)."""
    if target_node is None:
        return False
    return resolve_mask_input_index(target_node) is not None


def can_set_input_first_available(target_node):
    """True when target has any free input slot."""
    if target_node is None:
        return False
    return _first_free_input_index(target_node) is not None


# ---------------------------------------------------------------------------
# Link-creation helper shared by all four set_input_to_* entry points.
# ---------------------------------------------------------------------------

# Per-input horizontal offset between sibling links so they don't overlap when
# multiple links feed the same multi-input target.  Input 0 sits centered above
# the target; each subsequent input shifts the link 150px further right.
_LINK_INPUT_X_OFFSET = 150


def _position_link_for_input(link_node, target_node, input_index):
    """Place *link_node* above *target_node*, offset by input_index * 150px."""
    base_x = target_node.xpos() + target_node.screenWidth() // 2 - link_node.screenWidth() // 2
    link_node.setXYpos(
        base_x + input_index * _LINK_INPUT_X_OFFSET,
        target_node.ypos() - link_node.screenHeight() - 40,
    )


def _create_link_above_target(anchor_node, target_node, input_index):
    """Create a link to *anchor_node* and position it above *target_node*.

    Returns the new link node.  Horizontal offset scales with input_index so
    multiple links feeding the same target don't overlap.
    """
    link_node = anchor.create_from_anchor(anchor_node)
    _position_link_for_input(link_node, target_node, input_index)
    return link_node


def _set_input_to_index(input_index):
    """Open the picker; on selection, wire the new link to *input_index* on the target.

    Silent no-op when no single target node is selected.  The picker itself
    handles the "no anchors exist" case.
    """
    if not prefs.plugin_enabled:
        return
    target_node = _selected_target_node()
    if target_node is None:
        return

    def _on_pick(anchor_node, hit_group):
        with hit_group:
            link_node = _create_link_above_target(anchor_node, target_node, input_index)
            target_node.setInput(input_index, link_node)

    anchor.pick_anchor(_on_pick)


# ---------------------------------------------------------------------------
# Public entry points — invoked by leader.py dispatch table.
# ---------------------------------------------------------------------------

def set_input_to_b():
    """Open picker; wire new link into target's input 0 (the B slot on Merge)."""
    _set_input_to_index(0)


def set_input_to_a():
    """Open picker; wire new link into target's input 1 (the A slot on Merge)."""
    _set_input_to_index(1)


def set_input_to_mask():
    """Open picker; wire new link into target's mask input.

    Silent no-op when the target has no mask input
    (resolve_mask_input_index returns None).
    """
    if not prefs.plugin_enabled:
        return
    target_node = _selected_target_node()
    if target_node is None:
        return
    mask_index = resolve_mask_input_index(target_node)
    if mask_index is None:
        return
    _set_input_to_index(mask_index)


def set_input_to_first_available():
    """Open picker; wire new link into the lowest-index free input on the target.

    Silent no-op when every slot is already filled.
    """
    if not prefs.plugin_enabled:
        return
    target_node = _selected_target_node()
    if target_node is None:
        return
    free_index = _first_free_input_index(target_node)
    if free_index is None:
        return
    _set_input_to_index(free_index)


