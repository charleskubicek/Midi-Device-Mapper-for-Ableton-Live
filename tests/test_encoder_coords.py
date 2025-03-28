import unittest
from ableton_control_surface_as_code.core_model import parse_coords, parse_multiple_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords, Toggle


class TestEncoderCoords(unittest.TestCase):

    def setUp(self):
        self.encoder_coords = EncoderCoords(row=1, range_=(1, 2), encoder_refs=[])

    def test_range_inclusive(self):
        self.assertEqual(list(self.encoder_coords.range_inclusive), [1, 2])

    def test_parse(self):
        input = "row-3:4"
        expected = EncoderCoords(row=3, range_=(4, 4), encoder_refs=[])

        self.assertEqual(expected, parse_coords(input))

    def test_parse_range(self):
        input = "row-3:4-10"
        expected = EncoderCoords(row=3, range_=(4, 10), encoder_refs=[])

        self.assertEqual(expected, parse_coords(input))

    def test_parse_tow_ranges(self):
        input = "row-2:5-6,row-3:5-6"
        expected = [
            EncoderCoords(row=2, range_=(5, 6), encoder_refs=[]),
            EncoderCoords(row=3, range_=(5, 6), encoder_refs=[])]

        result = parse_multiple_coords(input)

        self.assertEqual(expected, result)

    def test_parse_toggle(self):
        input = "row-3:4 toggle"
        expected = EncoderCoords(row=3, range_=(4, 4), encoder_refs=[Toggle.instance()])

        self.assertEqual(expected, parse_coords(input))
