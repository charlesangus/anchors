"""Spatial view — a map of the script beside the ``A`` / ``Alt``+``A`` pickers.

With **Show the spatial view beside the A and Alt+A menus** ticked in
Preferences, the two anchor pickers open as a wider popup: the usual search
field and list on the left, and on the right a map of the current group — anchors as coloured tiles, Dot anchors as small
circles with their label beside them, and labelled backdrops as frames around
what they really enclose.  Recognising a place is faster than recalling a name.

The map keeps the script's real arrangement but squeezes out the empty space
between items (``compress_axis``), packing them only as close as their order
allows so that nothing collides and nothing changes places (``build_layout``).
Typing in the search field filters the list exactly as before and dims the map
items that no longer match; the row highlighted in the list is highlighted on
the map, and clicking a map item picks it as if its row had been chosen.

``SpatialPicker`` is the tabtabtab picker widget itself with the map added, so
the search, the item list, the selection weights, and what picking an item does
are all the pickers' own.  The layout maths is in module-level functions so it
can be unit-tested without a Qt session.
"""

import heapq

import nuke

try:
    if hasattr(nuke, 'NUKE_VERSION_MAJOR') and nuke.NUKE_VERSION_MAJOR >= 16:
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
    else:
        from PySide2 import QtCore, QtGui, QtWidgets
        from PySide2.QtCore import Qt
    import tabtabtab_anchors as _tabtabtab
except ImportError:
    QtCore = None
    QtGui = None
    QtWidgets = None
    Qt = None
    _tabtabtab = None

from constants import (
    ANCHOR_DEFAULT_COLOR,
    SPATIAL_BACKDROP_HEADER,
    SPATIAL_BACKDROP_PADDING,
    SPATIAL_DOT_TIERS,
    SPATIAL_EMPTY_BACKDROP_SCALE,
    SPATIAL_ITEM_GAP,
    SPATIAL_MAX_GAP,
    SPATIAL_MAX_SCREEN_FRACTION,
    SPATIAL_MAX_USER_ZOOM,
    SPATIAL_MIN_FIT_ZOOM,
    SPATIAL_MIN_USER_ZOOM,
    SPATIAL_SCALE,
    SPATIAL_SEARCH_PANEL_WIDTH,
    SPATIAL_TILE_HEIGHT,
    SPATIAL_TILE_WIDTH,
    SPATIAL_VIEW_ANIMATION_MS,
    SPATIAL_ZOOM_STEP,
)

MODE_NAVIGATE = 'navigate'
MODE_CREATE_LINK = 'create_link'

KIND_TILE = 'tile'
KIND_DOT = 'dot'
KIND_BACKDROP = 'backdrop'

_DEFAULT_BACKDROP_COLOR = 0x5A5A5AFF
_DOT_LABEL_SPACING = 5
_LABEL_POINT_SIZE = 8


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


def _dag_box(item):
    """Return the (left, top, right, bottom) *item* covers in the DAG."""
    if item['kind'] == KIND_BACKDROP:
        return (item['x'], item['y'],
                item['x'] + item['width'], item['y'] + item['height'])
    half_width, half_height = (size / 2.0 for size in item.get('dag_size', (0, 0)))
    return (item['x'] - half_width, item['y'] - half_height,
            item['x'] + half_width, item['y'] + half_height)


def _translate(rects, descendants, key, dx, dy):
    for moved_key in [key] + descendants.get(key, []):
        x, y, width, height = rects[moved_key]
        rects[moved_key] = (x + dx, y + dy, width, height)


def _separation_axis(first_box, second_box, first_size, second_size):
    """Return 0 (x) or 1 (y): the axis along which two siblings are kept apart.

    It is the axis along which the DAG already separates them most, relative to
    their size on the map: tiles are far wider than tall, so a raw comparison
    would stack side-by-side neighbours and lose their left/right relationship.
    """
    clearances = []
    for axis in (0, 1):
        clearance = max(second_box[axis] - first_box[axis + 2],
                        first_box[axis] - second_box[axis + 2])
        clearances.append(clearance / float(first_size[axis] + second_size[axis]))
    return 0 if clearances[0] >= clearances[1] else 1


def _place_siblings(keys, dag_boxes, sizes, origins, block_probes, scale, max_gap, gap):
    """Return {key: (left, top)} for sibling items packed as tightly as their order allows.

    Each pair is kept apart along one axis (see ``_separation_axis``) and so
    never overlaps.  Rows are settled first: a pair side by side in the DAG is
    always kept side by side, but a pair lying diagonally is only pushed apart
    sideways if their rows still overlap on the map.  See ``_pack_axis`` for how
    each axis is packed.
    """
    separation_axis = {}
    for first, second in _pairs(keys):
        axis = _separation_axis(dag_boxes[first], dag_boxes[second],
                                sizes[first], sizes[second])
        separation_axis[first, second] = separation_axis[second, first] = axis

    kept_apart = {pair for pair, axis in separation_axis.items() if axis == 1}
    tops = _pack_axis(keys, 1, dag_boxes, sizes, origins, block_probes, kept_apart,
                      scale, max_gap, gap)
    tops = {key: tops[key] - origins[key][1] for key in keys}

    def rows_overlap(first, second):
        if (dag_boxes[first][1] < dag_boxes[second][3]
                and dag_boxes[second][1] < dag_boxes[first][3]):
            return True
        return (tops[first] < tops[second] + sizes[second][1] + gap
                and tops[second] < tops[first] + sizes[first][1] + gap)

    kept_apart = {pair for pair, axis in separation_axis.items()
                  if axis == 0 and rows_overlap(*pair)}
    lefts = _pack_axis(keys, 0, dag_boxes, sizes, origins, block_probes, kept_apart,
                       scale, max_gap, gap)
    return {key: (lefts[key] - origins[key][0], tops[key]) for key in keys}


