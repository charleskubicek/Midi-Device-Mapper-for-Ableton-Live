# Drum Rack Mapping — Plan

## REVISION 2026-07-18 — fold into `device` + mapping precedence

Supersedes the "new `drum-rack-device` type" framing below. Decided with the user:

- **No new mapping type.** The existing `device` mapping gains three optional blocks —
  `pads:` / `sequencer:` / `velocities:` — that are inert unless the focused device is a
  drum rack (`can_have_drum_pads`). On any other device, `device` is unchanged.
- **Precedence via a single dispatching listener.** A drum block may share controls with a
  macro/switch role (e.g. `velocities:` on the same knobs as `encoders:`). Codegen emits
  ONE listener per shared control that branches at call time: drum rack focused → drum
  action, else the device macro/switch action. No two-listeners-per-element.
- **Clash validator** still catches cross-mapping conflicts; it now ignores a control that
  overlaps *itself within one mapping* (that self-overlap is the intentional precedence
  signal). De-dupe each mapping's coords before the cross-mapping check.
- **Static HUD labels** on shared cells still show macro names on a drum rack in V1; live
  step state comes via the separate `DRUM` message. Runtime label-swap-by-device-type is a
  follow-up.
- **Hardware assumptions (enforced/noted):** the `sequencer:` needs momentary buttons
  (toggle hardware alternates 127/0 so only every second tap registers); a `sequencer:` on
  a `button-behaviour: toggle` controller is a gen-time `GenError`. `velocities:` assume
  absolute encoders (map 0..127 → velocity 1..127); relative encoders are out of scope for
  V1. (The hold-A-tap-B long-note gesture was removed 2026-07-19 — see follow-up.)
- **HUD follow-ups:** `set_velocity` does not yet emit a `DRUM` message (only `step_event`
  does) — close when the Swift HUD side lands. Shared cells still show macro labels on a
  drum rack (runtime label-swap-by-device-type is the follow-up).
- **Pad SELECTION now wired (2026-07-18):** a `pads:` button selects the drum on press
  (`DrumRackController.select_pad` → sets the override index + mirrors to
  `view.selected_drum_pad`), so the sequencer edits the tapped drum. Shares controls with a
  device switch via the same dispatch pattern. `ck_grid`: main mode grid-1 = pad select,
  shift mode grid-1 = sequencer, grid-2 = velocity; the selection persists across the mode
  switch. UNVERIFIED: the button→pad index mapping assumes `view.drum_pads` order — if the
  physical orientation is flipped/rotated on the real rack, add an index transform.
- **Deferred seam:** pad AUDITION only (Live spike: no-sound confirmed — a `ButtonElement`
  consumes the note, so making the pad sound needs a separate re-emit/translation), and the
  Swift HUD `DRUM` rendering.

The runtime `DrumRackController` (`source_modules/drum_rack.py`), the `DRUM` HUD message,
and all step/velocity/clip editing already built stay as-is; only the model/codegen wiring
moves from a separate type into `device`.

---

## Summary (original — kept for context; see REVISION above)

New mapping type `drum-rack-device` that extends the existing `device` mapping. When the
focused device is a Drum Rack it additionally provides:

1. **Pads** — a range of buttons that trigger the drum pads in the rack's visible 4×4 bank.
2. **Step sequencer** — a range of 8 or 16 buttons (typically in a shift mode) that toggle
   sixteenth notes for the last-tapped pad in the detail clip.
3. **Velocity encoders** — a range of encoders that set the velocity of the note at the
   corresponding step.

The inherited `device` behaviour (`encoders:`, `encoder-list:`, `on-off:`, `button:`) works
exactly as in a plain `device` mapping, so drum-rack macros can sit on knobs as usual.

## Decisions (clarified 2026-07-17)

- **Pad bank**: pads map to the rack's currently *visible* 4×4 bank (follows Live's own
  pad-bank scrolling), not fixed notes. Button→pad layout mirrors Live: bottom row of the
  grid = lowest 4 notes of the bank (verify grid-1 coordinate ordering during impl).
- **Pad tap**: triggers the sound *and* selects the pad — it becomes the "last tapped" pad
  the sequencer/velocity controls edit. Also set `drum_rack.view.selected_drum_pad` so
  Live's UI tracks the selection.
- **Target clip**: the detail clip (`song.view.detail_clip`). If there is no MIDI detail
  clip, create a 1-bar MIDI clip in the highlighted session slot on the selected track and
  edit that.
- **Steps**: V1 edits only bar 1 at sixteenth resolution. 16 buttons = steps 1–16;
  8 buttons = steps 1–8 (first half-bar, still sixteenths). No paging in V1. Any other
  button count is a generation error.
