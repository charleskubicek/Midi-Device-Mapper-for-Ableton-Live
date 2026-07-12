# Grid dual-PO16 smart-zoning synth surface

**Goal:** turn BOTH PO16 modules (32 linear pots) + the left BU16 (16 RGB buttons) of the
Intech Studio Grid into a *predictable* synth control surface via a new first-class
concept: **smart-zoning**. The same physical pot drives the same semantic parameter on
every enrolled synth (Wavetable, Drift, Operator, Analog), each synth's signature
controls live in a fixed "special" area, and the Grid's per-element LEDs make the layout
self-documenting.

Handoff doc — self-contained. Decisions were resolved interactively (2026-07-10); this
captures them, the exact 32-slot parameter matrix (DRAFT — review §5 before building),
and the implementation steps.

---

## 1. What smart-zoning is (and is not)

Smart-zoning is a **new resolution tier**, not more entries in
`data/custom_device_mappings.json`:

- `custom_device_mappings.json` stays **effects-only**. Its lists are *positional*
  (list index = physical knob), so editing an entry silently reshuffles knobs — exactly
  the muscle-memory failure smart-zoning exists to prevent. No synth entries go there.
- Smart-zoning is **role-keyed**: a fixed zone template (semantic roles at fixed
  physical positions) plus shipped per-synth tables saying which parameter fills each
  role. The layout can never drift because positions belong to the template, not to any
  per-synth list.
- Enrollment is a **surface toggle**: the mapping `.nt` says `smart-zoning: on`. Any
  focused synth that has a shipped zone table gets the zoned layout; everything else
  behaves exactly as today. The shipped table IS the enrollment list — no per-instrument
  config anywhere.
- A synth **without** a zone table (random VST, Meld/Serum before extraction) falls back
  to today's behavior (BOB → factory banks → param-order paging). Zoning never guesses.
- For a zoned synth, the zone layout is **page 1**; the parameter-pager still pages
  onward into Live's factory banks (full access preserved). Standard banks start at
  page 2, same as the existing BOB behavior.

Resolution order per focused device when `smart-zoning: on`:
**zone table → BOB (custom mappings) → factory banks → unknown-class fallback.**
With the toggle off, the chain is unchanged from today.

---

## 2. Hardware reality

Physical row (magnetic modules, left→right): **`BU16 · PO16 · PO16 · BU16`** —
**all four already modeled** in `live_surfaces/grid/controller_grid.nt` as groups
1 (buttons, note C-2–DS-1), 2 (knobs, CC 48–63), 3 (knobs, CC 32–47),
4 (buttons, note C2–DS3), all channel 1, no MIDI clashes. **No controller-file changes
needed.**

`ck_grid.nt` **already binds everything this plan needs**: `grid-3:1-16` → device
slots 1–16, `grid-2:1-16` → slots 17–32, `grid-1:1-16` → device button slots. So there
is **no new mapping `.nt`** — the change is resolution-side (`smart-zoning: on` in
`ck_grid.nt`) plus the shipped zone tables.

- `grid-1` (left BU16) = the 16 synth-zone buttons.
- `grid-4` (right BU16) keeps ALL current duties: shift/mode (`grid-4:4::1`),
  mute/solo, functions, device-nav, parameter-pager. **Out of scope.**
- **PO16 = absolute linear potentiometers** → the jump problem (§7) and the LED plan (§8).
- Every Grid element has an RGB LED, set in Lua: `led_color(layer, {r,g,b,a})` (`glc`),
  plus `led_intensity`; layer 1 is the button/pot layer. Grid has MIDI RX, so the surface
  can drive LEDs over MIDI. Ref: docs.intech.studio → Actions → LED / MIDI Actions.

---

## 3. The zone layout — one zone group per module

**Decision: each module reads as a self-contained unit.** Left module (grid-2) = sound
generation; right module (grid-3) = shaping/global.

