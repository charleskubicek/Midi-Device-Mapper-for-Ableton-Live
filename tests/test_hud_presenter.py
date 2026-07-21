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


class _DeadDevice:
    """A device whose C++ handle was freed (replaced/deleted, e.g. Wavetable →
    Drift). Every attribute access raises — modeling Boost.Python.ArgumentError
    (a TypeError subclass, NOT AttributeError), which is exactly why
    `getattr(device, 'name', None)` at the top of emit_burst used to crash the
    whole burst instead of degrading."""
    def __getattr__(self, name):
        raise TypeError("Boost.Python.ArgumentError: dead device handle")


class _DeadDeviceRaisingEq(_DeadDevice):
    __hash__ = object.__hash__

    def __eq__(self, other):
        raise TypeError("Boost.Python.ArgumentError: dead device handle")


def _presenter(slot_assignments=(), switch_slot_assignments=(), hud_cells=(),
               slot_assignments_by_mode=None, switch_slot_assignments_by_mode=None,
               mode_hud_labels=None, button_switch_count=0, hud_trigger='controller-nav'):
    resolver = ParameterResolver(
        device_table=_build_device_table(None), device_banks={}, bank_names={},
        banks_per_page=1, button_switch_count=button_switch_count, button_slot_count=8,
        log=lambda m: None)
    remote = Mock()
    # Idle-toggle passthrough: default to "no send yet" so toggle's idle-sync is
    # skipped (Mock() > 7 would raise). Idle tests override return_value.
    remote.seconds_since_last_hud_send.return_value = None
    p = HudPresenter(remote=remote, resolver=resolver,
                     slot_assignments=list(slot_assignments),
                     switch_slot_assignments=list(switch_slot_assignments),
                     hud_cells=list(hud_cells), mode_hud_labels=mode_hud_labels or {},
                     log=lambda m: None, hud_trigger=hud_trigger,
                     slot_assignments_by_mode=slot_assignments_by_mode,
                     switch_slot_assignments_by_mode=switch_slot_assignments_by_mode)
    return p, remote


class TestHudPresenterDirect(unittest.TestCase):
    def test_emit_burst_none_device_is_noop(self):
        p, remote = _presenter()
        p.emit_burst(None)
        remote.device_update.assert_not_called()

    def test_emit_burst_resets_paging_for_new_device_bypassing_funnel(self):
        # Reproduces the stale-index bug: a burst arrives for a different device
        # without the Helpers funnel having reset the resolver (e.g. page left at
        # 4 by the previous device). emit_burst must self-correct to page 1.
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        dev_a = FakeDevice("A", [FakeParam("On/Off"), FakeParam("A")])
        p.emit_burst(dev_a)
        p._resolver.encoder_page = 4          # stale paging from dev_a
        dev_b = FakeDevice("B", [FakeParam("On/Off"), FakeParam("B")])
        p.emit_burst(dev_b)                   # funnel never ran for dev_b
        self.assertEqual(p._resolver.encoder_page, 1)

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

    def test_toggle_sends_marker_then_fresh_burst(self):
        # HUD-arbitrated toggle: every press sends a TOGGLE marker followed by a
        # fresh burst; the HUD decides show-vs-hide. Python never calls hide().
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)
        remote.send_toggle.assert_called_once()
        remote.device_update.assert_called_once()
        remote.hide.assert_not_called()

    def test_label_only_burst_when_no_device(self):
        p, remote = _presenter()
        p.refresh_for_mode('mode-a', None)
        remote.device_update.assert_called_once()
        # empty device name marks the label-only burst
        self.assertEqual(remote.device_update.call_args[0][0], '')


