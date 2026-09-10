# HUD zone colours: controls back to defaults, zone hue becomes a subtle group background

## Context

Smart-zoning (commit 1f335da) colour-codes the HUD by zone: each dial's value arc + dull
track and each button's border are tinted with the slot's zone hue from
`zone_colors` in `data/synth_zone_tables.json`. TODO: this is too loud. Revert the
controls themselves to the default colours (cyan value arc, grey track, white
border — what the TODO calls "ableton blue") and instead paint a **subtle
zone-coloured background area** behind each zone's group of slots.

**Scope decision (confirmed with user):** HUD only. The physical Grid button
LEDs keep the zone palette (`source_modules/grid_led_client.py` untouched), so
the hardware stays colour-coded; the HUD group background preserves the
hardware↔HUD correspondence, just quieter.

## Key facts

- The wire already carries everything needed: `ZONES|n|kind|idx|hex|…` delivers a
  per-slot colour map, published as `dialColors: [Int: String]` /
  `buttonColors: [Int: String]` on `DeviceState` (cleared on `DEVICE`, published
  on `COMMIT` — device-scoped lifecycle, unlike `DIVIDERS`). **No protocol or
  Python changes.**
- Zone membership is not on the wire explicitly, but zones are contiguous slot
  runs within a cell (env = enc slots 17–24, global = 25–28, signature = 29–32,
  etc.), so grouping *contiguous runs of equal hex* inside each cell recovers the
  zone areas exactly. Adjacent zones always differ in hue (7 distinct colours).
- Rendering happens in `ableton_hud/Sources/AbletonHUD/HUDView.swift`:
  `cellView(_:)` renders each `HudCell` as an HStack of `DialSlotView` /
  `ButtonSlotView`; the zone hex is passed per slot today.

## Changes (Swift only — `ableton_hud/Sources/AbletonHUD/HUDView.swift`)

1. **Revert control tints.**
   - `DialSlotView`: delete the `zoneTint` computed property and the `zoneHex`
     parameter; track stroke back to `Color.gray.opacity(0.3)`, value arc back to
     `Color.cyan` (lines ~342/348).
   - `ButtonSlotView`: delete `zoneHex`; `borderColor` back to
     `Color.white.opacity(slot != nil ? 0.35 : 0.25)` (line ~384).
   - Keep the `Color(zoneHex:)` initializer — it's reused for the background.

2. **Group background in `cellView(_:)`.**
   - Partition the cell's slot indices `0..<cell.count` into contiguous runs of
     equal zone hex (looked up in `region.dialColors` / `region.buttonColors` by
     wire index; `nil` hex = un-zoned run, no background).
   - Render each run as its own inner HStack of slot views, wrapped in
     `.padding(~3*scale)` + `.background(RoundedRectangle(cornerRadius: 6*scale)
     .fill(zoneColor.opacity(0.10)))`. Subtle = fill only, ~0.10 opacity, no
     stroke. Tune opacity on hardware (0.08–0.14 range).
   - A zone that spans a dial cell and a button cell renders as two stacked
     chips (one per cell) — accepted; they carry the same hue so they still read
     as one area.
   - Non-zoned devices have empty colour maps → single run with no background →
     pixel-identical to pre-zoning layout.

3. **Layout care** (see `ableton_hud/layout_principles.md`): the extra padding
   changes intrinsic size under `.fixedSize()` — verify the panel resizes
   correctly at all zoom levels and that spacing between runs vs. within runs
   still aligns with the 8-slot grid rhythm (compensate the inter-run spacing so
   total cell width stays stable).

## TDD / verification

- `swift test` in `ableton_hud/` (existing `WireProtocolTests` must stay green;
  `DeviceState` is untouched). Add a unit test for the run-partition helper if it
  is extracted as a pure function (recommended: `func zoneRuns(count:colors:start:)
  -> [(Range<Int>, String?)]` in the view file or Core).
- `./ableton_hud/restart.sh`, then in Live: focus Operator/Drift → controls in
  default colours, subtle background chips behind osc/filter/lfo/env/global/
  signature runs; focus a non-zoned device (e.g. EQ Eight) → no chips; Grid
  button LEDs unchanged.
- Python `poetry run pytest` + `./build.sh` untouched but run before any commit
  per CLAUDE.md (mention this plan in the commit message).
