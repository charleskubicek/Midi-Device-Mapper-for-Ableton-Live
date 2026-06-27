"""Direct unit tests for HudPresenter (R9): burst assembly + show/hide intent,
testable with a fake Remote + a real ParameterResolver, no surface needed."""
import unittest
from unittest.mock import Mock

from source_modules.hud_presenter import HudPresenter
from source_modules.param_resolver import ParameterResolver, _build_device_table


class FakeParam:
    def __init__(self, name, value=0.0, mn=0.0, mx=1.0, is_quantized=False):
        self.name = name
        self.original_name = name
        self.value = value
        self.min = mn
        self.max = mx
        self.is_quantized = is_quantized


class FakeDevice:
    def __init__(self, class_name, parameters):
        self.class_name = class_name
        self.name = class_name
        self.parameters = parameters


def _presenter(slot_assignments=(), switch_slot_assignments=(), hud_cells=(),
               slot_assignments_by_mode=None, switch_slot_assignments_by_mode=None,
               mode_hud_labels=None, button_switch_count=0):
    resolver = ParameterResolver(
        device_table=_build_device_table(None), device_banks={}, bank_names={},
        banks_per_page=1, button_switch_count=button_switch_count, button_slot_count=8,
        log=lambda m: None)
    remote = Mock()
    p = HudPresenter(remote=remote, resolver=resolver,
                     slot_assignments=list(slot_assignments),
                     switch_slot_assignments=list(switch_slot_assignments),
                     hud_cells=list(hud_cells), mode_hud_labels=mode_hud_labels or {},
                     log=lambda m: None,
                     slot_assignments_by_mode=slot_assignments_by_mode,
                     switch_slot_assignments_by_mode=switch_slot_assignments_by_mode)
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


class TestPerModeAssignments(unittest.TestCase):
    """Device slot/switch assignments are resolved per active mode, not from a
    global union across all modes — otherwise an encoder device-bound in one
    mode shows stale device data in a mode where it is mixer/empty-bound."""

    @staticmethod
    def _real_params(remote):
        # device_update(name, real_params, ...) — real_params is positional arg 1.
        return [r for r in remote.device_update.call_args[0][1] if r is not None]

    @staticmethod
    def _switch_entries(remote):
        # device_update(name, real_params, info_text, switch_entries, ...)
        return list(remote.device_update.call_args[0][3])

    def test_encoder_device_bound_only_in_its_mode(self):
        p, remote = _presenter(
            slot_assignments_by_mode={'a': [(1, 'slot1')], 'b': []})
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])

        p.refresh_for_mode('a', dev)
        # on_off + the device-bound encoder
        self.assertEqual(len(self._real_params(remote)), 2)

        p.refresh_for_mode('b', dev)
        # mode b binds no device encoders -> only on_off
        self.assertEqual(len(self._real_params(remote)), 1)

    def test_switch_device_bound_only_in_its_mode(self):
        p, remote = _presenter(
            button_switch_count=1,
            switch_slot_assignments_by_mode={'a': [(0, 'switch1')], 'b': []})
        dev = FakeDevice("X", [FakeParam("On/Off"),
                               FakeParam("Q", is_quantized=True, mn=0, mx=2)])

        p.refresh_for_mode('a', dev)
        self.assertEqual(len(self._switch_entries(remote)), 1)

        p.refresh_for_mode('b', dev)
        self.assertEqual(len(self._switch_entries(remote)), 0)

    def test_label_overlays_encoder_left_empty_in_mode(self):
        # In mode 'b' the encoder is not device-bound, so its dial slot is EMPTY
        # and the mode's static dial label overlays it (this is the shift-mode
        # "encoder text not updated" bug).
        from source_modules.hud_protocol import LayoutCell, EMPTY_SLOT
        cells = [tuple(LayoutCell(0, 0, 'dial', 1, 0, 0))]
        p, remote = _presenter(
            hud_cells=cells,
            slot_assignments_by_mode={'a': [(1, 'slot1')], 'b': []},
            mode_hud_labels={'b': {('dial', 0): 'Volume'}})
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])

        p.refresh_for_mode('b', dev)
        mode_labels = remote.device_update.call_args.kwargs.get('mode_labels')
        self.assertEqual(mode_labels, {('dial', 0): 'Volume'})
        # encoder is not resolved against the device in mode 'b'
        self.assertEqual(len(self._real_params(remote)), 1)

    def test_falls_back_to_global_when_mode_unknown(self):
        # Modeless / pre-goto_mode: no by-mode dict entry -> use the flat list.
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.emit_burst(dev)
        self.assertEqual(len(self._real_params(remote)), 2)


class TestVisibilityWiring(unittest.TestCase):
    """R10 follow-up: the template's app-view dismiss, the mode refresh and the
    compositor re-emit all route through the HudVisibility table instead of
    raw send_hide()/flag writes."""

    def test_view_left_hides_and_sets_intent(self):
        p, remote = _presenter()
        p.view_left()
        remote.hide.assert_called_once()
        self.assertTrue(p.hud_dismissed)

    def test_view_left_dismiss_is_cleared_by_mode_refresh(self):
        # ModeChange always shows — even after a view-left dismiss.
        p, remote = _presenter()
        p.view_left()
        p.refresh_for_mode('mode-a', None)
        self.assertFalse(p.hud_dismissed)
        remote.device_update.assert_called_once()

    def test_reemit_combined_burst_clears_dismiss(self):
        # RegionCommit is a real burst: it must clear a sticky dismiss.
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        p.view_left()
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.reemit_combined_burst(dev)
        self.assertFalse(p.hud_dismissed)
        remote.device_update.assert_called_once()


if __name__ == "__main__":
    unittest.main()
