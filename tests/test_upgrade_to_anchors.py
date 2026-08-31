"""Tests for the "Upgrade to Anchors" adoption path in migrations.py (issue #71).

Covers:
- Detecting anchor-like parents built by another tool and their hidden-input children.
- Converting a NoOp parent in place: name, label, colour and the three anchor knobs.
- Converting a Dot parent into a real Dot anchor (marker knob, prefix, font size).
- Children keeping their class and position while becoming true Links.
- The naming options: name source per parent kind, and strip prefix/suffix.
- Keeping existing colours versus taking the plugin's derived anchor colour.
- Node-name collisions between two parents that derive the same name.
- Chained rigs: a node that is both a parent and a child stays a parent.
- Idempotency: re-running over an upgraded script does nothing.
"""

import contextlib
import unittest
from unittest.mock import patch

import nuke

import migrations
from constants import (
    ANCHOR_DEFAULT_COLOR,
    ANCHOR_RECONNECT_KNOB_NAME,
    ANCHOR_RENAME_KNOB_NAME,
    ANCHOR_SET_COLOR_KNOB_NAME,
    DOT_ANCHOR_KNOB_NAME,
    DOT_ANCHOR_MIN_FONT_SIZE,
    KNOB_NAME,
    NAME_SOURCE_LABEL,
    NAME_SOURCE_NODE_NAME,
)
from tests.stubs import StubKnob, StubNode

PARENT_COLOR = 0x11223344
SOURCE_COLOR = 0x55667788


def make_node(name, node_class='NoOp', label='', tile_color=0, hide_input=False,
              note_font_size=0, extra_knobs=None):
    """Build a StubNode carrying the knobs the upgrade path touches."""
    knobs = {
        'label': StubKnob(label, 'label'),
        'tile_color': StubKnob(tile_color, 'tile_color'),
        'hide_input': StubKnob(hide_input, 'hide_input'),
        'note_font_size': StubKnob(note_font_size, 'note_font_size'),
    }
    if extra_knobs:
        knobs.update(extra_knobs)
    return StubNode(name=name, node_class=node_class, knobs_dict=knobs)


def make_child(name, parent, node_class='NoOp'):
    """Build a hidden-input node wired to *parent* — the foreign 'link' shape."""
    child = make_node(name, node_class, hide_input=True)
    child.setInput(0, parent)
    return child


def make_knob(knob_name, *args, **kwargs):
    """Knob factory matching tests/stubs.py, used to pin nuke's knob constructors.

    Other test modules replace those constructors with bare MagicMocks and do not
    restore them, so a knob added during our tests would otherwise land under a
    MagicMock name instead of its real one.  script() re-pins them per test rather
    than depending on collection order.
    """
    return StubKnob(knob_name=knob_name)


@contextlib.contextmanager
def script(nodes):
    """Serve *nodes* as the current script for the duration of the block."""
    def all_nodes(node_class=None, *args, **kwargs):
        if node_class is None:
            return list(nodes)
        return [node for node in nodes if node.Class() == node_class]

    def to_node(node_name):
        for node in nodes:
            if node.name() == node_name:
                return node
        return None

    with contextlib.ExitStack() as patch_stack:
        patch_stack.enter_context(patch.object(nuke, 'allNodes', side_effect=all_nodes))
        patch_stack.enter_context(patch.object(nuke, 'toNode', side_effect=to_node))
        for factory_name in ('String_Knob', 'Tab_Knob', 'PyScript_Knob', 'Boolean_Knob'):
            patch_stack.enter_context(patch.object(nuke, factory_name, side_effect=make_knob))
        yield


def foreign_rig():
    """A Read, a foreign 'Pointer_FG' NoOp parent, and two hidden-input children.

    Returns (nodes, parent, children).
    """
    source = make_node('Read1', 'Read', tile_color=SOURCE_COLOR)
    parent = make_node('Pointer_FG', 'NoOp', label='FG plate', tile_color=PARENT_COLOR)
    parent.setInput(0, source)
    children = [
        make_child('NoOp7', parent),
        make_child('PostageStamp3', parent, node_class='PostageStamp'),
    ]
    return [source, parent] + children, parent, children


