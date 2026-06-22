# Grid 2D indexing, `layout: grid`, and note ranges

Builds on the shipped grid feature (`grid-N:flat`). Three additions the user asked for,
for a controller with a 4×4 grid of knobs and a grid of buttons:

## 1. `layout: grid` becomes a real controller axis
`core_model.py` — add `grid = 'grid'` to `LayoutAxis`.

`model_controller.py::ControlGroupPartV2` — add two optional fields:
```
rows: Optional[int]    = Field(None)
columns: Optional[int] = Field(None)
```
`validate_midi_range` (model_validator): when `layout == grid`, **require** both `rows` and
`columns` (and forbid `row_parts`); when layout != grid they must be absent. `rows × columns`
must equal the control count — checked in `validate_controller_semantics` (where `_midi_list`
is already evaluated defensively) so the message lands with the other MIDI problems.

`ControlGroup` gains `columns`/`rows` attributes; `merge_groups` propagates them from
`groups[0]`. (A grid is one control group in practice; if a grid spans several groups, 2D
access uses the first group's `columns`.)

## 2. Note ranges (`midi_range: C2-DS4`)
`ControlGroupPartV2._midi_list` — for note-typed groups with no comma and a `-`, expand the
inclusive chromatic run between two **note names**. Note names themselves contain `-` (e.g.
`C-2` = 0), so split on the *leftmost* dash that yields two valid note names (handles
`C-2-DS4`). Must be increasing (`to >= from`); otherwise a readable error. Comma-lists and
single notes keep working unchanged.

## 3. `::` 2D coordinate — `grid-2:2::1-4`
Single `:` stays invariant (axis selector → range). `::` lives *inside* the range slot as the
row→col separator, used ONLY for grids.

`encoder_coords.py`
- Grammar: the range slot after `:` becomes `(grid_cell | range)`:
  ```
  range     : NUMBER | (NUMBER "-" NUMBER)
  grid_cell : NUMBER "::" range
  coords    : axis "-" axis_no ":" (grid_cell | range)
  ```
- Transformer: `grid_cell` → a `GridCell(row, cols)` marker. `single`/`multi` detect the
  marker: flat → `EncoderCoords(row=axis_no, range_=range, axis_kind=axis)`; 2D →
  `EncoderCoords(row=axis_no, grid_row=cell.row, range_=cell.cols, axis_kind=axis)`.
- `EncoderCoords` gains `grid_row: Optional[int] = None` (None = flat; default keeps every
  existing construction/equality intact).

`core_model.py::_validate_encoder_coords` — when `grid_row` is set, require `grid_row >= 1`.

`model_controller.py::_resolve_grid_coords`
- Flat path (grid_row is None): unchanged.
- 2D path: `columns = grid[0].columns` (error if None → "grid-N is not 2D; add rows/columns").
  Validate `1 <= grid_row <= rows` and each col `1 <= c <= columns`; flat index
  `= (grid_row-1)*columns + (c-1)`; append `flat[idx].with_encoder_refs(...)`.

## Tests (TDD)
- `test_encoder_coords.py`: parse `grid-2:2::3` → `grid_row=2, range_=(3,3)`;
  `grid-2:2::1-4` → `grid_row=2, range_=(1,4)`; `grid-2:1-16` flat → `grid_row=None`;
  `grid-2:2::3 toggle` carries the refinement.
- `test_controller.py`: note-range `C2-DS4` expands to 28 increasing numbers, first 48;
  a 4×4 grid group resolves `grid-1:2::3` to the right MIDI number, `grid-1:1::1-4` to row 1,
  `grid-1:r::c` flat-index math matches `grid-1:flat`; out-of-range row/col raise readable
  errors; `layout: grid` missing rows/columns raises; `rows*cols != count` raises.
- Keep the existing flat-grid + back-compat suite green.
