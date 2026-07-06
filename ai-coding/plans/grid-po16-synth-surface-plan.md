# Grid PO16 synth surface — generic per-synth mapping + LEDs

**Goal:** turn the new left `PO16` (16 linear pots) + `BU16` (16 RGB buttons) of an Intech
Studio Grid into a *predictable* synth control surface: the **same physical control drives
the same semantic parameter on every synth** (Wavetable, Drift, Operator, Analog, Diva),
with each synth's signature controls in a fixed "special" area, and the Grid's per-element
LEDs used to make the layout self-documenting.

Handoff doc — self-contained. The design rationale was worked out interactively; this
captures the decisions, the exact parameter matrix, and the implementation steps.

---

## 1. Hardware reality (drives the whole design)

Physical row (magnetic modules, left→right): **`BU16 · PO16 · PO16 · BU16`**.
Currently only `PO16 · BU16` (existing compact rig) is wired. The **new left pair**
(`BU16` + `PO16`) is the synth zone; the existing right pair keeps its current
mixer/nav duties and is **out of scope** here.

- **Synth zone now = 16 pots + 16 buttons** (one PO16 + one BU16). Designed to extend to
  32 pots later when the second PO16 joins the synth zone — this 16 stays the
  highest-priority core so muscle memory transfers.
- **PO16 = absolute linear potentiometers** (physical position, ~300°). This creates the
  **jump problem** (§6, open decision) and reshapes the LED plan (§7).
- **Every Grid element has an RGB LED**, set in Lua: `led_color(layer, {{r,g,b,a}})`
  (shortname `glc`), plus `led_intensity` and blink animations. **Layer 1** is the
  button/potmeter layer. Ref: docs.intech.studio → Actions → LED Actions.
- **Grid has MIDI RX** (receive) and MIDI TX (7-bit / 14-bit / NRPN / SysEx). So the
  generated surface can send MIDI *to* the Grid and a small Lua handler lights LEDs from
  it. Ref: docs.intech.studio → Actions → MIDI Actions.
- Pots send **absolute CC** as configured in Grid Editor.

---

## 2. The layout (muscle-memory blocks)

One 4×4 PO16 bank, read top row → bottom row. Blocks occupy whole rows where possible:

| Row (pots) | Block | Slots |
|---|---|---|
| 1 | Filter | 1–4 |
| 2 | Oscillators | 5–8 |
| 3 | Amp envelope | 9–12 |
| 4 | Mod / Global (glide, LFO, volume) | 13–16 |

This mirrors Ableton's own "Best of Bank" taxonomy (e.g. Wavetable's factory banks are
literally Osc / Filter / Amp Env / LFO / Global), so it is validated, not just intuited.

Block colours (used for LEDs + the HUD): filter=teal, osc=amber, env=rose, LFO=violet,
global=green.

---

## 3. Per-synth pot matrix (16 slots)

**Parameter names are byte-exact** — they are what the generated surface binds to.
Source of truth: `data/devices_12.json` (already gathered for these five) and
`data/live_device_banks.py`. Watch trailing spaces and exact casing.

`className` keys for `custom_device_mappings.json`:
Wavetable → **`InstrumentVector`**, Drift → **`Drift`**, Operator → **`Operator`**,
Analog → **`UltraAnalog`**, Diva → **`Diva`**.

