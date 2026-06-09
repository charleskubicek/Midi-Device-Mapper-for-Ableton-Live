"""HUD visibility as one explicit, table-driven state machine (plan item R10).

"Is the HUD visible, and may this event show it?" used to be decided in six
scattered places (the suppress branch in the burst path, toggle_hud, the
mode-refresh, the app-view listeners, RegionState's HIDE/PING rules, and the
Swift sticky flag). Each carried a prose comment about a race it dodged.

`HudVisibility` is the single owner of that decision on the Python side. It
mirrors the Swift sticky-dismiss flag: `dismissed` is set by HIDE-style
outcomes and cleared by a real burst. `decide(event)` returns a `Decision` and
applies the state transition. It is pure (no Live, no sockets) so the full
event x policy matrix — including the three race invariants — is a unit-tested
table rather than comments spread across modules.
"""
from dataclasses import dataclass
from enum import Enum


class Decision(Enum):
    EMIT_BURST = 'emit_burst'                       # show the HUD; clears dismissed
    EMIT_SILENT_AND_HIDE = 'emit_silent_and_hide'   # data to OSC/feedback sinks only; HUD gets HIDE; sets dismissed
    HIDE = 'hide'                                    # sticky-hide; sets dismissed
    PING = 'ping'                                    # keepalive / dismiss-timer reset; no state change
    NOTHING = 'nothing'                              # no-op


# ---- events -----------------------------------------------------------------

@dataclass(frozen=True)
class DeviceFocus:
    """A device became focused. source='nav' is an explicit controller device-nav
    action; source='selection' is Live's selection poll (mouse / track select)."""
    source: str  # 'nav' | 'selection'


@dataclass(frozen=True)
class ModeChange:
    """goto_mode swapped the active binding set — the HUD always repaints."""


@dataclass(frozen=True)
class UserToggle:
    """The hud_toggle button: flip between shown and sticky-hidden."""


@dataclass(frozen=True)
class ViewLeft:
    """User navigated away from the device (doc-view switch, browser opened,
    detail/device-chain hidden) — the app-view listeners' dismiss."""


@dataclass(frozen=True)
class RegionCommit:
    """The lc_parks secondary region changed and a combined burst must re-emit."""


@dataclass(frozen=True)
class RegionHide:
    """The lc_parks region asked the HUD to hide."""


@dataclass(frozen=True)
class ControlTouched:
    """A live parameter change (knob turn) — the per-listener keepalive ping."""


class HudVisibility:
    def __init__(self, trigger, combined=False):
        # trigger: 'selection' (HUD follows Live's selected device) or
        # 'controller-nav' (HUD only on explicit device-nav actions).
        self.trigger = trigger
        # combined=True is the lc_parks compositor: it forces selection-driven
        # focus to show, because a HIDE-on-select would race the parks-driven
        # combined COMMIT and make values flash then vanish.
        self.combined = combined
        # Mirrors the Swift sticky dismissed flag.
        self.dismissed = False

    def decide(self, event) -> Decision:
        decision = self._classify(event)
        if decision is Decision.EMIT_BURST:
            self.dismissed = False
        elif decision in (Decision.EMIT_SILENT_AND_HIDE, Decision.HIDE):
            self.dismissed = True
        return decision

    def _classify(self, event) -> Decision:
        if isinstance(event, DeviceFocus):
            if event.source == 'nav':
                return Decision.EMIT_BURST
            # selection poll: show unless the surface is controller-nav-only
            # (and not the combined compositor, which always shows on select).
            if self.combined or self.trigger == 'selection':
                return Decision.EMIT_BURST
            return Decision.EMIT_SILENT_AND_HIDE
        if isinstance(event, ModeChange):
            return Decision.EMIT_BURST
        if isinstance(event, UserToggle):
            # Flip: shown -> hide, hidden -> show.
            return Decision.EMIT_BURST if self.dismissed else Decision.HIDE
        if isinstance(event, ViewLeft):
            return Decision.HIDE
        if isinstance(event, RegionCommit):
            return Decision.EMIT_BURST
        if isinstance(event, RegionHide):
            return Decision.HIDE
        if isinstance(event, ControlTouched):
            # A ping must never resurrect a dismissed HUD.
            return Decision.NOTHING if self.dismissed else Decision.PING
        return Decision.NOTHING
