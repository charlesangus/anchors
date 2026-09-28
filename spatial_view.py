"""Spatial view — a map of the script beside the ``A`` / ``Alt``+``A`` pickers.

With **Show the spatial view beside the A and Alt+A menus** ticked in
Preferences, the two anchor pickers open as a wider popup: the usual search
field and list on the left, and on the right a map of the current group — anchors as coloured tiles, Dot anchors as small
circles with their label beside them, and labelled backdrops as frames around
what they really enclose.  Recognising a place is faster than recalling a name.

The map keeps the script's real arrangement but squeezes out the empty space
between items (``compress_axis``), then nudges items apart until nothing
collides (``build_layout``).  Typing in the search field filters the list
exactly as before and dims the map items that no longer match; the row
highlighted in the list is highlighted on the map, and clicking a map item picks
it as if its row had been chosen.

``SpatialPicker`` is the tabtabtab picker widget itself with the map added, so
the search, the item list, the selection weights, and what picking an item does
are all the pickers' own.  The layout maths is in module-level functions so it
can be unit-tested without a Qt session.
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

import tabtabtab_anchors as _tabtabtab
from constants import (
    ANCHOR_DEFAULT_COLOR,
    SPATIAL_BACKDROP_HEADER,
    SPATIAL_BACKDROP_PADDING,
    SPATIAL_DOT_TIERS,
    SPATIAL_EMPTY_BACKDROP_SCALE,
    SPATIAL_ITEM_GAP,
    SPATIAL_MAX_GAP,
    SPATIAL_MAX_SCREEN_FRACTION,
    SPATIAL_SCALE,
    SPATIAL_SEARCH_PANEL_WIDTH,
    SPATIAL_TILE_HEIGHT,
    SPATIAL_TILE_WIDTH,
)

MODE_NAVIGATE = 'navigate'
MODE_CREATE_LINK = 'create_link'

KIND_TILE = 'tile'
KIND_DOT = 'dot'
KIND_BACKDROP = 'backdrop'

_DEFAULT_BACKDROP_COLOR = 0x5A5A5AFF
_DOT_LABEL_SPACING = 5
_LABEL_POINT_SIZE = 8
# Bounds how long the de-overlap pass may run on a pathological pile-up; in
# practice it settles in a handful of passes.
_MAX_SEPARATION_PASSES = 400


# ---------------------------------------------------------------------------
# Layout — pure functions, no Qt and no nuke.
# ---------------------------------------------------------------------------

def compress_axis(values, scale=SPATIAL_SCALE, max_gap=SPATIAL_MAX_GAP):
    """Return {value: pixel position} keeping the order of *values* but not their gaps.

    Each gap between neighbouring distinct values is scaled by *scale* and then
    capped at *max_gap*, so near neighbours keep their proportions while a wide
    empty stretch of DAG collapses to a short one.
    """
    positions = {}
    position = 0.0
    previous_value = None
    for value in sorted(set(values)):
        if previous_value is not None:
            position += min((value - previous_value) * scale, max_gap)
        positions[value] = position
        previous_value = value
    return positions


def _area(backdrop):
    return backdrop['width'] * backdrop['height']


def _contains_point(backdrop, x, y):
    return (backdrop['x'] <= x < backdrop['x'] + backdrop['width']
            and backdrop['y'] <= y < backdrop['y'] + backdrop['height'])


def _contains_backdrop(outer, inner):
    if outer['key'] == inner['key']:
        return False
    if (_area(outer), str(outer['key'])) <= (_area(inner), str(inner['key'])):
        return False
    return (outer['x'] <= inner['x']
            and outer['y'] <= inner['y']
            and inner['x'] + inner['width'] <= outer['x'] + outer['width']
            and inner['y'] + inner['height'] <= outer['y'] + outer['height'])


def _smallest(backdrops):
    if not backdrops:
        return None
    return min(backdrops, key=lambda backdrop: (_area(backdrop), str(backdrop['key'])))


def _centre(item):
    if item['kind'] == KIND_BACKDROP:
        return item['x'] + item['width'] / 2.0, item['y'] + item['height'] / 2.0
    return item['x'], item['y']


def _translate(rects, descendants, key, dx, dy):
    for moved_key in [key] + descendants.get(key, []):
        x, y, width, height = rects[moved_key]
        rects[moved_key] = (x + dx, y + dy, width, height)


def _separate(keys, rects, descendants, gap=SPATIAL_ITEM_GAP):
    """Push the rectangles of *keys* apart until none overlap (with *gap* clearance).

    Each overlapping pair is split half each way along the axis where the pair
    overlaps least *relative to its size*: tiles are far wider than tall, so the
    raw smaller push would stack side-by-side neighbours vertically and lose
    the left/right relationship the DAG gave them.  A key with descendants (a
    backdrop frame) moves as a rigid group with everything inside it.
    """
    for _pass in range(_MAX_SEPARATION_PASSES):
        moved = False
        order = sorted(keys, key=lambda key: (rects[key][0], str(key)))
        for index, first in enumerate(order):
            for second in order[index + 1:]:
                ax, ay, aw, ah = rects[first]
                bx, by, bw, bh = rects[second]
                if bx >= ax + aw + gap:
                    break
                if ax + aw / 2.0 <= bx + bw / 2.0:
                    push_x = ax + aw + gap - bx
                    sign_x = 1
                else:
                    push_x = bx + bw + gap - ax
                    sign_x = -1
                if ay + ah / 2.0 <= by + bh / 2.0:
                    push_y = ay + ah + gap - by
                    sign_y = 1
                else:
                    push_y = by + bh + gap - ay
                    sign_y = -1
                if push_x <= 0 or push_y <= 0:
                    continue
                if push_x / (aw + bw) <= push_y / (ah + bh):
                    half = push_x / 2.0
                    _translate(rects, descendants, first, -sign_x * half, 0)
                    _translate(rects, descendants, second, sign_x * half, 0)
                else:
                    half = push_y / 2.0
                    _translate(rects, descendants, first, 0, -sign_y * half)
                    _translate(rects, descendants, second, 0, sign_y * half)
                moved = True
        if not moved:
            return


def _bounding_box(rect_list):
    left = min(x for x, _y, _w, _h in rect_list)
    top = min(y for _x, y, _w, _h in rect_list)
    right = max(x + w for x, _y, w, _h in rect_list)
    bottom = max(y + h for _x, y, _w, h in rect_list)
    return left, top, right, bottom


def build_layout(items,
                 scale=SPATIAL_SCALE,
                 max_gap=SPATIAL_MAX_GAP,
                 padding=SPATIAL_BACKDROP_PADDING,
                 header=SPATIAL_BACKDROP_HEADER,
                 gap=SPATIAL_ITEM_GAP):
    """Place *items* on the map.

    Parameters
    ----------
    items : sequence of dict
        Every item has 'key' and 'kind'.  Tiles and dots carry 'x' / 'y' (their
        DAG centre), 'size' (width, height in pixels) and 'origin' (the pixel
        offset of the DAG centre inside that box — a dot's circle sits at the
        left of its box, its label to the right).  Backdrops carry their DAG
        bounds 'x' / 'y' / 'width' / 'height', 'size' (the box drawn when they
        enclose no anchor) and 'min_width' (room for their label when drawn as a
        frame).

    Returns
    -------
    dict
        ``rects``   {key: (x, y, width, height)} in pixels, top-left at (0, 0).
        ``frames``  keys of the backdrops drawn as frames around anchors; every
                    other backdrop is drawn as a box of its own.
        ``depth``   {frame key: nesting depth}, outermost 0, for draw order.
        ``parent``  {key: key of the frame drawn around it, or None}.
        ``width`` / ``height``  the extent of the map.
    """
    if not items:
        return {'rects': {}, 'frames': set(), 'depth': {}, 'parent': {},
                'width': 0, 'height': 0}

    items_by_key = {item['key']: item for item in items}
    backdrops = [item for item in items if item['kind'] == KIND_BACKDROP]
    anchors = [item for item in items if item['kind'] != KIND_BACKDROP]

    # Same rule as link.find_smallest_containing_backdrop: the innermost
    # backdrop around a node is the one it belongs to.
    anchor_container = {
        anchor['key']: _smallest([b for b in backdrops if _contains_point(b, anchor['x'], anchor['y'])])
        for anchor in anchors
    }
    backdrop_container = {
        backdrop['key']: _smallest([b for b in backdrops if _contains_backdrop(b, backdrop)])
        for backdrop in backdrops
    }

    frames = set()
    for container in anchor_container.values():
        while container is not None and container['key'] not in frames:
            frames.add(container['key'])
            container = backdrop_container[container['key']]

    def framing_parent(container):
        while container is not None and container['key'] not in frames:
            container = backdrop_container[container['key']]
        return container['key'] if container is not None else None

    parent = {}
    for anchor in anchors:
        parent[anchor['key']] = framing_parent(anchor_container[anchor['key']])
    for backdrop in backdrops:
        parent[backdrop['key']] = framing_parent(backdrop_container[backdrop['key']])

    leaves = [item for item in items if item['key'] not in frames]
    leaf_centres = {leaf['key']: _centre(leaf) for leaf in leaves}
    x_positions = compress_axis([x for x, _y in leaf_centres.values()], scale, max_gap)
    y_positions = compress_axis([y for _x, y in leaf_centres.values()], scale, max_gap)

    rects = {}
    for leaf in leaves:
        centre_x, centre_y = leaf_centres[leaf['key']]
        width, height = leaf['size']
        if leaf['kind'] == KIND_BACKDROP:
            origin_x, origin_y = width / 2.0, height / 2.0
        else:
            origin_x, origin_y = leaf['origin']
        rects[leaf['key']] = (x_positions[centre_x] - origin_x,
                              y_positions[centre_y] - origin_y,
                              width, height)

    children = {}
    for key, parent_key in parent.items():
        children.setdefault(parent_key, []).append(key)
    for child_keys in children.values():
        child_keys.sort(key=lambda key: (_centre(items_by_key[key])[1],
                                         _centre(items_by_key[key])[0], str(key)))

    depth = {}
    for frame_key in frames:
        level = 0
        ancestor = parent[frame_key]
        while ancestor is not None:
            level += 1
            ancestor = parent[ancestor]
        depth[frame_key] = level

    descendants = {}
    for frame_key in sorted(frames, key=lambda key: (-depth[key], str(key))):
        child_keys = children.get(frame_key, [])
        _separate(child_keys, rects, descendants, gap)
        descendants[frame_key] = []
        for child_key in child_keys:
            descendants[frame_key].append(child_key)
            descendants[frame_key].extend(descendants.get(child_key, []))
        left, top, right, bottom = _bounding_box([rects[key] for key in child_keys])
        width = max(right - left + 2 * padding, items_by_key[frame_key].get('min_width', 0))
        rects[frame_key] = (left - padding, top - padding - header,
                            width, bottom - top + 2 * padding + header)

    _separate(children.get(None, []), rects, descendants, gap)

    left, top, right, bottom = _bounding_box(list(rects.values()))
    rects = {key: (x - left, y - top, w, h) for key, (x, y, w, h) in rects.items()}
    return {
        'rects': rects,
        'frames': frames,
        'depth': depth,
        'parent': parent,
        'width': right - left,
        'height': bottom - top,
    }


# ---------------------------------------------------------------------------
# Item collection — reads nodes, not Qt.
# ---------------------------------------------------------------------------

def display_name_for(item):
    """Return the name the picker lists *item* under — the leaf of its menu path."""
    return item['menupath'].rpartition('/')[2]


def node_color(node):
    """Return the 0xRRGGBBAA colour to draw *node* with.

    Uses the colour the node carries; an uncoloured anchor falls back to the
    colour the DAG would give it, so the map reads like the nodes it stands for.
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


