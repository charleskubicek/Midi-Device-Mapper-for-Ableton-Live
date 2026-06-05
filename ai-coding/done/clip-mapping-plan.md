# Clip Mapping Plan

## Context

We want to edit Ableton **clip** attributes (gain, pitch, loop/markers, warping, etc.)
from the MIDI controller, with the HUD showing what is being edited. The original
draft (`ai-coding/plans/clip-mapping.md`) assumed clip and device mappings could
share the same encoders in a mode, with clip taking precedence — which is the
source of nearly all the complexity (runtime gating, auto-mode-swap FSM, burst
precedence, edits to existing device codegen).

**Decision (user):** clip controls must be **dedicated** — they may not share a
physical control with device/mixer/etc. mappings in the same mode. This collapses
the feature into a self-contained new mapping type, sized like `transport`/`functions`,
plus one genuinely new mechanism (relative-encoder stepping of scalar clip properties).

**Precedent:** Push's `pushbase/clip_control_component.py` (in
`~/oss/AbletonLive12_MIDIRemoteScripts`) does exactly this — listens to
`song.view.detail_clip`, splits behavior into `no_clip`/`midi`/`audio`, and steps
loop/marker/gain/pitch with relative encoders. We borrow its math and audio/midi split.

## Scope (v1)

- New `clip` mapping type: encoders + buttons that edit the currently-detailed clip.
- HUD: clip cells render live attribute names/values via a `detail_clip` burst,
  greyed when no clip is detailed. **Deferred:** auto-moving the HUD panel to the
  bottom of the Ableton window (Swift change, follow-up).

## Design

### Activation model — none needed (no FSM, no gating)

Clip controls are dedicated, always-bound listeners. Each clip listener resolves
`self.song().view.detail_clip` at call time:

```python
clip = self.song().view.detail_clip
if not self._helpers.liveobj_valid(clip):
    return
```

No mode swap, no `clip_focused` flag, **zero edits to existing device/mixer/button
codegen**. The "clip vs device" mutual exclusivity is now a layout fact (different
controls), not a runtime concern.

### Clip attribute set

Mapping keys in the `.nt` file (audio-only ones no-op on MIDI clips, see guards):

| Key | Control | Live API | Notes |
|-----|---------|----------|-------|
| `gain` | rel encoder | `clip.gain` | audio only; `clamp(gain + d*f, 0, 1)` |
| `pitch-coarse` | rel encoder | `clip.pitch_coarse` | audio only; `int(clamp(.. , -48, 48))` |
| `pitch-fine` | rel encoder | `clip.pitch_fine` | audio only |
| `loop-start` | rel encoder | `clip.loop_start` | beats; +/- step per detent |
| `loop-end` | rel encoder | `clip.loop_end` | beats |
| `start-marker` | rel encoder | `clip.start_marker` | beats |
| `end-marker` | rel encoder | `clip.end_marker` | beats |
| `looping` | button (toggle) | `clip.looping` | boolean on/off |
| `warping` | button (toggle) | `clip.warping` | boolean on/off; audio only |
| `duplicate-loop` | button | `clip.duplicate_loop()` | method |
| `sync-loop-and-markers` | button | set `start_marker=loop_start`, `end_marker=loop_end` | composite |
| `move-loop-forward` / `move-loop-backward` | button | `loop_start += d; loop_end += d` (size preserved), 1 beat | composite |

