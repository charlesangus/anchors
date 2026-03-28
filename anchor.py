"""Anchor system: creation, renaming, reconnection, and the tabtabtab picker."""

import contextlib
import os
import re

import nuke
import nukescripts

try:
    if hasattr(nuke, 'NUKE_VERSION_MAJOR') and nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
    else:
        from PySide2 import QtCore, QtGui, QtWidgets
        from PySide2.QtCore import Qt
except ImportError:
    QtGui = None
    QtWidgets = None
    QtCore = None

import prefs
import tabtabtab_anchors as _tabtabtab
from colors import ColorPaletteDialog
from constants import (
    ANCHOR_DEFAULT_COLOR,
    ANCHOR_PREFIX,
    ANCHOR_RECONNECT_KNOB_NAME,
    ANCHOR_RENAME_KNOB_NAME,
    ANCHOR_SET_COLOR_KNOB_NAME,
    DOT_LABEL_FONT_SIZE_LARGE,
    DOT_LABEL_FONT_SIZE_MEDIUM,
    KNOB_NAME,
    NODE_LABEL_FONT_SIZE_LARGE,
)
from link import (
    find_node_color,
    find_smallest_containing_backdrop,
    get_fully_qualified_node_name,
    get_link_class_for_source,
    is_anchor,
    is_link,
    reconnect_link_node,
    setup_link_node,
)


def sanitize_anchor_name(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name.strip())


def find_anchor_color(anchor):
    """Return the tile color an anchor should display.

    Priority:
      1. Smallest BackdropNode containing the anchor — only when the anchor's
         input is a Read node.
      2. The anchor's input node color (with Preferences fallback).
      3. Hard-coded default purple if neither is available.
    """
    input_node = anchor.input(0)

    # --- 1. Backdrop color — only for Read nodes ---
    if input_node is not None and input_node.Class() == 'Read':
        smallest = find_smallest_containing_backdrop(anchor)
        if smallest is not None:
            color = smallest['tile_color'].value()
            if color != 0:
                return color

    # --- 2. Attached input node color (with Preferences fallback) ---
    if input_node is not None:
        return find_node_color(input_node)

    # --- 3. Default anchor color ---
    return ANCHOR_DEFAULT_COLOR


def add_reconnect_anchor_knob(node):
    if ANCHOR_RECONNECT_KNOB_NAME in node.knobs():
        return
    # Bug fix: use ANCHOR_RECONNECT_KNOB_NAME (not LINK_RECONNECT_KNOB_NAME) so
    # the guard above actually fires on subsequent calls.
    knob = nuke.PyScript_Knob(ANCHOR_RECONNECT_KNOB_NAME, "Reconnect Child Links",
        """import anchor
anchor.reconnect_anchor_node(nuke.thisNode())""")
    node.addKnob(knob)


def add_rename_anchor_knob(node):
    if ANCHOR_RENAME_KNOB_NAME in node.knobs():
        return
    knob = nuke.PyScript_Knob(ANCHOR_RENAME_KNOB_NAME, "Rename",
        """import anchor
anchor.rename_anchor(nuke.thisNode())""")
    node.addKnob(knob)


def add_set_color_anchor_knob(node):
    """Add a 'Set Color' PyScript_Knob to *node* if it does not already have one.

    Dot anchors are excluded from the color system — this function is a no-op for them.
    """
    if node.Class() == 'Dot':
        return
    if ANCHOR_SET_COLOR_KNOB_NAME in node.knobs():
        return
    knob = nuke.PyScript_Knob(ANCHOR_SET_COLOR_KNOB_NAME, "Set Color",
        """import anchor
anchor.set_anchor_color(nuke.thisNode())""")
    node.addKnob(knob)


