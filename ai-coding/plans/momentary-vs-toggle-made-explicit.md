# Plan: Make momentary vs. toggle explicit (act-once-on-press by default)

> On execution, also copy this plan to `ai-coding/plans/momentary-vs-toggle-made-explicit.md` per CLAUDE.md.

## Context

The user keeps getting bitten by button behavior: pressing a button "switches something on then off again straight away," or "does two operations at once." Both are symptoms of the same root cause — the codebase is **inconsistent about whether a button acts on press only, or on both press (127) and release (0)**.

Tracing every button path shows three distinct double-fire behaviors today:

1. **Method-call buttons** (functions, transport, track-nav, device-nav) — `generate_control_value_listener_function_action` emits `if True:` unless the `toggle` keyword is present, so the action fires on **both** edges. → *"two operations at once."*
2. **Switch / mode buttons** — `_switch_action_dispatch_fn` (`gen_code.py:217`) calls `helpers.switch_slot_action` with **no press guard at all** (`helpers.py:566`). For a `bool` slot it toggles twice per press (net nothing); for `min_max` it ends stuck at max.
3. **Device-param buttons without `toggle`** — route through `device_parameter_action` (`helpers.py:548`) with `toggle=False`, which `normalise`s the value on every edge: max while held, min on release. → *"switched on then off again."*

By contrast, two paths are already correct and **must stay untouched**:
- **Mixer mute/solo/arm** bind through Ableton's own `MixerComponent` (`set_mute_button(self.<btn>)`, `core_model.py:242`). The framework handles press/toggle; the `toggle` refinement does nothing for them.
- **Clip buttons** (`model_clip.py`) already fire once per press by design.

**The fix (decisions confirmed with the user):**
- A button **acts once on press by default**, across all button paths.
- A new explicit **`momentary`** refinement opts into act-on-both-edges: for a device-param button = max-held / min-released (true hold); for a method-call button = fire on press and again on release.
- Continuous **knobs/sliders are never affected** — the new default is gated on `EncoderType.is_button()`.
- The old **`toggle` keyword becomes the default**, so it is accepted as a no-op and emits a one-line deprecation warning at generation time.

Corollary worth stating: configs that **already** use `toggle` (`on-off: row-3:4 toggle`, `record_midi_… toggle` in launch_control & ec4) already work today and see **no behavior change** — they just carry a now-redundant keyword. The buttons actually biting the user are the **un-`toggle`d** ones: nav (double-nav) and switch/mode buttons.

## Behavior matrix (the load-bearing logic)

For device params, `device_parameter_action(..., toggle=<bool>)` already yields all three behaviors — we only change which bool we pass:

| Encoder | Refinement | `toggle` passed | Result |
|---|---|---|---|
| button | (default) | `True` | latch min↔max, **press only** |
| button | `momentary` | `False` | `normalise(value)` → max held / min released (true hold) |
| knob/slider | any | `False` | continuous `normalise` (unchanged) |

So: `toggle_arg = only_midi_coord.encoder_type.is_button() and not enc_refs.has_momentary()`.
**The `is_button()` gate is load-bearing — if dropped, knobs start latching.**

For method-call buttons: `press_only = builtin or not enc_refs.has_momentary()`.

## Changes

### 1. Grammar — add `momentary` refinement
`ableton_control_surface_as_code/encoder_coords.py`
- Add grammar rule `momentary : "momentary"` and include it in the `refinements` alternation (alongside `toggle | map_mode_absolute | mode`).
- Add a `Momentary` refinement class with `name()` → `"momentary"` (mirror the existing `Toggle` class, lines ~18–26).
- Add `EncoderRefinements.has_momentary()` (mirror `has_toggle()`, lines ~56–57).
- `momentary` flows through to `MidiCoords.encoder_refs` exactly as `toggle` does today (no extra plumbing).

### 2. Method-call buttons — press-only default
`ableton_control_surface_as_code/gen_code.py:283` (`button_listener_function_caller_templates`)
- Change `press_only = enc_refs.has_toggle() or getattr(midi_map, 'builtin', False)`
  → `press_only = getattr(midi_map, 'builtin', False) or not enc_refs.has_momentary()`
- Update the adjacent comment to describe the new default. This covers functions, transport, track-nav, device-nav (all route through `map_controllers`).

### 3. Device-param buttons — latch default, gated on button
`ableton_control_surface_as_code/gen_code.py:187` (`device_templates`)
- Change the arg passed to `generate_parameter_listener_action` from `enc_refs.has_toggle()`
  → `mm.only_midi_coord.encoder_type.is_button() and not enc_refs.has_momentary()`
- No change needed in `device_parameter_action` (`helpers.py:548`) — its two branches already produce the right behaviors.

