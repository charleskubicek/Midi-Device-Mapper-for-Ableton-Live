"""Intech Grid RGB-LED feedback sink.

Rides the device-focus burst — same seam as `Ec4Client` and the HUD — but instead
of text/UDP it emits a single batched SysEx to the Grid's MIDI RX carrying a dense
48-slot RGB frame (32 pots + 16 buttons). The Grid-side Lua (`self.sysexrx_cb`,
see `live_surfaces/grid/grid_led_handler.lua`) parses it and drives each element's
LED via `glc`. See grid-po16-synth-surface-plan §F.

Per slot:
  * hue    = the slot's zone colour (`snapshot.zone_colors` hex6); unmapped => off.
  * bright = the slot's live value normalised over vmin..vmax, floored to
             MAPPED_FLOOR so a mapped-but-low pot / off button stays visibly dim
             rather than reading as unmapped.
RGB is pre-multiplied (hue x brightness) and scaled 8-bit -> 7-bit; the Lua scales
back up for `glc`. The frame is DENSE every burst, so focusing a non-zoned device
(empty zone_colors) emits all-off and clears the previous synth's tint.

Transport is `manager._send_midi` (the surface's own MIDI out == the Grid), exactly
like `Ec4Client`.
"""
import logging

logger = logging.getLogger("grid-led-client")

# ---- Grid LED SysEx v1 framing (see module docstring) -----------------------
SYSEX_START = 0xF0
NON_COMMERCIAL_ID = 0x7D   # SysEx "non-commercial / educational" manufacturer id
LED_CMD = 0x4C             # 'L' — set-LEDs command
VERSION = 0x01
SYSEX_END = 0xF7

NUM_DIALS = 32             # grid-2 + grid-3 pots, wire_idx 0..31
NUM_BUTTONS = 16           # grid-1 buttons, wire_idx 0..15
NUM_SLOTS = NUM_DIALS + NUM_BUTTONS

# Mapped-but-dark floor: keeps a mapped slot at its minimum value visibly lit so
# it never reads as an unmapped (fully off) slot. Tuned during LED bring-up.
MAPPED_FLOOR = 0.15

OFF = [0, 0, 0]


def _normalise(payload):
    """Value in [0, 1] over vmin..vmax, clamped. Degenerate range => full."""
    lo, hi = payload.vmin, payload.vmax
    if hi == lo:
        return 1.0
    frac = (payload.value - lo) / (hi - lo)
    return 0.0 if frac < 0.0 else 1.0 if frac > 1.0 else frac


def _rgb7(hexv, payload):
    """Pre-multiplied, 7-bit-safe [r, g, b] for one slot. `hexv` is a 6-char hex
    zone colour or None (=> off); `payload` is the slot's SlotPayload or None."""
    if not hexv:
        return list(OFF)
    r = int(hexv[0:2], 16)
    g = int(hexv[2:4], 16)
    b = int(hexv[4:6], 16)
    bright = MAPPED_FLOOR + (1.0 - MAPPED_FLOOR) * _normalise(payload) if payload else MAPPED_FLOOR
    # scale by brightness, then 8-bit -> 7-bit (>>1) to stay inside SysEx data range.
    return [(int(c * bright)) >> 1 for c in (r, g, b)]


class GridLedClient:
    def __init__(self, manager):
        self._manager = manager

    def on_burst(self, snapshot):
        """Emit the dense 48-slot RGB frame for this device-focus burst. Fires on
        suppressed-HUD bursts too — LEDs are persistent device state, not the
        transient HUD."""
        colours = {(kind, wire): hexv for kind, wire, hexv in snapshot.zone_colors}
        dials = {wire: p for wire, p in snapshot.dials}
        buttons = {wire: p for wire, p in snapshot.buttons}

        body = []
        for i in range(NUM_DIALS):
            body += _rgb7(colours.get(('dial', i)), dials.get(i))
        for i in range(NUM_BUTTONS):
            body += _rgb7(colours.get(('button', i)), buttons.get(i))

        msg = ([SYSEX_START, NON_COMMERCIAL_ID, LED_CMD, VERSION]
               + body + [SYSEX_END])
        try:
            self._manager._send_midi(tuple(msg))
        except Exception as e:
            # Route through the surface log so a bad send path is visible in
            # tail_logs.sh, mirroring Ec4Client.
            try:
                self._manager.log_message(f"GridLedClient.on_burst failed: {e}")
            except Exception:
                logger.error(f"GridLedClient.on_burst: {e}")

    def on_hide(self):
        """No-op: LEDs are persistent physical state, not tied to HUD dismissal.
        (Kept for feedback-sink interface symmetry; `hide()` never fans to sinks.)"""
        pass


class NullGridLedClient:
    def on_burst(self, snapshot): pass
    def on_hide(self): pass
