"""Shared predicates and link-node utilities.

Neither anchor.py nor anchors.py need to import from each other;
both pull what they need from here and from constants.py.
"""

import contextlib
import re

import nuke

from constants import (
    ANCHOR_DEFAULT_COLOR,
    ANCHOR_PREFIX,
    DOT_ANCHOR_KNOB_NAME,
    DOT_LINK_LABEL_FONT_SIZE,
    DOT_TYPE_KNOB_NAME,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    TAB_NAME,
)


def get_fully_qualified_node_name(node):
    """Return <script_stem>.<node.fullName()> so we can detect cross-script refs."""
    return f"{nuke.root().name().split('.')[0]}.{node.fullName()}"


def find_node_default_color(node):
    prefs = nuke.toNode("preferences")
    node_colour_slots = [
        prefs[knob_name].value().split(' ')
        for knob_name in prefs.knobs()
        if knob_name.startswith("NodeColourSlot")
    ]
    node_colour_slots = [
        [item.replace("'", "").lower() for item in parent_item]
        for parent_item in node_colour_slots
    ]
    node_colour_choices = [
        prefs[knob_name].value()
        for knob_name in prefs.knobs()
        if knob_name.startswith("NodeColourChoice")
    ]
    for i, slot in enumerate(node_colour_slots):
        if node.Class().lower() in slot:
            return node_colour_choices[i]
    return prefs["NodeColor"].value()


def find_node_color(node):
    tile_color = node["tile_color"].value()
    if tile_color == 0:
        tile_color = find_node_default_color(node)
    return tile_color


def find_smallest_containing_backdrop(node):
    """Return the smallest BackdropNode that fully contains *node*, or None."""
    nx, ny = node.xpos(), node.ypos()
    containing = []
    for bd in nuke.allNodes('BackdropNode'):
        bx = bd.xpos()
        by = bd.ypos()
        bw = bd['bdwidth'].value()
        bh = bd['bdheight'].value()
        if bx <= nx < bx + bw and by <= ny < by + bh:
            containing.append(bd)
    if not containing:
        return None
    return min(containing, key=lambda bd: bd['bdwidth'].value() * bd['bdheight'].value())


def get_link_class_for_source(source_node):
    """Return the appropriate link node class for a given source node.

    Dot nodes produce a 'Dot' link; all other nodes produce a 'NoOp' link.
    """
    if source_node is not None and source_node.Class() == 'Dot':
        return 'Dot'
    return 'NoOp'


def mark_dot_as_anchor(dot_node):
    """Add the canonical anchor marker knob to a Dot node if not already present.

    Also syncs the Dot's node name to 'Anchor_<sanitized_label>' so that the
    FQNN reflects the anchor name and cross-script reconnect can strip the
    ANCHOR_PREFIX to recover the display name.  If the label is empty or
    sanitizes to empty, the node name is left unchanged (the caller can set
    the label before calling, or rename_anchor_to() can fix it later).
    """
    if DOT_ANCHOR_KNOB_NAME in dot_node.knobs():
        dot_node[DOT_ANCHOR_KNOB_NAME].setValue(True)
        return
    knob = nuke.Boolean_Knob(DOT_ANCHOR_KNOB_NAME, 'Dot Anchor')
    knob.setVisible(False)
    knob.setValue(True)
    dot_node.addKnob(knob)

    label = dot_node['label'].getValue().strip()
    sanitized_label = re.sub(r'[^A-Za-z0-9_]', '_', label)
    if sanitized_label:
        dot_node.setName(ANCHOR_PREFIX + sanitized_label)

    dot_node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)


def is_anchor(node):
    try:
        if node.name().startswith(ANCHOR_PREFIX):
            return True
        if node.Class() == 'Dot':
            # Explicit anchor knob (set by mark_dot_as_anchor)
            if DOT_ANCHOR_KNOB_NAME in node.knobs():
                return True
            # Legacy: labelled dot that is not a link, not hidden-input, no "Link: " prefix
            label = node['label'].getValue().strip()
            if (label and not label.startswith('Link: ')
                    and not is_link(node) and not node['hide_input'].getValue()):
                return True
        return False
    except Exception:
        return False


def is_link(node):
    return KNOB_NAME in node.knobs()


def add_link_reconnect_knob(node):
    if LINK_RECONNECT_KNOB_NAME in node.knobs():
        return
    knob = nuke.PyScript_Knob(LINK_RECONNECT_KNOB_NAME, "Reconnect",
        """import link
link.reconnect_link_node(nuke.thisNode())""")
    node.addKnob(knob)


def add_input_knob(node, dot_type=None):
    if not is_anchor(node):
        add_link_reconnect_knob(node)

    # Remove our custom knobs to make sure they're at the end.
    # DOT_TYPE_KNOB_NAME is removed first so it can be re-added last (keeping correct order:
    # TAB_NAME → KNOB_NAME → DOT_TYPE_KNOB_NAME).
    with contextlib.suppress(Exception):
        node.removeKnob(node[DOT_TYPE_KNOB_NAME])
    with contextlib.suppress(Exception):
        node.removeKnob(node[KNOB_NAME])
    with contextlib.suppress(Exception):
        node.removeKnob(node[TAB_NAME])

    tab = nuke.Tab_Knob(TAB_NAME)
    tab.setFlag(nuke.INVISIBLE)
    tab.setVisible(False)
    node.addKnob(tab)

    k = nuke.String_Knob(KNOB_NAME)
    k.setVisible(False)
    node.addKnob(k)

    if dot_type is not None:
        dot_type_knob = nuke.String_Knob(DOT_TYPE_KNOB_NAME)
        dot_type_knob.setVisible(False)
        dot_type_knob.setValue(dot_type)
        node.addKnob(dot_type_knob)


def setup_link_node(input_node, link_node):
    link_node["hide_input"].setValue(True)
    link_node["tile_color"].setValue(find_node_color(input_node))

    if input_node["label"].getText():
        link_node["label"].setValue(f"Link: {input_node['label'].getText()}")
    else:
        link_node["label"].setValue(f"Link: {input_node.name()}")

    if link_node.Class() == 'Dot':
        link_node["note_font_size"].setValue(DOT_LINK_LABEL_FONT_SIZE)

    add_input_knob(link_node)
    link_node[KNOB_NAME].setValue(get_fully_qualified_node_name(input_node))
    link_node.setInput(0, input_node)


def find_anchor_node(link_node):
    fully_qualified_name_from_knob = link_node[KNOB_NAME].getText()
    fqn_from_knob_split = fully_qualified_name_from_knob.split(".")

    # strip off the script name to get Nuke's version of a full name
    full_name_from_knob = ".".join(fqn_from_knob_split[1:])
    fully_qualified_name_from_current = get_fully_qualified_node_name(link_node)
    fqn_from_current_split = fully_qualified_name_from_current.split(".")
    prefix_from_knob = fqn_from_knob_split[:-1]
    prefix_from_current = fqn_from_current_split[:-1]
    if prefix_from_knob != prefix_from_current:
        # we are in a different script and/or Group, do nothing
        return None
    anchor_node = nuke.toNode(full_name_from_knob)
    return anchor_node


def reconnect_link_node(link_node):
    anchor_node = find_anchor_node(link_node)
    if not anchor_node:
        return None
    link_node.setInput(0, anchor_node)
