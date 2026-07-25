# grid-origin plan

## Problem

`live_surfaces/grid/controller_grid.nt` declares 4x4 `layout: grid` blocks with a
`midi_range`. The generator walks that range **row-major from the top-left**:
list index 0 lands at row 1 col 1, index 1 at row 1 col 2, and so on.

The Intech Grid hardware does not number its buttons that way. It counts **rows
bottom-to-top, columns left-to-right**. For `grid-4` with `midi_range: B2-D4`
(notes 59-74) the hardware actually emits:

```
 71 72 73 74      <- physical top row
 67 68 69 70
 63 64 65 66
 59 60 61 62      <- physical bottom row
```

The generator assumes the mirror image of that. Every `grid-N:r::c` coordinate
therefore addresses the wrong physical button, in a way that looks like "Ableton
is still using the old mapping" because nothing errors — the notes simply land on
different cells than the config says.

Confirmed empirically: the `mode-button: grid-4:4::1` binding resolves to note 71,
and the physical button that emits note 71 is the **top-left** of the block.

## Decision

Add an optional `origin:` field to `layout: grid` control groups naming the
physical corner that holds the **first** value of `midi_range`.

```
control_groups:
    -
        layout: grid
        number: 4
        type: button
        midi_channel: 1
        midi_type: note
        midi_range: B2-D4
        rows: 4
        columns: 4
        origin: bottom-left     # default: top-left
```

Values: `top-left` (default), `top-right`, `bottom-left`, `bottom-right`.

Traversal is always row-major *from that origin*: fill the origin's row
horizontally away from the origin corner, then step to the next row away from the
origin corner.

### Rejected alternatives

- **Descending ranges** (`midi_range: D4-B2`). Only expresses a 180 degree
  rotation. This hardware is a *vertical flip* — descending would also mirror the
  columns and silently transpose 12 of the 16 cells. It also encodes a physical
  fact as a side effect of range direction rather than stating it.
- **Comma form** (`midi_range: D4,CS4,...`). Already works today and expresses any
  permutation; kept as the escape hatch, but too verbose and error-prone to be the
  answer for a whole-block flip.
- **`column-major` traversal.** No evidence any real controller needs it. Add when
  one does.

## Design

`ControlGroupPartV2._midi_list` produces the ordered MIDI numbers;
`build_midi_coords` assigns list index -> logical row-major position, and
everything downstream (`_resolve_grid_2d`'s `idx = (r-1)*cols + (c-1)`, the flat
`grid-N:col` form, `hud_layout`) reads that list as logical top-left row-major.

So **the single insertion point is a permutation of `_midi_list`**. No downstream
consumer changes.

For a grid with `R` rows and `C` columns, logical cell `(r, c)` (1-based, top-left)
reads raw index:

| origin | raw index for logical (r, c) |
|---|---|
| `top-left` (default) | `(r-1)*C + (c-1)` |
| `top-right` | `(r-1)*C + (C-c)` |
| `bottom-left` | `(R-r)*C + (c-1)` |
| `bottom-right` | `(R-r)*C + (C-c)` |

i.e. flip the row term when the origin is `bottom-*`, flip the column term when
the origin is `right`.

## Consequence to flag

The flat form `grid-N:i` indexes the *logical* list, so once `origin` is set the
flat bindings in `ck_grid.nt` move too. `on-off: grid-4:3` currently resolves to
note 61; under `origin: bottom-left` it resolves to note 73 (logical top row,
3rd cell). That is the intended correction, not a regression — but the mapping
file's flat bindings need a re-read against the physical layout after the change.

## Steps (TDD)

1. **Failing tests** in `tests/test_controller.py`:
   - `origin` defaults to `top-left`; existing grid tests keep passing unchanged.
   - `origin: bottom-left` on a 4x4 note grid: `grid-N:1::1` -> last row's first
     raw value; full logical order equals the expected flipped table.
   - `origin: top-right` and `origin: bottom-right` permutation tables.
   - `origin` on a non-grid layout raises a readable `ValueError`.
   - Ascending-only note range error message names `origin:`.
   - Reverse CC range (`31-16`) produces a real error rather than an empty list
     that trips the `rows*columns` count check with a confusing message.
2. **Implement** in `ableton_control_surface_as_code/model_controller.py`:
   - `GridOrigin` enum in `core_model.py`.
   - `origin: Optional[GridOrigin]` on `ControlGroupPartV2`; validate grid-only in
     `validate_midi_range`.
   - Apply the permutation at the end of `_midi_list` (grid layout only).
   - Retarget the "Note range must be increasing" message to mention `origin:`.
   - Reject reverse CC ranges in `RangeV2.parse` / `_midi_list`.
   - Fix the off-by-one in `source_info=... position {i - 1}` (enumerate starts at
     0, so the first control currently reports `position -1`) — it is the debug
     string for exactly this feature.
3. **Integration**: a fixture controller with `origin: bottom-left` generating a
   surface, asserting the emitted `ConfigurableButtonElement` note numbers land on
   the expected cells.
4. **Docs**: `docs/` entry for `origin:`, including the traversal diagram above.
5. **Apply** to `live_surfaces/grid/controller_grid.nt` (all four blocks) and
   re-read `ck_grid.nt`'s flat bindings. User redeploys and restarts Ableton.

## Open question for step 5

Only `grid-4` has been verified empirically (note 71 = physical top-left). Whether
grid-1 (buttons) and grid-2/grid-3 (knobs) share the same `bottom-left` origin
needs one press/turn each to confirm before setting `origin` on all four blocks.