def propagate_anchor_color(anchor_node, color_int):
    """Set *anchor_node* tile_color to *color_int* and propagate to all referencing Link nodes.

    Dot anchors have fixed colors managed by the system — this function returns
    early without making any changes for Dot anchors.
    """
    if anchor_node.Class() == 'Dot':
        return
    anchor_node['tile_color'].setValue(color_int)
    for link_node in get_links_for_anchor(anchor_node):
        link_node['tile_color'].setValue(color_int)


def _persist_custom_colors_from_dialog(dialog):
    """Save any newly staged custom colors from *dialog* back to prefs and disk.

    Call this on every accepted ColorPaletteDialog so custom colors added via
    "Custom Color..." persist across sessions.  Only saves when the staged list
    differs from the current prefs.custom_colors to avoid spurious disk writes.
    """
    staged = dialog.chosen_custom_colors()
    if staged != prefs.custom_colors:
        prefs.custom_colors = staged
        prefs.save()


def set_anchor_color(anchor_node):
    """Open the color palette dialog and apply the chosen color to *anchor_node*.

    This is the entry point called by the 'Set Color' PyScript_Knob on the anchor node.
    """
    if ColorPaletteDialog is None:
        return
    if anchor_node.Class() == 'Dot':
        return
    current_color = anchor_node['tile_color'].value()
    dialog = ColorPaletteDialog(
        initial_color=current_color,
        show_name_field=False,
        custom_colors=prefs.custom_colors,
    )
    if dialog.exec_() == ColorPaletteDialog.Accepted:
        _persist_custom_colors_from_dialog(dialog)
        chosen_color = dialog.selected_color_int()
        if chosen_color is not None:
            propagate_anchor_color(anchor_node, chosen_color)


def anchor_display_name(node):
    if node.Class() == 'Dot':
        return node['label'].getValue().strip()
    return node.name()[len(ANCHOR_PREFIX):]


def all_anchors():
    anchors = [n for n in nuke.allNodes() if is_anchor(n)]
    anchors.sort(key=lambda n: anchor_display_name(n).lower())
    return anchors


def find_anchor_by_name(display_name):
    """Return the anchor node whose display name equals *display_name*, or None."""
    for anchor in all_anchors():
        if anchor_display_name(anchor) == display_name:
            return anchor
    return None


def get_links_for_anchor(anchor_node):
    """Return all link nodes in the current script that reference *anchor_node*."""
    fqnn = get_fully_qualified_node_name(anchor_node)
    return [node for node in nuke.allNodes() if is_link(node) and node[KNOB_NAME].getText() == fqnn]


# Compiled once at module level — covers %d, %04d, ####, %V, %v frame token styles
_FRAME_TOKEN_PATTERN = re.compile(r'[._]?(?:%0?\d*d|#{1,}|%[Vv])')


def suggest_anchor_name(input_node):
    """Return a suggested anchor name based on the input node's file knob and backdrop context."""
    import prefs
    suggestion = ""

    if 'file' in input_node.knobs():
        filepath = input_node['file'].getValue()
        if filepath:
            filename = os.path.basename(filepath)
            stripped_filename = _FRAME_TOKEN_PATTERN.sub('', filename)
            user_regex = prefs.naming_regex
            if user_regex:
                try:
                    compiled_pattern = re.compile(user_regex)
                    regex_match = compiled_pattern.match(stripped_filename)
                    if regex_match:
                        naming_template = prefs.naming_template
                        if naming_template:
                            try:
                                suggestion = naming_template.format_map(regex_match.groupdict())
                            except (KeyError, ValueError):
                                suggestion = regex_match.group(0)
                        else:
                            suggestion = regex_match.group(0)
                    # No match — fall through to hardcoded path below
                except re.error:
                    pass  # Invalid regex — fall through to hardcoded path below
            # Hardcoded fallback: runs when user_regex is blank, regex has no match, or re.error
            if not suggestion:
                hardcoded_match = re.match(r'^(.+)_v\d+(?:\.[^.]+)?\.[^.]+$', stripped_filename)
                suggestion = hardcoded_match.group(1) if hardcoded_match else os.path.splitext(stripped_filename)[0]

    smallest = find_smallest_containing_backdrop(input_node)
    if smallest is not None:
        label = smallest['label'].getValue().strip()
        if label:
            suggestion = label + '_' + suggestion

    return suggestion


