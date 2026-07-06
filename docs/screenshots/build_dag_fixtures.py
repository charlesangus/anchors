"""Build the Nuke script (.nk) that nuke-docs-screenshotter captures for the docs.

Run headless under Nuke's terminal mode::

    nuke -t docs/screenshots/build_dag_fixtures.py

Every graph is assembled by driving the *real* anchors plugin code — the same
``anchor``/``anchors``/``link`` functions the menu commands call — so the
documentation images always reflect how the plugin actually builds, colours,
links, and reconnects nodes. Nothing is emulated: anchors are made with
``anchor.create_anchor_named``, links with ``anchor.create_from_anchor``, copy and
paste with ``anchors.copy_anchors``/``anchors.paste_anchors``, and Link Dots with
``anchors.toggle_input_visibility``.

``nuke.nodeCopy`` refuses the clipboard in terminal mode, but it copies happily to
a real file, so ``nukescripts.cut_paste_file`` is redirected to a temp file and the
genuine copy/paste code paths run unchanged.

Scripts follow a clean modular layout built on a vertical **B-spine**: a node's
main input (input 0 / the B pipe) comes straight down the spine, and secondary
inputs (A, mask) join from the right. Each scene is wrapped in a ``screenshot:``
backdrop. The DAG capture renders node *names* and tile colours but not label
text, so captions that must be visible live in node names.
"""

import os
import sys
import tempfile

import nuke
import nukescripts

SCRIPT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT = os.path.abspath(os.path.join(SCRIPT_DIRECTORY, os.pardir, os.pardir))
if REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT)

import anchor  # noqa: E402
import anchors  # noqa: E402
import constants  # noqa: E402
import prefs  # noqa: E402

# Drive the real copy/paste code paths headlessly: nuke.nodeCopy cannot reach the
# clipboard in terminal mode, but it can copy to a file, so point the plugin's
# cut/paste file at a temp path instead of the clipboard sentinel.
_CUT_PASTE_FILE = os.path.join(tempfile.gettempdir(), "anchors_docs_cutpaste.nk")
nukescripts.cut_paste_file = lambda: _CUT_PASTE_FILE

prefs.plugin_enabled = True

FIXTURES_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, "fixtures")
OUTPUT_SCRIPT_PATH = os.path.join(FIXTURES_DIRECTORY, "anchors_dag.nk")

# Nominal node footprint used when sizing the enclosing backdrops. Nuke does not
# report reliable screen sizes in terminal mode, so a fixed size is used.
NOMINAL_NODE_WIDTH = 80
NOMINAL_NODE_HEIGHT = 78


def make_node(node_class, name, xpos, ypos, **knob_values):
    """Create a node at an explicit DAG position with its thumbnail suppressed.

    Read/PostageStamp postage stamps are turned off so source nodes draw as plain
    tiles instead of tall gradients, keeping the B-spine layout tight and readable.
    """
    node = getattr(nuke.nodes, node_class)()
    node.setName(name)
    if "postage_stamp" in node.knobs():
        node["postage_stamp"].setValue(False)
    for knob_name, value in knob_values.items():
        node[knob_name].setValue(value)
    node.setXYpos(xpos, ypos)
    return node


def select_only(nodes):
    """Make *nodes* the entire current selection."""
    for existing in nuke.allNodes():
        existing.setSelected(False)
    for node in nodes:
        node.setSelected(True)


def copy_paste(nodes):
    """Copy *nodes* and paste them with the real plugin code; return the pasted nodes."""
    select_only(nodes)
    anchors.copy_anchors()
    names_before = {node.name() for node in nuke.allNodes()}
    anchors.paste_anchors()
    return [node for node in nuke.allNodes() if node.name() not in names_before]


def link_from(anchor_node, name, xpos, ypos):
    """Create a link wired to *anchor_node* (what the ``A`` picker does) and place it."""
    link_node = anchor.create_from_anchor(anchor_node)
    link_node.setName(name)
    link_node.setXYpos(xpos, ypos)
    return link_node


