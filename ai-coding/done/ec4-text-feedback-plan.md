# EC4 Text Feedback — Generic Feedback-Sink Framework

## Goal

Let the generated surface push **text to output targets on certain runtime
changes**. First concrete use: write parameter names to the Faderfox EC4's 16
readouts (4 chars/cell, via SysEx). Built as a **generic hook framework** (user
decision), with the EC4 as its first non-HUD sink.

The three triggers the user named are **not new mechanisms** — they map 1:1 onto
notification points that already drive the HUD:

| Trigger                 | Existing call site                                                            |
|-------------------------|------------------------------------------------------------------------------|
| selected-device change  | `on_device_selected` → `Helpers.selected_device_changed` → `Remote.device_update` |
| mode change             | `goto_mode` → `refresh_hud_for_mode` + `hud_client.send_mode`                 |
| button press            | pager/switch path that re-maps the 16 knobs → already triggers a HUD refresh  |

So this is: **formalise those call sites as named events, and make the HUD one
of several pluggable sinks.** EC4 becomes a second sink.

## Core design

### The indexing trap (this shapes everything)

The HUD addresses cells by its own **wire-index** (`hud_cells`, dial-vs-button
split, `_build_dial_payloads`). The EC4 addresses cells by **encoder_id = the
knob's CC number** (`ec4.nt` assigns CC 0–15 to the 16 knobs;
`MidiCoords.number`). These do **not** line up.

⇒ The event payload must be **coordinate-addressed and semantic**, never
HUD-wire-indexed. Each sink translates the snapshot into its own wire format:
- HUD sink → `hud_cells` wire index (existing builders)
- EC4 sink → `encoder_id = MidiCoords.number`, truncate to 4 chars, build SysEx, `send_midi`

### Events (the fixed, small "certain changes" set)

Deliberately a closed enum of lifecycle events — not a user-scriptable bus.

1. `on_device(snapshot)` — selected device changed.
2. `on_controls_remapped(snapshot)` — pager/switch changed which params the
   encoders address (the "button press" case; same payload shape as `on_device`).
