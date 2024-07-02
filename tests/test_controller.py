import unittest

from ableton_control_suface_as_code.core_model import EncoderCoords
from ableton_control_suface_as_code.model_controller import ControllerV2
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part, build_control_group


class TestBuildModeModelV2(unittest.TestCase):

    def test_build_midi_coords(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=1, encoder_refs=[]))

        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 21)

    def test_build_midi_coords_over_rws(self):
        groups = [
            build_control_group_part(midi_range='21-24', number=1, layout='row-part', row_parts='1-4'),
            build_control_group_part(midi_range='25-28', number=1, layout='row-part', row_parts='5-8')
        ]

        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=8, encoder_refs=[]))

        self.assertEqual(8, len(e))
        self.assertEqual(e[0].number, 21)
        self.assertEqual(e[7].number, 28)

    def test_build_midi_coords_from_list(self):
        groups = [
            build_control_group(midi_range='29, 10, 11, 12', number=1, layout='row'),
        ]

        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=4, encoder_refs=[]))

        self.assertEqual(4, len(e))
        self.assertEqual(e[0].number, 29)
        self.assertEqual(e[3].number, 12)


    def test_build_midi_coords_from_list_of_notes_fails_with_invalid_note(self):
        groups = [
            build_control_group(
                midi_range='ES2, C-1, CS1, D1',
                number=1,
                midi_type='note',
                layout='row'),
        ]

        with self.assertRaises(ValueError):
            ControllerV2.build_from(build_raw_controller_v2(groups))

    def test_build_midi_coords_from_list_of_notes(self):
        groups = [
            build_control_group(
                midi_range='C-2, C-1, CS1, D1',
                number=1,
                midi_type='note',
                layout='row'),
        ]

        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, col=1, row_range_end=4, encoder_refs=[]))

        self.assertEqual(4, len(e))
        self.assertEqual(e[0].number, 0)
        self.assertEqual(e[1].number, 12)
        self.assertEqual(e[2].number, 37)
        self.assertEqual(e[3].number, 38)
