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
- **Step 1 — rack tier.** Gated on the `update.py` prerequisite below (and on
  re-adding the `rackprobe` command, reverted with the rest). Then add the
  `macro_at` shape function + resolver tier + config.

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

## PREREQUISITE — one `update.py` run before any rack-shaping code

`macro_at()` returns a macro *number*; the resolver needs a *parameter*. That
cell→param path is **undefined** until we confirm the rack's parameter layout, so
this gates the code (not a footnote). On a real rack, log via `update.py`:

- `device.parameters` names + indices — is Macro M at `parameters[M]` (Device On
  at 0)? The screenshot's first cell reads "Chain Selector": is that a **renamed
  macro** or the actual **`chain_selector`** parameter sitting in `parameters[1]`?
  If the latter, every macro index shifts by one and a 2×4 rack would drive the
  wrong eight params. This must be pinned first.
- `device.visible_macro_count` — readable, and correct (8 vs 16)?
- `len(device.macros_mapped)` — 16, or `visible`? The resolver indexes
  `macros_mapped[M-1]`; a wrong length is an IndexError *inside a burst* (worst
  failure site). Guard the access accordingly.

## Resolved (no longer open)

- **Paging:** racks cap at 16 macros = one 2×8 page. Page 1 is the whole rack; no
  rack paging.

## Open questions (design choices, decide at review)

1. **Odd/small counts.** Is Live's panel always 2 rows with `cols=ceil(n/2)`?
   8/16 are certain; verify 6/12 if you use them.
2. **Flag placement** — own `rack-shaping:` flag, or part of `smart-zoning`?
3. **BOB precedence** — if a rack also has a custom BOB entry, which wins? Default
   proposal: rack shaping wins for racks (more specific, dynamic).

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