def _pack_axis(keys, axis, dag_boxes, sizes, origins, block_probes, kept_apart,
               scale, max_gap, gap):
    """Return {key: anchor position along *axis*}, each as far back as these allow.

    - A pair in *kept_apart* is at least the ``compress_axis`` spacing of their
      DAG centres apart, and clears by *gap*.
    - Two single items keep the ``compress_axis`` spacing of their DAG centres,
      so the empty space between them shrinks but their order holds.
    - A frame, which moves as one block, keeps every point it carries (see
      ``_probes``) on the same side of every point its sibling carries as in the
      DAG.  Where a block and its sibling interleave, a far pair can contradict
      the rest; such a pair keeps only what can still be met, nearest pairs
      winning (see ``_add_if_consistent``).
    """
    centres = {key: (dag_boxes[key][axis] + dag_boxes[key][axis + 2]) / 2.0 for key in keys}
    order = sorted(keys, key=lambda key: (centres[key], str(key)))
    successors, interleaved = _axis_distances(order, axis, centres, dag_boxes, sizes, origins,
                                              block_probes, kept_apart, scale, max_gap, gap)

    # Everything in successors so far points forward along the order, so one
    # pass settles it.
    positions = {key: 0.0 for key in keys}
    for key in order:
        for later_key, distance in successors[key]:
            positions[later_key] = max(positions[later_key], positions[key] + distance)
    rank = {key: index for index, key in enumerate(order)}
    for _distance_apart, _first, _second, from_key, to_key, distance in sorted(interleaved):
        _add_if_consistent(positions, successors, rank, from_key, to_key, distance)
    return positions


def _axis_distances(order, axis, centres, dag_boxes, sizes, origins, block_probes, kept_apart,
                    scale, max_gap, gap):
    """Return (successors, interleaved): the least distances between siblings along *axis*.

    *successors* maps each key to [(later key, least distance ahead of it)],
    every one pointing forward along *order*.  *interleaved* lists the
    distances pointing back, from blocks interleaved with a sibling, as
    (distance apart across the axis, first key, second key, from key, to key,
    least distance) so that sorting puts the nearest pairs first.
    """
    compressed = compress_axis(centres.values(), scale, max_gap)
    points = {}
    for key in order:
        points[key] = [(probe[axis], probe[axis + 2])
                       for probe in _probes(key, dag_boxes, block_probes)]
    successors = {key: [] for key in order}
    interleaved = []
    for index, first in enumerate(order):
        for second in order[index + 1:]:
            spacing = compressed[centres[second]] - compressed[centres[first]]
            if (first, second) in kept_apart:
                clearance = (sizes[first][axis] - origins[first][axis]
                             + origins[second][axis] + gap)
                successors[first].append((second, max(spacing, clearance)))
            elif first in block_probes or second in block_probes:
                ahead, behind = _probe_distances(points[first], points[second], scale, max_gap)
                if ahead is not None:
                    successors[first].append((second, ahead))
                if behind is not None:
                    distance_apart = _box_gap(dag_boxes[first], dag_boxes[second], 1 - axis)
                    interleaved.append((distance_apart, str(first), str(second),
                                        second, first, behind))
            else:
                successors[first].append((second, spacing))
    return successors, interleaved


def _box_gap(first_box, second_box, axis):
    """The empty space between two DAG boxes along *axis*, 0 if they overlap on it."""
    return max(0, second_box[axis] - first_box[axis + 2], first_box[axis] - second_box[axis + 2])