def enclose_in_backdrop(slug, nodes, title):
    """Wrap *nodes* in a ``screenshot:`` backdrop whose drawn title is *title*.

    The label drives the output PNG filename (``screenshot:<slug>``); the node name
    is what Nuke actually draws across the top, so it doubles as the figure caption.
    """
    left = min(node.xpos() for node in nodes)
    right = max(node.xpos() + NOMINAL_NODE_WIDTH for node in nodes)
    top = min(node.ypos() for node in nodes)
    bottom = max(node.ypos() + NOMINAL_NODE_HEIGHT for node in nodes)
    horizontal_margin = 45
    top_margin = 80
    bottom_margin = 45
    return nuke.nodes.BackdropNode(
        xpos=left - horizontal_margin,
        ypos=top - top_margin,
        bdwidth=(right - left) + 2 * horizontal_margin,
        bdheight=(bottom - top) + top_margin + bottom_margin,
        label="screenshot:" + slug,
        note_font_size=30,
        name=title,
    )


# --------------------------------------------------------------------------- #
# Scenes. Each builds one clean B-spine comp in its own region of the DAG and  #
# wraps it in a screenshot backdrop. Anchor names are unique across scenes so   #
# links and paste-reconnection never resolve to the wrong anchor.              #
# --------------------------------------------------------------------------- #


def build_problem_long_pipe(origin_x, origin_y):
    """The 'reuse by a long pipe' anti-pattern: a plate routed the long way round."""
    plate = make_node("Read", "Plate", origin_x, origin_y)
    grade = make_node("Grade", "Grade", origin_x, origin_y + 130)
    grade.setInput(0, plate)
    write = make_node("Write", "Write", origin_x, origin_y + 470)
    # A second consumer of the plate, far to the right, reached by routing dots
    # that loop around the comp — legible only with effort.
    routing_dots = []
    dot_path = [
        (origin_x + 60, origin_y + 20),
        (origin_x + 420, origin_y + 20),
        (origin_x + 420, origin_y + 360),
        (origin_x + 300, origin_y + 360),
    ]
    previous = plate
    for index, (dot_x, dot_y) in enumerate(dot_path):
        dot = make_node("Dot", "Dot%d" % (index + 1), dot_x, dot_y)
        dot.setInput(0, previous)
        routing_dots.append(dot)
        previous = dot
    keyer = make_node("Keyer", "Key", origin_x + 280, origin_y + 470)
    keyer.setInput(0, previous)
    merge = make_node("Merge2", "Comp", origin_x, origin_y + 360)
    merge.setInput(0, grade)
    merge.setInput(1, keyer)
    write.setInput(0, merge)
    enclose_in_backdrop(
        "problem long pipe",
        [plate, grade, write, keyer, merge] + routing_dots,
        title="Reuse_by_a_long_pipe_is_unreadable",
    )


def build_problem_fragile(origin_x, origin_y):
    """The 'bare hidden input' anti-pattern: a hidden-input copy lost its source."""
    plate = make_node("Read", "Plate", origin_x, origin_y)
    connected = make_node("PostageStamp", "Stamp", origin_x, origin_y + 150,
                          hide_input=True)
    connected.setInput(0, plate)
    # The pasted copy: a hidden-input stamp with nothing on its input — the
    # connection did not survive the copy/paste.
    broken = make_node("PostageStamp", "Pasted_Stamp", origin_x + 220,
                       origin_y + 150, hide_input=False)
    enclose_in_backdrop(
        "problem fragile",
        [plate, connected, broken],
        title="A_bare_hidden_input_breaks_on_paste",
    )


