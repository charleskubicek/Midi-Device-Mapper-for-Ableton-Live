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
| `on`          | Default. All mappings render in the HUD: device parameters (live values), plus static labels for `mixer`, `functions`, `track-nav`, `device-nav`, `transport`, `parameter-pager`, `clip`. |
| `off`         | The generated surface uses `NullHudClient` — no UDP traffic at all. Use this if you don't run the HUD app. |
| `device_only` | The HUD client is live, but only `device`-mapped slots show content. Static labels for non-device mappings are suppressed; those slots stay blank. Useful when you only care about seeing the focused device's parameter names/values and find the static labels for buttons noisy. |

The choice is baked in at codegen — change it and regenerate to switch.

### `show-hud-on` — when the HUD appears

`hud:` controls *what content* shows; `show-hud-on:` controls *when the HUD pops up*.
They are orthogonal — `hud: off` is still the master kill switch.

| Value           | Behavior |
| --------------- | -------- |
| `controller-nav`| **Default.** The HUD burst fires **only** on a controller device-nav action (device-nav left/right/first/last). Selecting a device by mouse or track navigation still remaps the encoders and pushes OSC, but the HUD is hidden (a `HIDE` is sent so turning a knob can't wake it on a stale device). Pair with a `hud_toggle` binding to summon the HUD on demand for a mouse-selected device. |
| `selection`     | The HUD follows Live's selected device: whenever the focused device changes (mouse click, track select, device-nav), a burst shows the HUD. This was the behavior before `show-hud-on` existed. |

```
show-hud-on: controller-nav
```

Note: `controller-nav` covers device-nav buttons only — **track-nav is excluded** (stepping
tracks via the controller stays silent). `show-hud-on` does not affect the HUD's
*dismiss*/auto-hide behavior, which is a separate concern (auto-timer, navigate-away HIDE,
the `hud_toggle` binding).

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
| `row-3:4 momentary`   | Refinement: button acts on *both* edges — on-while-held for a device param, fire-on-press-and-release for a function. Buttons act once on press by default, so this is the opt-in for hold behavior. |
| `row-3:4 toggle`      | **Deprecated** — `toggle` is now the default (act once on press) and emits a removal warning at generation time. |
| `row-3:2 mode`        | Refinement: button acts as a mode trigger. |
| `row-1:1 map_mode_absolute` | Refinement: encoder uses absolute MIDI value mapping. |

Row numbers and column counts come from the controller file.

### Controller `button-behaviour` (hardware press mode)

A press-once button (switch, nav, function, on-off) acts once per press. *How*
the hardware reports a press differs by controller, and the wrong assumption
makes a button fire every **other** press. Declare it once per controller file:

```nestedtext
button-behaviour: momentary   # default — omit unless your buttons are toggle
```

- `momentary` (default): the button sends its "on" value when pressed and `0`
  when released (two MIDI events per press). The guard acts on the press and
  ignores the release.
- `toggle`: the button sends a single alternating on/off event per press (no
  release event), as configured in e.g. Novation Components. The guard acts on
  **every** edge, because each edge is its own press.

The hold-style mode/shift button is handled separately and always uses
press-and-release, regardless of this setting. Unsure which your buttons use?
Run `update.py doctor`, press each button twice, and read the report
(`./bin/tail_logs.sh`) — it classifies each button and prints the exact
`button-behaviour:` to set.

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
      on-off: row-3:4
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
      record_midi_from_track_to_new_track: row-3:2
      clip_extend: row-5:2
      clip_delete_end: row-5:1
```

The function names must match methods exposed by a `Functions` class in a
`functions.py` file sitting next to the mapping file. The generator copies that
file into the generated surface. Function buttons fire once on press by default;
add `momentary` to fire on both press and release. (`toggle` is deprecated — it
is now the default and can be removed.)

**Reserved built-in: `hud_toggle`.** One name is intercepted and does *not* need an
entry in `functions.py`:

```nt
- type: functions
  mappings:
      hud_toggle: row-4:8
```

Pressing the bound button toggles the floating HUD: the first press dismisses it
(sticky HIDE), the next press re-shows it with the current device/mode labels. Use
this when you want to clear the overlay on demand from the controller rather than
reaching for the `Esc` key. The HUD also auto-dismisses after a period of inactivity
and when you navigate away from the focused device, so the binding is optional. No
effect when `hud: off`. (If the auto-dismiss timer already hid the HUD, the first
press may be a no-op HIDE — press again to re-show.)

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

#### Pager in a shift mode — page preview

The pager often has to live in a *shift* mode rather than the base mode, simply
because its `inc`/`dec` buttons are already occupied in the base mode (on the
`grid` surface, for example, those buttons are `device-nav` left/right in
`main_mode`). The catch: while you hold shift, the device encoders are rebound
to other things (mixer volume/pan/sends), so the HUD shows *those* labels — not
the device page you are paging. Without help you cannot see the parameters you
just paged to until you release shift.

To fix this, pressing the pager from a shift mode emits a one-shot **page
preview** burst: the HUD shows the *base* mode's device page (the actual new
parameter names) for that device, while you stay in shift. The preview persists
until the next normal burst overwrites it — in practice, **releasing shift**
(which repaints the live base-mode view) or paging again. It is *not* cleared by
moving a natively-mapped mixer encoder (those bypass the script entirely) nor by
most shift device-switch presses; the preview simply stays up while you keep
holding shift, which is when you want to read it. This is automatic whenever the
pager's mode differs from the mode that binds the device encoders; no config
flag is needed.

The HUD shows a single combined page indicator (e.g. "1/3") between the device
name and the grid rows. It only appears when more than one page exists. The
indicator shows the current encoder page over the larger of the encoder and
button page totals — so if a device has 5 encoder pages and 2 button pages, the
indicator reads e.g. "1/5". When the encoder page exceeds the button page count
(e.g. page 3 of 5), the button slots display their last defined page
(page 2).

The HUD shows a single combined page indicator (e.g. "1/3") between the device
name and the grid rows. It only appears when more than one page exists. The
indicator shows the current encoder page over the larger of the encoder and
button page totals — so if a device has 5 encoder pages and 2 button pages, the
indicator reads e.g. "1/5". When the encoder page exceeds the button page count
(e.g. page 3 of 5), the button slots display their last defined page
(page 2).

### `clip` — edit the currently-detailed clip

Binds controls to attributes of the clip shown in Live's detail view
(`song().view.detail_clip`). Each listener acts on whatever clip is detailed at
the time, and is a no-op when none is. Audio-only attributes (`gain`, `pitch-*`,
`warping`) silently do nothing on MIDI clips.

```nt
- type: clip
  mappings:
      gain: row-1:1               # absolute encoder, 0..1
      pitch-coarse: row-1:2       # absolute encoder, -48..48 semitones
      pitch-fine: row-1:3         # absolute encoder, -50..50
      loop-start-inc: row-2:1     # button, +1 beat per press
      loop-start-dec: row-2:2     # button, -1 beat
      loop-end-inc: row-2:3
      loop-end-dec: row-2:4
      start-marker-inc: row-2:5
      start-marker-dec: row-2:6
      end-marker-inc: row-2:7
      end-marker-dec: row-2:8
      looping: row-2:9            # button, toggle on/off
      warping: row-2:10           # button, toggle on/off (audio only)
      duplicate-loop: row-2:11    # button
      sync-loop-and-markers: row-2:12   # button: start/end markers := loop start/end
      move-loop-forward: row-2:13       # button: shift loop region +1 beat (size kept)
      move-loop-backward: row-2:14      # button: shift loop region -1 beat
```

Encoders map an **absolute** 0..127 value onto the property's bounded range, so
they suit controllers whose encoders send absolute values (the default). The
unbounded loop/marker positions (in beats) use inc/dec **button** pairs that
nudge one beat per press. Clip controls must be **dedicated** — a clip control
sharing a MIDI coord with another mapping in the same mode is a generate-time
error (the standard clash check). The HUD shows each clip control's name
prefixed with `clip: ` (e.g. `clip: gain`).

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
