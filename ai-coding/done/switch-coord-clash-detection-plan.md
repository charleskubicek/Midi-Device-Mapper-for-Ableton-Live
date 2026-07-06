# Switch-list coords escape clash detection — plan

## Symptom

In the `grid` surface, pressing a device-mode button (e.g. top-left
`grid-2:1`) ALSO triggers the mixer mute/solo bound to the same physical
button. "Both are being triggered."

## Root cause (provable, static)

`grid-2:N` flat addressing is row-major over the 4x4 button grid (notes
48-63), so `main_mode`'s device `switch-list: range grid-2:1-4` claims the
entire first row = notes 48,49,50,51. That row is *also* bound by other
`main_mode` mappings:

- note 48 = mixer `mute` (`grid-2:1`)
- note 49 = mixer `solo` (`grid-2:2`)
- note 50 = function `back8` (`grid-2:1::3`)
- note 51 = function `iterate_midi_pattern` (`grid-2:1::4`)

The generated `mode_main_mode_add_listeners` therefore attaches TWO listeners
to each of notes 48-51 (e.g. `switch1` + `set_mute_button` on 48), so one
press fires both. The HUD's own `mode_hud_labels` for main_mode label these
buttons as mute/solo/back8/iterate — never as device slots — confirming the
switch-list on row 1 is leftover/unintended.

This should have been caught at generation time. `validate_mappings`
(model_v2.py) detects exactly this kind of within-mode coord clash by
`ch_num` — BUT it only walks `withMidi.midi_maps`. `DeviceWithMidi` stores
switch-list buttons in a SEPARATE field, `switch_maps`
(model_device.py:88), which the validator never inspects. So the switch
coords are invisible to the clash check while the mixer mute coord is seen —
they're never compared, and the double-binding generates silently.

## Fix

### 1. Generator guard (the real bug)
Make `validate_mappings` consider every coord a mapping binds, not just
`midi_maps`. Collect coords from `midi_maps` (lists) AND `switch_maps`
(single coord each) per `withMidi`. Keeps the existing `ch_num` clash logic
and `CLASHING_MAPPINGS` error; just closes the field-coverage gap.

User confirmed: yes, the generator should error on this overlap.

### 2. Config fix (the actual remedy for grid)
Row 1 in `main_mode` is fully spoken for by mute/solo/back8/iterate (matching
the HUD labels). The device `switch-list` block in `main_mode` has no free
buttons, so remove it. `shift_mode` keeps its own switch-list
(`grid-2:1-8` -> slots 5-12), which is the real one and does not clash.

User confirmed intent: grid-2:1/grid-2:2 = mute/solo only.

## Tests (TDD)

- `test_validation`: a device switch (explicit `switch1` or `switch-list`)
  sharing a coord with a mixer button in the same mode now raises
  `CLASHING_MAPPINGS` (currently passes silently). Regression: a clean
  config with switches and no overlap still builds.

## Verify
- Regenerate grid, launch_control, parks — confirm no new false-positive
  clash errors and grid no longer double-binds row 1.
- `./build.sh`; report quality delta.