def _probes(key, dag_boxes, block_probes):
    """The (DAG x, DAG y, map x offset, map y offset) of each point *key* keeps in order.

    A single item's point is its centre, offset 0 from its anchor point; a
    frame's are its own corners and the centres of the items inside it (see
    build_layout), offset from the frame's anchor point.
    """
    if key in block_probes:
        return block_probes[key]
    box = dag_boxes[key]
    return [((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0, 0.0, 0.0)]


def _probe_distances(first_points, second_points, scale, max_gap):
    """Return (ahead, behind): how far the second block must be ahead of the first, and vice versa.

    Points are (DAG position, map offset from the block's anchor point) along
    one axis.  A point of the first block before a point of the second in the
    DAG stays before it on the map, by half their ``compress_axis`` spacing:
    half, so that a point between two points of a block still fits between
    them however that block packed its inside.  *ahead* is the least distance
    from the first block's anchor point to the second's, *behind* the least
    from the second's to the first's; either is None when no pair of points
    asks for it, and either can be negative.
    """
    ahead = None
    behind = None
    for first_dag, first_offset in first_points:
        for second_dag, second_offset in second_points:
            if first_dag < second_dag:
                needed = (first_offset - second_offset
                          + min((second_dag - first_dag) * scale, max_gap) / 2.0)
                if ahead is None or needed > ahead:
                    ahead = needed
            elif first_dag > second_dag:
                needed = (second_offset - first_offset
                          + min((first_dag - second_dag) * scale, max_gap) / 2.0)
                if behind is None or needed > behind:
                    behind = needed
    return ahead, behind


def _add_if_consistent(positions, successors, rank, from_key, to_key, distance):
    """Ask for positions[to_key] >= positions[from_key] + distance, unless it contradicts the rest.

    *positions* is the tightest packing meeting every distance in *successors*
    ({key: [(later key, distance)]}).  The new distance is added and the
    positions pushed forward to meet it, visiting items in *rank* order so each
    is settled about once; if meeting it would push *from_key* itself forward,
    the distances contradict each other, so everything is put back and False
    returned.
    """
    pushed = {}
    pending = {to_key: positions[from_key] + distance}
    queue = [(rank[to_key], to_key)]
    while queue:
        _rank, key = heapq.heappop(queue)
        position = pending.pop(key)
        if position <= positions[key] + 1e-6:
            continue
        if key == from_key:
            positions.update(pushed)
            return False
        pushed.setdefault(key, positions[key])
        positions[key] = position
        for later_key, later_distance in successors[key]:
            candidate = position + later_distance
            if candidate <= positions[later_key] + 1e-6:
                continue
            if later_key not in pending:
                heapq.heappush(queue, (rank[later_key], later_key))
                pending[later_key] = candidate
            elif candidate > pending[later_key]:
                pending[later_key] = candidate
    successors[from_key].append((to_key, distance))
    return True


def _pairs(keys):
    for index, first in enumerate(keys):
        for second in keys[index + 1:]:
            yield first, second


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

    Frames are laid out innermost first: the items directly inside a frame are
    packed by ``_place_siblings``, the frame is sized around them, and the frame
    then moves as one block when its own siblings are packed.  Packing only
    closes up empty space, so every item keeps its position relative to its
    siblings.

    Parameters
    ----------
    items : sequence of dict
        Every item has 'key' and 'kind'.  Tiles and dots carry 'x' / 'y' (their
        DAG centre), optionally 'dag_size' (their DAG width, height), 'size'
        (width, height in pixels) and 'origin' (the pixel offset of the DAG
        centre inside that box — a dot's circle sits at the left of its box, its
        label to the right).  Backdrops carry their DAG bounds 'x' / 'y' /
        'width' / 'height', 'size' (the box drawn when they enclose no anchor)
        and 'min_width' (room for their label when drawn as a frame).

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

    children = {}
    for key, parent_key in parent.items():
        children.setdefault(parent_key, []).append(key)
    for child_keys in children.values():
        child_keys.sort(key=str)

    depth = {}
    for frame_key in frames:
        level = 0
        ancestor = parent[frame_key]
        while ancestor is not None:
            level += 1
            ancestor = parent[ancestor]
        depth[frame_key] = level

    dag_boxes = {key: _dag_box(item) for key, item in items_by_key.items()}
    sizes = {}
    origins = {}
    for item in items:
        if item['key'] in frames:
            continue
        width, height = item['size']
        sizes[item['key']] = (width, height)
        if item['kind'] == KIND_BACKDROP:
            origins[item['key']] = (width / 2.0, height / 2.0)
        else:
            origins[item['key']] = item['origin']

    rects = {}
    descendants = {}
    block_probes = {}

    def place(child_keys):
        placements = _place_siblings(child_keys, dag_boxes, sizes, origins, block_probes,
                                     scale, max_gap, gap)
        for key in child_keys:
            left, top = placements[key]
            if key in frames:
                frame_x, frame_y, _width, _height = rects[key]
                _translate(rects, descendants, key, left - frame_x, top - frame_y)
            else:
                width, height = sizes[key]
                rects[key] = (left, top, width, height)

    for frame_key in sorted(frames, key=lambda key: (-depth[key], str(key))):
        child_keys = children.get(frame_key, [])
        place(child_keys)
        descendants[frame_key] = []
        for child_key in child_keys:
            descendants[frame_key].append(child_key)
            descendants[frame_key].extend(descendants.get(child_key, []))
        left, top, right, bottom = _bounding_box([rects[key] for key in child_keys])
        width = max(right - left + 2 * padding, items_by_key[frame_key].get('min_width', 0))
        height = bottom - top + 2 * padding + header
        rects[frame_key] = (left - padding, top - padding - header, width, height)
        sizes[frame_key] = (width, height)
        origins[frame_key] = (width / 2.0, height / 2.0)
        frame_anchor_x = rects[frame_key][0] + width / 2.0
        frame_anchor_y = rects[frame_key][1] + height / 2.0
        # Its own corners, but not those of frames nested in it: those are
        # placed by their centres, so their corners need not be in order.
        box = dag_boxes[frame_key]
        x, y, width, height = rects[frame_key]
        block_probes[frame_key] = [
            (box[0], box[1], x - frame_anchor_x, y - frame_anchor_y),
            (box[2], box[3], x + width - frame_anchor_x, y + height - frame_anchor_y)]
        for key in descendants[frame_key]:
            if key in frames:
                continue
            box = dag_boxes[key]
            block_probes[frame_key].append((
                (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0,
                rects[key][0] + origins[key][0] - frame_anchor_x,
                rects[key][1] + origins[key][1] - frame_anchor_y))

    place(children.get(None, []))

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


def fit_zoom(bounds_width, bounds_height, view_width, view_height,
             min_zoom=SPATIAL_MIN_FIT_ZOOM):
    """Return the zoom that fits a *bounds* box of map into a *view*-sized window.

    Never above 1, so a small map is not blown up, and never below *min_zoom*,
    below which labels stop being readable; matches that do not fit even then
    are a scroll away.
    """
    if bounds_width <= 0 or bounds_height <= 0:
        return 1.0
    zoom = min(float(view_width) / bounds_width, float(view_height) / bounds_height)
    return max(min_zoom, min(1.0, zoom))


def clamp_user_zoom(zoom, min_zoom=SPATIAL_MIN_USER_ZOOM, max_zoom=SPATIAL_MAX_USER_ZOOM):
    """Return *zoom* limited to the range the user can zoom the map over."""
    return max(min_zoom, min(max_zoom, zoom))


def interpolate_view(start, end, progress):
    """Return the view *progress* (0 to 1) of the way from view *start* to view *end*.

    A view is ``(zoom, map_x, map_y, view_x, view_y)``: the unzoomed map point
    (map_x, map_y) shown at the viewport point (view_x, view_y) at *zoom*.  The
    zoom moves geometrically, so every frame zooms by the same factor, and the
    points move in a straight line; a zoom that keeps one map point under the
    pointer therefore keeps it there on every frame.
    """
    zoom = start[0] * (end[0] / start[0]) ** progress
    return (zoom,) + tuple(start[i] + (end[i] - start[i]) * progress for i in range(1, 5))


def visible_span(map_point, view_point, zoom, view_length, map_length):
    """Return (start, length) of the map a view shows along one axis, in unzoomed units.

    The view puts *map_point* at *view_point* as far as scrolling allows: like
    a scroll bar it stops at either end of the map, and a map no longer than
    the view shows whole.
    """
    zoomed_length = map_length * zoom
    if zoomed_length <= view_length:
        return 0.0, float(map_length)
    scroll = min(max(map_point * zoom - view_point, 0.0), zoomed_length - view_length)
    return scroll / zoom, view_length / zoom


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
            'dag_size': (node.screenWidth(), node.screenHeight()),
            'size': (width, height),
            'origin': origin,
        })
    return items