class UpgradeNoOpParentTest(unittest.TestCase):
    """A foreign NoOp parent and its hidden-input children become an anchor + Links."""

    def test_parent_becomes_a_named_anchor(self):
        nodes, parent, _children = foreign_rig()
        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(counts, (1, 2))
        self.assertEqual(parent.name(), 'Anchor_FG_plate')
        self.assertEqual(parent['label'].getValue(), 'FG_plate')

    def test_parent_gains_the_anchor_knobs(self):
        nodes, parent, _children = foreign_rig()
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)

        for knob_name in (ANCHOR_RECONNECT_KNOB_NAME, ANCHOR_RENAME_KNOB_NAME,
                          ANCHOR_SET_COLOR_KNOB_NAME):
            self.assertIn(knob_name, parent.knobs())

    def test_children_become_links_to_the_anchor(self):
        nodes, parent, children = foreign_rig()
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)

        for child in children:
            self.assertIn(KNOB_NAME, child.knobs())
            self.assertEqual(child[KNOB_NAME].getText(), parent.name())
            self.assertEqual(child['label'].getValue(), 'Link: FG_plate')
            self.assertTrue(child['hide_input'].getValue())
            self.assertIs(child.input(0), parent)

    def test_children_keep_their_class(self):
        """A PostageStamp child stays a PostageStamp — Links are knob-based."""
        nodes, _parent, children = foreign_rig()
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual([child.Class() for child in children], ['NoOp', 'PostageStamp'])

    def test_second_run_is_a_no_op(self):
        nodes, _parent, _children = foreign_rig()
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)
            second_run_counts = migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(second_run_counts, (0, 0))

    def test_a_parent_without_hidden_input_children_is_not_upgraded(self):
        source = make_node('Read1', 'Read')
        lonely = make_node('Pointer_FG', 'NoOp', label='FG')
        lonely.setInput(0, source)
        nodes = [source, lonely]

        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(counts, (0, 0))
        self.assertEqual(lonely.name(), 'Pointer_FG')


class UpgradeDotParentTest(unittest.TestCase):
    """A foreign labelled Dot parent becomes a real Dot anchor."""

    def setUp(self):
        self.source = make_node('Read1', 'Read')
        self.parent = make_node('Dot4', 'Dot', label='CG', tile_color=0x00FF00FF,
                                note_font_size=20)
        self.parent.setInput(0, self.source)
        self.child = make_child('Dot9', self.parent, node_class='Dot')
        self.nodes = [self.source, self.parent, self.child]

    def test_dot_parent_is_renamed_and_marked(self):
        with script(self.nodes):
            counts = migrations.upgrade_nodes_to_anchors(self.nodes)

        self.assertEqual(counts, (1, 1))
        self.assertEqual(self.parent.name(), 'Anchor_Dot_CG')
        self.assertIn(DOT_ANCHOR_KNOB_NAME, self.parent.knobs())
        self.assertEqual(self.parent['label'].getValue(), 'CG')

    def test_dot_parent_font_size_is_raised_to_the_anchor_minimum(self):
        with script(self.nodes):
            migrations.upgrade_nodes_to_anchors(self.nodes)

        self.assertEqual(self.parent['note_font_size'].getValue(), DOT_ANCHOR_MIN_FONT_SIZE)

    def test_dot_parent_takes_the_default_anchor_colour(self):
        """Dot anchor colours are system-managed, so the keep-colours option
        does not apply to them."""
        options = migrations.UpgradeOptions(keep_colors=True)
        with script(self.nodes):
            migrations.upgrade_nodes_to_anchors(self.nodes, options)

        self.assertEqual(self.parent['tile_color'].getValue(), ANCHOR_DEFAULT_COLOR)

    def test_dot_child_is_linked_to_the_dot_anchor(self):
        with script(self.nodes):
            migrations.upgrade_nodes_to_anchors(self.nodes)

        self.assertEqual(self.child[KNOB_NAME].getText(), 'Anchor_Dot_CG')
        self.assertEqual(self.child['label'].getValue(), 'Link: CG')


