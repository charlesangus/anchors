"""Tests for anchor.suggest_anchor_name() — user-regex, frame-token stripping,
template substitution, and fallback behaviors.

All tests in this file are Wave 0 (TDD RED): they define the behavioral
contract for Plan 02. They will FAIL until Plan 02 adds naming_regex /
naming_template support to both prefs.py and anchor.suggest_anchor_name().

Test classes:
  TestSuggestAnchorNameUserRegex    — user-supplied regex replaces hardcoded stripping
  TestFrameTokenStripping           — frame tokens stripped before regex is applied
  TestTemplateSubstitution          — named groups substituted into template string
  TestTemplateSubstitutionFallback  — missing template group falls back to full match
  TestNoFileKnobFallback            — nodes without a 'file' knob return ""
  TestRegexNoMatchFallback          — no-match and invalid regex fall back to hardcoded path
"""

import os
import sys
import types
import unittest
from unittest.mock import patch

# Install nuke stub before importing anchor so the module-level nuke import
# inside anchor.py succeeds in a headless test environment.
from tests.stubs import StubKnob, StubNode, make_stub_nuke_module

if 'nuke' not in sys.modules:
    sys.modules['nuke'] = make_stub_nuke_module()

import anchor
import prefs as prefs_module


def _make_read_node(filepath):
    """Return a StubNode that looks like a Read node with the given file knob path."""
    file_knob = StubKnob(value=filepath, knob_name='file')
    return StubNode(name='Read1', node_class='Read', knobs_dict={'file': file_knob})


class TestSuggestAnchorNameUserRegex(unittest.TestCase):
    """User-supplied naming_regex drives the suggestion instead of the hardcoded pattern."""

    def setUp(self):
        # Patch find_smallest_containing_backdrop to return None so backdrop
        # prefix logic never fires in this test class.
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()

        # Remember original prefs values so setUp/tearDown are symmetric.
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_user_regex_applied_to_basename(self):
        """Regex with named group + template produces substituted result."""
        node = _make_read_node('/mnt/proj/plate_v003.exr')
        prefs_module.naming_regex = r'(?P<shot>.+)_v\d+'
        prefs_module.naming_template = '{shot}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'plate')

    def test_user_regex_replaces_hardcoded(self):
        """A file that only the new regex path handles correctly resolves via new path.

        Hardcoded path strips `_v003` giving `comp`. The new regex `(?P<name>comp)`
        also gives `comp` via group(0) since the whole match is `comp`. What makes
        this test discriminating is that a regex pattern that would NOT match
        without the new code path is used, confirming the new code runs.
        """
        node = _make_read_node('SEQUENCE_ONLY_REGEX.exr')
        # Only matches files starting with 'SEQ_' — the hardcoded path would give
        # 'SEQUENCE_ONLY_REGEX', but our user regex matches and returns 'SEQ'
        prefs_module.naming_regex = r'(?P<prefix>SEQ)'
        prefs_module.naming_template = '{prefix}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'SEQ')

    def test_user_regex_no_template_uses_full_match(self):
        """When naming_template is empty, the full regex match (group 0) is returned."""
        node = _make_read_node('plate_v003.exr')
        prefs_module.naming_regex = r'(?P<name>.+)_v\d+'
        prefs_module.naming_template = ''
        result = anchor.suggest_anchor_name(node)
        # group(0) of the whole regex match against 'plate_v003.exr' basename
        # The regex matches 'plate_v003' in 'plate_v003.exr'
        self.assertEqual(result, 'plate_v003')


