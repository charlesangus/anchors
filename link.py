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
    DOT_ANCHOR_MIN_FONT_SIZE,
    DOT_ANCHOR_PREFIX,
    DOT_LINK_LABEL_FONT_SIZE,
    DOT_TYPE_KNOB_NAME,
    KNOB_NAME,
    LINK_RECONNECT_KNOB_NAME,
    TAB_NAME,
)


def get_fully_qualified_node_name(node):
    """Return node.fullName() — the group-hierarchy path without script stem.

    Stored on link/anchor knobs to identify anchors across scripts.
    Group hierarchy (e.g. 'Group1.Anchor_Foo') is preserved; the script name
    is not included because anchors must remain reconnectable when copied
    across scripts.
    """
    return node.fullName()


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

    Also syncs the Dot's node name to 'Anchor_Dot_<sanitized_label>' so that the
    FQNN reflects the anchor name and cross-script reconnect can strip the
    DOT_ANCHOR_PREFIX to recover the display name.  If the label is empty or
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
        dot_node.setName(DOT_ANCHOR_PREFIX + sanitized_label)

    dot_node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)


def is_anchor(node):
    try:
        if node.name().startswith(ANCHOR_PREFIX):
            return True
        if node.name().startswith(DOT_ANCHOR_PREFIX):
            return True
        if node.Class() == 'Dot':
            # Font size gate: Dots must have a sufficiently large label to qualify as anchors.
            # Dots with note_font_size below DOT_ANCHOR_MIN_FONT_SIZE are organisational notes
            # and must never appear in anchor navigation.
            note_font_size = node['note_font_size'].value()
            if note_font_size < DOT_ANCHOR_MIN_FONT_SIZE:
                return False
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
    stored_name = link_node[KNOB_NAME].getText()
    if not stored_name:
        return None
    stored_name_parts = stored_name.split(".")

    # Resolve the stored name to a live node.  Values written by older versions
    # of the plugin included a script-stem prefix (e.g. "scriptName.Anchor_Foo"
    # or "scriptName.Group1.Anchor_Foo").  Try the stored name as-is first; if
    # that fails and there are multiple segments, strip the first segment as a
    # backward-compat fallback so those older scripts continue to work.
    anchor_node = nuke.toNode(stored_name)
    if anchor_node is None and len(stored_name_parts) > 1:
        name_without_stem = ".".join(stored_name_parts[1:])
        candidate = nuke.toNode(name_without_stem)
        if candidate is not None:
            anchor_node = candidate
            stored_name_parts = name_without_stem.split(".")

    if anchor_node is None:
        return None

    # Verify group context: link node and anchor must share the same group
    # prefix so that an anchor inside Group1 is not reachable from a
    # root-level link node (and vice versa).
    link_name_parts = link_node.fullName().split(".")
    if stored_name_parts[:-1] != link_name_parts[:-1]:
        return None

    return anchor_node


def reconnect_link_node(link_node):
    anchor_node = find_anchor_node(link_node)
    if not anchor_node:
        return None
    link_node.setInput(0, anchor_node)
