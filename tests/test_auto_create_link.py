"""Tests for the auto-create-link behaviour of create_anchor() (issue #69).

Covers:
- create_link_below_anchor() places the link centred directly beneath the anchor
- create_anchor() creates a link when prefs.auto_create_link is True
- create_anchor() creates no link when prefs.auto_create_link is False
- Both the Qt dialog path and the plain-text fallback path honour the preference
- create_anchor_named() itself never creates a link (the public API stays a
  single-node primitive)
"""

import ast
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from constants import ANCHOR_PREFIX
from tests.stubs import StubKnob, StubNode

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_anchor_node(name='Foo', xpos=100, ypos=200):
    """Return a StubNode that acts as a freshly created NoOp anchor."""
    return StubNode(
        name=ANCHOR_PREFIX + name,
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            'label': StubKnob(name),
            'tile_color': StubKnob(0),
            'selected': StubKnob(True),
        },
    )


def _make_link_node(name='NoOp1', xpos=0, ypos=0):
    """Return a StubNode representing a newly created link node."""
    return StubNode(
        name=name,
        node_class='NoOp',
        xpos=xpos,
        ypos=ypos,
        knobs_dict={
            'selected': StubKnob(False),
        },
    )


def _prefs_dialog_method_source(method_name):
    """Return the source text of a PrefsDialog method in colors.py, or None.

    Qt is stubbed out as a MagicMock in this suite, so the dialog cannot be
    instantiated; source inspection is how the rest of the suite pins down
    PrefsDialog wiring (see tests/test_anchor_color_system.py).
    """
    source_text = (_REPO_ROOT / 'colors.py').read_text()
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'PrefsDialog':
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    source_lines = source_text.splitlines()
                    return '\n'.join(source_lines[item.lineno - 1:item.end_lineno])
    return None


def _accepting_dialog(chosen_name='Foo'):
    """Return a ColorPaletteDialog stand-in whose exec_() reports Accepted."""
    import anchor as anchor_module
    dialog = MagicMock()
    dialog.exec_.return_value = anchor_module.QtWidgets.QDialog.Accepted
    dialog.chosen_name = chosen_name
    dialog.chosen_custom_colors.return_value = []
    dialog.selected_color_int.return_value = 0x8040FFFF
    return dialog


# ---------------------------------------------------------------------------
# create_link_below_anchor() placement
# ---------------------------------------------------------------------------

