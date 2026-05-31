import unittest

from source_modules.hud_protocol import (
    EMPTY_SLOT,
    SlotPayload,
    LayoutMsg,
    DeviceMsg,
    SlotMsg,
    UpdateMsg,
    CommitMsg,
    PingMsg,
    HideMsg,
    PageMsg,
    UnknownMsg,
    encode_layout,
    encode_device,
    encode_slot,
    encode_slot_payload,
    encode_update,
    encode_commit,
    encode_ping,
    encode_hide,
    encode_page_info,
    parse,
    parse_all,
)


class TestEncodeBytes(unittest.TestCase):
    """Pin exact wire format. Any change here is a wire-protocol change and
    requires a parallel update in the Swift parser."""

    def test_layout(self):
        cells = [(0, 0, 'dial', 8, 0), (2, 0, 'button', 4, 0)]
        self.assertEqual(encode_layout(cells), "LAYOUT|2|0|0|dial|8|0|2|0|button|4|0")

    def test_layout_empty(self):
        self.assertEqual(encode_layout([]), "LAYOUT|0")

    def test_device(self):
        self.assertEqual(encode_device("EQ Eight"), "DEVICE|EQ Eight")

    def test_slot_dial(self):
        self.assertEqual(
            encode_slot('dial', 0, "Frequency", 440.0, 20.0, 20000.0),
            "SLOT|dial|0|Frequency|440.0|20.0|20000.0",
        )

    def test_slot_empty_sentinel(self):
        # The sentinel format is the contract that distinguishes "empty slot"
        # from a real mapping. Every receiver depends on this exact shape.
        self.assertEqual(
            encode_slot_payload('button', 1, EMPTY_SLOT),
            "SLOT|button|1||0|0|1",
        )

    def test_update(self):
        self.assertEqual(
            encode_update('dial', 2, "Resonance", 0.81, 0.0, 1.0),
            "UPDATE|dial|2|Resonance|0.81|0.0|1.0",
        )

    def test_commit(self):
        self.assertEqual(encode_commit(12), "COMMIT|12")

    def test_ping(self):
        self.assertEqual(encode_ping(), "PING")

    def test_hide(self):
        self.assertEqual(encode_hide(), "HIDE")

    def test_page_info(self):
        self.assertEqual(encode_page_info(1, 3, 1, 2), "PAGE|1|3|1|2")

    def test_page_info_single_page(self):
        self.assertEqual(encode_page_info(1, 1, 1, 1), "PAGE|1|1|1|1")

    def test_page_info(self):
        self.assertEqual(encode_page_info(1, 3, 1, 2), "PAGE|1|3|1|2")

    def test_page_info_single_page(self):
        self.assertEqual(encode_page_info(1, 1, 1, 1), "PAGE|1|1|1|1")


class TestParseRoundtrip(unittest.TestCase):
    def test_layout_roundtrip(self):
        cells = [(0, 0, 'dial', 8, 0), (2, 0, 'button', 4, 0)]
        msg = parse(encode_layout(cells))
        self.assertEqual(msg, LayoutMsg(cells))

    def test_device_roundtrip(self):
        self.assertEqual(parse(encode_device("EQ Eight")), DeviceMsg("EQ Eight"))

    def test_slot_roundtrip(self):
        line = encode_slot('dial', 3, "Q", 0.5, 0.0, 1.0)
        self.assertEqual(parse(line), SlotMsg('dial', 3, SlotPayload("Q", 0.5, 0.0, 1.0)))

    def test_empty_sentinel_roundtrip(self):
        line = encode_slot_payload('button', 0, EMPTY_SLOT)
        self.assertEqual(parse(line), SlotMsg('button', 0, EMPTY_SLOT))

    def test_update_roundtrip(self):
        line = encode_update('dial', 2, "R", 0.7, 0.0, 1.0)
        self.assertEqual(parse(line), UpdateMsg('dial', 2, SlotPayload("R", 0.7, 0.0, 1.0)))

    def test_commit_roundtrip(self):
        self.assertEqual(parse(encode_commit(7)), CommitMsg(7))

    def test_ping_roundtrip(self):
        self.assertEqual(parse(encode_ping()), PingMsg())

    def test_hide_roundtrip(self):
        self.assertEqual(parse(encode_hide()), HideMsg())

    def test_page_info_roundtrip(self):
        line = encode_page_info(2, 4, 1, 2)
        self.assertEqual(parse(line), PageMsg(2, 4, 1, 2))

    def test_page_info_roundtrip(self):
        line = encode_page_info(2, 4, 1, 2)
        self.assertEqual(parse(line), PageMsg(2, 4, 1, 2))


class TestParseAll(unittest.TestCase):
    def test_full_burst_concatenated(self):
        burst = "\n".join([
            encode_device("Amp"),
            encode_page_info(1, 3, 1, 2),
            encode_slot('dial', 0, "Bass", 0.5, 0.0, 1.0),
            encode_slot_payload('dial', 1, EMPTY_SLOT),
            encode_slot('button', 0, "Type", 1, 0, 2),
            encode_commit(3),
        ]) + "\n"
        msgs = parse_all(burst)
        self.assertEqual(len(msgs), 6)
        self.assertIsInstance(msgs[0], DeviceMsg)
        self.assertIsInstance(msgs[1], PageMsg)
        self.assertIsInstance(msgs[-1], CommitMsg)

    def test_blank_lines_skipped(self):
        msgs = parse_all("\n\n" + encode_ping() + "\n\n")
        self.assertEqual(msgs, [PingMsg()])


class TestMalformed(unittest.TestCase):
    def test_unknown_verb(self):
        self.assertEqual(parse("WHAT|1|2"), UnknownMsg("WHAT|1|2"))

    def test_hide_with_trailing_field_is_unknown(self):
        self.assertEqual(parse("HIDE|x"), UnknownMsg("HIDE|x"))

    def test_layout_field_count_mismatch(self):
        # claims 2 cells but only 1 cell of fields follows
        self.assertIsInstance(parse("LAYOUT|2|0|0|dial|8|0"), UnknownMsg)

    def test_layout_bad_int(self):
        self.assertIsInstance(parse("LAYOUT|1|x|0|dial|8|0"), UnknownMsg)

    def test_slot_bad_float(self):
        self.assertIsInstance(parse("SLOT|dial|0|n|notafloat|0|1"), UnknownMsg)

    def test_slot_unknown_kind(self):
        self.assertIsInstance(parse("SLOT|knob|0|n|0|0|1"), UnknownMsg)

    def test_slot_wrong_field_count(self):
        self.assertIsInstance(parse("SLOT|dial|0|n|0|0"), UnknownMsg)

    def test_commit_bad_int(self):
        self.assertIsInstance(parse("COMMIT|abc"), UnknownMsg)

    def test_page_info_bad_int(self):
        self.assertIsInstance(parse("PAGE|x|3|1|2"), UnknownMsg)

    def test_page_info_wrong_field_count(self):
        self.assertIsInstance(parse("PAGE|1|3|1"), UnknownMsg)

    def test_page_info_bad_int(self):
        self.assertIsInstance(parse("PAGE|x|3|1|2"), UnknownMsg)

    def test_page_info_wrong_field_count(self):
        self.assertIsInstance(parse("PAGE|1|3|1"), UnknownMsg)


if __name__ == '__main__':
    unittest.main()