| # | Role | Wavetable (`InstrumentVector`) | Drift (`Drift`) | Operator (`Operator`) | Analog (`UltraAnalog`) | Diva (`Diva`) |
|---|---|---|---|---|---|---|
| 1 | Cutoff | `Filter 1 Freq` | `LP Freq` | `Filter Freq` | `F1 Freq` | `VCF1: Frequency` |
| 2 | Resonance | `Filter 1 Res` | `LP Reso` | `Filter Res` | `F1 Resonance` | `VCF1: Resonance` |
| 3 | Filter env amt | `Filter 1 Drive` | `LP Mod Amt 1` | `Fe Amount` | `F1 Freq < Env` | `VCF1: FreqModDepth` |
| 4 | Drive / morph | `Filter 1 Morph` | `HP Freq` | `Filter Drive` | `F1 Drive` | `VCF1: FilterFM` |
| 5 | Osc 1 timbre | `Osc 1 Pos` | `Osc 1 Shape` | `A Coarse` † | `OSC1 Shape` | `OSC: Shape1` |
| 6 | Osc 2 timbre | `Osc 2 Pos` | `Osc 2 Wave` | `B Coarse` † | `OSC2 Shape` | `OSC: Shape2` |
| 7 | Osc 2 pitch | `Osc 2 Transp` | `Osc 2 Oct` | `Osc-B Level` † | `OSC2 Octave` | `OSC: Tune2` |
| 8 | Osc balance / detune | `Osc 2 Gain` | `Osc 2 Gain` | `Osc-A Feedb` † | `OSC2 Detune` | `OSC: OscMix` |
| 9 | Amp attack | `Amp Attack` | `Env 1 Attack` | `Ae Attack` | `AEG1 Attack` | `ENV1: Attack` |
| 10 | Amp decay | `Amp Decay` | `Env 1 Decay` | `Ae Decay` | `AEG1 Decay` | `ENV1: Decay` |
| 11 | Amp sustain | `Amp Sustain` | `Env 1 Sustain` | `Ae Sustain` | `AEG1 Sustain` | `ENV1: Sustain` |
| 12 | Amp release | `Amp Release` | `Env 1 Release` | `Ae Release` | `AEG1 Rel` | `ENV1: Release` |
| 13 | Glide | `Glide` | `Glide Time` | `Glide Time` | `Glide Time` | `VCC: Glide` |
| 14 | LFO rate | `LFO 1 Rate` | `LFO Rate` | `LFO Rate` | `LFO1 Speed` | `LFO1: Rate` |
| 15 | LFO depth | `LFO 1 Amount` | `LFO Amt` | `LFO Amt` | `F1 Freq < LFO` | `LFO1: DepthMod Dpt1` |
| 16 | Volume | `Volume` | `Volume` | `Volume` | `Volume` | *(none — see §5)* |

† **Operator is an FM deviation** (documented, wanted): a 2-osc × 4-control template can't
represent 4 FM operators, so the "osc" row becomes coarse ratios + operator level +
feedback, and `Algorithm` moves to a button. Do **not** try to force it back into the osc
template.

---

## 4. Per-synth button matrix (16 keys, BU16)

Toggles grouped to match the pot blocks. `—` = no equivalent on that synth (leave the key
unmapped). **B16 is reserved** for shift/mode (the existing FSM), not a parameter.

| # | Role | Wavetable | Drift | Operator | Analog | Diva |
|---|---|---|---|---|---|---|
| B1 | Filter on | `Filter 1 On` | `Osc 1 Flt On` | `Filter On` | `F1 On/Off` | — |
| B2 | Filter type | `Filter 1 Type` | `LP Type` | `Filter Type` | `F1 Type` | `VCF1: Model` |
| B3 | LP / HP | `Filter 1 LP/HP` | — | — | — | — |
| B4 | Filter 2 on | `Filter 2 On` | `Osc 2 Flt On` | — | `F2 On/Off` | — |
| B5 | Osc 1 on | `Osc 1 On` | `Osc 1 On` | `Osc-A On` | `OSC1 On/Off` | `OSC: Saw1On` |
| B6 | Osc 2 on | `Osc 2 On` | `Osc 2 On` | `Osc-B On` | `OSC2 On/Off` | `OSC: Saw2On` |
| B7 | Sub / noise on | `Sub On` | `Noise On` | `Osc-C On` | `Noise On/Off` | `OSC: Noise1On` |
| B8 | Osc wave / sync | — | `Osc 1 Wave` | `Osc-D On` | — | `OSC: Pwm1On` |
| B9 | LFO sync | `LFO 1 Sync` | `LFO Synced` | `LFO Sync` | `LFO1 Sync` | `LFO1: Sync` |
| B10 | LFO retrig | `LFO 1 Retrigger` | `LFO Retrig On` | `LFO Retrigger` | `LFO1 Retrig` | `LFO1: Restart` |
| B11 | Env loop / mode | `Amp Loop Mode` | `Env 2 Cyc On` | `Ae Loop` | `AEG1 Loop` | `ENV1: Release On` |
| B12 | Unison on | — | — | — | `Unison On/Off` | — |
| B13 | Glide on | — | — | `Glide On` | `Glide On/Off` | `ARP: OnOff` |
| B14 | Mono / legato | — | `Legato On` | — | `Glide Legato` | — |
| B15 | Device on | `Device On` | `Device On` | `Device On` | `Device On` | `Device On` |
| B16 | Shift / page | *(reserved — mode FSM)* | | | | |

