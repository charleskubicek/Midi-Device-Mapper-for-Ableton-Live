# HUD Wire Protocol

The protocol between the generated Ableton control surface (Python, sender) and
the AbletonHUD macOS app (Swift, receiver).

- **Transport:** UDP, fire-and-forget, no reply channel
- **Address:** `127.0.0.1:5006` (loopback only)
- **Framing:** one message per UDP datagram, terminated with `\n`. Multiple
  messages may also arrive concatenated in a single datagram and are split on
  `\n`.
- **Encoding:** UTF-8
- **Field delimiter:** `|` (pipe)
- **Direction:** sender → receiver only. There is no protocol-level ack.

## Single source; composition happens upstream

The HUD has exactly **one** sender, so messages carry no source/group/order —
the wire is `VERB|<payload…>`. A standalone surface sends directly to the HUD.

To show **two** controllers side by side, the composition happens *upstream of
the HUD*, in the primary surface — not in the HUD app. The `lc_parks` compositor
(generated from a composition config, see `model_composition.py`) owns the
launch_control MIDI port and drives the entire HUD. The secondary (parks)
surface keeps resolving its own region but points its `HudClient` at the
compositor's **region port** instead of the HUD; the compositor's
`RegionListener` (`source_modules/region_listener.py` + `region_state.py`)
merges that region into one stream via `hud_layout.combine_layouts`: the
secondary's cells are tagged `section` 1 (and their slot indices bumped past the
primary's) so the HUD renders them as a self-contained block to the right of the
primary. A single stream goes to the HUD.

Because only one process talks to the HUD, the receiver is a simple single-state
machine — no per-source buffers, no active-group selection, no LAYOUT-once race.
The dismiss timer is global: any `COMMIT`/`UPDATE`/`PING` re-arms it; `HIDE`
dismisses the panel.

## Terminology

**Burst** — a contiguous sequence of messages framed by `DEVICE` … `COMMIT` that
together describe the full HUD state for a single device. A burst is the unit
of atomic update: the receiver buffers everything between `DEVICE` and `COMMIT`
in *pending* state and only swaps it into *published* state when `COMMIT`
arrives. Bursts are emitted on every device-focus change. Outside of a burst,
the sender uses `UPDATE` for single-slot live patches and `PING` for keepalive
— neither participates in burst framing.

Authoritative implementations:

- Sender: `source_modules/hud_protocol.py` (encode/decode + parse), `source_modules/hud_client.py` (UDP transport), `source_modules/helpers.py` `Remote` class (burst orchestration), `Helpers.refresh_hud_for_mode` (mode-change trigger)
- Receiver: `Sources/AbletonHUDCore/WireProtocol.swift` (parser), `Sources/AbletonHUDCore/DeviceState.swift` (state machine), `Sources/AbletonHUD/UDPListener.swift` (socket)

---

## Message catalog

There are nine message types.

### `LAYOUT`

Describes the physical grid: which cells exist, where they sit, whether each
cell is a bank of dials or a bank of buttons.

```
LAYOUT|<n>|<gr0>|<gc0>|<kind0>|<count0>|<start0>|<section0>|<gr1>|<gc1>|<kind1>|<count1>|<start1>|<section1>|...
```

| Field      | Type   | Meaning                                       |
|------------|--------|-----------------------------------------------|
| `n`        | int    | number of cells that follow                  |
| `gr`       | int    | grid row of this cell                         |
| `gc`       | int    | grid column of this cell                      |
| `kind`     | string | `dial` or `button`                            |
| `count`    | int    | number of slots in this cell                  |
| `start`    | int    | starting slot index for this cell             |
| `section`  | int    | independent-layout block id (see below)       |

`section` groups cells into independently-laid-out blocks. A standalone surface
emits everything as section `0`. The `lc_parks` compositor tags the secondary
controller's cells section `1`, and the HUD renders each section as its own
self-contained sub-grid placed side-by-side (secondary to the right of the
primary, with a divider) — each section's grid rows/cols are independent. Slot
`start` indices still live in **one flat** dial/button space across all sections
(the secondary's are bumped past the primary's counts), so sections only affect
*placement*, not slot indexing.

