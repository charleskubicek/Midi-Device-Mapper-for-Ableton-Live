# Mapping File Reference

A mapping `.nt` file is the per-surface config: it points at a controller
description, declares top-level options, and lists the modes and mappings that
bind physical controls to Ableton actions. This doc walks through every
top-level attribute and mapping type using
`live_surfaces/launch_control/ck_launch_control_16.nt` as the running example.

## Top-level attributes

```nt
controller: controller_lc.nt
ableton_dir: /Applications/Ableton Live 12 Suite.app
parameter_mappings_file: ../../data/custom_device_mappings.json
remote_on: false
hud: device_only
mode-button:
    button: row-3:1
    type: shift
modes:
    - ...
```

| Attribute                  | Required | Default       | Purpose |
| -------------------------- | -------- | ------------- | ------- |
| `controller`               | yes      | —             | Path (relative to this file) to the controller `.nt` describing the physical layout (rows, MIDI channels, light colors). |
| `ableton_dir`              | yes      | —             | Absolute path to the Ableton app bundle. `deploy.sh` copies the generated surface into this app's `MIDI Remote Scripts` directory. |
| `parameter_mappings_file`  | no       | none          | Path to the custom device-mapping JSON. See [`custom_device_mappings.md`](./custom_device_mappings.md). When omitted, the surface falls back to identity parameter mapping. |
| `remote_on`                | no       | `false`       | When `true`, the generated surface emits OSC parameter updates to a multi-client target (localhost + a hard-coded LAN IP). When `false`, OSC is a no-op (`NullOSCClient`). |
| `hud`                      | no       | `on`          | Controls the floating HUD overlay. See [HUD modes](#hud-modes). |
| `mode-button`              | no       | none          | Declares a physical button that drives the mode FSM. See [Modes](#modes). |
| `modes`                    | no       | none          | Named list of modes, each with its own mappings. If omitted, you can use a flat top-level `mappings:` instead and the generator wraps it in a single anonymous mode. |

### HUD modes

The HUD is a separate macOS app that displays a floating overlay of currently
mapped controls. The generated surface pushes layout + per-slot updates over
UDP. The `hud` attribute decides what gets sent:

| Value         | Behavior |
| ------------- | -------- |
| `on`          | Default. All mappings render in the HUD: device parameters (live values), plus static labels for `mixer`, `functions`, `track-nav`, `device-nav`, `transport`, `parameter-pager`. |
| `off`         | The generated surface uses `NullHudClient` — no UDP traffic at all. Use this if you don't run the HUD app. |
| `device_only` | The HUD client is live, but only `device`-mapped slots show content. Static labels for non-device mappings are suppressed; those slots stay blank. Useful when you only care about seeing the focused device's parameter names/values and find the static labels for buttons noisy. |

The choice is baked in at codegen — change it and regenerate to switch.

## Modes

A mapping file is either modeless (flat `mappings:`) or has explicit `modes:`.
With modes, a single physical button cycles or holds-to-shift between named
mode states; each mode has its own complete set of mappings.

```nt
mode-button:
    button: row-3:1
    type: shift            # 'switch' (toggle/cycle) or 'shift' (held)
modes:
    -
        name: main_mode
        on_color: red_low  # color shown on mode-button while this mode is active
        mappings: ...
    -
        name: shift_mode
        on_color: green_full
        mappings: ...
```

- `type: switch` — pressing the mode button advances to the next mode in the
  list, wrapping at the end.
- `type: shift` — the second mode is active only while the button is held;
  releasing returns to the first.
- `on_color` must be a name defined in the controller's `light_colors` block.
  It's rendered on the mode button itself so you can see which mode is active.

## Encoder coordinates

Mappings reference physical controls by **coordinate strings** parsed by a Lark
grammar in `encoder_coords.py`. The shapes:

| Form                  | Meaning |
| --------------------- | ------- |
| `row-1:3`             | Row 1, column 3 (single control). |
| `row-1:1-8`           | Row 1, columns 1 through 8 (range). |
| `row-1:5-7,row-2:5-7` | Multiple ranges concatenated. |
| `row-3:4 toggle`      | Refinement: button acts as a toggle rather than momentary. |
| `row-3:2 mode`        | Refinement: button acts as a mode trigger. |
| `row-1:1 map_mode_absolute` | Refinement: encoder uses absolute MIDI value mapping. |

Row numbers and column counts come from the controller file.

## Mapping types

Each entry under a mode's `mappings:` (or top-level modeless `mappings:`) has a
`type` and type-specific keys. The example file exercises all the common ones.

### `device` — bind encoders/buttons to a device's parameters

```nt
- type: device
  track: selected
  device: selected
  mappings:
      encoder-list:
          - { range: row-1:1-8, slots: 1-8 }
          - { range: row-2:1-8, slots: 9-16 }
      on-off: row-3:4 toggle
```

- `track` / `device`: which device to bind. `selected` follows the focused
  track/device; you can also specify a track name and a device name to pin to a
  fixed device.
- `mappings.encoder-list`: list of `range` (controller coords) → `slots`
  (parameter slot indices, 1-based). The slot numbers feed into the custom
  device-mapping JSON, or fall back to the device's parameter list by index.
- `mappings.on-off`: a button that toggles the device's on/off state.
- Other keys: `switch1`..`switch4` map buttons to discrete switch positions
  on the focused device (used in `shift_mode` in the example).

### `mixer` — bind to selected track's mixer

```nt
- type: mixer
  track: selected
  mappings:
      mute: row-3:2
      solo: row-3:3
      volume: row-1:8
      pan: row-2:8
      sends: row-1:5-7,row-2:5-7
      arm: row-3:3      # also available
```

`sends` accepts a multi-coord range — each coord controls send A, B, C, …

### `functions` — bind buttons to named Python functions

```nt
- type: functions
  mappings:
      iterate_midi_pattern: row-3:5
      back8: row-3:6
      update_colors: row-3:7
      press_rack_random_button: row-3:8
      record_midi_from_track_to_new_track: row-3:2 toggle
      clip_extend: row-5:2
      clip_delete_end: row-5:1
```

The function names must match methods exposed by a `Functions` class in a
`functions.py` file sitting next to the mapping file. The generator copies that
file into the generated surface. `toggle` makes a button latch instead of fire
on press.

### `track-nav` — move the selected-track cursor

```nt
- type: track-nav
  mappings:
      left: row-4:1
      right: row-4:2
```

### `device-nav` — move the selected-device cursor within a track

```nt
- type: device-nav
  mappings:
      left: row-5:1
      right: row-5:2
      first-last: row-3:8   # also available; jumps to first or last device
```

### `transport` — play/stop/record etc.

Not used in `ck_launch_control_16.nt`, but supported. Maps named transport
calls (e.g. `play`, `stop`, `record`) to single coords.

### `parameter-pager` — page through device parameter banks

```nt
- type: parameter-pager
  encoders:
      inc: row-4:2
      dec: row-4:1
```

When a device has more parameters than encoders, the pager shifts which slots
are visible. `inc` / `dec` are buttons that step the visible page forward /
backward.

## How the file is processed

1. `gen.py` parses the mapping `.nt` via `RootV2ModesOrModeless` →
   `RootV2`.
2. The referenced controller file is parsed into `ControllerV2`.
3. Each mapping has its encoder coords resolved to `MidiCoords` (channel +
   note/CC number + type), producing `*WithMidi` models.
4. Cross-mapping conflicts (two mappings claiming the same MIDI coord in the
   same mode) are detected and reported with source locations.
5. Mappings are rendered through `string.Template` files in `templates/` to
   produce a Python control surface in a directory next to the mapping file,
   named after the file's stem.
6. `deploy.sh` (also generated) copies that directory into the Ableton app's
   `MIDI Remote Scripts` folder. Restart Ableton to pick it up.

## Quick reference: minimal modeless file

```nt
controller: my_controller.nt
ableton_dir: /Applications/Ableton Live 12 Suite.app
mappings:
    -
        type: mixer
        track: selected
        mappings:
            volume: row-1:1
```

No `modes:`, no `mode-button:` — the generator wraps the mappings in a single
fake mode internally, and no mode button is wired up.
