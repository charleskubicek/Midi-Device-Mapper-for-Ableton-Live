import unittest
from unittest.mock import Mock

from source_modules.ec4_client import Ec4Client, NullEc4Client, translate_string
from source_modules.hud_protocol import SlotPayload, EMPTY_SLOT


def _payload(name):
    return SlotPayload(name, 0.5, 0.0, 1.0)


def _data_triples(text):
    """Encode a string the way the EC4 expects each char: 4D 2<hi> 1<lo>."""
    out = []
    for ch in translate_string(text):
        v = ord(ch)
        out += [0x4D, 0x20 | (v >> 4), 0x10 | (v & 0x0F)]
    return out


class TestEc4ClientMessage(unittest.TestCase):
    def setUp(self):
        self.manager = Mock()
        self.client = Ec4Client(self.manager)

    def _sent(self):
        self.manager._send_midi.assert_called_once()
        return list(self.manager._send_midi.call_args[0][0])

    def test_header_and_address_and_length(self):
        # A single dial in cell 0 still produces one full 64-cell message.
        self.client.on_device_burst("Dev", [(0, _payload("Vol"))], [])
        msg = self._sent()
        # header: F0 00 00 00 | device-id 4E 2C 1B | type 4E 22 10 | addr0 4A 20 10
        self.assertEqual(msg[:13],
                         [0xF0, 0, 0, 0, 0x4E, 0x2C, 0x1B, 0x4E, 0x22, 0x10, 0x4A, 0x20, 0x10])
        self.assertEqual(msg[-1], 0xF7)
        # 13 header + 64*3 data + 1 end
        self.assertEqual(len(msg), 13 + 64 * 3 + 1)

    def test_reso_in_control_16_matches_manual(self):
        # Manual worked example: 'Reso' written to control 16 (cell index 15,
        # char offset 60). R=0x52 e=0x65 s=0x73 o=0x6F.
        self.client.on_device_burst("Dev", [(15, _payload("Reso"))], [])
        msg = self._sent()
        data = msg[13:-1]  # strip header + F7
        cell15 = data[15 * 4 * 3: 16 * 4 * 3]
        self.assertEqual(cell15, [
            0x4D, 0x25, 0x12,  # 'R'
            0x4D, 0x26, 0x15,  # 'e'
            0x4D, 0x27, 0x13,  # 's'
            0x4D, 0x26, 0x1F,  # 'o'
        ])

    def test_unset_cells_are_dashes(self):
        self.client.on_device_burst("Dev", [(0, _payload("Vol"))], [])
        msg = self._sent()
        data = msg[13:-1]
        cell5 = data[5 * 4 * 3: 6 * 4 * 3]
        self.assertEqual(cell5, _data_triples("----"))

    def test_empty_slot_payload_renders_dashes(self):
        self.client.on_device_burst("Dev", [(2, EMPTY_SLOT)], [])
        msg = self._sent()
        data = msg[13:-1]
        cell2 = data[2 * 4 * 3: 3 * 4 * 3]
        self.assertEqual(cell2, _data_triples("----"))

    def test_label_truncated_to_four_chars(self):
        self.client.on_device_burst("Dev", [(0, _payload("Frequency"))], [])
        msg = self._sent()
        data = msg[13:-1]
        cell0 = data[0: 4 * 3]
        self.assertEqual(cell0, _data_triples("Freq"))

    def test_short_label_padded_with_dashes(self):
        self.client.on_device_burst("Dev", [(0, _payload("Q"))], [])
        msg = self._sent()
        data = msg[13:-1]
        cell0 = data[0: 4 * 3]
        self.assertEqual(cell0, _data_triples("Q---"))


class TestEc4ClientThroughRemote(unittest.TestCase):
    """Integration across the real seam: a real Ec4Client registered as a
    feedback sink on Remote must emit one SysEx message on a device burst. This
    is the only test that exercises the actual feature path end-to-end (Remote's
    try/except would otherwise swallow a real mismatch)."""

    def test_device_update_drives_real_ec4_client(self):
        from source_modules.helpers import Remote

        ec4_manager = Mock()
        remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=Mock(),
                        feedback_sinks=[Ec4Client(ec4_manager)])

        on_off = Mock(); on_off.param = Mock(); on_off.alias = None; on_off.button = None
        on_off.param.name = "On/Off"
        dial = Mock()
        dial.param = Mock(); dial.param.name = "Freq"
        dial.param.value, dial.param.min, dial.param.max = 0.5, 0.0, 1.0
        dial.alias = None; dial.button = None

        remote.device_update("EQ Eight", [on_off, dial],
                             hud_layout=[(0, 0, 'dial', 8, 0)])

        ec4_manager._send_midi.assert_called_once()
        msg = list(ec4_manager._send_midi.call_args[0][0])
        self.assertEqual(msg[:7], [0xF0, 0x00, 0x00, 0x00, 0x4E, 0x2C, 0x1B])
        self.assertEqual(msg[-1], 0xF7)
        # cell 0 ("Freq") should be present at char offset 0
        self.assertEqual(msg[13:13 + 12], _data_triples("Freq"))


class TestNullEc4Client(unittest.TestCase):
    def test_null_client_sends_nothing(self):
        manager = Mock()
        client = NullEc4Client()
        # Should accept the same calls and do nothing (no manager involved).
        client.on_device_burst("Dev", [(0, _payload("Vol"))], [])
        client.on_hide()
        manager._send_midi.assert_not_called()


if __name__ == "__main__":
    unittest.main()