Example (one section-0 dial cell + one section-1 button cell):

```
LAYOUT|2|0|0|dial|8|0|0|2|0|button|4|0|1
```

- **Emitted:** at surface init by `Remote.init_layout()`, **and re-emitted at the
  head of every (non-suppressed) device burst** by `Remote.refresh_burst()`
  (just before `DEVICE`). The physical layout is fixed for the life of the
  surface, so the cells are identical each time; re-emitting exists purely so a
  HUD that started *after* the surface (and missed the one-shot init LAYOUT)
  still gets a grid — it makes HUD/Ableton startup order irrelevant.
- **Receiver effect:** stored in `pendingCells`; published to `hudCells` at the
  next `COMMIT`. `DEVICE` clears pending *slots* but not `pendingCells`, so a
  LAYOUT→DEVICE→SLOT…→COMMIT burst publishes the cells correctly.

### `DEVICE`

Burst start marker. Names the device that the following `SLOT` messages belong
to.

```
DEVICE|<name>
```

| Field   | Type   | Meaning                  |
|---------|--------|--------------------------|
| `name`  | string | device display name      |

- **Emitted:** first message in every device-focus burst (`helpers.py:334`).
- **Receiver effect:** clears `pendingDials` and `pendingButtons`, sets
  `pendingName`. Published state is not touched until `COMMIT`.

### `SLOT`

A single slot's data, sent inside a burst.

```
SLOT|<kind>|<index>|<name>|<value>|<min>|<max>
```

| Field    | Type   | Meaning                                   |
|----------|--------|-------------------------------------------|
| `kind`   | string | `dial` or `button`                        |
| `index`  | int    | slot index — see "Indexing" below         |
| `name`   | string | parameter / button label (may be empty)   |
| `value`  | float  | current value                             |
| `min`    | float  | minimum                                   |
| `max`    | float  | maximum                                   |

- **Emitted:** during a burst, one per parameter (dials) or one per cell
  (buttons — see indexing notes).
- **Receiver effect:** writes to `pendingDials[index]` or
  `pendingButtons[index]`. Not visible until `COMMIT`.

### `UPDATE`

Single-slot live update outside any burst. Same wire shape as `SLOT`, different
verb.

```
UPDATE|<kind>|<index>|<name>|<value>|<min>|<max>
```

- **Emitted:** when a parameter value changes after the initial burst, by
  `Remote.parameter_updated()` (`helpers.py:326-327`). Suppressed during a
  burst (see "Burst semantics" below).
- **Receiver effect:** applies immediately to published state if `index` is in
  bounds. No `COMMIT` required. Also fires the dismiss-timer reset.
- Today only `kind=dial` is emitted; the format leaves room for `kind=button`.

### `COMMIT`

End-of-burst marker. Atomic swap from pending to published state.

```
COMMIT|<count>
```

| Field    | Type | Meaning                                     |
|----------|------|---------------------------------------------|
| `count`  | int  | number of `SLOT` lines in the burst         |

- **Emitted:** last message of every device-focus burst (`helpers.py:364`).
- **Receiver effect:** computes total dial / button counts from `pendingCells`,
  builds slot arrays from the pending dicts (missing indices become empty
  slots), and publishes `dialSlots`, `buttonSlots`, `deviceName`, `hudCells`.
  Resets the dismiss timer.

### `PING`

Keepalive.

```
PING
```

- **Emitted:** after device parameter actions and switch / button actions, from
  generated surface code (templates dispatched via
  `ableton_control_surface_as_code/gen_code.py`).
- **Receiver effect:** resets the auto-dismiss timer. Does not change displayed
  state.

### `HIDE`

Explicit dismiss. Sent when the Live API shows the user has navigated away from
the focused device (opened the browser, switched Session ↔ Arrangement, left the
device chain).