class TestDeadDeviceGuard(unittest.TestCase):
    """emit_burst must never touch a dead device handle. The reported crash was
    a Boost.Python.ArgumentError raised by `getattr(device, 'name', None)` at
    the top of emit_burst after a device was replaced (Wavetable → Drift),
    which aborted the burst and left the HUD permanently dead."""

    def test_emit_burst_on_dead_device_does_not_raise_and_hides(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        p.emit_burst(_DeadDevice())            # must not raise
        remote.device_update.assert_not_called()
        remote.hide.assert_called_once()

    def test_emit_burst_on_dead_device_with_raising_eq(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        p.emit_burst(_DeadDeviceRaisingEq())   # must not raise
        remote.device_update.assert_not_called()
        remote.hide.assert_called_once()

    def test_emit_burst_none_device_still_noop_no_hide(self):
        # None is the pre-existing early-return contract: no burst AND no hide.
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        p.emit_burst(None)
        remote.device_update.assert_not_called()
        remote.hide.assert_not_called()

    def test_live_device_still_produces_full_burst(self):
        # Regression: the dead-handle guard must not break the happy path.
        p, remote = _presenter(slot_assignments=[(1, 'slot1')])
        dev = FakeDevice("Drift", [FakeParam("On/Off"), FakeParam("A")])
        p.emit_burst(dev)
        remote.device_update.assert_called_once()
        remote.hide.assert_not_called()

    def test_getattr_default_does_not_swallow_dead_handle(self):
        # Anti-vacuous: proves the double models the real (non-AttributeError)
        # failure that getattr's default cannot catch.
        with self.assertRaises(TypeError):
            getattr(_DeadDevice(), 'name', None)


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
            switch_slot_assignments_by_mode={'a': [(0, 1)], 'b': []})
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


class TestPagePreviewBurst(unittest.TestCase):
    """Parameter-pager pressed from a shift mode: one burst resolves the *base*
    mode's device page so the user sees the new params, without leaving shift."""

    @staticmethod
    def _real_params(remote):
        return [r for r in remote.device_update.call_args[0][1] if r is not None]

    def test_preview_resolves_other_modes_device_encoders(self):
        # In shift_mode the encoder is mixer/empty-bound (no device slots); main
        # binds the device encoder. A preview burst keyed on 'main' resolves it.
        p, remote = _presenter(
            slot_assignments_by_mode={'main': [(1, 'slot1')], 'shift': []})
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.refresh_for_mode('shift', dev)
        self.assertEqual(len(self._real_params(remote)), 1)  # on_off only

        p.emit_burst(dev, preview_mode_name='main')
        # on_off + the base mode's device-bound encoder, previewed
        self.assertEqual(len(self._real_params(remote)), 2)

    def test_preview_does_not_change_active_mode(self):
        p, remote = _presenter(
            slot_assignments_by_mode={'main': [(1, 'slot1')], 'shift': []})
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.refresh_for_mode('shift', dev)
        p.emit_burst(dev, preview_mode_name='main')
        self.assertEqual(p._current_mode_name, 'shift')

    def test_preview_noop_when_target_is_active_mode(self):
        # Paging while already in the base mode: preview target == active mode,
        # so it behaves like a normal burst (no special-casing).
        p, remote = _presenter(
            slot_assignments_by_mode={'main': [(1, 'slot1')], 'shift': []})
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.refresh_for_mode('main', dev)
        p.emit_burst(dev, preview_mode_name='main')
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


class TestModeRefreshHonoursSilentDecision(unittest.TestCase):
    """Under summon, a mode press while the HUD is hidden must not summon it:
    refresh_for_mode routes the ModeChange decision into suppress_hud like
    on_device_focus, instead of always showing."""

    def test_mode_refresh_while_hidden_summon_is_silent(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='summon')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        # summon boots dismissed; a mode change must stay silent + hide.
        p.refresh_for_mode('mode-a', dev)
        self.assertTrue(p.hud_dismissed)
        remote.hide.assert_called_once()

    def test_mode_refresh_while_shown_summon_repaints(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='summon')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)                 # summon -> shown
        remote.reset_mock()
        remote.seconds_since_last_hud_send.return_value = None
        p.refresh_for_mode('mode-a', dev)
        self.assertFalse(p.hud_dismissed)
        remote.hide.assert_not_called()
        remote.device_update.assert_called()

    def test_label_only_mode_refresh_while_hidden_summon_is_silent(self):
        # No focused device: the label-only path must also honour suppress.
        p, remote = _presenter(hud_trigger='summon')
        p.refresh_for_mode('mode-a', None)
        self.assertTrue(p.hud_dismissed)
        remote.hide.assert_called_once()

    def test_selection_trigger_mode_refresh_still_shows(self):
        # Non-summon surfaces keep the old "mode change always shows" feel.
        p, remote = _presenter(hud_trigger='selection')
        p.refresh_for_mode('mode-a', None)
        self.assertFalse(p.hud_dismissed)
        remote.hide.assert_not_called()


