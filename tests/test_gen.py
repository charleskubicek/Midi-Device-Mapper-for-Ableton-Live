# from ableton_control_surface_as_code import gen

import unittest
from difflib import Differ
from unittest.mock import patch

from autopep8 import fix_code

import builders
from ableton_control_surface_as_code.gen import generate_code_as_template_vars, create_code_model
from ableton_control_surface_as_code.gen_code import generate_parameter_listener_action
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi, AllMappingWithMidiTypes, ModeMappingsV2, \
    ModeGroupV2
from model_device import DeviceWithMidi
from tests.builders import build_mixer_with_midi, build_midi_device_mapping
from tests.custom_assertions import CustomAssertions

differ = Differ()


def diff(a, b):
    return ''.join(differ.compare(a.split("\n"), b.split("\n")))


class TestGen(unittest.TestCase, CustomAssertions):

    def test_generate_code_in_template_vars(self):
        mixer_with_midi = build_mixer_with_midi(api_fn='pan')

        m = ModeGroupWithMidi(mappings={"mode_1": [mixer_with_midi]})

        res = generate_code_as_template_vars(m)
        self.assertGreater(len(res['code_creation']), 1)

    def test_generate_lister_fn(self):
        n = 1
        parameter = 2

        expected_output = """
def fn(self, value):
    device = lom_value
    self.device_parameter_action(device, 2, 22, value, "fn")
    """

        expected_output = fix_code(expected_output)
        generated = fix_code("\n".join(generate_parameter_listener_action(
            parameter, 22, "lom_value", 'selected', 'fn', False, "dbg")))

        print(generated)

        expected_call = 'self.device_parameter_action(device, 2, 22, value, "fn", toggle=False'
        self.assert_string_in(expected_call, generated)

        expected_device = 'device = self.find_device("lom_value", "selected")'
        self.assert_string_in(expected_device, generated)

    def test_create_code_model(self):
        mode_mappings = [
            ("mode_1", [build_midi_device_mapping(param=1)]),
            ("mode_2", [build_midi_device_mapping(param=1)])
        ]
        mm = ModeMappingsV2(mode_group=ModeGroupV2(button='0', modes=[]),
                            button=builders.midi_coords_ch2_cc_50_knob())

        modes = ModeGroupWithMidi(mappings=mode_mappings, mode_mappings={})

        with patch('ableton_control_surface_as_code.gen_code.GeneratedCodes') as MockGeneratedCodes:
            MockGeneratedCodes.common_midi_coords_in_control_defs.return_value = []
        result = create_code_model(modes)

        self.assertIn("mode_1", result)
        self.assertIn("mode_2", result)
        self.assertEqual(len(result["mode_1"]), 1)
        self.assertEqual(len(result["mode_2"]), 1)

        if __name__ == '__main__':
            unittest.main()