class TestFrameTokenStripping(unittest.TestCase):
    """Frame tokens are stripped from the filename before the user regex is applied.

    Each test verifies end-to-end behavior of suggest_anchor_name(): the named
    group in the regex sees the already-stripped basename.
    """

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_strips_percent04d(self):
        """%04d frame token is removed before regex sees the filename."""
        node = _make_read_node('plate_v003.%04d.exr')
        # After stripping: 'plate_v003.exr'; regex matches with name='plate'; template gives 'plate'
        prefs_module.naming_regex = r'(?P<name>.+)_v\d+'
        prefs_module.naming_template = '{name}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'plate')

    def test_strips_hashes(self):
        """Hash frame token (####) is removed before regex sees the filename."""
        node = _make_read_node('comp_####.exr')
        # After stripping: 'comp.exr'; regex does not match _v\d+ pattern; falls to full match
        prefs_module.naming_regex = r'(?P<name>.+)_v\d+'
        prefs_module.naming_template = '{name}'
        # No match → fallback to hardcoded strip, which gives 'comp' (no _v pattern either)
        # The file 'comp.exr' has no _v\d+ so hardcoded fallback gives os.path.splitext = 'comp'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'comp')

    def test_strips_percent_capital_V(self):
        """%V stereo token is removed before regex sees the filename."""
        node = _make_read_node('left.%V.exr')
        # After stripping: 'left.exr'; regex does not match; hardcoded fallback gives 'left'
        prefs_module.naming_regex = r'(?P<name>.+)_v\d+'
        prefs_module.naming_template = '{name}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'left')

    def test_no_token_unchanged(self):
        """Files with no frame token are passed through unchanged."""
        node = _make_read_node('plate_v003.exr')
        # No frame token to strip; regex matches with name='plate'; template gives 'plate'
        prefs_module.naming_regex = r'(?P<name>.+)_v\d+'
        prefs_module.naming_template = '{name}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'plate')


class TestTemplateSubstitution(unittest.TestCase):
    """Named capture groups are substituted into the template string."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_template_substitutes_named_group(self):
        """Single named group is substituted into the template."""
        node = _make_read_node('BG010_v003.exr')
        prefs_module.naming_regex = r'(?P<shot>\w+)_v\d+'
        prefs_module.naming_template = '{shot}_anchor'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'BG010_anchor')

    def test_multiple_groups_in_template(self):
        """Multiple named groups are each substituted into the template."""
        node = _make_read_node('BG010_v003.exr')
        prefs_module.naming_regex = r'(?P<seq>[A-Z]+)(?P<num>\d+)_v\d+'
        prefs_module.naming_template = '{seq}_{num}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'BG_010')


class TestTemplateSubstitutionFallback(unittest.TestCase):
    """Template referencing a group name not present in the regex falls back to full match."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_missing_group_in_template_falls_back_to_full_match(self):
        """Template references {nonexistent} group — result is the full regex match."""
        node = _make_read_node('BG010_v003.exr')
        prefs_module.naming_regex = r'(?P<shot>\w+)_v\d+'
        prefs_module.naming_template = '{nonexistent}'
        result = anchor.suggest_anchor_name(node)
        # match.group(0) of r'(?P<shot>\w+)_v\d+' against 'BG010_v003.exr' = 'BG010_v003'
        self.assertEqual(result, 'BG010_v003')