def rename_anchor_to(anchor_node, name, color=None):
    """Rename an anchor to *name* and update all referencing link nodes.

    Raises ValueError if *name* sanitizes to an empty string.
    For Dot anchors the node name is kept in sync with the label so that the
    FQNN (which embeds the node name) reflects the new name.  Old FQNNs stored
    on link nodes are updated to the new FQNN.

    Parameters
    ----------
    anchor_node : nuke.Node
        The anchor node to rename.
    name : str
        New display name for the anchor.
    color : int or None
        If provided, propagate this color to the anchor and all its Link nodes
        after renaming.
    """
    if anchor_node.Class() == 'Dot':
        sanitized = sanitize_anchor_name(name)
        if not sanitized:
            raise ValueError(f"Anchor name {name!r} produces an empty sanitized name")

        old_fqnn = get_fully_qualified_node_name(anchor_node)
        anchor_node.setName(ANCHOR_PREFIX + sanitized)
        new_label = name.strip()
        anchor_node['label'].setValue(new_label)
        new_fqnn = get_fully_qualified_node_name(anchor_node)

        for node in nuke.allNodes():
            if is_link(node) and node[KNOB_NAME].getText() == old_fqnn:
                node[KNOB_NAME].setValue(new_fqnn)
                node['label'].setValue(f"Link: {new_label}")
    else:
        sanitized = sanitize_anchor_name(name)
        if not sanitized:
            raise ValueError(f"Anchor name {name!r} produces an empty sanitized name")

        old_fqn = get_fully_qualified_node_name(anchor_node)
        anchor_node.setName(ANCHOR_PREFIX + sanitized)
        anchor_node['label'].setValue(anchor_display_name(anchor_node))
        new_fqn = get_fully_qualified_node_name(anchor_node)

        new_label = anchor_node['label'].getText() or anchor_node.name()
        for node in nuke.allNodes():
            if is_link(node) and node[KNOB_NAME].getText() == old_fqn:
                node[KNOB_NAME].setValue(new_fqn)
                node['label'].setValue(f"Link: {new_label}")

    if color is not None:
        propagate_anchor_color(anchor_node, color)


def rename_anchor(anchor_node):
    """Prompt the user for a new name (and optionally a new color) and rename the anchor."""
    if anchor_node.Class() == 'Dot':
        suggested = anchor_display_name(anchor_node)
    else:
        input_node = anchor_node.input(0)
        suggested = (
            suggest_anchor_name(input_node) if input_node is not None
            else anchor_display_name(anchor_node)
        )

    if ColorPaletteDialog is None:
        # Qt unavailable — fall back to plain text input
        name = nuke.getInput("Rename anchor:", suggested)
        if not name or not name.strip():
            return
        with contextlib.suppress(ValueError):
            rename_anchor_to(anchor_node, name)
        return

    current_color = int(anchor_node['tile_color'].value())
    auto_derived_color = int(find_anchor_color(anchor_node))
    dialog = ColorPaletteDialog(
        initial_color=current_color,
        show_name_field=True,
        initial_name=suggested,
        custom_colors=prefs.custom_colors,
        default_color=auto_derived_color,
    )
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    _persist_custom_colors_from_dialog(dialog)
    chosen_name = dialog.chosen_name
    if not chosen_name or not chosen_name.strip():
        return
    chosen_color = dialog.selected_color_int()
    try:
        rename_anchor_to(anchor_node, chosen_name)
    except ValueError:
        nuke.message(f"Invalid anchor name: {chosen_name!r}")
        return
    if chosen_color is not None:
        propagate_anchor_color(anchor_node, chosen_color)


