import unittest
from unittest.mock import Mock

from source_modules.grid_led_client import (
    GridLedClient, SYSEX_START, NON_COMMERCIAL_ID, LED_CMD, VERSION,
    SYSEX_END, NUM_DIALS, NUM_BUTTONS, NUM_SLOTS, MAPPED_FLOOR,
)
from source_modules.hud_protocol import BurstSnapshot, SlotPayload


def _snap(dials=(), buttons=(), zone_colors=(), suppress_hud=False):
    return BurstSnapshot(
        device_name="Dev",
        dials=tuple(dials),
        buttons=tuple(buttons),
        zone_colors=tuple(zone_colors),
        suppress_hud=suppress_hud,
    )


class TestGridLedFrame(unittest.TestCase):
    def setUp(self):
        self.manager = Mock()
        self.client = GridLedClient(self.manager)

    def _sent(self):
        self.manager._send_midi.assert_called_once()
        return list(self.manager._send_midi.call_args[0][0])

    def _body(self, msg):
        # strip 4-byte header + trailing F7
        return msg[4:-1]

    def _slot(self, body, slot):
        return body[slot * 3: slot * 3 + 3]

    def test_header_and_length(self):
        # An empty burst still emits one dense 48-slot frame of all-off.
        self.client.on_burst(_snap())
        msg = self._sent()
        self.assertEqual(msg[:4], [SYSEX_START, NON_COMMERCIAL_ID, LED_CMD, VERSION])
        self.assertEqual(msg[-1], SYSEX_END)
        # 4 header + 48*3 data + 1 end
        self.assertEqual(len(msg), 4 + NUM_SLOTS * 3 + 1)

    def test_no_hue_slot_is_off(self):
        # No zone colour (a non-zoned device, or a slot outside any zone) -> off,
        # regardless of value. NB a zoned synth's *unmapped* hole still gets a hue
        # (template-position tint) and renders dim-coloured, not off — see
        # test_mapped_min_value_uses_floor and the through-Remote integration test.
        self.client.on_burst(_snap(dials=[(0, SlotPayload("P", 1.0, 0.0, 1.0))]))
        body = self._body(self._sent())
        self.assertEqual(self._slot(body, 0), [0, 0, 0])

    def test_dial_zone_colour_premultiplied_full_value(self):
        # E0A33E at full value -> 0xE0/0xA3/0x3E scaled 255->127 (>>1).
        self.client.on_burst(_snap(
            dials=[(0, SlotPayload("P", 1.0, 0.0, 1.0))],
            zone_colors=[('dial', 0, 'E0A33E')],
        ))
        body = self._body(self._sent())
        self.assertEqual(self._slot(body, 0), [0xE0 >> 1, 0xA3 >> 1, 0x3E >> 1])

    def test_mapped_min_value_uses_floor_not_off(self):
        # Mapped pot at its minimum stays dimly lit (floor), never confused with
        # an unmapped/off slot.
        self.client.on_burst(_snap(
            dials=[(0, SlotPayload("P", 0.0, 0.0, 1.0))],
            zone_colors=[('dial', 0, 'FFFFFF')],
        ))
        body = self._body(self._sent())
        expected = (0xFF * MAPPED_FLOOR).__int__() >> 1
        self.assertEqual(self._slot(body, 0), [expected, expected, expected])
        self.assertGreater(expected, 0)

    def test_button_slots_are_offset_after_dials(self):
        # Button wire_idx 0 lands at slot NUM_DIALS.
        self.client.on_burst(_snap(
            buttons=[(0, SlotPayload("B", 1.0, 0.0, 1.0))],
            zone_colors=[('button', 0, '57B368')],
        ))
        body = self._body(self._sent())
        self.assertEqual(self._slot(body, NUM_DIALS), [0x57 >> 1, 0xB3 >> 1, 0x68 >> 1])
        # ...and dial slot 0 is untouched (off).
        self.assertEqual(self._slot(body, 0), [0, 0, 0])

    def test_all_data_bytes_are_7bit(self):
        self.client.on_burst(_snap(
            dials=[(i, SlotPayload("P", 1.0, 0.0, 1.0)) for i in range(NUM_DIALS)],
            zone_colors=[('dial', i, 'FFFFFF') for i in range(NUM_DIALS)],
        ))
        for b in self._sent()[1:-1]:  # exclude F0/F7 framing
            self.assertLessEqual(b, 0x7F)
            self.assertGreaterEqual(b, 0)

    def test_out_of_range_wire_idx_ignored(self):
        # grid-4 buttons or extra dials beyond the 48-slot surface are dropped,
        # not written past the frame.
        self.client.on_burst(_snap(
            dials=[(99, SlotPayload("P", 1.0, 0.0, 1.0))],
            buttons=[(50, SlotPayload("B", 1.0, 0.0, 1.0))],
            zone_colors=[('dial', 99, 'FFFFFF'), ('button', 50, 'FFFFFF')],
        ))
        msg = self._sent()
        self.assertEqual(len(msg), 4 + NUM_SLOTS * 3 + 1)
        self.assertTrue(all(b == 0 for b in self._body(msg)))

    def test_fires_on_suppress_hud_burst(self):
        # LEDs are persistent device state; a suppressed-HUD burst still updates them.
        self.client.on_burst(_snap(
            dials=[(0, SlotPayload("P", 1.0, 0.0, 1.0))],
            zone_colors=[('dial', 0, 'FFFFFF')],
            suppress_hud=True,
        ))
        self.manager._send_midi.assert_called_once()

    def test_dense_clears_prior_tint_on_nonzoned_device(self):
        # Focusing a non-zoned device (empty zone_colors) emits an all-off dense
        # frame, clearing whatever the previous synth lit.
        self.client.on_burst(_snap(
            dials=[(i, SlotPayload("P", 0.5, 0.0, 1.0)) for i in range(NUM_DIALS)],
        ))
        self.assertTrue(all(b == 0 for b in self._body(self._sent())))

    def test_send_midi_failure_is_swallowed(self):
        self.manager._send_midi.side_effect = RuntimeError("bad port")
        # Must not raise out of the burst.
        self.client.on_burst(_snap())
        self.manager.log_message.assert_called()