class TestNoFileKnobFallback(unittest.TestCase):
    """Nodes without a 'file' knob produce an empty string suggestion."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_node_without_file_knob_returns_empty(self):
        """A StubNode with no 'file' knob in its knobs_dict returns ''."""
        node = StubNode(name='NoOp1', node_class='NoOp', knobs_dict={})
        prefs_module.naming_regex = r'(?P<name>.+)_v\d+'
        prefs_module.naming_template = '{name}'
        result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, '')


class TestRegexNoMatchFallback(unittest.TestCase):
    """When user regex does not match (or is invalid), hardcoded stripping is used."""

    def setUp(self):
        self._backdrop_patcher = patch(
            'anchor.find_smallest_containing_backdrop', return_value=None
        )
        self._backdrop_patcher.start()
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')

    def tearDown(self):
        self._backdrop_patcher.stop()
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def test_user_regex_no_match_falls_back_to_hardcoded(self):
        """User regex that produces no match causes fallback to hardcoded _v\\d+ strip."""
        node = _make_read_node('plate_v003.exr')
        prefs_module.naming_regex = r'^NOMATCH'
        prefs_module.naming_template = ''
        result = anchor.suggest_anchor_name(node)
        # Hardcoded path: r'^(.+)_v\d+(?:\.[^.]+)?\.[^.]+$' matches 'plate_v003.exr' → 'plate'
        self.assertEqual(result, 'plate')

    def test_invalid_regex_falls_back_to_hardcoded(self):
        """Invalid regex (re.error) is swallowed and hardcoded stripping fires."""
        node = _make_read_node('plate_v003.exr')
        prefs_module.naming_regex = r'[invalid('
        prefs_module.naming_template = ''
        result = anchor.suggest_anchor_name(node)
        # Same hardcoded fallback result as above
        self.assertEqual(result, 'plate')


class TestHtmlStrippingInBackdropLabel(unittest.TestCase):
    """HTML tags in backdrop labels are stripped before use as a name prefix.

    Regression tests for issue #10.
    """

    def setUp(self):
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')
        prefs_module.naming_regex = ''
        prefs_module.naming_template = ''

    def tearDown(self):
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def _make_backdrop(self, label):
        label_knob = StubKnob(value=label, knob_name='label')
        return StubNode(name='BackdropNode1', node_class='BackdropNode', knobs_dict={'label': label_knob})

    def test_fully_wrapped_html_tags_stripped_from_backdrop_label(self):
        """<center><b><i>PLATES</i></b></center> in backdrop label becomes PLATES prefix."""
        node = _make_read_node('shot_v001.exr')
        backdrop = self._make_backdrop('<center><b><i>PLATES</i></b></center>')
        with patch('anchor.find_smallest_containing_backdrop', return_value=backdrop):
            result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'PLATES_shot')

    def test_unclosed_html_tag_stripped_from_backdrop_label(self):
        """<b>PLATES (unclosed tag, valid in Nuke) in backdrop label becomes PLATES prefix."""
        node = _make_read_node('shot_v001.exr')
        backdrop = self._make_backdrop('<b>PLATES')
        with patch('anchor.find_smallest_containing_backdrop', return_value=backdrop):
            result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'PLATES_shot')

    def test_mixed_html_and_plain_text_stripped(self):
        """Tags interspersed with text are all removed, leaving only plain text."""
        node = _make_read_node('shot_v001.exr')
        backdrop = self._make_backdrop('<b>COMP<i>_WORK</i>')
        with patch('anchor.find_smallest_containing_backdrop', return_value=backdrop):
            result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'COMP_WORK_shot')

    def test_plain_backdrop_label_unchanged(self):
        """Backdrop labels with no HTML pass through unchanged."""
        node = _make_read_node('shot_v001.exr')
        backdrop = self._make_backdrop('PLATES')
        with patch('anchor.find_smallest_containing_backdrop', return_value=backdrop):
            result = anchor.suggest_anchor_name(node)
        self.assertEqual(result, 'PLATES_shot')


class TestHtmlStrippingInDotLabel(unittest.TestCase):
    """HTML tags in Dot node labels are stripped before use as a name suggestion.

    Regression tests for issue #10.
    """

    def setUp(self):
        self._original_naming_regex = getattr(prefs_module, 'naming_regex', '')
        self._original_naming_template = getattr(prefs_module, 'naming_template', '')
        prefs_module.naming_regex = ''
        prefs_module.naming_template = ''

    def tearDown(self):
        prefs_module.naming_regex = self._original_naming_regex
        prefs_module.naming_template = self._original_naming_template

    def _make_labelled_dot(self, label):
        label_knob = StubKnob(value=label, knob_name='label')
        return StubNode(name='Dot1', node_class='Dot', knobs_dict={'label': label_knob})

    def test_html_tags_stripped_from_dot_label(self):
        """<b>PLATES</b> in a Dot label becomes PLATES."""
        dot = self._make_labelled_dot('<b>PLATES</b>')
        with patch('anchor.find_smallest_containing_backdrop', return_value=None):
            result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, 'PLATES')

    def test_unclosed_html_tag_stripped_from_dot_label(self):
        """<b>PLATES (unclosed) in a Dot label becomes PLATES."""
        dot = self._make_labelled_dot('<b>PLATES')
        with patch('anchor.find_smallest_containing_backdrop', return_value=None):
            result = anchor.suggest_anchor_name(dot)
        self.assertEqual(result, 'PLATES')


class TestAnchorDisplayNameDuplicateDotLabels(unittest.TestCase):
    """anchor_display_name() appends node name when Dot labels are duplicated (issue #34).

    Test cases:
      - Two Dot anchors sharing the label "INPUT" each get the node name suffix.
      - A Dot anchor with a unique label is returned plain (no suffix).
    """

    def setUp(self):
        from tests.stubs import StubKnob, StubNode

        label_knob_a = StubKnob(value='INPUT', knob_name='label')
        self._dot_anchor_a = StubNode(
            name='Anchor_INPUT',
            node_class='Dot',
            knobs_dict={'label': label_knob_a},
        )

        label_knob_b = StubKnob(value='INPUT', knob_name='label')
        self._dot_anchor_b = StubNode(
            name='Anchor_INPUT1',
            node_class='Dot',
            knobs_dict={'label': label_knob_b},
        )

        label_knob_unique = StubKnob(value='OUTPUT', knob_name='label')
        self._dot_anchor_unique = StubNode(
            name='Anchor_OUTPUT',
            node_class='Dot',
            knobs_dict={'label': label_knob_unique},
        )

    def _stub_all_anchors(self, nodes):
        """Patch nuke.allNodes and link.is_anchor so _dot_anchor_duplicate_labels sees *nodes*."""
        import nuke as nuke_module
        nuke_module.allNodes.return_value = nodes

    def test_duplicate_label_dot_gets_node_name_suffix_first(self):
        """Dot anchor 'Anchor_INPUT' with duplicate label returns 'INPUT (Anchor_INPUT)'."""
        self._stub_all_anchors([self._dot_anchor_a, self._dot_anchor_b, self._dot_anchor_unique])
        with patch('anchor.is_anchor', side_effect=lambda n: n in (
            self._dot_anchor_a, self._dot_anchor_b, self._dot_anchor_unique
        )):
            result = anchor.anchor_display_name(self._dot_anchor_a)
        self.assertEqual(result, 'INPUT (Anchor_INPUT)')

    def test_duplicate_label_dot_gets_node_name_suffix_second(self):
        """Dot anchor 'Anchor_INPUT1' with duplicate label returns 'INPUT (Anchor_INPUT1)'."""
        self._stub_all_anchors([self._dot_anchor_a, self._dot_anchor_b, self._dot_anchor_unique])
        with patch('anchor.is_anchor', side_effect=lambda n: n in (
            self._dot_anchor_a, self._dot_anchor_b, self._dot_anchor_unique
        )):
            result = anchor.anchor_display_name(self._dot_anchor_b)
        self.assertEqual(result, 'INPUT (Anchor_INPUT1)')

    def test_unique_label_dot_returns_plain_label(self):
        """Dot anchor with a unique label returns just the label with no suffix."""
        self._stub_all_anchors([self._dot_anchor_a, self._dot_anchor_b, self._dot_anchor_unique])
        with patch('anchor.is_anchor', side_effect=lambda n: n in (
            self._dot_anchor_a, self._dot_anchor_b, self._dot_anchor_unique
        )):
            result = anchor.anchor_display_name(self._dot_anchor_unique)
        self.assertEqual(result, 'OUTPUT')

    def test_pre_computed_duplicate_labels_used_when_supplied(self):
        """When duplicate_dot_labels is passed in, no allNodes scan is triggered."""
        import nuke as nuke_module
        nuke_module.allNodes.reset_mock()
        duplicate_dot_labels = {'INPUT'}
        result = anchor.anchor_display_name(self._dot_anchor_a, duplicate_dot_labels)
        nuke_module.allNodes.assert_not_called()
        self.assertEqual(result, 'INPUT (Anchor_INPUT)')


if __name__ == '__main__':
    unittest.main()
