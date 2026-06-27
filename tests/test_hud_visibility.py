"""The HUD visibility decision table (R10). Encodes today's exact behaviour,
warts included (suppressed-selection sends HIDE; mode change always shows), so
the table is the executable spec the wiring must preserve."""
import unittest

from source_modules.hud_visibility import (
    HudVisibility, Decision,
    DeviceFocus, ModeChange, UserToggle, ViewLeft, RegionCommit, RegionHide, ControlTouched,
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