class UpgradeNamingTest(unittest.TestCase):
    """The name-source and strip options decide what each anchor is called."""

    def upgrade(self, parent, nodes, **option_values):
        options = migrations.UpgradeOptions(**option_values)
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes, options)
        return parent.name()

    def test_auto_prefers_the_label(self):
        nodes, parent, _children = foreign_rig()
        self.assertEqual(self.upgrade(parent, nodes), 'Anchor_FG_plate')

    def test_node_name_source_ignores_the_label(self):
        nodes, parent, _children = foreign_rig()
        self.assertEqual(
            self.upgrade(parent, nodes, noop_name_source=NAME_SOURCE_NODE_NAME),
            'Anchor_Pointer_FG',
        )

    def test_auto_falls_back_to_the_node_name_when_unlabelled(self):
        source = make_node('Read1', 'Read')
        parent = make_node('Pointer_FG', 'NoOp')
        parent.setInput(0, source)
        nodes = [source, parent, make_child('NoOp7', parent)]
        self.assertEqual(self.upgrade(parent, nodes), 'Anchor_Pointer_FG')

    def test_strip_prefix_and_suffix(self):
        nodes, parent, _children = foreign_rig()
        self.assertEqual(
            self.upgrade(parent, nodes, noop_name_source=NAME_SOURCE_NODE_NAME,
                         strip_prefix='Pointer'),
            'Anchor_FG',
        )

    def test_strip_that_would_empty_the_name_is_ignored(self):
        nodes, parent, _children = foreign_rig()
        self.assertEqual(
            self.upgrade(parent, nodes, noop_name_source=NAME_SOURCE_NODE_NAME,
                         strip_prefix='Pointer_FG'),
            'Anchor_Pointer_FG',
        )

    def test_html_tags_and_extra_lines_are_dropped_from_a_label(self):
        source = make_node('Read1', 'Read')
        parent = make_node('Pointer1', 'NoOp', label='<b>FG plate\nsecond line')
        parent.setInput(0, source)
        nodes = [source, parent, make_child('NoOp7', parent)]
        self.assertEqual(self.upgrade(parent, nodes), 'Anchor_FG_plate')

    def test_label_source_skips_a_node_with_no_label(self):
        source = make_node('Read1', 'Read')
        parent = make_node('Pointer_FG', 'NoOp')
        parent.setInput(0, source)
        child = make_child('NoOp7', parent)
        nodes = [source, parent, child]

        options = migrations.UpgradeOptions(noop_name_source=NAME_SOURCE_LABEL)
        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes, options)

        self.assertEqual(counts, (0, 0))
        self.assertEqual(parent.name(), 'Pointer_FG')
        self.assertNotIn(KNOB_NAME, child.knobs())

    def test_colliding_names_are_made_unique(self):
        source = make_node('Read1', 'Read')
        first_parent = make_node('Pointer_A', 'NoOp', label='FG')
        second_parent = make_node('Pointer_B', 'NoOp', label='FG')
        first_parent.setInput(0, source)
        second_parent.setInput(0, source)
        nodes = [source, first_parent, second_parent,
                 make_child('NoOp7', first_parent), make_child('NoOp8', second_parent)]

        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(first_parent.name(), 'Anchor_FG')
        self.assertEqual(second_parent.name(), 'Anchor_FG1')
        self.assertEqual(second_parent['label'].getValue(), 'FG1')


