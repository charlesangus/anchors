"""Tests for backdrop setup (issue #68).

Pressing ``A`` with a single backdrop selected opens a setup dialog offering a
label field, the colour palette, a font-size selector and a "Filled" checkbox.

Covers:
- resolve_backdrop_font_size(): preset sizes round-trip, anything else opens Large
- backdrop_is_filled(): reads Nuke's appearance knob, defaults True when absent
- apply_backdrop_setup(): writes label, font size, colour and appearance;
  None arguments leave that aspect untouched; a missing appearance knob is ignored
- setup_backdrop(): seeds the dialog from the backdrop, applies on accept, leaves
  the backdrop untouched on cancel, persists staged custom colours, and falls
  back to a plain label prompt when Qt is unavailable
- setup_selected_backdrop(): acts only on a single selected backdrop
- anchor_shortcut(): a lone selected backdrop routes to setup_backdrop() rather
  than creating an anchor from it
- BackdropDialog: source-level checks (Qt is stubbed offline, so the class object
  itself is a MagicMock and cannot be instantiated)
"""

import ast
import textwrap
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).parent.parent

_DIALOG_ACCEPTED = 1
_DIALOG_REJECTED = 0


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_backdrop_node(label='', font_size=42, color=0x8F8F8FFF, appearance='Fill',
                        with_appearance_knob=True):
    """Return a BackdropNode StubNode carrying the knobs the dialog reads."""
    import nuke as _nuke
    knobs = {
        'label': _nuke.StubKnob(label),
        'note_font_size': _nuke.StubKnob(font_size),
        'tile_color': _nuke.StubKnob(color),
    }
    if with_appearance_knob:
        knobs['appearance'] = _nuke.StubKnob(appearance)
    return _nuke.StubNode(name='BackdropNode1', node_class='BackdropNode', knobs_dict=knobs)


def _make_fake_dialog_class(accepted=True, chosen_name='Comp', chosen_font_size=111,
                            chosen_filled=True, color=0x336699FF, staged_colors=None):
    """Return (dialog_class, record) standing in for colors.BackdropDialog.

    ``record`` captures the constructor keyword arguments so tests can assert how
    the dialog was seeded from the backdrop.
    """
    record = {}

    class FakeBackdropDialog:
        def __init__(self, **kwargs):
            record['kwargs'] = kwargs
            self.chosen_name = chosen_name
            self.chosen_font_size = chosen_font_size
            self.chosen_filled = chosen_filled

        def exec_(self):
            return _DIALOG_ACCEPTED if accepted else _DIALOG_REJECTED

        def selected_color_int(self):
            return color

        def chosen_custom_colors(self):
            return list(staged_colors or [])

    return FakeBackdropDialog, record


def _make_qt_stub():
    """Minimal QtWidgets stand-in exposing QDialog.Accepted."""
    return types.SimpleNamespace(QDialog=types.SimpleNamespace(Accepted=_DIALOG_ACCEPTED))


def _make_prefs_stub(custom_colors=None):
    prefs_stub = MagicMock()
    prefs_stub.plugin_enabled = True
    prefs_stub.custom_colors = list(custom_colors or [])
    return prefs_stub


# ---------------------------------------------------------------------------
# resolve_backdrop_font_size
# ---------------------------------------------------------------------------

