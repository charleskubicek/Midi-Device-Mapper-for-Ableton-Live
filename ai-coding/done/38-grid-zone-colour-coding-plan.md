# Grid zone colour-coding — HUD outlines + Grid buttons

**Goal:** make the smart-zoning zones *visible* by colour, in two coherent places:
1. **HUD** — tint the **dial outline** (encoder ring) and **button outline** with the
   slot's zone hue. The value-fill arc stays as-is (it shows value).
2. **Grid controller** — the physical BU16 button LEDs show the same zone hues, so the
   operator's eye maps a HUD button to its physical key **by colour**. (Phase 1 = static
   hues set in the Grid Editor, zero Ableton code.)

Colour is a property of the **template slot**, independent of what resolved — an
unmapped (dim) slot still shows its zone hue. Single source of truth: a new
`zone_colors` map in `data/synth_zone_tables.json` feeds the HUD (pushed over the wire)
AND the Grid Phase-1 table (generated from the same map), so they cannot drift.

Scope this pass (decided 2026-07-12): **HUD tinting + Grid Phase-1 colour table.**
GridLedClient (dynamic Phase 2 — brightness/state over MIDI) is a later pass.

---

## 1. Colour source — `zone_colors` in the JSON

Seven zones exist in the shipped template (derive programmatically, don't hand-list):
`osc, filter, lfo, env, global, signature` (pots) + `character` (buttons B9–16).

Add a top-level `zone_colors: { <zone>: "RRGGBB" }` to `synth_zone_tables.json`
(hex, no `#`). `model_synth_zones.py` gains a `zone_colors` field (its `extra='forbid'`
would otherwise reject it — same trip as the `comment` field) and a validator rule:
**every zone used in the template must have a colour**, no orphan colours.

**Proposed palette (needs sign-off — see §7):**

| zone | hex | note |
|---|---|---|
| osc | `E0A33E` | amber |
| filter | `33B5A6` | teal |
| lfo | `9B8CE0` | violet |
| env | `E06B86` | rose |
| global | `57B368` | green |
| signature | `8A9A4B` | warm/olive green (kin to global) |
| character | `5B8BC4` | slate blue (button-only zone) |

`filter` and `osc` appear on both pots and buttons → same hex in both places
(consistency by construction). Button LEDs use the `filter / osc / character` subset;
those three hexes are exactly what the Grid Editor sets on the BU16 (§6).

---

## 2. Data flow — a per-burst `ZONES` message (not a field on SLOT)

Colour is emitted as its **own** message inside the burst, keyed by wire index — NOT
bolted onto `SLOT`. Why: colour is template metadata, must cover *every* slot including
empty/unmapped ones, and the presenter (which owns the resolver) is the clean producer.
Tying it to the resolved SLOT payload would be fragile and lose the tint on empty slots.

Emitted **every** (non-suppressed) burst, inside `DEVICE…COMMIT`:
- zoned device → full slot→colour map;
- non-zoned device → **empty** `ZONES` (actively clears any previous synth's tint —
  same stale-state care as HIDE/`dismissed`).

Wire form (self-describing, keyed by wire index, mirrors dense SLOT emission):
```
ZONES|<n>|<kind>|<idx>|<hex>|<kind>|<idx>|<hex>| … × n
```
`kind` ∈ `dial|button`, `idx` = wire index (same space as SLOT), `hex` = `RRGGBB`.
Empty burst: `ZONES|0`. Old Swift falls to `.unknown` and ignores it (forward-compat);
new Swift with no ZONES line defaults to no tint (backward-compat).

### Index alignment (verified)
- **Dials:** `_build_dial_payloads` maps wire idx `W` → `real_parameters[W+1]` →
  **surface slot `W+1`**. So dial wire idx `W` ← zone of surface slot `W+1`.
- **Buttons:** presenter's `_active_switch_slot_assignments` gives `(wire_idx, slot)`;
  colour ← zone of surface `slot`. Keyed by the same `wire_idx` the SLOT uses.

### Producer path (Python)
- `param_resolver.py`: `zone_for_slot(kind, surface_slot)` → zone or None (None when
  not zoned or slot not in template); `color_for_slot(kind, surface_slot)` → hex or None.
  `_build_zone_tables` also carries the `zone_colors` map.
- `hud_presenter.emit_burst`: when the device is zoned, build
  `{'dial': {surface_slot: hex}, 'button': {surface_slot: hex}}` and pass through
  `Remote.device_update(..., zone_colors=…)`.
- `helpers.py` `_build_dial_payloads` / `_build_button_payloads` already know
  wire_idx ↔ surface slot; build a parallel `(wire_idx, hex)` list. `refresh_burst`
  emits the `ZONES` line between `send_page_info` and the SLOT loop (inside begin/flush).
- `hud_client.py` + `hud_protocol.py`: `encode_zones(entries)` / `send_zones(entries)`
  (+ `NullHudClient` no-op). Pure encode tested in `test_hud_protocol.py`.

---

## 3. Receiver (Swift HUD)

- `WireProtocol.swift`: new `case zones([(SlotKind, Int, String)])`; `parse` handles
  `ZONES` (never crashes on malformed — bad hex/idx tokens skipped). Empty → `.zones([])`.
- `DeviceState.swift`: `pendingDialColors`/`pendingButtonColors` (`[Int: Color]`),
  written by `.zones`, published on `COMMIT` to `dialColors`/`buttonColors`
  (cleared when the burst carried an empty/again-absent map — a non-zoned burst wipes
  the tint). Hex→`Color` helper in core.
- `HUDView.swift`:
  - `DialSlotView` — recolour the base ring stroke (`:263`) with `dialColors[index]`
    when present, else today's `Color.gray.opacity(0.3)`. Value arc (`:269`) unchanged.
  - `ButtonSlotView` — recolour the border stroke (`:307`) with `buttonColors[index]`,
    else today's white. Fill/active behaviour unchanged.
  - Index the colour by the cell's slot index (same index the slot uses).

---

## 4. Button ↔ controller colour parity

The button-zone hexes (`filter / osc / character`) are **the same values** set on the
physical Grid BU16 LEDs. HUD button outline colour == controller button LED colour, by
sharing `zone_colors`. This is the explicit requirement ("button colours map to the
controller"): one palette, two renderers.

---

## 5. Implementation steps

**A. Palette sign-off** ✅ — user approved §7 hexes (2026-07-13) and asked that they be
configurable → they live as data in `zone_colors` (edit + regenerate; nothing hardcoded).

**B. JSON + validator (TDD)** ✅ — `zone_colors` in `synth_zone_tables.json`;
`model_synth_zones.py` gained the field + "colour every template zone, no orphan,
valid RRGGBB" rule; `synth_zone_tables.md` shows a colour column. Tests in
`test_model_synth_zones.py::TestZoneColors`.

**C. Resolver + wire (Python, TDD)** ✅ — `zone_for_slot`/`color_for_slot`/`is_zoned` +
`zone_colors` in `_build_zone_tables`; `encode_zones`/`send_zones` (+ Null); presenter
builds dial (parallel to real_params) + button (wire-keyed) maps; `helpers` emits `ZONES`
in `refresh_burst` (empty when non-zoned → clears). Tests: `test_hud_protocol`,
`test_synth_zone_resolver::TestZoneColors`, `test_helpers::TestRemoteZoneColors`.

**D. Swift (TDD)** ✅ — `ZoneTint` + `.zones` parse case; `DeviceState` pending/published
`dialColors`/`buttonColors` (cleared on DEVICE, published on COMMIT); `RegionSnapshot`
carries them; `HUDView` recolours dial ring (`ringColor`) + button border (`borderColor`)
via `Color(zoneHex:)`. Swift tests green (75). `hud_protocol.md` updated with `ZONES`.

**E. Grid Phase-1 table** ✅ — `live_surfaces/grid/grid_led_colours.md` (per-module 4×4
colour table + RGB + Lua snippet, from `zone_colors`). Static, zero Ableton code.

**F. Regenerate surface + build** — regenerate `ck_grid`; run `./build.sh`; commit;
user deploys + restarts Live and rebuilds/restarts the HUD (`create-app-bundle.sh`).

---

## 6. Grid Phase-1 (static, Grid Editor)

Per element, set `led_color(1, {r,g,b,a})` on its init event from the zone hue:
- grid-2 (LEFT pots): slots 1–8 osc (amber), 9–12 filter (teal), 13–16 lfo (violet).
- grid-3 (RIGHT pots): 17–24 env (rose), 25–28 global (green), 29–32 signature (olive).
- grid-1 (LEFT buttons): B1–4 filter (teal), B5–8 osc (amber), B9–16 character (slate).

Generated table + Lua ships as a doc artifact (step E). This is the zero-Ableton-code
self-documenting rig; Phase 2 (GridLedClient) later adds live brightness/state.

---

## 7. Open decision

**Palette (§1).** Sign off the seven hexes — especially `signature` (proposed
olive/warm-green, distinct from `global`) and `character` (proposed slate-blue,
button-only). `filter`/`osc` are shared pot+button and drive the physical BU16, so pick
hues that read well as LEDs too.

---

## 8. Guardrails (from CLAUDE.md)

- Cross-language change: Python `encode_zones` and Swift `WireProtocol.parse` must stay
  in sync — add round-trip tests on both sides (the `LayoutCell` shape `assert` is the
  precedent). "Testing" includes rebuilding + restarting the Swift HUD, not just pytest.
- Update `hud_protocol.md` with the `ZONES` message (catalog + sequence).
- Let the **user redeploy** (Live) and rebuild/restart the HUD. Don't run `deploy.sh`.
- Run `./build.sh` before committing; mention `grid-zone-colour-coding-plan`.
