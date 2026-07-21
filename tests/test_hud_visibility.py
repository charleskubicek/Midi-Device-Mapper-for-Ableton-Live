"""The HUD visibility decision table (R10). Encodes today's exact behaviour,
warts included (suppressed-selection sends HIDE; mode change always shows), so
the table is the executable spec the wiring must preserve."""
import unittest

from source_modules.hud_visibility import (
    HudVisibility, Decision,
    DeviceFocus, ModeChange, UserToggle, ViewLeft, RegionCommit, RegionHide, ControlTouched,
    ClipViewChanged,
)


class TestDeviceFocus(unittest.TestCase):
    def test_nav_always_emits(self):
        for trigger in ('selection', 'controller-nav'):
            v = HudVisibility(trigger)
            self.assertEqual(v.decide(DeviceFocus('nav')), Decision.EMIT_BURST)
            self.assertFalse(v.dismissed)

    def test_selection_under_selection_trigger_emits(self):
        v = HudVisibility('selection')
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_BURST)

    def test_selection_under_controller_nav_is_silent_and_hides(self):
        v = HudVisibility('controller-nav')
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_SILENT_AND_HIDE)
        self.assertTrue(v.dismissed)

class TestApply(unittest.TestCase):
    """apply() is the single state-transition function: every dismissed change
    in production goes through it (decide() = classify + apply)."""

    def test_apply_emit_burst_clears_dismissed(self):
        v = HudVisibility('controller-nav')
        v.dismissed = True
        v.apply(Decision.EMIT_BURST)
        self.assertFalse(v.dismissed)

    def test_apply_hide_variants_set_dismissed(self):
        for d in (Decision.HIDE, Decision.EMIT_SILENT_AND_HIDE):
            v = HudVisibility('controller-nav')
            v.apply(d)
            self.assertTrue(v.dismissed)

    def test_apply_ping_and_nothing_leave_state(self):
        for d in (Decision.PING, Decision.NOTHING):
            for start in (False, True):
                v = HudVisibility('selection')
                v.dismissed = start
                v.apply(d)
                self.assertEqual(v.dismissed, start)


class TestSimpleEvents(unittest.TestCase):
    def test_mode_change_always_shows(self):
        v = HudVisibility('controller-nav')
        v.dismissed = True
        self.assertEqual(v.decide(ModeChange()), Decision.EMIT_BURST)
        self.assertFalse(v.dismissed)

    def test_view_left_hides(self):
        v = HudVisibility('selection')
        self.assertEqual(v.decide(ViewLeft()), Decision.HIDE)
        self.assertTrue(v.dismissed)

    def test_region_commit_emits(self):
        v = HudVisibility('controller-nav')
        v.dismissed = True
        self.assertEqual(v.decide(RegionCommit()), Decision.EMIT_BURST)
        self.assertFalse(v.dismissed)


class TestUserToggle(unittest.TestCase):
    def test_toggle_from_shown_hides(self):
        v = HudVisibility('selection')  # starts shown (dismissed=False)
        self.assertEqual(v.decide(UserToggle()), Decision.HIDE)
        self.assertTrue(v.dismissed)

    def test_toggle_from_hidden_shows(self):
        v = HudVisibility('selection')
        v.dismissed = True
        self.assertEqual(v.decide(UserToggle()), Decision.EMIT_BURST)
        self.assertFalse(v.dismissed)


class TestRaceInvariants(unittest.TestCase):
    """The three races that used to live as prose comments, now named tests."""

    def test_ping_never_resurrects_dismissed(self):
        v = HudVisibility('controller-nav')
        v.decide(ViewLeft())                       # now dismissed
        self.assertEqual(v.decide(ControlTouched()), Decision.NOTHING)
        self.assertTrue(v.dismissed)               # still hidden

    def test_control_touched_pings_while_visible(self):
        v = HudVisibility('selection')             # shown
        self.assertEqual(v.decide(ControlTouched()), Decision.PING)
        self.assertFalse(v.dismissed)

    def test_region_hide_does_not_reburst(self):
        v = HudVisibility('controller-nav')
        self.assertEqual(v.decide(RegionHide()), Decision.HIDE)
        self.assertTrue(v.dismissed)

    def test_burst_resyncs_dismiss_intent(self):
        v = HudVisibility('controller-nav')
        v.decide(ViewLeft())                       # dismissed=True
        self.assertTrue(v.dismissed)
        v.decide(DeviceFocus('nav'))               # a real burst
        self.assertFalse(v.dismissed)              # intent re-synced