class TestResolveBackdropFontSize(unittest.TestCase):
    """Preset sizes are preserved; everything else opens on Large."""

    def test_each_preset_size_is_preserved(self):
        from colors import resolve_backdrop_font_size
        from constants import BACKDROP_FONT_SIZE_PRESETS

        for _preset_name, preset_size in BACKDROP_FONT_SIZE_PRESETS:
            self.assertEqual(resolve_backdrop_font_size(preset_size), preset_size)

    def test_nuke_default_backdrop_size_falls_back_to_large(self):
        from colors import resolve_backdrop_font_size
        from constants import BACKDROP_DEFAULT_FONT_SIZE

        # 42 is the size Nuke's own autoBackdrop applies — not one of our presets.
        self.assertEqual(resolve_backdrop_font_size(42), BACKDROP_DEFAULT_FONT_SIZE)

    def test_float_knob_value_matches_integer_preset(self):
        from colors import resolve_backdrop_font_size
        from constants import DOT_LABEL_FONT_SIZE_MEDIUM

        # Nuke knob values arrive as floats.
        self.assertEqual(
            resolve_backdrop_font_size(float(DOT_LABEL_FONT_SIZE_MEDIUM)),
            DOT_LABEL_FONT_SIZE_MEDIUM,
        )

    def test_none_falls_back_to_large(self):
        from colors import resolve_backdrop_font_size
        from constants import BACKDROP_DEFAULT_FONT_SIZE

        self.assertEqual(resolve_backdrop_font_size(None), BACKDROP_DEFAULT_FONT_SIZE)

    def test_default_font_size_is_the_large_dot_size(self):
        from constants import BACKDROP_DEFAULT_FONT_SIZE, DOT_LABEL_FONT_SIZE_LARGE

        self.assertEqual(BACKDROP_DEFAULT_FONT_SIZE, DOT_LABEL_FONT_SIZE_LARGE)

    def test_presets_are_the_dot_anchor_sizes(self):
        from constants import (
            BACKDROP_FONT_SIZE_PRESETS,
            DOT_LABEL_FONT_SIZE_LARGE,
            DOT_LABEL_FONT_SIZE_MEDIUM,
            DOT_LABEL_FONT_SIZE_SMALL,
        )

        self.assertEqual(
            [size for _name, size in BACKDROP_FONT_SIZE_PRESETS],
            [DOT_LABEL_FONT_SIZE_SMALL, DOT_LABEL_FONT_SIZE_MEDIUM, DOT_LABEL_FONT_SIZE_LARGE],
        )


# ---------------------------------------------------------------------------
# backdrop_is_filled / is_backdrop
# ---------------------------------------------------------------------------

class TestBackdropPredicates(unittest.TestCase):
    """is_backdrop() and backdrop_is_filled() read the node's class and appearance."""

    def test_is_backdrop_true_for_backdrop_node(self):
        from labels import is_backdrop

        self.assertTrue(is_backdrop(_make_backdrop_node()))

    def test_is_backdrop_false_for_other_classes(self):
        import nuke as _nuke

        from labels import is_backdrop

        self.assertFalse(is_backdrop(_nuke.StubNode(name='Dot1', node_class='Dot')))

    def test_filled_appearance_reports_true(self):
        from labels import backdrop_is_filled

        self.assertTrue(backdrop_is_filled(_make_backdrop_node(appearance='Fill')))

    def test_border_appearance_reports_false(self):
        from labels import backdrop_is_filled

        self.assertFalse(backdrop_is_filled(_make_backdrop_node(appearance='Border')))

    def test_missing_appearance_knob_reports_filled(self):
        """Nuke versions before the appearance knob always draw backdrops filled."""
        from labels import backdrop_is_filled

        self.assertTrue(backdrop_is_filled(_make_backdrop_node(with_appearance_knob=False)))


# ---------------------------------------------------------------------------
# apply_backdrop_setup
# ---------------------------------------------------------------------------

