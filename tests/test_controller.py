import unittest

from ableton_control_suface_as_code.core_model import EncoderCoords
from ableton_control_suface_as_code.model_controller import ControllerV2
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part


class TestBuildModeModelV2(unittest.TestCase):

    # def test_build_mode_model(self):
    #     device_with_midi = build_mode_model_v2([self.build_mode_model_v2()], self.build_controller())
    #     self.assertEqual(len(device_with_midi[0].midi_range_maps), 16)  # 9 parameters for each of the 2 rows

    def test_build_midi_coords(self):

        controller = ControllerV2.build_from(build_raw_controller_v2())
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=1))

        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 21)

    def test_build_midi_coords_over_rws(self):

        groups =[
            build_control_group_part(midi_range='21-24', number=1, layout='row-part', row_parts='1-4'),
            build_control_group_part(midi_range='25-28', number=1, layout='row-part', row_parts='5-8')
        ]


        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=8))

        self.assertEqual(8, len(e))
        self.assertEqual(e[0].number, 21)
        self.assertEqual(e[7].number, 28)


    def test_build_midi_coords_from_list(self):

        groups =[
            build_control_group_part(midi_range='29, 10, 11, 12', number=1, layout='row-part', row_parts='1-4'),
        ]


        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=4))

        self.assertEqual(4, len(e))
        self.assertEqual(e[0].number, 29)
        self.assertEqual(e[3].number, 12)
