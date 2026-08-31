"""Spatial view — a popup map of the script's anchors and labelled backdrops.

Where the ``A`` / ``Alt``+``A`` pickers present anchors as a flat, weight-ordered
list, the spatial view (issue #83) presents them as *cards on a coarse grid whose
cells echo where each anchor sits in the DAG*, with labelled backdrops drawn as
outlines around the cards they contain.  Recognising a place is faster than
recalling a name, so the view is the quickest route to an anchor you know the
position of.

The same fuzzy search the pickers use carries into this view: the filter field
honours the space-prefix search modes from preferences (see
``tabtabtab_anchors.parse_search_modes``), and as you type, cards that no longer
match grey out rather than disappearing — the map keeps its shape while you
narrow it down.

Two modes, mirroring the two existing pickers:

- ``MODE_NAVIGATE`` (``Alt``+``S``, leader ``S``) — activating a card navigates
  to that anchor or backdrop, exactly as **Anchor Find** does.
- ``MODE_CREATE_LINK`` (**Edit > Anchors > Spatial View (Create Link)**) —
  activating a card creates a link to that anchor, exactly as **Create Link**
  does.  Backdrops are drawn for context but are not selectable, matching the
  link picker's item list.

Both modes borrow the matching picker's tabtabtab plugin, so item collection,
node colours, invocation, and the on-disk selection weights are shared with the
pickers rather than reimplemented here — pick an anchor in either UI and it
sorts first in both.

The grid maths and the filtering live in module-level functions above the Qt
classes so they can be unit-tested without a Qt session; the widgets below are
only defined when Qt is importable, following the pattern in colors.py.
"""

import nuke

try:
    if hasattr(nuke, 'NUKE_VERSION_MAJOR') and nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
    else:
        from PySide2 import QtCore, QtGui, QtWidgets
        from PySide2.QtCore import Qt
except ImportError:
    QtCore = None
    QtGui = None
    QtWidgets = None
    Qt = None

import prefs
import tabtabtab_anchors as _tabtabtab
from constants import (
    ANCHOR_DEFAULT_COLOR,
    SPATIAL_CARD_HEIGHT,
    SPATIAL_CARD_WIDTH,
    SPATIAL_CELL_TOLERANCE,
    SPATIAL_GRID_SPACING,
    SPATIAL_MAX_COLUMNS,
    SPATIAL_MAX_ROWS,
    SPATIAL_MAX_SCREEN_FRACTION,
)

# The two things the view can be opened to do.  Plain strings so the menu
# commands in menu.py read clearly.
MODE_NAVIGATE = 'navigate'
MODE_CREATE_LINK = 'create_link'

# Fallback tile colour for a backdrop that has never been coloured.
_DEFAULT_BACKDROP_COLOR = 0x5A5A5AFF


# ---------------------------------------------------------------------------
# Grid layout — pure functions, no Qt and no nuke.
#
# The DAG is sparse: nodes sit hundreds of units apart with nothing in between,
# so reproducing their coordinates to scale would give a mostly-empty map.
# Instead each axis is *binned* — coordinates within a tolerance of each other
# collapse onto one row or column — which keeps the relative arrangement (what
# is left of what, what is above what) while squeezing out the empty space.
# ---------------------------------------------------------------------------

def _bin_coordinates(values, tolerance):
    """Return a {coordinate: index} map placing nearby coordinates in one bin.

    Walking the sorted coordinates, a new bin starts whenever the coordinate is
    more than *tolerance* beyond the one that opened the current bin.
    """
    bins = {}
    index = -1
    bin_start = None
    for value in sorted(set(values)):
        if bin_start is None or value - bin_start > tolerance:
            index += 1
            bin_start = value
        bins[value] = index
    return bins


def _binned_axis(values, tolerance, maximum):
    """Bin *values*, doubling *tolerance* until the axis fits in *maximum* bins.

    A script whose anchors are spread over a huge area would otherwise produce a
    grid too large to read; widening the tolerance merges the closest neighbours
    first, so the coarser map still groups what the DAG groups.
    """
    bins = _bin_coordinates(values, tolerance)
    while bins and maximum > 0 and tolerance > 0 and max(bins.values()) + 1 > maximum:
        tolerance *= 2
        bins = _bin_coordinates(values, tolerance)
    return bins