class TestApplyBackdropSetup(unittest.TestCase):
    """apply_backdrop_setup() writes exactly the attributes it is given."""

    def test_applies_every_attribute(self):
        from labels import apply_backdrop_setup

        backdrop = _make_backdrop_node(label='old', font_size=42, color=0, appearance='Border')
        apply_backdrop_setup(backdrop, label_text='PLATES', font_size=111,
                             filled=True, color=0x336699FF)

        self.assertEqual(backdrop['label'].getValue(), 'PLATES')
        self.assertEqual(backdrop['note_font_size'].getValue(), 111)
        self.assertEqual(backdrop['tile_color'].getValue(), 0x336699FF)
        self.assertEqual(backdrop['appearance'].getValue(), 'Fill')

    def test_unfilled_sets_border_appearance(self):
        from labels import apply_backdrop_setup

        backdrop = _make_backdrop_node(appearance='Fill')
        apply_backdrop_setup(backdrop, filled=False)

        self.assertEqual(backdrop['appearance'].getValue(), 'Border')

    def test_none_arguments_leave_the_backdrop_untouched(self):
        from labels import apply_backdrop_setup

        backdrop = _make_backdrop_node(label='keep', font_size=42, color=0x111111FF,
                                       appearance='Border')
        apply_backdrop_setup(backdrop)

        self.assertEqual(backdrop['label'].getValue(), 'keep')
        self.assertEqual(backdrop['note_font_size'].getValue(), 42)
        self.assertEqual(backdrop['tile_color'].getValue(), 0x111111FF)
        self.assertEqual(backdrop['appearance'].getValue(), 'Border')

    def test_empty_label_clears_the_backdrop_label(self):
        """An empty string is a real choice — only None means "leave alone"."""
        from labels import apply_backdrop_setup

        backdrop = _make_backdrop_node(label='old')
        apply_backdrop_setup(backdrop, label_text='')

        self.assertEqual(backdrop['label'].getValue(), '')

    def test_missing_appearance_knob_is_ignored(self):
        from labels import apply_backdrop_setup

        backdrop = _make_backdrop_node(with_appearance_knob=False)
        apply_backdrop_setup(backdrop, label_text='NOTES', filled=False)

        self.assertEqual(backdrop['label'].getValue(), 'NOTES')
        self.assertNotIn('appearance', backdrop.knobs())


# ---------------------------------------------------------------------------
# setup_backdrop
# ---------------------------------------------------------------------------

