"""Copy-cut-paste behaviour that re-connects hidden inputs."""

import os

import contextlib

import nuke
import nukescripts

import prefs
from anchor import (
    anchor_display_name,
    find_anchor_by_name,
    rename_anchor_to,
)
from constants import (
    ANCHOR_DEFAULT_COLOR,
    ANCHOR_PREFIX,
    DOT_ANCHOR_PREFIX,
    DOT_TYPE_KNOB_NAME,
    HIDDEN_INPUT_CLASSES,
    KNOB_NAME,
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


def _get_script_stem():
    # os.path.splitext handles multi-dot names like "project.shotA.nk" → "project.shotA"
    # whereas split('.')[0] would give the ambiguous "project" for both shotA and shotB.
    # Returns '' for unsaved scripts (nuke.root().name() == '').  _find_local_node()
    # will then pass the same-script guard trivially (both source and destination stems
    # are ''), so a local-dot FQNN like '.NodeName' still resolves — this is intentional
    # and consistent behaviour for unsaved-script workflows.
    return os.path.splitext(os.path.basename(nuke.root().name()))[0]


def copy_anchors(cut=False):  # noqa: C901 — complexity is inherent: multiple node-class paths × same/cross-script gate
    """Add a hidden knob storing the original name of the node/node's input. We
    can then, when pasting, replace the node or reconnect its inputs.

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
        selection_is_all_anchors = bool(selected_nodes) and all(is_anchor(n) for n in selected_nodes)
        for node in selected_nodes:
            # Path L — existing link nodes: re-setup from the current live input so the
            # clipboard copy always reflects fresh state.  Anchors that also carry a stale
            # KNOB_NAME are handled by the elif at the bottom of the chain, not here.
            if is_link(node) and not is_anchor(node):
                input_node = node.input(0)
                if input_node is None or input_node in selected_nodes:
                    # Input is absent or being copied alongside this node.  Stamp "" so
                    # paste_anchors() knows to re-setup from whatever Nuke re-connects the
                    # pasted copy to.
                    node[KNOB_NAME].setText("")
                elif is_anchor(input_node):
                    add_input_knob(node, dot_type='link')
                    setup_link_node(input_node, node)
                else:
                    # Local Dot: restore Local appearance after setup_link_node() overwrites
                    # label/color, matching the behaviour of Path B for non-link hidden-input nodes.
                    script_stem = _get_script_stem()
                    stored_fqnn = f"{script_stem}.{get_fully_qualified_node_name(input_node)}"
                    setup_link_node(input_node, node)
                    add_input_knob(node, dot_type='local')
                    source_label = (input_node['label'].getText() if 'label' in input_node.knobs() else '') or input_node.name()
                    node['label'].setValue(f"Local: {source_label}")
                    node['tile_color'].setValue(LOCAL_DOT_COLOR)
                    node[KNOB_NAME].setText(stored_fqnn)


            # Path B — hidden-input Dot (or PostageStamp/NoOp with hide_input set):
            # split on whether the upstream input is an anchor (Link Dot) or a plain node (Local Dot).
            elif node.Class() in HIDDEN_INPUT_CLASSES and node['hide_input'].getValue():
                input_node = node.input(0)
                if input_node is None or input_node in selected_nodes:
                    stored_fqnn = ""
                    add_input_knob(node)
                    node[KNOB_NAME].setText(stored_fqnn)
                elif is_anchor(input_node):
                    # Link Dot: anchor-backed, cross-script capable.
                    # Override tile_color to canonical purple — setup_link_node() may apply a
                    # custom anchor color via find_node_color(), which we do not want here.
                    add_input_knob(node, dot_type='link')
                    setup_link_node(input_node, node)
                    node['tile_color'].setValue(ANCHOR_DEFAULT_COLOR)
                else:
                    # Local Dot: plain-node-backed, same-script only.
                    # Restore Local appearance after setup_link_node() overwrites label/color.
                    script_stem = _get_script_stem()
                    stored_fqnn = f"{script_stem}.{get_fully_qualified_node_name(input_node)}"
                    setup_link_node(input_node, node)
                    add_input_knob(node, dot_type='local')
                    source_label = (input_node['label'].getText() if 'label' in input_node.knobs() else '') or input_node.name()
                    node['label'].setValue(f"Local: {source_label}")
                    node['tile_color'].setValue(LOCAL_DOT_COLOR)
                    node[KNOB_NAME].setText(stored_fqnn)

            elif is_anchor(node):
                if selection_is_all_anchors and not cut:
                    # Issue #37: entire selection is anchors — stamp each anchor's own FQNN
                    # so paste_anchors() can replace the pasted copy with a Link pointing
                    # back to the original anchor.  Skip when cutting: the originals will be
                    # deleted, so paste can never resolve them and would leave the pasted
                    # copies with stale link knobs.
                    add_input_knob(node, dot_type='link')
                    node[KNOB_NAME].setText(get_fully_qualified_node_name(node))
                elif is_link(node):
                    # Anchor with stale KNOB_NAME from a prior old-style paste: clear it so
                    # the clipboard copy carries no spurious reference.
                    node[KNOB_NAME].setValue('')

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

    Returns the display name string (with ANCHOR_PREFIX or DOT_ANCHOR_PREFIX stripped)
    if the last segment of the FQNN starts with either anchor prefix, or None otherwise.
    Returns None for empty or blank FQNNs.
    """
    if not stored_fqnn:
        return None
    node_full_name = stored_fqnn.split('.')[-1]
    if node_full_name.startswith(DOT_ANCHOR_PREFIX):
        return node_full_name[len(DOT_ANCHOR_PREFIX):]
    if node_full_name.startswith(ANCHOR_PREFIX):
        return node_full_name[len(ANCHOR_PREFIX):]
    return None


def _find_local_node(stored_fqnn):
    """Resolve a local-dot FQNN to a live node, enforcing same-script guard.

    Expects "scriptStem.nodeFullName" format.  Returns the node when the stem
    matches the current script; returns None for a different stem (cross-script)
    or for any FQNN without a dot (defensively handles pre-fix nodes that are
    restamped at copy time before being pasted).
    """
    if not stored_fqnn or '.' not in stored_fqnn:
        return None
    current_stem = _get_script_stem()
    prefix = current_stem + '.'
    if not stored_fqnn.startswith(prefix):
        return None
    node_name = stored_fqnn[len(prefix):]
    if not node_name:
        return None
    return nuke.toNode(node_name)


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

        # Issue #35: re-stamp the visible anchor name/label on plain pasted
        # anchors (no KNOB_NAME = not a link-stamped copy). After nodePaste,
        # Nuke may have renamed the node to avoid collision (e.g. Anchor_Foo →
        # Anchor_Foo1) while the label knob still holds the old serialised
        # value. For NoOp anchors the display name is re-derived from the
        # (now correct) post-collision node name; for Dot anchors the label
        # knob is the source of truth and is written back directly.
        for pasted_node in nodes_to_process:
            if is_anchor(pasted_node) and KNOB_NAME not in pasted_node.knobs():
                display_name = anchor_display_name(pasted_node)
                if not display_name:
                    continue
                label_knob = pasted_node.knobs().get("label")
                if label_knob is not None:
                    if label_knob.value() != display_name:
                        label_knob.setValue(display_name)
                    continue
                with contextlib.suppress(ValueError):
                    rename_anchor_to(pasted_node, display_name)

        for node in nodes_to_process:
            if KNOB_NAME not in node.knobs():
                # we haven't stored any info on this node, do nothing
                continue

            if (is_anchor(node)
                  and DOT_TYPE_KNOB_NAME in node.knobs()
                  and node[DOT_TYPE_KNOB_NAME].getValue() == 'link'):
                # Path D (Issue #37): pasted node is an anchor that was stamped at copy
                # time because the entire selection was anchors.  Only anchors that carry
                # DOT_TYPE_KNOB_NAME = 'link' are processed — this knob is added by
                # add_input_knob(node, dot_type='link') in copy_anchors() and is absent
                # on old-style stale-KNOB_NAME anchors (which must remain as-is per BUG-02).
                # Path D is checked before Path B because NoOp is in HIDDEN_INPUT_CLASSES;
                # without this ordering a stamped anchor NoOp would enter Path B instead.
                input_node = find_anchor_node(node)
                if not input_node:
                    # Cross-script (or unresolvable FQNN): attempt name-based fallback.
                    # KNOB_NAME is guaranteed present here — we passed the top-of-loop guard.
                    stored_fqnn = node[KNOB_NAME].getText()
                    display_name = _extract_display_name_from_fqnn(stored_fqnn)
                    original_anchor = find_anchor_by_name(display_name) if display_name else None
                else:
                    original_anchor = input_node
                if not original_anchor:
                    # Cannot resolve — leave the pasted anchor as-is.
                    continue
                nukescripts.clear_selection_recursive()
                node["selected"].setValue(True)
                link_node = nuke.createNode(get_link_class_for_source(original_anchor))
                setup_link_node(original_anchor, link_node)
                link_node.setXYpos(node.xpos(), node.ypos())
                if node in final_selection:
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

                if dot_type == 'local':
                    input_node = _find_local_node(stored_fqnn)
                else:
                    input_node = find_anchor_node(node)

                # "Input was in selection" case: KNOB_NAME="" because the input was copied
                # alongside this node.  Nuke has already re-connected the pasted copy to the
                # pasted copy of the input, so just re-setup from the actual live input.
                if stored_fqnn == "" and node.input(0) is not None:
                    setup_link_node(node.input(0), node)
                    continue

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
                    source_label = (input_node['label'].getText() if 'label' in input_node.knobs() else '') or input_node.name()
                    node['label'].setValue(f"Local: {source_label}")
                    node['tile_color'].setValue(LOCAL_DOT_COLOR)

        # it's possible we changed selection, reset it
        nukescripts.clear_selection_recursive()
        for node in final_selection:
            node['selected'].setValue(True)

        # same return as nuke.nodePaste()
        return last_pasted_node


def paste_multiple_anchors():
    with nuke.lastHitGroup():
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


def migrate_to_stemless_names():
    """Migrate stored anchor references from old format (script stem prefix) to new format.

    Old format: "scriptStem.fullName"       e.g. "myScript.Anchor_Foo"
    New format: "fullName" only             e.g. "Anchor_Foo" or "Group1.Anchor_Foo"

    Scans every node in the current script (including inside Groups) that has a
    KNOB_NAME knob.  If the stored value cannot be resolved by nuke.toNode() but
    CAN be resolved after stripping the first segment, the stored value is rewritten
    to the shorter form.  References that cannot be resolved either way (orphaned or
    pointing to a node in a different script) are left unchanged.

    Prints a summary of how many nodes were updated.

    Usage (Python console or Anchors menu):
        import anchors
        anchors.migrate_to_stemless_names()
    """
    nodes_updated = 0

    for node in nuke.allNodes(recurseGroups=True):
        if KNOB_NAME not in node.knobs():
            continue

        stored_name = node[KNOB_NAME].getText()
        if not stored_name:
            continue

        name_parts = stored_name.split('.')
        if len(name_parts) <= 1:
            # Single segment — already new format, nothing to strip
            continue

        if nuke.toNode(stored_name) is not None:
            # Resolves as-is: stored value is already new format (or first segment
            # happens to be a group name that Nuke resolves correctly)
            continue

        name_without_stem = '.'.join(name_parts[1:])
        if nuke.toNode(name_without_stem) is not None:
            # Old format confirmed: full value failed but stripped value resolves
            node[KNOB_NAME].setValue(name_without_stem)
            nodes_updated += 1
        # else: orphaned or cross-script reference — leave unchanged

    print(f"anchors.migrate_to_stemless_names(): updated {nodes_updated} node(s).")


def copy_old():
    nuke.nodeCopy(nukescripts.cut_paste_file())


def cut_old():
    selected_nodes = nuke.selectedNodes()
    nuke.nodeCopy(nukescripts.cut_paste_file())
    for node in selected_nodes:
        nuke.delete(node)


def paste_old():
    nuke.nodePaste(nukescripts.cut_paste_file())
