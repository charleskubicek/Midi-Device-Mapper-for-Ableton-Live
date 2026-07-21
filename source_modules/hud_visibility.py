"""HUD visibility as one explicit, table-driven state machine (plan item R10).

"Is the HUD visible, and may this event show it?" used to be decided in six
scattered places (the suppress branch in the burst path, toggle_hud, the
mode-refresh, the app-view listeners, RegionState's HIDE/PING rules, and the
Swift sticky flag). Each carried a prose comment about a race it dodged.

`HudVisibility` is the single owner of that decision on the Python side. It
mirrors the Swift sticky-dismiss flag: `dismissed` is set by HIDE-style
outcomes and cleared by a real burst. `decide(event)` returns a `Decision` and
applies the state transition; `apply(decision)` is the one transition function
every production path goes through. It is pure (no Live, no sockets) so the
full event x policy matrix — including the three race invariants — is a
unit-tested table rather than comments spread across modules.

Wiring status: DeviceFocus, ModeChange, ClipViewChanged, ViewLeft and
RegionCommit are fired by HudPresenter/Helpers/the generated template. The
hud_toggle button is HUD-arbitrated (Swift owns the show-vs-hide decision) and
no longer fires a table event. RegionHide and ControlTouched encode
RegionState's and the listeners' rules but those call sites still own their
behaviour directly — routing them through this table is the deferred,
hardware-verified step of plan item R10.
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
class ViewLeft:
    """User navigated away from the device (doc-view switch, browser opened,
    detail/device-chain hidden) — the app-view listeners' dismiss."""


@dataclass(frozen=True)
class ClipViewChanged:
    """Detail/Clip visibility flipped (hud-summon-only-plan, absorbed from the
    clip-view plan). Entering clip view hides the HUD and gates later
    selection/mode/region bursts; leaving clears the gate without re-showing."""
    visible: bool


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
    def __init__(self, trigger, fine=None):
        # trigger: 'selection' (HUD follows Live's selected device),
        # 'controller-nav' (HUD only on explicit device-nav actions), or
        # 'summon' (hidden by default; only hud_toggle / device-nav shows it).
        # The lc_parks compositor needs selection-driven focus to always show
        # (a HIDE-on-select races the parks-driven combined COMMIT); gen.py
        # expresses that by forcing the compositor's trigger to 'selection'.
        self.trigger = trigger
        # Mirrors the Swift sticky dismissed flag. A summon surface boots
        # hidden — nothing shows until the user asks.
        self.dismissed = (trigger == 'summon')
        # Detail/Clip is open: selection/mode/region bursts stay silent until the
        # user leaves clip view (nav and toggle still override). The browser and
        # other non-device views are handled by the Swift input monitor now
        # (hud-input-autohide-plan), not by enumerating view listeners here.
        self.clip_view_active = False
        # Gated trace sink. Off by default so unit tests and pre-flag
        # surfaces stay silent.
        self._fine = fine or (lambda msg: None)

    def decide(self, event) -> Decision:
        before = self.dismissed
        decision = self._classify(event)
        self.apply(decision)
        # The single most important diagnostic line for both HUD bugs: what
        # fired, under which trigger, what it decided, and the dismissed flip.
        self._fine(
            f"[vis] decide event={type(event).__name__}({getattr(event, 'source', '')}) "
            f"trigger={self.trigger} dismissed={before}->{self.dismissed} "
            f"clip={self.clip_view_active} decision={decision.value}"
        )
        return decision

    def apply(self, decision):
        """The single state-transition function. Callers that already hold a
        Decision (the burst path) apply it here instead of writing `dismissed`
        directly, so every transition lives in one place."""
        if decision is Decision.EMIT_BURST:
            self.dismissed = False
        elif decision in (Decision.EMIT_SILENT_AND_HIDE, Decision.HIDE):
            self.dismissed = True

    def _classify(self, event) -> Decision:
        if isinstance(event, ClipViewChanged):
            # Entering hides + gates; leaving clears the gate but never
            # auto-re-shows (the HUD stays hidden until the next normal trigger).
            self.clip_view_active = event.visible
            return Decision.HIDE if event.visible else Decision.NOTHING
        if isinstance(event, DeviceFocus):
            # Explicit controller device-nav is a summon: it overrides both the
            # summon-hidden default and any view gate (clear user intent).
            if event.source == 'nav':
                return Decision.EMIT_BURST
            if self.trigger == 'summon':
                # Mouse/track selection never shows a summon HUD. Always silent
                # (not "repaint if shown"): under summon the Swift input monitor
                # hides on the very click that changed the device, so a repaint
                # here would fight it across processes — and syncing to dismissed
                # keeps the Python mirror consistent with the monitor's hide.
                return Decision.EMIT_SILENT_AND_HIDE
            # selection poll under selection / controller-nav. While a clip is
            # open the HUD stays hidden (clip-view gate suppression).
            if self.clip_view_active:
                return Decision.EMIT_SILENT_AND_HIDE
            if self.trigger == 'selection':
                return Decision.EMIT_BURST
            return Decision.EMIT_SILENT_AND_HIDE
        if isinstance(event, ModeChange):
            if self.trigger == 'summon':
                # A mode press must not summon a hidden HUD; repaint only a
                # visible one.
                if self.dismissed or self.clip_view_active:
                    return Decision.EMIT_SILENT_AND_HIDE
                return Decision.EMIT_BURST
            if self.clip_view_active:
                return Decision.EMIT_SILENT_AND_HIDE
            return Decision.EMIT_BURST
        if isinstance(event, ViewLeft):
            return Decision.HIDE
        if isinstance(event, RegionCommit):
            if self.clip_view_active:
                return Decision.EMIT_SILENT_AND_HIDE
            return Decision.EMIT_BURST
        if isinstance(event, RegionHide):
            return Decision.HIDE
        if isinstance(event, ControlTouched):
            # A ping must never resurrect a dismissed HUD.
            return Decision.NOTHING if self.dismissed else Decision.PING
        return Decision.NOTHING