def _free_cell_near(row, column, taken_cells):
    """Return (row, column) if free, else the first free cell below it.

    Nuke comps run down a vertical spine with modules laid out left to right, so
    a column of the grid stands for a module.  Resolving a collision by stacking
    downwards therefore keeps every card in the column its node sits in, which is
    the stronger half of the spatial analogy; the grid grows taller rather than
    scattering cards sideways into other modules' columns.
    """
    while (row, column) in taken_cells:
        row += 1
    return (row, column)


def assign_cells(placements,
                 tolerance=SPATIAL_CELL_TOLERANCE,
                 max_rows=SPATIAL_MAX_ROWS,
                 max_columns=SPATIAL_MAX_COLUMNS):
    """Map each placement onto a distinct grid cell echoing its DAG position.

    Parameters
    ----------
    placements : sequence of (key, x, y)
        *key* identifies the item; *x* / *y* are its DAG coordinates.  DAG y
        grows downwards, as grid rows do, so neither axis needs flipping.

    Returns
    -------
    dict
        {key: (row, column)}, normalised so the top-left cell is (0, 0).
    """
    if not placements:
        return {}

    column_bins = _binned_axis([x for _key, x, _y in placements], tolerance, max_columns)
    row_bins = _binned_axis([y for _key, _x, y in placements], tolerance, max_rows)

    # Assign in reading order of the binned grid rather than in whatever order
    # nuke.allNodes() returned, so the same script always lays out the same way.
    ordered_placements = sorted(
        placements,
        key=lambda placement: (row_bins[placement[2]], column_bins[placement[1]],
                               placement[2], placement[1], str(placement[0])),
    )

    keys_by_cell = {}
    for key, x, y in ordered_placements:
        cell = _free_cell_near(row_bins[y], column_bins[x], keys_by_cell)
        keys_by_cell[cell] = key

    top_row = min(row for row, _column in keys_by_cell)
    left_column = min(column for _row, column in keys_by_cell)
    return {
        key: (row - top_row, column - left_column)
        for (row, column), key in keys_by_cell.items()
    }


def build_layout(anchors, backdrops, **cell_options):
    """Lay out *anchors* as cards and *backdrops* as spans around them.

    Parameters
    ----------
    anchors : sequence of dict
        Each with 'key', 'x', 'y' — the anchor's DAG position.
    backdrops : sequence of dict
        Each with 'key', 'x', 'y', 'width', 'height' — the backdrop's DAG bounds.

    Returns
    -------
    dict
        ``cells``   {key: (row, column)} for every anchor, plus every backdrop
                    that contains no anchor (it has no cards to draw an outline
                    around, so it takes a cell of its own and stays reachable).
        ``spans``   {backdrop key: (top, left, bottom, right)} — the inclusive
                    cell rectangle the backdrop's outline covers.
        ``rows`` / ``columns``  the grid's extent.
    """
    anchor_keys_by_backdrop = {}
    for backdrop in backdrops:
        # Same containment test as link.find_smallest_containing_backdrop, so a
        # card sits inside the same outline its node sits inside in the DAG.
        anchor_keys_by_backdrop[backdrop['key']] = [
            anchor['key'] for anchor in anchors
            if (backdrop['x'] <= anchor['x'] < backdrop['x'] + backdrop['width']
                and backdrop['y'] <= anchor['y'] < backdrop['y'] + backdrop['height'])
        ]

    placements = [(anchor['key'], anchor['x'], anchor['y']) for anchor in anchors]
    placements += [
        (backdrop['key'], backdrop['x'], backdrop['y'])
        for backdrop in backdrops if not anchor_keys_by_backdrop[backdrop['key']]
    ]
    cells = assign_cells(placements, **cell_options)

    spans = {}
    for backdrop in backdrops:
        member_cells = [cells[key] for key in anchor_keys_by_backdrop[backdrop['key']]]
        if not member_cells:
            row, column = cells[backdrop['key']]
            spans[backdrop['key']] = (row, column, row, column)
            continue
        spans[backdrop['key']] = (
            min(row for row, _column in member_cells),
            min(column for _row, column in member_cells),
            max(row for row, _column in member_cells),
            max(column for _row, column in member_cells),
        )

    rows = max((row for row, _column in cells.values()), default=-1) + 1
    columns = max((column for _row, column in cells.values()), default=-1) + 1
    return {'cells': cells, 'spans': spans, 'rows': rows, 'columns': columns}