def build_hero(origin_x, origin_y):
    """The realistic scenario: a plate reused for both the comp base and its key."""
    plate = make_node("Read", "Plate", origin_x, origin_y)
    plate_anchor = anchor.create_anchor_named("Plate", input_node=plate)

    # CG branch joins the spine from the right.
    cg_read = make_node("Read", "CG", origin_x + 230, origin_y - 20)
    premult = make_node("Premult", "Premult_CG", origin_x + 230, origin_y + 110)
    premult.setInput(0, cg_read)

    # Key branch: a Link back to the plate anchor feeds the keyer (same plate).
    key_link = link_from(plate_anchor, "Link_Plate", origin_x + 470, origin_y + 110)
    keyer = make_node("Keyer", "Key", origin_x + 470, origin_y + 250)
    keyer.setInput(0, key_link)

    merge_cg = make_node("Merge2", "Merge_CG", origin_x, origin_y + 330)
    merge_cg.setInput(0, plate_anchor)
    merge_cg.setInput(1, premult)
    merge_key = make_node("Merge2", "Merge_Key", origin_x, origin_y + 470)
    merge_key.setInput(0, merge_cg)
    merge_key.setInput(1, keyer)
    write = make_node("Write", "Write", origin_x, origin_y + 600)
    write.setInput(0, merge_key)

    enclose_in_backdrop(
        "hero comp",
        [plate, plate_anchor, cg_read, premult, key_link, keyer,
         merge_cg, merge_key, write],
        title="One_plate_reused_through_an_anchor",
    )


def build_make_anchor(origin_x, origin_y):
    """Close-up: a source node with the anchor created beneath it."""
    beauty = make_node("Read", "Beauty", origin_x, origin_y)
    beauty_anchor = anchor.create_anchor_named("Beauty", input_node=beauty)
    enclose_in_backdrop(
        "make anchor",
        [beauty, beauty_anchor],
        title="Press_A_to_anchor_a_node",
    )


def build_link_by_paste(origin_x, origin_y):
    """A link created by copying an anchor and pasting it (paste-as-link)."""
    bg_read = make_node("Read", "BG", origin_x, origin_y)
    bg_anchor = anchor.create_anchor_named("BG", input_node=bg_read)
    pasted = copy_paste([bg_anchor])
    for pasted_node in pasted:
        pasted_node.setName("Link_BG")
        pasted_node.setXYpos(origin_x + 220, origin_y + 110)
    enclose_in_backdrop(
        "link by paste",
        [bg_read, bg_anchor] + pasted,
        title="Copy_an_anchor_paste_a_link",
    )


def build_reconnect(origin_x, origin_y):
    """Copy a block carrying two links; paste reconnects both to their anchors."""
    # Two anchored sources on a shared spine.
    plate = make_node("Read", "Roto", origin_x, origin_y)
    roto_anchor = anchor.create_anchor_named("Roto", input_node=plate)
    defocus_source = make_node("Read", "Defocus", origin_x + 200, origin_y)
    defocus_anchor = anchor.create_anchor_named("Defocus", input_node=defocus_source)

    # A reusable block: two links feeding a merge.
    roto_link = link_from(roto_anchor, "Link_Roto", origin_x, origin_y + 200)
    defocus_link = link_from(defocus_anchor, "Link_Defocus", origin_x + 200,
                             origin_y + 200)
    block_merge = make_node("Merge2", "Block_Merge", origin_x, origin_y + 330)
    block_merge.setInput(0, roto_link)
    block_merge.setInput(1, defocus_link)
    enclose_in_backdrop(
        "reconnect before",
        [plate, roto_anchor, defocus_source, defocus_anchor,
         roto_link, defocus_link, block_merge],
        title="Copy_a_block_with_two_links",
    )

    # Paste the block: both links reconnect to the original anchors by name.
    pasted = copy_paste([roto_link, defocus_link, block_merge])
    pasted_left = min(node.xpos() for node in pasted)
    pasted_top = min(node.ypos() for node in pasted)
    delta_x = (origin_x + 560) - pasted_left
    delta_y = (origin_y + 200) - pasted_top
    for pasted_node in pasted:
        pasted_node.setXYpos(pasted_node.xpos() + delta_x, pasted_node.ypos() + delta_y)
    enclose_in_backdrop(
        "reconnect after",
        pasted,
        title="Pasted_links_reconnect_themselves",
    )


