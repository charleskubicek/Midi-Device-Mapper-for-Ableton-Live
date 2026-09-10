# Rack macro shaping — map an Ableton rack's macro panel onto the grid

Status: **IN PROGRESS.** Foundation (Step 0) being built first; rack-shaping tier
gated on the `update.py` prerequisite below.

## Build sequence

- **Step 0 — foundation. ✅ DONE (889 tests green).** The base the rack tier sits
  on: without it the HUD mislabels knobs and reused/reordered slots drive the
  wrong parameter.
  - (0a) ✅ **Literal slots** — a device encoder drives the parameter its `slot`
    *names*, not its list position (`model_device`, `slots.slot_number`).
  - (0b) ✅ **Burst wire alignment** — `code_from_slot_assignments` bakes the
    physical wire index (via `find_wire_index`); `hud_presenter` places dials
    densely at `real_params[wire+1]` (order- and gap-robust).
  - (0c) ✅ **Live UPDATE wire fix** — `device_parameter_action` gained a trailing
    `wire_idx` kwarg; the single-dial repaint keys on the turned knob's wire
    (`wire+1`), not the parameter number. On-off keeps `parameter_updated(rp, 0)`
    on purpose (index 0 = static label, no dial UPDATE — never a dial cell).
- **Step 1 — rack tier. ✅ DONE (900 tests green).** Prerequisite answered (below).
  - **`macro_at`** (`param_resolver`) — pure panel-cell → macro shape function.
  - **Resolver tier** — page-1 rack tier gated on `rack_shaping` + a readable
    `visible_macro_count`; `macro_at` → `parameters[macro]`, dim outside the shape
    or where `macros_mapped[M-1]` is False. Racks added to `known` (one page).
  - **Config** — `rack-shaping: on` + `macro-panel-columns` (default 8), baked
    through model_v2 → gen.py → SurfaceConfig → ParameterResolver (mirrors
    `smart-zoning`). Verified end-to-end on ck_grid.
  - **Decisions taken** (were open questions): dedicated `rack-shaping:` flag (NOT
    folded into smart-zoning); rack tier wins over BOB/fallback for racks; odd
    counts use `cols = ceil(visible/2)`. Reversible if you disagree.

## Goal

Make the hardware grid mirror the *shape* of the focused Ableton rack's macro
panel, so a knob's position matches where that macro sits on screen:

- A **2×8 rack** (16 visible macros): macros 1-8 top row, 9-16 bottom row.
- A **2×4 rack** (8 visible macros): macros 1-4 top row, 5-8 **below** them —
  and macros 9-16 (which don't exist on screen) must NOT appear.

- A **2×2 rack** (4 visible macros): macros 1-2 top row, 3-4 bottom row.

Today every rack resolves as 16 positional params (the unknown-class fallback),
so a 2×4 rack wrongly shows macros 9-16 and the shapes don't line up.

## Key finding — the API gives us the shape directly

The name-counting heuristic isn't needed. `dev-docs/Live.md`:

- **`RackDevice.visible_macro_count`** (RO, get/observe) — exact count of visible
  macros (8 for a 2×4, 16 for a 2×8). This is the authoritative signal.
- **`RackDevice.macros_mapped`** — per-macro list of bools (True where mapped);
  use to dim a *visible but unmapped* macro.
- **`RackDevice.chain_selector`** — the chain-selector parameter, distinct from
  the macros (matters for indexing, see Open Questions).

Non-rack devices (Wavetable, Operator, …) have no `visible_macro_count`; that
absence is the gate — this tier only fires for racks.

## Design: shape is resolved at RUNTIME, in the resolver

The `encoder-list` is baked at gen time; the rack shape is only known at focus
time. So the shape logic lives in `ParameterResolver`, exactly where
`smart-zoning` already does per-device runtime layout. Two layers:

1. **Baked (mapping):** physical knob → **panel cell** (a stable 1..N index in a
   canonical macro panel). This is just the existing `slots:` — slot S = panel
   cell S.
2. **Runtime (resolver):** panel cell → actual macro parameter (or None), from
   `visible_macro_count`.

### Canonical panel + the shape function

The macro panel on this hardware is **`panel_cols` wide × `panel_rows` tall**
(this grid: 8×2, the top two physical rows). Slot S (1-based):

```
srow = (S-1) // panel_cols
scol = (S-1) %  panel_cols
```

The rack's own shape from the count (2-row panels, left-aligned per the user's
decision):

```
rack_cols = ceil(visible_macro_count / 2)     # 8→4, 16→8
macro_at(S):
    if scol >= rack_cols:            return None      # right of the rack
    macro = srow * rack_cols + scol + 1
    if macro > visible_macro_count:  return None      # below the rack
    return macro                                       # 1-based macro number
```

Worked example, `panel_cols=8`, **visible=8** (2×4, left-aligned on grid-2):

| slot | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |10 |11 |12 |13-16 |
|------|---|---|---|---|---|---|---|---|---|---|---|---|------|
| macro| 1 | 2 | 3 | 4 | – | – | – | – | 5 | 6 | 7 | 8 | –    |

