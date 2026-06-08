import unittest

from ableton_control_surface_as_code.core_model import EncoderType
from ableton_control_surface_as_code.hud_layout import (
    offset_layout,
    dial_count,
    button_count,
    combine_layouts,
)


class TestLayoutMetrics(unittest.TestCase):
    def test_counts(self):
        cells = [
            (0, 0, 'dial', 8, 0, 0),
            (1, 0, 'dial', 8, 8, 0),
            (2, 0, 'button', 4, 0, 0),
        ]
        self.assertEqual(dial_count(cells), 16)
        self.assertEqual(button_count(cells), 4)


class TestOffsetLayout(unittest.TestCase):
    def test_bumps_start_per_kind_and_tags_section_keeping_grid(self):
        # offset_layout no longer shifts grid_col: the secondary is rendered as
        # an independent block (its own grid), placed by the HUD via `section`.
        # It only bumps the wire start per kind (shared slot arrays) and tags
        # the section.
        cells = [
            (0, 0, 'dial', 2, 0, 0),
            (1, 0, 'button', 4, 0, 0),
        ]
        out = offset_layout(cells, dial_offset=16, button_offset=8, section=1)
        self.assertEqual(out, [
            (0, 0, 'dial', 2, 16, 1),
            (1, 0, 'button', 4, 8, 1),
        ])

    def test_does_not_mutate_input(self):
        cells = [(0, 0, 'dial', 2, 0, 0)]
        offset_layout(cells, dial_offset=1, button_offset=1, section=1)
        self.assertEqual(cells, [(0, 0, 'dial', 2, 0, 0)])


class TestCombineLayouts(unittest.TestCase):
    def test_secondary_is_independent_section_with_no_index_collisions(self):
        primary = [
            (0, 0, 'dial', 8, 0, 0),
            (1, 0, 'dial', 8, 8, 0),
            (2, 0, 'button', 4, 0, 0),
        ]
        secondary = [
            (0, 0, 'button', 8, 0, 0),
        ]
        combined, dial_off, btn_off = combine_layouts(primary, secondary)

        # offsets reflect the primary's index spaces (unchanged — RegionState
        # remap path relies on these)
        self.assertEqual(dial_off, 16)
        self.assertEqual(btn_off, 4)

        # primary cells unchanged (section 0)
        self.assertEqual(combined[:3], primary)
        # secondary keeps its OWN grid (grid_col 0) — placement is the HUD's job
        # via section — but its wire start is bumped (primary button count 4) and
        # it is tagged section 1.
        self.assertEqual(combined[3], (0, 0, 'button', 8, 4, 1))

        # no two cells of the same kind share a wire range
        dial_starts = [c[4] for c in combined if c[2] == 'dial']
        button_starts = [c[4] for c in combined if c[2] == 'button']
        self.assertEqual(sorted(dial_starts), dial_starts)
        self.assertEqual(button_starts, [0, 4])

    def test_allocate_tags_section_zero(self):
        from ableton_control_surface_as_code.hud_layout import allocate_global_layout

        class _G:
            def __init__(self, gr, gc, type_, n):
                self.grid_row = gr
                self.grid_col = gc
                self.type = type_
                self.midi_coords = [None] * n

        class _C:
            control_groups = [_G(0, 0, EncoderType.knob, 4)]

        cells = allocate_global_layout(_C())
        self.assertEqual(cells, [(0, 0, 'dial', 4, 0, 0)])


if __name__ == '__main__':
    unittest.main()
