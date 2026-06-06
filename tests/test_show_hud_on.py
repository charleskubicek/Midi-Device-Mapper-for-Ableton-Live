import unittest
from unittest.mock import Mock

from ableton_control_surface_as_code.model_v2 import (
    read_root, HudTrigger, ModeGroupWithMidi, ModeType, ModeButtonWithMidi,
)
from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from source_modules.helpers import Helpers
from source_modules.helpers import Remote
from tests.builders import build_mixer_with_midi, midi_coords_ch2_cc_50_knob


_BASE = """\
controller: ec4.nt
ableton_dir: /tmp
"""


class FakeDevice:
    def __init__(self, name="Dev", parameters=None):
        self.name = name
        self.class_name = name
        self.parameters = parameters or [Mock(name="p0")]


# ---------------------------------------------------------------------------
# Parsing: the new `show-hud-on:` trigger key.
# ---------------------------------------------------------------------------
class TestShowHudOnParsing(unittest.TestCase):
    def test_defaults_to_controller_nav(self):
        root = read_root(_BASE)
        self.assertEqual(root.show_hud_on, HudTrigger.ControllerNav)

    def test_controller_nav_parsed(self):
        root = read_root(_BASE + "show-hud-on: controller-nav\n")
        self.assertEqual(root.show_hud_on, HudTrigger.ControllerNav)

    def test_selection_parsed(self):
        root = read_root(_BASE + "show-hud-on: selection\n")
        self.assertEqual(root.show_hud_on, HudTrigger.Selection)

    def test_bad_value_rejected(self):
        with self.assertRaises(Exception):
            read_root(_BASE + "show-hud-on: device-view\n")


# ---------------------------------------------------------------------------
# Codegen: the trigger is threaded into the template vars.
# ---------------------------------------------------------------------------
class TestShowHudOnCodegen(unittest.TestCase):
    def _vars(self, **kwargs):
        m = ModeGroupWithMidi(
            mappings=[("mode_1", [build_mixer_with_midi(api_fn='pan')])],
            mode_button=ModeButtonWithMidi(
                on_colors=[], button=midi_coords_ch2_cc_50_knob(), type=ModeType.Switch),
        )
        return generate_code_as_template_vars(m, **kwargs)

    def test_default_trigger_is_controller_nav(self):
        res = self._vars()
        self.assertEqual(res['hud_trigger'], "'controller-nav'")

    def test_controller_nav_trigger_rendered(self):
        res = self._vars(hud_trigger=HudTrigger.ControllerNav)
        self.assertEqual(res['hud_trigger'], "'controller-nav'")


# ---------------------------------------------------------------------------
# Runtime gating at the Helpers layer: selected_device_changed decides whether
# the burst is suppressed based on (trigger, source).
# ---------------------------------------------------------------------------
class TestHelpersBurstGating(unittest.TestCase):
    def _helpers(self, trigger):
        return Helpers(Mock(), Mock(), hud_trigger=trigger)

    def _suppress_arg(self, remote):
        # device_update is called with a keyword suppress_hud=...
        self.assertTrue(remote.device_update.called)
        return remote.device_update.call_args.kwargs.get('suppress_hud')

    def test_controller_nav_suppresses_on_selection_source(self):
        h = self._helpers('controller-nav')
        h.selected_device_changed(FakeDevice())  # default source = selection
        self.assertTrue(self._suppress_arg(h._remote))

    def test_controller_nav_shows_on_nav_source(self):
        h = self._helpers('controller-nav')
        h.selected_device_changed(FakeDevice(), source='nav')
        self.assertFalse(self._suppress_arg(h._remote))

    def test_selection_trigger_never_suppresses(self):
        h = self._helpers('selection')
        h.selected_device_changed(FakeDevice())
        self.assertFalse(self._suppress_arg(h._remote))

    def test_selection_trigger_shows_on_nav_too(self):
        h = self._helpers('selection')
        h.selected_device_changed(FakeDevice(), source='nav')
        self.assertFalse(self._suppress_arg(h._remote))

    def test_suppressed_selection_sends_hide(self):
        # A suppressed selection change must HIDE so a later live send_update
        # (knob turn) can't wake the HUD on the wrong/stale device.
        h = self._helpers('controller-nav')
        h.selected_device_changed(FakeDevice())
        self.assertTrue(h._remote.hide.called)
        self.assertTrue(h._hud_dismissed)

    def test_nav_source_does_not_hide(self):
        h = self._helpers('controller-nav')
        h.selected_device_changed(FakeDevice(), source='nav')
        h._remote.hide.assert_not_called()

    def test_selection_trigger_does_not_hide(self):
        h = self._helpers('selection')
        h.selected_device_changed(FakeDevice())
        h._remote.hide.assert_not_called()

    def test_suppressed_burst_keeps_remap_running(self):
        # Even when the HUD is suppressed, the device must be remapped so the
        # encoders control it: _last_selected_device updates + the param push
        # (device_update) still fires (it carries the OSC sends too).
        h = self._helpers('controller-nav')
        dev = FakeDevice()
        h.selected_device_changed(dev)
        self.assertIs(h._last_selected_device, dev)
        self.assertTrue(h._remote.device_update.called)


# ---------------------------------------------------------------------------
# Runtime gating at the Remote layer: suppress_hud skips the HUD wire calls but
# keeps the OSC sends.
# ---------------------------------------------------------------------------
def _make_param(name="Freq", value=0.5, vmin=0.0, vmax=1.0):
    p = Mock()
    p.name = name
    p.value = value
    p.min = vmin
    p.max = vmax
    return p


def _make_real_param(param, alias=None, button=None):
    rp = Mock()
    rp.param = param
    rp.alias = alias
    rp.button = button
    return rp


class TestRemoteSuppressHud(unittest.TestCase):
    def setUp(self):
        self.osc = Mock()
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=self.osc, hud_client=self.hud)

    def test_suppress_skips_hud_wire(self):
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        self.remote.device_update("Dev", params, suppress_hud=True)
        self.hud.send_device.assert_not_called()
        self.hud.commit.assert_not_called()

    def test_suppress_still_sends_osc(self):
        params = [_make_real_param(_make_param())]
        self.remote.device_update("Dev", params, suppress_hud=True)
        self.assertTrue(self.osc.send_message.called)

    def test_no_suppress_sends_hud(self):
        params = [_make_real_param(_make_param())]
        self.remote.device_update("EQ Eight", params, suppress_hud=False)
        self.hud.send_device.assert_called_once_with("EQ Eight")


if __name__ == "__main__":
    unittest.main()