```
HIDE
```

- **Emitted:** by `application.view` listeners in the generated surface
  (`main_component.py`: `_on_doc_view_changed`, `_on_browser_visibility_changed`,
  `_on_detail_changed`) via `HudClient.send_hide()`. Callbacks are directional —
  they only fire on the away-transition, never on selecting a device.
- **Receiver effect:** sets the **sticky** `dismissed` flag and hides the
  overlay. While `dismissed` is set, every show path is suppressed
  (`COMMIT`/`UPDATE`/`PING` and app-refocus) so routine traffic — e.g. an
  automated parameter emitting `UPDATE` during playback — cannot resurrect the
  HUD. The flag is cleared only by the next device burst (`DEVICE` or `COMMIT`),
  i.e. the user reselecting a device.

### `PAGE`

Page indicator for the parameter pager. Sent inside a burst, between `DEVICE`
and `SLOT` messages. Not counted in the `COMMIT|<count>` value — it is metadata,
not a slot.

```
PAGE|<enc_page>|<enc_total>|<btn_page>|<btn_total>
```

| Field        | Type | Meaning                                |
|--------------|------|----------------------------------------|
| `enc_page`   | int  | current encoder page number (1-based)  |
| `enc_total`  | int  | total encoder pages                    |
| `btn_page`   | int  | current button page number (1-based)   |
| `btn_total`  | int  | total button pages                     |

- **Emitted:** during `Remote.refresh_burst()`, immediately after `DEVICE`
  (`helpers.py:436`).
- **Receiver effect:** writes to `pendingEncoderPage`, `pendingEncoderTotal`,
  `pendingButtonPage`, `pendingButtonTotal`. Published to `encoderPage` and
  `pageTotal` on `COMMIT`. `pageTotal` is `max(encTotal, btnTotal)` — the HUD
  shows a single combined indicator (e.g. "1/3"). Only rendered when
  `pageTotal > 1`.
- When the encoder page count exceeds the button page count (e.g. 5 encoder
  pages but only 2 button pages), the button page stays at its last valid page.
  The HUD indicator tracks the encoder page over the shared maximum total.

### `PAGE`

Page indicator for the parameter pager. Sent inside a burst, between `DEVICE`
and `SLOT` messages. Not counted in the `COMMIT|<count>` value — it is metadata,
not a slot.

```
PAGE|<enc_page>|<enc_total>|<btn_page>|<btn_total>
```

| Field        | Type | Meaning                                |
|--------------|------|----------------------------------------|
| `enc_page`   | int  | current encoder page number (1-based)  |
| `enc_total`  | int  | total encoder pages                    |
| `btn_page`   | int  | current button page number (1-based)   |
| `btn_total`  | int  | total button pages                     |

- **Emitted:** during `Remote.refresh_burst()`, immediately after `DEVICE`
  (`helpers.py:436`).
- **Receiver effect:** writes to `pendingEncoderPage`, `pendingEncoderTotal`,
  `pendingButtonPage`, `pendingButtonTotal`. Published to `encoderPage` and
  `pageTotal` on `COMMIT`. `pageTotal` is `max(encTotal, btnTotal)` — the HUD
  shows a single combined indicator (e.g. "1/3"). Only rendered when
  `pageTotal > 1`.
- When the encoder page count exceeds the button page count (e.g. 5 encoder
  pages but only 2 button pages), the button page stays at its last valid page.
  The HUD indicator tracks the encoder page over the shared maximum total.

### `EVENT`

Show-info feedback. When the user enables show-info mode (the `showinfo`
update.py command), every **button** press the surface receives is explained on
the HUD at the moment of the press. The HUD renders the text transiently and
fades it. Orthogonal to bursts — `EVENT` carries no slot data and never
participates in burst framing.

```
EVENT|<kind>|<wire_idx>|<text...>
```