### 4. Switch / mode buttons — add the missing press guard (distinct fix)
`ableton_control_surface_as_code/gen_code.py:217` (`_switch_action_dispatch_fn`)
- Wrap the `self._helpers.switch_slot_action(...)` call in a press guard so it fires once on press by default, respecting `momentary`. Thread the refinement in from `_mode_button_template` (`gen_code.py:202`), or guard inline using `value == 127`.
- This is its own line item: today there is **no** guard, so `bool` slots net-no-change and `min_max` slots stick at max. This is also what fixes the `Mono` / `Bass Mono` toggles declared via `button=toggle` in `device_parameters.nt` (see note below).

### 5. `toggle` keyword — accept as no-op + deprecation warning
- Keep parsing `toggle` (do **not** remove it from the grammar) so launch_control/ec4 configs still parse. It now has no effect (it equals the default).
- Emit a **non-fatal** one-line deprecation warning at generation time. The existing `ProblemAccumulator` (`gen_error.py`) is **errors-only** (collects → raises), so it is *not* the right channel. Instead print a warning to stderr from `gen.py` (near the readable-error block at `gen.py:478`), driven by a scan for `has_toggle()` on resolved coords — e.g. `WARNING: 'toggle' is now the default and can be removed (live_surfaces/.../file.nt: <mapping>)`. (Optional, larger: add a `warnings` list + `add_warning()` to `ProblemAccumulator` and print them after a successful build — only if a structured channel is preferred.)

### 6. Docs
- `docs/mapping_file.md:105` and `docs/user_manual.md:184`: replace the `toggle` description with the new model — "buttons act once on press by default; add `momentary` for on-while-held (params) / fire-on-both-edges (functions). `toggle` is deprecated (now the default)."
- `docs/mapping_file.md:171`: update the functions note likewise.

### Note on `device_parameters.nt` `button=toggle`
This is a **separate** runtime parameter-table annotation (consumed when resolving the custom parameter table / switch slots), **not** the encoder-coord refinement. It stays as-is. The behavior it produces (toggling `Mono`/`Bass Mono` on press) is corrected by the switch-path press guard in change #4 — not by anything in changes #1–3.

## Tests (TDD — write failing first, then implement)

Add to the gen/codegen test suites (e.g. `tests/test_gen.py`, `tests/test_gen_code.py`, `tests/test_encoder_coords.py`):
1. **Grammar**: `row-3:4 momentary` parses; `EncoderRefinements.has_momentary()` is True; `has_toggle()` False.
2. **Method-call default**: a function/nav button without refinement generates the press-only guard (`value_is_max(value, 127)`), **not** `if True:`.
3. **Method-call `momentary`**: with `momentary`, generates `if True:` (both edges).
4. **Device-param button default**: button mapped to a param generates `toggle=True` (latch) in `generate_parameter_listener_action`.
5. **Device-param `momentary`**: button + `momentary` generates `toggle=False` (hold).
6. **Knob unaffected**: knob/slider mapped to a param always generates `toggle=False`, with or without refinements (guards the `is_button()` gate).
7. **Switch/mode button**: generated switch dispatch fires once on press (guarded), and with `momentary` fires on both edges.
8. **`toggle` no-op + warning**: a config using `toggle` still generates the same code as the default and surfaces the deprecation warning.
9. **Regression**: existing launch_control/ec4 generation still succeeds (their `toggle` mappings are behaviorally unchanged).

## Backward-compatibility impact (concrete)

- **No behavior change** (keyword now redundant, deprecation warning only):
  - `live_surfaces/launch_control/ck_launch_control_16.nt:29` `on-off: row-3:4 toggle`
  - `…:86`/`:87` `record_midi_from_track_to_new_track`, `create_audio_track…` `toggle`
  - `live_surfaces/ec4/ck_ec4.nt:38,79,80` (same three, `row-5:*`)
- **Behavior changes (the fix the user wants)** — un-`toggle`d buttons that previously double-fired:
  - device-nav (`ck_launch_control_16.nt:44`) and track-nav (`:50`): stop double-stepping; one move per press.
  - any switch/mode buttons and `button=toggle` params: stop net-no-change / min↔max thrash; one clean toggle per press.
- **Unaffected**: all continuous knobs/sliders; mixer mute/solo/arm (framework-bound); clip buttons (already press-once).

## Verification (end-to-end)

1. `poetry run pytest` — all new + existing tests green (never commit on a red test, per CLAUDE.md).
2. Regenerate a real surface: `poetry run python ableton_control_surface_as_code/gen.py live_surfaces/launch_control/ck_launch_control_16.nt`. Confirm the deprecation warning prints for the `toggle` mappings and generation succeeds.
3. Inspect generated `modules/main_component.py`: nav/switch listeners now use the `value_is_max(value, 127)` guard (not `if True:`); device-param buttons pass `toggle=True`.
4. User redeploys (`./deploy.sh`) and restarts Ableton — let the user do this. Tail `./bin/tail_logs.sh`. Manually confirm: a switch/bool button toggles once per press; nav moves one step per press; a `momentary` param button is on-while-held.
