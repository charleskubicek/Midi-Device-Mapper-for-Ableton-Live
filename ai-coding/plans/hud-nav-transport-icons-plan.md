# HUD nav/transport icons plan

Render SF Symbol glyphs (macOS's standard icon set) on the HUD for transport and
nav buttons, instead of / alongside text labels. Buttons like track-nav,
device-nav, transport, and custom loop operations get an iconic label that reads
instantly in the small button cells.

## Why this is cheap

- The HUD is a **SwiftUI** app and **already uses SF Symbols** — the close button
  is `Image(systemName: "xmark")` (`ableton_hud/Sources/AbletonHUD/HUDView.swift:129`).
  No assets to bundle; SF Symbols ship with the OS.
- Every static button label flows through **one** Python function:
  `_label_pairs_for_mapping()` in `ableton_control_surface_as_code/hud_layout.py:155`.
  It returns `(coord, label)` strings for `track-nav`, `device-nav`, `transport`,
  `parameter-pager`, `functions`, etc. Those strings become the wire `name` field
  and land in the Swift `Text(slot?.name ?? "")`.
- No protocol change: the `SLOT`/`UPDATE` `name` field already carries an
  arbitrary string.

## Wire convention

> **SUPERSEDED by Phase 2.** The original `sf:`-prefix-in-`name` idea below is
> replaced by a **dedicated `glyph` field** on the slot wire. The new requirement
> is that a button shows an **icon *inside* the button** *and* a text name, so a
> single overloaded `name` field can't carry both — glyph and name must be
> separate. `@hud_name(name, glyph=None)` carries both. See **Phase 2**. The
> `sf:`-prefix design is kept here only for history.

~~Signal "this label is an icon" with an `sf:` prefix on the existing `name`
field:~~

```
SLOT|button|3|sf:chevron.right|1|0|1
```

- ~~No new field, no `COMMIT` count change, no protocol version bump.~~
- Device parameter names come from live Live data and never carry the prefix, so
  there is no collision risk with the static labels we control.
- The receiver **always keeps a text fallback**: an unknown `systemName` renders
  blank in SwiftUI, so an icon typo must degrade to text, not to an empty cell.

## Phase 0 — confirm the label→wire path (done)

Traced and verified: the label string reaches the wire **verbatim**.
`_label_pairs_for_mapping` → `collect_mode_labels` (`hud_layout.py:142`) →
`mode_hud_labels` (`gen.py:216`) → `_overlay_labels` wraps it as
`SlotPayload(label, 0, 0, 1)` (`helpers.py:47`) → `send_slot(..., p.name, …)` →
`encode_slot` → `SLOT|button|idx|{name}|…` (`hud_protocol.py:124`). No
lowercasing, sanitizing, or truncation on the path, and `sf:chevron.right`
contains no `|` to collide with the delimiter — so the prefix and dots survive.
The unstable button-slot emission flagged in the docs concerns *which* button
slots emit, not label mangling; the `name` field is passed through untouched.

## The three touch-points

### 1. Swift receiver — `HUDView.swift`

Add one small helper view and use it at the two label sites
(`HUDView.swift:354` dial, `:397` button). **Gate on symbol existence, not on the
prefix** — SwiftUI renders a *blank* for an unknown `systemName`, so branching on
`hasPrefix` alone would turn an `@hud_name` typo into an empty cell instead of
degrading to text. Check `NSImage(systemSymbolName:)` first:

```swift
struct SlotLabel: View {
    let raw: String
    let scale: CGFloat
    let dim: Bool

    private func textLabel(_ s: String) -> some View {
        Text(s)
            .font(.system(size: 9 * scale, weight: .light))
            .minimumScaleFactor(0.7)
            .allowsTightening(true)
            .foregroundColor(Color(white: dim ? 0.18 : 0.9))
            .lineLimit(2)
            .multilineTextAlignment(.center)
    }

    var body: some View {
        if raw.hasPrefix("sf:") {
            let sym = String(raw.dropFirst(3))
            // Existence check: unknown systemName renders blank, so fall back to
            // the (readable, debuggable) symbol name as text rather than nothing.
            if NSImage(systemSymbolName: sym, accessibilityDescription: nil) != nil {
                Image(systemName: sym)
                    .font(.system(size: 11 * scale, weight: .regular))
                    .foregroundColor(Color(white: dim ? 0.18 : 0.9))
            } else {
                textLabel(sym)
            }
        } else {
            textLabel(raw)
        }
    }
}
```

The built-in lookup labels are verified once, so they're safe; this existence
check exists to protect the **user-typed** `@hud_name("sf:…")` path, where typos
actually happen.

- Keep the existing `.frame(width: 44 * scale, height: 22 * scale, alignment: .top)`
  wrapper so an icon and a text label occupy the same footprint.
- Baseline: icon sits in the label slot (below the button chrome / arc), exactly
  where text sits now. This keeps dials and buttons consistent and is the
  smallest change.
- Optional enhancement (later): for `button` slots, render the symbol *inside*
  the rounded-rect chrome instead of below it, since a nav button is inherently
  iconic. Bigger change to `ButtonSlotView`; defer.

### 2. Python — `hud_layout.py`

Replace the hard-coded strings in `_label_pairs_for_mapping()` with symbol names
from a lookup, for the built-in button types. Keep the current strings as the
fallback when a symbol isn't defined for a case.

```python
# hud_symbols.py (new, leaf module)
TRACK_NAV_SF = {Direction.dec: "sf:chevron.left",  Direction.inc: "sf:chevron.right"}
DEVICE_NAV_SF = {
    DeviceNavAction.left:  "sf:arrowtriangle.left.fill",
    DeviceNavAction.right: "sf:arrowtriangle.right.fill",
    DeviceNavAction.first: "sf:arrow.left.to.line",
    DeviceNavAction.last:  "sf:arrow.right.to.line",
}
TRANSPORT_SF = {
    "play_stop_raw":            "sf:playpause.fill",
    "record_session_raw":       "sf:record.circle",
    "record_arrangement_raw":   "sf:record.circle.fill",
    "loop_raw":                 "sf:repeat",
    "midi_arrange_overdub_raw": "sf:pencil.and.outline",
}
PAGER_SF = {"dec": "sf:chevron.up", "inc": "sf:chevron.down"}
```

Then in `_label_pairs_for_mapping`:

```python
if t == 'track-nav':
    return [(mm.only_midi_coord, TRACK_NAV_SF.get(mm.direction, f"track {mm.direction.value}"))
            for mm in mapping.midi_maps]
```

…and likewise for `device-nav`, `transport`, `parameter-pager`.

This is a display-only change — the `api_call` / `direction` / `action` values
that drive behavior are untouched.

### 3. Custom operations (loop move, loop expand/shrink) — via `@hud_name`

Loop move and loop expand/shrink are **custom functions** in `functions.py`, not
built-in mapping types. They already support `@hud_name("...")`
(`model_functions.py:94`), which sets the HUD label statically. Under the `sf:`
convention the icon is chosen **at the function definition** — no generator
change needed beyond the receiver understanding the prefix:

```python
class Functions:
    @hud_name("sf:arrow.left.and.line.vertical.and.arrow.right")   # loop expand
    def loop_expand(self): ...

    @hud_name("sf:arrow.right.and.line.vertical.and.arrow.left")   # loop shrink
    def loop_shrink(self): ...

    @hud_name("sf:arrowshape.left.fill")                           # loop move ←
    def loop_move_left(self): ...

    @hud_name("sf:arrowshape.right.fill")                          # loop move →
    def loop_move_right(self): ...
```

So the answer to "how do I pick which arrow": for built-ins it's the lookup
table above; for custom ops the user picks it themselves in `@hud_name`.

## Choosing the arrows — a symbol vocabulary

The problem: four different operations all conceptually move "left/right", and
plain `←`/`→` on all of them would be ambiguous. SF Symbols solves this because
directional arrows come in **semantic families** — encode the *operation type* in
the glyph family, the *direction* in the `.left`/`.right` suffix:

| Operation                | Meaning                    | Left symbol                                   | Right symbol                                  |
|--------------------------|----------------------------|-----------------------------------------------|-----------------------------------------------|
| **Track nav**            | step selection between tracks | `chevron.left`                             | `chevron.right`                               |
| **Device nav (step)**    | move within device chain   | `arrowtriangle.left.fill`                     | `arrowtriangle.right.fill`                    |
| **Device nav (ends)**    | jump to first / last       | `arrow.left.to.line`                          | `arrow.right.to.line`                         |
| **Loop move**            | translate loop in time     | `arrowshape.left.fill`                        | `arrowshape.right.fill`                       |
| **Loop expand / shrink** | resize loop length         | expand: `arrow.left.and.line.vertical.and.arrow.right` | shrink: `arrow.right.and.line.vertical.and.arrow.left` |

Rationale:
- **chevron** = light "next/prev" step → track paging.
- **filled triangle** = a firmer "advance" → device chain, distinct from chevrons.
- **`.to.line`** = "go to the end" → device first/last.
- **filled arrowshape (banner arrow)** = "shove this block over" → loop translate.
- **arrows around a vertical line** = the two arrows push *away from* a center
  line (expand) or *toward* it (shrink) — reads as literally widening/narrowing a
  region, which is exactly the loop-length gesture. This is the strongest pick in
  the set and the reason SF Symbols is worth it over ad-hoc glyphs.

Verify each name in the SF Symbols app against the app's **deployment target**
before wiring; substitute a near neighbour if a weight/variant is missing. Known
risk: `arrowshape.left.fill` / `arrowshape.right.fill` may be SF Symbols 4+
(macOS 13+) rather than 3 — check, and if the target is older use
`arrow.left`/`arrow.right` for loop-move. The vertical-line resize pair
(`arrow.left.and.line.vertical.and.arrow.right` + mirror) exists and is the
strongest pick — keep it. With the Phase-1 existence check in place, a missed
name degrades to visible text rather than a blank cell, which is what makes this
"pick names, verify later" workflow safe.

## Testing

- Python: extend the `hud_layout` label tests (find existing tests for
  `collect_mode_labels` / `_label_pairs_for_mapping`) to assert the `sf:` labels
  for track-nav / device-nav / transport / pager, and that an unmapped case falls
  back to the old text string. TDD: write these first.
- Swift: `AbletonHUDCore` parser tests already cover `SLOT`; the `sf:` prefix
  needs no parser change (it's an opaque `name`). Add a `SlotLabel` view smoke
  test if the target has view tests; otherwise verify by eye on a real burst.
- Integration: regenerate `ck_grid`, deploy, confirm nav/transport buttons show
  glyphs and that an intentionally-bad symbol name degrades to text.

---

# Phase 2 — icon *inside* the button + `@hud_name(name, glyph)` (ACTIVE)

Supersedes the Phase-1 `sf:`-in-`name` sketch. A button cell now carries **two**
independent pieces of display data: a text `name` (rendered below the button, as
today) and an optional SF Symbol `glyph` (rendered **inside** the button
rounded-rect). They travel in separate wire fields.

## `@hud_name` — two arguments

```python
# source_modules/hud_name.py — runtime no-op, now carries both
def hud_name(label, glyph=None):
    def decorator(fn):
        fn._hud_name = label
        fn._hud_glyph = glyph
        return fn
    return decorator
```

Usage in a user `functions.py`:

```python
@hud_name("Loop Expand", "arrow.left.and.line.vertical.and.arrow.right")
def loop_expand(self): ...

@hud_name("Prev Track")            # glyph omitted -> text only, empty button
def prev(self): ...
```

Glyph is the **bare** SF Symbol name (no `sf:` prefix — it's a dedicated field
now).

## Wire — new optional `glyph` field (8th)

```
SLOT|<kind>|<index>|<name>|<value>|<min>|<max>|<glyph>
UPDATE|<kind>|<index>|<name>|<value>|<min>|<max>|<glyph>
```

- Trailing field, appended **only when non-empty** (chosen over always-8 so the
  common text-only slot keeps its historical 7-field shape — existing golden
  tests and any older HUD keep parsing it unchanged):
  `SLOT|button|3|Loop Expand|1.0|0|1|arrow.left.and.line.vertical.and.arrow.right`.
- Both parsers accept **7 or 8** fields (7 ⇒ `glyph=""`) — mirrors the existing
  PAGE 5-or-7 tolerance, so a mid-upgrade old-surface/new-HUD pair still works.
- No `COMMIT` count change (still counts SLOT lines).

> **Phase 2a + 2b status: IMPLEMENTED & green.** Python (731) + Swift (82) suites
> pass. `ck_grid` regenerates with real glyphs baked end-to-end
> (`('Move loop L', 'arrowshape.left.fill')`, `('track inc', 'chevron.right')`,
> `('device left', 'arrowtriangle.left.fill')`) — proves the full
> `build_functions_model_v2` → bake chain and the built-in nav/transport tables.
> Emission-boundary guarded by a client-level datagram test. The Swift render is
> width-defensive (`resizable().scaledToFit()` + max frame) so wide multi-arrow
> glyphs fit the 36pt button. Glyph vocab lives in `hud_layout.py`
> (`_TRACK_NAV_GLYPH` / `_DEVICE_NAV_GLYPH` / `_TRANSPORT_GLYPH` / `_PAGER_GLYPH`).
> `live_surfaces/grid/functions.py` loop functions now carry glyphs. **Not yet
> committed or deployed** (user redeploys + restarts Ableton).

## Touch-points

### A. Swift receiver — `WireProtocol.swift`

1. `Slot` struct gains `public let glyph: String` (default `""` in a convenience
   init to keep existing call sites/tests compiling).
2. `SLOT`/`UPDATE` case: `guard fields.count == 7 || fields.count == 8`; read
   `let glyph = fields.count == 8 ? fields[7] : ""`; pass into `Slot`.

### B. Swift render — `HUDView.swift` `ButtonSlotView`

Render the glyph **inside** the `RoundedRectangle` via `.overlay`, keep the name
text below:

```swift
RoundedRectangle(cornerRadius: 5 * scale)
    .fill(isActive ? Color.white.opacity(0.35) : Color.clear)
    .overlay(RoundedRectangle(cornerRadius: 5 * scale).stroke(borderColor, lineWidth: 1.5 * scale))
    .overlay(glyphView)                       // <-- icon centered in the button
    .frame(width: 36 * scale, height: 20 * scale)

Text(slot?.name ?? "")                        // unchanged: name below
    ...
```

```swift
@ViewBuilder private var glyphView: some View {
    if let g = slot?.glyph, !g.isEmpty,
       NSImage(systemSymbolName: g, accessibilityDescription: nil) != nil {
        Image(systemName: g)
            .font(.system(size: 12 * scale, weight: .medium))
            .foregroundColor(Color(white: 0.92))
    }
    // invalid/missing glyph -> no overlay; the name text below still identifies
    // the button (existence-gated so a typo never blanks anything).
}
```

- Icon size tuned to the 36×20 button; `minimumScaleFactor` not needed for a
  symbol. Dials are unaffected (glyph only rendered in `ButtonSlotView`).

### C. Python `SlotPayload` — `hud_protocol.py`

Add a trailing defaulted field so every existing positional construction stays
valid:

```python
@dataclass(frozen=True)
class SlotPayload:
    name: str
    value: float
    vmin: float
    vmax: float
    glyph: str = ""
```

Update `encode_slot`/`encode_update` (and `encode_slot_payload`) to append
`|{glyph}`, and `_parse_slot_fields` to accept 7 or 8 fields.

**Critical — the glyph must survive the emission boundary.** The live burst path
does NOT call `encode_slot_payload`; it explodes the payload into scalars at
`helpers.py:687-690` via `HudClient.send_slot(kind, idx, p.name, p.value, ...)`,
which never reads `p.glyph`. So also:
- add a trailing `glyph: str = ""` param to `HudClient.send_slot` **and**
  `NullHudClient.send_slot` (hud_client.py:94, :135), forwarding to `encode_slot`;
- pass `p.glyph` at the button call site (helpers.py:690). Dial site (`:687`) and
  the `send_update` dial path (`:636`) leave glyph defaulted `""` — dials have no
  glyph.
- **Coalesce `None`→`""`** at the model boundary (make `SlotPayload.glyph`
  non-optional; have the decorator reader / `hud_glyph` yield `""` not `None`) so
  the wire never carries the literal string `"None"`.
- Add a **client-level test** asserting the emitted datagram carries the glyph —
  encode/parse unit tests alone go green while the feature is dead.

### D. Python label threading — `model_functions.py` + `hud_layout.py` + `helpers.py`

1. `FunctionLookup._hud_name_from_decorators` returns `(name, glyph)` — read the
   2nd positional arg or `glyph=` keyword from the `ast.Call`. `inspect_python_file`
   and `get_functions_from_class` thread the tuple through.
2. `FunctionsMidiMapping` gains `hud_glyph: Optional[str] = None`;
   `build_functions_model_v2` populates it.
3. `_label_pairs_for_mapping` returns `(coord, name, glyph)` triples. Built-ins
   fill `glyph` from the lookup tables (Phase-1 vocab), functions from
   `mm.hud_glyph`, everything else `glyph=""`.
4. `collect_mode_labels` value type becomes `(name, glyph)`; baked via `repr`
   into `mode_hud_labels` as a 2-tuple literal `('Loop Expand','arrow...')`
   (gen.py:261 already `repr`s the value — tuples serialize cleanly).
5. `_overlay_labels` (helpers.py:47) unpacks: `name, glyph = labels[key]` →
   `SlotPayload(name, 0, 0, 1, glyph=glyph)`.

## TDD order

1. **hud_protocol** (Python): round-trip test `encode_slot_payload` →
   `parse` with and without glyph; assert 7-field lines still parse (glyph="").
2. **WireProtocol** (Swift): parse test for 7- and 8-field SLOT/UPDATE.
3. **model_functions**: `@hud_name("N","g")`, `@hud_name("N")`, and
   `@hud_name("N", glyph="g")` all read correctly.
4. **hud_layout**: `collect_mode_labels` yields `(name, glyph)` for a function
   mapping with a glyph, `("...","")` without.
5. Implement each to green; then integration: regenerate `ck_grid`, deploy,
   confirm a `@hud_name(...,glyph)` function shows the icon in the button with
   the name below, and a bad glyph shows name-only.

## Rollout / scope

- **Phase 2a (this):** wire `glyph` field + `SlotPayload.glyph` + `@hud_name`
  two-arg + `ButtonSlotView` in-chrome render. Fully backward compatible (empty
  glyph everywhere ⇒ current behavior).
- **Phase 2b:** populate built-in nav/transport/pager glyphs from the vocabulary
  table above (each built-in button then shows icon-in-button + text name).
- Out of scope: icons on dial params (cutoff/resonance/etc. have no meaningful
  symbol — text stays); animating the active-state fill around the icon.

## Build / commit

- Run `./build.sh` before committing; report quality delta.
- Mention this plan (`hud-nav-transport-icons-plan`) in the commit message.
- Let the user redeploy so they can restart Ableton.
