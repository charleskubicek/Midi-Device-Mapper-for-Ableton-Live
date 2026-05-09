# Custom Device Mapping — Feature Spec

## What this feature is

The user wants to control which Ableton device parameters are assigned to the 8 knobs and 4 switch
buttons on the Launch Control. Rather than a single hardcoded mapping strategy, the system
supports swappable **device mapping sets** — JSON files that declare, per device class, which
parameter numbers map to which slot positions (slot1–slot8, switch1–switch8).

The mapping set is chosen per `.nt` surface file via the `device_mapping:` key at the root.

---

## Two mapping sets (currently)

### 1. `family` — `data/device_family_intents.json`

The original system. Devices are grouped into **semantic families** (Drive & Distortion, Dynamics,
EQ, etc.). Within a family, slots represent roles: slot1 = Dry/Wet, slot2 = Drive/Amount, slot3 =
Tone, etc. The idea is that all distortion-type devices share the same knob roles even though the
underlying parameter numbers differ.

Supports rich **switch actions** for cycle-type parameters:

| Action | Meaning |
|---|---|
| `cycle` | Step through cycleMin..cycleMax on a specific parameter |
| `pulse` | Trigger a parameter by name to 1 then back |
| `inc` / `dec` | Increment or decrement a named parameter |
| `random` | Set a single named parameter to a random value |
| `group_random` | Randomise a list of named parameters simultaneously |

The switch action vocab lives in `family_intents.py:SWITCH_ACTIONS`.

**Used for:** standard Ableton devices (EQ Eight, Compressor 2, Amp, Reverb, etc.).

### 2. `blue_hand` — `data/blue_hand.json`

A personal/curated mapping set. Rather than semantic roles across families, each device gets an
explicit full mapping to 8 parameter numbers. Also covers the user's custom Audio Effect Racks with
names like `AudioEffectGroupDevice / "CK Utility - Shaper Version"`.

Extra fields present in this JSON (currently **not handled** in code):

- `fixed: true` — all 8 slots are explicitly mapped; no holes
- `fuzzy: true` per slot — the parameter number was uncertain when the mapping was written
- Slots beyond 8 (`slot9`–`slot13`, etc.) — present in some entries but controller only has 8

**Used for:** the user's own live set devices, custom racks, and M4L devices.

**Data source:** the `data/blue_hand.txt` is a human-readable dump of Ableton parameter lists per
device, used as reference when filling in `blue_hand.json` manually. The `data/gathered_*.json`
files suggest an auto-collection script is being built to scrape parameter data from a running
Ableton instance.

---

## Current implementation state

### What's done (uncommitted changes on `master`)

| File | Change |
|---|---|
| `model_v2.py` | `device_mapping: Literal["family", "blue_hand"] = "family"` added to `RootV2` and `RootV2ModesOrModeless` |
| `family_intents.py` | `_BLUE_HAND_PATH`, `load_blue_hand_intents()`, `get_intents(device_mapping)` added |
| `gen.py` | `device_mapping` threaded from root through `generate_code_as_template_vars` → `create_code_model` → `build_mode_code`; `device` no longer in `template_to_code` dict (handled inline to pass `device_mapping`) |
| `gen_code.py` | `_intents_cache` dict replaces module-level `_family_intents` load; `_get_intents(device_mapping)` helper added; `device_mapping` param threaded into `device_templates`, `_mode_button_template`, `_switch_action_dispatch_fn`, `code_from_slot_assignments`, `code_from_switch_slot_assignments` |

The `.nt` mapping file (`ck_launch_control_16.nt`) currently has `device_mapping: blue_hand`.

### What's NOT done / open issues

1. **`fuzzy` flag is ignored.** Blue hand entries with `fuzzy: true` load fine but there is no
   runtime behaviour difference. At minimum, a warning or comment in generated code would help.

2. **Slots >8 are silently present** in some blue_hand entries but the controller has 8 knobs.
   Nothing validates or truncates these.

3. **`fixed: true` is ignored.** Could be used to give better error messages when a slot is
   missing from a "fully-mapped" device.

