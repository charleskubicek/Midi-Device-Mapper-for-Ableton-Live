# Zoned-synth display aliases: hand-written → role fallback → raw name

## Context

Zoned synths show raw Live parameter names on the HUD — Operator's envelopes
read "Ae Attack" / "Fe Attack", Analog's "AEG1 Attack" / "FEG1 Rel". The zone
tables already contain two alias layers: per-synth `display` overrides (used)
and a per-role `display` in the shared template (currently **ignored** by the
resolver).

**Agreed policy (user):** label precedence is
**hand-written per-synth `display` → template role `display` → raw `name`**,
with two data rules: Amp-envelope ADSR drops the "Amp" prefix everywhere (just
"Attack" / "Decay" / "Sustain" / "Release"), and every display label is
Title-Cased.

## Code change — `source_modules/param_resolver.py`

1. `_build_zone_tables` (line ~79): also compile role→display maps from the
   template: `enc_role_display = {e['role']: e.get('display') for e in
   template.get('encoders', [])}` and the `btn_` equivalent.
2. Encoder zone path (`resolve_encoder`, line ~580): replace
   `entry.get('display') or name` with the chain
   `entry.get('display') or role_display or name`, where `role_display` is the
   template display for the slot's role. `_zone_lookup` currently returns only
   `(outcome, entry)` — extend it to return the role (or add a
   `role_display_for(kind, slot)` helper next to `zone_for_slot`, line ~426).
3. Button zone path (`resolve_switch`, line ~673): same chain for `alias`.
4. **Toggle-group entries skip the template fallback**: when
   `_resolve_group_member` (line ~632) resolves the active member, the label
   stays `member display → member name` (e.g. Operator's "A Coarse" / "A Freq"
   are already specific; "Osc 1 Timbre" would be a regression).
5. BOB / custom_device_mappings paths are untouched (they have no roles).

No wire/HUD changes — the alias already flows into `SLOT`/`UPDATE` names.

## Data change — `data/synth_zone_tables.json`

1. **Template**: Title-Case all `display` values ("Amp attack" → "Amp Attack",
   "Env 2 attack" → "Env 2 Attack", "LFO rate" → "LFO Rate", …), then set the
   amp-env roles to the bare ADSR names:
   `amp_attack: "Attack"`, `amp_decay: "Decay"`, `amp_sustain: "Sustain"`,
   `amp_release: "Release"` (all synths inherit — no per-synth amp aliases).
2. **Per-synth `display` fields** (adopted with user). Only slots listed get a
   hand-written alias; everything else inherits the role fallback:

   **Operator** — enc env2 21–24: `Filt Attack/Filt Decay/Filt Sustain/Filt
   Release`; enc 3/7 (`Osc-A/B Feedb`): `A Feedback`/`B Feedback`; enc 12:
   `Drive`; enc 16: `LFO Amt B`; sig 29–32: `Tone`/`Time`/`Pitch Env`/`Shaper
   Drive`; btn 1–4: `Filt On`/`Filt Type`/`LP/HP`/`Filt<LFO`; btn 5–8: `Osc A
   On`/`Osc B On`/`A Fixed`/`B Fixed`; btn 11–15: `LFO On`/`Algorithm`/`Amp
   Loop`/`Filt Loop`/`Glide On`.

   **InstrumentVector (Wavetable)** — enc 1/5: `Osc 1 Pos`/`Osc 2 Pos`; enc 2:
   `Osc 1 FX 1`; enc 11 (`Filter 1 Drive` — template "Filter Env Amt" would be
   wrong): `Drive`; enc 12: `Morph`; enc 16: `Shaping`; sig 29–32: `Sub
   Gain`/`Osc 1 FX 2`/`Mod Amount`/`Filt 2 Freq`; btn 1–4: `F1 On`/`F1 Type`/`F1
   LP/HP`/`F2 On`; btn 5–8: `Osc 1 On`/`Osc 2 On`/`Sub On`/`Sub Transp`; btn
   11–15: `LFO 2 Sync`/`LFO 2 Retrig`/`Amp Loop`/`Env 2 Loop`/`F1 Slope`.

   **Drift** — enc 1/2: `Osc 1 Shape`/`Shape Mod`; enc 5: `Osc 2 Wave`; enc 12
   (`HP Freq` — template "Drive / Morph" would be wrong): `HP Freq`; enc 16:
   `LFO Mod`; sig 29–32: `Drift`/`Thickness`/`Strength`/`Noise Gain`; btn 1–4:
   `Osc1 Filt`/`LP Type`/`Osc2 Filt`/`Noise Filt`; btn 5–8: `Osc 1 On`/`Osc 2
   On`/`Noise On`/`Osc 1 Wave`; btn 11–15: `LFO Time`/`Osc Retrig`/`Env2
   Cycle`/`Legato`/`Cyc Time`.

   **UltraAnalog (Analog)** — enc env2 21–24: `Filt Attack/Filt Decay/Filt
   Sustain/Filt Release`; enc 1/2/5: `Osc 1 Shape`/`Osc 1 PW`/`Osc 2 Shape`;
   enc 12: `Drive`; enc 16: `Fade In`; sig 29–32: `Vib Amount`/`Vib
   Speed`/`Noise Level`/`Noise Color`; btn 1–4: `F1 On`/`F1 Type`/`F2 On`/`F2
   Type`; btn 5–8: `Osc 1 On`/`Osc 2 On`/`Noise On`/`Sub/Sync`; btn 11–15:
   `Unison`/`Vibrato`/`Glide`/`Legato`/`Glide Mode`.

3. Update `data/synth_zone_tables.md` (the human-readable doc) to describe the
   three-step precedence and the Title-Case/bare-ADSR conventions.

## TDD order

1. Failing unit tests in `tests/test_synth_zone_resolver.py` (and
   `tests/test_param_resolver.py` where the alias assertions live): synth
   `display` wins; template role display used when synth entry has none; raw
   name when the role has no template display; group members never take the
   template fallback; button path same chain.
2. Implement the resolver chain.
3. Data edit + a data-integrity test (e.g. all template/synth `display` values
   are Title-Case, amp-env template displays are the bare ADSR names) so future
   table edits keep the convention.
4. Fix any existing tests asserting old labels (e.g. golden bursts containing
   "Ae Attack" or "Amp attack").

## Verification

- `poetry run pytest`; `./build.sh` before commit (mention this plan in the
  commit message).
- Regenerate: `poetry run python ableton_control_surface_as_code/gen.py
  live_surfaces/grid/ck_grid.nt`; user redeploys + restarts Live.
- In Live: focus Operator → env row reads "Attack…Release / Filt Attack…Filt
  Release"; Analog → same; Wavetable enc 11 reads "Drive"; check labels fit the
  2-line HUD cells (44 pt wide) via the HUD.
