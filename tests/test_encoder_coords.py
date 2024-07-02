import unittest
from ableton_control_suface_as_code.core_model import EncoderCoords

class TestEncoderCoords(unittest.TestCase):

    def setUp(self):
        self.encoder_coords = EncoderCoords(row=1, col=1, row_range_end=2, encoder_refs=[])

    def test_initialization(self):
        self.assertEqual(self.encoder_coords.row, 1)
        self.assertEqual(self.encoder_coords.col, 1)
        self.assertEqual(self.encoder_coords.row_range_end, 2)


    def test_range_inclusive(self):
        self.assertEqual(list(self.encoder_coords.range_inclusive), [1, 2])

