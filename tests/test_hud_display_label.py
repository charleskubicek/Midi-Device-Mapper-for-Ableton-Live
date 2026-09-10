"""Presentation rule for HUD slot labels (hud-quick-fixes-plan §2).

Every label the HUD renders is capitalised on the wire, whatever case the source
data used. The rule lives in ONE place — `hud_protocol.display_label`, applied by
`encode_slot`/`encode_update` — so static mode labels and live Live-parameter
names go through the same transform.
"""
import unittest

from source_modules.hud_protocol import (
    EMPTY_SLOT,
    display_label,
    encode_slot,
    encode_slot_payload,
    encode_update,
)


class TestDisplayLabel(unittest.TestCase):
    def test_lowercase_words_are_capitalised(self):
        self.assertEqual(display_label("track left"), "Track Left")

    def test_slash_separated_words_each_capitalise(self):
        self.assertEqual(display_label("dev on/off"), "Dev On/Off")

    def test_underscores_become_spaces(self):
        # Function labels default to the raw identifier; showing the user
        # `move_loop_left` is the same defect as showing them `hud_toggle`.
        self.assertEqual(display_label("move_loop_left"), "Move Loop Left")

    def test_hyphen_separated_words_keep_the_hyphen(self):
        self.assertEqual(display_label("first-last"), "First-Last")

    def test_digits_survive(self):
        self.assertEqual(display_label("send 1"), "Send 1")
        self.assertEqual(display_label("page dec"), "Page Dec")

    def test_existing_capitals_are_left_alone(self):
        # THE reason this is a Python rule and not Swift `.capitalized`: live
        # Live parameter names are already cased, and `.capitalized`/`.title()`
        # would destroy every one of these.
        for name in ["LFO Rate", "dB", "EQ8", "Osc 1 Wave", "MacBook"]:
            self.assertEqual(display_label(name), name)

    def test_mixed_case_only_lifts_the_all_lowercase_runs(self):
        self.assertEqual(display_label("LFO shape"), "LFO Shape")

    def test_empty_stays_empty(self):
        # The empty-slot sentinel must survive untouched.
        self.assertEqual(display_label(""), "")

    def test_non_string_passes_through(self):
        self.assertIsNone(display_label(None))


class TestEncodersApplyIt(unittest.TestCase):
    def test_encode_slot_capitalises_the_name(self):
        self.assertEqual(
            encode_slot('button', 2, "dev on/off", 1.0, 0.0, 1.0),
            "SLOT|button|2|Dev On/Off|1.0|0.0|1.0",
        )

    def test_encode_update_capitalises_the_name(self):
        self.assertEqual(
            encode_update('dial', 2, "filter freq", 0.81, 0.0, 1.0),
            "UPDATE|dial|2|Filter Freq|0.81|0.0|1.0",
        )

    def test_empty_slot_sentinel_is_unchanged(self):
        self.assertEqual(
            encode_slot_payload('button', 1, EMPTY_SLOT),
            "SLOT|button|1||0|0|1",
        )
