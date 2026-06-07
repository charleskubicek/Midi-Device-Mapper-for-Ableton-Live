import unittest

from ableton_control_surface_as_code.hud_layout import (
    offset_layout,
    dial_count,
    button_count,
    grid_width,
    combine_layouts,
)


class TestLayoutMetrics(unittest.TestCase):
    def test_counts_and_width(self):
        cells = [
            (0, 0, 'dial', 8, 0),
            (1, 0, 'dial', 8, 8),
            (2, 0, 'button', 4, 0),
        ]
        self.assertEqual(dial_count(cells), 16)
        self.assertEqual(button_count(cells), 4)
        self.assertEqual(grid_width(cells), 1)   # max grid_col 0 → width 1

    def test_width_multi_column(self):
        cells = [(0, 0, 'dial', 1, 0), (0, 2, 'dial', 1, 1)]
        self.assertEqual(grid_width(cells), 3)   # cols 0..2 → width 3


class TestOffsetLayout(unittest.TestCase):
    def test_shifts_grid_col_and_start_per_kind(self):
        cells = [
            (0, 0, 'dial', 2, 0),
            (1, 0, 'button', 4, 0),
        ]
        out = offset_layout(cells, col_offset=3, dial_offset=16, button_offset=8)
        self.assertEqual(out, [
            (0, 3, 'dial', 2, 16),
            (1, 3, 'button', 4, 8),
        ])

    def test_does_not_mutate_input(self):
        cells = [(0, 0, 'dial', 2, 0)]
        offset_layout(cells, 1, 1, 1)
        self.assertEqual(cells, [(0, 0, 'dial', 2, 0)])


class TestCombineLayouts(unittest.TestCase):
    def test_secondary_offset_to_the_right_with_no_index_collisions(self):
        primary = [
            (0, 0, 'dial', 8, 0),
            (1, 0, 'dial', 8, 8),
            (2, 0, 'button', 4, 0),
        ]
        secondary = [
            (0, 0, 'button', 8, 0),
        ]
        combined, dial_off, btn_off = combine_layouts(primary, secondary, col_gap=1)

        # offsets reflect the primary's index spaces
        self.assertEqual(dial_off, 16)
        self.assertEqual(btn_off, 4)

        # primary cells unchanged, secondary appended + offset
        self.assertEqual(combined[:3], primary)
        # secondary button cell: grid_col = primary width (1) + gap (1) = 2,
        # start = primary button count (4)
        self.assertEqual(combined[3], (0, 2, 'button', 8, 4))

        # no two cells of the same kind share a wire range
        dial_starts = [c[4] for c in combined if c[2] == 'dial']
        button_starts = [c[4] for c in combined if c[2] == 'button']
        self.assertEqual(sorted(dial_starts), dial_starts)
        self.assertEqual(button_starts, [0, 4])


if __name__ == '__main__':
    unittest.main()