---

## 5. Meld & Serum — parameter extraction required

Neither is in `data/devices_12.json` (Meld = Live 12.1+, Serum = VST). They get the **same
16-slot template**, but the exact param strings must be **extracted from the live device**
— guessed names silently fail to bind (the JSON matches on exact parameter name).

Steps:
1. Load Meld / Serum on a track, focus it.
2. Dump its exact parameter names via the runtime-query flow (`update.py` on the generated
   surface, or `data/list_device_params.sh`), read from `./bin/tail_logs.sh`. Mirror how
   `data/live_device_banks.py` / `data/gathered_*.json` were produced.
3. Fill the 16 slots by the semantic roles in §2–3.

**Diva slot 16:** Diva exposes no master-volume parameter, so slot 16 is intentionally
empty for Diva (dim LED, §7). Confirm during implementation whether the mappings format
wants the entry omitted or an explicit empty placeholder.

---

## 6. Open decisions (need a call before / during build)

1. **Scope — 16 or 32 pots now?** This plan assumes **16** (one PO16) for the synth zone,
   extensible to 32. If both PO16 modules are for synths *today*, the pot matrix expands to
   the full 8-osc / 4-filter / 4-LFO / 8-env / 8-global layout (that design already exists;
   ask the user).
2. **Jump handling (absolute pots).** One physical pot mapped across many synths won't match
   the new value after a device switch, so a touch jumps the parameter. Options:
   - **(a) Accept it** for Phase 1 and lean on the LED brightness cue (§7). Lowest effort.
   - **(b) Soft-takeover** — suppress output until the pot passes through Live's current
     value. Implementable in Grid Lua (MIDI RX + stored target + comparison) or Ableton-side.
     Better feel, more work, and it interacts with where value-feedback lives.
   Recommendation: ship (a), design the LED feedback so (b) can be layered on later.
3. **Where the synth mapping lives.** Recommend a **new mapping `.nt`** targeting only the new
   modules (leave the existing compact `ck_grid.nt` untouched), rather than adding a mode to
   `ck_grid`. Confirm with user.

---

## 7. LED plan (PO16 specifics)

Pots have physical position, so the LED is **not** a position indicator. Repurpose each
pot's RGB LED for:

- **Hue = block** — filter teal / osc amber / env rose / LFO violet / global green. The bank
  reads as blocks at rest and matches the HUD colours. This is the free win.
- **Brightness = live value** — LED intensity tracks the parameter's *actual* Live value, so
  a stale pot (position ≠ Live after a device switch) still shows the truth until you catch
  up. More useful on absolute pots than it would be on encoders.
- **Dim = unmapped** — a slot the current device can't fill (Diva's Volume, a borrowed slot)
  sits dimmed, not misleading.

**Buttons:** hue = block + on/off state read back from the device (light when on, dim when
off) so colour reflects Live, not the last press; action keys flash on press; shift/mode
reuses the existing `on_color` (red/green) convention.

### Architecture — mirror `HudClient`

Add a `GridLedClient` alongside `source_modules/hud_client.py`, hooked at the **same point**
in `templates/surface_name/modules/main_component.py` that already calls
`send_device()` / `send_slot()` / `commit()` on device focus. It rides the same coalesced
device-switch burst (consistent with the recent transactional-focus work) but emits **MIDI
to the Grid's RX** instead of UDP to the HUD — so HUD and hardware stay coherent because they
fire from one event. Provide a `NullGridLedClient` no-op fallback (same pattern as
`NullHudClient`) so generated code never branches.

