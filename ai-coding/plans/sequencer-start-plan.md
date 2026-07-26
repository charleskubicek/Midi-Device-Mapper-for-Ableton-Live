# sequencer-start plan

## Symptom

The 16-step sequencer (grid-1 buttons) and the per-step velocity encoders
disagree about where beat 1 lives:

- sequencer: beat 1 on the physical **bottom-left** pad, running **upward**
- velocities: step 1 on the physical **top-left** encoder, running left-to-right

## Two distinct decisions, only one of which is expressible today

There are two independent orientation questions, and conflating them is what
made this hard to see:

1. **Hardware -> grid coordinates.** Which physical corner emits the first value
   of `midi_range`. This is a *fact about the controller*, measured, not chosen.
   Already expressible: `origin:` in the controller file (grid-origin plan).
2. **Grid coordinates -> step number.** Which grid cell is beat 1, and which way
   the steps advance. This is a *musical preference*, chosen, not measured.
   **Not expressible today.**

These compose rather than duplicate: `origin` decides which button is cell
(1,1); `sequencer-start` decides which cell is step 1. Even with the hardware
perfectly described, "beat 1 at bottom-left, running up" remains a legitimate
choice that the config currently cannot state.

Decision 2 is currently hardcoded: `_build_drum_maps` (`model_device.py:338/357/364`)
does `enumerate(midis)` over the flat resolved list, which is logical row-major
from the top-left. So step 1 is always the top-left cell, and there is no knob.

## Design

A single top-level key in the **mapping** file (`ck_grid.nt`), because the
traversal is a property of the sequence, not of any one control block:

```
# Which grid corner holds step 1 of the drum sequencer, and therefore which way
# steps advance (row-major from that corner). Default: top-left.
sequencer-start: top-left     # top-left | top-right | bottom-left | bottom-right
```

**Governs `sequencer:` and `velocities:` together.** They are two views of the
same 16 steps; letting them differ would reintroduce exactly the bug being
fixed. One key, both roles — that is the single source of truth the surface was
missing.

**Does not govern `pads:`.** A pad index selects *which drum*, not which step;
that ordering belongs to Live's drum rack, not to us.

Reuses the existing `GridOrigin` enum and its `flips_rows` / `flips_columns`
traversal rule, so the codebase keeps one definition of "row-major from a
corner" rather than growing a second.

### Where it applies

In `_build_drum_maps`, permute the resolved `midis` list before `enumerate`.
That is the one place list position becomes a step number, mirroring how
`_midi_list` is the one place list index becomes a grid position.

### Grid dimensions

The permutation needs rows/columns. Derived from the `ControlGroup` the range
resolves to (`ControlGroup.rows` / `.columns`, looked up by the group number in
`EncoderCoords.row`). Only valid when the range covers exactly one grid block
whose `rows * columns` equals the control count.

Anything else (a range spanning two blocks, an 8-of-16 subrange, a non-grid
layout) has no unambiguous 2D shape, so a non-default `sequencer-start` there is
a `GenError` naming the reason rather than a silent guess. `top-left` stays
valid everywhere since it is the identity permutation.

### Threading

`sequencer-start` is a root-level setting consumed by one builder. That is the
same shape as `functions_file`, which is threaded as a 5th argument through
`_MAPPING_BUILDERS` and ignored by every builder except `functions`. Follow that
precedent rather than inventing a new carrier.

## Steps (TDD)

1. **Failing tests** in `tests/test_drum_rack.py` / `tests/test_gen.py`:
   - default (key absent) -> step 0 is the top-left cell; existing tests unchanged.
   - `sequencer-start: bottom-left` on a 4x4 -> step 0 is the bottom-left cell,
     step 3 the bottom-right, step 12 the top-left.
   - `sequencer:` and `velocities:` over two different blocks get the *same*
     traversal from the one key.
   - `top-right` / `bottom-right` permutation tables.
   - non-default value over a range with no unambiguous grid shape -> GenError.
   - `pads:` is unaffected by the key.
2. **Implement**: `sequencer_start` on `RootV2` / `RootV2ModesOrModeless`
   (alias `sequencer-start`, default `top_left`); thread through
   `build_mappings_model_v2` into `build_device_model_v2_1` -> `_build_drum_maps`;
   apply the permutation.
3. **Docs**: `docs/mapping_file.md` entry, contrasting it with the controller
   file's `origin:` so the two are not confused again.
4. Regenerate; user redeploys and restarts Live.

## Separate, still-live issue: grid-1's `origin` is probably wrong

Independent of this feature, the evidence says `controller_grid.nt`'s grid-1
carries an incorrect hardware description. It was added by commit `7612587`
with an explicit `UNVERIFIED — inferred from grid-4, not measured` comment.

grid-1 declares `origin: bottom-left`, giving
`logical=[48,49,50,51, 44..47, 40..43, 36..39]`.

- If grid-1 truly counted bottom-left, logical[0] = 48 would be at the physical
  **top**-left and the sequencer would run **downward**.
- If grid-1 counts top-left, logical[0] = 48 is at the physical **bottom**-left,
  steps 12-15 (notes 36-39) land on the top row, and it runs **upward**.

The reported symptom is the second. So grid-1's hardware counts from the
top-left and the `origin:` line should be dropped — the `36 = no flip (drop this
line)` branch its own comment describes.

**Why this still matters after `sequencer-start` ships:** setting
`sequencer-start: bottom-left` would cancel the wrong `origin` and make the
sequencer look correct, but `origin` also drives things `sequencer-start` never
touches — grid-1's `button:` slot bindings in both modes (`ck_grid.nt:67`,
`:130`) and the HUD labels for grid-1, which would stay flipped. Two wrongs
cancelling in one role and not the others.

Recommended: drop grid-1's `origin`, then leave `sequencer-start` at its
top-left default. Needs one press to confirm (physical top-left button of grid-1
should log note 36).

grid-2 is now confirmed `top-left` by this same symptom (its velocity step 1 is
physically top-left, as declared). grid-3 remains unverified.
