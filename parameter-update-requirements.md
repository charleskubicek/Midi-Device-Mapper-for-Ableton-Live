# Parameter mapping — redesign requirements

## Why this is being rewritten

`data/custom_device_mappings.json` currently identifies device parameters by **integer index** (`"number": 28`). This broke for `OriginalSimpler` when Live added a Pitch envelope (5 new params: `Pe < Env`, `Pe Attack`, `Pe Decay`, `Pe Sustain`, `Pe Release`). Every param after that point shifted by 5 — `Fade In` is now at 33 instead of 28, `Filter Freq` at 41 instead of 36. The JSON kept addressing the old positions and silently moved the wrong parameters (e.g., the encoder labelled "Fade In" actually drove "Ve Sustain").

Index-based addressing is fundamentally fragile: Live updates, presets exposing more macros, or M4L bank changes can all invalidate it.

## How Ableton's own surfaces solve this

Source: `/Users/ck/oss/AbletonLive12_MIDIRemoteScripts/_Generic/Devices.py` and the `ableton.v2.control_surface` framework.

1. **Name-based banks per device class.** `Devices.py` ships a curated dict of every built-in device. Each entry is a tuple of bank tuples, where each bank is exactly **8 parameter names** (strings).

   ```python
   SIM_BANK1 = ('Ve Attack', 'Ve Decay', 'Ve Sustain', 'Ve Release',
                'S Start', 'S Loop Length', 'S Length', 'S Loop Fade')
   SIM_BANK2 = ('Fe Attack', 'Fe Decay', 'Fe Sustain', 'Fe Release',
                'Filter Freq', 'Filter Res', 'Filt < Vel', 'Fe < Env')
   SIM_BANK3 = ('L Attack', 'L Rate', 'L R < Key', 'L Wave',
                'Vol < LFO', 'Filt < LFO', 'Pitch < LFO', 'Pan < LFO')
   SIM_BANK4 = ('Pe Attack', 'Pe Decay', 'Pe Sustain', 'Pe Release',
                'Glide Time', 'Spread', 'Pan', 'Volume')
   SIM_BANKS = (SIM_BANK1, SIM_BANK2, SIM_BANK3, SIM_BANK4)
   SIM_BNK_NAMES = ('Amplitude', 'Filter', 'LFO', 'Pitch Modifiers')

   DEVICE_DICT     = { ..., 'OriginalSimpler': SIM_BANKS, ... }
   BANK_NAME_DICT  = { ..., 'OriginalSimpler': SIM_BNK_NAMES, ... }
   ```

2. **"Best of bank" (BOB)** — one extra tuple of 8 names per device, used as the default page when the user hasn't navigated banks. This is the "show me the most important knobs for this device" view.

   ```python
   SIM_BOB = ('Filter Freq', 'Filter Res', 'S Start', 'S Length',
              'Ve Attack', 'Ve Release', 'Transpose', 'Volume')
   ```

3. **Resolution by `original_name`.**

   ```python
   def get_parameter_by_name(device, name):
       for i in device.parameters:
           if i.original_name == name:
               return i
   ```

   `Parameter.original_name` is the device's canonical name; `Parameter.name` reflects user renames (macros, M4L) and is unstable. Live's surfaces always use `original_name`.

4. **Fallbacks** (`parameter_banks(device)`):
   - Known class → hand-curated banks resolved by name.
   - `MxDevice*` → `device.get_bank_count()` + `device.get_bank_parameters(i)` (Max-defined banks, by index, but the indices come from the device itself so they stay valid).
   - Unknown → `group(device.parameters[1:], 8)` (chunk the parameter list in 8s, skipping On/Off at index 0).

## What we want

A two-tier resolution model:

1. **Best-of (BOB) — authored by hand in `custom_device_mappings.json`.**
   - A number per device that will be used in the `type: device` mapping in the main .nt mapping file.
   - Curated for what we actually want at our fingertips: every device's `Dry/Wet` lives at the same encoder position, every `Filter Freq` at the same one, etc. (Goal: muscle memory across devices.)
   - This is the page that appears on the first device-focus.

2. **Standard banks — taken from `_Generic/Devices.py`.**
   - Pages 2+ surface the named banks already curated by Ableton.
   - Each bank is 8 params. If a controller is 16. **Two banks fit per page** — pair them automatically (e.g., page 2 = `SIM_BANK1` + `SIM_BANK2`, page 3 = `SIM_BANK3` + `SIM_BANK4`).
   - Bank names from `BANK_NAME_DICT` go on the HUD page label (e.g., "Amplitude / Filter").

3. **Everything resolved by name.**
   - `get_parameter_by_name` style lookup using `original_name`.
   - `number` field stops being authoritative; we keep it only if useful as a cached fast path that gets revalidated. Probably simpler to drop it entirely.
   - Our `dump2`/`gather_custom_json.py` scripts need to write `original_name`, not `name`.

4. **Behaviour when a name doesn't resolve.**
   - HUD slot stays empty / shows the name as a dead label.
   - Don't fall back to a wrong index — silent mis-mapping is exactly the bug we're getting rid of.

## Implications for the codebase

### Data model (`model_custom_devices.py`)