class TestCreateLinkBelowAnchor(unittest.TestCase):
    """The link is centred on the anchor and sits one node height below it."""

    def test_link_positioned_directly_below_anchor(self):
        """setXYpos centres the link horizontally and offsets it by height + 20."""
        anchor_node = _make_anchor_node('Foo', xpos=100, ypos=200)
        link_node = _make_link_node()
        # StubNode: screenWidth() == 100, screenHeight() == 50
        expected_x = 100 + 100 // 2 - 100 // 2   # 100
        expected_y = 200 + 50 + 20               # 270

        with patch('anchor.create_from_anchor', return_value=link_node) as mock_create_from_anchor:
            import anchor as anchor_module
            returned_link = anchor_module.create_link_below_anchor(anchor_node)

        mock_create_from_anchor.assert_called_once_with(anchor_node)
        self.assertIs(returned_link, link_node)
        self.assertEqual(link_node.xpos(), expected_x)
        self.assertEqual(link_node.ypos(), expected_y)

    def test_narrower_link_is_centred_on_a_wider_anchor(self):
        """A link narrower than its anchor is centred rather than left-aligned."""
        anchor_node = _make_anchor_node('Foo', xpos=300, ypos=40)
        link_node = _make_link_node()
        link_node.screenWidth = lambda: 20  # e.g. a Dot link under a wider anchor

        with patch('anchor.create_from_anchor', return_value=link_node):
            import anchor as anchor_module
            anchor_module.create_link_below_anchor(anchor_node)

        self.assertEqual(link_node.xpos(), 300 + 100 // 2 - 20 // 2)  # 340
        self.assertEqual(link_node.ypos(), 40 + 50 + 20)              # 110


# ---------------------------------------------------------------------------
# create_anchor() — plain-text fallback path (Qt unavailable)
# ---------------------------------------------------------------------------

class TestCreateAnchorPlainTextPath(unittest.TestCase):
    """The nuke.getInput() fallback honours prefs.auto_create_link."""

    def _run_create_anchor(self, auto_create_link):
        anchor_node = _make_anchor_node('Foo')
        link_node = _make_link_node()

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.ColorPaletteDialog', None), \
             patch('anchor.create_anchor_named',
                   return_value=anchor_node) as mock_create_anchor_named, \
             patch('anchor.create_from_anchor',
                   return_value=link_node) as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_prefs.auto_create_link = auto_create_link
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = []
            mock_nuke.getInput.return_value = 'Foo'

            import anchor as anchor_module
            anchor_module.create_anchor()

        return mock_create_anchor_named, mock_create_from_anchor, anchor_node, link_node

    def test_link_created_when_preference_enabled(self):
        """auto_create_link=True creates one link wired to the new anchor."""
        (mock_create_anchor_named, mock_create_from_anchor,
         anchor_node, link_node) = self._run_create_anchor(auto_create_link=True)

        mock_create_anchor_named.assert_called_once_with('Foo', None, color=None)
        mock_create_from_anchor.assert_called_once_with(anchor_node)
        self.assertEqual(link_node.ypos(), anchor_node.ypos() + 50 + 20)

    def test_no_link_created_when_preference_disabled(self):
        """auto_create_link=False still creates the anchor but no link."""
        (mock_create_anchor_named, mock_create_from_anchor,
         _anchor_node, _link_node) = self._run_create_anchor(auto_create_link=False)

        mock_create_anchor_named.assert_called_once_with('Foo', None, color=None)
        mock_create_from_anchor.assert_not_called()

    def test_no_link_created_when_name_prompt_cancelled(self):
        """Cancelling the name prompt creates neither an anchor nor a link."""
        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.ColorPaletteDialog', None), \
             patch('anchor.create_anchor_named') as mock_create_anchor_named, \
             patch('anchor.create_from_anchor') as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_prefs.auto_create_link = True
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = []
            mock_nuke.getInput.return_value = ''

            import anchor as anchor_module
            anchor_module.create_anchor()

        mock_create_anchor_named.assert_not_called()
        mock_create_from_anchor.assert_not_called()


# ---------------------------------------------------------------------------
# create_anchor() — Qt dialog path
# ---------------------------------------------------------------------------

class TestCreateAnchorDialogPath(unittest.TestCase):
    """The ColorPaletteDialog path honours prefs.auto_create_link."""

    def _run_create_anchor(self, auto_create_link):
        anchor_node = _make_anchor_node('Foo')
        link_node = _make_link_node()
        dialog = _accepting_dialog('Foo')

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.ColorPaletteDialog', return_value=dialog), \
             patch('anchor._persist_custom_colors_from_dialog'), \
             patch('anchor._derive_dialog_default_color', return_value=0), \
             patch('anchor.create_anchor_named',
                   return_value=anchor_node) as mock_create_anchor_named, \
             patch('anchor.create_from_anchor',
                   return_value=link_node) as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_prefs.auto_create_link = auto_create_link
            mock_prefs.custom_colors = []
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = []

            import anchor as anchor_module
            anchor_module.create_anchor()

        return mock_create_anchor_named, mock_create_from_anchor, anchor_node, link_node

    def test_link_created_when_preference_enabled(self):
        """auto_create_link=True creates one link below the accepted anchor."""
        (mock_create_anchor_named, mock_create_from_anchor,
         anchor_node, link_node) = self._run_create_anchor(auto_create_link=True)

        mock_create_anchor_named.assert_called_once_with('Foo', None, color=0x8040FFFF)
        mock_create_from_anchor.assert_called_once_with(anchor_node)
        self.assertEqual(link_node.xpos(), anchor_node.xpos())
        self.assertEqual(link_node.ypos(), anchor_node.ypos() + 50 + 20)

    def test_no_link_created_when_preference_disabled(self):
        """auto_create_link=False leaves the anchor on its own."""
        (mock_create_anchor_named, mock_create_from_anchor,
         _anchor_node, _link_node) = self._run_create_anchor(auto_create_link=False)

        mock_create_anchor_named.assert_called_once_with('Foo', None, color=0x8040FFFF)
        mock_create_from_anchor.assert_not_called()

    def test_no_link_created_when_dialog_rejected(self):
        """A rejected dialog creates neither an anchor nor a link."""
        dialog = MagicMock()
        dialog.exec_.return_value = 'rejected'

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.ColorPaletteDialog', return_value=dialog), \
             patch('anchor._derive_dialog_default_color', return_value=0), \
             patch('anchor.create_anchor_named') as mock_create_anchor_named, \
             patch('anchor.create_from_anchor') as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_prefs.auto_create_link = True
            mock_prefs.custom_colors = []
            mock_nuke.lastHitGroup.return_value = MagicMock()
            mock_nuke.selectedNodes.return_value = []

            import anchor as anchor_module
            anchor_module.create_anchor()

        mock_create_anchor_named.assert_not_called()
        mock_create_from_anchor.assert_not_called()