# ---------------------------------------------------------------------------
# Filtering — the pickers' fuzzy search, applied to cards instead of rows.
# ---------------------------------------------------------------------------

def rank_entries(query, entries, weight_fn=None, space_mode_order=None):
    """Return the keys of the entries matching *query*, best match first.

    Mirrors ``tabtabtab_anchors.NodeModel.update``: consecutive matches rank
    above merely fuzzy ones, and within each group the most-used entry (by the
    picker's own weights) comes first, then alphabetically.  So the card the view
    highlights first is the row the picker would have put first.

    Parameters
    ----------
    query : str
        Raw filter text, including any leading-space or ``*`` mode prefix.
    entries : sequence of dict
        Each with 'key' and 'menupath'.
    weight_fn : callable or None
        Called with a menupath, returns its selection weight.  None means unweighted.
    space_mode_order : sequence of str or None
        The space-prefix mode mapping from preferences.
    """
    filtertext, anchored, force_non_anchored, force_consecutive = _tabtabtab.parse_search_modes(
        query.lower(), space_mode_order)

    consecutive_matches = []
    fuzzy_matches = []
    for entry in entries:
        uiname = _tabtabtab.menupath_uiname(entry['menupath'])
        search_string = uiname.lower()
        if force_non_anchored:
            search_string = search_string[1:]
        score = weight_fn(entry['menupath']) if weight_fn is not None else 0
        if _tabtabtab.consec_find(filtertext, search_string, anchored):
            consecutive_matches.append((-score, uiname, entry['key']))
        elif not force_consecutive and _tabtabtab.nonconsec_find(
                filtertext, search_string, anchored):
            fuzzy_matches.append((-score, uiname, entry['key']))

    ranked = sorted(consecutive_matches) + sorted(fuzzy_matches)
    return [key for _score, _uiname, key in ranked]


def cell_in_direction(cells, current_key, direction, candidate_keys):
    """Return the candidate key nearest to *current_key* in *direction*, or None.

    Powers the arrow keys: movement is spatial, so pressing Right steps to the
    card to the right on the map rather than to the next item in a list.  Cards
    filtered out by the search are not candidates, so arrowing walks only the
    matches while the greyed cards keep the map's shape.

    Candidates are ranked by how far off the travelled line they sit first and
    how far along it second, so Right stays on its row for as long as that row
    has cards rather than drifting diagonally to a nearer neighbour.
    """
    if current_key not in cells:
        return None
    current_row, current_column = cells[current_key]

    best_key = None
    best_distance = None
    for key in candidate_keys:
        if key == current_key or key not in cells:
            continue
        row, column = cells[key]
        if direction == 'left':
            along, across = current_column - column, abs(row - current_row)
        elif direction == 'right':
            along, across = column - current_column, abs(row - current_row)
        elif direction == 'up':
            along, across = current_row - row, abs(column - current_column)
        elif direction == 'down':
            along, across = row - current_row, abs(column - current_column)
        else:
            return None
        if along <= 0:
            continue
        distance = (across, along, row, column)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_key = key
    return best_key


# ---------------------------------------------------------------------------
# Item collection — anchors, backdrops, colours.  Needs nuke, not Qt.
# ---------------------------------------------------------------------------

def display_name_for(entry):
    """Return the text shown on an entry's card or outline.

    The picker menu path already carries the display name the pickers use, so
    both UIs always name an anchor the same way.
    """
    return entry['menupath'].rpartition('/')[2]


def node_color(node):
    """Return the 0xRRGGBBAA colour to draw *node* with in the view.

    Uses the colour the node actually carries; an uncoloured anchor falls back to
    the colour the DAG would give it, so cards read like the nodes they stand for
    rather than turning black.
    """
    try:
        color_int = int(node['tile_color'].value())
    except (NameError, TypeError, ValueError):
        color_int = 0
    if color_int:
        return color_int
    if node.Class() == 'BackdropNode':
        return _DEFAULT_BACKDROP_COLOR
    try:
        import anchor
        return int(anchor.find_anchor_color(node))
    except Exception:
        return ANCHOR_DEFAULT_COLOR


