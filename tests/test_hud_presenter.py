"""Direct unit tests for HudPresenter (R9): burst assembly + show/hide intent,
testable with a fake Remote + a real ParameterResolver, no surface needed."""
import unittest
from unittest.mock import Mock

from source_modules.hud_presenter import HudPresenter
from source_modules.param_resolver import ParameterResolver, _build_device_table


class FakeParam:
    def __init__(self, name, value=0.0, mn=0.0, mx=1.0):
        self.name = name
        self.original_name = name
        self.value = value
        self.min = mn
        self.max = mx
        self.is_quantized = False


class FakeDevice:
    def __init__(self, class_name, parameters):
        self.class_name = class_name
        self.name = class_name
        self.parameters = parameters


def _presenter(slot_assignments=(), switch_slot_assignments=(), hud_cells=()):
    resolver = ParameterResolver(
        device_table=_build_device_table(None), device_banks={}, bank_names={},
        banks_per_page=1, button_switch_count=0, button_slot_count=8, log=lambda m: None)
    remote = Mock()
    p = HudPresenter(remote=remote, resolver=resolver,
                     slot_assignments=list(slot_assignments),
                     switch_slot_assignments=list(switch_slot_assignments),
                     hud_cells=list(hud_cells), mode_hud_labels={}, log=lambda m: None)
    return p, remote


class TestHudPresenterDirect(unittest.TestCase):
    def test_emit_burst_none_device_is_noop(self):
        p, remote = _presenter()
        p.emit_burst(None)
        remote.device_update.assert_not_called()

    def test_emit_burst_clears_dismiss_intent(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        p.hud_dismissed = True
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.emit_burst(dev)
        self.assertFalse(p.hud_dismissed)
        remote.device_update.assert_called_once()

    def test_suppress_sets_dismiss_and_hides(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.emit_burst(dev, suppress_hud=True)
        self.assertTrue(p.hud_dismissed)
        remote.hide.assert_called_once()

    def test_toggle_hides_then_reshows(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)               # dismiss -> hide
        self.assertTrue(p.hud_dismissed)
        remote.hide.assert_called_once()
        p.toggle(dev)               # show -> burst
        self.assertFalse(p.hud_dismissed)
        remote.device_update.assert_called()

    def test_label_only_burst_when_no_device(self):
        p, remote = _presenter()
        p.refresh_for_mode('mode-a', None)
        remote.device_update.assert_called_once()
        # empty device name marks the label-only burst
        self.assertEqual(remote.device_update.call_args[0][0], '')


if __name__ == "__main__":
    unittest.main()