class TestClipViewChanged(unittest.TestCase):
    """The presenter's clip_view_changed forwards both directions to the
    visibility table and hides on the HIDE decision."""

    def test_entering_clip_view_hides(self):
        p, remote = _presenter(hud_trigger='selection')
        p.clip_view_changed(True)
        remote.hide.assert_called_once()
        self.assertTrue(p.hud_dismissed)

    def test_leaving_clip_view_does_not_hide_or_show(self):
        p, remote = _presenter(hud_trigger='selection')
        p.clip_view_changed(True)
        remote.reset_mock()
        p.clip_view_changed(False)
        remote.hide.assert_not_called()
        remote.device_update.assert_not_called()

    def test_clip_view_gate_suppresses_selection_burst(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='selection')
        p.clip_view_changed(True)
        remote.reset_mock()
        remote.seconds_since_last_hud_send.return_value = None
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.on_device_focus(dev, 'selection')
        self.assertTrue(p.hud_dismissed)
        remote.hide.assert_called_once()


class TestHudArbitratedToggle(unittest.TestCase):
    """hud_toggle is arbitrated by the HUD (Python can't track HUD visibility —
    it hides autonomously via the idle timer and the input monitor). Every press
    sends a TOGGLE marker + a fresh burst; the HUD hides if it was visible, shows
    the fresh data if not. So on the Python side a press is always
    `send_toggle()` + a burst, never a hide(), for every trigger."""

    def test_summon_toggle_marker_then_burst(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='summon')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)
        remote.send_toggle.assert_called_once()
        remote.device_update.assert_called_once()
        remote.hide.assert_not_called()

    def test_marker_precedes_burst(self):
        # The TOGGLE must reach the HUD before the burst's COMMIT so the HUD arms
        # its arbitration against the pre-burst visibility. send_toggle is fired
        # before emit_current_burst (which produces device_update).
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='summon')
        order = []
        remote.send_toggle.side_effect = lambda: order.append('toggle')
        remote.device_update.side_effect = lambda *a, **k: order.append('burst')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)
        self.assertEqual(order, ['toggle', 'burst'])

    def test_non_summon_toggle_also_arbitrated(self):
        # No more Python-side flip/idle-sync — the HUD decides for every trigger.
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='controller-nav')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)
        remote.send_toggle.assert_called_once()
        remote.hide.assert_not_called()

    def test_toggle_without_device_still_sends_marker_and_burst(self):
        p, remote = _presenter(hud_trigger='summon')
        p.toggle(None)
        remote.send_toggle.assert_called_once()
        remote.device_update.assert_called_once()   # label-only burst
        remote.hide.assert_not_called()