- **Toggle semantics**: tap a step → if a note for the selected pad starts in that step's
  window, delete it; otherwise add one (duration = 1/16 bar = 0.25 beats, default
  velocity 100).
- **Long notes**: ~~hold step A, tap step B → one note A..B~~ REMOVED 2026-07-19
  (see follow-up below) — the gesture didn't work in practice. Every step tap is now a
  plain single-step toggle.
- **Velocity encoders**: absolute — encoder *i* sets the velocity (1–127) of the existing
  note at step *i* for the selected pad. Turning an encoder on an empty step does nothing.
- **Non-drum-rack device focused**: the whole mapping (including the inherited encoder
  block) is inert. Plain `device` mappings elsewhere continue to handle other devices.
  Detection: `device.can_have_drum_pads` / class_name `DrumGroupDevice` on the focused
  device (same focus path main_component already uses for the HUD).
- **Feedback (V1)**: HUD only — push the selected pad name and the 16-step pattern.
  No grid LEDs for steps or pad selection in V1 (follow-up).

## Config schema

`pads` / `sequencer` / `velocities` take just a `range:` — step/pad index is implied by
position within the range (no `slots:` list, unlike device encoder blocks). `encoders:`
keeps full device-mapping semantics (`parameters:` or `slots:`).

```
mappings:
    -
        type: drum-rack-device
        track: selected
        device: selected
        mappings:
            encoders:                 # inherited device-mapping block (optional)
                range: grid-2:1-16
                parameters: 1-16
            pads:                     # 16 buttons -> visible 4x4 bank
                range: grid-1:1-16
            velocities:               # 8 or 16 encoders -> per-step velocity
                range: grid-3:1-16

modes / shift mode:
    -
        type: drum-rack-device
        track: selected
        device: selected
        mappings:
            sequencer:                # 8 or 16 buttons -> step toggles
                range: grid-1:1-16
```

Validation at gen time: `pads` resolves to exactly 16 buttons; `sequencer` to 8 or 16;
`velocities` to 8 or 16 encoders. Pads/sequencer must be button-type controls,
velocities knob-type.

## Live API notes

- Read notes: `clip.get_notes_extended(from_pitch, pitch_span, from_time, time_span)`
- Add: `clip.add_new_notes([MidiNoteSpecification(...)])`
- Delete: `clip.remove_notes_extended(from_pitch, pitch_span, from_time, time_span)`
- Velocity edit: mutate results of `get_notes_extended` then
  `clip.apply_note_modifications(notes)` — preserves note IDs / per-note data.
- Step *i* window: `[i × 0.25, (i+1) × 0.25)` beats; "note at step" = note with matching
  pitch whose start falls in the window.
- Visible bank: drum rack `view` scroll position + `drum_pads` (128 entries) → 16 pad
  notes for the current bank.
- Clip create: `clip_slot.create_clip(4.0)` on the highlighted slot when no detail clip.

**Technical risk — pad audition.** Remote Scripts have no direct "play this pad" API.
Candidate approaches, to be verified first (spike + `./bin/tail_logs.sh`):
1. Note forwarding + translation (what Push's DrumGroupComponent does): grab the pad
   buttons via `Live.MidiMap.forward_midi_note`, and install a note translation so the
   hardware note is re-emitted as the pad's note on the track (`c_instance` translation
   API). Script still sees press/release for selection.
2. If translation proves unavailable in our setup: keep selection on the grabbed note and
   accept select-only pads for V1 (degrade gracefully; flag to user).

## Implementation (TDD)

1. **Model + parsing** (`model_drum_rack.py`, failing tests first in
   `tests/test_drum_rack.py`):
   `DrumRackDeviceV2` extending the `DeviceV2` shape with optional `pads` / `sequencer` /
   `velocities` blocks; `DrumRackWithMidi` extending `DeviceWithMidi` with
   `pad_maps` / `step_maps` / `velocity_maps` (each a `MidiCoords` + index). Count
   validation (16 / 8-or-16) with `GenError`.
2. **Codegen** (`gen_code.py` + `template_to_code` dispatch): reuse the device codegen for
   the inherited parts; new listener code for pads (press+release), steps (press+release,
   for the hold gesture), and velocity CCs. All runtime logic lives in a source module —
   generated code just wires listeners to it.
3. **Runtime module** (`source_modules/drum_rack.py`): a `DrumRackController` class
   holding selected-pad state, pressed-step state (for long notes), step math, and the
   clip read/create/toggle/velocity operations. Unit-test with fake clip/device objects
   (pure-Python, no Live imports at module top level — follow existing source_modules
   conventions).
