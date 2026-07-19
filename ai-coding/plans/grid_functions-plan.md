# Grid functions plan

Realise the `design.md` two-mode (Main / Shift) 4×4 **button** layout — which maps
onto **grid-4** — in `live_surfaces/grid/ck_grid.nt`, creating the functions it
references. Companion to the brief in `grid_functions.md`.

## Coordinate reminder
grid-4 is the right-hand 4×4 button block. Two coord spellings appear:
- flat linear `grid-4:N` (row-major 1..16): `grid-4:1`=R1C1, `grid-4:3`=R1C3.
- grid-cell `grid-4:R::C`: `grid-4:2::1`=R2C1, `grid-4:4::2`=R4C2.

## `@hud_name` decorator (DONE)
`@hud_name("Label")` on a `Functions` method sets that button's HUD label for
every mapping that references it. Runtime no-op (`source_modules/hud_name.py`);
generator reads it statically (`FunctionLookup`). Falls back to the raw function
name when absent.

## Main mode (grid-4) — status per cell
| Cell | Design label | Mapping | Status |
|------|--------------|---------|--------|
| R1C1 | Mute | mixer `mute: grid-4:1` | ✓ exists |
| R1C2 | Solo | mixer `solo: grid-4:2` | ✓ exists |
| R1C3 | Device on/off | device `on-off: grid-4:3` | ✓ exists |
| R1C4 | Mono on/off | functions `toggle_mono_on_master` | **port from custom.py** |
| R2C1 | Move loop left | functions `move_loop_left` | **create (custom.py `loop_nudge_left`)** |
| R2C2 | Move loop Right | functions `move_loop_right` | **create (custom.py `loop_nudge_right`)** |
| R2C3 | Back 8 | functions `back8` | ✓ exists |
| R2C4 | fwd8 | functions `fwd8` | **create (mirror of back8)** |
| R3C1 | Back to loop start | functions `move_playhead_to_loop_start` | **create** |
| R3C2 | first-last | device-nav `first-last` | ✓ exists |
| R3C3 | Track Nav L | track-nav `left` | ✓ exists |
| R3C4 | Track Nav R | track-nav `right` | ✓ exists — **fix nt typo** (`::3`→`::4`) |
| R4C1 | Shift | mode-button (shift) | ✓ |
| R4C2 | HUD on/off | functions `hud_toggle` (builtin) | ✓ |
| R4C3 | Dev Nav L | device-nav `left` | ✓ |
| R4C4 | Dev Nav R | device-nav `right` | ✓ |

**nt cleanup:** the stray functions block maps `back8: grid-4:1::3` (R1C3, dupes
device on-off) and `iterate_midi_pattern: grid-4:1::4` (R1C4) — both contradict
design R1. Remove them; keep `hud_toggle: grid-4:4::2`. Put mono on R1C4.

### Assumptions (defaults; correct on review)
- `move_playhead_to_loop_start` = move the playhead to loop start **only** (no
  auto-play; transport start is a separate concern).
- `move_loop_left/right` = nudge the whole loop by one loop-length (custom.py
  `loop_nudge_*` semantics), keeping length.

## Shift mode (grid-4) — NOT yet built (design table, mostly TODO)
| Cell | Design label | Candidate | Notes |
|------|--------------|-----------|-------|
| R1C1 | Rec Audio New | `create_audio_track_taking_input_from_selected_track` | exists; confirm intent |
| R1C2 | Rec Audio Resample | — | **create** (resample record) |
| R1C3 | Rec Midi new | `record_midi_from_track_to_new_track` | exists |
| R1C4 | Audio to Simpler | `selected_audio_to_simpler_in_new_track` | exists |
| R2C1 | half loop len | — | **create** — halve loop vs clip? (clarify) |
| R2C2 | double loop len | — | **create** — custom.py `double_clip`/`smart_clip_extend`? (clarify) |
| R2C3 | Move dev L | — | **create** — needs `Song.move_device`; feasibility spike |
| R2C4 | Move dev R | — | **create** — same |
| R3C1 | rack random | `press_rack_random_button` | exists (nt currently on R4C2 — reconcile) |
| R3C2 | cust Button 1 | — | placeholder; defer |
| R3C3 | Track Nav L x 3 | `track_nav_dec_x3` | **port from custom.py** |
| R3C4 | Track Nav R x 3 | `track_nav_inc_x3` | **port from custom.py** |
| R4C1 | Shift | mode-button | ✓ |
| R4C2 | Shift 2 | — | **open** — second held-shift = new FSM mode + 2nd mode-button |
| R4C3 | Dev Page L | parameter-pager `dec` | ✓ |
| R4C4 | Dev Page R | parameter-pager `inc` | ✓ |

## Decisions (answered)
1. **Shift 2** (R4C2) — **drop, leave empty.**
2. **Move dev L/R** — **yes**, via `Live.Song.Song.move_device(device, target, position)`
   (dev-docs/Live.md:2550). Mapped R2C3/R2C4.
3. **half/double loop len** — **arrangement loop**, clamped [1, 128] bars
   (`loop_length` in beats; bar = `signature_numerator`). Mapped R2C1/R2C2.
4. **rack random** → `grid-4:4::1` (done in nt).
5. **cust Button 1** (R3C2) — **drop, leave empty.**
6. **device on/off blank HUD** — device mappings emit no static label (runtime
   burst fills param cells; the on/off toggle is not a param, so it was blank).
   Fixed: `DeviceParameterMidiMapping.is_on_off` flag + static "dev on/off" label
   in `_label_pairs_for_mapping`.

## Execution log
1. `@hud_name` decorator — **DONE**.
2. Main-mode functions (`fwd8`, `move_loop_left/right`,
   `move_playhead_to_loop_start`, `toggle_mono_on_master`) — **DONE**.
3. `ck_grid.nt` Main: track-nav typo, stray block, mono on R1C4 — **DONE**.
4. Shift-mode: `halve_loop_length`, `double_loop_length`, `move_device_left/right`
   + `is_on_off` HUD label fix — **DONE** (this pass).

## Still TODO (Shift mode, need design)
- **Move dev L/R** — `move_device` target-position semantics (index±1) are a
  best guess; verify one live nudge reorders by exactly one, not to the end.
- **Track Nav L/R ×3** (R3C3/R3C4) — port from custom.py, but track nav lives on
  the surface (`source_modules/nav.py`), not in `functions.py`; needs a seam so a
  Functions method can step nav 3×.
- **Rec Audio Resample** (R1C2) — new function (audio track w/ Resampling input).
- **Rec Audio New** (R1C1) — map to existing
  `create_audio_track_taking_input_from_selected_track` (confirm intent).
