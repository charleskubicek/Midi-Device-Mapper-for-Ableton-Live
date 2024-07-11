import unittest

from ableton_control_surface_as_code.model_mixer import MixerMappingsV2, MixerV2, build_mixer_model_v2
from tests.builders import build_1_group_controller
from tests.custom_assertions import CustomAssertions


class TestMixerTemplates(unittest.TestCase, CustomAssertions):

    def test_mixer_pan(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(pan="row-1:2"))
        result = build_mixer_model_v2(build_1_group_controller(), mixer)

        self.assertEqual(result.midi_maps[0].midi_type, "CC")
        self.assertEqual(result.midi_maps[0].midi_channel, 2)
        self.assertEqual(result.midi_maps[0].midi_number, 22)
        self.assertEqual(result.midi_maps[0].encoder_coords.row, 1)
        self.assertEqual(result.midi_maps[0].encoder_coords.col, 2)
        self.assertEqual(result.midi_maps[0].encoder_coords.row_range_end, 2)
        self.assertEqual(result.midi_maps[0].api_function, "pan")


    def test_mixer_sends(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(sends="row-1:5-8"))
        result = build_mixer_model_v2(build_1_group_controller(midi_range='21-28'), mixer)

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
        mixer = MixerV2(track='master', mappings=MixerMappingsV2(volume="row-1:1"))
        result = build_mixer_model_v2(build_1_group_controller(midi_range='1-1'), mixer)

        map_1 = result.midi_maps[0]
        self.assertEqual("CC", map_1.midi_type)
        self.assertEqual(2, map_1.midi_channel)
        self.assertEqual(1, map_1.midi_number)
        self.assertEqual(map_1.encoder_coords.row, 1)
        self.assertEqual(map_1.encoder_coords.col, 1)
        self.assertEqual(map_1.encoder_coords.row_range_end, 1)
        self.assertEqual(map_1.api_function, "volume")




