"""Workstream C: semantic validation that today only fails at Ableton load time
must instead fail at generation time, with all problems reported at once."""
import unittest
from pathlib import Path

from ableton_control_surface_as_code.core_model import parse_coords
from ableton_control_surface_as_code.model_v2 import (
    read_root, read_controller, build_validated_model)
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


_ROOT_BASE = "controller: ec4.nt\nableton_dir: /tmp\nhud: on\nshow-hud-on: selection\n"


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


class TestAccumulatingPass(unittest.TestCase, CustomAssertions):
    """The whole-config pass must report EVERY problem at once, across both the
    controller file and the mapping file — not fail on the first one found."""

    def _build(self, mapping_text, controller_text):
        return build_validated_model(
            mapping_text, Path("/tmp"),
            resolve_controller=lambda root: (controller_text, "ctrl.nt"),
            mapping_source="mapping.nt")

    def test_reports_problems_across_both_files_at_once(self):
        # Controller file: channel 17 (out of range).
        # Mapping file: duplicate mode name AND a coord on a non-existent row.
        controller = _controller(channel="17")
        mapping = (
            _ROOT_BASE + "modes:\n"
            "    -\n        name: main_mode\n"
            "        mappings:\n"
            "            -\n                type: track-nav\n"
            "                mappings:\n"
            "                    left: row-9:1\n"      # row 9 doesn't exist
            "                    right: row-1:2\n"
            "    -\n        name: main_mode\n"          # duplicate name
            "        mappings:\n"
            "            -\n                type: track-nav\n"
            "                mappings:\n"
            "                    left: row-1:1\n"
            "                    right: row-1:2\n")
        self.assert_gen_error(
            lambda: self._build(mapping, controller),
            ErrorCode.SEMANTIC_VALIDATION,
            "17", "main_mode", "row-9")

    def test_clean_config_builds(self):
        controller = _controller(channel="3")
        mapping = (
            _ROOT_BASE + "modes:\n"
            "    -\n        name: main_mode\n"
            "        mappings:\n"
            "            -\n                type: track-nav\n"
            "                mappings:\n"
            "                    left: row-1:1\n"
            "                    right: row-1:2\n")
        root, controller_v2, mode_with_midi = self._build(mapping, controller)
        self.assertEqual(1, len(root.modes))


class TestRangeVsSlots(unittest.TestCase, CustomAssertions):
    """A device `range:` whose length doesn't match its `slots:`/`parameters:`
    count silently truncated before; now it must be a named error."""

    def _device_mapping(self, encoder_range, slots):
        return (
            _ROOT_BASE + "modes:\n"
            "    -\n        name: m1\n"
            "        mappings:\n"
            "            -\n                type: device\n"
            "                track: selected\n"
            "                device: selected\n"
            "                mappings:\n"
            "                    encoders:\n"
            f"                        range: {encoder_range}\n"
            f"                        slots: {slots}\n")

    def test_range_longer_than_slots_rejected(self):
        # range covers 8 encoders but only 4 slots are listed.
        controller = _controller(channel="3", midi_range="21-28")
        self.assert_gen_error(
            lambda: build_validated_model(
                self._device_mapping("row-1:1-8", "1-4"), Path("/tmp"),
                resolve_controller=lambda root: (controller, "ctrl.nt")),
            ErrorCode.SEMANTIC_VALIDATION, "8", "4")