# ---------------------------------------------------------------------------
# create_anchor_named() stays a single-node primitive
# ---------------------------------------------------------------------------

class TestCreateAnchorNamedCreatesNoLink(unittest.TestCase):
    """The public API primitive must not gain a second node (api.create_anchor)."""

    def test_no_link_created_even_when_preference_enabled(self):
        """create_anchor_named() never calls create_from_anchor(), pref or not."""
        anchor_node = _make_anchor_node('Foo')

        with patch('anchor.prefs') as mock_prefs, \
             patch('anchor.nuke') as mock_nuke, \
             patch('anchor.nukescripts'), \
             patch('anchor.find_anchor_color', return_value=0), \
             patch('anchor.create_from_anchor') as mock_create_from_anchor:
            mock_prefs.plugin_enabled = True
            mock_prefs.auto_create_link = True
            mock_nuke.createNode.return_value = anchor_node

            import anchor as anchor_module
            created = anchor_module.create_anchor_named('Foo')

        self.assertIs(created, anchor_node)
        mock_create_from_anchor.assert_not_called()
        mock_nuke.createNode.assert_called_once_with('NoOp')


# ---------------------------------------------------------------------------
# PrefsDialog exposes the preference
# ---------------------------------------------------------------------------

class TestPrefsDialogAutoCreateLinkCheckbox(unittest.TestCase):
    """The preference must be reachable from Anchor Preferences..., and persist."""

    def test_build_ui_creates_the_checkbox(self):
        """_build_ui adds a checkbox seeded from the local working copy."""
        build_ui_source = _prefs_dialog_method_source('_build_ui')
        self.assertIsNotNone(build_ui_source, "PrefsDialog._build_ui not found in colors.py")
        self.assertIn('self._auto_create_link_checkbox = QtWidgets.QCheckBox', build_ui_source)
        self.assertIn(
            'self._auto_create_link_checkbox.setChecked(self._local_auto_create_link)',
            build_ui_source,
        )

    def test_init_seeds_the_local_working_copy(self):
        """__init__ seeds _local_auto_create_link from the prefs module."""
        init_source = _prefs_dialog_method_source('__init__')
        self.assertIsNotNone(init_source, "PrefsDialog.__init__ not found in colors.py")
        self.assertIn(
            'self._local_auto_create_link = prefs_module.auto_create_link',
            init_source,
        )

    def test_on_accept_flushes_the_checkbox_to_prefs(self):
        """_on_accept writes the checkbox state back to the prefs module before save()."""
        accept_source = _prefs_dialog_method_source('_on_accept')
        self.assertIsNotNone(accept_source, "PrefsDialog._on_accept not found in colors.py")
        self.assertIn(
            'prefs_module.auto_create_link = self._local_auto_create_link',
            accept_source,
        )
        self.assertIn(
            'self._local_auto_create_link = self._auto_create_link_checkbox.isChecked()',
            accept_source,
        )
        self.assertLess(
            accept_source.index('prefs_module.auto_create_link ='),
            accept_source.index('prefs_module.save()'),
            "the flush must happen before save() so the value is persisted",
        )


if __name__ == '__main__':
    unittest.main()
