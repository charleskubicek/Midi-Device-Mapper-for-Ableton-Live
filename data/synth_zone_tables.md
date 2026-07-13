# Synth zone tables — VISUALIZATION ONLY

> # ⚠️ THIS FILE IS NOT AUTHORITATIVE. EDITING IT CHANGES NOTHING.
>
> This is an auto-generated, human-readable snapshot of
> **`data/synth_zone_tables.json`** — the real source of truth that gets baked
> into the generated Grid surface. **Nothing reads this markdown.** To change a
> mapping or a zone colour, edit the JSON (then regenerate the surface). This
> file may drift from the JSON until re-rendered; the JSON always wins.

Slot numbering (shipped orientation): grid-2 (LEFT PO16) → slots 1–16
(osc/filter/LFO); grid-3 (RIGHT PO16) → slots 17–32 (env/global/signature).
Buttons are grid-1 (LEFT BU16), slots 1–16, grouped into AREAS: 1–4 filter,
5–8 osc, 9–16 character. `—` = role legitimately unmapped (dim LED, blank HUD).

## Zone colours

Single source (`zone_colors` in the JSON) feeding both HUD outline tints and
Grid LED hues.

| Zone | Colour |
|---|---|
| osc | `#E0A33E` |
| filter | `#33B5A6` |
| lfo | `#9B8CE0` |
| env | `#E06B86` |
| global | `#57B368` |
| signature | `#8A9A4B` |
| character | `#5B8BC4` |

---

## Pot matrix — 32 slots

| Slot | Zone | Colour | Role | Wavetable | Drift | Operator | Analog |
|---|---|---|---|---|---|---|---|
| 1 | osc | `#E0A33E` | Osc 1 timbre | `Osc 1 Pos` | `Osc 1 Shape` | `A Coarse` | `OSC1 Shape` |
| 2 | osc | `#E0A33E` | Osc 1 timbre 2 | `Osc 1 Effect 1` | `Osc 1 Shape Mod Amt` | `A Fine` | `OSC1 PW` |
| 3 | osc | `#E0A33E` | Osc 1 pitch | `Osc 1 Transp` | `Osc 1 Oct` | `Osc-A Feedb` | `OSC1 Octave` |
| 4 | osc | `#E0A33E` | Osc 1 level | `Osc 1 Gain` | `Osc 1 Gain` | `Osc-A Level` | `OSC1 Level` |
| 5 | osc | `#E0A33E` | Osc 2 timbre | `Osc 2 Pos` | `Osc 2 Wave` | `B Coarse` | `OSC2 Shape` |
| 6 | osc | `#E0A33E` | Osc 2 detune | `Osc 2 Detune` | `Osc 2 Detune` | `B Fine` | `OSC2 Detune` |
| 7 | osc | `#E0A33E` | Osc 2 pitch | `Osc 2 Transp` | `Osc 2 Oct` | `Osc-B Feedb` | `OSC2 Octave` |
| 8 | osc | `#E0A33E` | Osc 2 level | `Osc 2 Gain` | `Osc 2 Gain` | `Osc-B Level` | `OSC2 Level` |
| 9 | filter | `#33B5A6` | Cutoff | `Filter 1 Freq` | `LP Freq` | `Filter Freq` | `F1 Freq` |
| 10 | filter | `#33B5A6` | Resonance | `Filter 1 Res` | `LP Reso` | `Filter Res` | `F1 Resonance` |
| 11 | filter | `#33B5A6` | Filter env amt | `Filter 1 Drive` | `LP Mod Amt 1` | `Fe Amount` | `F1 Freq < Env` |
| 12 | filter | `#33B5A6` | Drive / morph | `Filter 1 Morph` | `HP Freq` | `Filter Drive` | `F1 Drive` |
| 13 | lfo | `#9B8CE0` | LFO rate | `LFO 1 Rate` | `LFO Rate` | `LFO Rate` | `LFO1 Speed` |
| 14 | lfo | `#9B8CE0` | LFO depth | `LFO 1 Amount` | `LFO Amt` | `LFO Amt` | `F1 Freq < LFO` |
| 15 | lfo | `#9B8CE0` | LFO shape | `LFO 1 Shape` | `LFO Wave` | `LFO Type` | `LFO1 Shape` |
| 16 | lfo | `#9B8CE0` | LFO extra | `LFO 1 Shaping` | `LFO Mod Amt` | `LFO Amt B` | `LFO1 Fade In` |
| 17 | env | `#E06B86` | Amp attack | `Amp Attack` | `Env 1 Attack` | `Ae Attack` | `AEG1 Attack` |
| 18 | env | `#E06B86` | Amp decay | `Amp Decay` | `Env 1 Decay` | `Ae Decay` | `AEG1 Decay` |
| 19 | env | `#E06B86` | Amp sustain | `Amp Sustain` | `Env 1 Sustain` | `Ae Sustain` | `AEG1 Sustain` |
| 20 | env | `#E06B86` | Amp release | `Amp Release` | `Env 1 Release` | `Ae Release` | `AEG1 Rel` |
| 21 | env | `#E06B86` | Env 2 attack | `Env 2 Attack` | `Env 2 Attack` | `Fe Attack` | `FEG1 Attack` |
| 22 | env | `#E06B86` | Env 2 decay | `Env 2 Decay` | `Env 2 Decay` | `Fe Decay` | `FEG1 Decay` |
| 23 | env | `#E06B86` | Env 2 sustain | `Env 2 Sustain` | `Env 2 Sustain` | `Fe Sustain` | `FEG1 Sustain` |
| 24 | env | `#E06B86` | Env 2 release | `Env 2 Release` | `Env 2 Release` | `Fe Release` | `FEG1 Rel` |
| 25 | global | `#57B368` | Volume | `Volume` | `Volume` | `Volume` | `Volume` |
| 26 | global | `#57B368` | Glide | `Glide` | `Glide Time` | `Glide Time` | `Glide Time` |
| 27 | global | `#57B368` | Transpose | `Transpose` | `Transpose` | `Transpose` | `Semitone` |
| 28 | global | `#57B368` | Spread | `Unison Amount` | `Spread` | `Spread` | `Unison Detune` |
| 29 | signature | `#8A9A4B` | Signature 1 | `Sub Gain` | `Drift` | `Tone` | `Vib Amount` |
| 30 | signature | `#8A9A4B` | Signature 2 | `Osc 1 Effect 2` | `Thickness` | `Time` | `Vib Speed` |
| 31 | signature | `#8A9A4B` | Signature 3 | `Global Mod Amount` | `Strength` | `Pe Amount` | `Noise Level` |
| 32 | signature | `#8A9A4B` | Signature 4 | `Filter 2 Freq` | `Noise Gain` | `Shaper Drive` | `Noise Color` |

