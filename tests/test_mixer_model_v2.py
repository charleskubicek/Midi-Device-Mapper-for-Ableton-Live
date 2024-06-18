import unittest

from ableton_control_suface_as_code.model_v2 import ControllerV2, build_mixer_model_v2, MixerV2, MixerMappingsV2, \
    ControlGroupV2
from tests.test_mixer_template import CustomAssertions


class TestMixerTemplates(unittest.TestCase, CustomAssertions):
    def build_controller(self):
        return ControllerV2.model_construct(
            on_led_midi =1,
            off_led_midi=1,
            control_groups=[ControlGroupV2.model_construct(
                layout='row',
                number=1,
                type='knob',
                midi_channel=2,
                midi_type="CC",
                midi_range='21-28'
            )])

    def test_mixer(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(pan="row_1:2"))
        result = build_mixer_model_v2(self.build_controller(), mixer)

        self.assertEqual(result.midi_maps[0].midi_type, "CC")
        self.assertEqual(result.midi_maps[0].midi_channel, 2)
        self.assertEqual(result.midi_maps[0].midi_number, 22)
        self.assertEqual(result.midi_maps[0].encoder_coords.row, 1)
        self.assertEqual(result.midi_maps[0].encoder_coords.col, 2)
        self.assertEqual(result.midi_maps[0].encoder_coords.cols, None)
        self.assertEqual(result.midi_maps[0].api_function, "pan")




    def test_mixer_sends(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(sends="row_1:5-8"))
        result = build_mixer_model_v2(self.build_controller(), mixer)

        self.assertEqual(result.midi_maps[0].midi_type, "CC")
        self.assertEqual(result.midi_maps[0].midi_channel, 2)
        self.assertEqual(result.midi_maps[0].midi_number, 22)
        self.assertEqual(result.midi_maps[0].encoder_coords.row, 1)
        self.assertEqual(result.midi_maps[0].encoder_coords.col, 2)
        self.assertEqual(result.midi_maps[0].encoder_coords.cols, None)
        self.assertEqual(result.midi_maps[0].api_function, "send")




