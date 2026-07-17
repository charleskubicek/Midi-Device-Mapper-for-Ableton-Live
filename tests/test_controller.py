import unittest

from ableton_control_surface_as_code.core_model import EncoderType
from ableton_control_surface_as_code.encoder_coords import EncoderCoords
from ableton_control_surface_as_code.gen_error import GenError, ProblemAccumulator
from ableton_control_surface_as_code.hud_layout import allocate_global_layout, find_wire_index
from ableton_control_surface_as_code.model_controller import ControllerV2, ControlGroupPartV2, \
    ControllerRawV2, Divider, validate_controller_semantics
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

    def _ec4_style_controller(self):
        """Knobs on rows 1-4 (grid col 0), buttons on rows 5-8 (grid col 1),
        mirroring the ec4 layout: row 5 sits right_of row 1, then each lower
        button row sits under the one above."""
        groups = [
            ControlGroupPartV2(layout='row', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-3'),
            ControlGroupPartV2(layout='row', number=2, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='4-7', under=1),
            ControlGroupPartV2(layout='row', number=3, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='8-11', under=2),
            ControlGroupPartV2(layout='row', number=4, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='12-15', under=3),
            ControlGroupPartV2(layout='row', number=5, type='button',
                               midi_channel=1, midi_type='CC', midi_range='40-43', right_of=1),
            ControlGroupPartV2(layout='row', number=6, type='button',
                               midi_channel=1, midi_type='CC', midi_range='44-47', under=5),
            ControlGroupPartV2(layout='row', number=7, type='button',
                               midi_channel=1, midi_type='CC', midi_range='48-51', under=6),
            ControlGroupPartV2(layout='row', number=8, type='button',
                               midi_channel=1, midi_type='CC', midi_range='52-55', under=7),
        ]
        return ControllerV2.build_from(build_raw_controller_v2(groups))

    def test_grid_1_first_is_first_knob(self):
        controller = self._ec4_style_controller()
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=1, range_=(1, 1), axis_kind="grid", encoder_refs=[]))

        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 0)
        self.assertEqual(tps, EncoderType.knob)

    def test_grid_1_spans_all_knobs_in_layout_order(self):
        controller = self._ec4_style_controller()
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=1, range_=(1, 16), axis_kind="grid", encoder_refs=[]))

        self.assertEqual(16, len(e))
        self.assertEqual([c.number for c in e], list(range(0, 16)))

    def test_grid_2_spans_buttons_top_to_bottom_left_to_right(self):
        controller = self._ec4_style_controller()
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=2, range_=(1, 15), axis_kind="grid", encoder_refs=[]))

        self.assertEqual(15, len(e))
        # first == row-5 col-1
        self.assertEqual(e[0].number, 40)
        self.assertEqual(e[14].number, 54)
        self.assertEqual(tps, EncoderType.button)

    def _multi_block_grid_controller(self):
        """Four physical 4x4 `layout: grid` blocks in a right_of chain, mirroring
        controller_grid.nt: block1 buttons, block2 knobs, block3 knobs, block4
        buttons. Unlike the ec4 (rows merged by type), each grid block is its own
        grid-N."""
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='button',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='48-63',
                               rows=4, columns=4, right_of=1),
            ControlGroupPartV2(layout='grid', number=3, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='32-47',
                               rows=4, columns=4, right_of=2),
            ControlGroupPartV2(layout='grid', number=4, type='button',
                               midi_channel=1, midi_type='CC', midi_range='64-79',
                               rows=4, columns=4, right_of=3),
        ]
        return ControllerV2.build_from(build_raw_controller_v2(groups))

    def test_each_grid_block_is_its_own_grid(self):
        # grid-3 must resolve to physical block 3 (knobs, CC 32-47), not a
        # type-merged bucket. There are 4 grids, one per block.
        controller = self._multi_block_grid_controller()
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=3, range_=(1, 16), axis_kind="grid", encoder_refs=[]))
        self.assertEqual(16, len(e))
        self.assertEqual([c.number for c in e], list(range(32, 48)))
        self.assertEqual(tps, EncoderType.knob)

    def test_grid_4_is_fourth_block_not_out_of_range(self):
        controller = self._multi_block_grid_controller()
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=4, range_=(1, 1), axis_kind="grid", encoder_refs=[]))
        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 64)
        self.assertEqual(tps, EncoderType.button)

    def test_grid_block_2d_indexing_stays_within_block(self):
        # grid-4:4::1 = block 4, row 4, col 1 -> idx 12 within the block.
        controller = self._multi_block_grid_controller()
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=4, grid_row=4, range_=(1, 1), axis_kind="grid",
                          encoder_refs=[]))
        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 64 + 12)

    def test_multi_block_grid_out_of_range_reports_four_grids(self):
        controller = self._multi_block_grid_controller()
        with self.assertRaises(GenError) as ctx:
            controller.build_midi_coords(
                EncoderCoords(row=5, range_=(1, 1), axis_kind="grid", encoder_refs=[]))
        msg = str(ctx.exception)
        self.assertIn('grid', msg)
        self.assertIn('4', msg)  # how many grids exist

    def test_grid_number_out_of_range_raises_readable_error(self):
        controller = self._ec4_style_controller()
        with self.assertRaises(GenError) as ctx:
            controller.build_midi_coords(
                EncoderCoords(row=3, range_=(1, 1), axis_kind="grid", encoder_refs=[]))
        msg = str(ctx.exception)
        self.assertIn('grid', msg)
        self.assertIn('2', msg)  # how many grids exist

    def test_grid_index_out_of_range_raises_readable_error(self):
        controller = self._ec4_style_controller()
        with self.assertRaises(GenError) as ctx:
            controller.build_midi_coords(
                EncoderCoords(row=2, range_=(1, 17), axis_kind="grid", encoder_refs=[]))
        msg = str(ctx.exception)
        self.assertIn('16', msg)  # grid size

    def test_grid_layout_allocates_one_hud_cell_per_grid_row(self):
        # A 4x4 knob grid should render as 4 rows of 4 in the HUD, not one
        # strip of 16. allocate_global_layout emits one cell per grid row.
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=4),
        ]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        cells = allocate_global_layout(controller)
        dial_cells = [c for c in cells if c.kind == 'dial']
        self.assertEqual(len(dial_cells), 4)
        # each row: count 4, stacked grid rows 0..3, wire starts 0,4,8,12
        self.assertEqual([c.count for c in dial_cells], [4, 4, 4, 4])
        self.assertEqual([c.grid_row for c in dial_cells], [0, 1, 2, 3])
        self.assertEqual([c.grid_col for c in dial_cells], [0, 0, 0, 0])
        self.assertEqual([c.start for c in dial_cells], [0, 4, 8, 12])

    def test_non_grid_group_still_one_cell(self):
        # Back-compat: a plain row of 8 knobs stays a single HUD cell.
        groups = [build_control_group(midi_range='21-28', number=1, layout='row')]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups))
        cells = allocate_global_layout(controller)
        self.assertEqual(len([c for c in cells if c.kind == 'dial']), 1)

    def test_note_range_expands_to_increasing_chromatic_run(self):
        cg = ControlGroupPartV2(
            layout='row', number=1, type='button',
            midi_channel=1, midi_type='note', midi_range='C2-DS4',
        )
        nums = cg._midi_list
        self.assertEqual(len(nums), 28)
        self.assertEqual(nums[0], 48)   # C2
        self.assertEqual(nums[-1], 75)  # DS4
        self.assertEqual(nums, list(range(48, 76)))

    def test_note_range_with_negative_octave_start(self):
        cg = ControlGroupPartV2(
            layout='row', number=1, type='button',
            midi_channel=1, midi_type='note', midi_range='C-2-DS-2',
        )
        # C-2 == 0, DS-2 == 3
        self.assertEqual(cg._midi_list, [0, 1, 2, 3])

    def _grid_controller(self):
        """A 4x4 knob grid (grid-1) and a 4x4 button grid (grid-2)."""
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type='button',
                               midi_channel=1, midi_type='note', midi_range='C2-DS3',
                               rows=4, columns=4, right_of=1),
        ]
        return ControllerV2.build_from(build_raw_controller_v2(groups))

    def test_grid_2d_single_cell(self):
        controller = self._grid_controller()
        # grid-1 row 2 col 3 -> flat index (2-1)*4 + (3-1) = 6 -> CC 6
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=1, grid_row=2, range_=(3, 3), axis_kind="grid", encoder_refs=[]))
        self.assertEqual(1, len(e))
        self.assertEqual(e[0].number, 6)

    def test_grid_2d_row_range(self):
        controller = self._grid_controller()
        # grid-1 row 1, cols 1-4 -> CC 0,1,2,3
        e, tps = controller.build_midi_coords(
            EncoderCoords(row=1, grid_row=1, range_=(1, 4), axis_kind="grid", encoder_refs=[]))
        self.assertEqual([c.number for c in e], [0, 1, 2, 3])

    def test_grid_2d_matches_flat_indexing(self):
        controller = self._grid_controller()
        # row 3 col 2 (2D) == flat index (3-1)*4 + 2 = 10
        e_2d, _ = controller.build_midi_coords(
            EncoderCoords(row=1, grid_row=3, range_=(2, 2), axis_kind="grid", encoder_refs=[]))
        e_flat, _ = controller.build_midi_coords(
            EncoderCoords(row=1, range_=(10, 10), axis_kind="grid", encoder_refs=[]))
        self.assertEqual(e_2d[0].number, e_flat[0].number)

    def test_grid_2d_row_out_of_range_raises(self):
        controller = self._grid_controller()
        with self.assertRaises(GenError):
            controller.build_midi_coords(
                EncoderCoords(row=1, grid_row=5, range_=(1, 1), axis_kind="grid", encoder_refs=[]))

    def test_grid_2d_col_out_of_range_raises(self):
        controller = self._grid_controller()
        with self.assertRaises(GenError):
            controller.build_midi_coords(
                EncoderCoords(row=1, grid_row=1, range_=(1, 5), axis_kind="grid", encoder_refs=[]))

    def test_grid_layout_requires_rows_and_columns(self):
        with self.assertRaises(ValueError):
            ControlGroupPartV2(layout='grid', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-15')

    def test_grid_rows_times_columns_must_match_count(self):
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=3),  # 12 != 16
        ]
        with self.assertRaises(GenError):
            validate_controller_semantics(build_raw_controller_v2(groups))

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