class TestSetupBackdrop(unittest.TestCase):
    """setup_backdrop() seeds the dialog, then applies what the user chose."""

    def test_dialog_is_seeded_from_the_backdrop(self):
        import labels

        backdrop = _make_backdrop_node(label='old label', font_size=66,
                                       color=0x112233FF, appearance='Border')
        dialog_class, record = _make_fake_dialog_class()
        prefs_stub = _make_prefs_stub(custom_colors=[0xAABBCCFF])

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', prefs_stub):
            labels.setup_backdrop(backdrop)

        self.assertEqual(record['kwargs']['initial_label'], 'old label')
        self.assertEqual(record['kwargs']['initial_font_size'], 66)
        self.assertEqual(record['kwargs']['initial_color'], 0x112233FF)
        self.assertFalse(record['kwargs']['initial_filled'])
        self.assertEqual(record['kwargs']['custom_colors'], [0xAABBCCFF])

    def test_accepted_dialog_applies_all_choices(self):
        import labels

        backdrop = _make_backdrop_node(label='old', font_size=42, appearance='Border')
        dialog_class, _record = _make_fake_dialog_class(
            chosen_name='PLATES', chosen_font_size=33, chosen_filled=True, color=0x336699FF
        )

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', _make_prefs_stub()):
            labels.setup_backdrop(backdrop)

        self.assertEqual(backdrop['label'].getValue(), 'PLATES')
        self.assertEqual(backdrop['note_font_size'].getValue(), 33)
        self.assertEqual(backdrop['tile_color'].getValue(), 0x336699FF)
        self.assertEqual(backdrop['appearance'].getValue(), 'Fill')

    def test_multiline_label_is_applied_verbatim(self):
        """Backdrop labels routinely carry several lines of notes."""
        import labels

        backdrop = _make_backdrop_node(label='one line')
        dialog_class, _record = _make_fake_dialog_class(chosen_name='first\nsecond')

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', _make_prefs_stub()):
            labels.setup_backdrop(backdrop)

        self.assertEqual(backdrop['label'].getValue(), 'first\nsecond')

    def test_cancelled_dialog_leaves_the_backdrop_untouched(self):
        import labels

        backdrop = _make_backdrop_node(label='old', font_size=42, color=0x111111FF,
                                       appearance='Border')
        dialog_class, _record = _make_fake_dialog_class(accepted=False)

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', _make_prefs_stub()):
            labels.setup_backdrop(backdrop)

        self.assertEqual(backdrop['label'].getValue(), 'old')
        self.assertEqual(backdrop['note_font_size'].getValue(), 42)
        self.assertEqual(backdrop['tile_color'].getValue(), 0x111111FF)
        self.assertEqual(backdrop['appearance'].getValue(), 'Border')

    def test_accepted_dialog_persists_staged_custom_colors(self):
        import labels

        backdrop = _make_backdrop_node()
        dialog_class, _record = _make_fake_dialog_class(staged_colors=[0xFF0000FF])
        prefs_stub = _make_prefs_stub()

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', prefs_stub):
            labels.setup_backdrop(backdrop)

        prefs_stub.persist_custom_colors_from_dialog.assert_called_once()

    def test_cancelled_dialog_does_not_persist_custom_colors(self):
        import labels

        backdrop = _make_backdrop_node()
        dialog_class, _record = _make_fake_dialog_class(accepted=False,
                                                        staged_colors=[0xFF0000FF])
        prefs_stub = _make_prefs_stub()

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', prefs_stub):
            labels.setup_backdrop(backdrop)

        prefs_stub.persist_custom_colors_from_dialog.assert_not_called()

    def test_plugin_disabled_opens_no_dialog(self):
        import labels

        backdrop = _make_backdrop_node(label='old')
        dialog_class, record = _make_fake_dialog_class()
        prefs_stub = _make_prefs_stub()
        prefs_stub.plugin_enabled = False

        with patch.object(labels, 'BackdropDialog', dialog_class), \
             patch.object(labels, 'QtWidgets', _make_qt_stub()), \
             patch.object(labels, 'prefs', prefs_stub):
            labels.setup_backdrop(backdrop)

        self.assertNotIn('kwargs', record)
        self.assertEqual(backdrop['label'].getValue(), 'old')

    def test_without_qt_falls_back_to_a_label_prompt(self):
        """No Qt → prompt for the label only; colour and font size stay as they are."""
        import nuke as _nuke

        import labels

        backdrop = _make_backdrop_node(label='old', font_size=42, color=0x111111FF)
        _nuke.getInput = MagicMock(return_value='NEW LABEL')

        with patch.object(labels, 'BackdropDialog', None), \
             patch.object(labels, 'nuke', _nuke), \
             patch.object(labels, 'prefs', _make_prefs_stub()):
            labels.setup_backdrop(backdrop)

        _nuke.getInput.assert_called_once()
        self.assertEqual(backdrop['label'].getValue(), 'NEW LABEL')
        self.assertEqual(backdrop['note_font_size'].getValue(), 42)
        self.assertEqual(backdrop['tile_color'].getValue(), 0x111111FF)

    def test_cancelled_fallback_prompt_leaves_the_label_alone(self):
        import nuke as _nuke

        import labels

        backdrop = _make_backdrop_node(label='old')
        _nuke.getInput = MagicMock(return_value=None)

        with patch.object(labels, 'BackdropDialog', None), \
             patch.object(labels, 'nuke', _nuke), \
             patch.object(labels, 'prefs', _make_prefs_stub()):
            labels.setup_backdrop(backdrop)

        self.assertEqual(backdrop['label'].getValue(), 'old')


# ---------------------------------------------------------------------------
# setup_selected_backdrop — the menu entry
# ---------------------------------------------------------------------------

