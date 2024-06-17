import unittest

from tests.test_mixer_template import CustomAssertions
from ableton_control_suface_as_code.model import ControllerV1, build_mixer_model, MixerV1, MixerMappingsV1


class TestMixerTemplates(unittest.TestCase, CustomAssertions):
    def build_controller(self):
        self.controller = {
            'control_groups': [
                {
                    'layout': 'row',
                    'number': 1,
                    'type': 'knob',
                    'midi_channel': 2,
                    'midi_type': "CC",
                    'midi_range': {'from': 21, 'to': 28}
                },
            ],
        }

        return ControllerV1.model_validate(self.controller)

    def test_mixer_(self):
        mixer = MixerV1(track='selected', mappings=MixerMappingsV1(pan="r1-2"))
        result = build_mixer_model(self.build_controller(), mixer)

        self.assertEqual(result.midi_maps[0].midi_type, "CC")
        self.assertEqual(result.midi_maps[0].midi_channel, 2)
        self.assertEqual(result.midi_maps[0].midi_number, 22)
        self.assertEqual(result.midi_maps[0].encoder_coords, "r1-2")
        self.assertEqual(result.midi_maps[0].api_function, "pan")