```
grid-2 (left PO16)                grid-3 (right PO16)
O1  O2  O3  O4   osc 1            E1  E2  E3  E4   amp env (ADSR)
O5  O6  O7  O8   osc 2            E5  E6  E7  E8   env 2 / mod env (ADSR)
F1  F2  F3  F4   filter           G1  G2  G3  G4   global (fixed roles)
L1  L2  L3  L4   LFO              G5  G6  G7  G8   signature (per-synth)
```

**Slot numbering** — ⚠ **SHIPPED orientation differs from the original draft
below.** ck kept `ck_grid.nt` binding grid-2 (LEFT PO16) → slots **1–16** and
grid-3 (RIGHT) → slots **17–32**, and wants osc/filter/LFO under the LEFT hand.
So the **zone template swaps its two halves** (the fix lives in
`synth_zone_tables.json`, not the `.nt`):
- grid-2 (LEFT) = slots **1–16**: O1–O8 = slots 1–8, F1–F4 = slots 9–12, L1–L4 = slots 13–16.
- grid-3 (RIGHT) = slots **17–32**: E1–E8 = slots 17–24, G1–G4 = slots 25–28, S1–S4 = slots 29–32.
- Within-module row order (§3 diagram) is preserved; only the ±16 block offset flips.
- Pinned by `test_model_synth_zones.py::test_module_orientation`.

*Original draft (superseded — kept for context): grid-3 = slots 1–16 (E/G),
grid-2 = slots 17–32 (O/F/L). The §4 per-row (N) values still use this old
numbering; the authoritative slot→role map is the shipped JSON + the block above.*

Zone colours (LEDs + HUD): **osc=amber, filter=teal, LFO=violet, env=rose, global=green**
(signature row shares green, dimmer or warmer variant — pick during LED work).