class TestSetupSelectedBackdrop(unittest.TestCase):
    """The menu entry acts only on a single selected backdrop."""

    def test_single_selected_backdrop_opens_the_dialog(self):
        import nuke as _nuke

        import labels

        backdrop = _make_backdrop_node()
        _nuke.selectedNodes = MagicMock(return_value=[backdrop])

        with patch.object(labels, 'nuke', _nuke), \
             patch.object(labels, 'prefs', _make_prefs_stub()), \
             patch.object(labels, 'setup_backdrop') as mock_setup:
            labels.setup_selected_backdrop()

        mock_setup.assert_called_once_with(backdrop)

    def test_non_backdrop_selection_does_nothing(self):
        import nuke as _nuke

        import labels

        _nuke.selectedNodes = MagicMock(
            return_value=[_nuke.StubNode(name='Dot1', node_class='Dot')]
        )

        with patch.object(labels, 'nuke', _nuke), \
             patch.object(labels, 'prefs', _make_prefs_stub()), \
             patch.object(labels, 'setup_backdrop') as mock_setup:
            labels.setup_selected_backdrop()

        mock_setup.assert_not_called()

    def test_multiple_selected_nodes_do_nothing(self):
        import nuke as _nuke

        import labels

        _nuke.selectedNodes = MagicMock(
            return_value=[_make_backdrop_node(), _make_backdrop_node()]
        )

        with patch.object(labels, 'nuke', _nuke), \
             patch.object(labels, 'prefs', _make_prefs_stub()), \
             patch.object(labels, 'setup_backdrop') as mock_setup:
            labels.setup_selected_backdrop()

        mock_setup.assert_not_called()

    def test_plugin_disabled_does_nothing(self):
        import nuke as _nuke

        import labels

        _nuke.selectedNodes = MagicMock(return_value=[_make_backdrop_node()])
        prefs_stub = _make_prefs_stub()
        prefs_stub.plugin_enabled = False

        with patch.object(labels, 'nuke', _nuke), \
             patch.object(labels, 'prefs', prefs_stub), \
             patch.object(labels, 'setup_backdrop') as mock_setup:
            labels.setup_selected_backdrop()

        mock_setup.assert_not_called()


# ---------------------------------------------------------------------------
# anchor_shortcut dispatch
# ---------------------------------------------------------------------------

class TestAnchorShortcutBackdropRouting(unittest.TestCase):
    """Pressing A on a backdrop sets it up instead of anchoring it."""

    def setUp(self):
        import importlib

        import anchor as anchor_mod
        importlib.reload(anchor_mod)
        self.anchor_mod = anchor_mod
        import nuke as nuke_stub
        self.nuke_stub = nuke_stub

    def test_single_backdrop_selected_calls_setup_backdrop(self):
        backdrop = _make_backdrop_node()
        self.nuke_stub.selectedNodes = MagicMock(return_value=[backdrop])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'is_anchor', return_value=False), \
             patch.object(self.anchor_mod.labels, 'setup_backdrop') as mock_setup, \
             patch.object(self.anchor_mod, 'create_anchor') as mock_create_anchor:
            self.anchor_mod.anchor_shortcut()

        mock_setup.assert_called_once_with(backdrop)
        mock_create_anchor.assert_not_called()

    def test_backdrop_among_several_nodes_still_creates_an_anchor(self):
        """A backdrop dragged along with its contents keeps the old behaviour."""
        import nuke as _nuke

        backdrop = _make_backdrop_node()
        read_node = _nuke.StubNode(name='Read1', node_class='Read')
        self.nuke_stub.selectedNodes = MagicMock(return_value=[backdrop, read_node])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', True), \
             patch.object(self.anchor_mod, 'is_anchor', return_value=False), \
             patch.object(self.anchor_mod.labels, 'setup_backdrop') as mock_setup, \
             patch.object(self.anchor_mod, 'create_anchor') as mock_create_anchor:
            self.anchor_mod.anchor_shortcut()

        mock_setup.assert_not_called()
        mock_create_anchor.assert_called_once()

    def test_plugin_disabled_does_not_open_the_backdrop_dialog(self):
        backdrop = _make_backdrop_node()
        self.nuke_stub.selectedNodes = MagicMock(return_value=[backdrop])

        with patch.object(self.anchor_mod.prefs, 'plugin_enabled', False), \
             patch.object(self.anchor_mod.labels, 'setup_backdrop') as mock_setup:
            self.anchor_mod.anchor_shortcut()

        mock_setup.assert_not_called()