class TestDividers(unittest.TestCase):
    """Cosmetic HUD dividers (hud_dividers plan): `dividers` resolves grid-N
    pairs to HUD grid_col boundaries."""

    def _four_block_grid(self, dividers):
        """controller_grid.nt shape: four 4x4 blocks in a right_of chain, so
        grid-1..grid-4 sit at grid_col 0..3."""
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='button',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='16-31',
                               rows=4, columns=4, right_of=1),
            ControlGroupPartV2(layout='grid', number=3, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='32-47',
                               rows=4, columns=4, right_of=2),
            ControlGroupPartV2(layout='grid', number=4, type='button',
                               midi_channel=1, midi_type='CC', midi_range='64-79',
                               rows=4, columns=4, right_of=3),
        ]
        raw = ControllerRawV2(light_colors={}, control_groups=groups,
                              dividers=dividers)
        return ControllerV2.build_from(raw)

    def test_no_dividers_is_empty(self):
        controller = self._four_block_grid([])
        self.assertEqual(controller.divider_columns(), [])

    def test_adjacent_dividers_resolve_to_boundary_columns(self):
        # grid-1|grid-2 boundary is before col 1; grid-2|grid-3 before col 2.
        controller = self._four_block_grid([
            Divider(a='grid-1', b='grid-2'),
            Divider(a='grid-2', b='grid-3'),
        ])
        self.assertEqual(controller.divider_columns(), [1, 2])

    def test_boundary_is_deduped_and_sorted(self):
        controller = self._four_block_grid([
            Divider(a='grid-3', b='grid-4'),
            Divider(a='grid-1', b='grid-2'),
            Divider(a='grid-2', b='grid-1'),  # same boundary as 1|2, reversed
        ])
        self.assertEqual(controller.divider_columns(), [1, 3])

    def test_out_of_range_grid_ref_raises(self):
        controller = self._four_block_grid([Divider(a='grid-1', b='grid-9')])
        with self.assertRaises(GenError) as ctx:
            controller.divider_columns()
        self.assertIn('grid-9', str(ctx.exception))

    def test_malformed_grid_ref_raises(self):
        controller = self._four_block_grid([Divider(a='grid-1', b='row-2')])
        with self.assertRaises(GenError) as ctx:
            controller.divider_columns()
        self.assertIn('row-2', str(ctx.exception))

    def test_same_column_stacked_grids_raises(self):
        # Two 4x4 knob blocks stacked vertically (under), same grid_col -> a
        # horizontal (row) boundary, which the vertical-only MVP rejects.
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='16-31',
                               rows=4, columns=4, under=1),
        ]
        raw = ControllerRawV2(light_colors={}, control_groups=groups,
                              dividers=[Divider(a='grid-1', b='grid-2')])
        controller = ControllerV2.build_from(raw)
        with self.assertRaises(GenError) as ctx:
            controller.divider_columns()
        self.assertIn('column', str(ctx.exception).lower())


class TestDividerAdjacency(unittest.TestCase):
    def test_non_adjacent_grids_raise(self):
        groups = [
            ControlGroupPartV2(layout='grid', number=1, type='button',
                               midi_channel=1, midi_type='CC', midi_range='0-15',
                               rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='16-31',
                               rows=4, columns=4, right_of=1),
            ControlGroupPartV2(layout='grid', number=3, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='32-47',
                               rows=4, columns=4, right_of=2),
        ]
        raw = ControllerRawV2(light_colors={}, control_groups=groups,
                              dividers=[Divider(a='grid-1', b='grid-3')])
        controller = ControllerV2.build_from(raw)
        with self.assertRaises(GenError) as ctx:
            controller.divider_columns()
        self.assertIn('adjacent', str(ctx.exception).lower())