def build_color_coded(origin_x, origin_y):
    """Several anchored passes carrying distinct colours, side by side."""
    palette = [
        (constants.ANCHOR_DEFAULT_COLOR, "Beauty"),
        (0x3399FFFF, "Reflection"),
        (0x33CC66FF, "Matte"),
        (0xCC6633FF, "Depth"),
    ]
    nodes = []
    for index, (color, pass_name) in enumerate(palette):
        source = make_node("Read", pass_name, origin_x + index * 150, origin_y)
        anchor.create_anchor_named(pass_name, input_node=source, color=color)
        nodes.append(source)
        nodes.append(nuke.toNode("Anchor_" + pass_name))
    enclose_in_backdrop(
        "color coded",
        nodes,
        title="Anchors_carry_a_colour",
    )


def build_jump_target(origin_x, origin_y):
    """Close-up of an anchor module — the view you land on after a jump."""
    hero = make_node("Read", "HeroPlate", origin_x, origin_y)
    hero_anchor = anchor.create_anchor_named("HeroPlate", input_node=hero)
    grade = make_node("Grade", "Hero_Grade", origin_x, origin_y + 200)
    grade.setInput(0, hero_anchor)
    enclose_in_backdrop(
        "jump target",
        [hero, hero_anchor, grade],
        title="Alt_J_jumps_to_the_anchor",
    )


def build_link_dots(origin_x, origin_y):
    """Link Dots: hide a wired Dot's input (Alt+H) to turn it into a Link Dot.

    The anchor and its dots live in the same backdrop so the hidden-input
    indicator Nuke draws stays inside the frame.
    """
    matte_source = make_node("Read", "Matte", origin_x, origin_y)
    matte_anchor = anchor.create_anchor_named("Matte", input_node=matte_source)

    link_dots = []
    for index, dot_x in enumerate((origin_x + 60, origin_x + 200)):
        dot = make_node("Dot", "LinkDot%d" % (index + 1), dot_x, origin_y + 150)
        dot.setInput(0, matte_anchor)
        select_only([dot])
        anchors.toggle_input_visibility()
        link_dots.append(dot)

    enclose_in_backdrop(
        "link dots",
        [matte_source, matte_anchor] + link_dots,
        title="Hide_a_dots_input_to_make_a_Link_Dot",
    )


def build_link_dot_paste(origin_x, origin_y):
    """Copy/paste a Link Dot: the pasted dot reconnects to the same anchor."""
    spill_source = make_node("Read", "Spill", origin_x, origin_y)
    spill_anchor = anchor.create_anchor_named("Spill", input_node=spill_source)
    dot = make_node("Dot", "SpillDot", origin_x + 60, origin_y + 150)
    dot.setInput(0, spill_anchor)
    select_only([dot])
    anchors.toggle_input_visibility()
    pasted = copy_paste([dot])
    for pasted_node in pasted:
        pasted_node.setXYpos(origin_x + 200, origin_y + 150)
    enclose_in_backdrop(
        "link dot paste",
        [spill_source, spill_anchor, dot] + pasted,
        title="A_pasted_Link_Dot_reconnects",
    )


def main():
    nuke.scriptClear()

    # Scenes are spaced well apart (≈900 px columns, ≈1000 px rows) so no
    # backdrop's title bleeds into a neighbour's capture.
    build_problem_long_pipe(0, 0)
    build_problem_fragile(900, 0)
    build_make_anchor(1800, 0)

    build_hero(0, 1000)
    build_color_coded(900, 1000)
    build_jump_target(1800, 1000)

    build_reconnect(0, 2100)
    build_link_by_paste(1100, 2100)
    build_link_dots(1800, 2100)

    build_link_dot_paste(0, 3000)

    if not os.path.isdir(FIXTURES_DIRECTORY):
        os.makedirs(FIXTURES_DIRECTORY)
    nuke.scriptSaveAs(OUTPUT_SCRIPT_PATH, overwrite=True)
    sys.stderr.write("Wrote %s\n" % OUTPUT_SCRIPT_PATH)


main()