`visible=16` → `rack_cols=8` → `macro == slot` (identity, current good behaviour).

### New resolver tier

In `resolve_encoder(device, slot)` (page 1), add a **rack tier** gated on
`visible_macro_count` being readable (dead-handle-safe via `_safe_device_attr`)
and a feature flag:

- compute `macro = macro_at(slot)`; `None` → dim (blank HUD cell, dead knob);
- else resolve macro → the rack's M-th macro `RealParameter`; if
  `macros_mapped[M-1]` is False, optionally still show it but dim.

Precedence: rack tier fires only for racks, so it's orthogonal to the synth
**zone** tier and the className **standard-bank** tier (non-racks). It should
take precedence over the generic **unknown-class fallback** (that's the mess it
replaces). Interaction with a per-rack **BOB** entry is an Open Question.

### Config surface

- A flag to turn it on, mirroring `smart-zoning: on`. Proposed
  `rack-shaping: on` (surface-level), OR fold under `smart-zoning` if they should
  always travel together (Open Question — user leaned "spec it first").
- `panel_cols` / `panel_rows`: the macro-panel geometry on the hardware. Prefer
  **deriving** it from the mapping (the dial grids are 8 wide) but a config
  override (`macro-panel: {columns: 8, rows: 2}`) is the safe MVP.

## Live UPDATE wire fix — ✅ DONE (Step 0c)

Fixed the 16-param bug ("moving one grid dial moves the OTHER HUD encoder"):
`device_parameter_action` now repaints the dial of the knob turned (its baked
`wire_idx + 1`), not the parameter-number dial, so two knobs sharing a parameter
no longer repaint each other. Resolution still keys on the slot/parameter; the
OSC parameter-update rides the same wire index the burst uses.

## PREREQUISITE — ANSWERED (rackprobe on real racks, 2026-09-10)

Confirmed on a 2×4 `AudioEffectGroupDevice` and a 2×8 `InstrumentGroupDevice`:

- **Macro M is at `parameters[M]`** (Device On at 0, Macro 1 at index 1 … Macro 16
  at 16). No off-by-one. The "Chain Selector" seen in the HUD was a *renamed*
  Macro 1 (`original_name='Macro 1'`, display `'Chain Selector'`), NOT the chain
  selector parameter. The real `chain_selector` sits at index **17**, after the
  16 macros — it never shifts them. (`chain_selector` the property returns a proxy
  that fails an `is` identity check against `parameters`, so don't match it by
  identity; it's simply not one of the 16 macros.)
- **`visible_macro_count`** returns 8 / 16 exactly. ✓ gate + shape signal.
- **`macros_mapped`** is always **len 16**; the 2×4 reads `[True×8, False×8]`.
  Safe to index `[M-1]` for M in 1..16; use it to dim a visible-but-unmapped macro.
- Rack className is `*GroupDevice` (`AudioEffectGroupDevice`,
  `InstrumentGroupDevice`, and by extension Midi/Drum); non-racks have no
  `visible_macro_count`, which stays the gate.

Resolution is therefore: `macro = macro_at(slot)`; if None → dim; else
`RealParameter(device.parameters[macro])` (its display name is the user's macro
name); if `macros_mapped[macro-1]` is False → dim.

## Resolved (no longer open)

- **Paging:** racks cap at 16 macros = one 2×8 page. Page 1 is the whole rack; no
  rack paging.

## Notes / behaviour choices made (all reversible)

- **Drum racks excluded.** A `DrumGroupDevice` has `visible_macro_count`, but
  surfaces that enable shaping repurpose the encoder grid for per-step velocity,
  so shaping would mislabel those knobs. Drum racks stay on today's behaviour.
  (The live velocity listener already short-circuits before the resolver; the
  exclusion keeps the HUD burst consistent with that.)
- **Visible-but-unmapped macro → blank** (not "shown but dimmed"). Simpler MVP;
  only visible on a rack with a `macros_mapped[M-1] == False` cell.
- **`macro-panel-columns` must match the `slots:` numbering.** No validation ties
  them yet — a mismatch silently misplaces macros. A `GenError` when
  `max(slot) > panel_cols * 2` would catch the obvious case (future).

## Still open

1. **Odd/small counts.** Panel assumed 2 rows, `cols=ceil(n/2)`; 8/16 certain,
   verify 6/12 if you use them.
2. **BOB precedence** — a rack with a custom BOB entry currently gets shaping
   (rack tier precedes BOB). Fine by default; revisit if a rack needs BOB.

## Test plan (once specced is agreed)

- Pure `macro_at(slot, panel_cols, visible)` unit table: 8→2×4 left-aligned,
  16→identity, boundary None cases.
- Resolver: fake rack device with `visible_macro_count` 8 and 16 → correct macro
  params and dims; non-rack device unaffected.
- HUD burst: 2×4 rack shows 8 macros on grid-2's two rows, grid-3 blank.
- Live UPDATE: turning knob at wire W repaints dial W (not parameter-number dial),
  incl. the shared-parameter case.
- Regression: 16-macro rack identical to today's good behaviour; smart-zoning
  synths and BOB devices unchanged.
