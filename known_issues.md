# Known Issues

Tracked gaps and rough spots. Nothing here is broken-broken — these are
deliberate scope cuts or asymmetries we've chosen not to fix yet.

---

## HUD: non-device slots show labels but not live values

**Status:** active
**Affects:** the floating HUD when the active mode binds physical controls
to anything other than device parameters (mixer / functions / transport /
track-nav / device-nav / parameter-pager).

After the Phase 2 mode-aware burst work, the HUD correctly *labels* every
slot in the current mode — e.g. shift mode on the LC XL shows
"Volume / Pan / Send 1 / Send 2 / Send 3" on the dials and the function
names ("rec_midi", "clip_extend", …) on the buttons. The mode-change burst
fires from `goto_mode()` so labels stay in sync with the active bindings.

What's *not* yet wired: the bar / needle on each non-device slot. Slots
emit a placeholder `SlotPayload(label, value=0, vmin=0, vmax=1)` at burst
time, so:

- A mixer-volume dial in shift mode shows the label "Volume" but the bar
  doesn't track the actual track volume.
- A mute button shows "Mute" but the LED-style fill doesn't reflect
  whether the track is currently muted.
- Function buttons that have no meaningful "current value" are unaffected
  (their bar always being 0 is correct).

Device parameters are unaffected — they continue to push real values
through the existing `parameter_updated` / `device_update` path.

### Why deferred

Wiring live values requires per-mapping-type code generation:

- A "read current value" closure per slot, calling the relevant Live API
  surface (`track.mixer_device.volume.value`, `song.is_playing`, etc.).
- Listeners on each of those properties so changes outside the burst push
  an `UPDATE` to the HUD — otherwise the bar would only refresh on mode
  change, not when the user actually moves a fader.

That listener-hookup work duplicates infrastructure that the device path
already has and is large enough to deserve its own design pass. We chose
to ship the labels-only fix first because it solves the immediately
visible bug (HUD showing the *wrong* mode's bindings) and leaves the
value-tracking work as a clean, isolated follow-up.

### What it would take to fix

- For each mapping type's `*WithMidi` model: a `value_reader_for(slot)`
  helper that returns Python source code reading the live value.
- For each mapping type: a `value_listener_for(slot)` helper that
  registers an Ableton Live property listener and calls
  `Remote.send_update('dial'|'button', wire_idx, …)`.
- Generated per-mode setup that installs those listeners on mode enter
  and removes them on mode exit (parallel to the existing
  `mode_*_add_listeners` / `remove_all_listeners` lifecycle).
- Tests pinning that `UPDATE|...` messages fire on Live property changes.

See `ai-coding/plans/lets-look-at-the-indexed-gadget.md` Phase 2 for
context, and the original options A / B / C discussion (this file is the
A → C delta).