class TestSummonTrigger(unittest.TestCase):
    """show-hud-on: summon (hud-summon-only-plan): hidden by default; only
    UserToggle or an explicit controller device-nav summons the HUD. A
    selection poll / mode press repaints only while the HUD is already shown
    (a visible HUD must never go stale), and stays silent while hidden."""

    def test_starts_dismissed_only_under_summon(self):
        self.assertTrue(HudVisibility('summon').dismissed)
        for trigger in ('selection', 'controller-nav'):
            self.assertFalse(HudVisibility(trigger).dismissed)

    def test_selection_while_hidden_is_silent(self):
        v = HudVisibility('summon')
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_SILENT_AND_HIDE)
        self.assertTrue(v.dismissed)

    def test_selection_always_silent_even_when_shown(self):
        # Mouse/track selection never shows a summon HUD — not even to repaint a
        # visible one. The Swift input monitor hides on that same click; a
        # repaint here would fight it across processes (hud-input-autohide-plan).
        v = HudVisibility('summon')
        v.decide(UserToggle())               # summoned -> shown
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_SILENT_AND_HIDE)
        self.assertTrue(v.dismissed)

    def test_mode_change_while_hidden_is_silent(self):
        # Under summon a mode press must not summon the HUD.
        v = HudVisibility('summon')
        self.assertEqual(v.decide(ModeChange()), Decision.EMIT_SILENT_AND_HIDE)
        self.assertTrue(v.dismissed)

    def test_mode_change_while_shown_repaints(self):
        v = HudVisibility('summon')
        v.decide(UserToggle())
        self.assertEqual(v.decide(ModeChange()), Decision.EMIT_BURST)

    def test_nav_summons(self):
        v = HudVisibility('summon')
        self.assertEqual(v.decide(DeviceFocus('nav')), Decision.EMIT_BURST)
        self.assertFalse(v.dismissed)

    def test_toggle_flips_from_startup_hidden(self):
        v = HudVisibility('summon')
        self.assertEqual(v.decide(UserToggle()), Decision.EMIT_BURST)
        self.assertEqual(v.decide(UserToggle()), Decision.HIDE)

    def test_nav_summons_even_in_clip_view(self):
        v = HudVisibility('summon')
        v.decide(ClipViewChanged(visible=True))
        self.assertEqual(v.decide(DeviceFocus('nav')), Decision.EMIT_BURST)

    def test_toggle_summons_even_in_clip_view(self):
        v = HudVisibility('summon')
        v.decide(ClipViewChanged(visible=True))
        self.assertEqual(v.decide(UserToggle()), Decision.EMIT_BURST)

    def test_selection_in_clip_view_is_silent_even_if_shown(self):
        # Summoned inside clip view, then a mouse selection: the clip gate wins.
        v = HudVisibility('summon')
        v.decide(ClipViewChanged(visible=True))
        v.decide(UserToggle())               # shown, clip gate still active
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_SILENT_AND_HIDE)

    def test_view_left_hides(self):
        v = HudVisibility('summon')
        v.decide(UserToggle())
        self.assertEqual(v.decide(ViewLeft()), Decision.HIDE)
        self.assertTrue(v.dismissed)


class TestClipViewChanged(unittest.TestCase):
    """The Detail/Clip gate (absorbed from hide-hud-in-clip-view-plan), for
    every trigger: entering hides, leaving clears the gate without re-showing,
    and while the gate is up selection/mode/region bursts go silent."""

    def test_entering_clip_view_hides_under_every_trigger(self):
        for trigger in ('selection', 'controller-nav', 'summon'):
            v = HudVisibility(trigger)
            self.assertEqual(v.decide(ClipViewChanged(visible=True)), Decision.HIDE)
            self.assertTrue(v.dismissed)
            self.assertTrue(v.clip_view_active)

    def test_leaving_clip_view_never_reshows(self):
        v = HudVisibility('selection')
        v.decide(ClipViewChanged(visible=True))
        self.assertEqual(v.decide(ClipViewChanged(visible=False)), Decision.NOTHING)
        self.assertFalse(v.clip_view_active)
        self.assertTrue(v.dismissed)   # hidden until the next normal trigger

    def test_selection_burst_suppressed_while_clip_open(self):
        for trigger in ('selection', 'controller-nav'):
            v = HudVisibility(trigger)
            v.decide(ClipViewChanged(visible=True))
            self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_SILENT_AND_HIDE)

    def test_mode_change_suppressed_while_clip_open(self):
        v = HudVisibility('selection')
        v.decide(ClipViewChanged(visible=True))
        self.assertEqual(v.decide(ModeChange()), Decision.EMIT_SILENT_AND_HIDE)

    def test_region_commit_suppressed_while_clip_open(self):
        v = HudVisibility('selection')
        v.decide(ClipViewChanged(visible=True))
        self.assertEqual(v.decide(RegionCommit()), Decision.EMIT_SILENT_AND_HIDE)

    def test_nav_overrides_clip_view(self):
        # Explicit controller device-nav is clear user intent — show anyway.
        for trigger in ('selection', 'controller-nav'):
            v = HudVisibility(trigger)
            v.decide(ClipViewChanged(visible=True))
            self.assertEqual(v.decide(DeviceFocus('nav')), Decision.EMIT_BURST)

    def test_selection_resumes_after_leaving_clip_view(self):
        v = HudVisibility('selection')
        v.decide(ClipViewChanged(visible=True))
        v.decide(ClipViewChanged(visible=False))
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_BURST)


class TestFineTrace(unittest.TestCase):
    """decide() emits a trace line through the injected `fine` callback capturing
    event -> dismissed-before -> decision -> dismissed-after. This is the single
    most important diagnostic line for both HUD reliability bugs; it must never
    alter the decision and must be silent when no callback is wired."""

    def test_decide_unchanged_without_fine_callback(self):
        v = HudVisibility('controller-nav')
        # No fine callback wired: behaviour is identical, no crash.
        self.assertEqual(v.decide(DeviceFocus('selection')),
                         Decision.EMIT_SILENT_AND_HIDE)

    def test_decide_emits_trace_with_event_and_decision(self):
        lines = []
        v = HudVisibility('controller-nav', fine=lines.append)
        v.decide(DeviceFocus('selection'))
        self.assertEqual(len(lines), 1)
        line = lines[0]
        # The decisive facts: event kind, the decision, and the dismissed flip.
        self.assertIn('DeviceFocus', line)
        self.assertIn('selection', line)
        self.assertIn('emit_silent_and_hide', line)
        self.assertIn('dismissed', line)

    def test_fine_does_not_change_decision(self):
        lines = []
        v = HudVisibility('controller-nav', fine=lines.append)
        self.assertEqual(v.decide(DeviceFocus('nav')), Decision.EMIT_BURST)
        self.assertFalse(v.dismissed)


if __name__ == "__main__":
    unittest.main()
