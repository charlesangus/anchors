"""Copy-cut-paste behaviour that re-connects hidden inputs and replaces
input-type nodes with hidden-inputted NoOp link nodes.

Configure which node classes trigger link replacement by editing LINK_SOURCE_CLASSES
in constants.py.
"""

import nuke
import nukescripts

import prefs
from anchor import find_anchor_by_name
from constants import (
    ANCHOR_DEFAULT_COLOR,
    DOT_TYPE_KNOB_NAME,
    HIDDEN_INPUT_CLASSES,
    KNOB_NAME,
    LINK_SOURCE_CLASSES,
    LOCAL_DOT_COLOR,
)
from link import (
    add_input_knob,
    find_anchor_node,
    get_fully_qualified_node_name,
    get_link_class_for_source,
    is_anchor,
    is_link,
    setup_link_node,
)


def copy_anchors(cut=False):  # noqa: C901 — complexity is inherent: 3 node-class paths × same/cross-script gate
    """Add a hidden knob storing the original name of the node/node's input. We
    can then, when pasting, replace the node or reconnect its inputs.

    Setting cut to True does not store the original name on nodes in LINK_SOURCE_CLASSES,
    causing our paste routine to do a normal paste without replacement. This is required
    for cuts, as the original node will have been deleted.

    Uses `with nuke.lastHitGroup():` so that when this is triggered from a Group
    View floating panel (where nuke.thisGroup() = root but the user's last click
    was inside a Group), nuke.selectedNodes() and nuke.nodeCopy() operate in the
    correct group context.
    """
    if not prefs.plugin_enabled:
        with nuke.lastHitGroup():
            nuke.nodeCopy(nukescripts.cut_paste_file())
        return
    with nuke.lastHitGroup():
        selected_nodes = nuke.selectedNodes()
        for node in selected_nodes:
            # Skip nodes that are already links (hidden-input Dots, PostageStamps, etc.)
            # but NOT anchor nodes — an anchor may have KNOB_NAME set from a prior copy
            # or old paste, yet it is still an independent anchor and must be re-stamped
            # with its own current FQNN (Path C below) so subsequent pastes link to it
            # rather than to whatever anchor KNOB_NAME happened to point to previously.
            if is_link(node) and not is_anchor(node):
                continue

            # Path A — LINK_SOURCE_CLASSES file node: scan for an anchor whose input is this
            # node and store the anchor's FQNN so paste can read the correct link class
            # from the anchor's hidden knob. Falls back to the file node's own FQNN when
            # no anchor points at it (legacy direct-file-node path).
            if node.Class() in LINK_SOURCE_CLASSES:
                if prefs.link_classes_paste_mode == 'passthrough':
                    # skip stamping; node copies plainly via nuke.nodeCopy() at end of function
                    continue
                if cut:
                    stored_fqnn = ""
                else:
                    anchor_for_node = None
                    for candidate in nuke.allNodes():
                        if is_anchor(candidate) and candidate.input(0) is node:
                            anchor_for_node = candidate
                            break
                    if anchor_for_node is not None:
                        stored_fqnn = get_fully_qualified_node_name(anchor_for_node)
                    else:
                        # Legacy fallback: no anchor found, store the file node's own FQNN
                        stored_fqnn = get_fully_qualified_node_name(node)
                add_input_knob(node)
                node[KNOB_NAME].setText(stored_fqnn)

            # Path B — hidden-input Dot (or PostageStamp/NoOp with hide_input set):
            # split on whether the upstream input is an anchor (Link Dot) or a plain node (Local Dot).
            elif node.Class() in HIDDEN_INPUT_CLASSES and node['hide_input'].getValue():
                input_node = node.input(0)
                if input_node is None or input_node in selected_nodes:
                    stored_fqnn = ""
                    add_input_knob(node)
                elif is_anchor(input_node):
                    # Link Dot: anchor-backed, cross-script capable.
                    # Override tile_color to canonical purple — setup_link_node() may apply a
                    # custom anchor color via find_node_color(), which we do not want here.
                    stored_fqnn = get_fully_qualified_node_name(input_node)
                    setup_link_node(input_node, node)
                    node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)
                    add_input_knob(node, dot_type='link')
                else:
                    # Local Dot: plain-node-backed, same-script only.
                    # Restore Local appearance after setup_link_node() overwrites label/color.
                    stored_fqnn = get_fully_qualified_node_name(input_node)
                    setup_link_node(input_node, node)
                    source_label = input_node['label'].getText() or input_node.name()
                    node['label'].setValue(f"Local: {source_label}")
                    node['tile_color'].setValue(LOCAL_DOT_COLOR)
                    add_input_knob(node, dot_type='local')
                node[KNOB_NAME].setText(stored_fqnn)

            # Path C — existing anchor node (e.g. a NoOp named Anchor_*) being copied.
            elif is_anchor(node):
                stored_fqnn = "" if cut else get_fully_qualified_node_name(node)
                add_input_knob(node)
                node[KNOB_NAME].setText(stored_fqnn)

        # now that we've stored the info we need on the nodes, do a regular copy
        nuke.nodeCopy(nukescripts.cut_paste_file())