class UpgradeColorTest(unittest.TestCase):
    """The colour option decides whether a parent keeps its own tile colour."""

    def test_existing_colour_is_kept_by_default(self):
        nodes, parent, children = foreign_rig()
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(parent['tile_color'].getValue(), PARENT_COLOR)
        for child in children:
            self.assertEqual(child['tile_color'].getValue(), PARENT_COLOR)

    def test_anchor_colour_is_derived_when_not_keeping_colours(self):
        nodes, parent, _children = foreign_rig()
        options = migrations.UpgradeOptions(keep_colors=False)
        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes, options)

        # No containing backdrop, so the anchor colour comes from the source node.
        self.assertEqual(parent['tile_color'].getValue(), SOURCE_COLOR)


class UpgradeScopeTest(unittest.TestCase):
    """Which parents are considered, and how the pool is filtered."""

    def test_dot_parents_can_be_excluded(self):
        source = make_node('Read1', 'Read')
        noop_parent = make_node('Pointer_FG', 'NoOp', label='FG')
        dot_parent = make_node('Dot4', 'Dot', label='CG', note_font_size=20)
        noop_parent.setInput(0, source)
        dot_parent.setInput(0, source)
        nodes = [source, noop_parent, dot_parent,
                 make_child('NoOp7', noop_parent), make_child('NoOp8', dot_parent)]

        options = migrations.UpgradeOptions(include_dot_parents=False)
        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes, options)

        self.assertEqual(counts, (1, 1))
        self.assertEqual(noop_parent.name(), 'Anchor_FG')
        self.assertEqual(dot_parent.name(), 'Dot4')

    def test_noop_parents_can_be_excluded(self):
        nodes, parent, _children = foreign_rig()
        options = migrations.UpgradeOptions(include_noop_parents=False)
        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes, options)

        self.assertEqual(counts, (0, 0))
        self.assertEqual(parent.name(), 'Pointer_FG')

    def test_only_the_nodes_passed_in_are_upgraded(self):
        """Passing one selected parent leaves every other rig in the script alone."""
        source = make_node('Read1', 'Read')
        selected_parent = make_node('Pointer_A', 'NoOp', label='FG')
        other_parent = make_node('Pointer_B', 'NoOp', label='BG')
        selected_parent.setInput(0, source)
        other_parent.setInput(0, source)
        nodes = [source, selected_parent, other_parent,
                 make_child('NoOp7', selected_parent), make_child('NoOp8', other_parent)]

        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors([selected_parent])

        self.assertEqual(counts, (1, 1))
        self.assertEqual(selected_parent.name(), 'Anchor_FG')
        self.assertEqual(other_parent.name(), 'Pointer_B')


class UpgradeChainedRigTest(unittest.TestCase):
    """A node that is both a parent and a hidden-input child stays a parent."""

    def test_middle_node_becomes_an_anchor_not_a_link(self):
        source = make_node('Read1', 'Read')
        top_parent = make_node('Pointer_A', 'NoOp', label='A')
        top_parent.setInput(0, source)
        middle = make_child('Pointer_B', top_parent)
        middle['label'].setValue('B')
        leaf = make_child('NoOp9', middle)
        nodes = [source, top_parent, middle, leaf]

        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(counts, (1, 1))
        self.assertEqual(middle.name(), 'Anchor_B')
        self.assertNotIn(KNOB_NAME, middle.knobs())
        self.assertEqual(leaf[KNOB_NAME].getText(), 'Anchor_B')
        # The top parent had no link-like children left, so it was not touched.
        self.assertEqual(top_parent.name(), 'Pointer_A')