def host_main_window():
    if _tabtabtab is None:
        return None
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
    _DARK_TILE_TEXT = QtGui.QColor(17, 17, 17)
    _LIGHT_TILE_TEXT = QtGui.QColor(238, 238, 238)

    def _qcolor(color_int, alpha=255):
        red, green, blue = rgb_for(color_int)
        return QtGui.QColor(red, green, blue, alpha)

    _label_fonts = {}

    def _label_font(bold=False, italic=False, point_size=_LABEL_POINT_SIZE):
        """The label font for these settings, made once and shared: callers must not change it."""
        settings = (bold, italic, point_size)
        font = _label_fonts.get(settings)
        if font is None:
            font = QtGui.QFont()
            font.setPointSize(point_size)
            font.setBold(bold)
            font.setItalic(italic)
            _label_fonts[settings] = font
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
            self._base_size = QtCore.QSize(0, 0)
            self._with_text = True
            self.zoom = 1.0
            # Worked out once per set of entries rather than on every paint:
            # painting a big script in Python is slow enough to stutter.
            self._colors = {}
            self._light = {}
            self._elided_names = {}
            self._frame_order = []
            self._empty_backdrops = []
            self._leaves = []
            # Bumped whenever what paint_map draws changes, so the minimap
            # knows when its cached picture is stale.
            self.content_version = 0

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
            self._colors = {key: _qcolor(entry['color']) for key, entry in self._entries.items()}
            self._light = {key: is_light(entry['color']) for key, entry in self._entries.items()}
            self._elided_names = {}
            self._frame_order = sorted(self._frames, key=lambda key: self._depth[key])
            self._empty_backdrops = [key for key, entry in self._entries.items()
                                     if entry['kind'] == KIND_BACKDROP and key not in self._frames]
            self._leaves = [key for key, entry in self._entries.items()
                            if entry['kind'] in (KIND_DOT, KIND_TILE)]
            self.content_version += 1
            self._base_size = QtCore.QSize(int(layout['width']) + 2 * _MAP_MARGIN + 1,
                                           int(layout['height']) + 2 * _MAP_MARGIN + 1)
            self.set_zoom(1.0)

        def base_size(self):
            """The map's size at zoom 1."""
            return QtCore.QSize(self._base_size)

        def set_zoom(self, zoom):
            self.zoom = zoom
            self.setFixedSize(max(1, int(self._base_size.width() * zoom)),
                              max(1, int(self._base_size.height() * zoom)))
            self.update()

        def matched_bounds(self):
            """Return the unzoomed rect around every matched, selectable item, or None."""
            bounds = None
            for key in self._matched:
                entry = self._entries.get(key)
                if entry is None or not entry['selectable']:
                    continue
                rect = self._rects[key]
                bounds = rect if bounds is None else bounds.united(rect)
            return bounds

        def set_matched(self, keys):
            matched = set(keys)
            if matched != self._matched:
                self._matched = matched
                self.content_version += 1
                self.update()

        def set_highlighted(self, key):
            """Highlight *key*; return its unzoomed rect so the caller can scroll to it."""
            if key != self._highlighted_key:
                self._highlighted_key = key
                self.content_version += 1
                self.update()
            rect = self._rects.get(key)
            return QtCore.QRectF(rect) if rect is not None else None

        def entry(self, key):
            return self._entries.get(key)

        def _lit(self, key):
            return key in self._matched or not self._entries[key]['selectable']

        # -- painting ----------------------------------------------------------

        def paintEvent(self, event):  # noqa: N802 — Qt naming
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(event.rect(), _BACKGROUND)
            painter.scale(self.zoom, self.zoom)
            exposed = QtCore.QRectF(event.rect())
            self.paint_map(painter, visible=QtCore.QRectF(
                exposed.x() / self.zoom, exposed.y() / self.zoom,
                exposed.width() / self.zoom, exposed.height() / self.zoom))
            painter.end()

        def paint_map(self, painter, with_text=True, visible=None):
            """Paint the items, in unzoomed map coordinates, onto *painter*.

            With *visible* (an unzoomed rect), only the items touching it are
            painted.
            """
            if visible is not None:
                # Outlines are drawn a little outside their items' rects.
                visible = visible.adjusted(-4, -4, 4, 4)

            def shown(keys):
                if visible is None:
                    return keys
                return [key for key in keys if self._rects[key].intersects(visible)]

            self._with_text = with_text
            for key in shown(self._frame_order):
                self._paint_frame(painter, key)
            for key in shown(self._empty_backdrops):
                self._paint_empty_backdrop(painter, key)
            for key in shown(self._leaves):
                if self._entries[key]['kind'] == KIND_DOT:
                    self._paint_dot(painter, key)
                else:
                    self._paint_tile(painter, key)
            self._with_text = True

        def _paint_frame(self, painter, key):
            rect = self._rects[key]
            lit = self._lit(key)
            color = self._colors[key] if lit else _DIMMED
            fill = QtGui.QColor(color)
            fill.setAlpha(70 if lit else 40)
            painter.setBrush(fill)
            if key == self._highlighted_key:
                painter.setPen(QtGui.QPen(_HIGHLIGHT, 2.5))
            else:
                painter.setPen(QtGui.QPen(color.lighter(130), 1.5))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

            if not self._with_text:
                return
            painter.setFont(_label_font(bold=True))
            painter.setPen(color.lighter(170) if lit else _DIMMED_TEXT)
            header = QtCore.QRectF(rect.left() + SPATIAL_BACKDROP_PADDING, rect.top() + 2,
                                   rect.width() - 2 * SPATIAL_BACKDROP_PADDING,
                                   SPATIAL_BACKDROP_HEADER)
            painter.drawText(header, int(Qt.AlignVCenter | Qt.AlignLeft),
                             self._elided(key, header.width()))

        def _paint_empty_backdrop(self, painter, key):
            rect = self._rects[key]
            lit = self._lit(key)
            highlighted = key == self._highlighted_key
            painter.save()
            painter.setOpacity(1.0 if highlighted else (0.5 if lit else 0.25))
            color = self._colors[key] if lit else _DIMMED
            fill = QtGui.QColor(color)
            fill.setAlpha(80)
            painter.setBrush(fill)
            pen = QtGui.QPen(_HIGHLIGHT if highlighted else color.lighter(140),
                             2 if highlighted else 1.2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)
            if not self._with_text:
                painter.restore()
                return
            painter.setFont(_label_font(italic=True))
            painter.setPen(QtGui.QColor(230, 230, 230) if lit else _DIMMED_TEXT)
            text_rect = rect.adjusted(6, 4, -6, -4)
            painter.drawText(text_rect, int(Qt.AlignCenter), self._elided(key, text_rect.width()))
            painter.restore()

        def _paint_tile(self, painter, key):
            rect = self._rects[key]
            lit = self._lit(key)
            if lit:
                painter.setBrush(self._colors[key])
                text_color = _DARK_TILE_TEXT if self._light[key] else _LIGHT_TILE_TEXT
            else:
                painter.setBrush(_DIMMED)
                text_color = _DIMMED_TEXT
            if key == self._highlighted_key:
                painter.setPen(QtGui.QPen(_HIGHLIGHT, 2.5))
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 90), 1))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
            if not self._with_text:
                return
            painter.setFont(_label_font(bold=True))
            painter.setPen(text_color)
            text_rect = rect.adjusted(5, 0, -5, 0)
            painter.drawText(text_rect, int(Qt.AlignCenter), self._elided(key, text_rect.width()))

        def _paint_dot(self, painter, key):
            entry = self._entries[key]
            rect = self._rects[key]
            lit = self._lit(key)
            highlighted = key == self._highlighted_key
            _font_size, diameter, point_size = SPATIAL_DOT_TIERS[entry['tier']]
            circle = QtCore.QRectF(rect.left(), rect.center().y() - diameter / 2.0,
                                   diameter, diameter)
            painter.setBrush(self._colors[key] if lit else _DIMMED)
            if highlighted:
                painter.setPen(QtGui.QPen(_HIGHLIGHT, 2.5))
            else:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 120), 1))
            painter.drawEllipse(circle)
            if not self._with_text:
                return
            painter.setFont(_label_font(bold=highlighted, point_size=point_size))
            painter.setPen(_HIGHLIGHT if highlighted else (_DOT_LABEL_TEXT if lit else _DIMMED_TEXT))
            text_rect = QtCore.QRectF(circle.right() + _DOT_LABEL_SPACING, rect.top(),
                                      rect.right() - circle.right(), rect.height())
            painter.drawText(text_rect, int(Qt.AlignVCenter | Qt.AlignLeft), entry['name'])

        def _elided(self, key, width):
            """*key*'s name cut to *width*; an item's width is fixed per set of entries."""
            text = self._elided_names.get(key)
            if text is None:
                metrics = QtGui.QFontMetrics(_label_font(bold=True))
                text = metrics.elidedText(self._entries[key]['name'], Qt.ElideRight, int(width))
                self._elided_names[key] = text
            return text

        # -- mouse -------------------------------------------------------------

        def key_at(self, point):
            """Return the key of the topmost item under the widget point *point*, or None."""
            point = QtCore.QPointF(point.x() / self.zoom, point.y() / self.zoom)
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
            if event.button() != Qt.LeftButton:
                return
            key = self._selectable_key_at(QtCore.QPointF(event.pos()))
            if key is not None and self.on_activate is not None:
                # Picking closes the popup under a still mouse, so no leave or
                # move event arrives to put the cursor back.
                self.unsetCursor()
                self.on_activate(key)

    _MINIMAP_MAX_WIDTH = 240
    _MINIMAP_MAX_HEIGHT = 150
    _MINIMAP_MARGIN = 10

    class Minimap(QtWidgets.QWidget):
        """An overview of the whole map above the zoom controls, with the visible part outlined.

        Clicking or dragging on it moves the view there.
        """

        def __init__(self, canvas, scroll_area, zoom_controls, on_navigate):
            super(Minimap, self).__init__(scroll_area)
            self._canvas = canvas
            self._scroll_area = scroll_area
            self._zoom_controls = zoom_controls
            # Called with the unzoomed map point to centre the view on, and
            # whether to glide there (a click) or jump (a drag).
            self._on_navigate = on_navigate
            # The map drawn small, redrawn only when the map or the minimap's
            # size changes, so a moving view repaints just the outline.
            self._picture = None
            self._picture_stamp = None
            self.setCursor(Qt.PointingHandCursor)
            scroll_area.horizontalScrollBar().valueChanged.connect(self.update)
            scroll_area.verticalScrollBar().valueChanged.connect(self.update)
            scroll_area.installEventFilter(self)

        def eventFilter(self, watched, event):  # noqa: N802 — Qt naming
            if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show) and self.isVisible():
                QtCore.QTimer.singleShot(0, self.reposition)
            return False

        def _scale(self):
            base = self._canvas.base_size()
            if base.width() <= 0 or base.height() <= 0:
                return 1.0
            return min(float(_MINIMAP_MAX_WIDTH) / base.width(),
                       float(_MINIMAP_MAX_HEIGHT) / base.height())

        def reposition(self):
            """Size to the map's aspect ratio and sit bottom-right, just above the zoom controls."""
            base = self._canvas.base_size()
            scale = self._scale()
            self.setFixedSize(int(base.width() * scale) + 2, int(base.height() * scale) + 2)
            viewport = self._scroll_area.viewport().geometry()
            controls_height = self._zoom_controls.sizeHint().height()
            self.move(viewport.right() - self.width() - _MINIMAP_MARGIN,
                      viewport.bottom() - controls_height - self.height() - 2 * _MINIMAP_MARGIN)
            self.raise_()
            self.update()

        def visible_rect(self):
            """The part of the map the view shows, in unzoomed map coordinates."""
            zoom = self._canvas.zoom
            viewport = self._scroll_area.viewport()
            return QtCore.QRectF(
                self._scroll_area.horizontalScrollBar().value() / zoom,
                self._scroll_area.verticalScrollBar().value() / zoom,
                viewport.width() / zoom, viewport.height() / zoom)

        def paintEvent(self, event):  # noqa: N802 — Qt naming
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(self.rect(), QtGui.QColor(20, 20, 20, 230))
            painter.setPen(QtGui.QPen(QtGui.QColor(110, 110, 110), 1))
            painter.drawRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
            painter.drawPixmap(1, 1, self._map_picture())
            painter.translate(1, 1)
            scale = self._scale()
            painter.scale(scale, scale)
            painter.setBrush(QtGui.QColor(255, 255, 255, 25))
            painter.setPen(QtGui.QPen(_HIGHLIGHT, 1.5 / scale))
            painter.drawRect(self.visible_rect())
            painter.end()

        def _map_picture(self):
            ratio = self.devicePixelRatioF()
            stamp = (self._canvas.content_version, self.width(), self.height(), ratio)
            if stamp != self._picture_stamp:
                self._picture = QtGui.QPixmap(max(1, int((self.width() - 2) * ratio)),
                                              max(1, int((self.height() - 2) * ratio)))
                self._picture.setDevicePixelRatio(ratio)
                self._picture.fill(Qt.transparent)
                painter = QtGui.QPainter(self._picture)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                scale = self._scale()
                painter.scale(scale, scale)
                self._canvas.paint_map(painter, with_text=False)
                painter.end()
                self._picture_stamp = stamp
            return self._picture

        def _map_point(self, point):
            """The unzoomed map point under the minimap point *point*."""
            scale = self._scale()
            return QtCore.QPointF((point.x() - 1) / scale, (point.y() - 1) / scale)

        def mousePressEvent(self, event):  # noqa: N802 — Qt naming
            self._on_navigate(self._map_point(event.pos()), True)

        def mouseMoveEvent(self, event):  # noqa: N802 — Qt naming
            if event.buttons() & Qt.LeftButton:
                self._on_navigate(self._map_point(event.pos()), False)

        def wheelEvent(self, event):  # noqa: N802 — Qt naming
            # Swallowed, so it does not fall through to scroll the view.
            event.accept()

    class ZoomControls(QtWidgets.QWidget):
        """Zoom out / zoom level / zoom in / fit buttons in the view's bottom-right corner."""

        def __init__(self, scroll_area, on_zoom_out, on_zoom_in, on_fit):
            super(ZoomControls, self).__init__(scroll_area)
            self._scroll_area = scroll_area
            self.setObjectName('SpatialZoomControls')
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setStyleSheet(
                "#SpatialZoomControls { background: rgba(20, 20, 20, 230);"
                " border: 1px solid rgb(110, 110, 110); border-radius: 4px; }"
                "QToolButton { color: rgb(220, 220, 220); background: transparent;"
                " border: none; padding: 2px 6px; font-weight: bold; }"
                "QToolButton:hover { background: rgb(60, 60, 60); }"
                "QLabel { color: rgb(200, 200, 200); padding: 0 2px; }")
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(0)
            for text, tip, callback in (('\u2212', 'Zoom out (Ctrl+-, mouse wheel)', on_zoom_out),
                                        (None, None, None),
                                        ('+', 'Zoom in (Ctrl+=, mouse wheel)', on_zoom_in),
                                        ('Fit', 'Fit the matches (Ctrl+0)', on_fit)):
                if text is None:
                    self._level = QtWidgets.QLabel('100%')
                    self._level.setAlignment(Qt.AlignCenter)
                    self._level.setMinimumWidth(40)
                    layout.addWidget(self._level)
                    continue
                button = QtWidgets.QToolButton()
                button.setText(text)
                button.setToolTip(tip)
                button.setFocusPolicy(Qt.NoFocus)
                button.clicked.connect(callback)
                layout.addWidget(button)
            scroll_area.installEventFilter(self)

        def wheelEvent(self, event):  # noqa: N802 — Qt naming
            # Swallowed, so it does not fall through to scroll the view.
            event.accept()

        def set_zoom(self, zoom):
            self._level.setText('%d%%' % round(zoom * 100))

        def reposition(self):
            self.adjustSize()
            viewport = self._scroll_area.viewport().geometry()
            self.move(viewport.right() - self.width() - _MINIMAP_MARGIN,
                      viewport.bottom() - self.height() - _MINIMAP_MARGIN)
            self.raise_()

        def eventFilter(self, watched, event):  # noqa: N802 — Qt naming
            if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show):
                QtCore.QTimer.singleShot(0, self.reposition)
            return False

    def _global_position(event):
        """The mouse event's global position, as a QPointF under PySide2 or PySide6."""
        if hasattr(event, 'globalPosition'):
            return event.globalPosition()
        return QtCore.QPointF(event.globalPos())

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
            # Set once the user zooms: from then on typing leaves the zoom alone
            # and only scrolls the highlighted match into view, until Fit or the
            # next show hands the zoom back to the search.
            self._user_zoomed = False
            self._zoom_controls = ZoomControls(
                self._map_scroll,
                on_zoom_out=lambda: self.zoom_by(1.0 / SPATIAL_ZOOM_STEP),
                on_zoom_in=lambda: self.zoom_by(SPATIAL_ZOOM_STEP),
                on_fit=self.fit_matched)
            self._minimap = Minimap(self.map_canvas, self._map_scroll, self._zoom_controls,
                                    on_navigate=self._centre_on)
            # Every zoom and scroll the picker makes glides there: see _move_view.
            self._view_animation = QtCore.QVariantAnimation(self)
            self._view_animation.setDuration(SPATIAL_VIEW_ANIMATION_MS)
            self._view_animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self._view_animation.setStartValue(0.0)
            self._view_animation.setEndValue(1.0)
            self._view_animation.valueChanged.connect(self._step_view_animation)
            self._animation_start = None
            self._animation_end = None
            self._minimap.hide()
            # Where a middle-button drag started: its global position and the
            # scroll position then; None while no drag is under way.
            self._pan_start = None
            self._map_scroll.viewport().installEventFilter(self)
            self.map_canvas.installEventFilter(self)
            for keys, callback in (('Ctrl+=', lambda: self.zoom_by(SPATIAL_ZOOM_STEP)),
                                   ('Ctrl++', lambda: self.zoom_by(SPATIAL_ZOOM_STEP)),
                                   ('Ctrl+-', lambda: self.zoom_by(1.0 / SPATIAL_ZOOM_STEP)),
                                   ('Ctrl+0', self.fit_matched)):
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(keys), self) \
                    if hasattr(QtGui, 'QShortcut') else QtWidgets.QShortcut(QtGui.QKeySequence(keys), self)
                shortcut.activated.connect(callback)

        def _build_layout(self):
            self.map_canvas = MapCanvas()
            self._map_scroll = QtWidgets.QScrollArea()
            self._map_scroll.setWidget(self.map_canvas)
            self._map_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
            # A click on the map or its overlays must leave the search field
            # focused, so typing carries on.
            self._map_scroll.setFocusPolicy(Qt.NoFocus)
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

        def _sync_map(self, animate=True):
            self.map_canvas.set_matched(
                self._matched_item_key(item) for item in self.things_model._items)
            if not self._user_zoomed:
                self._fit_matched_view(animate)
            self._sync_highlight(animate)
            self._minimap.update()

        # -- zoom --------------------------------------------------------------

        def eventFilter(self, watched, event):  # noqa: N802 — Qt naming
            viewport = self._map_scroll.viewport()
            if watched in (viewport, self.map_canvas) and event.type() == QtCore.QEvent.Wheel:
                # The wheel zooms, as in the Node Graph; dragging with the middle
                # button and the minimap move the view.
                steps = event.angleDelta().y() / 120.0
                if steps:
                    position = event.position() if hasattr(event, 'position') else event.pos()
                    focus = watched.mapTo(viewport, QtCore.QPointF(position).toPoint())
                    self.zoom_by(SPATIAL_ZOOM_STEP ** steps, QtCore.QPointF(focus))
                return True
            if watched in (viewport, self.map_canvas) and self._pan(event):
                return True
            return super(SpatialPicker, self).eventFilter(watched, event)

        def _pan(self, event):
            """Move the view with a middle-button drag, as in the Node Graph; True if handled."""
            event_type = event.type()
            if event_type == QtCore.QEvent.MouseButtonPress and event.button() == Qt.MiddleButton:
                self._view_animation.stop()
                self._pan_start = (_global_position(event),
                                   self._map_scroll.horizontalScrollBar().value(),
                                   self._map_scroll.verticalScrollBar().value())
                self.map_canvas.setCursor(Qt.ClosedHandCursor)
                return True
            if self._pan_start is None:
                return False
            if event_type == QtCore.QEvent.MouseMove:
                start_position, start_x, start_y = self._pan_start
                offset = _global_position(event) - start_position
                self._map_scroll.horizontalScrollBar().setValue(int(start_x - offset.x()))
                self._map_scroll.verticalScrollBar().setValue(int(start_y - offset.y()))
                return True
            if event_type == QtCore.QEvent.MouseButtonRelease and event.button() == Qt.MiddleButton:
                self._pan_start = None
                self.map_canvas.unsetCursor()
                return True
            return False

        def zoom_by(self, factor, focus=None):
            """Zoom by *factor*, keeping the map point under the viewport point *focus* still.

            *focus* defaults to the centre of the view.  This is the user
            zooming, so typing stops re-fitting the view until fit_matched.
            """
            self._user_zoomed = True
            if focus is None:
                focus = self._viewport_centre()
            # Zoom from where a zoom still gliding is heading, so quick clicks
            # or wheel notches add up.
            zoom = clamp_user_zoom(self._target_view()[0] * factor)
            _zoom, map_x, map_y, view_x, view_y = self._current_view(focus)
            self._move_view((zoom, map_x, map_y, view_x, view_y))

        # -- moving the view ---------------------------------------------------

        def _viewport_centre(self):
            viewport = self._map_scroll.viewport()
            return QtCore.QPointF(viewport.width() / 2.0, viewport.height() / 2.0)

        def _current_view(self, view_point):
            """The view shown now, pinned at the viewport point *view_point*.

            See interpolate_view for what a view is.
            """
            viewport = self._map_scroll.viewport()
            map_point = QtCore.QPointF(self.map_canvas.mapFrom(viewport, view_point.toPoint()))
            map_point /= self.map_canvas.zoom
            return (self.map_canvas.zoom, map_point.x(), map_point.y(),
                    view_point.x(), view_point.y())

        def _target_view(self):
            """The view being glided to, or the one shown when the view is still."""
            if self._view_animation.state() == QtCore.QAbstractAnimation.Running:
                return self._animation_end
            return self._current_view(self._viewport_centre())

        def _move_view(self, view, animate=True):
            """Glide to *view* (see interpolate_view), or jump there when not *animate*."""
            self._view_animation.stop()
            if not animate or not self.isVisible():
                self._set_view(view)
                return
            self._animation_start = self._current_view(QtCore.QPointF(view[3], view[4]))
            self._animation_end = view
            self._view_animation.start()

        def _step_view_animation(self, progress):
            if self._animation_start is not None:
                self._set_view(interpolate_view(self._animation_start, self._animation_end,
                                                float(progress)))

        def _set_view(self, view):
            zoom, map_x, map_y, view_x, view_y = view
            self._apply_zoom(zoom)
            self._scroll_to(QtCore.QPointF(map_x, map_y), QtCore.QPointF(view_x, view_y))

        def _centre_on(self, map_point, animate=True):
            """Scroll the unzoomed map point *map_point* to the middle of the view."""
            centre = self._viewport_centre()
            self._move_view((self._target_view()[0], map_point.x(), map_point.y(),
                             centre.x(), centre.y()), animate)

        def _visible_map_rect(self, view):
            """The unzoomed map rect *view* shows."""
            zoom, map_x, map_y, view_x, view_y = view
            viewport = self._map_scroll.viewport()
            base = self.map_canvas.base_size()
            left, width = visible_span(map_x, view_x, zoom, viewport.width(), base.width())
            top, height = visible_span(map_y, view_y, zoom, viewport.height(), base.height())
            return QtCore.QRectF(left, top, width, height)

        def _shows(self, view, rect):
            """Whether *view* shows all of the unzoomed map rect *rect* that lies on the map."""
            base = self.map_canvas.base_size()
            on_map = rect.intersected(QtCore.QRectF(0, 0, base.width(), base.height()))
            return self._visible_map_rect(view).contains(on_map)

        def _apply_zoom(self, zoom):
            self.map_canvas.set_zoom(zoom)
            # The scroll range only follows the new canvas size once the scroll
            # area has laid it out.
            self._map_scroll.widget().resize(self.map_canvas.size())
            self._zoom_controls.set_zoom(zoom)
            viewport = self._map_scroll.viewport().size()
            canvas = self.map_canvas.size()
            self._minimap.setVisible(canvas.width() > viewport.width()
                                     or canvas.height() > viewport.height())
            if self._minimap.isVisible():
                self._minimap.reposition()

        def _scroll_to(self, map_point, viewport_point):
            """Scroll so the unzoomed map point *map_point* sits at *viewport_point*."""
            zoom = self.map_canvas.zoom
            self._map_scroll.horizontalScrollBar().setValue(
                int(map_point.x() * zoom - viewport_point.x()))
            self._map_scroll.verticalScrollBar().setValue(
                int(map_point.y() * zoom - viewport_point.y()))

        def fit_matched(self):
            """Fit the view to the matches and let typing keep it fitted again (Fit, Ctrl+0)."""
            self._user_zoomed = False
            self._fit_matched_view()
            self._sync_highlight()

        def _fit_matched_view(self, animate=True):
            """Zoom and scroll the map so the items still matching the search fill the view.

            See fit_zoom for the zoom limits; when the matches cannot all fit,
            the view centres on them and the rest is a scroll away.
            """
            bounds = self.map_canvas.matched_bounds()
            if bounds is None:
                base = self.map_canvas.base_size()
                bounds = QtCore.QRectF(0, 0, base.width(), base.height())
            bounds = bounds.adjusted(-_MAP_MARGIN, -_MAP_MARGIN, _MAP_MARGIN, _MAP_MARGIN)
            viewport = self._map_scroll.viewport().size()
            centre = self._viewport_centre()
            self._move_view((fit_zoom(bounds.width(), bounds.height(),
                                      viewport.width(), viewport.height()),
                             bounds.center().x(), bounds.center().y(),
                             centre.x(), centre.y()), animate)

        def _sync_highlight(self, animate=True):
            key = None
            index = self.things.currentIndex()
            if index.isValid() and index.row() < len(self.things_model._items):
                key = self._matched_item_key(self.things_model._items[index.row()])
            rect = self.map_canvas.set_highlighted(key)
            # Judged against where the view is heading, so a fit still gliding
            # into place is not undone.
            if rect is not None and not self._shows(
                    self._target_view(),
                    rect.adjusted(-_MAP_MARGIN, -_MAP_MARGIN, _MAP_MARGIN, _MAP_MARGIN)):
                self._centre_on(rect.center(), animate)

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
            self._user_zoomed = False
            self._sync_map(animate=False)
            QtCore.QTimer.singleShot(0, self._zoom_controls.reposition)

        def _refresh_after_show(self):
            self.move_selection(where="first")

        def _fit_to_screen(self):
            available = _available_screen_rect()
            self.map_canvas.set_zoom(1.0)
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
            # The minimap and middle-button dragging stand in for scrollbars.
            self._map_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._map_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._map_scroll.setFixedSize(min(canvas_size.width(), max_width),
                                          min(canvas_size.height(), max_height))
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
