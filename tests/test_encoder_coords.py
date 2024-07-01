import unittest
from ableton_control_suface_as_code.core_model import EncoderCoords

class TestEncoderCoords(unittest.TestCase):

    def setUp(self):
        self.encoder_coords = EncoderCoords(row=1, col=1, row_range_end=2)

    def test_initialization(self):
        self.assertEqual(self.encoder_coords.row, 1)
        self.assertEqual(self.encoder_coords.col, 1)
        self.assertEqual(self.encoder_coords.row_range_end, 2)

    def test_is_range(self):
        self.assertTrue(self.encoder_coords.is_range)

    def test_range_inclusive(self):
        self.assertEqual(list(self.encoder_coords.range_inclusive), [1, 2])

    def test_list_inclusive(self):
        self.assertEqual(self.encoder_coords.list_inclusive(), [1, 2])

    def test_debug_string(self):
        self.assertEqual(self.encoder_coords.debug_string(), "r1c1")
