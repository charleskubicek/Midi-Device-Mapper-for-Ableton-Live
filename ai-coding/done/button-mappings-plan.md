# Plan: `button` / `button-list` device mappings (mirror `encoders` / `encoder-list`)

## Context

The user wants device button mappings to be expressed symmetrically with encoders:
under `device.mappings`, alongside `encoders:`/`encoder-list:`, add **`button:`** (single
`range` + `slots`) and **`button-list:`** (a list of the same), replacing the current
`switch-list:` / `switch1..switch8:` / `mode-buttons:` syntax.

The trigger was a real bug. In `live_surfaces/grid/ck_grid.nt`, shift_mode asks for
`switch-list … slots: 5-16`, but `SwitchListEntry` (`model_device.py:75-80`) has **no
`slots` field** — the key is silently dropped and the codegen loop
(`model_device.py:250-260`) always renumbers from `switch1`. The generated
`ck_grid/BEHAVIOR.md` proves it: shift_mode lists `switch1..switch12`, so the buttons
address device switch-params **1-12**, not the requested **5-16**.

Design intent the user confirmed: **shift and paging are orthogonal axes.** Shift
remaps the same physical buttons to *higher slot numbers within the current page* (e.g.
main = slots 1-4, shift = slots 5-16); the `parameter-pager` is what moves the whole
window to the next Ableton bank page. Honoring `slots:` literally is exactly what makes
the shift axis work.

## Button slots are integer indices, not `switchN` strings (per user)

The `switchN` strings are just an integer in disguise — every consumer does
`int(slot.replace('switch',''))-1`. So a button slot is represented as a **1-based
integer index** end-to-end (an "array of buttons"); the `switchN` naming is dropped.
The five consumers, all of which take the int directly:
`hud_presenter.py:115` (`logical_idx = slot-1`), `helpers.py:104` (stride
`max(slot)`), `helpers.py:291` `switch_slot_action(device, slot:int, …)`
(`switch_idx = slot-1`), `gen_code.py:272` (emit `(wire_idx, slot:int)`), and
`model_device.py` listener naming.

Resolution **already keys off that index**: `resolve_switch` (`param_resolver.py:452-507`)
takes `switch_idx`. So honoring `slots: 5-16` = emitting integer slots `5..16`
(→ `switch_idx 4..15`) instead of renumbering from 1. At `button_page=1` the page stride
term is 0, so `actual_idx = switch_idx` — the primary goal works with no resolver change.

Internal plumbing names (`switch_maps`, `switch_slot_action`, `resolve_switch`,
`switch_slot_assignments`) are **kept** — renaming them across templates/helpers/tests is
churn for no functional gain. Only the slot *value* changes from `str` to `int`.

HUD cell placement is **already decoupled** and needs no change: `find_wire_index`
(`gen_code.py:266-269`) resolves the HUD button index from the *physical controller
coord*, with slot-derived arithmetic only as a fallback. So labels stay on the correct
physical cells even when slot numbers start above 1.

Clash detection is **already covered**: `_bound_coords` (`model_v2.py`, commit 296bf73)
walks `switch_maps`, and `button`/`button-list` produce `SwitchMidiMapping`s into that
same field — no extra work.

## Design

New input syntax under `device.mappings`:

```nt
mappings:
    button: { range: grid-2:2::1-4, slots: 1-4 }          # single
    button-list:                                          # multiple ranges
        - { range: grid-2:1-8,  slots: 5-12 }
        - { range: grid-2:9-12, slots: 13-16 }
```

- `button` / `button-list` accept `range` + `slots` only (no `parameters:`; switches
  resolve via the device button table, not raw param index).
- `slots` are **switch** slots: `5-16` → slot names `switch5..switch16`. Per-group the
  control count must equal the slot count (same rule as encoder slot groups,
  `model_device.py:193-199`).
- `slots` may be non-contiguous physical coords via multi-coord ranges
  (`row-1:1-2,row-2:1-2`), reusing `parse_multiple_coords`.

## Implementation (TDD — failing tests first, per CLAUDE.md)

0. Copy this plan to `ai-coding/plans/button-mappings-plan.md` (CLAUDE.md convention; the
   commit message must reference it).

1. **Slot parsing** — `ableton_control_surface_as_code/slots.py`
   - Add `parse_button_slot_list(raw) -> List[int]` returning 1-based ints (reuse the
     range/comma logic from `parse_continuous_slot_list`, but yield ints; no upper cap).