def _rgb_for(color_int):
    from colors import _color_int_to_rgb
    return _color_int_to_rgb(color_int)


def text_color_for(color_int):
    """Return a near-black or near-white text colour that reads on *color_int*."""
    red, green, blue = _rgb_for(color_int)
    # Rec. 601 luma — good enough to choose between dark and light text.
    luma = 0.299 * red + 0.587 * green + 0.114 * blue
    return '#111111' if luma > 140 else '#eeeeee'


def _plugin_for_mode(mode, hit_group):
    """Return the tabtabtab picker plugin whose behaviour *mode* mirrors."""
    import anchor
    if mode == MODE_CREATE_LINK:
        plugin = anchor._make_anchor_picker_plugin()
    else:
        plugin = anchor._make_anchor_navigate_plugin()
    plugin._hit_group = hit_group
    return plugin


def collect_entries(mode, hit_group):
    """Return (plugin, entries) — the picker plugin and what the view shows.

    Each entry is a dict with:
        key         stable index, unique within this view
        menupath    the picker menu path ('Anchors/foo' or 'Backdrops/bar')
        node        the nuke node
        item        the picker item dict, handed straight back to plugin.invoke()
        kind        'anchor' or 'backdrop'
        selectable  whether activating it does anything in this mode

    In link-creation mode the plugin lists anchors only, so labelled backdrops
    are collected separately and drawn as unselectable context — the outlines are
    half of what makes the map readable.
    """
    plugin = _plugin_for_mode(mode, hit_group)
    items = plugin.get_items()

    entries = []
    listed_node_names = set()
    for item in items:
        node = item['menuobj']
        entries.append({
            'key': len(entries),
            'menupath': item['menupath'],
            'node': node,
            'item': item,
            'kind': 'backdrop' if node.Class() == 'BackdropNode' else 'anchor',
            'selectable': True,
        })
        listed_node_names.add(node.name())

    if mode == MODE_CREATE_LINK:
        with (hit_group or nuke.root()):
            context_backdrops = [
                backdrop for backdrop in nuke.allNodes('BackdropNode')
                if backdrop['label'].value().strip()
                and backdrop.name() not in listed_node_names
            ]
        for backdrop in context_backdrops:
            menupath = 'Backdrops/' + backdrop['label'].value().strip()
            entries.append({
                'key': len(entries),
                'menupath': menupath,
                'node': backdrop,
                'item': {'menuobj': backdrop, 'menupath': menupath},
                'kind': 'backdrop',
                'selectable': False,
            })

    return plugin, entries


def layout_for_entries(entries):
    """Build the grid layout for *entries* from their nodes' DAG geometry."""
    anchors = [
        {'key': entry['key'], 'x': entry['node'].xpos(), 'y': entry['node'].ypos()}
        for entry in entries if entry['kind'] == 'anchor'
    ]
    backdrops = [
        {
            'key': entry['key'],
            'x': entry['node'].xpos(),
            'y': entry['node'].ypos(),
            'width': entry['node']['bdwidth'].value(),
            'height': entry['node']['bdheight'].value(),
        }
        for entry in entries if entry['kind'] == 'backdrop'
    ]
    return build_layout(anchors, backdrops)


def host_main_window():
    """Return the Nuke main window to parent the popup to, or None.

    Parenting to the host is what the pickers do — it hands the widget's
    lifetime to Nuke, which destroys it in a defined order at shutdown.
    """
    return _tabtabtab._find_host_main_window()


def space_mode_order():
    """Return the space-prefix search mode mapping the pickers are using."""
    import anchor
    return anchor._current_space_mode_order()


# ---------------------------------------------------------------------------
# Qt widgets — only defined when Qt is importable (headless `nuke -t` is not).
# ---------------------------------------------------------------------------

if QtWidgets is None:
    AnchorCard = None
    BackdropOutline = None
    FilterLineEdit = None
    SpatialView = None