| Field      | Type   | Meaning                                                   |
|------------|--------|-----------------------------------------------------------|
| `kind`     | string | `button` / `dial`, or `info` when not tied to a HUD cell  |
| `wire_idx` | int    | HUD button-array index, or `-1` when none                 |
| `text`     | string | human-readable explanation; **may contain `\|`** — it is always the final field, so parsers must join `fields[3:]` |

- **Emitted:** from the generated button listeners (the single `button_event`
  chokepoint, `gen_code.py`) while show-info is enabled, via
  `HudClient.send_event()`. Continuous knobs/sliders never emit it.
- **Receiver effect:** renders `text` as a transient footer line (and, when
  `wire_idx >= 0`, a brief border pulse on that cell), auto-fading after ~2s.
  Does not alter published slot state.
- **Text format:** the sender emits e.g. `row-3:5 ▼127 → acted` on press and
  `… ▲0 ignored (press-only)` on release; an on-value ≠ 127 is annotated.

> **Status.** The protocol message, sender emission, and the Swift parser case
> are implemented + tested. The HUD *rendering* (footer fade + cell pulse) and
> moving the enable toggle into HUD chrome (which needs a HUD→surface back
> channel) are the remaining follow-up; today the toggle is the `showinfo`
> update.py command. See momentary-vs-toggle-made-explicit-plan, item #7.

---

## Indexing conventions

**Dial and button slots index differently.** This is easy to misread from the
wire alone.

### Dials

Wire `index` is `live_param_no - 1`. Live parameter 0 is "Device On" and is
intentionally skipped on the HUD, so wire dial index `0` corresponds to Live
parameter `1`.

This applies to both `SLOT|dial` (`helpers.py:341`) and `UPDATE|dial`
(`helpers.py:327`).

### Buttons

Wire `index` is **layout-cell-relative**: `start + i` where `start` is the
button cell's `start` from `LAYOUT` and `i` is the position within the cell
(`helpers.py:352`). It is **not** offset by 1 the way dials are.

---

## Burst semantics

A device-focus change produces a *burst* of messages framed by `DEVICE` and
`COMMIT`. While a burst is active, the sender holds an `_in_burst` flag
(`helpers.py:313, 333, 365`).

- During the burst, calls to `parameter_updated()` send their OSC update but
  **suppress** the corresponding `UPDATE|dial` message — the burst's own
  `SLOT|dial` line already carries the same data.
- This avoids the receiver applying a stream of partial `UPDATE`s before the
  atomic `COMMIT`.

The receiver enforces the same separation structurally: `SLOT` writes only to
the pending dicts; `UPDATE` writes only to the published arrays.

---

## Slot emission: dense and symmetric

The sender emits one `SLOT` per cell position for **both** `dial` and
`button` cells, whether or not the position is bound to a real parameter
in the active mode. The wire is self-describing per burst — the receiver
no longer depends on `LAYOUT` being correct to size a burst's slot
arrays.

### Empty-slot sentinel

Positions that aren't bound to a real parameter carry the sentinel:

```
SLOT|<kind>|<idx>||0|0|1
```

(empty name, value `0`, min `0`, max `1`.) The single source of truth is
`hud_protocol.EMPTY_SLOT` on the sender, mirrored by tests on both sides
(`tests/test_hud_protocol.py::test_slot_empty_sentinel`,
`WireProtocolTests::test_empty_slot_sentinel_parses_as_slot`).

The convention is: **empty name = empty slot**. A legitimately unnamed
mapped slot is not a case that occurs in practice (Live parameters have
names; mappings carry aliases). If that ever changes, introduce a
distinct verb rather than overloading the sentinel.

### Mode-aware burst content

Burst content is assembled per active mode, not just per device:

- **Device-bound cells** (slots whose mapping is `type: device` in the
  current mode) are populated from the focused device's parameters by
  `Helpers.update_remote_parameters`.
- **Non-device-bound cells** (mixer / functions / track-nav / device-nav /
  transport / parameter-pager) are overlaid with static labels from
  `mode_hud_labels[mode_name]`, generated at codegen time and threaded
  through `Helpers.__init__`.
