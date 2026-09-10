# Grid Layouts

## Context

Today, mapping `.nt` files address controls only by physical **rows** — e.g. `row-5:1-4`,
`row-6:1-4`, `row-7:1-4`, `row-8:1-3`. When a logical control set (say, the 15 buttons of a
device's switch-list) spans several rows, the author must enumerate every row and split the
count by hand. This is tedious and fragile.

We want a **grid** coordinate that addresses a whole block of same-type controls as one flat,
1-indexed sequence laid out left-to-right, top-to-bottom:

```
mappings:
    switch-list:
        - range: grid-2:1-15
```

…replacing the four-row enumeration above.

**Scoping decision (interpreted from the user's answer):** the user said "knobs = grid-1,
buttons = grid-2." I'm implementing that as: a grid is a block of controls of one **type**,
ordered by physical layout position. On the ec4 (rows 1–4 knobs, rows 5–8 buttons):
**grid-1 = the knobs, grid-2 = the buttons**. `N` in `grid-N` selects the Nth grid. (Note: the
original brief used `grid-1` for the buttons — with this rule that is `grid-2`. The example
here is corrected accordingly.)

Two behaviors worth a veto at approval time:
- **By type, not by contiguous region.** Grids are grouped by control `type`. On ec4 this is
  unambiguous (knobs at col 0, buttons at col 1). But two *non-contiguous* blocks of the same
  type on a future controller would merge into one grid rather than become two. If you'd
  rather grids be contiguous physical blocks, say so and I'll switch the grouping key.
- **Order follows layout position, not file order.** Within a grid, controls are ordered by
  `(grid_row, grid_col)` (which derives from `under`/`right_of`), then by position within each
  group — i.e. spatial reading order, not the order rows appear in the `.nt` file. These
  coincide on ec4. Groups with neither `under` nor `right_of` default to `(0,0)`.

## Approach

Add `grid` as a third axis kind alongside `row`/`col`. Parsing already throws the axis label
away, so the first step is to *preserve* it; the rest is a new resolution branch in the
controller that flattens a type-block of groups and indexes into it.

### 1. Grammar + EncoderCoords — preserve the axis kind
`ableton_control_surface_as_code/encoder_coords.py`

- Grammar: add a `grid` terminal and extend the axis rule:
  ```
  grid : "grid"
  axis : row | col | grid
  ```
- Transformer: add `grid = lambda self, _: "grid"` (mirrors existing `row`/`col` lambdas;
  `axis()` already returns `str(items[0])`).
- `EncoderCoords` (lines 63–70): add a defaulted field
  `axis_kind: str = "row"`. The default keeps every existing
  `EncoderCoords(row=…, range_=…)` call site and test equality intact.
- `single()` / `multi()` (lines 135–149): stop discarding `axis`; pass `axis_kind=axis`.

### 2. Grid resolution in the controller
`ableton_control_surface_as_code/model_controller.py`

- Add a helper on `ControllerV2` that builds the ordered list of grids — group the merged
  `control_groups` by `type`, ordered by first appearance after sorting on
  `(grid_row, grid_col)` (same sort key used in `hud_layout.py:32`). Returns a list of grids,
  each a list of `ControlGroup`s already in layout order:
  ```python
  def _grids(self) -> List[List[ControlGroup]]:
      by_type, order = {}, []
      for g in sorted(self.control_groups, key=lambda g: (g.grid_row, g.grid_col)):
          if g.type not in by_type:
              by_type[g.type] = []; order.append(g.type)
          by_type[g.type].append(g)
      return [by_type[t] for t in order]
  ```
- In `build_midi_coords` (lines 203–233), dispatch on `coords.axis_kind`. The existing
  `group.number == coords.row` loop stays as the `row`/`col` path. Add a `grid` branch:
  - `grids = self._grids()`; pick `grids[coords.row - 1]` (validate `1 <= N <= len(grids)`
    with a readable `ValueError` listing how many grids exist).
  - Flatten the block: `flat = flatten(g.midi_coords for g in grid)` (reuse the existing
    `flatten` helper at line 126).
  - For each `col in coords.range_inclusive`, bounds-check against `len(flat)` (error message
    states the grid size, mirroring the current row out-of-range message) and append
    `flat[col-1].with_encoder_refs(coords.encoder_refs)`.
  - `res_type` = the block's uniform type (`grid[0].type`).

This is the single central lookup every mapping module already calls, so grid support reaches
all mapping types with no per-type changes. The tests below exercise the device/switch-list
path directly; mixer/transport ride the same code path but aren't separately tested (low risk,
same `build_midi_coords` entry point).

### 3. Validation
`ableton_control_surface_as_code/core_model.py` — `_validate_encoder_coords` (line 296)
already checks `c.row >= 1` and range sanity; for grids `row` holds N, so the existing check
covers "grid number must be >= 1". Upper-bound (N beyond the number of grids, range beyond the
flattened size) is enforced at resolution time in step 2 where the controller is in scope.

## Files to modify
- `ableton_control_surface_as_code/encoder_coords.py` — grammar, transformer, `EncoderCoords.axis_kind`
- `ableton_control_surface_as_code/model_controller.py` — `_grids()` helper, grid branch in `build_midi_coords`
- Tests (see below)

No controller `.nt` schema change is required — grids are derived from existing `type` +
`under`/`right_of` layout fields.

## Tests (TDD: write failing first)
- `tests/test_encoder_coords.py` — parse `grid-2:1-15` →
  `EncoderCoords(row=2, range_=(1,15), axis_kind="grid", encoder_refs=[])`; a single
  `grid-1:3`; grid + refinement (`grid-2:4 toggle`); confirm `row-3:4` still parses with
  `axis_kind="row"` (back-compat).
- `tests/test_controller.py` — using the ec4-style fixture (knob rows 1–4, button rows 5–8):
  - `grid-1:1` → first knob's MIDI number; `grid-1` spans all knobs in layout order.
  - `grid-2:1-15` → 15 button coords, ordered top-to-bottom/left-to-right, first == row-5 col-1.
  - out-of-range grid number and out-of-range index each raise a readable error.
- `tests/test_device.py` — a `switch-list` (and/or `encoder-list`) using `grid-2:1-15`
  resolves to the same MIDI coords as the equivalent multi-row enumeration, proving the
  end-to-end mapping path.

## Verification
1. `poetry run pytest tests/test_encoder_coords.py tests/test_controller.py tests/test_device.py`
2. Edit `live_surfaces/ec4/ck_ec4.nt` to replace the row-5..row-8 `switch-list` with
   `- range: grid-2:1-15`, then
   `poetry run python ableton_control_surface_as_code/gen.py live_surfaces/ec4/ck_ec4.nt` and
   diff the generated surface against the pre-change output to confirm identical MIDI wiring.
3. `poetry run pytest` (full suite) to confirm no back-compat regressions.