4. **Auto-gathering pipeline is partial.** The `data/gathered_*.json` files exist (two runs:
   `gathered_20260507_201418.json` and `gathered_20260507_202333.json`) but there is no script
   in `scripts/` yet that merges them into `blue_hand.json`. The `scripts/` directory exists
   but is untracked and likely empty or partial.

5. **Only two mapping sets are hardcoded.** `device_mapping` is a `Literal["family", "blue_hand"]`.
   Adding a third set (e.g. a per-project custom mapping file) would require expanding the Literal
   and the `get_intents` dispatcher. A more extensible design would accept a filename/path.

6. **No HUD slot-name display for blue_hand.** The HUD currently receives slot names from the
   Python side. The blue_hand mapping uses `parameterName` as the canonical name — confirm
   `hud_client.send_slot()` is picking this up correctly rather than the slot index.

---

## Design decisions to revisit

### A. Should `device_mapping` be a file path instead of a name?

Current: `device_mapping: blue_hand` — a hardcoded name switch.  
Alternative: `device_mapping: ../data/my_mappings.json` — a path relative to the `.nt` file.

Pro path: extensible without code changes, user can maintain their own mapping file.  
Con: more complex loading, validation, error messages.

**Recommendation:** stay with named sets for now; add path support only when a third named set is
needed.

### B. Should `gathered_*.json` replace `blue_hand.json` or merge into it?

The gathered files appear to be raw auto-collected parameter dumps from Ableton. They have more
devices and slot9+ entries. Blue_hand.json is the curated subset.

**Recommendation:** keep blue_hand.json as the curated/authoritative source. Write a script in
`scripts/` that reads `gathered_*.json` and proposes additions/updates to blue_hand.json for
manual review.


---

## 3. `custom` — `data/custom_device_mappings.json`

### Schema

A flat `devices` array (no families). Per device, two positional arrays replace the named `slots`
dict:

```json
{
  "devices": [
    {
      "className": "Amp",
      "deviceName": "Amp",
      "fixed": true,
      "encoders": [
        { "number": 1, "name": "Amp Type" },
        { "number": 2, "name": "Bass" },
        ...
        { "number": 9, "name": "Dry/Wet" }
      ],
      "buttons": [
        { "number": 0, "name": "On/Off" },
        { "number": 1, "name": "Amp Type", "min": 0, "max": 6 }
      ]
    }
  ]
}
```

Rules:
- `encoders[0]` = physical knob 1, `encoders[1]` = physical knob 2, etc. No named slots.
- `buttons[0]` = physical switch button 1, etc.
- `number` is the Ableton parameter index (1-based; 0 = on/off).
- `name` is for HUD display.
- `fixed: true` — the device is fully declared. Warn at codegen time if the user requests
  more slots than the device has encoders defined.
- `min` / `max` on a button entry: optional cycle range. Populated by the gather script for
  quantized parameters. Omitting them defaults the button action to `pulse` (toggle to max then 0).
- Devices can have >8 encoders to support future paging (the paging system in `helpers.py` already
  handles slicing by page).

### How this maps to the existing runtime

At load time, `load_custom_intents()` converts the positional arrays to the same
`Dict[str, Dict[str, SlotEntry]]` interface that `family` and `blue_hand` use:

```
encoders[0]  →  slot1   → SlotEntry(parameter_number=number, parameter_name=name, action="cycle")
encoders[1]  →  slot2   → SlotEntry(...)
...
buttons[0]   →  switch1 → SlotEntry(parameter_number=number, ..., action="cycle"|"pulse")
buttons[1]   →  switch2 → SlotEntry(...)
```

Button action rule: if `min`/`max` are present and `max > 1`, action is `cycle` with those
ranges. Otherwise action is `pulse` (no range needed at codegen time; runtime sets to 127 then 0).

This conversion means **nothing in `gen_code.py`, `gen.py`, or `helpers.py` needs to change** for
the `custom` type — it speaks the same `SlotEntry` language as `family`/`blue_hand`.

### `fixed` validation

In `load_custom_intents()`, build a parallel `Dict[str, bool]` of `class_name → is_fixed`.
Expose it alongside the slot table. In `code_from_slot_assignments` (or at the point where slot
count is compared to controller encoder count), check: if a device is `fixed` and the number of
defined encoders is fewer than the user's requested slot count, print a clear warning:

```
Warning: Amp is fixed but only has 8 encoders defined; requested slot9 will be empty.
```

### Paging support (future-safe, no runtime change needed)

`encoders` may have >8 entries. The `custom_parameter_mappings` dict emits entries for **all** of
them (c_idx goes beyond 8). The existing `SelectedDeviceParameterPaging` in `helpers.py` already
slices these by page, so the paging system works for free once the data is in the dict.

### Code changes required

| File | Change |
|---|---|
| `ableton_control_surface_as_code/family_intents.py` | Add `_CUSTOM_PATH`, `load_custom_intents()` (converts positional arrays → slot dict), update `get_intents()` to handle `"custom"` |
| `ableton_control_surface_as_code/model_v2.py` | Expand `Literal["family", "blue_hand"]` → `Literal["family", "blue_hand", "custom"]` in both `RootV2` and `RootV2ModesOrModeless` |
| `data/custom_device_mappings.json` | Existing seed file; add `min`/`max` to button entries that have a cycle range |
| `scripts/gather_custom_json.py` | New gather script (see below) |

No changes needed to `gen.py`, `gen_code.py`, `helpers.py`, or templates — the `SlotEntry`
interface abstracts all three mapping types.

---

## Gather script: `scripts/gather_custom_json.py`

Same UDP protocol as `gather_family_json.py` (`PING/PONG`, `GET_DEVICE`, `GET_PARAMS`,
`GET_PARAM_VALUES`). Key differences in output format and recording logic:

### Output format

```json
{
  "devices": [
    {
      "className": "Amp",
      "deviceName": "Amp",
      "fixed": false,
      "encoders": [
        { "number": 1, "name": "Amp Type" }
      ],
      "buttons": [
        { "number": 1, "name": "Amp Type", "min": 0, "max": 6 }
      ]
    }
  ]
}
```

No `families` wrapper. `encoders` and `buttons` are positional arrays (order = controller position).

### Recording logic

- Moved parameter is **not** quantized → append to `encoders` list
- Moved parameter is quantized → append to `buttons` list with `min`/`max` from the param's
  `min_value`/`max_value`
- Each parameter can only appear once per device (deduplicate by `number`)
- On device change: print existing encoder/button counts so the user knows current state
- `fixed` starts as `false`; user sets it manually in the JSON after they are satisfied the mapping
  is complete

### CLI flags (same structure as existing script)

```
--host          default 127.0.0.1
--server-port   default 40844
--client-port   default 22021
--timeout       default 2.0
--interval      default 0.2   polling interval
--chunk-size    default 20
--output        default data/custom_device_mappings.json  (overwrites in place)
```

Unlike `gather_family_json.py` which writes timestamped output files, this script writes directly
to the canonical `data/custom_device_mappings.json` (or `--output` path). It reads the existing
file on startup to preserve entries for devices already defined, then merges new recordings in.

### Merge / resume behaviour

On startup, load `--output` if it exists. When a device is focused:
- If `class_name` is already in the file, resume from its existing `encoders`/`buttons` arrays
  (deduplication ensures no double entries)
- Print how many encoders and buttons are already recorded for this device

---

## Files to know

| Path | Role |
|---|---|
| `ableton_control_surface_as_code/family_intents.py` | Loads and dispatches between mapping sets |
| `ableton_control_surface_as_code/model_v2.py` | Parses `device_mapping:` from the `.nt` file |
| `ableton_control_surface_as_code/gen.py` | Threads `device_mapping` through code generation |
| `ableton_control_surface_as_code/gen_code.py` | Builds Python listener code from slot tables |
| `data/device_family_intents.json` | Family-based mapping set |
| `data/blue_hand.json` | Personal curated mapping set |
| `data/blue_hand.txt` | Human-readable reference dump of Ableton param lists |
| `data/gathered_*.json` | Auto-collected raw parameter dumps (source material for blue_hand) |
| `data/custom_device_mappings.json` | Custom positional mapping set (new) |
| `scripts/gather_family_json.py` | Gather script for `family`/`blue_hand` format (existing) |
| `scripts/gather_custom_json.py` | Gather script for `custom` format (to be created) |
| `live_surfaces/launch_control/ck_launch_control_16.nt` | Active surface config; uses `blue_hand` |