- Cells that aren't bound in the current mode emit the empty-slot
  sentinel.

A burst fires on:

- **Device-focus change** — `selected_device_changed` →
  `update_remote_parameters` → `Remote.device_update` (overlays the
  current mode's labels onto the device payloads).
- **Mode change** — `goto_mode` →
  `Helpers.refresh_hud_for_mode(name, device)` → re-emits a burst with the
  new overlay so the HUD reflects the new bindings immediately.

> **Known gap.** Non-device cells currently carry static labels with
> placeholder values (`value=0, min=0, max=1`). Live values for
> mixer/transport/etc. are not yet pushed. See `known_issues.md` ("HUD:
> non-device slots show labels but not live values") for the deferred
> follow-up.

---

## Sequence diagrams

### Surface startup (one-time)

```
sender                                       receiver
  |                                            |
  | LAYOUT|2|0|0|dial|8|0|0|2|0|button|4|0|1 |
  |------------------------------------------->|
  |                                  pendingCells = [...]
  |                                            |
```

`LAYOUT` is sent once, immediately after `Remote` is constructed. The receiver
does **not** publish `hudCells` until the first `COMMIT`.

### Device focus change (burst)

```
sender                                       receiver
  |                                            |
  | _in_burst = True                           |
  |                                            |
| DEVICE|EQ Eight                       |
  |------------------------------------------->|
  |                            pendingDials = {}, pendingButtons = {}
  |                            pendingName = "EQ Eight"
  |                                            |
  | PAGE|1|3|1|2                               |
  |------------------------------------------->|
  |                            pendingEncoderPage = 1, pendingEncoderTotal = 3
  |                            pendingButtonPage = 1, pendingButtonTotal = 2
  |                                            |
  | SLOT|dial|0|Frequency|440.0|20.0|20000.0 |
  |------------------------------------------->|
  | SLOT|dial|1|Resonance|0.7|0.0|1.0     |
  |------------------------------------------->|
  | ... (one SLOT|dial per real parameter)     |
  |------------------------------------------->|
  |                                            |
  | SLOT|button|0|Type|1.0|0.0|2.0        |
  |------------------------------------------->|
  | SLOT|button|1||0|0|1                  |  (empty-slot sentinel)
  |------------------------------------------->|
  | ... (one SLOT|button per button cell slot) |
  |------------------------------------------->|
  |                                            |
  | COMMIT|<count>                        |
  |------------------------------------------->|
|                          atomic swap → published state
  |                          dialSlots / buttonSlots / deviceName / hudCells
  |                          encoderPage / pageTotal
  |                          dismiss timer reset
  |                                            |
  | _in_burst = False                          |
  |                                            |
```

While `_in_burst` is true, any `parameter_updated()` calls fire OSC but skip
`UPDATE|dial` — the burst's own `SLOT|dial` carries the value.

### Live knob turn (after burst)

```
sender                                       receiver
  |                                            |
  | (user turns a mapped knob)                 |
  |                                            |
  | UPDATE|dial|2|Resonance|0.81|0.0|1.0  |
  |------------------------------------------->|
  |                          dialSlots[2] = ... (immediate)
  |                          dismiss timer reset
  |                                            |
  | (user presses a switch button)             |
  |                                            |
  | PING|main                                  |
  |------------------------------------------->|
  |                          dismiss timer reset
  |                                            |
```

No `COMMIT` is required for `UPDATE`. `PING` keeps the HUD visible without
changing what is displayed.

---

## Receiver state model

The receiver keeps two layers:

- **Pending** (`pendingDials`, `pendingButtons`, `pendingName`,
  `pendingCells`, `pendingEncoderPage`, `pendingEncoderTotal`,
  `pendingButtonPage`, `pendingButtonTotal`) — written by `LAYOUT`, `DEVICE`,
  `SLOT`, `PAGE`.
- **Published** (`dialSlots`, `buttonSlots`, `deviceName`, `hudCells`,
  `encoderPage`, `pageTotal`) —
  observed by the SwiftUI view layer. Written only by `COMMIT` (atomic swap)
  or `UPDATE` (single-slot patch).

`COMMIT` derives the array lengths for `dialSlots` / `buttonSlots` from
`pendingCells`, then fills each index from the pending dicts. With
dense-symmetric emission, every wire index in a burst is populated by a
`SLOT` message (real or empty-sentinel), so missing indices in the
pending dict are an error condition rather than the normal case.

The dismiss timer is reset on `COMMIT`, `UPDATE`, and `PING`. If none of those
arrive within the dismiss window, the HUD hides itself.

`HIDE` is an out-of-band dismiss orthogonal to the timer: it sets the sticky
`dismissed` flag (in `DeviceState`) and hides immediately. While set, the overlay
manager gates every show path on `!dismissed`, so the HUD stays hidden through
`UPDATE`/`PING`/refocus until a `DEVICE`/`COMMIT` burst clears the flag.

---

## Capturing a protocol trace (debugging reliability)

When the HUD misbehaves (flashes/hides on device move, drifts out of step with
shift), turn on gated `fine` tracing on **both** sides and read the two logs
together. Tracing is off by default and adds no wire traffic — the two switches
are independent (see `ai-coding/plans/hud-protocol-instrumentation-plan.md`).

- **Surface (Python sender).** `python update.py hudtrace` toggles
  `manager.fine`. While on, `Helpers.fine` emits `[hudtrace]`-tagged lines for
  the nav / app-view-listener / mode / visibility path. Read with
  `./bin/tail_logs.sh`. Key tags: `[funnel]` (the `selected_device_changed`
  guard — *the* Bug-1 line), `[vis] decide` (event → dismissed flip → decision),
  `[nav]`, `[mode]`, `[appview]`, `[burst]`, `[focus]`.
- **HUD (Swift receiver).** Toggle at runtime with a file sentinel —
  `touch /tmp/ableton_hud_fine` on, `rm /tmp/ableton_hud_fine` off. The recv loop
  re-reads it each datagram, so it takes effect within one message and needs no
  relaunch. (This is launch-agnostic: the HUD is started via `open
  AbletonHUD.app`, which inherits neither the shell environment nor
  `UserDefaults.standard`; `HUD_FINE=1` only works under `swift run`.) While on,
  `DeviceState.apply` logs every wire message it processes — especially the
  `dismissed` / `isShiftMode` flips on `DEVICE` / `COMMIT` / `HIDE` / `MODE` —
  plus the overlay show/hide/timer path, to `/tmp/ableton_hud_debug.log`.

Both sinks are wall-clock timestamped on the same host, so the receiver trace
interleaves with the sender trace for coarse cross-side alignment. **Within each
side, log order is execution order** (single-threaded) — that is the reliable
ordering signal: e.g. a synchronous `appointed_device` fire shows up as
`[listener] on_device_selected` landing *between* a nav method's `[nav] … enter`
and `[nav] … post-scroll` lines.

---

## Cross-references

| Concern                  | File                                                          |
|--------------------------|---------------------------------------------------------------|
| Wire constructors        | `source_modules/hud_client.py`                                |
| Send-site orchestration  | `source_modules/helpers.py` (`Remote` class)                  |
| `PING` emission          | `ableton_control_surface_as_code/gen_code.py` + templates     |
| `PAGE` emission          | `source_modules/helpers.py` (`Remote.refresh_burst`)          |
| Wire parser              | `Sources/AbletonHUDCore/WireProtocol.swift`                   |
| Receiver state machine   | `Sources/AbletonHUDCore/DeviceState.swift`                    |
| UDP socket               | `Sources/AbletonHUD/UDPListener.swift`                        |
| Burst-suppression tests  | `tests/test_helpers.py`                                       |
| Parser tests             | `Tests/WireProtocolTests/WireProtocolTests.swift`             |
