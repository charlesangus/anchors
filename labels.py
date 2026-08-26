"""User-facing label helper functions for anchor, link, and backdrop nodes."""

import nuke

try:
    if hasattr(nuke, 'NUKE_VERSION_MAJOR') and nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtWidgets
    else:
        from PySide2 import QtWidgets
except ImportError:
    QtWidgets = None

import prefs
from colors import BackdropDialog
from constants import (
    BACKDROP_APPEARANCE_BORDER,
    BACKDROP_APPEARANCE_FILLED,
    BACKDROP_APPEARANCE_KNOB_NAME,
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


def _prompt_and_label(prompt, default_supplier, applier):
    """Common preamble for label-shortcut commands.

    `prompt` is the dialog message. `default_supplier` is a callable taking the
    selected node and returning the default text shown in the dialog (this lets
    `append_to_label` use a different default from the create_*_label commands).
    `applier` is called as `applier(node, text)` once a non-None text is captured.
    """
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    node = selected_nodes[0]
    default = default_supplier(node)
    text = nuke.getInput(prompt, default)
    if text is None:
        return
    applier(node, text)


def create_large_label():
    """Prompt for a label and apply it with large font sizing."""
    def applier(node, text):
        _apply_label(node, text, DOT_LABEL_FONT_SIZE_LARGE, NODE_LABEL_FONT_SIZE_LARGE)
    _prompt_and_label("Label:", lambda node: node['label'].getText(), applier)


def create_medium_label():
    """Prompt for a label and apply it; Dot nodes get medium font size, others unchanged."""
    def applier(node, text):
        _apply_label(node, text, DOT_LABEL_FONT_SIZE_MEDIUM, None)
    _prompt_and_label("Label:", lambda node: node['label'].getText(), applier)


def create_small_label():
    """Prompt for a label and apply it; Dot nodes get small font size (33), others unchanged."""
    def applier(node, text):
        _apply_label(node, text, DOT_LABEL_FONT_SIZE_SMALL, None)
    _prompt_and_label("Label:", lambda node: node['label'].getText(), applier)


def append_to_label():
    """Prompt for a suffix and append it to the node's existing label."""
    def applier(node, text):
        _apply_label(node, node['label'].getText() + text)
    _prompt_and_label("Append to label:", lambda node: "", applier)


# ---------------------------------------------------------------------------
# Backdrop setup (issue #68)
# ---------------------------------------------------------------------------

def is_backdrop(node):
    """True if *node* is a BackdropNode."""
    return node.Class() == 'BackdropNode'


def backdrop_is_filled(backdrop_node):
    """True if *backdrop_node* currently draws filled rather than as an outline.

    Nuke gained the ``appearance`` knob in Nuke 11; older backdrops are always
    drawn filled, so they report True.
    """
    if BACKDROP_APPEARANCE_KNOB_NAME not in backdrop_node.knobs():
        return True
    return backdrop_node[BACKDROP_APPEARANCE_KNOB_NAME].value() == BACKDROP_APPEARANCE_FILLED


def apply_backdrop_setup(backdrop_node, label_text=None, font_size=None,
                         filled=None, color=None):
    """Apply the backdrop dialog's results to *backdrop_node*.

    Every attribute is optional: ``None`` leaves that aspect of the backdrop
    untouched, so callers can set just a label (the no-Qt fallback below) or the
    full set.  ``filled`` maps onto Nuke's ``appearance`` knob and is ignored on
    Nuke versions that predate it.
    """
    if label_text is not None:
        backdrop_node['label'].setValue(label_text)
    if font_size is not None:
        backdrop_node['note_font_size'].setValue(font_size)
    if color is not None:
        backdrop_node['tile_color'].setValue(color)
    if filled is not None and BACKDROP_APPEARANCE_KNOB_NAME in backdrop_node.knobs():
        appearance = BACKDROP_APPEARANCE_FILLED if filled else BACKDROP_APPEARANCE_BORDER
        backdrop_node[BACKDROP_APPEARANCE_KNOB_NAME].setValue(appearance)


def setup_backdrop(backdrop_node):
    """Open the backdrop setup dialog and apply what the user chose.

    Silent no-op when the plugin is disabled or the dialog is cancelled.  With Qt
    unavailable the dialog cannot be built, so this falls back to a plain label
    prompt and leaves the backdrop's colour, font size, and appearance alone.
    """
    if not prefs.plugin_enabled:
        return
    current_label = backdrop_node['label'].getValue()

    if BackdropDialog is None or QtWidgets is None:
        label_text = nuke.getInput("Backdrop label:", current_label)
        if label_text is None:
            return
        apply_backdrop_setup(backdrop_node, label_text=label_text)
        return

    dialog = BackdropDialog(
        initial_label=current_label,
        initial_color=int(backdrop_node['tile_color'].value()),
        initial_font_size=int(backdrop_node['note_font_size'].value()),
        initial_filled=backdrop_is_filled(backdrop_node),
        custom_colors=prefs.custom_colors,
    )
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    prefs.persist_custom_colors_from_dialog(dialog)
    apply_backdrop_setup(
        backdrop_node,
        label_text=dialog.chosen_name,
        font_size=dialog.chosen_font_size,
        filled=dialog.chosen_filled,
        color=dialog.selected_color_int(),
    )


def setup_selected_backdrop():
    """Open the backdrop setup dialog for the selected backdrop.

    Does nothing unless the selection is exactly one BackdropNode — the same
    single-node rule the ``A`` shortcut uses.
    """
    if not prefs.plugin_enabled:
        return
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) == 1 and is_backdrop(selected_nodes[0]):
        setup_backdrop(selected_nodes[0])
