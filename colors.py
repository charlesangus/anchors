"""Color palette dialog for the anchor color system."""

import nuke

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
    Qt = None

# ---------------------------------------------------------------------------
# Non-Qt helpers — always available
# ---------------------------------------------------------------------------

def _get_nuke_pref_colors():
    """Return list of color ints from Nuke's Edit > Preferences > Colors.

    Returns an empty list when called outside a Nuke session.
    """
    prefs = nuke.toNode("preferences")
    if prefs is None:
        return []
    colors = []
    for knob_name in prefs.knobs():
        if knob_name.startswith("NodeColourChoice"):
            val = prefs[knob_name].value()
            if val and val != 0:
                colors.append(int(val))
    return colors


def _get_script_backdrop_colors():
    """Return list of unique backdrop tile_color ints from the current script.

    Returns an empty list when called outside a Nuke session.
    """
    seen = set()
    colors = []
    for backdrop_node in nuke.allNodes('BackdropNode'):
        color = backdrop_node['tile_color'].value()
        if color and color not in seen:
            seen.add(color)
            colors.append(color)
    return colors


# ---------------------------------------------------------------------------
# Qt color palette dialog — only defined when Qt is available
# ---------------------------------------------------------------------------

def _color_int_to_rgb(color_int):
    """Unpack a 0xRRGGBBAA int into (r, g, b) tuple."""
    red = (color_int >> 24) & 0xFF
    green = (color_int >> 16) & 0xFF
    blue = (color_int >> 8) & 0xFF
    return red, green, blue


if QtWidgets is None:
    ColorPaletteDialog = None
    PrefsDialog = None
