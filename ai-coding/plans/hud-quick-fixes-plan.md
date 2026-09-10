# HUD quick fixes plan

Five reported defects on the `ck_grid` surface's HUD. Four are code; one is a
stale build artifact.

## 1. The shift button has no label

**Symptom.** `mode-button: grid-4:4::1` (button wire index 28) renders as the
empty-slot sentinel in every mode.

**Cause.** `hud_layout.collect_mode_labels` walks a mode's *mappings* only. The
mode-button is not a mapping — it lives on `ModeGroupWithMidi.mode_button` — so
no label pair is ever produced for its coord.

**Fix.** In `gen.py`, after `mode_hud_labels` is built, resolve the mode-button's
coord with `find_wire_index` and add it to **every** mode's dict with
`setdefault` (a real mapping on that coord must still win — it never should be
there, but the FSM breaks loudly if it is, and a silent label clobber would hide
that). Label: `Shift` for `ModeType.Shift`, `Mode` otherwise. No glyph.

Skipped when `hud: device_only`/`off`, exactly like the rest of the labels.

## 2. Labels must be capitalised

**Symptom.** `dev on/off`, `track left`, `move_loop_left`, `send 1`.

**Fix.** One presentation rule at one chokepoint: `hud_protocol.display_label`,
applied to the `name` field in `encode_slot` and `encode_update`. That covers
static mode labels *and* live device-parameter names in a single place.

Rule:

- split on whitespace, `/`, `_`, `-`, keeping the separators
- `_` becomes a space (so `move_loop_left` -> `Move Loop Left`; item 4 is the
  same intent — stop showing raw identifiers)
- upper-case the first letter of a run **only when the whole run is lowercase**

The lowercase-only guard is what protects live Live names: `LFO Rate`, `dB`,
`EQ8`, `Osc 1` all survive unchanged. `str.title()`/Swift `.capitalized` would
mangle every one of them, which is why this is done on the Python side and not
in the SwiftUI render.

The empty-slot sentinel (empty name) stays empty.

## 3. `on-off: grid-4:3` does nothing

**Cause.** `is_on_off` is set on the model but *dropped* at codegen:
`_plain_encoder_template` emits the ordinary
`device_parameter_action(device, 0, ...)`. At runtime that goes through
`ParamResolver.resolve_encoder(device, 0)`, which computes
`slot_in_page = c_idx - 1 = -1` and indexes `encoders[-1]` — i.e. the press
drives the **last Best-of-Bank parameter** instead of the device on/off switch
(or resolves to `None` and silently no-ops on a zoned synth).

Live parameter 0 is not an encoder slot, so it must not travel the encoder
resolver at all.

**Fix.** Dedicated path end to end:

- `gen_code._on_off_template` emits `self.device_on_off_action(device, midi_no,
  value, fn_name)` for `mm.is_on_off`
- template `main_component.device_on_off_action` delegates to
  `Helpers.device_on_off_action`
- `Helpers.device_on_off_action` takes `device.parameters[0]` directly, applies
  the same `should_act_on_edge` press-once guard as the toggle branch, flips
  min<->max, then `parameter_updated(RealParameter(p, 'On/Off'), 0)` (which
  already skips the dial `UPDATE` for parameter 0 and still emits OSC) and a
  `PING` so the toggle keeps the HUD alive.

Cannot be verified outside Ableton — this is a generation + unit-tested change;
the user redeploys and confirms on hardware.

## 4. `hud_toggle` should read "Hide HUD"

**Fix.** Populate `hud_name` for reserved builtins where they are declared
(`model_functions.RESERVED_BUILTIN_FUNCTIONS` -> a name map), so the existing
`mm.hud_name or mm.function_name` in `hud_layout` needs no change and there is
no second dispatch table.

## 5. HUD hides after ~7s in some cases, never in others

**Not a code bug — the running HUD binary is stale.**

- `ableton_hud/AbletonHUD.app/Contents/MacOS/AbletonHUD` is dated 21 Jul and is
  the running PID.
- `withTimeInterval: 7` was replaced by the configurable
  `DeviceState.idleTimeoutSeconds` in a708457, dated 25 Jul.
- The bundle contains no `IDLETIMEOUT` string, so it cannot receive the
  surface's `hud-idle-timeout: 120` and is hard-coded to 7s.

"Sometimes it stays forever" is `HUDOverlayManager`'s `chrome.$isMouseOver`
branch: hovering the panel invalidates the dismiss timer and only re-arms on
mouse-exit.

**Fix.** Rebuild: `ableton_hud/./create-app-bundle.sh` (or `./restart.sh`).

**Caveat to report.** This surface is `show-hud-on: summon`, which sends
`AUTOHIDE|1`; the Swift `GlobalInputMonitor` still sticky-dismisses on any click
or keystroke in Ableton. That is configured behaviour, not the timer. To tell
them apart: `touch /tmp/ableton_hud_fine`, reproduce, read
`/tmp/ableton_hud_debug.log` — `stickyDismiss(idleTimer)` is the timer, anything
from the input monitor is autohide.

## Test plan (failing first)

- `tests/test_hud_protocol.py` — `display_label` unit table; `encode_slot` /
  `encode_update` apply it; empty sentinel unchanged.
- `tests/test_hud_layout.py` — `dev on/off` pair unchanged at the label level
  (capitalisation is a wire concern, not a label-dict concern).
- `tests/test_gen.py` (or a new `tests/test_mode_button_label.py`) — the
  mode-button coord carries `Shift` in every mode's `mode_hud_labels`.
- `tests/test_hud_toggle.py` — the built midi map's `hud_name` is `Hide HUD`.
- `tests/test_device_on_off.py` — generated listener calls
  `device_on_off_action`, never `device_parameter_action(..., 0, ...)`; plus a
  resolver test pinning today's `resolve_encoder(device, 0)` misbehaviour so the
  bypass has a documented reason.