class TestSwitchCoordClash(unittest.TestCase, CustomAssertions):
    """A device switch button stored in `switch_maps` that shares a physical
    control with another mapping in the same mode used to escape the clash
    check (validate_mappings only walked `midi_maps`). It must now clash."""

    # Two-row controller: row 1 knobs (CC), row 2 buttons (note).
    _CONTROLLER = (
        "control_groups:\n"
        "  -\n"
        "    layout: row\n"
        "    number: 1\n"
        "    type: knob\n"
        "    midi_channel: 1\n"
        "    midi_type: CC\n"
        "    midi_range: 21-28\n"
        "  -\n"
        "    layout: row\n"
        "    number: 2\n"
        "    type: button\n"
        "    midi_channel: 1\n"
        "    midi_type: note\n"
        "    midi_range: C2-G2\n")

    def _build(self, mapping):
        return build_validated_model(
            mapping, Path("/tmp"),
            resolve_controller=lambda root: (self._CONTROLLER, "ctrl.nt"))

    def test_switch_clashing_with_mixer_button_rejected(self):
        # device button slot 1 and mixer mute both bind row-2:1 in the same mode.
        mapping = (
            _ROOT_BASE + "modes:\n"
            "    -\n        name: m1\n"
            "        mappings:\n"
            "            -\n                type: device\n"
            "                track: selected\n"
            "                device: selected\n"
            "                mappings:\n"
            "                    button:\n"
            "                        range: row-2:1\n"
            "                        slots: 1\n"
            "            -\n                type: mixer\n"
            "                track: selected\n"
            "                mappings:\n"
            "                    mute: row-2:1\n")
        # The whole-config pass aggregates problems under SEMANTIC_VALIDATION
        # (like TestRangeVsSlots); the clash message names both mappings and the
        # shared note (C2 = 48).
        self.assert_gen_error(
            lambda: self._build(mapping),
            ErrorCode.SEMANTIC_VALIDATION, "Clashing", "device", "mixer", "48")

    def test_switches_without_overlap_build(self):
        # button slots that don't collide with anything must still build.
        mapping = (
            _ROOT_BASE + "modes:\n"
            "    -\n        name: m1\n"
            "        mappings:\n"
            "            -\n                type: device\n"
            "                track: selected\n"
            "                device: selected\n"
            "                mappings:\n"
            "                    button:\n"
            "                        range: row-2:1\n"
            "                        slots: 1\n"
            "            -\n                type: mixer\n"
            "                track: selected\n"
            "                mappings:\n"
            "                    mute: row-2:2\n")
        root, controller_v2, mode_with_midi = self._build(mapping)
        self.assertEqual(1, len(root.modes))


class TestModeButtonCollision(unittest.TestCase, CustomAssertions):
    """A mapping bound onto the mode-button's own control double-binds the note
    and wedges the shift FSM at runtime — it must be rejected at generate time."""

    _CONTROLLER = (
        "light_colors:\n"
        "    c1: 1\n"
        "    c2: 2\n"
        "control_groups:\n"
        "  -\n"
        "    layout: row\n"
        "    number: 1\n"
        "    type: knob\n"
        "    midi_channel: 1\n"
        "    midi_type: CC\n"
        "    midi_range: 21-28\n"
        "  -\n"
        "    layout: row\n"
        "    number: 2\n"
        "    type: button\n"
        "    midi_channel: 1\n"
        "    midi_type: note\n"
        "    midi_range: C2-G2\n")

    def _build(self, mapping):
        return build_validated_model(
            mapping, Path("/tmp"),
            resolve_controller=lambda root: (self._CONTROLLER, "ctrl.nt"))

    _SHIFT = (
        "mode-button:\n"
        "    button: row-2:1\n"
        "    type: shift\n"
        "modes:\n"
        "    -\n        name: base\n        on_color: c1\n"
        "        mappings:\n"
        "            -\n                type: mixer\n"
        "                track: selected\n"
        "                mappings:\n"
        "                    mute: row-2:2\n"
        "    -\n        name: shift\n        on_color: c2\n"
        "        mappings:\n")

    def test_mapping_on_mode_button_rejected(self):
        # shift mode binds `solo` onto row-2:1 — the mode-button control itself.
        mapping = _ROOT_BASE + self._SHIFT + (
            "            -\n                type: mixer\n"
            "                track: selected\n"
            "                mappings:\n"
            "                    solo: row-2:1\n")
        self.assert_gen_error(
            lambda: self._build(mapping),
            ErrorCode.SEMANTIC_VALIDATION, "mode-button", "shift")

    def test_mapping_off_mode_button_builds(self):
        # shift mode binds `solo` onto a free control — must build.
        mapping = _ROOT_BASE + self._SHIFT + (
            "            -\n                type: mixer\n"
            "                track: selected\n"
            "                mappings:\n"
            "                    solo: row-2:3\n")
        root, controller_v2, mode_with_midi = self._build(mapping)
        self.assertEqual(2, len(root.modes))