Corrections vs the original draft, baked in (no longer open questions):
- `looping`/`warping` are **booleans → on/off toggle buttons** (draft's "left/right
  extend" was a copy-paste slip).
- "move clip one beat" = **move the loop region**, keeping its size, by 1 beat
  (no clip-position API exists for session clips).
- `move_..._bar` "by one beat" was a typo → bar variant moves by one bar if added.

### Encoder semantics — the one new mechanism

Existing encoder codegen (`generate_parameter_listener_action`,
`generate_control_value_listener_function_action` in `gen_code.py`) only maps an
absolute 0–127 value to a **Live parameter** (Live owns the range). Clip properties
are **not** Live parameters, so we need net-new codegen:

1. **Relative encoders required.** Clip encoders must be relative-mode
   (`EncoderMode.Relative` → `relative_smooth_two_compliment`, core_model.py:42).
   Per user: *"relative encoder — start with 50% as the current value and increment
   per bar where 4 encoder points = 4 beats"* → **1 detent = 1 beat** for
   loop/marker encoders. (HUD shows the encoder cell centered at ~50% because a
   relative encoder has no absolute position; the live readout shows the actual
   beat/dB/semitone value. Confirm this reading at approval.)
    - **Assumption:** the EC4 (endless encoders) is the target. Absolute pots
      (Launch Control XL) won't step cleanly; the generator should require
      relative-mode encoders for clip encoder mappings and error otherwise.

2. **Signed-delta decode helper** (net-new, ~5 lines) in `source_modules/helpers.py`:
   ```python
   def relative_delta(self, value):       # two's-complement-ish
       return value - 128 if value > 64 else value
   ```

3. **Per-property step + clamp** applied in the generated listener, math from Push
   (`clip_control_component.py` `set_clip_gain` / `set_clip_pitch_coarse` /
   `_adjusted_offset`). A small runtime clip-helper module holds the apply logic so
   generated code stays thin.

### Buttons

Reuse the existing button path (`map_controllers` →
`button_listener_function_caller_templates` in gen_code.py). `looping`/`warping`
use the existing `toggle` refinement (fire on value-max). `duplicate-loop`,
`sync-loop-and-markers`, `move-loop-*` call clip-helper methods operating on
`detail_clip`.

### Audio vs MIDI clip guard

gain / pitch-coarse / pitch-fine / warping act only on audio clips. The generated
listener guards `if clip.is_audio_clip:` (else no-op). The HUD greys/omits these
cells when the detailed clip is MIDI (mirror Push's audio/midi mode split, but as a
per-cell enable rather than a mode swap).

### Dedicated-control enforcement (reuse existing machinery)

Do **not** build a new validator. Reuse `GeneratedCodes.common_midi_coords_in_control_defs`
(used today by `validate_exports`, gen.py:91) plus `all_control_defs` (gen.py:80)
to add a general **within-mode duplicate-coord check**: if a clip control's MIDI
coord collides with any other mapping's control in the same mode, **hard-error** at
generate-time naming the clashing coord and both owners. This enforces the
dedicated-control rule. (Confirm whether a general per-mode duplicate check already
exists; if so, just ensure clip control_defs flow through it.)

### HUD

Clip cells are ordinary layout cells that always represent clip attributes. A
`detail_clip` listener in `main_component.py` (alongside the existing
`add_appointed_device_listener` / app-view listeners) pushes a **clip burst** to
those cells via the `Remote`/`HudClient` `send_device`/`send_slot`/`commit` path —
independent of the device burst (different cells, no contention). Greys cells when
`detail_clip` is invalid. Live value updates use the existing observable property
listeners on the clip (attach on `detail_clip` change, detach on swap), emitting
`send_update`. Activation signal: `detail_clip` validity; the verified view
identifier `'Detail/Clip'` (memory: live-view-listener-behavior) is available if we
later want to gate on "user is looking at the clip" for the reposition feature.

## Files

**New**
- `ableton_control_surface_as_code/model_clip.py` — `Clip`, `ClipMappings`,
  `ClipMidiMapping(ButtonProviderBaseModel)`, `ClipWithMidi`, `build_clip_model_v2`.
- `source_modules/clip_helpers.py` (or methods on existing helpers) — runtime
  apply/step/clamp logic + composite actions (sync, move-loop), borrowed from Push.

**Edit (mechanical registration — mirror `transport`)**
- `ableton_control_surface_as_code/model_v2.py` — add `Clip` to `AllMappingTypes`
  (l.24), `ClipWithMidi` to `AllMappingWithMidiTypes` (l.34), import, and the
  `if mapping.type == "clip"` branch in `build_mappings_model_v2` (l.236).
- `ableton_control_surface_as_code/gen_code.py` — add `clip_templates(...)`:
  buttons via `map_controllers`; encoders via the new relative-stepping listener
  generator.
- `ableton_control_surface_as_code/gen.py` — register `'clip': clip_templates` in
  `template_to_code` (l.195); add the within-mode duplicate-coord validation.
- `source_modules/helpers.py` — `relative_delta` helper; clip-burst plumbing on
  `Remote` (parallel to `device_update`).
- `templates/surface_name/modules/main_component.py` — `add_detail_clip_listener`
  registration + `_on_detail_clip_changed` handler driving the clip burst and
  (re)attaching per-clip property listeners.

## Testing (TDD — failing tests first, per CLAUDE.md)

Unit (`tests/`):
1. `model_clip` parse: a `clip` mapping `.nt` block → `ClipWithMidi` with correct
   coords/actions; audio-only vs always keys classified.
2. Relative-delta decode: `relative_delta(1)==1`, `relative_delta(127)==-1`, etc.
3. Stepping/clamp: gain clamps 0–1, pitch_coarse clamps ±48 and ints, loop move
   preserves size.
4. `gen_code.clip_templates`: generated listener strings contain the
   `detail_clip` guard, audio guard, and step/clamp call; buttons wired via
   existing path.
5. Enforcement: a mode with a clip control sharing a coord with a device control
   raises the duplicate-coord error.

Integration:
6. Full generate of a small mapping with a `clip` block produces valid Python
   (imports/compiles), clip cells appear in the HUD layout.

## Verification (end-to-end)

- `poetry run pytest`.
- Generate against a clip-enabled EC4 mapping:
  `poetry run python ableton_control_surface_as_code/gen.py <mapping>.nt`.
- User redeploys (`./deploy.sh`) and restarts Ableton; `./bin/tail_logs.sh` to
  confirm load. Use `@update.py` for runtime introspection if needed.
- Manual: detail a clip, turn a clip encoder → property changes; toggle
  looping/warping; duplicate-loop / sync-markers / move-loop behave; HUD clip cells
  show live values and grey when no clip / for MIDI-invalid attributes.

## Deferred / follow-up

- Move HUD panel to bottom of Ableton window on clip focus, restore prior drag
  position on exit (Swift: `ableton_hud/.../HUDOverlayManager.swift`), gated on
  `'Detail/Clip'` visibility.
- `*_bar` move variants if 1-beat proves too fine.

## Open items to confirm at approval

1. The "start at 50% / 1 detent = 1 beat" reading of the relative-encoder spec.
2. EC4-only assumption for clip encoders (require relative mode; error on absolute).
3. Exact `.nt` key names for the clip mapping block.
