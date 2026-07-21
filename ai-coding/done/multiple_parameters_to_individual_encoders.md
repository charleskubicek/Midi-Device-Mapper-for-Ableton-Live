# Conditional (toggle-dependent) parameters on zoned synth encoders — Operator Fixed mode

## Context

In Operator, tapping **Fixed** on an oscillator swaps the visible params: Coarse/Fine become Freq/Multi. The user wants the same physical encoder to always control whatever Live currently shows for that screen position, regardless of the Fixed state.

The codebase already solves this for BOB custom mappings: `controlledBy`/`group`/`activeWhen` entries (e.g. Hybrid Reverb "Algo Type", Delay "LFO T Mode") are resolved by `ParameterResolver._resolve_group_member`, and `helpers.py` attaches a value listener to the selector param so a toggle re-emits the HUD burst (relabel). But Operator is handled by the **smart-zoning tier** (`data/synth_zone_tables.json`), whose entries are plain `{name}` — no group support — and `group_selector_names` only scans BOB tables.

**Decision (user: "whichever is simplest"):** exclusive switch semantics (encoder controls only the currently-visible param), reusing the existing group mechanism, extended into the zone tier. Scope: Operator oscillators A/B only (the 32-slot template doesn't expose C/D). This is a data + resolver change, not a `.nt` mapping change — mappings only bind slots.

Confirmed Live original_names (devices_12.json): `A Coarse`, `A Fine`, `A Fix On ` (trailing space — already used by zone button `osc_b3`), `A Fix Freq`, `A Fix Freq Mul`; same pattern for B.

Encoder turns re-resolve on every turn (`device_parameter_action` → `resolve_encoder`, `source_modules/helpers.py:288`), so writes follow the Fixed state automatically once the zone branch understands groups; the selector listener is only needed for the HUD relabel and that hookup (`_attach_group_selector_listeners`, `helpers.py:264`) already keys off `group_selector_names`.

## Changes (TDD: failing tests first per CLAUDE.md)

### 1. Gen-side schema — `ableton_control_surface_as_code/model_synth_zones.py`
- Allow a synth encoder role value to be either the existing `ZoneRoleParam` or a grouped entry. **Reuse** `GroupedEncoderEntry` + `GroupMember` from `model_custom_devices.py` (they already validate non-empty groups, overlapping `activeWhen`, and support `display`): `SynthZoneEntry.encoders: Dict[str, Union[GroupedEncoderEntry, ZoneRoleParam]]`. Buttons stay plain.
- Update `_check_no_dupe_params` to expand a group entry into all member names for the duplicate-binding check (a param bound in two different roles is still the muscle-memory bug this guards).

### 2. Runtime resolver — `source_modules/param_resolver.py`
- `resolve_encoder`, zone branch (`'mapped'` outcome, ~line 555): if the entry has `controlledBy`/`group`, run it through `self._resolve_group_member(device, entry)` first — identical to the BOB branch at line 570. Member `None` (selector unreadable / no `activeWhen` match) → return `None` (dim slot). Then resolve the member's `name` / `display` as today. Zone-drift log message should name the member param.
- `group_selector_names(device)` (~line 235): for a zoned device, also collect de-duplicated `controlledBy` names from `self._zone_synth(device)['encoders']` group entries, so the selector listener attaches and a Fixed flip re-emits the burst. (Zoned synths have no BOB by design, but keep both sources merged for safety.)
- `_build_zone_tables` passes synth entries through as raw dicts — no change needed.

### 3. Data — `data/synth_zone_tables.json`, Operator encoders
Replace four plain entries with groups (note the trailing space in the selector names):
- `osc1_timbre`: `controlledBy: "A Fix On "` → `A Coarse` @ `activeWhen [0]`, `A Fix Freq` (display `A Freq`) @ `[1]`
- `osc1_timbre2`: same selector → `A Fine` @ `[0]`, `A Fix Freq Mul` (display `A Multi`) @ `[1]`
- `osc2_timbre`: `controlledBy: "B Fix On "` → `B Coarse` / `B Fix Freq` (display `B Freq`)
- `osc2_detune`: same selector → `B Fine` / `B Fix Freq Mul` (display `B Multi`)

### 4. Tests
- `tests/test_model_synth_zones.py`: group entry accepted; duplicate member-name across roles rejected; overlapping `activeWhen` rejected (via reused validator); the shipped `data/synth_zone_tables.json` still validates.
- `tests/test_synth_zone_resolver.py`: with a zoned fake device — selector value 0 resolves `A Coarse`; value 1 resolves `A Fix Freq` with alias `A Freq`; `group_selector_names` returns the zone selectors for a zoned device (and still returns BOB selectors for a BOB device).

## Verification
- `poetry run pytest` (then `./build.sh` before any commit, reporting quality delta).
- Regenerate the grid surface: `poetry run python ableton_control_surface_as_code/gen.py live_surfaces/grid/ck_grid.nt`.
- User redeploys (`./deploy.sh`) and restarts Live (per CLAUDE.md, let the user do this). Then on an Operator track: encoder 1/2 move Coarse/Fine; press the `A Fix On` zone button (or click Fixed in Live's UI) → HUD slots 1/2 relabel to `A Freq`/`A Multi` and the same encoders now move the fixed-frequency params; toggling back restores Coarse/Fine untouched. Same for oscillator B on encoders 5/6. `./bin/tail_logs.sh` for any `[zone]` drift messages.
