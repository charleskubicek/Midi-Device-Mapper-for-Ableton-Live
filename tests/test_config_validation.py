"""Workstream B: structural (Pydantic) config errors must surface as readable
GenErrors naming the file, the key, and the valid options — never a raw 16-line
Pydantic union dump."""
import unittest

from ableton_control_surface_as_code.model_v2 import read_root, read_controller
from ableton_control_surface_as_code.gen_error import ErrorCode
from tests.custom_assertions import CustomAssertions


_ROOT_BASE = """\
controller: ec4.nt
ableton_dir: /tmp
hud: on
show-hud-on: selection
"""

_CONTROLLER_BASE = """\
light_colors:
control_groups:
  -
    layout: row
    number: 1
    type: knob
    midi_channel: 3
    midi_type: CC
    midi_range: 21-28
"""


def _root_with_mapping(type_value="device", extra=""):
    return _ROOT_BASE + (
        "modes:\n"
        "    -\n"
        "        name: m1\n"
        "        mappings:\n"
        "            -\n"
        f"                type: {type_value}\n"
        f"{extra}"
    )


class TestStructuralConfigErrors(unittest.TestCase, CustomAssertions):

    def test_B1_unknown_mapping_type(self):
        e = self.assert_gen_error(
            lambda: read_root(_root_with_mapping("devcie")),
            ErrorCode.CONFIG_VALIDATION,
            "devcie", "device", "mixer")
        # Must NOT be a raw pydantic dump of all 8 union members.
        self.assertNotIn("MixerV2", str(e))

    def test_B2_missing_type_key(self):
        doc = (_ROOT_BASE +
               "modes:\n"
               "    -\n"
               "        name: m1\n"
               "        mappings:\n"
               "            -\n"
               "                track: selected\n")
        self.assert_gen_error(
            lambda: read_root(doc), ErrorCode.CONFIG_VALIDATION, "type")

    _VALID_TRACK_NAV = (
        "                mappings:\n"
        "                    left: row-1:1\n"
        "                    right: row-1:2\n")

    def test_B4_mode_button_missing_button(self):
        doc = (_root_with_mapping("track-nav", self._VALID_TRACK_NAV) +
               "mode-button:\n"
               "    type: shift\n")
        self.assert_gen_error(
            lambda: read_root(doc), ErrorCode.CONFIG_VALIDATION, "button")

    def test_B6_controller_bad_midi_type(self):
        doc = _CONTROLLER_BASE.replace("midi_type: CC", "midi_type: cc")
        self.assert_gen_error(
            lambda: read_controller(doc), ErrorCode.CONFIG_VALIDATION)

    def test_valid_root_still_parses(self):
        root = read_root(_root_with_mapping("track-nav", self._VALID_TRACK_NAV))
        self.assertEqual(len(root.modes), 1)
