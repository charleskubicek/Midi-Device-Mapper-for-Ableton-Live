"""`on-off:` under a device mapping (hud-quick-fixes-plan §3).

Live parameter 0 is the device's on/off switch. It is not an encoder slot, so it
must never travel `ParameterResolver.resolve_encoder` — which is exactly what
the old codegen did, by emitting the ordinary
`device_parameter_action(device, 0, ...)`.
"""
import unittest
from unittest.mock import Mock

from ableton_control_surface_as_code.core_model import (
    EncoderMode, EncoderType, MidiCoords, TrackInfo,
)
from ableton_control_surface_as_code.gen_code import device_templates
from ableton_control_surface_as_code.model_device import (
    DeviceParameterMidiMapping, DeviceWithMidi,
)
from source_modules.helpers import Helpers
from source_modules.param_resolver import ParameterResolver, _build_device_table
from tests.test_param_resolver import FakeDevice, FakeParam


def _coord(number, encoder_type=EncoderType.button):
    return MidiCoords(channel=1, type="note", number=number,
                      encoder_type=encoder_type, encoder_mode=EncoderMode.Absolute,
                      source_info="tests")


def _device_with_on_off():
    return DeviceWithMidi(
        track=TrackInfo.selected(),
        device="selected",
        midi_maps=[
            DeviceParameterMidiMapping(midi_coords=[_coord(10, EncoderType.knob)],
                                       parameter=3),
            DeviceParameterMidiMapping(midi_coords=[_coord(11)], parameter=0,
                                       is_on_off=True),
        ],
    )


class TestResolverRejectsParameterZero(unittest.TestCase):
    """Why the bypass exists, pinned as a fact rather than a comment: encoder
    slots are 1-based, so `resolve_encoder(device, 0)` computes slot index -1
    and negative-indexes the Best-of-Bank list — the on/off press silently drove
    the LAST bank parameter instead of the device switch."""

    def test_encoder_zero_negative_indexes_the_bob_list(self):
        raw = {"devices": [{"className": "Amp", "encoders": [
            {"name": "Bass"}, {"name": "Treble"}], "buttons": []}]}
        r = ParameterResolver(device_table=_build_device_table(raw), device_banks={},
                              bank_names={}, banks_per_page=1, button_switch_count=0,
                              button_slot_count=8, log=lambda _m: None)
        dev = FakeDevice("Amp", [FakeParam("Device On"), FakeParam("Bass"),
                                 FakeParam("Treble")])

        rp = r.resolve_encoder(dev, 0)

        self.assertIsNotNone(rp, "if this is now None the bug changed shape, not away")
        self.assertIs(rp.param, dev.parameters[2],
                      "encoder 0 wrapped around to the last BOB entry (Treble)")


class TestOnOffCodegen(unittest.TestCase):
    def _listener_source(self):
        codes = device_templates(_device_with_on_off(), 'main_mode')
        return "\n".join(line for c in codes for line in c.listener_fns)

    def test_on_off_gets_its_own_action(self):
        self.assertIn("device_on_off_action(device,", self._listener_source())

    def test_on_off_never_goes_through_the_encoder_resolver(self):
        body = self._listener_source()
        self.assertNotIn("device_parameter_action(device, 0,", body)

    def test_ordinary_parameters_are_untouched(self):
        self.assertIn("device_parameter_action(device, 3,", self._listener_source())

    def test_the_press_pings_the_hud(self):
        # `parameter_updated(rp, 0)` deliberately emits no dial UPDATE (this
        # cell carries a static label), so without an explicit PING the on/off
        # button would be the only control that never re-arms the HUD's
        # idle-dismiss timer.
        self.assertIn("self._hud_client.send_ping()", self._listener_source())


class TestOnOffRuntime(unittest.TestCase):
    def _helpers(self):
        h = Helpers.__new__(Helpers)
        h._remote = Mock()
        h._manager = Mock()
        h.should_act_on_edge = Mock(return_value=True)
        h.selected_device_changed = Mock()
        h.log_message = Mock()
        return h

    def test_toggles_live_parameter_zero_directly(self):
        h = self._helpers()
        dev = FakeDevice("Amp", [FakeParam("Device On", value=1.0, mn=0.0, mx=1.0),
                                 FakeParam("Bass", value=0.5)])

        h.device_on_off_action(dev, 11, 127, "fn")

        self.assertEqual(0.0, dev.parameters[0].value)
        self.assertEqual(0.5, dev.parameters[1].value, "no other parameter is touched")

    def test_toggles_back_on(self):
        h = self._helpers()
        dev = FakeDevice("Amp", [FakeParam("Device On", value=0.0, mn=0.0, mx=1.0)])

        h.device_on_off_action(dev, 11, 127, "fn")

        self.assertEqual(1.0, dev.parameters[0].value)

    def test_release_edge_does_not_re_toggle(self):
        h = self._helpers()
        h.should_act_on_edge = Mock(return_value=False)
        dev = FakeDevice("Amp", [FakeParam("Device On", value=1.0, mn=0.0, mx=1.0)])

        h.device_on_off_action(dev, 11, 0, "fn")

        self.assertEqual(1.0, dev.parameters[0].value)

    def test_no_device_is_a_no_op(self):
        h = self._helpers()
        h.device_on_off_action(None, 11, 127, "fn")  # must not raise

    def test_missing_parameters_is_a_no_op(self):
        h = self._helpers()
        h.device_on_off_action(FakeDevice("Amp", []), 11, 127, "fn")  # must not raise