- Encoder/button entries become: `{ "name": "Filter Freq", "display": "Filter", "button": "..." }` — no `number`.
- Existing `lom_property` / `lom_function` button kinds carry over (those are device properties, not `Parameter` lookups, so they're orthogonal to this change).
- Existing `controlledBy`/`group` grouped encoders still work — but `number` inside group members also becomes `name`.
- BOB section is the entire `encoders` / `buttons` arrays we already have; just rename what they mean (best-of, not "all of").

### Resolution (`source_modules/helpers.py`)

- New module-level table (or imported from `_Generic.Devices`-equivalent) of standard banks + names + BOBs for known device classes. We probably bundle a snapshot rather than depending on Ableton's installed scripts at runtime.
- New `_resolve_param_by_name(device, name)` — single lookup point, mirrors `get_parameter_by_name`. Builds a `{original_name: param}` dict on device focus and caches it (invalidate when device changes).
- `_resolve_encoder(c_idx)` becomes: figure out which page we're on, figure out which slot we're at, return the named param for that slot.
  - Page 1 → BOB (our JSON).
  - Page 2+ → pairs of standard banks (2 × 8 = 16 per page).
- `_encoder_pages_count` becomes `1 + ceil(num_standard_banks / 2)`.
- The "identity fallback" (chunk into 8s) still applies for completely unknown device classes — but operates on `original_name`-keyed groups, not raw indices.

### Page UI / HUD

- Page label needs more space — first page is "Best of", subsequent pages display two bank names ("Amplitude / Filter").
- Existing `parameter_page_inc` / `parameter_page_dec` already do paging; just update the page total calculation.

### Tooling

- `scripts/gather_custom_json.py` and the `dump2` command in `templates/surface_name/surface_name.py` switch from `p.name` to `p.original_name`.
- We could optionally add a `dump_bob` / `dump_best_of` helper that emits a 16-entry skeleton with `null` slots so the user can fill in their preferences.
- One-shot migration script that converts the existing `number`-keyed JSON to name-keyed JSON (using the current Live device's `parameters[number].original_name`) so we don't have to redo all device mappings by hand.

### Where to source the standard banks

Two options to consider when planning:

- **Bundle a snapshot of `_Generic/Devices.py` constants** into our project (probably as `data/live_device_banks.py` or `.json`). Pros: reproducible, no runtime dependency. Cons: needs occasional refresh.
- **Read Ableton's installed `_Generic/Devices.py` at gen time.** Pros: always current. Cons: path fragility, version drift. It is here; /Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/_Generic/Devices.py — but read the value from `ableton_dir` in the mapping file, not hardcoded. It will need to be decompiled, is that feesible? Once decompiled, it can be cached to the version number of ableton. 

Recommend bundling a snapshot, but mention both in the plan.

### Tests

- Unit tests for `_resolve_param_by_name` against a fake device whose params have `original_name`.
- Test that the resolver returns `None` (not the wrong param) when a name is missing.
- Test that page count adds up correctly: BOB + ceil(banks/2).
- Migration test: take a current `number`-based entry, simulate Live's current parameter list, confirm conversion produces the right names.

## Open questions to settle when writing the plan (and some answers...)

1. **What happens when the BOB has fewer than 16 entries?** Empty HUD slots, or pack subsequent bank into them? Answer: empty HUD slots, with no fallback to avoid silent mis-mapping.
2. **Should `controlledBy`/`group` survive the migration as-is, or get replaced by a more general "named contextual slot" mechanism?** Answer: Survive
3. **Bank pairing order** — Ableton's banks are themed (Amplitude, Filter, LFO, …). Always pair (1+2, 3+4)? Answer Yes, and you MUST show the bank names on the HUD
4. **Per-controller BOB vs shared BOB?** Currently each `live_surfaces/<controller>/` references the shared `data/custom_device_mappings.json`. Answer: keep shared — that's the whole point of muscle memory across controllers.
5. **Where do `lom_property` buttons live in the new page model?** Probably stay on the BOB page only (since they're hand-authored). Answer - on the BOB page


## Critical files (read these before drafting the plan)

- `data/custom_device_mappings.json` — current authoring format.
- `source_modules/helpers.py` — `_resolve_encoder`, `_resolve_switch`, `_build_device_table`, `update_remote_parameters`. The whole runtime mapping path lives here.
- `ableton_control_surface_as_code/model_custom_devices.py` — Pydantic schema for the JSON.
- `ableton_control_surface_as_code/gen.py` — where `parameter_mappings_raw` is loaded and baked into the surface.
- `ableton_control_surface_as_code/model_device.py` — `DeviceWithMidi`, `encoder_slot_count`, HUD cell layout. Page model needs updating here.
- `scripts/gather_custom_json.py` and `templates/surface_name/surface_name.py` (`dump_selected_device_parameter_info_split_into_encoders_and_buttons`) — both write `p.name` and need to switch to `original_name`.
- Reference (read-only): `/Users/ck/oss/AbletonLive12_MIDIRemoteScripts/_Generic/Devices.py` — source of truth for stock device banks. Also worth skimming `_Generic/util.py` and `parameter_banks` / `get_parameter_by_name` near the bottom of `Devices.py`.
- Reference (read-only): `/Users/ck/oss/AbletonLive12_MIDIRemoteScripts/Launchpad_Pro_MK3/simple_device.py` — example of how a modern surface delegates to `SimpleDeviceParameterComponent` and `use_parameter_banks=True`.