def cut_anchors():
    """Cut selected nodes (i.e. copy then delete). Do not store the original
    name in KNOB_NAME. This will disable replacement on paste.
    """
    if not prefs.plugin_enabled:
        with nuke.lastHitGroup():
            selected_nodes = nuke.selectedNodes()
            nuke.nodeCopy(nukescripts.cut_paste_file())
        for node in selected_nodes:
            nuke.delete(node)
        return
    with nuke.lastHitGroup():
        selected_nodes = nuke.selectedNodes()
    copy_anchors(cut=True)
    for node in selected_nodes:
        nuke.delete(node)


def _extract_display_name_from_fqnn(stored_fqnn):
    """Extract the anchor display name from a stored FQNN for cross-script lookup.

    Returns the display name string (with ANCHOR_PREFIX stripped) if the last
    segment of the FQNN starts with ANCHOR_PREFIX, or None otherwise.
    Returns None for empty or blank FQNNs.
    """
    from constants import ANCHOR_PREFIX
    if not stored_fqnn:
        return None
    node_full_name = stored_fqnn.split('.')[-1]
    if node_full_name.startswith(ANCHOR_PREFIX):
        return node_full_name[len(ANCHOR_PREFIX):]
    return None


def paste_anchors():  # noqa: C901 — complexity is inherent: anchor/link/dot paths × same/cross-script gate
    if not prefs.plugin_enabled:
        with nuke.lastHitGroup():
            return nuke.nodePaste(nukescripts.cut_paste_file())
    with nuke.lastHitGroup():
        last_pasted_node = nuke.nodePaste(nukescripts.cut_paste_file())
        # Snapshot the pasted nodes before the loop. We must not iterate over the live
        # list while mutating it — doing so skips every other element (classic Python
        # off-by-one when remove() shifts indices). GitHub #9.
        nodes_to_process = list(nuke.selectedNodes())
        # Build the final selection separately so replacements (link nodes) appear
        # selected in place of the originals after the loop.
        final_selection = list(nodes_to_process)

        for node in nodes_to_process:
            if KNOB_NAME not in node.knobs():
                # we haven't stored any info on this node, do nothing
                continue

            input_node = find_anchor_node(node)

            if node.Class() in LINK_SOURCE_CLASSES or is_anchor(node):
                # Path A/C: file node or anchor node pasted → replace with a link node.
                # find_anchor_node() resolves the stored FQNN; None means cross-script or
                # deleted.
                if not input_node:
                    # Cross-script (or deleted) case: find_anchor_node() returned None.
                    # File nodes and Dot anchors are left disconnected as placeholders.
                    # BUG-02 fix: anchor pasted cross-script stays an anchor — do not
                    # attempt replacement regardless of whether a same-named anchor exists
                    # in the destination.
                    # GitHub #5 fix: rewrite the stored name to reflect any auto-rename
                    # Nuke may have applied (e.g. appending a digit on name collision),
                    # so that subsequent Link Dots copied from this anchor reconnect correctly.
                    if is_anchor(node):
                        node[KNOB_NAME].setValue(node.fullName())
                    continue
                nukescripts.clear_selection_recursive()
                node["selected"].setValue(True)
                link_node = nuke.createNode(get_link_class_for_source(input_node))
                setup_link_node(input_node, link_node)
                link_node.setXYpos(node.xpos(), node.ypos())
                final_selection.remove(node)
                final_selection.append(link_node)
                nuke.delete(node)

            elif node.Class() in HIDDEN_INPUT_CLASSES:
                # Path B: hidden-input Dot (Link Dot or Local Dot).
                # Determine DOT_TYPE from the explicit knob if present; fall back to FQNN inspection
                # for pre-Phase-5 nodes that lack the knob.
                stored_fqnn = node[KNOB_NAME].getText()
                if DOT_TYPE_KNOB_NAME in node.knobs():
                    dot_type = node[DOT_TYPE_KNOB_NAME].getValue()
                else:
                    # Backward compat: infer from FQNN — anchor-prefix last segment → 'link',
                    # else → 'local'.
                    display_name_for_compat = _extract_display_name_from_fqnn(stored_fqnn)
                    dot_type = 'link' if display_name_for_compat is not None else 'local'

                if not input_node:
                    # Cross-script (or unresolvable FQNN): gate on DOT_TYPE.
                    if dot_type == 'link':
                        # Link Dot: attempt name-based reconnect to same-named anchor in destination.
                        display_name = _extract_display_name_from_fqnn(stored_fqnn)
                        if display_name:
                            destination_anchor = find_anchor_by_name(display_name)
                            if destination_anchor:
                                setup_link_node(destination_anchor, node)
                                # BUG-01 fix: removed ANCHOR_DEFAULT_COLOR overwrite;
                                # setup_link_node() already applies the anchor's real tile_color
                                # via find_node_color().
                    # Local Dot: silent no-op — do not reconnect under any circumstances.
                    continue

                # Same-script: reconnect to the original source by identity.
                # Read dot_type before calling setup_link_node() because setup_link_node()
                # calls add_input_knob() without dot_type, which strips the DOT_TYPE_KNOB_NAME
                # knob. Saving the value here makes the restoration guard reliable regardless
                # of whether the knob survives setup_link_node().
                saved_dot_type = (
                    node[DOT_TYPE_KNOB_NAME].getValue()
                    if DOT_TYPE_KNOB_NAME in node.knobs()
                    else None
                )
                setup_link_node(input_node, node)
                if saved_dot_type == 'local':
                    # Re-add the DOT_TYPE knob that setup_link_node stripped, then restore
                    # Local Dot appearance (label and color overwritten by setup_link_node).
                    add_input_knob(node, dot_type='local')
                    source_label = input_node['label'].getText() or input_node.name()
                    node['label'].setValue(f"Local: {source_label}")
                    node['tile_color'].setValue(LOCAL_DOT_COLOR)

        # it's possible we changed selection, reset it
        nukescripts.clear_selection_recursive()
        for node in final_selection:
            node['selected'].setValue(True)

        # same return as nuke.nodePaste()
        return last_pasted_node


