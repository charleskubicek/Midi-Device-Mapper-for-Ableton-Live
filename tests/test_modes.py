import unittest
from ableton_control_surface_as_code.core_model import MidiCoords, EncoderType, MidiType
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi, ModeMappingsV2, ModeGroupV2
from tests.builders import midi_coords_ch2_cc_50_knob


class TestModes(unittest.TestCase):

    def test_fsm_function(self):
        mg = ModeGroupV2(
            button="row-3:1",
            type="switch",
            on_color="ignored",
            off_color="ignored",
            mode_1=[],
            mode_2=[])

        mode_mappings = ModeMappingsV2(mode=mg,
                                       button=midi_coords_ch2_cc_50_knob(),
                                       on_color=0,
                                       off_color=1
                                       )

        mode_group = ModeGroupWithMidi(
            mode_mappings=mode_mappings, mappings={})

        expected_output = mode_group.fsm()

        self.assertEqual(expected_output[0].next, 'mode_2')
        self.assertEqual(expected_output[1].next, 'mode_1')
        self.assertEqual(expected_output[0].is_shift, False)
        self.assertEqual(expected_output[1].is_shift, False)
        self.assertEqual(expected_output[0].color, 0)
        self.assertEqual(expected_output[1].color, 1)