def rename_selected_anchor():
    if not prefs.plugin_enabled:
        return
    selected = nuke.selectedNodes()
    if len(selected) == 1 and is_anchor(selected[0]):
        rename_anchor(selected[0])


def reconnect_anchor_node(anchor_node):
    # Bug fix: filter by exact FQNN match so only this anchor's links reconnect,
    # not all links in the script (the old substring check was commented out).
    fqnn = get_fully_qualified_node_name(anchor_node)
    for node in nuke.allNodes():
        if is_link(node) and node[KNOB_NAME].getText() == fqnn:
            reconnect_link_node(node)


def reconnect_all_links():
    for node in nuke.allNodes():
        if is_link(node):
            reconnect_link_node(node)


def create_anchor():
    if not prefs.plugin_enabled:
        return
    # Capture the group context before any Qt event loop runs so we can restore
    # it when calling create_anchor_named() (which calls nuke.createNode()).
    hit_group = nuke.lastHitGroup()
    with hit_group:
        selected = nuke.selectedNodes()
    input_node = selected[0] if len(selected) == 1 else None

    suggested = suggest_anchor_name(input_node) if input_node is not None else ""

    if ColorPaletteDialog is None:
        # Qt unavailable — fall back to plain text input
        name = nuke.getInput("Anchor name:", suggested)
        if not name or not name.strip():
            return
        with hit_group:
            with contextlib.suppress(ValueError):
                create_anchor_named(name, input_node)
        return

    # Derive the auto-computed colour for the prospective anchor.  We cannot call
    # find_anchor_color() here because that function expects the anchor to already
    # exist and calls anchor.input(0) — passing input_node would instead examine
    # what is upstream *of* input_node.  Mirror the same priority logic directly:
    #   1. Backdrop colour — only when input_node is a Read
    #   2. Input node's own colour (tile_color with Preferences fallback)
    #   3. Hard-coded default purple
    if input_node is not None:
        if input_node.Class() == 'Read':
            containing_backdrop = find_smallest_containing_backdrop(input_node)
            if containing_backdrop is not None and containing_backdrop['tile_color'].value() != 0:
                pre_color = int(containing_backdrop['tile_color'].value())
            else:
                pre_color = int(find_node_color(input_node))
        else:
            pre_color = int(find_node_color(input_node))
    else:
        pre_color = ANCHOR_DEFAULT_COLOR

    dialog = ColorPaletteDialog(
        initial_color=pre_color,
        show_name_field=True,
        initial_name=suggested,
        custom_colors=prefs.custom_colors,
        default_color=pre_color,
    )
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    _persist_custom_colors_from_dialog(dialog)
    chosen_name = dialog.chosen_name
    if not chosen_name or not chosen_name.strip():
        return
    chosen_color = dialog.selected_color_int()
    with hit_group:
        with contextlib.suppress(ValueError):
            create_anchor_named(chosen_name, input_node, color=chosen_color)


def create_from_anchor(anchor_node):
    nukescripts.clear_selection_recursive()
    source = anchor_node if anchor_node.Class() == 'Dot' else anchor_node.input(0)
    link_class = get_link_class_for_source(source)
    link = nuke.createNode(link_class)
    setup_link_node(anchor_node, link)
    return link


