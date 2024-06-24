import unittest

from ableton_control_suface_as_code.core_model import EncoderType, MidiType
from ableton_control_suface_as_code.model_v2 import ControllerV2, build_mixer_model_v2, MixerV2, MixerMappingsV2, \
    ControlGroupV2, ControlGroupAggregateV2, ControllerRawV2, ControlGroupPartV2
from tests.test_mixer_template import CustomAssertions


class TestMixerTemplates(unittest.TestCase, CustomAssertions):
    def build_1_group_controller(self, midi_range='21-28'):
        return ControllerV2.build_from(ControllerRawV2(
            on_led_midi =1,
            off_led_midi=1,
            control_groups=[ControlGroupPartV2(
                layout='row',
                number=1,
                type=EncoderType.knob,
                midi_channel=2,
                midi_type=MidiType.CC,
                midi_range=midi_range
            )]))

    def test_mixer_pan(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(pan="row_1:2"))
        result = build_mixer_model_v2(self.build_1_group_controller(), mixer)

        self.assertEqual(result.midi_maps[0].midi_type, "CC")
        self.assertEqual(result.midi_maps[0].midi_channel, 2)
        self.assertEqual(result.midi_maps[0].midi_number, 22)
        self.assertEqual(result.midi_maps[0].encoder_coords.row, 1)
        self.assertEqual(result.midi_maps[0].encoder_coords.col, 2)
        self.assertEqual(result.midi_maps[0].encoder_coords.row_range_end, 2)
        self.assertEqual(result.midi_maps[0].api_function, "pan")


    def test_mixer_sends(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(sends="row_1:5-8"))
        result = build_mixer_model_v2(self.build_1_group_controller(midi_range='21-28'), mixer)

        map_1 = result.midi_maps[0]
        map_1_coords = map_1.midi_coords[0]
        self.assertEqual("CC", map_1_coords.type)
        self.assertEqual(2, map_1_coords.channel)
        self.assertEqual(25, map_1_coords.number)
        self.assertEqual(map_1.encoder_coords.row, 1)
        self.assertEqual(map_1.encoder_coords.col, 5)
        self.assertEqual(map_1.encoder_coords.row_range_end, 8)
        self.assertEqual(map_1.api_function, "sends")


    def test_master_volume(self):
        mixer = MixerV2(track='master', mappings=MixerMappingsV2(volume="row_1:1"))
        result = build_mixer_model_v2(self.build_1_group_controller(midi_range='1-1'), mixer)

        map_1 = result.midi_maps[0]
        self.assertEqual("CC", map_1.midi_type)
        self.assertEqual(2, map_1.midi_channel)
        self.assertEqual(1, map_1.midi_number)
        self.assertEqual(map_1.encoder_coords.row, 1)
        self.assertEqual(map_1.encoder_coords.col, 1)
        self.assertEqual(map_1.encoder_coords.row_range_end, 1)
        self.assertEqual(map_1.api_function, "volume")