def rgb_for(color_int):
    from colors import _color_int_to_rgb
    return _color_int_to_rgb(color_int)


def is_light(color_int):
    """Return True when dark text reads better than light text on *color_int*."""
    red, green, blue = rgb_for(color_int)
    return 0.299 * red + 0.587 * green + 0.114 * blue > 140


def _is_local_dot(node):
    if node.Class() != 'Dot':
        return False
    import link
    try:
        return link.is_link(node) or bool(node['hide_input'].getValue())
    except Exception:
        return False


def _kind_for(node):
    node_class = node.Class()
    if node_class == 'BackdropNode':
        return KIND_BACKDROP
    if node_class == 'Dot':
        return KIND_DOT
    return KIND_TILE


def dot_tier(font_size):
    """Return the index into SPATIAL_DOT_TIERS whose label size *font_size* is nearest."""
    return min(range(len(SPATIAL_DOT_TIERS)),
               key=lambda index: abs(SPATIAL_DOT_TIERS[index][0] - font_size))


def _dot_tier_for(node):
    try:
        return dot_tier(float(node['note_font_size'].value()))
    except (NameError, TypeError, ValueError):
        return 0


def _make_entry(node, item, selectable):
    kind = _kind_for(node)
    return {
        'key': node.name(),
        'name': display_name_for(item),
        'kind': kind,
        'tier': _dot_tier_for(node) if kind == KIND_DOT else None,
        'node': node,
        'item': item,
        'selectable': selectable,
        'color': node_color(node),
    }


