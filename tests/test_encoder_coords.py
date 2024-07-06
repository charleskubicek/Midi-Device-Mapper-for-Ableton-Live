import unittest
from ableton_control_suface_as_code.core_model import parse_coords
from ableton_control_suface_as_code.encoder_coords import EncoderCoords, Toggle


class TestEncoderCoords(unittest.TestCase):

    def setUp(self):
        self.encoder_coords = EncoderCoords(row=1, col=1, row_range_end=2, encoder_refs=[])

    def test_initialization(self):
        self.assertEqual(self.encoder_coords.row, 1)
        self.assertEqual(self.encoder_coords.col, 1)
        self.assertEqual(self.encoder_coords.row_range_end, 2)

    def test_range_inclusive(self):
        self.assertEqual(list(self.encoder_coords.range_inclusive), [1, 2])

    def test_parse(self):
        input = "row_3:4"
        expected = EncoderCoords(row=3, col=4, row_range_end=4, encoder_refs=[])

        self.assertEqual(expected, parse_coords(input))

    def test_parse_range(self):
        input = "row_3:4-10"
        expected = EncoderCoords(row=3, col=4, row_range_end=10, encoder_refs=[])

        self.assertEqual(expected, parse_coords(input))

    def test_parse_tow_ranges(self):
        input = "row_3:5:6,row_4:5:6,"
        expected = EncoderCoords(row=3, col=4, row_range_end=10, encoder_refs=[])

        self.assertEqual(expected, parse_coords(input))

    def test_parse_toggle(self):
        input = "row_3:4 toggle"
        expected = EncoderCoords(row=3, col=4, row_range_end=4, encoder_refs=[Toggle.instance()])

        self.assertEqual(expected, parse_coords(input))