else:
    # Column addresses: 1-9, 0 (10 columns max)
    _COLUMN_KEYS = '1234567890'
    # Row addresses: a-z (26 rows max)
    _ROW_KEYS = 'abcdefghijklmnopqrstuvwxyz'
    _SWATCHES_PER_ROW = 8

    class ColorPaletteDialog(QtWidgets.QDialog):
        """Color palette dialog showing swatches from Nuke prefs, backdrop colors, and user palette.

        Parameters
        ----------
        initial_color : int or None
            0xRRGGBBAA color int to pre-highlight on open.
        show_name_field : bool
            If True, shows a name QLineEdit at the top (for creation/rename dialogs).
        initial_name : str
            Pre-filled value for the name field (only relevant when show_name_field=True).
        custom_colors : list of int or None
            User-defined palette colors injected by the caller (e.g. from prefs.custom_colors).
            Defaults to an empty list if not provided.
        parent : QWidget or None
            Parent widget.
        """

        def __init__(self, initial_color=None, show_name_field=False,
                     initial_name="", custom_colors=None, parent=None):
            super().__init__(parent)

            self._selected_color = initial_color
            self._hint_mode = False
            self._hint_row = None  # stores logical row index after letter keypress
            self._swatch_cells = []  # list of (group_col, logical_row, color_int, button)
            self.chosen_name = initial_name
            self._custom_colors = custom_colors if custom_colors is not None else []
            # Dialog-local working copy for staging newly added custom colors.
            # On accept, callers read this via chosen_custom_colors().
            # On reject, staged colors are discarded (never written to prefs).
            self._staged_custom_colors = list(self._custom_colors)

            # Map from (col_index, row_index) to button for hint navigation
            self._cell_map = {}

            self._build_ui(show_name_field, initial_name)

        def _build_ui(self, show_name_field, initial_name):
            self.setWindowTitle("Color Palette")
            outer_layout = QtWidgets.QVBoxLayout()
            self.setLayout(outer_layout)

            # Optional name field at top
            self._name_edit = None
            if show_name_field:
                self._name_edit = QtWidgets.QLineEdit(initial_name)
                outer_layout.addWidget(self._name_edit)

            # Swatch grid
            grid_widget = QtWidgets.QWidget()
            self._grid_layout = QtWidgets.QGridLayout()
            self._grid_layout.setSpacing(2)
            grid_widget.setLayout(self._grid_layout)
            outer_layout.addWidget(grid_widget)

            # Collect all color sources
            nuke_pref_colors = _get_nuke_pref_colors()
            backdrop_colors = _get_script_backdrop_colors()
            user_palette_colors = self._custom_colors

            # Order: custom colors first, then backdrop colors, then Nuke defaults.
            # This matches PICKER-04: user's own colors appear at the top.
            # Each group is paired with a human-readable label shown above its swatches.
            _GROUP_LABELS = {
                id(user_palette_colors): "Custom Colors",
                id(backdrop_colors): "Backdrop Colors",
                id(nuke_pref_colors): "Nuke Defaults",
            }
            all_color_groups = [
                group for group in [user_palette_colors, backdrop_colors, nuke_pref_colors]
                if group
            ]

            grid_row = 0
            # logical_row counts only rows of swatches, ignoring section-label rows.
            # This ensures hint-mode row letters always start at 'a' for the first
            # swatch row regardless of how many label rows appear above it.
            logical_row = 0

            # Initialise the custom colors next-slot tracker.  If
            # user_palette_colors is non-empty, it will be the first group in
            # all_color_groups and we update these counters after that group.
            # If user_palette_colors is empty (filtered out by `if group`), we
            # pre-set them to (0, 0) so dynamically appended swatches start at
            # the top of the grid — before all other groups.
            self._custom_group_next_col = 0
            self._custom_group_next_row = 0
            self._custom_group_next_logical_row = 0
            custom_group_tracker_set = False

            for color_group in all_color_groups:
                # Section label spanning all swatch columns
                group_label_text = _GROUP_LABELS.get(id(color_group), "")
                if group_label_text:
                    section_label = QtWidgets.QLabel(group_label_text)
                    section_label.setFocusPolicy(Qt.NoFocus)
                    self._grid_layout.addWidget(
                        section_label, grid_row, 0, 1, _SWATCHES_PER_ROW
                    )
                    grid_row += 1
                    # logical_row does NOT increment for label rows

                group_col = 0
                for color_int in color_group:
                    button = QtWidgets.QPushButton()
                    button.setFixedSize(24, 24)
                    button.setFocusPolicy(Qt.NoFocus)
                    # Prevent button from intercepting Enter key — dialog-level
                    # keyPressEvent handles Enter to confirm swatch selection.
                    button.setAutoDefault(False)

                    red, green, blue = _color_int_to_rgb(color_int)
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 1px solid #555; "
                        "border-radius: 2px;"
                    )

                    # Pre-highlight is applied after all groups are built via
                    # _refresh_swatch_borders(), which uses the palette Highlight
                    # color.  The initial stylesheet here is the default (no
                    # selection) — _refresh_swatch_borders() corrects it at the
                    # end of _build_ui.

                    color_to_capture = color_int
                    button.clicked.connect(
                        lambda checked=False, c=color_to_capture: self._on_swatch_clicked(c)
                    )

                    self._grid_layout.addWidget(button, grid_row, group_col)
                    cell = (group_col, logical_row, color_int, button)
                    self._swatch_cells.append(cell)
                    self._cell_map[(group_col, logical_row)] = (color_int, button)

                    group_col += 1
                    if group_col >= _SWATCHES_PER_ROW:
                        group_col = 0
                        grid_row += 1
                        logical_row += 1

                if not custom_group_tracker_set and color_group is user_palette_colors:
                    # Record the next available slot in the custom colors group
                    # for dynamic swatch appending via _append_swatch_to_custom_group.
                    self._custom_group_next_col = group_col
                    self._custom_group_next_row = grid_row
                    self._custom_group_next_logical_row = logical_row
                    custom_group_tracker_set = True

                # Move to next group row (creates a blank-row gap between groups)
                if group_col > 0:
                    grid_row += 1
                    logical_row += 1

            # "Custom Color..." button — opens nuke.getColor(), stages result
            custom_button = QtWidgets.QPushButton("Custom Color...")
            custom_button.setFocusPolicy(Qt.NoFocus)
            custom_button.setAutoDefault(False)
            custom_button.clicked.connect(self._on_custom_color_clicked)
            outer_layout.addWidget(custom_button)

            # Cancel / OK buttons side by side — Cancel on left, OK on right,
            # matching Nuke's native dialog convention (positive action on the right).
            cancel_button = QtWidgets.QPushButton("Cancel")
            cancel_button.setFocusPolicy(Qt.NoFocus)
            cancel_button.setAutoDefault(False)
            cancel_button.clicked.connect(self.reject)

            ok_button = QtWidgets.QPushButton("OK")
            ok_button.setFocusPolicy(Qt.NoFocus)
            ok_button.setAutoDefault(False)
            ok_button.clicked.connect(self.accept)

            ok_cancel_layout = QtWidgets.QHBoxLayout()
            ok_cancel_layout.addWidget(ok_button)      # OK on left
            ok_cancel_layout.addWidget(cancel_button)  # Cancel on right
            outer_layout.addLayout(ok_cancel_layout)

            # Apply pre-highlight using palette Highlight color now that all
            # swatch cells are populated and the widget has a palette context.
            self._refresh_swatch_borders()

        def accept(self):
            if self._name_edit is not None:
                self.chosen_name = self._name_edit.text()
            super().accept()

        def _on_swatch_clicked(self, color_int):
            self._selected_color = color_int
            self._refresh_swatch_borders()
            self.accept()

        def _highlight_color_name(self):
            """Return the CSS color name to use for the selected swatch border.

            Uses the widget's QPalette Highlight color so the selection indicator
            matches the user's Qt theme, rather than a hardcoded white.
            """
            highlight_qcolor = self.palette().color(QtGui.QPalette.Highlight)
            return highlight_qcolor.name()

        def _refresh_swatch_borders(self):
            """Re-apply swatch border stylesheets: palette Highlight border for selected,
            default for others.

            Uses `is not None` comparison for the selected color so that color
            int 0 (black) is recognised correctly — `if not self._selected_color`
            would incorrectly treat 0 as unselected.
            """
            highlight_color = self._highlight_color_name()
            for _group_col, _logical_row, color_int, button in self._swatch_cells:
                red, green, blue = _color_int_to_rgb(color_int)
                if self._selected_color is not None and color_int == self._selected_color:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        f"border: 2px solid {highlight_color}; "
                        "border-radius: 2px;"
                    )
                else:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 1px solid #555; "
                        "border-radius: 2px;"
                    )

        def _on_custom_color_clicked(self):
            result = nuke.getColor()
            if result == 0:
                # nuke.getColor() returns 0 for both cancel and pure black;
                # treat 0 as cancel (known Nuke API limitation).
                return
            self._staged_custom_colors.append(result)
            self._selected_color = result
            self._append_swatch_to_custom_group(result)
            self._refresh_swatch_borders()
            self.accept()

        def selected_color_int(self):
            """Return the selected color as a 0xRRGGBBAA int, or None if cancelled."""
            return self._selected_color

        def showEvent(self, event):
            """Install an application-level event filter so keyboard shortcuts
            (Tab hint mode, Enter, Escape) work even when a child widget such as
            the name QLineEdit holds keyboard focus.
            """
            super().showEvent(event)
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.installEventFilter(self)

        def hideEvent(self, event):
            """Remove the application-level event filter when the dialog hides."""
            super().hideEvent(event)
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)

        def eventFilter(self, obj, event):  # noqa: C901  # complexity is inherent to Qt event dispatch logic
            """Intercept keys at the QApplication level so they reach the dialog
            even when a child widget (e.g. QLineEdit) has focus.
            """
            if event.type() != QtCore.QEvent.KeyPress:
                return False
            key = event.key()

            # Tab toggles hint mode regardless of which child has focus.
            if key == Qt.Key_Tab:
                self._hint_mode = not self._hint_mode
                self._hint_row = None
                self._update_hint_overlays()
                return True

            # Escape closes the dialog.
            if key == Qt.Key_Escape:
                self.reject()
                return True

            # Enter/Return confirms the current selection.
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if self._selected_color is not None:
                    self.accept()
                return True

            # In hint mode, route alphanumeric keys to the navigation handler.
            if self._hint_mode:
                key_text = event.text().lower()
                if key_text in _ROW_KEYS and self._hint_row is None:
                    self._hint_row = _ROW_KEYS.index(key_text)
                    self._highlight_hint_row(self._hint_row)
                    return True
                if key_text in _COLUMN_KEYS and self._hint_row is not None:
                    col_index = _COLUMN_KEYS.index(key_text)
                    target_cell = self._cell_map.get((col_index, self._hint_row))
                    if target_cell is not None:
                        color_int, button = target_cell
                        self._selected_color = color_int
                        self.accept()
                    self._hint_row = None
                    return True
                return True  # consume unknown keys in hint mode

            return False

        def keyPressEvent(self, event):  # noqa: C901  # complexity is inherent to Qt swatch rendering logic
            key_text = event.text().lower()

            if event.key() == Qt.Key_Escape:
                event.accept()
                self.reject()
                return

            if event.key() == Qt.Key_Tab:
                self._hint_mode = not self._hint_mode
                self._hint_row = None
                self._update_hint_overlays()
                event.accept()
                return

            # Enter confirms the current selection regardless of hint mode.
            # Must be checked BEFORE the hint-mode block so it works in both modes.
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self._selected_color is not None:
                    self.accept()
                event.accept()
                return

            if self._hint_mode:
                # First keypress: letter selects the row
                if key_text in _ROW_KEYS and self._hint_row is None:
                    self._hint_row = _ROW_KEYS.index(key_text)
                    self._highlight_hint_row(self._hint_row)
                    event.accept()
                    return

                # Second keypress: number selects the column and confirms
                if key_text in _COLUMN_KEYS and self._hint_row is not None:
                    col_index = _COLUMN_KEYS.index(key_text)
                    target_cell = self._cell_map.get((col_index, self._hint_row))
                    if target_cell is not None:
                        color_int, button = target_cell
                        self._selected_color = color_int
                        self.accept()
                    self._hint_row = None
                    event.accept()
                    return

                event.accept()
                return

            super().keyPressEvent(event)

        def _update_hint_overlays(self):
            """Show or hide row/column address labels on swatches in hint mode.

            Display format is "{row_letter}{col_number}" e.g. "a1", "a2", "b1".
            Letter-first matches the two-keypress navigation order: letter (row)
            then number (column).
            """
            for group_col, logical_row, _color_int, button in self._swatch_cells:
                if self._hint_mode:
                    row_label = _ROW_KEYS[logical_row] if logical_row < len(_ROW_KEYS) else '?'
                    col_label = _COLUMN_KEYS[group_col] if group_col < len(_COLUMN_KEYS) else '?'
                    button.setText(f"{row_label}{col_label}")  # letter-number: "a1", "b2"
                else:
                    button.setText("")

        def _highlight_hint_column(self, column_index):
            """Highlight swatches in the given column when column key pressed in hint mode."""
            for group_col, _logical_row, color_int, button in self._swatch_cells:
                red, green, blue = _color_int_to_rgb(color_int)
                if group_col == column_index:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 2px solid yellow; "
                        "border-radius: 2px;"
                    )
                else:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 1px solid #555; "
                        "border-radius: 2px;"
                    )

        def _highlight_hint_row(self, row_index):
            """Highlight swatches in the given logical row when row letter pressed in hint mode."""
            for _group_col, logical_row, color_int, button in self._swatch_cells:
                red, green, blue = _color_int_to_rgb(color_int)
                if logical_row == row_index:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 2px solid yellow; "
                        "border-radius: 2px;"
                    )
                else:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 1px solid #555; "
                        "border-radius: 2px;"
                    )

        def _append_swatch_to_custom_group(self, color_int):
            """Add a new swatch button to the custom colors group at the next available slot.

            Called by _on_custom_color_clicked to dynamically grow the custom
            colors section of the grid without rebuilding the entire dialog.
            Updates self._swatch_cells and self._cell_map so hint mode keeps
            working correctly.
            """
            button = QtWidgets.QPushButton()
            button.setFixedSize(24, 24)
            button.setFocusPolicy(Qt.NoFocus)
            button.setAutoDefault(False)

            red, green, blue = _color_int_to_rgb(color_int)
            button.setStyleSheet(
                f"background-color: rgb({red},{green},{blue}); "
                "border: 1px solid #555; "
                "border-radius: 2px;"
            )

            color_to_capture = color_int
            button.clicked.connect(
                lambda checked=False, c=color_to_capture: self._on_swatch_clicked(c)
            )

            self._grid_layout.addWidget(
                button,
                self._custom_group_next_row,
                self._custom_group_next_col,
            )
            cell = (
                self._custom_group_next_col, self._custom_group_next_logical_row, color_int, button
            )
            self._swatch_cells.append(cell)
            self._cell_map[(self._custom_group_next_col, self._custom_group_next_logical_row)] = (
                color_int, button
            )

            # Advance column counter; wrap to the next row at _SWATCHES_PER_ROW
            self._custom_group_next_col += 1
            if self._custom_group_next_col >= _SWATCHES_PER_ROW:
                self._custom_group_next_col = 0
                self._custom_group_next_row += 1
                self._custom_group_next_logical_row += 1

        def chosen_custom_colors(self):
            """Return a copy of the staged custom colors list.

            This list includes both the original custom_colors passed in at
            construction AND any colors added via "Custom Color..." during this
            session.  Returns a copy so the caller cannot mutate internal state.

            Callers should only persist this list when the dialog was accepted
            (dialog.result() == QDialog.Accepted).  On reject, the staged colors
            are discarded by not calling this method.
            """
            return list(self._staged_custom_colors)

    class PrefsDialog(QtWidgets.QDialog):
        """Preferences dialog for managing plugin settings and custom colors.

        Seeds local working copies of preferences at open time. Mutates
        prefs module variables only on OK (via _on_accept). Cancel leaves
        prefs module variables unchanged.
        """

        def __init__(self, parent=None):
            super().__init__(parent)
            import prefs as prefs_module
            # Seed local working copies — never mutate prefs module vars until accept
            self._local_plugin_enabled = prefs_module.plugin_enabled
            self._local_link_mode = prefs_module.link_classes_paste_mode
            self._local_custom_colors = list(prefs_module.custom_colors)
            # Snapshot of custom colors at open time so _on_accept can detect changes
            # and recolor any anchor nodes using the old color values.
            self._original_custom_colors = list(prefs_module.custom_colors)
            self._selected_swatch_index = None  # index into _local_custom_colors
            self._swatch_buttons = []  # parallel list of QPushButton refs
            self._local_naming_regex = prefs_module.naming_regex
            self._local_naming_template = prefs_module.naming_template
            self._local_naming_demo_filename = prefs_module.naming_demo_filename
            self._build_ui()

        def _build_ui(self):
            self.setWindowTitle("Preferences")
            outer_layout = QtWidgets.QVBoxLayout()
            self.setLayout(outer_layout)

            # Checkbox: plugin enabled
            self._plugin_checkbox = QtWidgets.QCheckBox("Enable anchors plugin")
            self._plugin_checkbox.setChecked(self._local_plugin_enabled)
            outer_layout.addWidget(self._plugin_checkbox)

            # Checkbox: link classes paste mode
            self._link_mode_checkbox = QtWidgets.QCheckBox("Input nodes paste as links")
            self._link_mode_checkbox.setChecked(self._local_link_mode == "create_link")
            outer_layout.addWidget(self._link_mode_checkbox)

            # ---- Anchor Naming section ----
            naming_section_label = QtWidgets.QLabel("Anchor Naming")
            naming_section_label.setFocusPolicy(Qt.NoFocus)
            outer_layout.addWidget(naming_section_label)

            # Regex field row
            naming_regex_row_layout = QtWidgets.QHBoxLayout()
            naming_regex_label = QtWidgets.QLabel("Regex:")
            naming_regex_label.setFocusPolicy(Qt.NoFocus)
            self._naming_regex_edit = QtWidgets.QLineEdit()
            self._naming_regex_edit.setText(self._local_naming_regex)
            self._naming_regex_edit.setPlaceholderText("e.g. (?P<shot>.+)_v\\d+")
            naming_regex_row_layout.addWidget(naming_regex_label)
            naming_regex_row_layout.addWidget(self._naming_regex_edit)
            outer_layout.addLayout(naming_regex_row_layout)

            # Template field row
            naming_template_row_layout = QtWidgets.QHBoxLayout()
            naming_template_label = QtWidgets.QLabel("Template:")
            naming_template_label.setFocusPolicy(Qt.NoFocus)
            self._naming_template_edit = QtWidgets.QLineEdit()
            self._naming_template_edit.setText(self._local_naming_template)
            self._naming_template_edit.setPlaceholderText("e.g. {shot}_anchor  (blank = use full match)")
            naming_template_row_layout.addWidget(naming_template_label)
            naming_template_row_layout.addWidget(self._naming_template_edit)
            outer_layout.addLayout(naming_template_row_layout)

            # Test filename row + validity indicator + Reset button
            naming_test_row_layout = QtWidgets.QHBoxLayout()
            naming_test_label = QtWidgets.QLabel("Test filename:")
            naming_test_label.setFocusPolicy(Qt.NoFocus)
            self._naming_test_filename_edit = QtWidgets.QLineEdit()
            self._naming_test_filename_edit.setText(self._local_naming_demo_filename)
            self._naming_validity_label = QtWidgets.QLabel("")
            self._naming_validity_label.setFocusPolicy(Qt.NoFocus)
            naming_reset_button = QtWidgets.QPushButton("Reset")
            naming_reset_button.setAutoDefault(False)
            naming_reset_button.clicked.connect(self._on_reset_naming)
            naming_test_row_layout.addWidget(naming_test_label)
            naming_test_row_layout.addWidget(self._naming_test_filename_edit)
            naming_test_row_layout.addWidget(self._naming_validity_label)
            naming_test_row_layout.addWidget(naming_reset_button)
            outer_layout.addLayout(naming_test_row_layout)

            # Preview row — shows the rendered anchor name from regex+template applied to test filename
            naming_preview_row_layout = QtWidgets.QHBoxLayout()
            naming_preview_description_label = QtWidgets.QLabel("Preview:")
            naming_preview_description_label.setFocusPolicy(Qt.NoFocus)
            self._naming_preview_label = QtWidgets.QLabel("")
            self._naming_preview_label.setFocusPolicy(Qt.NoFocus)
            naming_preview_row_layout.addWidget(naming_preview_description_label)
            naming_preview_row_layout.addWidget(self._naming_preview_label)
            naming_preview_row_layout.addStretch()
            outer_layout.addLayout(naming_preview_row_layout)

            # Wire live validity indicator to all three text fields (template changes affect preview)
            self._naming_regex_edit.textChanged.connect(self._update_naming_validity_indicator)
            self._naming_template_edit.textChanged.connect(self._update_naming_validity_indicator)
            self._naming_test_filename_edit.textChanged.connect(self._update_naming_validity_indicator)
            # Initial indicator state
            self._update_naming_validity_indicator()

            # Horizontal separator
            separator_top = QtWidgets.QFrame()
            separator_top.setFrameShape(QtWidgets.QFrame.HLine)
            separator_top.setFrameShadow(QtWidgets.QFrame.Sunken)
            separator_top.setFocusPolicy(Qt.NoFocus)
            outer_layout.addWidget(separator_top)

            # Label: Custom Colors
            custom_colors_label = QtWidgets.QLabel("Custom Colors")
            custom_colors_label.setFocusPolicy(Qt.NoFocus)
            outer_layout.addWidget(custom_colors_label)

            # Add/Edit/Remove buttons — created BEFORE _populate_swatch_grid so that
            # _update_edit_remove_buttons (called inside _populate_swatch_grid) can
            # reference self._edit_button and self._remove_button without AttributeError.
            button_row_layout = QtWidgets.QHBoxLayout()
            self._add_button = QtWidgets.QPushButton("Add")
            self._add_button.setAutoDefault(False)
            self._edit_button = QtWidgets.QPushButton("Edit")
            self._edit_button.setAutoDefault(False)
            self._remove_button = QtWidgets.QPushButton("Remove")
            self._remove_button.setAutoDefault(False)
            button_row_layout.addWidget(self._add_button)
            button_row_layout.addWidget(self._edit_button)
            button_row_layout.addWidget(self._remove_button)
            button_row_layout.addStretch()
            self._add_button.clicked.connect(self._on_add_color)
            self._edit_button.clicked.connect(self._on_edit_color)
            self._remove_button.clicked.connect(self._on_remove_color)

            # Swatch grid widget — the container itself must not grab focus;
            # only the swatch buttons inside it participate in the tab chain.
            self._swatch_grid_widget = QtWidgets.QWidget()
            self._swatch_grid_widget.setFocusPolicy(Qt.NoFocus)
            self._swatch_grid_layout = QtWidgets.QGridLayout()
            self._swatch_grid_layout.setSpacing(2)
            self._swatch_grid_widget.setLayout(self._swatch_grid_layout)
            outer_layout.addWidget(self._swatch_grid_widget)
            self._populate_swatch_grid()

            outer_layout.addLayout(button_row_layout)

            # Horizontal separator
            separator_bottom = QtWidgets.QFrame()
            separator_bottom.setFrameShape(QtWidgets.QFrame.HLine)
            separator_bottom.setFrameShadow(QtWidgets.QFrame.Sunken)
            separator_bottom.setFocusPolicy(Qt.NoFocus)
            outer_layout.addWidget(separator_bottom)

            # Establish explicit tab order so swatch buttons are reachable via Tab.
            self._update_swatch_tab_order()

            # Cancel / OK buttons in a horizontal row — Cancel on the left, OK on
            # the right, matching Nuke's native dialog convention (positive action
            # on the right).
            # setAutoDefault(False) prevents Enter from accidentally triggering a
            # button click instead of the dialog-level keyPressEvent.
            ok_cancel_row_layout = QtWidgets.QHBoxLayout()
            self._cancel_button = QtWidgets.QPushButton("Cancel")
            self._cancel_button.setAutoDefault(False)
            self._cancel_button.clicked.connect(self.reject)
            self._ok_button = QtWidgets.QPushButton("OK")
            self._ok_button.setAutoDefault(False)
            self._ok_button.clicked.connect(self._on_accept)
            ok_cancel_row_layout.addWidget(self._cancel_button)  # Cancel on left
            ok_cancel_row_layout.addWidget(self._ok_button)      # OK on right
            outer_layout.addLayout(ok_cancel_row_layout)

        def _on_reset_naming(self):
            """Clear the regex and template fields, restoring hardcoded fallback behavior."""
            self._naming_regex_edit.setText("")
            self._naming_template_edit.setText("")
            # Test filename field is intentionally not cleared

        def _update_naming_validity_indicator(self):
            """Update the validity label and rendered preview based on current field values.

            Validity label:
              Green 'Match' — regex compiles and matches the test filename.
              Red 'No match' — regex compiles but does not match.
              Red 'Invalid regex' — regex does not compile.
              Blank — regex field is empty.

            Preview label:
              Shows the anchor name that would be generated (template substituted).
              Blank when regex is empty, invalid, or does not match.
            """
            import re as re_module
            _FRAME_TOKEN_PATTERN = re_module.compile(r'[._]?(?:%0?\d*d|#{1,}|%[Vv])')
            regex_text = self._naming_regex_edit.text()
            template_text = self._naming_template_edit.text()
            test_filename = self._naming_test_filename_edit.text()
            stripped_filename = _FRAME_TOKEN_PATTERN.sub('', test_filename)

            if not regex_text:
                self._naming_validity_label.setText("")
                self._naming_validity_label.setStyleSheet("")
                self._naming_preview_label.setText("")
                return
            try:
                compiled_pattern = re_module.compile(regex_text)
            except re_module.error:
                self._naming_validity_label.setText("Invalid regex")
                self._naming_validity_label.setStyleSheet("color: red;")
                self._naming_preview_label.setText("")
                return
            regex_match = compiled_pattern.match(stripped_filename)
            if regex_match:
                self._naming_validity_label.setText("Match")
                self._naming_validity_label.setStyleSheet("color: green;")
                # Compute preview: template substitution or full match (group 0)
                if template_text:
                    try:
                        preview_text = template_text.format_map(regex_match.groupdict())
                    except (KeyError, ValueError):
                        preview_text = regex_match.group(0)
                else:
                    preview_text = regex_match.group(0)
                self._naming_preview_label.setText(preview_text)
            else:
                self._naming_validity_label.setText("No match")
                self._naming_validity_label.setStyleSheet("color: red;")
                self._naming_preview_label.setText("")

        def _populate_swatch_grid(self):
            """Fill the swatch grid from self._local_custom_colors."""
            self._swatch_buttons = []
            for index, color_int in enumerate(self._local_custom_colors):
                button = QtWidgets.QPushButton()
                button.setFixedSize(24, 24)
                button.setFocusPolicy(Qt.StrongFocus)
                button.setAutoDefault(False)
                red, green, blue = _color_int_to_rgb(color_int)
                button.setStyleSheet(
                    f"background-color: rgb({red},{green},{blue}); "
                    "border: 1px solid #555; "
                    "border-radius: 2px;"
                )
                button.clicked.connect(
                    lambda checked=False, i=index: self._on_swatch_selected(i)
                )
                self._swatch_grid_layout.addWidget(
                    button,
                    index // _SWATCHES_PER_ROW,
                    index % _SWATCHES_PER_ROW,
                )
                self._swatch_buttons.append(button)
            self._update_edit_remove_buttons()

        def _update_swatch_tab_order(self):
            """Establish explicit Qt tab order to chain focus through swatch buttons.

            Chains: last checkbox -> first swatch button -> each subsequent swatch
            button -> Add button.  This ensures Tab key reaches swatch buttons even
            though the QGridLayout container itself has Qt.NoFocus.

            Called at the end of _build_ui and after every _rebuild_swatch_grid so
            the chain stays correct when swatches are added or removed.
            """
            if not self._swatch_buttons:
                return
            # Chain from the last focusable checkbox down to the first swatch button
            QtWidgets.QWidget.setTabOrder(self._link_mode_checkbox, self._swatch_buttons[0])
            # Chain each swatch button to the next one
            for swatch_index in range(len(self._swatch_buttons) - 1):
                QtWidgets.QWidget.setTabOrder(
                    self._swatch_buttons[swatch_index],
                    self._swatch_buttons[swatch_index + 1],
                )
            # Chain last swatch button to Add button
            QtWidgets.QWidget.setTabOrder(self._swatch_buttons[-1], self._add_button)

        def _rebuild_swatch_grid(self):
            """Clear and repopulate the swatch grid from self._local_custom_colors."""
            while self._swatch_grid_layout.count() > 0:
                item = self._swatch_grid_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self._swatch_buttons = []
            self._selected_swatch_index = None
            self._populate_swatch_grid()
            self._update_swatch_tab_order()

        def _highlight_color_name(self):
            """Return the CSS color name to use for the selected swatch border.

            Uses the widget's QPalette Highlight color so the selection indicator
            matches the user's Qt theme, rather than a hardcoded white.
            Mirrors the same method on ColorPaletteDialog for consistency.
            """
            highlight_qcolor = self.palette().color(QtGui.QPalette.Highlight)
            return highlight_qcolor.name()

        def _on_swatch_selected(self, index):
            """Mark the swatch at index as selected; update button borders."""
            self._selected_swatch_index = index
            highlight_color = self._highlight_color_name()
            for button_index, button in enumerate(self._swatch_buttons):
                color_int = self._local_custom_colors[button_index]
                red, green, blue = _color_int_to_rgb(color_int)
                if button_index == index:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        f"border: 2px solid {highlight_color}; "
                        "border-radius: 2px;"
                    )
                else:
                    button.setStyleSheet(
                        f"background-color: rgb({red},{green},{blue}); "
                        "border: 1px solid #555; "
                        "border-radius: 2px;"
                    )
            self._update_edit_remove_buttons()

        def _update_edit_remove_buttons(self):
            """Enable or disable Edit and Remove based on swatch selection state."""
            has_selection = self._selected_swatch_index is not None
            self._edit_button.setEnabled(has_selection)
            self._remove_button.setEnabled(has_selection)

        def _on_add_color(self):
            """Open nuke.getColor() and append the result to the custom colors list."""
            result = nuke.getColor()
            if result == 0:
                return
            self._local_custom_colors.append(result)
            self._rebuild_swatch_grid()
            # Auto-select the newly appended color; _on_swatch_selected applies
            # the palette highlight border via _highlight_color_name().
            new_index = len(self._local_custom_colors) - 1
            self._on_swatch_selected(new_index)

        def _on_edit_color(self):
            """Replace the selected color via nuke.getColor() and immediately
            recolor matching anchors.
            """
            if self._selected_swatch_index is None:
                return
            result = nuke.getColor()
            if result == 0:
                return
            # Capture old color before updating so we can recolor matching anchors
            old_color = self._local_custom_colors[self._selected_swatch_index]
            self._local_custom_colors[self._selected_swatch_index] = result
            self._recolor_anchors_for_changed_custom_colors([old_color], [result])
            selected_index = self._selected_swatch_index
            self._rebuild_swatch_grid()
            self._on_swatch_selected(selected_index)

        def _on_remove_color(self):
            """Remove the selected color from the list and rebuild the grid."""
            if self._selected_swatch_index is None:
                return
            del self._local_custom_colors[self._selected_swatch_index]
            self._rebuild_swatch_grid()
            # _rebuild_swatch_grid resets _selected_swatch_index = None
            # and _populate_swatch_grid calls _update_edit_remove_buttons()

        def _recolor_anchors_for_changed_custom_colors(self, old_colors, new_colors):
            """Recolor anchor nodes in the current script whose tile_color matches
            a changed custom color.

            For each index where old_colors[i] != new_colors[i], iterates all
            NoOp anchor nodes and calls anchor.propagate_anchor_color() for any
            node whose current tile_color equals the old color value.

            Parameters
            ----------
            old_colors : list of int
                Custom color ints before the user's edits (snapshot from __init__).
            new_colors : list of int
                Custom color ints after the user's edits (from _local_custom_colors).
            """
            try:
                import anchor as anchor_module
            except ImportError:
                return

            for index in range(min(len(old_colors), len(new_colors))):
                old_color_int = old_colors[index]
                new_color_int = new_colors[index]
                if old_color_int == new_color_int:
                    continue
                for anchor_node in anchor_module.all_anchors():
                    if int(anchor_node['tile_color'].value()) == old_color_int:
                        anchor_module.propagate_anchor_color(anchor_node, new_color_int)

        def _on_accept(self):
            """Flush local working copies to prefs module, persist, and close."""
            import prefs as prefs_module
            # Read current checkbox states into local vars (user may have changed them)
            self._local_plugin_enabled = self._plugin_checkbox.isChecked()
            self._local_link_mode = (
                "create_link" if self._link_mode_checkbox.isChecked() else "passthrough"
            )
            self._local_naming_regex = self._naming_regex_edit.text()
            self._local_naming_template = self._naming_template_edit.text()
            self._local_naming_demo_filename = self._naming_test_filename_edit.text()
            # Flush local working copies to prefs module-level variables
            prefs_module.plugin_enabled = self._local_plugin_enabled
            prefs_module.link_classes_paste_mode = self._local_link_mode
            prefs_module.custom_colors = list(self._local_custom_colors)
            prefs_module.naming_regex = self._local_naming_regex
            prefs_module.naming_template = self._local_naming_template
            prefs_module.naming_demo_filename = self._local_naming_demo_filename
            # Persist to disk
            prefs_module.save()
            # Apply plugin_enabled live (menu enable/disable without restart).
            # set_anchors_menu_enabled is stored on the prefs module by menu.py at startup,
            # avoiding any import conflict with Nuke's built-in 'menu' module.
            set_menu_enabled = getattr(prefs_module, 'set_anchors_menu_enabled', None)
            if set_menu_enabled is not None:
                set_menu_enabled(prefs_module.plugin_enabled)
            # Recolor is applied immediately in _on_edit_color (on color picker confirm),
            # not here on OK — so no recolor call needed at accept time.
            self.accept()

        def showEvent(self, event):
            """Install an application-level event filter so Tab/Shift+Tab reach
            this dialog before Nuke's tabtabtab plugin can intercept them.

            Qt processes event filters in LIFO order (last installed runs first),
            so installing here in showEvent means our filter runs before the one
            registered by tabtabtab at startup.
            """
            super().showEvent(event)
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.installEventFilter(self)

        def hideEvent(self, event):
            """Remove the application-level event filter when the dialog is hidden."""
            super().hideEvent(event)
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)

        def eventFilter(self, obj, event):
            """Intercept Tab and Shift+Tab at the QApplication level.

            Returns True (consuming the event) for Tab/Backtab so that Nuke's
            tabtabtab event filter never sees them.  All other events are passed
            through by returning False.
            """
            if event.type() == QtCore.QEvent.KeyPress:
                key = event.key()
                if key == QtCore.Qt.Key_Tab:
                    self.focusNextChild()
                    return True  # consume — prevent Nuke's tabtabtab from firing
                if key == QtCore.Qt.Key_Backtab:
                    self.focusPreviousChild()
                    return True
            return False
