import unittest

from ableton_control_surface_as_code.core_model import EncoderType
from ableton_control_surface_as_code.encoder_coords import EncoderCoords
from ableton_control_surface_as_code.gen_error import GenError, ProblemAccumulator
from ableton_control_surface_as_code.hud_layout import allocate_global_layout, find_wire_index
from ableton_control_surface_as_code.model_controller import ControllerV2, ControlGroupPartV2
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part, build_control_group


class TestBuildModeModelV2(unittest.TestCase):

    def test_hud_defaults_to_true(self):
        cg = ControlGroupPartV2(
            layout='row', number=1, type='knob',
            midi_channel=2, midi_type='CC', midi_range='21-28',
        )
        self.assertTrue(cg.hud)

    def test_hud_false_parsed(self):
        cg = ControlGroupPartV2(
            layout='row', number=4, type='button',
            midi_channel=3, midi_type='CC', midi_range='114,115',
            hud=False,
        )
        self.assertFalse(cg.hud)

    def test_hud_false_propagates_to_control_group(self):
        groups = [
            build_control_group(
                midi_range='21-28', number=1, layout='row'),
            ControlGroupPartV2(
                layout='row', number=4, type='button',
                midi_channel=3, midi_type='CC', midi_range='114,115',
                hud=False,
            ),
        ]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        group4 = next(g for g in controller.control_groups if g.number == 4)
        self.assertFalse(group4.hud)

    def test_hud_false_excluded_from_layout_allocation(self):
        groups = [
            build_control_group(
                midi_range='21-28', number=1, layout='row'),
            ControlGroupPartV2(
                layout='row', number=4, type='button',
                midi_channel=3, midi_type='CC', midi_range='114,115',
                hud=False,
            ),
        ]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        cells = allocate_global_layout(controller)
        kinds = {c[2] for c in cells}
        self.assertIn('dial', kinds)
        self.assertNotIn('button', kinds)
        self.assertEqual(1, len(cells))

    def test_find_wire_index_skips_hud_false(self):
        groups = [
            build_control_group(
                midi_range='21-28', number=1, layout='row'),
            ControlGroupPartV2(
                layout='row', number=4, type='button',
                midi_channel=3, midi_type='CC', midi_range='114,115',
                hud=False,
            ),
        ]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        cells = allocate_global_layout(controller)

        button_group = next(g for g in controller.control_groups if g.number == 4)
        button_coord = button_group.midi_coords[0]
        result = find_wire_index(controller, button_coord, cells)
        self.assertIsNone(result)

    def test_hud_false_group_still_resolves_midi_coords(self):
        groups = [
            build_control_group(
                midi_range='21-28', number=1, layout='row'),
            ControlGroupPartV2(
                layout='row', number=4, type='button',
                midi_channel=3, midi_type='CC', midi_range='114,115',
                hud=False,
            ),
        ]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=4, range_=(1, 2), encoder_refs=[]))
        self.assertEqual(2, len(e))
        self.assertEqual(e[0].number, 114)
        self.assertEqual(e[1].number, 115)
        self.assertEqual(tps, EncoderType.button)

    def _groups_with_dangling_under(self):
        return [
            build_control_group(midi_range='21-28', number=1),
            ControlGroupPartV2(
                layout='row', number=2, type='knob',
                midi_channel=2, midi_type='CC', midi_range='31-38',
                under=99,
            ),
        ]

    def test_unresolvable_under_reference_raises_readable_error(self):
        groups = self._groups_with_dangling_under()
        with self.assertRaises(GenError) as ctx:
            ControllerV2.build_from(build_raw_controller_v2(groups))
        msg = str(ctx.exception)
        self.assertIn('99', msg)   # the dangling reference
        self.assertIn('2', msg)    # the offending row number

    def test_unresolvable_reference_accumulates_when_acc_passed(self):
        acc = ProblemAccumulator()
        groups = self._groups_with_dangling_under()
        ControllerV2.build_from(build_raw_controller_v2(groups), acc=acc)
        self.assertTrue(any('99' in p for p in acc.problems),
                        f"expected dangling-ref problem, got {acc.problems}")

    def test_resolvable_grid_does_not_report_problems(self):
        acc = ProblemAccumulator()
        groups = [
            build_control_group(midi_range='21-28', number=1),
            ControlGroupPartV2(
                layout='row', number=2, type='knob',
                midi_channel=2, midi_type='CC', midi_range='31-38',
                under=1,
            ),
        ]
        ControllerV2.build_from(build_raw_controller_v2(groups), acc=acc)
        self.assertEqual([], acc.problems)

    def test_build_midi_coords(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, range_=(1, 1), encoder_refs=[]))

        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 21)

    def test_build_midi_coords_over_rws(self):
        groups = [
            build_control_group_part(midi_range='21-24', number=1, layout='row-part', row_parts='1-4'),
            build_control_group_part(midi_range='25-28', number=1, layout='row-part', row_parts='5-8')
        ]

        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, range_=(1, 8), encoder_refs=[]))

        self.assertEqual(8, len(e))
        self.assertEqual(e[0].number, 21)
        self.assertEqual(e[7].number, 28)

    def test_build_midi_coords_from_list(self):
        groups = [
            build_control_group(midi_range='29, 10, 11, 12', number=1, layout='row'),
        ]

        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, range_=(1, 4), encoder_refs=[]))

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
        e, tps = controller.build_midi_coords(EncoderCoords(row=1, range_=(1, 4), encoder_refs=[]))

        self.assertEqual(4, len(e))
        self.assertEqual(e[0].number, 0)
        self.assertEqual(e[1].number, 12)
        self.assertEqual(e[2].number, 37)
        self.assertEqual(e[3].number, 38)