def collect_entries(items, mode, hit_group):
    """Return the map entries for the picker *items* in *mode*.

    Each entry is keyed by node name, which is how the picker's matched rows are
    tied back to map items.  Local Dots never appear.  In link-creation mode the
    picker lists anchors only, so the labelled backdrops are added as
    unselectable landmarks — without them the map would lose its modules.
    """
    entries = []
    listed_names = set()
    for item in items:
        node = item['menuobj']
        if _is_local_dot(node):
            continue
        entries.append(_make_entry(node, item, selectable=True))
        listed_names.add(node.name())

    if mode == MODE_CREATE_LINK:
        with (hit_group or nuke.root()):
            context_backdrops = [
                backdrop for backdrop in nuke.allNodes('BackdropNode')
                if backdrop['label'].value().strip()
                and backdrop.name() not in listed_names
            ]
        for backdrop in context_backdrops:
            item = {'menuobj': backdrop,
                    'menupath': 'Backdrops/' + backdrop['label'].value().strip()}
            entries.append(_make_entry(backdrop, item, selectable=False))

    return entries


def layout_items_for(entries, text_width):
    """Turn *entries* into ``build_layout`` items.

    *text_width(text, point_size)* returns the pixel width of a label; tiles and
    backdrop labels use _LABEL_POINT_SIZE, dot labels their tier's size.
    """
    empty_backdrop_size = (SPATIAL_TILE_WIDTH * SPATIAL_EMPTY_BACKDROP_SCALE,
                           SPATIAL_TILE_HEIGHT * SPATIAL_EMPTY_BACKDROP_SCALE)
    items = []
    for entry in entries:
        node = entry['node']
        if entry['kind'] == KIND_BACKDROP:
            items.append({
                'key': entry['key'],
                'kind': KIND_BACKDROP,
                'x': node.xpos(),
                'y': node.ypos(),
                'width': node['bdwidth'].value(),
                'height': node['bdheight'].value(),
                'size': empty_backdrop_size,
                'min_width': (text_width(entry['name'], _LABEL_POINT_SIZE)
                              + 2 * SPATIAL_BACKDROP_PADDING),
            })
            continue
        centre_x = node.xpos() + node.screenWidth() / 2.0
        centre_y = node.ypos() + node.screenHeight() / 2.0
        if entry['kind'] == KIND_DOT:
            _font_size, diameter, point_size = SPATIAL_DOT_TIERS[entry['tier']]
            height = max(diameter, point_size * 2)
            width = diameter + _DOT_LABEL_SPACING + text_width(entry['name'], point_size)
            origin = (diameter / 2.0, height / 2.0)
        else:
            width, height = SPATIAL_TILE_WIDTH, SPATIAL_TILE_HEIGHT
            origin = (width / 2.0, height / 2.0)
        items.append({
            'key': entry['key'],
            'kind': entry['kind'],
            'x': centre_x,
            'y': centre_y,
            'size': (width, height),
            'origin': origin,
        })
    return items


