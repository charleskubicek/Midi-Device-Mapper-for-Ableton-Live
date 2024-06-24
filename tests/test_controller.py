import unittest

from ableton_control_suface_as_code.core_model import EncoderCoords
from tests.test_gen_build_model_v2 import build_controller_v2, build_control_group


class TestBuildModeModelV2(unittest.TestCase):

    # def test_build_mode_model(self):
    #     device_with_midi = build_mode_model_v2([self.build_mode_model_v2()], self.build_controller())
    #     self.assertEqual(len(device_with_midi[0].midi_range_maps), 16)  # 9 parameters for each of the 2 rows

    def test_build_midi_coords(self):

        controller = build_controller_v2()
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=1))

        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 21)

    def test_build_midi_coords_over_rws(self):

        groups =[
            build_control_group(midi_range='21-24', number=1, layout='row-part'),
            build_control_group(midi_range='25-28', number=1, layout='row-part')
        ]

        controller = build_controller_v2(groups)
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=7, row_range_end=8))

        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 21)