def create_anchor_named(name, input_node=None, color=None):
    """Create an anchor with the given *name* without any user prompt.

    Returns the new anchor node.
    Raises ValueError if *name* sanitizes to an empty string.

    Parameters
    ----------
    name : str
        Display name for the anchor.
    input_node : nuke.Node or None
        Optional input node to connect the anchor to.
    color : int or None
        Explicit tile color as 0xRRGGBBAA int.  If None, falls back to
        find_anchor_color() for backward-compatible color derivation.
    """
    sanitized = sanitize_anchor_name(name)
    if not sanitized:
        raise ValueError(f"Anchor name {name!r} produces an empty sanitized name")

    nukescripts.clear_selection_recursive()
    anchor = nuke.createNode('NoOp')
    anchor.setName(ANCHOR_PREFIX + sanitized)
    anchor['label'].setValue(anchor_display_name(anchor))

    if input_node is not None:
        anchor.setInput(0, input_node)
        anchor.setXYpos(
            input_node.xpos() + input_node.screenWidth() // 2 - anchor.screenWidth() // 2,
            input_node.ypos() + input_node.screenHeight() + 20
        )

    if color is not None:
        anchor['tile_color'].setValue(color)
    else:
        anchor['tile_color'].setValue(find_anchor_color(anchor))
    add_reconnect_anchor_knob(anchor)
    add_rename_anchor_knob(anchor)
    add_set_color_anchor_knob(anchor)
    return anchor


def create_anchor_silent(input_node=None):
    """Create an anchor using the auto-suggested name without any user prompt.

    Falls back to the input node's name, then to ``"Anchor"`` if no suggestion
    can be derived.  Returns the new anchor node.
    """
    if input_node is not None:
        suggested = suggest_anchor_name(input_node) or input_node.name()
    else:
        suggested = "Anchor"
    return create_anchor_named(suggested, input_node)


def create_link_for_anchor_named(display_name):
    """Create a link node wired to the anchor with *display_name*.

    Returns the new link node.
    Raises ValueError if no anchor with that display name exists.
    """
    anchor = find_anchor_by_name(display_name)
    if anchor is None:
        raise ValueError(f"No anchor found with display name {display_name!r}")
    return create_from_anchor(anchor)


def try_create_link_for_anchor_named(display_name):
    """Create a link node wired to the anchor with *display_name*, or None.

    Returns the new link node, or None if no anchor with that display name exists.
    """
    anchor = find_anchor_by_name(display_name)
    if anchor is None:
        return None
    return create_from_anchor(anchor)


class AnchorPlugin(_tabtabtab.TabTabTabPlugin):
    """tabtabtab plugin that lists all anchor nodes for link creation."""

    def __init__(self):
        self._hit_group = None

    def get_items(self):
        # _hit_group is set externally by select_anchor_and_create() BEFORE
        # show() calls get_items().  We must NOT capture lastHitGroup() here
        # because show() runs after the original menu-callback context has
        # exited, so lastHitGroup() would return root.
        hit_group = self._hit_group or nuke.root()
        with hit_group:
            return [
                {
                    'menuobj': anchor,
                    'menupath': 'Anchors/' + anchor_display_name(anchor),
                }
                for anchor in all_anchors()
            ]

    def get_weights_file(self):
        return os.path.expanduser('~/.nuke/anchors_anchor_weights.json')

    def invoke(self, thing):
        anchor = thing['menuobj']
        with self._hit_group:
            if nuke.exists(anchor.name()):
                create_from_anchor(anchor)

    def get_icon(self, menuobj):
        return None

    def get_color(self, menuobj):
        color_int = menuobj['tile_color'].value()  # 0xRRGGBBAA — reads what was actually set
        r = (color_int >> 24) & 0xFF
        g = (color_int >> 16) & 0xFF
        b = (color_int >> 8) & 0xFF
        color = QtGui.QColor(r, g, b)
        return (color, color)


# Deprecated: superseded by create_anchor() for Dot nodes (BUG-04, Phase 14).
# Retained for reference only — do not call.
def _offer_make_dot_anchor(dot_node):
    """Prompt the user to label an un-anchored Dot and mark it as an anchor."""
    panel = nuke.Panel("Make Dot Anchor")
    panel.addEnumerationPulldown("Label size", "Medium Large")
    if not panel.show():
        return
    size = panel.value("Label size")
    text = nuke.getInput("Label:", dot_node['label'].getText())
    if text is None:
        return
    from labels import _apply_label
    if size == "Medium":
        _apply_label(dot_node, text, DOT_LABEL_FONT_SIZE_MEDIUM, None)
    else:
        _apply_label(dot_node, text, DOT_LABEL_FONT_SIZE_LARGE, NODE_LABEL_FONT_SIZE_LARGE)
    # _apply_label → mark_dot_as_anchor already ran; add anchor utility knobs
    add_reconnect_anchor_knob(dot_node)
    add_rename_anchor_knob(dot_node)