On the Grid side, a short Lua handler maps each incoming CC → `led_color` / `led_intensity`
on the matching element (layer 1).

**Phasing:**
- **Phase 1 (zero Ableton code):** set static block colours locally in Grid Editor via
  `led_color` on each element's init event. Instant self-documenting bank.
- **Phase 2 (dynamic):** `GridLedClient` streams value + on/off; Grid Lua renders brightness
  and button state. Unlocks the stale-pot cue, per-device recolour, and dimming.

---

## 8. Implementation steps

**A. Controller config (`live_surfaces/grid/controller_grid.nt`)**
- It currently models only 16 knobs + 16 buttons (two 4×4 `grid` groups). Add the new left
  `PO16` and `BU16` as new `grid` groups (rows 4, columns 4), chained with `right_of`, each
  with a **distinct, non-clashing `midi_channel` / `midi_range`** matching what the Grid
  Editor profile emits. Verify against the existing groups so CCs/notes don't collide.
- Confirm the grid coordinate names (e.g. `grid-3:1-16`) the new groups expose.

**B. Device parameter mappings (`data/custom_device_mappings.json`)**
- Add five `devices[]` entries keyed by `className` (§3), each with a 16-entry `encoders`
  list (slot order) and a `buttons` list (§4). Follow the existing entry shape
  (`{ "name": ..., "display": ... }`, buttons `{ "name": ..., "type": "param" }`).
- Optionally set `display` aliases for cleaner HUD/LED labels.
- `validate_custom_device_mappings` (`model_custom_devices.py`) runs at generation — keep it
  passing.

**C. Meld/Serum** — §5 extraction, then add their two entries.

**D. Synth mapping `.nt`** — new file (per §6.3) referencing `controller_grid.nt`, mapping
the new PO16 coords to a `device` block (`slots: 1-16`) and the new BU16 coords to
`device` `button` slots + the reserved shift button. Reuse `hud: on` / `show-hud-on`.

**E. LED feedback** — §7: `GridLedClient` + `NullGridLedClient`, hook in `main_component.py`,
plus the Grid Editor Lua profile. Phase 1 first (static colours, no Ableton change).

---

## 9. Test plan (TDD — failing tests first, per CLAUDE.md)

- **Config validation:** a test that the five new `custom_device_mappings.json` entries load
  and validate (extend `tests/test_config_validation.py` / the custom-devices validator test).
- **Mapping resolution:** generating the new synth `.nt` resolves all 16 pot coords + button
  coords to MIDI without clash (mirror existing `tests/test_gen.py` device-mapping tests and
  the switch-coord clash detection).
- **Slot ↔ parameter binding:** for each synth `className`, slot N → expected parameter name
  from §3 (guards against byte-exact drift, e.g. Operator trailing spaces, Diva colons).
- **`GridLedClient`:** unit tests mirroring `tests/test_hud_client.py` — burst
  buffering/coalescing, `set_enabled` gate, `Null` no-op parity. Assert it emits on the same
  device-focus event the HUD does (integration-level).
- **Controller expansion:** grid group cell-count vs MIDI-range validation still passes for
  the new 4×4 groups (`model_controller.py` already checks `rows*columns == len(range)`).
- Full suite green; run `./build.sh` before committing and report how quality changed.

---

## 10. Guardrails (from CLAUDE.md)

- Let the **user redeploy** (they restart Ableton). Don't run `deploy.sh` yourself.
- **Never commit with a failing test**, even unrelated. Mention **this plan name**
  (`grid-po16-synth-surface-plan`) in the commit message. Run `./build.sh` first.
- Runtime info from inside Live comes via `update.py` + `./bin/tail_logs.sh`.
- Flag any product/UX contradiction before coding (e.g. don't dismiss the HUD when it's
  needed; don't silently force Operator into the osc template).
