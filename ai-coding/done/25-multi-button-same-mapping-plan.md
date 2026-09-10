# Multi-button same-mapping plan

## Goal

Allow the **same logical action** (e.g. track-nav `right`) to be bound to **more than one
physical button**. Concretely, make line 50 of `live_surfaces/grid/ck_grid.nt` work:

```
right: grid-2:11      # primary
right: grid-1:14      # second button for the same action  <- currently impossible
```

## The constraint that shapes the syntax

The mapping files are NestedText. A NestedText dict **cannot have two keys with the same
name** (`right:` twice is a parse error). So "bind two buttons to one action" must be
expressed as **one key whose value is a comma-separated list of coords**:

```
right: grid-2:11, grid-1:14
```

This reuses the existing multi-coord grammar already used by mixer `sends` and device
`encoders` ranges. Confirmed behaviour:

- `parse_coords("grid-2:11, grid-1:14")` → **silently drops** the 2nd coord (uses the
  `single` start rule, whose transformer `return`s the first coord).
- `parse_multiple_coords("grid-2:11, grid-1:14")` → returns **both** `EncoderCoords`.
- `controller.build_midi_coords(list_of_coords)` already resolves a list → a flat list of
  `MidiCoords`.

So the only missing piece is: the single-button mapping types parse with `parse_coords`
(dropping extras) and the code generator emits **one** listener per mapping via
`only_midi_coord` (using just the first coord).

## Design: "resolve then expand"

Every single-button mapping type flows through the same generator path:
`map_controllers` → `button_listener_function_caller_templates` → `only_midi_coord`,
which produces exactly one listener per `*MidiMapping`.

Therefore the uniform fix is: **when a mapping resolves to N MidiCoords (because the user
comma-listed buttons), emit N independent single-coord `*MidiMapping`s** instead of one
mapping holding a list. Each expanded mapping then generates its own listener.

Why this is safe / collision-free:
- Two different physical buttons → different `controller_variable_name()` →
  different `controller_listener_fn_name(mode)` → no function-name clash.
- `info_string()` (debug string) is derived per-coord, so each listener is distinct.
- **No `gen_code.py` change is needed** — the existing per-`midi_map` loops do the rest.

Scope (confirmed with user): **all button-style mapping types** — track-nav, device-nav,
functions, transport, and single mixer buttons (mute/solo/arm) — plus mixer
encoders (volume/pan) for consistency. Mixer `sends` is **excluded** from expansion (see
below).

## Changes per module

### 1. `model_track_nav.py`
- `TrackNavMappings.as_list` → return `List[Tuple[Direction, List[EncoderCoords]]]` using
  `parse_multiple_coords` instead of `parse_coords`.
- **Fix existing bug**: the dec/left branch is guarded by `if self.right_raw is not None`
  (line 19) — should be `self.left_raw is not None`. As written, a config with `right` but
  no `left` calls `parse_coords(None)` and crashes; with `left` but no `right` the left
  binding is silently skipped.
- `build_track_nav_model_v2`: for each `(dir, encs)`, resolve `build_midi_coords(encs)` then
  loop the resolved coords, appending `TrackNavMidiMapping.from_single_coord(mc, dir)` per
  coord.

### 2. `model_device_nav.py`
- `DeviceNavMappings.as_list` → `parse_multiple_coords`; apply the same left-guard fix
  (line 22 currently checks `right_raw`).
- `build_device_nav_model_v2`: expand per resolved coord, constructing
  `DeviceNavMidiMapping(midi_coords=[mc], action=action)` (note its custom `__init__` wraps
  with `list(...)`, so pass a single-element list).

### 3. `model_functions.py`
- `Functions.mappings` property → `parse_multiple_coords`, yielding
  `Dict[str, List[EncoderCoords]]`.
- `build_functions_model_v2`: for each `(fn, encs)`, resolve once then emit one
  `FunctionsMidiMapping(midi_coords=[mc], ...)` per coord. (Bonus: this removes the current
  hard failure where `only_midi_coord` raises if more than one coord is present.)

### 4. `model_transport.py`
- `TransportMappings.as_parsed_dict` → `parse_multiple_coords` → `Dict[str, List]`.
- `build_transport_model`: expand per coord, one `TransportMidiMapping(midi_coords=[mc], ...)`
  each.

### 5. `model_mixer.py`
- `mute/solo/arm/volume/pan`: expand to one `MixerMidiMapping` per resolved coord.
- `sends`: **keep as a single mapping holding the full array** — sends semantics map the
  Nth knob to send index N, so the array must stay intact (handled by the `sends` branch in
  `mixer_templates`). Guard the expansion with `if api_name == 'sends': <append one>`.
- The `verify_correct_ranges` validator still forbids `-` ranges for the single controllers;
  comma lists are unaffected.

### 6. `gen_code.py`
No change. Verify by reading that `map_controllers` and `mixer_templates` already iterate
`midi_maps` and call `only_midi_coord` once per map.

## TDD order

1. **Failing unit tests first** (one per module):
   - track-nav: `right: row-2:1, row-2:2` → 2 `midi_maps`, both `Direction.inc`, distinct
     `only_midi_coord`.
   - track-nav bug fix: `left` set, `right` unset → a `Direction.dec` map bound to the
     `left` coord (today: silently dropped).
   - device-nav: analogous, plus a `first-last` single still works.
   - functions: `update_colors: grid-2:6, grid-2:7` → 2 maps, same `function_name`.
   - transport: 2 maps for one api call.
   - mixer: `mute` with two coords → 2 maps; `sends` with a range → still **one** map whose
     `midi_coords` is the array.
2. **Implement** the per-module changes above.
3. **Integration test** (`tests/test_gen.py`): generate a surface whose mode has a nav
   action bound to two buttons; assert the generated `main_component.py` contains **two**
   `add_value_listener` lines and **two** distinct listener defs for that action.

## Caveats to surface

- In the literal example, `grid-1:14` is also slot 14 of the device `encoders: grid-1:1-16`
  range in `main_mode`. Binding nav `right` there is a genuine *one-physical-control,
  two-actions* conflict, independent of this feature. The user should pick a free button
  (or we separately decide how same-control conflicts are reported). This plan does **not**
  add conflict detection; it only enables the multi-button binding.
- Backwards compatible: every existing single-coord config resolves to exactly one
  expanded mapping, identical to today.

## Validation

- `poetry run pytest` green.
- Regenerate `live_surfaces/grid/ck_grid.nt` with line 50 active (using a free button) and
  confirm two listeners in the output; `./build.sh` before any commit.
