# HUD Dividers

Add a new top-level key to controller `.nt` files, at the same level as
`control_groups`, called `dividers`. Each divider draws a **purely cosmetic**
vertical rule in the HUD between two named grids — grouping the surface into
readable zones (e.g. the two PO16 synth banks). No effect on slot indexing,
modes, or mappings.

```yaml
dividers:
    -
        a: grid-1
        b: grid-2
    -
        a: grid-2
        b: grid-3
```

## Design decisions (grill-me)

- **Purpose:** cosmetic zone grouping only. A divider never triggers the
  section machinery (`offset_layout`/`combine_layouts` slot-index bumping) — it
  reuses only the *visual treatment* of the existing section rule
  (`HUDView.swift` renders a full-height `Rectangle` between sections).
- **`a`/`b` semantics:** the two grids a boundary sits between, addressed with
  the existing `grid-N` identifiers (resolved through `ControllerV2._grids()`).
- **Orientation:** vertical rules only (MVP). The grid/PO16 surface lays grids
  out side-by-side (columns). Two grids that share a `grid_col` (vertically
  stacked → a row boundary) raise a clear GenError rather than silently drawing
  nothing.
- **Location:** controller file (physical), not mapping file — the 4×4 blocks
  are a physical property of the surface.

## Boundary resolution

`grid-N` → the logical grid `_grids()[N-1]`, whose cells all share one HUD
`grid_col`. A divider `{a: grid-A, b: grid-B}` resolves to a boundary column =
`max(grid_col(A), grid_col(B))` — the HUD draws a full-height rule immediately
to the *left* of that column. `divider_columns()` returns the sorted, de-duped
set of boundary columns. Errors: grid ref out of range, malformed `grid-N`, or
`grid_col(A) == grid_col(B)` (stacked, unsupported).

## Wire protocol

New backward-compatible message (unknown verbs already parse to
`.unknown`/`UnknownMsg` and are ignored by old receivers):

```
DIVIDERS|<n>|<col0>|<col1>|...
```

`col` values are HUD `grid_col` boundaries (draw a rule to the left of that
column). Only emitted when the surface has dividers, so non-divider surfaces
are byte-identical on the wire. Emitted alongside `LAYOUT`: once at init
(`Remote.init_layout`), on re-handshake (`resend_layout`), and at the head of
every non-suppressed burst (`refresh_burst`). Buffered into pending on the
receiver, published on `COMMIT`, persists across `DEVICE` (like `pendingCells`).

## Files

**Python**
- `model_controller.py` — `Divider` model; `dividers` on `ControllerRawV2` /
  `ControllerV2`; `ControllerV2.divider_columns()`.
- `hud_protocol.py` — `encode_dividers`, `DividersMsg`, parse `DIVIDERS`.
- `hud_client.py` — `HudClient.send_dividers` + `NullHudClient` no-op.
- `helpers.py` — `SurfaceConfig.hud_dividers`; thread into
  `Remote.init_layout(cells, dividers)`; emit in `resend_layout` +
  `refresh_burst`.
- `gen.py` — compute `hud_dividers_raw` from `controller.divider_columns()`
  (empty for the compositor override path); bake as `$hud_dividers`.
- `templates/surface_name/modules/main_component.py` — pass `hud_dividers=`.

**Swift**
- `WireProtocol.swift` — `.dividers([Int])` + `DIVIDERS` parse.
- `DeviceState.swift` — `pendingDividerCols`/`dividerCols`, publish on COMMIT.
- `HUDView.swift` — split each section's columns into groups at the divider
  boundaries; render the existing full-height rule between groups. No dividers
  → single group → identical to today.

## Scope notes

- Composition (lc_parks): `dividerCols` are applied within every section; the
  standalone grid surface is section 0 only, so this is fine in practice. A
  composited primary's dividers would need per-section tagging — deferred.