def paste_multiple_anchors():
    selected_nodes = nuke.selectedNodes()
    new_selection = []

    for node in selected_nodes:
        nukescripts.clear_selection_recursive()
        node["selected"].setValue(True)
        paste_anchors()

        new_selection.extend(nuke.selectedNodes())

    nukescripts.clear_selection_recursive()
    for node in new_selection:
        node["selected"].setValue(True)


def migrate_script():
    """Migrate all nodes in the current script from old paste_hidden knob names to anchors knob names.

    Renames the following FROZEN knobs on every node that has them:
      - 'paste_hidden_dot_anchor'  →  'anchors_dot_anchor'
      - 'paste_hidden_dot_type'    →  'anchors_dot_type'

    Removes the old knobs after copying their values to the new names.
    Prints a summary of how many nodes were updated.

    Usage (Python console):
        import anchors
        anchors.migrate_script()
    """
    from constants import DOT_ANCHOR_KNOB_NAME, DOT_TYPE_KNOB_NAME
    OLD_DOT_ANCHOR = 'paste_hidden_dot_anchor'
    OLD_DOT_TYPE = 'paste_hidden_dot_type'

    nodes_updated = 0
    knobs_renamed = 0

    for node in nuke.allNodes(recurseGroups=True):
        node_changed = False
        knobs = node.knobs()

        if OLD_DOT_ANCHOR in knobs and DOT_ANCHOR_KNOB_NAME not in knobs:
            old_value = node[OLD_DOT_ANCHOR].getValue()
            new_knob = nuke.String_Knob(DOT_ANCHOR_KNOB_NAME, '')
            new_knob.setFlag(nuke.INVISIBLE)
            node.addKnob(new_knob)
            node[DOT_ANCHOR_KNOB_NAME].setValue(old_value)
            node.removeKnob(node[OLD_DOT_ANCHOR])
            knobs_renamed += 1
            node_changed = True

        if OLD_DOT_TYPE in knobs and DOT_TYPE_KNOB_NAME not in knobs:
            old_value = node[OLD_DOT_TYPE].getValue()
            new_knob = nuke.String_Knob(DOT_TYPE_KNOB_NAME, '')
            new_knob.setFlag(nuke.INVISIBLE)
            node.addKnob(new_knob)
            node[DOT_TYPE_KNOB_NAME].setValue(old_value)
            node.removeKnob(node[OLD_DOT_TYPE])
            knobs_renamed += 1
            node_changed = True

        if node_changed:
            nodes_updated += 1

    print(f"anchors.migrate_script(): updated {nodes_updated} node(s), renamed {knobs_renamed} knob(s).")


def copy_old():
    nuke.nodeCopy(nukescripts.cut_paste_file())


def cut_old():
    selected_nodes = nuke.selectedNodes()
    nuke.nodeCopy(nukescripts.cut_paste_file())
    for node in selected_nodes:
        nuke.delete(node)


def paste_old():
    nuke.nodePaste(nukescripts.cut_paste_file())
