"""Workstream C: semantic validation that today only fails at Ableton load time
must instead fail at generation time, with all problems reported at once."""
import unittest

from ableton_control_surface_as_code.core_model import parse_coords
from ableton_control_surface_as_code.model_v2 import read_root, read_controller
from ableton_control_surface_as_code.gen_error import ErrorCode
from tests.custom_assertions import CustomAssertions


def _controller(channel="3", midi_range="21-28", channel2=None, range2=None):
    doc = ("control_groups:\n"
           "  -\n"
           "    layout: row\n"
           "    number: 1\n"
           "    type: knob\n"
           f"    midi_channel: {channel}\n"
           "    midi_type: CC\n"
           f"    midi_range: {midi_range}\n")
    if channel2 is not None:
        doc += ("  -\n"
                "    layout: row\n"
                "    number: 2\n"
                "    type: knob\n"
                f"    midi_channel: {channel2}\n"
                "    midi_type: CC\n"
                f"    midi_range: {range2}\n")
    return doc


_ROOT_BASE = "controller: ec4.nt\nableton_dir: /tmp\n"


def _two_modes(name1, name2):
    nav = ("        mappings:\n"
           "            -\n"
           "                type: track-nav\n"
           "                mappings:\n"
           "                    left: row-1:1\n"
           "                    right: row-1:2\n")
    return (_ROOT_BASE + "modes:\n" +
            f"    -\n        name: {name1}\n" + nav +
            f"    -\n        name: {name2}\n" + nav)


class TestEncoderSemantics(unittest.TestCase, CustomAssertions):

    def test_descending_range_rejected(self):
        self.assert_gen_error(
            lambda: parse_coords("row-1:8-1"),
            ErrorCode.SEMANTIC_VALIDATION, "8-1")

    def test_zero_axis_rejected(self):
        self.assert_gen_error(
            lambda: parse_coords("row-0:1"), ErrorCode.SEMANTIC_VALIDATION)

    def test_valid_range_still_parses(self):
        self.assertEqual((1, 8), parse_coords("row-1:1-8").range_)


class TestControllerSemantics(unittest.TestCase, CustomAssertions):

    def test_midi_channel_out_of_range(self):
        self.assert_gen_error(
            lambda: read_controller(_controller(channel="17")),
            ErrorCode.SEMANTIC_VALIDATION, "channel", "17")

    def test_midi_number_out_of_range(self):
        # 120-130 overflows past the MIDI max of 127.
        self.assert_gen_error(
            lambda: read_controller(_controller(midi_range="120-130")),
            ErrorCode.SEMANTIC_VALIDATION, "127")

    def test_reports_all_problems_at_once(self):
        # One bad channel AND one bad number, in different groups: a single
        # GenError must mention both — proving accumulation, not fail-fast.
        e = self.assert_gen_error(
            lambda: read_controller(
                _controller(channel="17", channel2="2", range2="120-130")),
            ErrorCode.SEMANTIC_VALIDATION, "channel", "17", "127")

    def test_valid_controller_passes(self):
        # Should not raise.
        read_controller(_controller())


class TestModeSemantics(unittest.TestCase, CustomAssertions):

    def test_duplicate_mode_names_rejected(self):
        self.assert_gen_error(
            lambda: read_root(_two_modes("main_mode", "main_mode")),
            ErrorCode.SEMANTIC_VALIDATION, "main_mode")

    def test_distinct_mode_names_ok(self):
        root = read_root(_two_modes("main_mode", "shift_mode"))
        self.assertEqual(2, len(root.modes))
