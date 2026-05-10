# Custom Device Mappings

`data/custom_device_mappings.json` (or any path you point at) defines how the
generated control surface picks which device parameters to expose on which
encoders/buttons, on a per-device-class basis. Without it, the surface falls
back to identity mapping — first N continuous params land on encoders, first N
quantized params land on buttons. The JSON lets you curate a stable, named
layout per device.

## Wiring it in

Reference the file from your mapping `.nt`:

```nt
parameter_mappings_file: ../../data/custom_device_mappings.json
```

The path is resolved relative to the mapping file. `gen.py` reads it at
codegen time, validates it, and bakes the parsed dict into the generated
surface as a Python literal — the JSON is **not** opened at runtime.

## Top-level shape

```json
{
  "devices": [
    { "className": "...", "encoders": [...], "buttons": [...] }
  ]
}
```

`className` matches Ableton's `Device.class_name` (e.g. `Amp`, `AutoFilter2`,
`EQ Eight`). One entry per device class.

## Encoder entries

An encoder entry is either a **plain entry** or a **grouped entry**.

### Plain entry

Maps one encoder slot to one parameter index on the device.

```json
{ "number": 2, "name": "Bass" }
```

| field    | required | meaning                                             |
|----------|----------|-----------------------------------------------------|
| `number` | yes      | Index into `device.parameters` (0 = Device On).     |
| `name`   | no       | Override label shown in the HUD. Falls back to live param name. |
| `button` | no       | Reserved.                                           |

Order matters: encoders are filled in JSON order, paged by the controller's
encoder slot count.

### Grouped entry

One encoder slot, but the bound parameter changes based on the value of
another parameter on the same device. Use this when a device has mutually
exclusive controls (e.g. an LFO with a `T Mode` selector that toggles which
of `LFO Freq` / `LFO Time` / `LFO Rate` / `LFO 16th` is visible).

```json
{
  "controlledBy": "LFO T Mode",
  "group": [
    { "number": 15, "activeWhen": [0] },
    { "number": 16, "activeWhen": [1] },
    { "number": 17, "activeWhen": [2, 3] },
    { "number": 18, "activeWhen": [4] }
  ]
}
```

| field          | required | meaning                                                       |
|----------------|----------|---------------------------------------------------------------|
| `controlledBy` | yes      | Name of the selector parameter on the same device.            |
| `group`        | yes      | List of group members; one is active at any given time.       |

Each group member:

| field        | required | meaning                                                         |
|--------------|----------|-----------------------------------------------------------------|
| `number`     | yes      | Parameter index this member binds when active.                  |
| `activeWhen` | yes      | List of selector values that activate this member.              |
| `name`       | no       | Override label. Otherwise the live param's `.name` is used (so the HUD label tracks Ableton's own label as the selector changes). |

Validation (enforced at codegen):

- `activeWhen` values must be unique across all members in a group.
- `group` must be non-empty.
- A soft warning is printed if `controlledBy` doesn't match any declared name in the same device entry — the actual parameter is verified at runtime.

Runtime behaviour:

- The encoder always writes to whichever member's `activeWhen` contains the
  selector's current integer value. If no member matches, the encoder is
  inert until the selector changes.
- A value listener is attached to the selector parameter on device focus.
  Changing the selector — whether from the controller or directly in Live's
  device UI — re-bursts the HUD so the active member's name and value
  appear immediately.
- Listeners are torn down on device change.

## Button entries

```json
{ "number": 4, "name": "Amp Type", "min": 0, "max": 2 }
```

| field    | required | meaning                                                        |
|----------|----------|----------------------------------------------------------------|
| `number` | yes      | Parameter index to bind.                                       |
| `name`   | no       | HUD label override.                                            |
| `min`    | no       | Cycle floor (inclusive). Pair with `max`.                      |
| `max`    | no       | Cycle ceiling (inclusive).                                     |

Behaviour:

- With `min`+`max`: each press cycles `value` through `min..max` and wraps.
- Without `min`+`max` on a quantized param: cycles through the param's own `min..max`.
- Without `min`+`max` on a non-quantized param: pulses to `max`.

## Top-level device fields

| field        | required | meaning                                                         |
|--------------|----------|-----------------------------------------------------------------|
| `className`  | yes      | Ableton's `Device.class_name`.                                  |
| `deviceName` | no       | Documentation only.                                             |
| `fixed`      | no       | Documentation only — flag indicating the layout shouldn't drift.|
| `encoders`   | no       | List of plain or grouped encoder entries. Defaults to `[]`.     |
| `buttons`    | no       | List of button entries. Defaults to `[]`.                       |

## Full example

```json
{
  "devices": [
    {
      "className": "Amp",
      "deviceName": "Amp",
      "fixed": true,
      "encoders": [
        { "number": 2, "name": "Bass" },
        { "number": 3, "name": "Middle" },
        { "number": 4, "name": "Treble" },
        { "number": 5, "name": "Presence" },
        { "number": 6, "name": "Gain" },
        { "number": 7, "name": "Volume" },
        { "number": 9, "name": "Dry/Wet" }
      ],
      "buttons": [
        { "number": 1, "name": "Amp Type" },
        { "number": 8, "name": "Dual Mono" }
      ]
    },
    {
      "className": "AutoFilter2",
      "encoders": [
        { "number": 1, "name": "Frequency" },
        { "number": 2, "name": "Resonance" },
        {
          "controlledBy": "LFO T Mode",
          "group": [
            { "number": 15, "activeWhen": [0] },
            { "number": 16, "activeWhen": [1] },
            { "number": 17, "activeWhen": [2, 3] },
            { "number": 18, "activeWhen": [4] }
          ]
        }
      ],
      "buttons": [
        { "number": 4, "name": "Filter Type" },
        { "number": 14, "name": "LFO T Mode" }
      ]
    }
  ]
}
```

## Discovering parameter indices

`scripts/gather_custom_json.py` is the helper for harvesting parameter
indices from a focused device in Live. Use it to bootstrap an entry, then
hand-curate the order and add grouped entries where needed.

## Where the code lives

- **Schema + validation**: `ableton_control_surface_as_code/model_custom_devices.py`
- **Codegen entry point**: `ableton_control_surface_as_code/gen.py` (calls `validate_custom_device_mappings`)
- **Runtime resolution**: `source_modules/helpers.py` — `_resolve_encoder`, `_resolve_switch`, `_resolve_group_member`, and the selector-listener machinery.