4. **Focus integration** (`templates/surface_name/modules/main_component.py`): on device
   focus change (same path that feeds the HUD), activate/deactivate the drum-rack
   controller based on `can_have_drum_pads`; inert otherwise.
5. **HUD**: extend the protocol with a drum message (e.g. `DRUM|<pad name>|<16-char
   pattern>`), sent on pad select and after every step/velocity edit. Update
   `hud_protocol.md`, `source_modules/hud_protocol.py` + tests, and the Swift side
   (`WireProtocol.swift`, `DeviceState.swift`, `HUDView.swift`). Note: button-slot
   emission rules are already flagged unstable in hud_protocol.md — keep the drum message
   independent of the SLOT path.
6. **Integration**: generate a grid mapping using the schema above; assert the generated
   surface compiles and wires all three ranges; add the mapping to `ck_grid_full_nav.nt`
   (or a test surface) for manual verification.
7. **Manual verify**: user redeploys + restarts Live; confirm via `./bin/tail_logs.sh`,
   starting with the pad-audition spike (step 0 in practice — do this before building the
   sequencer on top).

## Out of scope (follow-ups)

- Step paging for clips longer than 1 bar.
- Grid LEDs for step pattern / selected pad / playhead.
- Non-4/4 signatures (V1 assumes a 4-beat bar).
- Note-repeat, choke feedback, pad-bank scrolling from the controller.

## Follow-up: arrangement-mode clip creation (2026-07-18)

When the user sequences with no MIDI detail clip focused, clip creation now
branches on the focused document view (`application().view.focused_document_view`):

- **Session view** (unchanged): create a fresh 1-bar clip in the highlighted
  clip slot.
- **Arrangement view**: create ONE looping MIDI clip on the selected track at the
  arrangement loop start (`song.loop_start`), spanning the whole arrangement loop
  (`song.loop_length`, floored to at least one bar), with `looping = True` and
  `loop_end = BAR_BEATS` so its content repeats every bar. This is the API
  equivalent of the manual Ableton gesture "make a 1-bar clip, enable loop, drag
  the right edge to fill the loop". Because it is a **single clip** (not tiled
  independent copies), every step/velocity edit updates all repetitions — there
  is no divergence to keep in sync (this is why the initial tiling design was
  dropped). The clip is set as `detail_clip`, which also makes the operation
  idempotent (subsequent taps resolve it via `_detail_clip()`); a secondary guard
  scans `track.arrangement_clips` for a MIDI clip already anchored at loop_start.

Runtime seam covered by `TestDrumRackArrangementClip`.

**Needs runtime confirmation on deploy** (tests run against fakes, so they verify
the internal logic, not the real Live API behaviour). Recipe: set a 4-bar
arrangement loop, focus a drum rack, sequence one step, then check the created
clip in the arrangement.
- Expected: the clip visually spans the full 4 bars and the 1-bar pattern
  repeats.
- If it collapses to a single bar at the loop start, the loop brace and the
  clip's dragged-out extent are independent handles — set `clip.end_marker = span`
  after `loop_end` (one-line fix in `_arrangement_clip_for_edit`).
- `Track.create_midi_clip(start_time, arg3)` is assumed to be `(start_time,
  length)`; if arg3 is an end_time, pass `loop_start + span` instead.

## Follow-up: pad orientation flip (2026-07-19)

The controller numbers its 4x4 pad grid top-down (range index 0 = top-left), but
Live's drum bank (`visible_drum_pads`) is laid out bottom-up (index 0 = the
bottom-left pad, note 36). Selecting pad `i` used to index `visible_drum_pads[i]`
directly, so every controller pad hit the vertically-mirrored drum. Fixed with a
pure `bank_index_from_controller(index)` that flips rows (columns unchanged),
applied at both indexing sites via `_bank_pad`. Corners: controller top-left ->
Live top-left (note 48), controller bottom-left -> note 36. Covered by
`TestPadOrientationMapping` + regression tests in `TestDrumRackPadSelect`.

## Follow-up: long-note gesture removed (2026-07-19)

The hold-step-A + tap-step-B "long note" gesture (originally in `_on_step_press` /
`_on_step_release` / `_anchor_for` / `_create_long_note`, with `_pressed` state)
did not work in practice and was fully removed at the user's request. Every step
tap is now a plain single-step toggle: `step_event` toggles on the release edge
(value == 0). Overlapping presses just produce two independent one-step notes
(`TestDrumRackNoLongNote`).

The momentary-buttons requirement for `sequencer:` **stays** (gen-time `GenError`),
but its rationale is updated: toggle hardware alternates 127/0 so only every second
tap would register — the sequencer needs one clean edge per tap, independent of the
removed gesture. Codegen still forwards both edges (harmless; release is the acting
one). `set_velocity` and pad selection are unchanged.