# ---------------------------------------------------------------------------
# BackdropDialog — source-level checks
#
# Qt is stubbed as a MagicMock offline, so `class BackdropDialog(...)` evaluates
# to a mock rather than a real class and cannot be instantiated. The existing
# colour-picker tests handle this by reading colors.py's AST; these do the same.
# ---------------------------------------------------------------------------

def _colors_source():
    """Return the full text of colors.py."""
    with open(_REPO_ROOT / 'colors.py', 'r') as source_file:
        return source_file.read()


def _node_source(node):
    """Return the dedented source text spanned by an AST *node*."""
    source_lines = _colors_source().splitlines()
    return textwrap.dedent('\n'.join(source_lines[node.lineno - 1:node.end_lineno]))


def _class_node(class_name):
    """Return the ast.ClassDef named *class_name* in colors.py, or None."""
    for node in ast.walk(ast.parse(_colors_source())):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _method_source(class_node, method_name):
    """Return the dedented source of *method_name* on *class_node*, or None."""
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == method_name:
            return _node_source(item)
    return None


class TestBackdropDialogDefinition(unittest.TestCase):
    """The dialog reuses the colour palette and adds the backdrop-only controls."""

    def setUp(self):
        self.class_node = _class_node('BackdropDialog')
        if self.class_node is None:
            self.fail("BackdropDialog not found in colors.py")

    def test_extends_the_colour_palette_dialog(self):
        base_names = [base.id for base in self.class_node.bases if isinstance(base, ast.Name)]
        self.assertIn('ColorPaletteDialog', base_names)

    def test_uses_a_multiline_label_field(self):
        self.assertIn('_NAME_FIELD_MULTILINE = True', _node_source(self.class_node))

    def test_builds_a_font_size_selector_and_a_fill_checkbox(self):
        source = _method_source(self.class_node, '_build_extra_fields')
        self.assertIsNotNone(source, "_build_extra_fields not found on BackdropDialog")
        self.assertIn('QComboBox', source)
        self.assertIn('BACKDROP_FONT_SIZE_PRESETS', source)
        self.assertIn('Custom', source)
        self.assertIn('QSpinBox', source)
        self.assertIn('QCheckBox', source)

    def test_accept_captures_the_font_size_and_fill_choices(self):
        source = _method_source(self.class_node, 'accept')
        self.assertIsNotNone(source, "accept() not found on BackdropDialog")
        self.assertIn('self.chosen_font_size', source)
        self.assertIn('self.chosen_filled', source)
        self.assertIn('super().accept()', source)

    def test_custom_font_size_sentinel_is_not_a_valid_preset(self):
        from colors import BACKDROP_CUSTOM_FONT_SIZE
        from constants import BACKDROP_FONT_SIZE_PRESETS

        self.assertNotIn(
            BACKDROP_CUSTOM_FONT_SIZE,
            [size for _name, size in BACKDROP_FONT_SIZE_PRESETS],
        )


class TestColorPaletteDialogNameFieldHooks(unittest.TestCase):
    """The base dialog gained the hooks BackdropDialog builds on."""

    def setUp(self):
        self.class_node = _class_node('ColorPaletteDialog')
        if self.class_node is None:
            self.fail("ColorPaletteDialog not found in colors.py")

    def test_name_field_text_reads_the_matching_widget_kind(self):
        source = _method_source(self.class_node, '_name_field_text')
        self.assertIsNotNone(source, "_name_field_text not found on ColorPaletteDialog")
        self.assertIn('toPlainText()', source)
        self.assertIn('.text()', source)

    def test_build_ui_calls_the_extra_fields_hook(self):
        source = _method_source(self.class_node, '_build_ui')
        self.assertIsNotNone(source, "_build_ui not found on ColorPaletteDialog")
        self.assertIn('self._build_extra_fields(outer_layout)', source)


if __name__ == '__main__':
    unittest.main()