else:
    _TITLES = {
        MODE_NAVIGATE: 'ANCHORS SPATIAL VIEW',
        MODE_CREATE_LINK: 'ANCHORS SPATIAL VIEW — CREATE LINK',
    }
    _HINTS = {
        MODE_NAVIGATE: 'type to filter  ·  arrows to move  ·  Enter to navigate  ·  Esc to close',
        MODE_CREATE_LINK: 'type to filter  ·  arrows to move  ·  Enter to link  ·  Esc to close',
    }
    # Navigate mode lists labelled backdrops alongside the anchors and filters
    # both; in link mode the backdrops are context only, so only anchors match.
    _PLACEHOLDERS = {
        MODE_NAVIGATE: 'Search anchors and backdrops',
        MODE_CREATE_LINK: 'Search anchors',
    }
    _FILTERED_OUT_COLOR = QtGui.QColor(70, 70, 70)
    _FILTERED_OUT_TEXT = '#888888'
    _HIGHLIGHT_BORDER = '#ffffff'
    _CARD_BORDER = 'rgba(0, 0, 0, 60)'
    # Room the popup's chrome (title, filter field, hint) needs beside the grid.
    _CHROME_HEIGHT = 130

    def _rgb_string(color_int):
        return "rgb(%d, %d, %d)" % _rgb_for(color_int)

    def _direction_for_key(key):
        """Return the arrow direction *key* means, or None if it is not an arrow."""
        if key == Qt.Key_Left:
            return 'left'
        if key == Qt.Key_Right:
            return 'right'
        if key == Qt.Key_Up:
            return 'up'
        if key == Qt.Key_Down:
            return 'down'
        return None

    def _owning_view(widget):
        """Return the SpatialView *widget* belongs to, or None."""
        window = widget.window()
        return window if isinstance(window, SpatialView) else None

    class AnchorCard(QtWidgets.QFrame):
        """One anchor as a coloured, clickable card.

        Greys out — rather than vanishing — when the search filters it out, so
        the map keeps its shape as the user narrows the search.
        """

        def __init__(self, entry, parent=None):
            super(AnchorCard, self).__init__(parent)
            self.entry = entry
            self._color_int = node_color(entry['node'])
            self._matched = True
            self._highlighted = False

            self.setFixedSize(SPATIAL_CARD_WIDTH, SPATIAL_CARD_HEIGHT)
            self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))

            self._name_label = QtWidgets.QLabel(display_name_for(entry))
            self._name_label.setAlignment(Qt.AlignCenter)
            self._name_label.setWordWrap(True)
            name_font = QtGui.QFont()
            name_font.setPointSize(8)
            name_font.setBold(True)
            self._name_label.setFont(name_font)

            card_layout = QtWidgets.QVBoxLayout(self)
            card_layout.setContentsMargins(4, 2, 4, 2)
            card_layout.addWidget(self._name_label)

            self._apply_style()

        def set_matched(self, matched):
            """Colour the card normally when *matched*, grey it out otherwise."""
            if matched == self._matched:
                return
            self._matched = matched
            self._apply_style()

        def set_highlighted(self, highlighted):
            """Draw (or clear) the border marking the card Enter would activate."""
            if highlighted == self._highlighted:
                return
            self._highlighted = highlighted
            self._apply_style()

        def _apply_style(self):
            if self._matched:
                background = _rgb_string(self._color_int)
                text_color = text_color_for(self._color_int)
            else:
                background = "rgb(%d, %d, %d)" % (
                    _FILTERED_OUT_COLOR.red(),
                    _FILTERED_OUT_COLOR.green(),
                    _FILTERED_OUT_COLOR.blue(),
                )
                text_color = _FILTERED_OUT_TEXT
            border_color = _HIGHLIGHT_BORDER if self._highlighted else _CARD_BORDER
            self.setStyleSheet(
                "QFrame { background-color: %s; border: 2px solid %s; border-radius: 5px; }"
                % (background, border_color)
            )
            self._name_label.setStyleSheet(
                "color: %s; background-color: transparent; border: none;" % text_color
            )

        def mousePressEvent(self, event):  # noqa: N802 — Qt naming
            view = _owning_view(self)
            if view is not None:
                view.activate_key(self.entry['key'])

    class BackdropOutline(QtWidgets.QWidget):
        """A labelled backdrop, drawn as an outline around the cards it holds.

        Sits behind the cards and paints nothing where they are, so a click on a
        card hits the card and a click on the backdrop's own area hits this.
        """

        def __init__(self, entry, parent=None):
            super(BackdropOutline, self).__init__(parent)
            self.entry = entry
            self._color = QtGui.QColor(*_rgb_for(node_color(entry['node'])))
            self._label = display_name_for(entry)
            self._matched = True
            self._highlighted = False
            if entry['selectable']:
                self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))

        def set_matched(self, matched):
            if matched == self._matched:
                return
            self._matched = matched
            self.update()

        def set_highlighted(self, highlighted):
            if highlighted == self._highlighted:
                return
            self._highlighted = highlighted
            self.update()

        def paintEvent(self, event):  # noqa: N802 — Qt naming
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            color = self._color if self._matched else _FILTERED_OUT_COLOR
            painter.setPen(QtGui.QPen(color, 3 if self._highlighted else 2))
            fill = QtGui.QColor(color)
            fill.setAlpha(40)
            painter.setBrush(fill)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 6, 6)

            label_font = QtGui.QFont()
            label_font.setPointSize(7)
            painter.setFont(label_font)
            painter.setPen(color)
            painter.drawText(self.rect().adjusted(6, 3, -6, -3),
                             Qt.AlignTop | Qt.AlignLeft, self._label)

        def mousePressEvent(self, event):  # noqa: N802 — Qt naming
            if not self.entry['selectable']:
                return
            view = _owning_view(self)
            if view is not None:
                view.activate_key(self.entry['key'])

    class FilterLineEdit(QtWidgets.QLineEdit):
        """The search field, forwarding the keys that drive the card grid.

        Mirrors tabtabtab's TabyLineEdit: the arrows, Escape and Tab have to be
        caught in event() rather than keyPressEvent or they never arrive.
        """

        pressed_arrow = QtCore.Signal(str)
        cancelled = QtCore.Signal()

        def event(self, event):
            if event.type() == QtCore.QEvent.KeyPress:
                key = event.key()
                direction = _direction_for_key(key)
                if direction is not None:
                    self.pressed_arrow.emit(direction)
                    return True
                if key == Qt.Key_Escape:
                    self.cancelled.emit()
                    return True
                if key == Qt.Key_Tab:
                    self.returnPressed.emit()
                    return True
            return super(FilterLineEdit, self).event(event)

    class SpatialView(QtWidgets.QDialog):
        """The popup itself: a filter field over a grid of cards and outlines."""

        def __init__(self, mode, hit_group, plugin, entries, parent=None):
            super(SpatialView, self).__init__(parent)
            # Qt.Dialog keeps this a top-level window even with the host main
            # window as parent — see _create_tabtabtab_widget in
            # tabtabtab_anchors.py for why dropping it breaks click-outside.
            self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)

            self._mode = mode
            self._hit_group = hit_group
            self._plugin = plugin
            self._entries_by_key = {entry['key']: entry for entry in entries}
            self._selectable_keys = [entry['key'] for entry in entries if entry['selectable']]
            self._weights = _tabtabtab.NodeWeights(plugin.get_weights_file())
            self._weights.load()

            layout = layout_for_entries(entries)
            self._cells = layout['cells']
            self._matched_keys = []
            self._highlighted_key = None
            self._widgets_by_key = {}

            self._build_ui(entries, layout)
            self._apply_filter('')

        # -- construction ----------------------------------------------------

        def _build_ui(self, entries, layout):
            title_label = QtWidgets.QLabel(_TITLES[self._mode])
            title_font = QtGui.QFont()
            title_font.setBold(True)
            title_font.setPointSize(10)
            title_label.setFont(title_font)
            title_label.setStyleSheet("color: #cccccc; background: transparent;")
            title_label.setAlignment(Qt.AlignCenter)

            self.filter_input = FilterLineEdit()
            self.filter_input.setPlaceholderText(_PLACEHOLDERS[self._mode])
            self.filter_input.textChanged.connect(self._apply_filter)
            self.filter_input.returnPressed.connect(self._activate_highlighted)
            self.filter_input.cancelled.connect(self.close)
            self.filter_input.pressed_arrow.connect(self._move_highlight)

            grid_container = QtWidgets.QWidget()
            grid_container.setAttribute(Qt.WA_TranslucentBackground)
            grid_layout = QtWidgets.QGridLayout(grid_container)
            grid_layout.setContentsMargins(6, 6, 6, 6)
            grid_layout.setSpacing(SPATIAL_GRID_SPACING)

            # Outlines go in first and are lowered, so the cards they span stay
            # on top of them and keep taking the clicks.
            for entry in entries:
                if entry['kind'] != 'backdrop':
                    continue
                span = layout['spans'].get(entry['key'])
                if span is None:
                    continue
                top, left, bottom, right = span
                outline = BackdropOutline(entry, grid_container)
                grid_layout.addWidget(outline, top, left, bottom - top + 1, right - left + 1)
                outline.lower()
                self._widgets_by_key[entry['key']] = outline

            for entry in entries:
                if entry['kind'] != 'anchor':
                    continue
                row, column = self._cells[entry['key']]
                card = AnchorCard(entry, grid_container)
                grid_layout.addWidget(card, row, column)
                self._widgets_by_key[entry['key']] = card

            self._grid_container = grid_container
            self._scroll_area = QtWidgets.QScrollArea()
            self._scroll_area.setWidget(grid_container)
            self._scroll_area.setWidgetResizable(True)
            self._scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
            self._scroll_area.viewport().setAutoFillBackground(False)
            self._scroll_area.setStyleSheet(
                "QScrollArea { background: transparent; border: none; }")

            hint_label = QtWidgets.QLabel(_HINTS[self._mode])
            hint_font = QtGui.QFont()
            hint_font.setPointSize(7)
            hint_label.setFont(hint_font)
            hint_label.setStyleSheet("color: #888888; background: transparent;")
            hint_label.setAlignment(Qt.AlignCenter)

            main_layout = QtWidgets.QVBoxLayout()
            main_layout.setContentsMargins(16, 12, 16, 12)
            main_layout.setSpacing(8)
            main_layout.addWidget(title_label)
            main_layout.addWidget(self.filter_input)
            main_layout.addWidget(self._scroll_area)
            main_layout.addWidget(hint_label)
            self.setLayout(main_layout)

            self._fit_to_screen()

        def _fit_to_screen(self):
            """Size the popup to its grid, capped at most of the current screen."""
            available = self._available_screen_rect()
            grid_hint = self._grid_container.sizeHint()
            if available is None:
                self.adjustSize()
                return
            max_width = int(available.width() * SPATIAL_MAX_SCREEN_FRACTION)
            max_height = int(available.height() * SPATIAL_MAX_SCREEN_FRACTION)
            self._scroll_area.setMinimumSize(
                max(0, min(grid_hint.width(), max_width)),
                max(0, min(grid_hint.height(), max_height - _CHROME_HEIGHT)),
            )
            self.setMaximumSize(max_width, max_height)
            self.adjustSize()

        def _available_screen_rect(self):
            """Return the working area of the screen under the cursor, or None."""
            cursor_position = QtGui.QCursor.pos()
            screen = None
            if hasattr(QtWidgets.QApplication, 'screenAt'):
                screen = QtWidgets.QApplication.screenAt(cursor_position)
            if screen is None:
                screen = QtWidgets.QApplication.primaryScreen()
            if screen is None:
                return None
            return screen.availableGeometry()

        # -- filtering and highlight ------------------------------------------

        def _selectable_entries(self):
            return [self._entries_by_key[key] for key in self._selectable_keys]

        def _apply_filter(self, text):
            """Grey out the cards that no longer match, and re-pick the highlight."""
            ranked_keys = rank_entries(
                text,
                self._selectable_entries(),
                weight_fn=self._weights.get,
                space_mode_order=space_mode_order(),
            )
            self._matched_keys = ranked_keys
            matched = set(ranked_keys)
            for key, widget in self._widgets_by_key.items():
                # Context-only backdrops are never filtered out: they are the
                # map's landmarks, not candidates for the search.
                widget.set_matched(
                    key in matched or not self._entries_by_key[key]['selectable'])
            self._set_highlight(ranked_keys[0] if ranked_keys else None)

        def _set_highlight(self, key):
            if key == self._highlighted_key:
                return
            previous_widget = self._widgets_by_key.get(self._highlighted_key)
            if previous_widget is not None:
                previous_widget.set_highlighted(False)
            self._highlighted_key = key
            current_widget = self._widgets_by_key.get(key)
            if current_widget is not None:
                current_widget.set_highlighted(True)
                self._scroll_area.ensureWidgetVisible(current_widget)

        def _move_highlight(self, direction):
            if self._highlighted_key is None:
                self._set_highlight(self._matched_keys[0] if self._matched_keys else None)
                return
            next_key = cell_in_direction(
                self._cells, self._highlighted_key, direction, self._matched_keys)
            if next_key is not None:
                self._set_highlight(next_key)

        # -- activation --------------------------------------------------------

        def _activate_highlighted(self):
            if self._highlighted_key is not None:
                self.activate_key(self._highlighted_key)

        def activate_key(self, key):
            """Invoke the entry for *key* through the picker plugin, then close.

            Mirrors TabTabTabWidget.create(): the plugin does the work (navigate,
            or create a link) and the selection weight is bumped, so choosing an
            anchor here also floats it to the top of the pickers.
            """
            entry = self._entries_by_key.get(key)
            if entry is None or not entry['selectable']:
                return
            self._plugin.invoke(entry['item'])
            self._weights.increment(entry['menupath'])
            self.close()

        # -- window plumbing ---------------------------------------------------

        def paintEvent(self, event):  # noqa: N802 — Qt naming
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setBrush(QtGui.QColor(20, 20, 20, 225))
            painter.setPen(QtGui.QColor(180, 180, 180, 120))
            painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

        def event(self, event):
            """Close when the window goes inactive — i.e. on a click outside."""
            if event.type() == QtCore.QEvent.WindowDeactivate:
                self.close()
                return True
            return super(SpatialView, self).event(event)

        def under_cursor(self):
            """Centre the popup on the cursor, clamped to the current screen."""
            available = self._available_screen_rect()
            if available is None:
                return
            cursor_position = QtGui.QCursor.pos()
            x_position = cursor_position.x() - self.width() // 2
            y_position = cursor_position.y() - self.height() // 2
            x_position = max(available.left(),
                             min(x_position, available.right() - self.width()))
            y_position = max(available.top(),
                             min(y_position, available.bottom() - self.height()))
            self.move(x_position, y_position)

        def show(self):
            super(SpatialView, self).show()
            self.filter_input.setFocus()

        def close(self):
            self._weights.save()
            return super(SpatialView, self).close()


