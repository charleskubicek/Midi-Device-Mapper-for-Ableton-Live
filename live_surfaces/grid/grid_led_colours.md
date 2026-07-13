# Grid LED zone colours — Phase 1 (static, set in the Grid Editor)

**Zero Ableton code.** Set each element's LED once in the Grid Editor (on its init
event) so the rig is self-documenting the moment smart-zoning is on. These hues match
the HUD outline tints exactly — both come from `zone_colors` in
`data/synth_zone_tables.json` (the single source). **If you change the palette there,
update this doc.** Phase 2 (`GridLedClient`, dynamic brightness/state over MIDI) is a
later pass.

## Palette (from `zone_colors`)

| Zone | Hex | RGB (0–255) | Where |
|---|---|---|---|
| osc | `E0A33E` | `224, 163, 62` | pots + buttons |
| filter | `33B5A6` | `51, 181, 166` | pots + buttons |
| lfo | `9B8CE0` | `155, 140, 224` | pots |
| env | `E06B86` | `224, 107, 134` | pots |
| global | `57B368` | `87, 179, 104` | pots |
| signature | `8A9A4B` | `138, 154, 75` | pots |
| character | `5B8BC4` | `91, 139, 196` | buttons |

## Per-module layout (4×4 each, top-left = first slot, row-major)

Blocks fall on clean 4-element rows, so each row of a module is one colour.

### grid-2 — LEFT PO16 (pots, surface slots 1–16)
```
row 1  slots  1– 4   osc     amber   224,163, 62
row 2  slots  5– 8   osc     amber   224,163, 62
row 3  slots  9–12   filter  teal     51,181,166
row 4  slots 13–16   lfo     violet  155,140,224
```

### grid-3 — RIGHT PO16 (pots, surface slots 17–32)
```
row 1  slots 17–20   env        rose    224,107,134
row 2  slots 21–24   env        rose    224,107,134
row 3  slots 25–28   global     green    87,179,104
row 4  slots 29–32   signature  olive   138,154, 75
```

### grid-1 — LEFT BU16 (buttons, surface slots B1–B16)
```
row 1  B1– B4   filter     teal     51,181,166
row 2  B5– B8   osc        amber   224,163, 62
row 3  B9–B12   character  slate    91,139,196
row 4  B13–B16  character  slate    91,139,196
```

The button hues (filter/osc/character) are what the HUD draws on its button outlines —
so a physical key and its HUD cell read as the same colour.

## Lua (per element init event)

Grid LED layer 1 is the pot/button layer; values are 0–255. Set the element's colour on
its init event, e.g. the osc rows on grid-2:

```lua
-- osc (amber) — put on each osc element's init
led_color(1, 224, 163, 62)
-- filter (teal)
-- led_color(1, 51, 181, 166)
-- lfo (violet)
-- led_color(1, 155, 140, 224)
-- env (rose)      led_color(1, 224, 107, 134)
-- global (green)  led_color(1, 87, 179, 104)
-- signature(olive)led_color(1, 138, 154, 75)
-- character(slate)led_color(1, 91, 139, 196)
```

(Use `led_intensity` to taste; Phase 2 will drive intensity live from Ableton.)