class TestDeviceFocusLost(unittest.TestCase):
    """Track-nav onto a device-less track routes through on_device_focus_lost:
    the visibility table decides, and only EMIT_SILENT_AND_HIDE sends hide. No
    burst, no resolver — there is nothing to resolve (hud-hide-on-empty-track)."""

    def test_focus_lost_hides_under_summon(self):
        p, remote = _presenter(hud_trigger='summon')
        p.on_device_focus_lost('selection')
        remote.hide.assert_called_once()
        self.assertTrue(p.hud_dismissed)
        remote.device_update.assert_not_called()

    def test_focus_lost_hides_under_controller_nav(self):
        p, remote = _presenter(hud_trigger='controller-nav')
        p.on_device_focus_lost('selection')
        remote.hide.assert_called_once()
        self.assertTrue(p.hud_dismissed)

    def test_focus_lost_noop_under_selection(self):
        # 'selection' classifies DeviceFocus('selection') to EMIT_BURST; with
        # nothing to burst it is a deliberate no-op (no hide races the COMMIT).
        p, remote = _presenter(hud_trigger='selection')
        p.on_device_focus_lost('selection')
        remote.hide.assert_not_called()
        remote.device_update.assert_not_called()


class TestReemitCombinedBurstClipGate(unittest.TestCase):
    """reemit_combined_burst must honour the clip-view gate: while a clip is
    open the RegionCommit decision is EMIT_SILENT_AND_HIDE, so the combined
    burst is suppressed (hide sent, HUD wire skipped) rather than re-shown."""

    def test_clip_open_suppresses_region_burst(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='selection')
        p.clip_view_changed(True)                 # enter clip view -> gate up + hide
        remote.reset_mock()
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.reemit_combined_burst(dev)
        remote.hide.assert_called_once()
        self.assertTrue(p.hud_dismissed)
        # device_update still fires (OSC/sinks) but suppressed on the HUD wire.
        self.assertTrue(remote.device_update.call_args.kwargs.get('suppress_hud'))

    def test_clip_closed_region_burst_shows(self):
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='selection')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.reemit_combined_burst(dev)
        self.assertFalse(p.hud_dismissed)
        self.assertFalse(remote.device_update.call_args.kwargs.get('suppress_hud'))


class TestIdleSyncOnDeviceFocus(unittest.TestCase):
    """The idle-sync mirror fix still guards the device-focus / mode-refresh
    paths (a Swift idle-dismiss the Python mirror never learned about)."""

    def test_summon_selection_after_idle_hide_stays_hidden(self):
        # The core-promise regression: under summon the HUD is shown (toggled
        # on), the Swift idle timer then sticky-hides it (Python mirror still
        # reads shown), and a mouse selection arrives. It must NOT re-summon.
        from source_modules.hud_protocol import IDLE_DISMISS_SECONDS
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='summon')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)                          # summon -> shown, mirror dismissed=False
        self.assertFalse(p.hud_dismissed)
        remote.reset_mock()
        remote.seconds_since_last_hud_send.return_value = IDLE_DISMISS_SECONDS + 1
        p.on_device_focus(dev, 'selection')    # mouse click after the idle hide
        self.assertTrue(p.hud_dismissed)       # stayed hidden
        remote.hide.assert_called_once()

    def test_summon_mode_press_after_idle_hide_stays_hidden(self):
        from source_modules.hud_protocol import IDLE_DISMISS_SECONDS
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='summon')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        p.toggle(dev)
        remote.reset_mock()
        remote.seconds_since_last_hud_send.return_value = IDLE_DISMISS_SECONDS + 1
        p.refresh_for_mode('mode-a', dev)      # shift/mode press after idle hide
        self.assertTrue(p.hud_dismissed)
        remote.hide.assert_called_once()

    def test_selection_trigger_after_idle_hide_still_repaints(self):
        # Non-summon must be unaffected: selection repaints regardless of the
        # synced mirror (its DeviceFocus rule ignores `dismissed`).
        from source_modules.hud_protocol import IDLE_DISMISS_SECONDS
        p, remote = _presenter(slot_assignments=[(1, 'slot1')], hud_trigger='selection')
        dev = FakeDevice("X", [FakeParam("On/Off"), FakeParam("A")])
        remote.seconds_since_last_hud_send.return_value = IDLE_DISMISS_SECONDS + 1
        p.on_device_focus(dev, 'selection')
        self.assertFalse(p.hud_dismissed)      # repainted, shown
        remote.hide.assert_not_called()


if __name__ == "__main__":
    unittest.main()