# ---------------------------------------------------------------------------
# Entry points — bound in menu.py and dispatched by the leader key.
# ---------------------------------------------------------------------------

_active_view = None


def open_view(mode, hit_group=None):
    """Open the spatial view in *mode* for the group under the cursor.

    Silent no-op when the plugin is disabled, when Qt is unavailable (headless
    sessions), or when the group holds nothing the view could show — the same
    guards the pickers apply.
    """
    global _active_view
    if not prefs.plugin_enabled:
        return None
    if QtWidgets is None:
        return None
    if hit_group is None:
        hit_group = nuke.lastHitGroup()

    plugin, entries = collect_entries(mode, hit_group)
    if not any(entry['selectable'] for entry in entries):
        return None

    # The view mirrors the script's geometry, which changes as the user works,
    # so it is rebuilt on every open rather than cached the way the pickers are.
    if _active_view is not None:
        try:
            _active_view.close()
            _active_view.deleteLater()
        except RuntimeError:
            pass
    _active_view = SpatialView(mode, hit_group, plugin, entries, parent=host_main_window())
    _active_view.under_cursor()
    _active_view.show()
    _active_view.raise_()
    return _active_view


def open_navigate_view():
    """Open the spatial view for navigation (Alt+S, or leader S)."""
    return open_view(MODE_NAVIGATE)


def open_create_link_view():
    """Open the spatial view for link creation."""
    return open_view(MODE_CREATE_LINK)