class UpgradeExistingAnchorTest(unittest.TestCase):
    """A real anchor with foreign hidden-input children keeps its name."""

    def test_children_are_linked_without_renaming_the_anchor(self):
        source = make_node('Read1', 'Read')
        anchor_node = make_node('Anchor_BG', 'NoOp', label='BG', tile_color=PARENT_COLOR)
        anchor_node.setInput(0, source)
        child = make_child('NoOp7', anchor_node)
        nodes = [source, anchor_node, child]

        with script(nodes):
            counts = migrations.upgrade_nodes_to_anchors(nodes)

        self.assertEqual(counts, (1, 1))
        self.assertEqual(anchor_node.name(), 'Anchor_BG')
        self.assertEqual(child[KNOB_NAME].getText(), 'Anchor_BG')

    def test_a_hand_named_anchor_gains_its_missing_buttons(self):
        source = make_node('Read1', 'Read')
        anchor_node = make_node('Anchor_BG', 'NoOp', label='BG')
        anchor_node.setInput(0, source)
        nodes = [source, anchor_node, make_child('NoOp7', anchor_node)]

        with script(nodes):
            migrations.upgrade_nodes_to_anchors(nodes)

        for knob_name in (ANCHOR_RECONNECT_KNOB_NAME, ANCHOR_RENAME_KNOB_NAME,
                          ANCHOR_SET_COLOR_KNOB_NAME):
            self.assertIn(knob_name, anchor_node.knobs())


class PlanUpgradesTest(unittest.TestCase):
    """The plan the dialog previews describes the work without doing it."""

    def test_plan_does_not_mutate_anything(self):
        nodes, parent, children = foreign_rig()
        with script(nodes):
            entries = migrations.plan_upgrades(nodes, migrations.UpgradeOptions())

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].target_node_name, 'Anchor_FG_plate')
        self.assertEqual(entries[0].children, children)
        self.assertEqual(parent.name(), 'Pointer_FG')
        self.assertNotIn(KNOB_NAME, children[0].knobs())

    def test_describe_reads_as_a_preview_line(self):
        nodes, _parent, _children = foreign_rig()
        with script(nodes):
            entries = migrations.plan_upgrades(nodes, migrations.UpgradeOptions())

        self.assertIn('Pointer_FG', entries[0].describe())
        self.assertIn('Anchor_FG_plate', entries[0].describe())
        self.assertIn('2 links', entries[0].describe())


class StripAffixesTest(unittest.TestCase):
    """_strip_affixes() trims separator debris only when it removed something."""

    def test_prefix_removal_trims_the_separator(self):
        self.assertEqual(migrations._strip_affixes('Pointer_Foo', 'Pointer', ''), 'Foo')

    def test_suffix_removal_trims_the_separator(self):
        self.assertEqual(migrations._strip_affixes('Foo_OUT', '', 'OUT'), 'Foo')

    def test_untouched_names_keep_their_separators(self):
        self.assertEqual(migrations._strip_affixes('_Foo_', 'Bar', 'Baz'), '_Foo_')

    def test_a_strip_that_would_empty_the_name_is_ignored(self):
        self.assertEqual(migrations._strip_affixes('Foo', 'Foo', ''), 'Foo')


class UpgradeOptionsTest(unittest.TestCase):
    """UpgradeOptions.from_dict() reads the dialog's plain dict."""

    def test_values_round_trip_from_the_dialog_dict(self):
        options = migrations.UpgradeOptions.from_dict({
            'include_noop_parents': False,
            'include_dot_parents': True,
            'noop_name_source': NAME_SOURCE_LABEL,
            'dot_name_source': NAME_SOURCE_NODE_NAME,
            'strip_prefix': 'Pointer_',
            'strip_suffix': '_OUT',
            'keep_colors': False,
        })

        self.assertFalse(options.include_noop_parents)
        self.assertTrue(options.include_dot_parents)
        self.assertEqual(options.noop_name_source, NAME_SOURCE_LABEL)
        self.assertEqual(options.dot_name_source, NAME_SOURCE_NODE_NAME)
        self.assertEqual(options.strip_prefix, 'Pointer_')
        self.assertEqual(options.strip_suffix, '_OUT')
        self.assertFalse(options.keep_colors)

    def test_missing_keys_fall_back_to_the_defaults(self):
        options = migrations.UpgradeOptions.from_dict({})
        defaults = migrations.UpgradeOptions()

        self.assertEqual(options.include_noop_parents, defaults.include_noop_parents)
        self.assertEqual(options.noop_name_source, defaults.noop_name_source)
        self.assertEqual(options.keep_colors, defaults.keep_colors)


if __name__ == '__main__':
    unittest.main()