def anchor_shortcut():
    """If a node is selected, create an anchor from it. Otherwise, pick an anchor to create from."""
    if not prefs.plugin_enabled:
        return
    hit_group = nuke.lastHitGroup()
    with hit_group:
        selected = nuke.selectedNodes()
    if len(selected) == 1 and is_anchor(selected[0]):
        rename_anchor(selected[0])
    elif selected:
        create_anchor()
    else:
        select_anchor_and_create(hit_group)


_anchor_picker_widget = None


def select_anchor_and_create(hit_group=None):
    if not prefs.plugin_enabled:
        return
    if QtWidgets is None:
        return
    if hit_group is None:
        hit_group = nuke.lastHitGroup()
    with hit_group:
        if not all_anchors():
            return
    global _anchor_picker_widget
    if _anchor_picker_widget is not None:
        try:
            _anchor_picker_widget.plugin._hit_group = hit_group
            _anchor_picker_widget.under_cursor()
            _anchor_picker_widget.show()
            _anchor_picker_widget.raise_()
            return
        except RuntimeError:
            _anchor_picker_widget = None
    plugin = AnchorPlugin()
    plugin._hit_group = hit_group
    _anchor_picker_widget = _tabtabtab.TabTabTabWidget(
        plugin, winflags=Qt.FramelessWindowHint
    )
    _anchor_picker_widget.under_cursor()
    _anchor_picker_widget.show()
    _anchor_picker_widget.raise_()


def _save_dag_position():
    """Capture the current DAG viewport state into the back-navigation slot.

    Called before every navigate-to-anchor or navigate-to-backdrop jump.
    Overwrites any previously saved position — single-slot, no history stack.
    """
    global _back_position
    _back_position = (nuke.zoom(), nuke.center())


def navigate_back():
    """Restore the DAG to the position saved before the last Alt+A jump.

    Silent no-op if no position has been saved yet. Consumes the slot —
    subsequent calls are no-ops until the next navigate-to-anchor jump.
    """
    if not prefs.plugin_enabled:
        return
    global _back_position
    if _back_position is None:
        return
    zoom_level, center_xy = _back_position
    _back_position = None
    nuke.zoom(zoom_level, center_xy)
    nukescripts.clear_selection_recursive()


def navigate_to_backdrop(backdrop_node):
    """Zoom the DAG to fit *backdrop_node*.

    Uses nuke.zoom() rather than nuke.zoomToFitSelected() so that the
    currently focused DAG panel (which may be a Group's internal panel)
    is targeted instead of always zooming the root DAG.
    """
    nukescripts.clear_selection_recursive()
    backdrop_node['selected'].setValue(True)
    center_x = backdrop_node.xpos() + backdrop_node.screenWidth() // 2
    center_y = backdrop_node.ypos() + backdrop_node.screenHeight() // 2
    nuke.zoom(1.0, [center_x, center_y])
    nukescripts.clear_selection_recursive()