def host_main_window():
    return _tabtabtab._find_host_main_window()


def space_mode_order():
    import anchor
    return anchor._current_space_mode_order()


def _plugin_for_mode(mode):
    import anchor
    if mode == MODE_CREATE_LINK:
        return anchor._make_anchor_picker_plugin()
    return anchor._make_anchor_navigate_plugin()


# ---------------------------------------------------------------------------
# Qt widgets — only defined when Qt is importable (headless `nuke -t` is not).
# ---------------------------------------------------------------------------

if QtWidgets is None:
    MapCanvas = None
    SpatialPicker = None
else:
    _MAP_MARGIN = 10
    _BACKGROUND = QtGui.QColor(38, 38, 38)
    # The leader overlay's backdrop colour, opaque: Nuke's own grey would make the
    # popup's border vanish against the DAG.
    _POPUP_BACKGROUND = QtGui.QColor(20, 20, 20)
    _DIMMED = QtGui.QColor(70, 70, 70)
    _DIMMED_TEXT = QtGui.QColor(120, 120, 120)
    _HIGHLIGHT = QtGui.QColor(255, 255, 255)
    _DOT_LABEL_TEXT = QtGui.QColor(220, 220, 220)

    def _qcolor(color_int, alpha=255):
        red, green, blue = rgb_for(color_int)
        return QtGui.QColor(red, green, blue, alpha)

    def _label_font(bold=False, italic=False, point_size=_LABEL_POINT_SIZE):
        font = QtGui.QFont()
        font.setPointSize(point_size)
        font.setBold(bold)
        font.setItalic(italic)
        return font

    def _available_screen_rect():
        cursor_position = QtGui.QCursor.pos()
        screen = None
        if hasattr(QtWidgets.QApplication, 'screenAt'):
            screen = QtWidgets.QApplication.screenAt(cursor_position)
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    class MapCanvas(QtWidgets.QWidget):
        """Paints the map and turns clicks on it into picks."""

        def __init__(self, parent=None):
            super(MapCanvas, self).__init__(parent)
            self.setMouseTracking(True)
            self.on_activate = None
            self._entries = {}
            self._rects = {}
            self._frames = set()
            self._depth = {}
            self._matched = set()
            self._highlighted_key = None

        def set_entries(self, entries):
            self.unsetCursor()

            def text_width(text, point_size):
                metrics = QtGui.QFontMetrics(_label_font(bold=True, point_size=point_size))
                if hasattr(metrics, 'horizontalAdvance'):
                    return metrics.horizontalAdvance(text)
                return metrics.width(text)

            self._entries = {entry['key']: entry for entry in entries}
            layout = build_layout(layout_items_for(entries, text_width))
            self._rects = {
                key: QtCore.QRectF(x + _MAP_MARGIN, y + _MAP_MARGIN, width, height)
                for key, (x, y, width, height) in layout['rects'].items()
            }
            self._frames = layout['frames']
            self._depth = layout['depth']
            self._highlighted_key = None
            self.setFixedSize(int(layout['width']) + 2 * _MAP_MARGIN + 1,
                              int(layout['height']) + 2 * _MAP_MARGIN + 1)
            self.update()

        def set_matched(self, keys):
            self._matched = set(keys)
            self.update()

        def set_highlighted(self, key):
            """Highlight *key*; return its rect so the caller can scroll to it."""
            self._highlighted_key = key
            self.update()
            return self._rects.get(key)

        def entry(self, key):
            return self._entries.get(key)

        def _lit(self, key):
            return key in self._matched or not self._entries[key]['selectable']

        # -- painting ----------------------------------------------------------

        def paintEvent(self, event):  # noqa: N802 — Qt naming
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(self.rect(), _BACKGROUND)

            for key in sorted(self._frames, key=lambda key: self._depth[key]):
                self._paint_frame(painter, key)
            for key, entry in self._entries.items():
                if entry['kind'] == KIND_BACKDROP and key not in self._frames:
                    self._paint_empty_backdrop(painter, key)
            for key, entry in self._entries.items():
                if entry['kind'] == KIND_DOT:
                    self._paint_dot(painter, key)
                elif entry['kind'] == KIND_TILE:
                    self._paint_tile(painter, key)
            painter.end()

        def _paint_frame(self, painter, key):
            entry = self._entries[key]
            rect = self._rects[key]
            lit = self._lit(key)
            color = _qcolor(entry['color']) if lit else _DIMMED
            fill = QtGui.QColor(color)
            fill.setAlpha(70 if lit else 40)
            painter.setBrush(fill)
            if key == self._highlighted_key:
                painter.setPen(QtGui.QPen(_HIGHLIGHT, 2.5))
            else:
                painter.setPen(QtGui.QPen(color.lighter(130), 1.5))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

            painter.setFont(_label_font(bold=True))
            painter.setPen(color.lighter(170) if lit else _DIMMED_TEXT)
            header = QtCore.QRectF(rect.left() + SPATIAL_BACKDROP_PADDING, rect.top() + 2,
                                   rect.width() - 2 * SPATIAL_BACKDROP_PADDING,
                                   SPATIAL_BACKDROP_HEADER)
            painter.drawText(header, int(Qt.AlignVCenter | Qt.AlignLeft),
                             self._elided(entry['name'], header.width()))

        def _paint_empty_backdrop(self, painter, key):
            entry = self._entries[key]
            rect = self._rects[key]
            lit = self._lit(key)
            highlighted = key == self._highlighted_key
            painter.save()
            painter.setOpacity(1.0 if highlighted else (0.5 if lit else 0.25))
            color = _qcolor(entry['color']) if lit else _DIMMED
            fill = QtGui.QColor(color)
            fill.setAlpha(80)
            painter.setBrush(fill)
            pen = QtGui.QPen(_HIGHLIGHT if highlighted else color.lighter(140),
                             2 if highlighted else 1.2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)
            painter.setFont(_label_font(italic=True))
            painter.setPen(QtGui.QColor(230, 230, 230) if lit else _DIMMED_TEXT)
            text_rect = rect.adjusted(6, 4, -6, -4)
            painter.drawText(text_rect, int(Qt.AlignCenter),
                             self._elided(entry['name'], text_rect.width()))
            painter.restore()

        def _paint_tile(self, painter, key):
            entry = self._entries[key]
            rect = self._rects[key]
            lit = self._lit(key)
            if lit:
                painter.setBrush(_qcolor(entry['color']))
                text_color = QtGui.QColor(17, 17, 17) if is_light(entry['color']) \
                    else QtGui.QColor(238, 238, 238)
            else:
                painter.setBrush(_DIMMED)
                text_color = _DIMMED_TEXT
            if key == self._highlighted_key:
                painter.setPen(QtGui.QPen(_HIGHLIGHT, 2.5))
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 90), 1))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
            painter.setFont(_label_font(bold=True))
            painter.setPen(text_color)
            text_rect = rect.adjusted(5, 0, -5, 0)
            painter.drawText(text_rect, int(Qt.AlignCenter),
                             self._elided(entry['name'], text_rect.width()))

        def _paint_dot(self, painter, key):
            entry = self._entries[key]
            rect = self._rects[key]
            lit = self._lit(key)
            highlighted = key == self._highlighted_key
            _font_size, diameter, point_size = SPATIAL_DOT_TIERS[entry['tier']]
            circle = QtCore.QRectF(rect.left(), rect.center().y() - diameter / 2.0,
                                   diameter, diameter)
            painter.setBrush(_qcolor(entry['color']) if lit else _DIMMED)
            if highlighted:
                painter.setPen(QtGui.QPen(_HIGHLIGHT, 2.5))
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 120), 1))
            painter.drawEllipse(circle)
            painter.setFont(_label_font(bold=highlighted, point_size=point_size))
            painter.setPen(_HIGHLIGHT if highlighted else (_DOT_LABEL_TEXT if lit else _DIMMED_TEXT))
            text_rect = QtCore.QRectF(circle.right() + _DOT_LABEL_SPACING, rect.top(),
                                      rect.right() - circle.right(), rect.height())
            painter.drawText(text_rect, int(Qt.AlignVCenter | Qt.AlignLeft), entry['name'])

        def _elided(self, text, width):
            metrics = QtGui.QFontMetrics(_label_font(bold=True))
            return metrics.elidedText(text, Qt.ElideRight, int(width))

        # -- mouse -------------------------------------------------------------

        def key_at(self, point):
            """Return the key of the topmost item under *point*, or None."""
            for key in self._entries:
                if key not in self._frames and self._rects[key].contains(point):
                    return key
            for key in sorted(self._frames, key=lambda key: -self._depth[key]):
                if self._rects[key].contains(point):
                    return key
            return None

        def _selectable_key_at(self, point):
            key = self.key_at(point)
            if key is None or not self._entries[key]['selectable']:
                return None
            return key

        def mouseMoveEvent(self, event):  # noqa: N802 — Qt naming
            if self._selectable_key_at(QtCore.QPointF(event.pos())) is not None:
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.unsetCursor()

        def leaveEvent(self, event):  # noqa: N802 — Qt naming
            self.unsetCursor()

        def mousePressEvent(self, event):  # noqa: N802 — Qt naming
            key = self._selectable_key_at(QtCore.QPointF(event.pos()))
            if key is not None and self.on_activate is not None:
                # Picking closes the popup under a still mouse, so no leave or
                # move event arrives to put the cursor back.
                self.unsetCursor()
                self.on_activate(key)

    class SpatialPicker(_tabtabtab.TabTabTabWidget):
        """The anchor picker with a map of the script beside its search panel."""

        def __init__(self, plugin, mode, parent=None, space_mode_order=None):
            # Qt.Dialog keeps this a top-level window even with the host main
            # window as parent — see _create_tabtabtab_widget in
            # tabtabtab_anchors.py for why dropping it breaks click-outside.
            super(SpatialPicker, self).__init__(
                plugin,
                parent=parent,
                winflags=Qt.Dialog | Qt.FramelessWindowHint,
                space_mode_order=space_mode_order,
            )
            self.setObjectName('SpatialPicker')
            palette = self.palette()
            palette.setColor(QtGui.QPalette.Window, _POPUP_BACKGROUND)
            self.setPalette(palette)
            self.setAutoFillBackground(True)
            self.mode = mode
            self.map_canvas.on_activate = self.activate_key

        def _build_layout(self):
            self.map_canvas = MapCanvas()
            self._map_scroll = QtWidgets.QScrollArea()
            self._map_scroll.setWidget(self.map_canvas)
            self._map_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
            self._map_scroll.setAlignment(Qt.AlignCenter)
            self._map_scroll.setStyleSheet(
                "QScrollArea, QScrollArea > QWidget > QWidget { background: rgb(%d, %d, %d); }"
                % (_BACKGROUND.red(), _BACKGROUND.green(), _BACKGROUND.blue()))

            search_panel = QtWidgets.QWidget()
            search_panel.setFixedWidth(SPATIAL_SEARCH_PANEL_WIDTH)
            search_layout = QtWidgets.QVBoxLayout(search_panel)
            search_layout.setContentsMargins(0, 0, 0, 0)
            search_layout.addStretch(1)
            search_layout.addWidget(self.input)
            search_layout.addWidget(self.things)
            search_layout.addStretch(1)

            layout = QtWidgets.QHBoxLayout()
            layout.addWidget(search_panel)
            layout.addWidget(self._map_scroll, 1)
            return layout

        # -- keeping the map in step with the list -----------------------------

        def update(self, text):
            super(SpatialPicker, self).update(text)
            self._sync_map()

        def move_selection(self, where):
            super(SpatialPicker, self).move_selection(where)
            self._sync_highlight()

        def _matched_item_key(self, item):
            try:
                return item['menuobj'].name()
            except ValueError:
                return None

        def _sync_map(self):
            self.map_canvas.set_matched(
                self._matched_item_key(item) for item in self.things_model._items)
            self._sync_highlight()

        def _sync_highlight(self):
            key = None
            index = self.things.currentIndex()
            if index.isValid() and index.row() < len(self.things_model._items):
                key = self._matched_item_key(self.things_model._items[index.row()])
            rect = self.map_canvas.set_highlighted(key)
            if rect is not None:
                centre = rect.center()
                self._map_scroll.ensureVisible(
                    int(centre.x()), int(centre.y()),
                    int(rect.width() / 2) + 20, int(rect.height() / 2) + 20)

        def activate_key(self, key):
            """Pick the map item *key* exactly as if its row had been chosen."""
            entry = self.map_canvas.entry(key)
            if entry is None or not entry['selectable']:
                return
            self.plugin.invoke(entry['item'])
            self.weights.increment(entry['item']['menupath'])
            self.close()

        # -- showing -----------------------------------------------------------

        def show(self):
            """Rebuild the list and the map from the script, then show.

            The base picker defers its item refresh until after it is on screen;
            here the items are needed up front, because the map decides the
            popup's size and position.
            """
            self.weights.load()
            items = self.plugin.get_items()
            self.things_model.refresh_items(items)
            self.map_canvas.set_entries(
                collect_entries(items, self.mode, self.plugin._hit_group))
            self._fit_to_screen()
            self.under_cursor()
            super(SpatialPicker, self).show()
            self._sync_map()

        def _refresh_after_show(self):
            self.move_selection(where="first")

        def _fit_to_screen(self):
            available = _available_screen_rect()
            canvas_size = self.map_canvas.size()
            if available is None:
                self._map_scroll.setFixedSize(canvas_size)
                self.adjustSize()
                return
            margins = self.layout().contentsMargins()
            chrome_width = (SPATIAL_SEARCH_PANEL_WIDTH + self.layout().spacing()
                            + margins.left() + margins.right())
            chrome_height = margins.top() + margins.bottom()
            max_width = int(available.width() * SPATIAL_MAX_SCREEN_FRACTION) - chrome_width
            max_height = int(available.height() * SPATIAL_MAX_SCREEN_FRACTION) - chrome_height
            scrollbar = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
            width = canvas_size.width()
            height = canvas_size.height()
            if height > max_height:
                width += scrollbar
            if width > max_width:
                height += scrollbar
            self._map_scroll.setFixedSize(min(width, max_width), min(height, max_height))
            self.adjustSize()

        def under_cursor(self):
            """Put the search field under the cursor, as the plain picker does."""
            available = _available_screen_rect()
            if available is None:
                return
            self.layout().activate()
            input_centre = self.input.mapTo(
                self, QtCore.QPoint(self.input.width() // 2, self.input.height() // 2))
            cursor_position = QtGui.QCursor.pos()
            x_position = cursor_position.x() - input_centre.x()
            y_position = cursor_position.y() - input_centre.y()
            x_position = max(available.left(),
                             min(x_position, available.right() - self.width()))
            y_position = max(available.top(),
                             min(y_position, available.bottom() - self.height()))
            self.move(x_position, y_position)


# ---------------------------------------------------------------------------
# Entry point — called by the A / Alt+A pickers when the preference is on.
# ---------------------------------------------------------------------------

_pickers = {}


def open_picker(mode, hit_group, plugin=None):
    """Show the spatial picker for *mode* in *hit_group*; return it, or None without Qt.

    *plugin* overrides what picking does (the leader's Set Input To… commands
    pass their own); by default it is the plugin of the matching plain picker.
    One picker is kept per mode and reused, like the plain pickers; its list and
    map are rebuilt from the script on every show.
    """
    if SpatialPicker is None:
        return None
    if plugin is None:
        plugin = _plugin_for_mode(mode)
    plugin._hit_group = hit_group
    picker = _pickers.get(mode)
    if picker is not None:
        try:
            picker.isVisible()
        except RuntimeError:
            picker = None
    if picker is None:
        picker = SpatialPicker(plugin, mode,
                               parent=host_main_window(),
                               space_mode_order=space_mode_order())
        _pickers[mode] = picker
    else:
        picker.plugin = plugin
        picker.things_model._space_mode_order = space_mode_order()
    picker.show()
    picker.raise_()
    return picker
