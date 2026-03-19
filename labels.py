"""User-facing label helper functions for anchor and link nodes."""

import nuke

import prefs
from constants import (
    DOT_ANCHOR_MIN_FONT_SIZE,
    DOT_LABEL_FONT_SIZE_LARGE,
    DOT_LABEL_FONT_SIZE_MEDIUM,
    DOT_LABEL_FONT_SIZE_SMALL,
    DOT_LINK_LABEL_FONT_SIZE,
    KNOB_NAME,
    NODE_LABEL_FONT_SIZE_LARGE,
)
from link import (
    get_fully_qualified_node_name,
    is_anchor,
    is_link,
    mark_dot_as_anchor,
    reconnect_link_node,
)


def _update_dot_link_labels(dot_node, new_label):
    """Set the label on every link node pointing at dot_node and reconnect each one."""
    dot_fqnn = get_fully_qualified_node_name(dot_node)
    for candidate_node in nuke.allNodes():
        if not is_link(candidate_node) or is_anchor(candidate_node):
            continue
        if candidate_node[KNOB_NAME].getText() == dot_fqnn:
            candidate_node['label'].setValue(f"Link: {new_label}")
            candidate_node['note_font_size'].setValue(DOT_LINK_LABEL_FONT_SIZE)
            reconnect_link_node(candidate_node)


def _apply_label(node, text, dot_font_size=None, node_font_size=None):
    """Set node's label to text and optionally update font size.

    For Dot nodes: apply dot_font_size (if given) and propagate the label to
    linked nodes. For all other nodes: apply node_font_size (if given).
    """
    node['label'].setValue(text)
    if node.Class() == 'Dot':
        if dot_font_size is not None:
            node['note_font_size'].setValue(dot_font_size)
        if dot_font_size is not None and dot_font_size >= DOT_ANCHOR_MIN_FONT_SIZE:
            mark_dot_as_anchor(node)
            _update_dot_link_labels(node, text)
    else:
        if node_font_size is not None:
            node['note_font_size'].setValue(node_font_size)


def create_large_label():
    """Prompt for a label and apply it with large font sizing."""
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    node = selected_nodes[0]
    text = nuke.getInput("Label:", node['label'].getText())
    if text is None:
        return
    _apply_label(node, text, DOT_LABEL_FONT_SIZE_LARGE, NODE_LABEL_FONT_SIZE_LARGE)


def create_medium_label():
    """Prompt for a label and apply it; Dot nodes get medium font size, others unchanged."""
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    node = selected_nodes[0]
    text = nuke.getInput("Label:", node['label'].getText())
    if text is None:
        return
    _apply_label(node, text, DOT_LABEL_FONT_SIZE_MEDIUM, None)


def create_small_label():
    """Prompt for a label and apply it; Dot nodes get small font size (33), others unchanged."""
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    node = selected_nodes[0]
    text = nuke.getInput("Label:", node['label'].getText())
    if text is None:
        return
    _apply_label(node, text, DOT_LABEL_FONT_SIZE_SMALL, None)


def append_to_label():
    """Prompt for a suffix and append it to the node's existing label."""
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    node = selected_nodes[0]
    text = nuke.getInput("Append to label:", "")
    if text is None:
        return
    _apply_label(node, node['label'].getText() + text)