2. **Model** — `ableton_control_surface_as_code/model_device.py`
   - Change `SwitchMidiMapping.slot: str` → `slot: int` (1-based). Update `info_string`/
     `short_info_string`/`controller_listener_fn_name` to format the int (e.g. `button{n}`).
   - Add a `ButtonRowMap` model: `range_raw` (`range`) + `slots_raw` (`slots`, required),
     with a `button_slots -> List[int]` property using `parse_button_slot_list` and a
     `multi_encoder_coords` property (reuse `parse_multiple_coords`). Mirror `RowMapV2_1`.
   - On `DeviceEncoderMappings`: add `button: Optional[ButtonRowMap]` and
     `button_list: List[ButtonRowMap]` (alias `button-list`); add a `buttons_all()`
     helper mirroring `encoders_all()` (`model_device.py:156-160`).
   - Update `_reject_unknown_keys` valid-key set + message to list `button`/`button-list`
     and drop the removed keys.

3. **Codegen** — `model_device.py:build_device_model_v2_1`
   - Replace the `switch_list` loop (`:250-260`) with a `buttons_all()` loop: per group,
     zip `build_midi_coords` results with `button_slots`, validate equal counts, emit
     `SwitchMidiMapping(midi_coords=…, slot=<int>)` **using the slot number directly**.
   - Remove the `mode_buttons` and `switch_entries()` loops (`:237-249`).
   - `gen_code.py`: `code_from_switch_slot_assignments` emits `(wire_idx, <int>)` and the
     `switch_slot_action` dispatch passes the int; runtime `switch_slot_action`
     (`helpers.py:291`), the stride calc (`helpers.py:102-105`), and `hud_presenter.py:115`
     consume the int directly (`switch_idx = slot - 1`) — drop the `.replace('switch','')`.

4. **Remove old input syntax** (recommended — clean break, single-user repo):
   - Delete `switch1..switch8`, `switch_list`/`SwitchListEntry`, `mode_buttons`/
     `SwitchEntry`, `_SWITCH_LITERAL`, and the `parse_switch`/`_no_mix_*` validators from
     `model_device.py`.
   - Keep `SwitchMidiMapping` and `DeviceWithMidi.switch_maps` — those are the internal
     runtime representation and stay unchanged.

5. **Migrate the four live configs** to the new syntax:
   - `live_surfaces/grid/ck_grid.nt` ×2: main `button: {range: grid-2:2::1-4, slots: 1-4}`;
     shift `button: {range: grid-2:1-12, slots: 5-16}`.
   - `live_surfaces/ec4/ck_ec4.nt`: `switch-list` → `button`/`button-list`.
   - `live_surfaces/launch_control/ck_launch_control_16.nt`:
     `switch1-4` → `button: {range: row-3:5-8, slots: 1-4}`.
   - `live_surfaces/parks/ck_parkstool_buttons.nt`:
     `switch1-4` (non-contiguous) → `button: {range: row-1:1-2,row-2:1-2, slots: 1-4}`.

6. **Tests** — update `tests/test_device.py`, `tests/test_validation.py` to the new
   syntax; add cases: (a) `slots: 5-16` produces `switch5..switch16` in `switch_maps`;
   (b) per-group count-mismatch raises `GenError`; (c) `button`+`button-list` combine via
   `buttons_all()`; (d) a `button` coord clashing with a mixer button in the same mode is
   caught by `validate_mappings`. Regenerate `ck_grid/BEHAVIOR.md` and assert shift_mode
   now shows `switch5..switch16`.

## Flagged for the user (per CLAUDE.md "flag contradictions")

- **Encoder/button resolution asymmetry (NOT fixed here).** Encoders resolve by running
  *ordinal* (`parameter=encoder_index` → `resolve_encoder` uses `c_idx-1`), so an encoder
  group with `slots: 9-16` as the only group in a shift mode would still resolve to page
  positions 1-8, *not* 9-16 — the slot number is label-only for encoders. Buttons (this
  change) resolve by slot *number*. No current config needs encoder shift-banding
  (grid's shift mode has no device encoders), and aligning encoders is entangled with the
  HUD dial index (`parameter_updated → send_update('dial', parameter_no-1)`). Recommend a
  separate follow-up if the user later wants shift to expose higher *encoder* slots.

- **Shift + paging combined uses a global stride.** `button_switch_count` (the per-page
  stride) is `max(slot number)` computed once from the flat `switch_slot_assignments`
  (`helpers.py:102-106`), not per-mode. With main(1-4)+shift(5-16) it tiles cleanly
  across pages, but verify what feeds the flat list during implementation (per-mode union
  vs single mode) since it sets the stride. Does not block the page-1 behavior.

## Verification

- `poetry run pytest` (all green; per CLAUDE.md never commit with any failing test).
- Regenerate grid: `poetry run python ableton_control_surface_as_code/gen.py
  live_surfaces/grid/ck_grid.nt`; confirm `ck_grid/BEHAVIOR.md` shift_mode shows
  `switch5..switch16`.
- `./build.sh` before committing; report quality delta; commit message references
  `button-mappings-plan`.
- Runtime check (user redeploys + restarts Ableton): in shift_mode on the grid, the
  buttons drive device switch-params 5-16 (not 1-12); HUD labels land on the correct
  physical cells; `./bin/tail_logs.sh` shows `[switch] … switch5..16` resolving.
