"""Documentation-only Nuke startup hooks for GUI screenshot capture.

This file is placed on ``NUKE_PATH`` *only* while nuke-docs-screenshotter is
generating the documentation images (see the Makefile ``gui-shots`` target). It
is never part of the shipped plugin and never loaded by ordinary users.

It does two things, both purely to support deterministic playback capture:

1. Loads the ``docs/examples-workflows.nk`` example comp into the start-up
   session so the anchor pickers (``A`` / ``Alt+A``) list the guide's real
   example anchors and coloured backdrops, keeping the picker screenshots in
   step with the narrative that references them.
2. Registers menu commands — each on a dedicated keyboard shortcut — that show
   the otherwise-modal anchor dialogs *non-modally* (``.show()`` instead of
   ``.exec_()``). A modal ``.exec_()`` would block the playback engine's event
   loop, so the screenshotter could never reach the screenshot step; showing the
   same dialog non-modally lets playback capture it by class name.

The dialog widgets are kept alive in a module-level list so Qt does not garbage
collect them the moment the creating function returns.
"""

import os
import sys

import nuke

# Make the anchors plugin modules importable regardless of NUKE_PATH ordering.
# This file lives at <repo>/docs/screenshots/nuke_path/menu.py, so the repo root
# is three directories up.
_THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
_REPOSITORY_ROOT = os.path.abspath(
    os.path.join(_THIS_DIRECTORY, os.pardir, os.pardir, os.pardir)
)
if _REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, _REPOSITORY_ROOT)

# Keep references to shown dialogs so they are not garbage collected.
_live_dialogs = []


def _load_example_script():
    """Open the workflows example comp so the pickers list real example content."""
    import prefs

    prefs.plugin_enabled = True

    example_script = os.path.join(
        _REPOSITORY_ROOT, "docs", "examples-workflows.nk"
    )
    nuke.scriptClear()
    nuke.scriptReadFile(example_script)

    # Drop the nuke-docs-screenshotter marker backdrops ("screenshot: ...") so the
    # navigation picker lists only the comp's real anchors and coloured backdrops
    # rather than the capture-region markers.
    for backdrop in nuke.allNodes("BackdropNode"):
        label = backdrop["label"].value()
        if isinstance(label, str) and label.startswith("screenshot:"):
            nuke.delete(backdrop)

    # Leave nothing selected so pressing ``A`` opens the link picker rather than
    # the (modal) create-anchor prompt, which would block the playback engine.
    for selected_node in nuke.selectedNodes():
        selected_node.setSelected(False)


def _show_color_palette():
    """Show the colour palette dialog (set-colour variant) non-modally."""
    import colors
    import prefs

    if colors.ColorPaletteDialog is None:
        return
    dialog = colors.ColorPaletteDialog(
        initial_color=0x3399FFFF,
        show_name_field=False,
        custom_colors=prefs.custom_colors,
    )
    dialog.setWindowTitle("Set Anchor Colour")
    _live_dialogs.append(dialog)
    dialog.show()


def _show_create_dialog():
    """Show the create-anchor dialog (name + colour) non-modally."""
    import colors
    import prefs

    if colors.ColorPaletteDialog is None:
        return
    dialog = colors.ColorPaletteDialog(
        initial_color=0x6F3399FF,
        show_name_field=True,
        initial_name="BG_Plate",
        custom_colors=prefs.custom_colors,
    )
    dialog.setWindowTitle("Create Anchor")
    _live_dialogs.append(dialog)
    dialog.show()


def _register_doc_commands():
    """Register the documentation capture commands with stable shortcuts."""
    docs_menu = nuke.menu("Nuke").addMenu("DocsCapture")
    docs_menu.addCommand("Show Colour Palette", _show_color_palette, "F6")
    docs_menu.addCommand("Show Create Dialog", _show_create_dialog, "F7")


if nuke.GUI:
    _load_example_script()
    _register_doc_commands()
