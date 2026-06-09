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

    def test_combined_compositor_forces_show_on_selection(self):
        # lc_parks: controller-nav primary, but combined=True must still show.
        v = HudVisibility('controller-nav', combined=True)
        self.assertEqual(v.decide(DeviceFocus('selection')), Decision.EMIT_BURST)


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
        v = HudVisibility('controller-nav', combined=True)
        self.assertEqual(v.decide(RegionHide()), Decision.HIDE)
        self.assertTrue(v.dismissed)

    def test_burst_resyncs_dismiss_intent(self):
        v = HudVisibility('controller-nav')
        v.decide(ViewLeft())                       # dismissed=True
        self.assertTrue(v.dismissed)
        v.decide(DeviceFocus('nav'))               # a real burst
        self.assertFalse(v.dismissed)              # intent re-synced


if __name__ == "__main__":
    unittest.main()
