import unittest
from ableton_control_surface_as_code.core_model import parse_coords, parse_multiple_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords, Toggle, Momentary, EncoderRefinements
from ableton_control_surface_as_code.gen_error import ErrorCode
from tests.custom_assertions import CustomAssertions


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

    def test_parse_momentary(self):
        input = "row-3:4 momentary"
        expected = EncoderCoords(row=3, range_=(4, 4), encoder_refs=[Momentary.instance()])

        self.assertEqual(expected, parse_coords(input))

    def test_has_momentary_true_has_toggle_false(self):
        coords = parse_coords("row-3:4 momentary")
        refs = EncoderRefinements(coords.encoder_refs)
        self.assertTrue(refs.has_momentary())
        self.assertFalse(refs.has_toggle())

    def test_has_toggle_true_has_momentary_false(self):
        coords = parse_coords("row-3:4 toggle")
        refs = EncoderRefinements(coords.encoder_refs)
        self.assertTrue(refs.has_toggle())
        self.assertFalse(refs.has_momentary())


class TestEncoderCoordErrors(unittest.TestCase, CustomAssertions):
    """Bad coordinate strings must raise a readable GenError, not a raw Lark dump."""

    def _assert_coord_syntax_error(self, raw, *fragments):
        self.assert_gen_error(
            lambda: parse_coords(raw), ErrorCode.COORD_SYNTAX, raw, *fragments)

    def test_A1_space_instead_of_dash(self):
        # 'row 1:1-8' — space where the axis separator '-' should be
        self._assert_coord_syntax_error("row 1:1-8", "row-")

    def test_A2_double_dot_range(self):
        self._assert_coord_syntax_error("row-1:1..8")

    def test_A3_capitalised_axis(self):
        self._assert_coord_syntax_error("Row-1:1-8")

    def test_A4_missing_range(self):
        self._assert_coord_syntax_error("row-1")

    def test_A5_empty_range(self):
        self._assert_coord_syntax_error("row-1:")

    def test_A7_misspelled_refinement(self):
        self._assert_coord_syntax_error("row-1:1-8 togle")

    def test_A11_empty_string(self):
        self._assert_coord_syntax_error("")

    def test_A12_negative_axis(self):
        self._assert_coord_syntax_error("row--1:1")

    def test_message_includes_an_example(self):
        # The whole point: the message teaches the correct syntax.
        e = self.assert_gen_error(
            lambda: parse_coords("row 1:1-8"), ErrorCode.COORD_SYNTAX)
        self.assertIn("toggle", str(e))  # lists valid refinements
        self.assertIn("row-1", str(e))   # shows a correct example

    def test_col_axis_still_parses(self):
        self.assertEqual(
            EncoderCoords(row=2, range_=(3, 3), encoder_refs=[]),
            parse_coords("col-2:3"))