class TestGridLedThroughRemote(unittest.TestCase):
    """Integration across the real seam: a real GridLedClient registered as a
    feedback sink on Remote must emit a non-zero LED frame when a zoned device
    burst carries zone colours. This is the only test that proves the feature is
    not a silent all-off no-op — it drives the actual
    device_update -> _build_zone_color_entries -> refresh_burst -> on_burst path
    (Remote's try/except would otherwise swallow a real mismatch)."""

    def test_zoned_device_burst_lights_leds(self):
        from source_modules.helpers import Remote

        grid_manager = Mock()
        remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=Mock(),
                        feedback_sinks=[GridLedClient(grid_manager)])

        on_off = Mock(); on_off.param = Mock(); on_off.alias = None; on_off.button = None
        on_off.param.name = "On/Off"
        dial = Mock()
        dial.param = Mock(); dial.param.name = "Osc 1 Pos"
        dial.param.value, dial.param.min, dial.param.max = 1.0, 0.0, 1.0
        dial.alias = None; dial.button = None

        # dial_zone_colors is parallel to real_parameters (index 0 = Device On =
        # None); index 1 tints the single mapped dial at wire_idx 0.
        remote.device_update(
            "Wavetable", [on_off, dial],
            hud_layout=[(0, 0, 'dial', 8, 0)],
            dial_zone_colors=[None, 'E0A33E'])

        grid_manager._send_midi.assert_called_once()
        msg = list(grid_manager._send_midi.call_args[0][0])
        self.assertEqual(msg[:4], [SYSEX_START, NON_COMMERCIAL_ID, LED_CMD, VERSION])
        self.assertEqual(msg[-1], SYSEX_END)
        body = msg[4:-1]
        # Slot 0 (the mapped, tinted, full-value dial) must be lit.
        self.assertEqual(body[0:3], [0xE0 >> 1, 0xA3 >> 1, 0x3E >> 1])
        self.assertTrue(any(b > 0 for b in body), "LED frame must not be all-off")


if __name__ == '__main__':
    unittest.main()