3. `on_mode(mode_info)` — mode changed (name, `is_shift`, static mode labels).
4. `on_param_update(slot)` — single live value change (keeps HUD's UPDATE path).
5. `on_hide()` — dismiss (HUD uses it; EC4 may clear or ignore).

### Neutral payload types (new, in a shared runtime module)

```python
@dataclass
class SlotInfo:
    coord: MidiCoords      # carries channel/number/type — the source of truth
    label: str
    value: float
    vmin: float
    vmax: float
    kind: str              # 'dial' | 'button'

@dataclass
class Snapshot:
    device_name: str
    slots: list[SlotInfo]
    page_info: tuple | None
```

`Remote` builds a `Snapshot` once at each event and fans it out. HUD sink and
EC4 sink each consume the same `Snapshot`, addressing it their own way.

### Sink protocol

```python
class FeedbackSink:            # duck-typed; Null* variants no-op everything
    def on_device(self, snap): ...
    def on_controls_remapped(self, snap): ...
    def on_mode(self, mode): ...
    def on_param_update(self, slot): ...
    def on_hide(self): ...
```

- `HudClient` is refactored to satisfy this (or wrapped by a thin
  `HudSink` adapter that calls today's `send_device/send_slot/commit`).
- `Ec4Client` is the new sink.
- `Remote._hud_client` → `Remote._sinks: list[FeedbackSink]`. Burst suppression
  (`_in_burst`) stays in `Remote` and gates whether `on_param_update` fans out,
  so HUD behaviour is unchanged.

## Config model (`model_v2.py`)

New top-level `feedback:` list, discriminated on `type`:

```nestedtext
feedback:
    -
        type: hud
        mode: device_only
    -
        type: ec4_text
```

- New pydantic models: `HudSinkDef`, `Ec4TextSinkDef`, union `FeedbackSinkDef`.
- `RootV2.feedback: list[FeedbackSinkDef]`.
- **Back-compat:** existing `hud: HudMode` still works. If `feedback:` is absent,
  synthesise `[HudSinkDef(mode=self.hud)]`. If present, it is authoritative.

## gen.py wiring

Today: `hud_client_class = 'NullHudClient' if hud_mode == Off else 'HudClient'`
and a single template var.

New: emit a **constructed sink list** template var, e.g.
```python
self._sinks = [
    HudClient(),                                   # or NullHudClient()
    Ec4Client(self.manager, encoder_id_by_coord=$ec4_encoder_map,
              setup_id=0, group_id=0),             # or NullEc4Client()
]
```
- Build `$ec4_encoder_map` from the controller model (coord → CC number).
- `main_component.py` passes `self._sinks` into `Remote(...)` instead of one client.

## Validated against Ableton's own driver

`/.../MIDI Remote Scripts/Faderfox_Universal_2/` (`consts.py`,
`faderfox_display_element.py`, `faderfox_parameter_display.py`) confirms the
decode below **byte-for-byte**. Reuse from it:
- the OLED **char table** (`CHARS`) + `translate_string` (collapse whitespace,
  unknown char → 0x1F) — do NOT use raw `ord()`.
- main control-name display is sent as **one full 64-char message** every refresh
  (header at offset 0, 16 × 4-char segments) — matches our one-message plan.
- blank cell == `-` (0x2D); `CLEAR_MAIN_DISPLAY` = 64 dashes. Confirms the
  `----` overwrite rule from the hardware side; our reset buffer is `'-'*64`.
- **total display** (type 3, `0x4E 0x22 0x13`, show `0x14` / hide `0x15`): 4 lines
  × 20 chars — the place to render **device name + mode name** (mode-change trigger).
- send path for our v1 surface: `self.manager._send_midi(tuple(payload))`
  (their v2 element uses `ControlElement.send_midi`).
- their template gates writes to `DEVICE_DISPLAY_SETUPS = [12,13,14,15]` — a
  template convention, not a protocol requirement. Our prerequisite is only that
  the active EC4 setup/group has the 16 encoder names = `----`.

## EC4 SysEx protocol (decoded from manual — supersedes the "good authority" snippet)

The original snippet (`HEADER + (CMD, setup_id, group_id, encoder_id) + ascii + END`)
is **wrong**. Real Faderfox format is **nibble-framed**: every logical byte `V`
becomes a 3-byte group `[cmd, 0x20|(V>>4), 0x10|(V&0x0F)]`.

`set encoder display` (display type 0 = control names):

```
F0 00 00 00                       # sysex start + 3-byte inventor id
4E 2C 1B                          # APP_FUNC, data 0xCB = device-id (0xC0 | 11), EC4 = 11
4E 22 10                          # APP_FUNC, data 0x20 = APP_FUNC_DISP_CTRL (control names)
4A 2<ah> 1<al>                    # PAGE_NUM_L, data = start address (0..63)
<per char>: 4D 2<vh> 1<vl>        # PAGE_DATA, data = char code
F7
```

- **Address = (control − 1) × 4.** 16 controls × 4 chars = addresses 0..63.
- **Send all 16 in ONE message:** address 0 + 64 chars → ~206 SysEx bytes, one
  handshake. Far better than 16 separate commands.
- **Charset only:** `0-9 A-Z a-z space . / -` (codes 48-57,65-90,97-122,32,46,47,45).
  Sanitise labels to these, then truncate/pad to 4.

```python
# header bytes confirmed against Faderfox_Universal_2/consts.py
SYSEX_START          = (0xF0, 0, 0, 0)
FADERFOX_EC4_DEV_ID  = (0x4E, 0x2C, 0x1B)   # device-id 0xCB (EC4 = 11)
SET_TEXT_MSG_HEADER  = (0x4E, 0x22, 0x10)   # display type 0 = control names
SYSEX_END            = (0xF7,)
CHARS = { ... }                              # copy OLED table from consts.py
def translate_string(s): ...                 # copy from consts.py

def _data(v): return [0x4D, 0x20 | (v >> 4), 0x10 | (v & 0x0F)]

class Ec4Client:
    def __init__(self, manager, cell_by_coord):  # cell_by_coord: ch_num -> control index 0..15
        self.manager = manager
        self.cell_by_coord = cell_by_coord
    def on_device(self, snap):            self._render(snap)
    def on_controls_remapped(self, snap): self._render(snap)
    def _render(self, snap):
        # one full 64-char message (16 cells x 4), like Ableton's driver.
        # '-' fills unset cells (the overwriteable/blank state).
        buf = ['-'] * 64
        for s in snap.slots:
            cell = self.cell_by_coord.get(s.coord.ch_num())
            if cell is None: continue
            for i, ch in enumerate(_fit4(s.label)):   # _fit4: translate+pad/truncate to 4
                buf[cell * 4 + i] = ch
        codes = [ord(c) for c in translate_string(''.join(buf))]
        payload = list(SYSEX_START) + list(FADERFOX_EC4_DEV_ID) \
                  + list(SET_TEXT_MSG_HEADER) \
                  + [0x4A, 0x20, 0x10] \              # address 0
                  + [b for v in codes for b in _data(v)] + list(SYSEX_END)
        self.manager._send_midi(tuple(payload))
class NullEc4Client: ...  # all methods no-op
```

`cell_by_coord` (ch_num → control index 0..15) is computed at generation time
from the controller model (`ec4.nt` row/col → physical control number).
Optional: a parallel total-display path renders device + mode name (type 3).

## Hard prerequisites (hardware / setup — not code)

- **`----` overwrite rule:** `!!! display overwrite only for names with content '----' !!!`
  The live display-write is IGNORED unless that encoder's name in the active EC4
  setup/group is literally `----`. ⇒ the EC4 setup must have all 16 encoder names
  pre-set to `----`, or nothing shows. Document this; possibly ship a setup dump.
- **Handshake:** EC4 acks each command (`F0 00 00 00 4E 2C 1B F7`); manual says
  wait before next. We can't block in `send_midi` → one-message-per-refresh,
  fire-and-forget. Verify no dropped/garbled writes under rapid device switching.

## OPEN — confirm before/while implementing

- **control-number ↔ CC mapping:** does `ec4.nt`'s physical row/col order match the
  EC4's internal control numbering (control 1 = top-left … 16 = bottom-right)?
  This decides the generated `addr_by_coord`; it's a gen-time constant we can fix.
- **4-char rule:** plain truncate (`Frequency`→`Freq`) vs. smarter abbreviation.
- **Scope of labels:** knob params only, or also mode name / function buttons on
  the **total display** (type 3 overlay — reference: `FaderfoxGlobalDisplay` /
  `get_display_msg`)?
- **Send path:** RESOLVED — `self.manager._send_midi(tuple)` (v1 `_Framework`
  ControlSurface). Still verify the EC4 is enabled as a MIDI **output** in Live prefs.

## STATUS — implemented (2026-06-04)

Steps 1–5 below are done and green (203 tests pass; the only failure,
`test_custom_mappings.py`, is a pre-existing collection error unrelated to this work):

- `source_modules/ec4_client.py` — `Ec4Client` / `NullEc4Client` + OLED `CHARS`
  table & `translate_string` copied from the stock driver. Golden-vector test
  (`Reso`→control 16) passes byte-for-byte (`tests/test_ec4_client.py`).
- `Remote` (`helpers.py`) — `feedback_sinks` list, fanned out in `refresh_burst`
  (`tests/test_helpers.py::TestFeedbackSinkFanout`).
- `model_v2.py` — `FeedbackSinkDef` / `FeedbackSinkType` + `feedback:` list on
  `RootV2` (`tests/test_feedback_config.py`).
- `gen.py` — renders `$feedback_sinks` ctor list; `main_component.py` template
  builds `self._feedback_sinks` and passes them to `Remote`.
- `live_surfaces/ec4/ck_ec4.nt` — enabled via `feedback: [type: ec4_text]`.

**Key simplification found during impl:** dial `wire_idx` is already the EC4 cell
0..15 (dials are allocated row-major), so the sink reuses the HUD's `dial_payloads`
directly — no coordinate map needed. `addr = wire_idx * 4`.

**Deferred / not yet done:**
- HUD itself is NOT migrated onto the sink list (kept on its dedicated client to
  avoid regression). The framework is generic; HUD migration is future work.
- Mode/device name on the EC4 **total display** (type 3) — not implemented.
- EC4 clear on HUD-hide (browser/nav-away) — `on_hide` exists on the sink but
  `main_component` calls `self._hud_client.send_hide()` directly, not via Remote,
  so the EC4 isn't cleared on dismiss yet.
- **Send path CONFIRMED:** stock `FaderfoxSurface(ControlSurface)` — same
  `_Framework.ControlSurface` base our surface uses — calls
  `self._send_midi((0xf0,…,0xf7))` with a flat byte tuple. `manager._send_midi`
  is correct. An integration test (`TestEc4ClientThroughRemote`) drives a real
  `Ec4Client` through `Remote` and asserts the emitted bytes.
- **Hardware-side only:** confirm the EC4 is enabled as a MIDI **output** in Live
  prefs, and the EC4 setup/group has all 16 encoder names = `----`.

## Build order (TDD per CLAUDE.md)

1. Config model: parse `feedback:` list + back-compat synthesis. Failing tests
   in `tests/test_*model*` / `test_gen.py` first.
2. `FeedbackSink` protocol + `Snapshot`; refactor `Remote` to fan out to a list;
   HUD as first sink. Existing HUD tests must stay green (behaviour unchanged).
3. `Ec4Client` against a fake `send_midi` capture; unit-test exact SysEx bytes
   for a known label + encoder_id (once constants are known).
4. `gen.py` builds the sink-list template var + `ec4_encoder_map`.
5. Integration: generate the `ck_ec4` surface; assert the generated
   `main_component.py` instantiates both sinks and wires them into `Remote`.