---

## Button matrix — 16 keys (grid-1), area-based

Areas: **B1–4 filter · B5–8 osc · B9–16 character**. Operator B7/B8 =
`A Fix On ` / `B Fix On ` (trailing spaces are the exact Live param names).

| Slot | Zone | Colour | Role | Wavetable | Drift | Operator | Analog |
|---|---|---|---|---|---|---|---|
| 1 | filter | `#33B5A6` | Filter A | `Filter 1 On` | `Osc 1 Flt On` | `Filter On` | `F1 On/Off` |
| 2 | filter | `#33B5A6` | Filter B | `Filter 1 Type` | `LP Type` | `Filter Type` | `F1 Type` |
| 3 | filter | `#33B5A6` | Filter C | `Filter 1 LP/HP` | `Osc 2 Flt On` | `Filter Circuit - LP/HP` | `F2 On/Off` |
| 4 | filter | `#33B5A6` | Filter D | `Filter 2 On` | `Noise Flt On` | `Filt < LFO` | `F2 Type` |
| 5 | osc | `#E0A33E` | Osc A | `Osc 1 On` | `Osc 1 On` | `Osc-A On` | `OSC1 On/Off` |
| 6 | osc | `#E0A33E` | Osc B | `Osc 2 On` | `Osc 2 On` | `Osc-B On` | `OSC2 On/Off` |
| 7 | osc | `#E0A33E` | Osc C | `Sub On` | `Noise On` | `A Fix On ` | `Noise On/Off` |
| 8 | osc | `#E0A33E` | Osc D | `Sub Transpose` | `Osc 1 Wave` | `B Fix On ` | `O1 Sub/Sync` |
| 9 | character | `#5B8BC4` | LFO sync | `LFO 1 Sync` | `LFO Synced` | `LFO Sync` | `LFO1 Sync` |
| 10 | character | `#5B8BC4` | LFO retrig | `LFO 1 Retrigger` | `LFO Retrig On` | `LFO Retrigger` | `LFO1 Retrig` |
| 11 | character | `#5B8BC4` | Char 3 | `LFO 2 Sync` | `LFO Time Mode` | `LFO On` | `Unison On/Off` |
| 12 | character | `#5B8BC4` | Char 4 | `LFO 2 Retrigger` | `Osc Retrig On` | `Algorithm` | `Vib On/Off` |
| 13 | character | `#5B8BC4` | Char 5 | `Amp Loop Mode` | `Env 2 Cyc On` | `Ae Loop` | `Glide On/Off` |
| 14 | character | `#5B8BC4` | Char 6 | `Env 2 Loop Mode` | `Legato On` | `Fe Loop` | `Glide Legato` |
| 15 | character | `#5B8BC4` | Char 7 | `Filter 1 Slope` | `Cyc Env Time Mode` | `Glide On` | `Glide Mode` |
| 16 | character | `#5B8BC4` | Device on | `Device On` | `Device On` | `Device On` | `Device On` |
