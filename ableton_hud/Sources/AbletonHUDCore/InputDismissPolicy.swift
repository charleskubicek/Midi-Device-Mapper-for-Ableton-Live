/// Pure decision for the input-driven auto-hide (hud-input-autohide-plan): given
/// a mac mouse/keyboard event, should the HUD sticky-dismiss? Extracted from the
/// AppKit `GlobalInputMonitor` so the rule is unit-testable without AppKit/TCC.
///
/// Rule: hide only when the surface asked for it (`enabled`, i.e. a summon
/// surface sent `AUTOHIDE|1`) AND Ableton is the frontmost app (the user is
/// working in Live, not another app) AND the event isn't over the HUD's own
/// panel. The spike showed a global monitor never even receives the HUD's own
/// clicks, so `overHud` is belt-and-suspenders.
public enum InputDismissPolicy {
    public static func shouldDismiss(enabled: Bool, abletonFrontmost: Bool, overHud: Bool) -> Bool {
        enabled && abletonFrontmost && !overHud
    }
}