Global row split (decision): **G1–G4 fixed roles** (identical meaning on every synth),
**G5–G8 signature** (each synth's character controls, free choice per synth).

---

## 4. Per-synth pot matrix — 32 slots (DRAFT, review before building)

**Parameter names are byte-exact** — verified against `data/devices_12.json`
(all four synths present). Watch exact casing/spacing; Operator has params with
trailing spaces (e.g. `A Fix On `) — none used here, but never hand-retype names.

`className` keys: Wavetable → **`InstrumentVector`**, Drift → **`Drift`**,
Operator → **`Operator`**, Analog → **`UltraAnalog`**.
*(Diva is not part of the current synth set — ignore any old references.)*

† **Operator is an FM deviation** (documented, wanted): a 2-osc template can't represent
4 FM operators, so its osc rows become operator-A/B coarse+fine+level+feedback, and
`Algorithm` goes on button B16. Do **not** force it into the osc template.

### Left module — osc 1 (slots 17–20), osc 2 (21–24), filter (25–28), LFO (29–32)

| Slot | Role | Wavetable | Drift | Operator † | Analog |
|---|---|---|---|---|---|
| O1 (17) | Osc 1 timbre | `Osc 1 Pos` | `Osc 1 Shape` | `A Coarse` | `OSC1 Shape` |
| O2 (18) | Osc 1 timbre 2 | `Osc 1 Effect 1` | `Osc 1 Shape Mod Amt` | `A Fine` | `OSC1 PW` |
| O3 (19) | Osc 1 pitch | `Osc 1 Transp` | `Osc 1 Oct` | `Osc-A Feedb` | `OSC1 Octave` |
| O4 (20) | Osc 1 level | `Osc 1 Gain` | `Osc 1 Gain` | `Osc-A Level` | `OSC1 Level` |
| O5 (21) | Osc 2 timbre | `Osc 2 Pos` | `Osc 2 Wave` | `B Coarse` | `OSC2 Shape` |
| O6 (22) | Osc 2 detune / timbre 2 | `Osc 2 Detune` | `Osc 2 Detune` | `B Fine` | `OSC2 Detune` |
| O7 (23) | Osc 2 pitch | `Osc 2 Transp` | `Osc 2 Oct` | `Osc-B Feedb` | `OSC2 Octave` |
| O8 (24) | Osc 2 level | `Osc 2 Gain` | `Osc 2 Gain` | `Osc-B Level` | `OSC2 Level` |
| F1 (25) | Cutoff | `Filter 1 Freq` | `LP Freq` | `Filter Freq` | `F1 Freq` |
| F2 (26) | Resonance | `Filter 1 Res` | `LP Reso` | `Filter Res` | `F1 Resonance` |
| F3 (27) | Filter env amt | `Filter 1 Drive` | `LP Mod Amt 1` | `Fe Amount` | `F1 Freq < Env` |
| F4 (28) | Drive / morph | `Filter 1 Morph` | `HP Freq` | `Filter Drive` | `F1 Drive` |
| L1 (29) | LFO rate | `LFO 1 Rate` | `LFO Rate` | `LFO Rate` | `LFO1 Speed` |
| L2 (30) | LFO depth | `LFO 1 Amount` | `LFO Amt` | `LFO Amt` | `F1 Freq < LFO` |
| L3 (31) | LFO shape | `LFO 1 Shape` | `LFO Wave` | `LFO Type` | `LFO1 Shape` |
| L4 (32) | LFO extra ⚠ | `LFO 1 Shaping` | `LFO Mod Amt` | `LFO Amt B` | `LFO1 Fade In` |

⚠ **L4 is the weakest row of the draft** — confirm each choice (or nominate better)
during review. L3 lands on quantized params for Drift/Operator/Analog; acceptable on an
absolute pot (steps divide the throw), flagged for feel-testing.

### Right module — amp env (slots 1–4), env 2 (5–8), global (9–12), signature (13–16)

| Slot | Role | Wavetable | Drift | Operator † | Analog |
|---|---|---|---|---|---|
| E1 (1) | Amp attack | `Amp Attack` | `Env 1 Attack` | `Ae Attack` | `AEG1 Attack` |
| E2 (2) | Amp decay | `Amp Decay` | `Env 1 Decay` | `Ae Decay` | `AEG1 Decay` |
| E3 (3) | Amp sustain | `Amp Sustain` | `Env 1 Sustain` | `Ae Sustain` | `AEG1 Sustain` |
| E4 (4) | Amp release | `Amp Release` | `Env 1 Release` | `Ae Release` | `AEG1 Rel` |
| E5 (5) | Env 2 attack | `Env 2 Attack` | `Env 2 Attack` | `Fe Attack` | `FEG1 Attack` |
| E6 (6) | Env 2 decay | `Env 2 Decay` | `Env 2 Decay` | `Fe Decay` | `FEG1 Decay` |
| E7 (7) | Env 2 sustain | `Env 2 Sustain` | `Env 2 Sustain` | `Fe Sustain` | `FEG1 Sustain` |
| E8 (8) | Env 2 release | `Env 2 Release` | `Env 2 Release` | `Fe Release` | `FEG1 Rel` |
| G1 (9) | Volume | `Volume` | `Volume` | `Volume` | `Volume` |
| G2 (10) | Glide | `Glide` | `Glide Time` | `Glide Time` | `Glide Time` |
| G3 (11) | Transpose | `Transpose` | `Transpose` | `Transpose` | `Semitone` |
| G4 (12) | Spread / unison amt | `Unison Amount` | `Spread` | `Spread` | `Unison Detune` |
| S1 (13) | Signature 1 | `Sub Gain` | `Drift` | `Tone` | `Vib Amount` |
| S2 (14) | Signature 2 | `Osc 1 Effect 2` | `Thickness` | `Time` | `Vib Speed` |
| S3 (15) | Signature 3 | `Global Mod Amount` | `Strength` | `Pe Amount` | `Noise Level` |
| S4 (16) | Signature 4 | `Filter 2 Freq` | `Noise Gain` | `Shaper Drive` | `Noise Color` |

Env-2 semantics per synth: Wavetable/Drift = their literal `Env 2` (mod env);
Operator/Analog = the **filter envelope** (`Fe *` / `FEG1 *`) — the musically dominant
second envelope on those two.

---

## 5. Button matrix — 16 keys on grid-1, AREA-BASED (revised 2026-07-12)

**Design change:** grid-1 is now grouped into **areas**, not 16 fixed cross-synth
roles. Mechanically the button slots became positional per-synth free choice (like
the signature pots) — a **data/template-only change, no resolver code**.

- **B1–B4 = filter area**, **B5–B8 = osc area**, **B9–B16 = character area**
  (each synth's best-fit discrete controls).
- Muscle-memory anchors kept aligned across synths: **B1/B2** (filter on / type),
  **B5/B6** (osc 1 / 2 on), **B9/B10** (LFO sync / retrig), **B16** (Device on).
  B3–B4, B7–B8, B11–B15 vary per synth (topologies differ).
- **Operator osc B7/B8 = `A Fix On ` / `B Fix On `** (fixed-freq toggles for ops
  A/B — **trailing spaces are the exact Live names**), replacing the C/D on
  toggles per ck. Operator `Algorithm` lands in the character area (B12).
- Every cell is filled for all four synths; verified byte-exact vs
  `devices_12.json` with **no pot/button collision** per synth (a param never sits
  on both a pot and a button).

The authoritative slot→param map is `data/synth_zone_tables.json`; a rendered
snapshot lives in `data/synth_zone_tables.md` (visualization only). The old
16-fixed-role table is superseded.

| # | Area | Wavetable | Drift | Operator | Analog |
|---|---|---|---|---|---|
| B1 | filter | `Filter 1 On` | `Osc 1 Flt On` | `Filter On` | `F1 On/Off` |
| B2 | filter | `Filter 1 Type` | `LP Type` | `Filter Type` | `F1 Type` |
| B3 | filter | `Filter 1 LP/HP` | `Osc 2 Flt On` | `Filter Circuit - LP/HP` | `F2 On/Off` |
| B4 | filter | `Filter 2 On` | `Noise Flt On` | `Filt < LFO` | `F2 Type` |
| B5 | osc | `Osc 1 On` | `Osc 1 On` | `Osc-A On` | `OSC1 On/Off` |
| B6 | osc | `Osc 2 On` | `Osc 2 On` | `Osc-B On` | `OSC2 On/Off` |
| B7 | osc | `Sub On` | `Noise On` | `A Fix On ` | `Noise On/Off` |
| B8 | osc | `Sub Transpose` | `Osc 1 Wave` | `B Fix On ` | `O1 Sub/Sync` |
| B9 | character | `LFO 1 Sync` | `LFO Synced` | `LFO Sync` | `LFO1 Sync` |
| B10 | character | `LFO 1 Retrigger` | `LFO Retrig On` | `LFO Retrigger` | `LFO1 Retrig` |
| B11 | character | `LFO 2 Sync` | `LFO Time Mode` | `LFO On` | `Unison On/Off` |
| B12 | character | `LFO 2 Retrigger` | `Osc Retrig On` | `Algorithm` | `Vib On/Off` |
| B13 | character | `Amp Loop Mode` | `Env 2 Cyc On` | `Ae Loop` | `Glide On/Off` |
| B14 | character | `Env 2 Loop Mode` | `Legato On` | `Fe Loop` | `Glide Legato` |
| B15 | character | `Filter 1 Slope` | `Cyc Env Time Mode` | `Glide On` | `Glide Mode` |
| B16 | character | `Device On` | `Device On` | `Device On` | `Device On` |

---

## 6. Data + config design

### `data/synth_zone_tables.json` (new shipped file)

Role-keyed, two parts (exact JSON shape may be adjusted during TDD, spirit is fixed):

- **`template`** — defined once: the zone list (name, colour, slot numbers, ordered role
  ids) for the 32 pot slots and 16 button slots. This is what makes positions immovable.
- **`synths`** — one entry per `className`: `display` name plus `role → { name, display? }`
  maps for encoders and buttons. A missing role = legitimately unmapped (silent, dim LED).

Validated at generation by a new `model_synth_zones.py` (mirror
`validate_custom_device_mappings`): every synth's roles must exist in the template,
no duplicate parameter names within a synth, template slots must cover 1–32 / B1–B16
exactly once.

### Mapping `.nt`

One new top-level key in `ck_grid.nt`:

```
smart-zoning: on
```

`gen.py` bakes `synth_zone_tables.json` into the generated surface (same pattern as
`parameter_mappings_file`) and passes an enabled flag through the Helpers config.
Default off: other surfaces (launch_control, parks) are untouched until they opt in —
and a 32-slot template on a 16-encoder surface would show only slots 1–16 (right-module
content), which is another reason enrollment is per-surface.

### Resolver (`source_modules/param_resolver.py`)

New tier ahead of BOB in `resolve_encoder` / `resolve_switch`, active only when the
surface flag is on AND the focused device's `class_name` has a `synths` entry:

- Page 1, slot N → template slot N's role → synth's param name → `resolve_param_by_name`
  (strict `original_name`, dead-handle-safe — all existing machinery reused).
- Role miss or param-name miss on a *mapped* role: return `None`; only log when a
  **mapped** name fails to resolve (byte-drift bug), never for template holes.
- `encoder_pages_count` / `page_label_for` / `_first_standard_page`: a zoned device
  behaves like a BOB-with-encoders device — zone is page 1 (label e.g. `"Zoned"`),
  factory banks from page 2.
- Buttons: same pattern via the template's 16 button roles; `button_pages_count`
  accordingly.
- Precedence: zone table beats BOB if both exist (shouldn't happen — custom mappings
  stay effects-only).

---

## 7. Open decisions

1. **Jump handling (absolute pots).** Unchanged from before:
   - **(a) Accept it** for Phase 1, lean on LED brightness (§8). Lowest effort. ← ship this
   - **(b) Soft-takeover** (Grid Lua MIDI-RX compare, or Ableton-side) — layer on later;
     the LED design below keeps that door open.
2. **§4 draft review** — especially row L4 and the four signature slots per synth.
   User signs off on the matrix before the data file is written.
3. **Meld & Serum** — not in `devices_12.json` (Live 12.1+ / VST). Same template; exact
   param strings must be **extracted from the live device** (guessed names silently fail):
   load device → dump names via `update.py` / `data/list_device_params.sh` → read
   `./bin/tail_logs.sh` → fill roles → add `synths` entries. Do after the four built-ins ship.

---

## 8. LED plan (32 pots + 16 buttons)

Pots are absolute, so the LED is **not** a position indicator:

- **Hue = zone** — per-module blocks (§3 colours). The rig reads as six blocks at rest
  and matches the HUD. Free win.
- **Brightness = live value** — intensity tracks the parameter's actual Live value, so a
  stale pot (position ≠ Live after device switch) shows the truth until you catch up.
- **Dim = unmapped** — a role the current synth can't fill sits dimmed, not misleading.

**Buttons (grid-1):** hue = zone; on/off state read back from Live (lit when on, dim
when off); action keys flash on press.

### Architecture — mirror `HudClient`

`GridLedClient` alongside `source_modules/hud_client.py`, hooked at the **same point** in
`templates/surface_name/modules/main_component.py` that calls
`send_device()` / `send_slot()` / `commit()` on device focus. Rides the same coalesced
device-switch burst but emits **MIDI to the Grid's RX** instead of UDP — HUD and hardware
stay coherent because they fire from one event. `NullGridLedClient` no-op fallback (same
pattern as `NullHudClient`) so generated code never branches.

Grid side: a short Lua handler maps incoming CC → `led_color` / `led_intensity` (layer 1).

**Phasing:**
- **Phase 1 (zero Ableton code):** static zone colours set locally in Grid Editor on each
  element's init event. Instant self-documenting rig.
- **Phase 2 (dynamic):** `GridLedClient` streams value + on/off; Lua renders brightness,
  button state, and dimming of unmapped roles.

---

## 9. Implementation steps

**A. Matrix sign-off** ✅ — user signed off §4/§5 (2026-07-10). Every param name
verified byte-exact against `data/devices_12.json`.

**B. Zone data + validator (TDD)** ✅ — `model_synth_zones.py`
(`SynthZoneTables`/`validate_synth_zone_tables`) + `data/synth_zone_tables.json`
(template + four synths, generated from the §4/§5 matrix). Tests:
`test_model_synth_zones.py`, incl. a non-circular ground-truth check that every
shipped name is a member of its className's param set in `devices_12.json`.

**C. Config plumbing** ✅ — `smart-zoning` key on `RootV2`/`RootV2ModesOrModeless`
(`model_v2.py`); `gen.py` loads+validates+bakes `synth_zone_tables.json` and the
enabled flag (`smart_zoning`, `zone_tables_raw`) into the surface; threaded
through `SurfaceConfig → Helpers → ParameterResolver`.

**D. Resolver tier** ✅ — `param_resolver.py`: `_build_zone_tables`, `_zone_synth`/
`_is_zoned`, three-way `_zone_lookup` (fallthrough / unmapped / mapped) wired into
`resolve_encoder` + `resolve_switch` ahead of BOB; zone = page 1 ("Zoned" label),
banks from page 2; slots outside the template fall through (preserves shift-mode's
grid-1 second bank). Tests: `test_synth_zone_resolver.py` + regression pins in
`test_param_resolver.py`.

**E. Surface flip** ✅ — `smart-zoning: on` in `ck_grid.nt`; regenerated. User
deploys + restarts Live (never run `deploy.sh` here).

**LED work (§8) — deferred** to a follow-up pass (scope decision 2026-07-11:
ship functional zoning first). Phase 1 = static zone hues in the Grid Editor (zero
Ableton code); Phase 2 = `GridLedClient` streaming value/state over MIDI on the
device-focus burst.


---

## 10. Test plan (TDD — failing tests first, per CLAUDE.md)

- **Zone-table validation:** template covers slots 1–32/B1–B16 exactly once; synth roles
  all exist in template; the shipped file for all four synths loads and validates.
- **Slot ↔ parameter binding:** for each synth `className`, slot N → the byte-exact §4
  name (guards drift; Operator's trailing-space params make hand-retyping fatal).
- **Resolver:** zoned synth → zone param on page 1, factory bank on page 2, page label;
  unknown synth → identical to today (regression pin); toggle off → identical to today;
  role-miss → None without log spam; mapped-name miss → logged.
- **Gen integration:** `ck_grid.nt` with `smart-zoning: on` generates; zone file baked;
  existing gen/clash tests stay green.
- **`GridLedClient`:** burst buffering/coalescing, `set_enabled` gate, Null parity,
  fires on the same device-focus event as the HUD (integration-level).
- Full suite green; run `./build.sh` before committing and report quality change.

---

## 11. Guardrails (from CLAUDE.md)

- Let the **user redeploy** (they restart Ableton). Don't run `deploy.sh` yourself.
- **Never commit with a failing test**, even unrelated. Mention **this plan name**
  (`grid-po16-synth-surface-plan`) in the commit message. Run `./build.sh` first.
- Runtime info from inside Live comes via `update.py` + `./bin/tail_logs.sh`.
- Flag product/UX contradictions before coding (don't silently force Operator into the
  osc template; don't let per-synth data creep back into positional
  `custom_device_mappings.json`).