def navigate_to_anchor(anchor_node):
    """Zoom the DAG to fit *anchor_node* and its visible-path upstream nodes.

    Uses nuke.zoom() rather than nuke.zoomToFitSelected() so that the
    currently focused DAG panel (which may be a Group's internal panel)
    is targeted instead of always zooming the root DAG.
    """
    from util import upstream_ignoring_hidden
    upstream_nodes = upstream_ignoring_hidden(anchor_node) or set()
    nodes_to_fit = upstream_nodes | {anchor_node}

    nukescripts.clear_selection_recursive()
    for node in nodes_to_fit:
        node["selected"].setValue(True)

    center_x = sum(n.xpos() + n.screenWidth() // 2 for n in nodes_to_fit) / len(nodes_to_fit)
    center_y = sum(n.ypos() + n.screenHeight() // 2 for n in nodes_to_fit) / len(nodes_to_fit)
    nuke.zoom(1.0, [center_x, center_y])
    nukescripts.clear_selection_recursive()


class AnchorNavigatePlugin(_tabtabtab.TabTabTabPlugin):
    """tabtabtab plugin that lists all anchor nodes for DAG navigation."""

    def __init__(self):
        self._hit_group = None

    def get_items(self):
        # _hit_group is set externally by select_anchor_and_navigate() BEFORE
        # show() calls get_items().  We must NOT capture lastHitGroup() here
        # because show() runs after the original menu-callback context has
        # exited, so lastHitGroup() would return root.
        hit_group = self._hit_group or nuke.root()
        with hit_group:
            items = [
                {
                    'menuobj': anchor_node,
                    'menupath': 'Anchors/' + anchor_display_name(anchor_node),
                }
                for anchor_node in all_anchors()
            ]
            for backdrop_node in nuke.allNodes('BackdropNode'):
                label = backdrop_node['label'].value().strip()
                if label:
                    items.append({
                        'menuobj': backdrop_node,
                        'menupath': 'Backdrops/' + label,
                    })
        return items

    def get_weights_file(self):
        return os.path.expanduser('~/.nuke/anchors_anchor_navigate_weights.json')

    def invoke(self, thing):
        node = thing['menuobj']
        hit_group = self._hit_group or nuke.root()

        def _deferred_navigate():
            with hit_group:
                if not nuke.exists(node.name()):
                    return
                _save_dag_position()
                if node.Class() == 'BackdropNode':
                    navigate_to_backdrop(node)
                    return
                navigate_to_anchor(node)

        # Defer navigation until after the picker widget closes and Qt
        # restores focus to the DAG panel.  nuke.zoom() targets whichever
        # panel has Qt focus, so calling it while the picker is still open
        # would zoom the wrong panel (or do nothing).
        QtCore.QTimer.singleShot(0, _deferred_navigate)

    def get_icon(self, menuobj):
        return None

    def get_color(self, menuobj):
        color_int = menuobj['tile_color'].value()  # 0xRRGGBBAA — reads what was actually set
        r = (color_int >> 24) & 0xFF
        g = (color_int >> 16) & 0xFF
        b = (color_int >> 8) & 0xFF
        color = QtGui.QColor(r, g, b)
        return (color, color)


_anchor_navigate_widget = None
_back_position = None  # (zoom_level, center_xy) tuple or None — session-only back-navigation slot


def select_anchor_and_navigate():
    if not prefs.plugin_enabled:
        return
    if QtWidgets is None:
        return
    hit_group = nuke.lastHitGroup()
    with hit_group:
        labelled_backdrops = [
            bd for bd in nuke.allNodes('BackdropNode')
            if bd['label'].value().strip()
        ]
        if not all_anchors() and not labelled_backdrops:
            return
    global _anchor_navigate_widget
    if _anchor_navigate_widget is not None:
        try:
            _anchor_navigate_widget.plugin._hit_group = hit_group
            _anchor_navigate_widget.under_cursor()
            _anchor_navigate_widget.show()
            _anchor_navigate_widget.raise_()
            return
        except RuntimeError:
            _anchor_navigate_widget = None
    plugin = AnchorNavigatePlugin()
    plugin._hit_group = hit_group
    _anchor_navigate_widget = _tabtabtab.TabTabTabWidget(
        plugin, winflags=Qt.FramelessWindowHint
    )
    _anchor_navigate_widget.under_cursor()
    _anchor_navigate_widget.show()
    _anchor_navigate_widget.raise_()
