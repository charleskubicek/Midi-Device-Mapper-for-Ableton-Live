# HUD Protocol Hardening + Mode-Aware Bursts

## Context

`hud_protocol.md` flags the button-slot emission rules as unstable and the
suspected source of a rendering bug. Investigating that section surfaced two
deeper gaps that share the same root cause — the sender doesn't have a
unified, per-cell view of "what is bound right now":

1. **Wire-layer asymmetry.** `SLOT|dial` is sparse (sender only emits real
   parameters; receiver fills missing indices from `pendingCells`).
   `SLOT|button` is dense (sender fills empties with `||0|0|1`). The receiver
   thus depends on `LAYOUT` being correct and timely for buttons but not for
   dials. Tests pin behavior, not bytes-on-wire.
2. **Content gap.** `Remote.device_update()` only feeds device parameters and
   a narrow `switch_entries` list. Mixer / transport / functions /
   track-nav / device-nav / parameter-pager mappings occupy physical cells
   but never push state to the HUD. In shift mode on the LC XL, dials are
   bound to mixer volume/pan/sends — the HUD still shows the previous
   device's parameters.
3. **Trigger gap.** `goto_mode()`
   (`templates/surface_name/modules/main_component.py:127-141`) tears down
   and re-installs listeners but never triggers a HUD refresh. Mode switches
   are invisible to the HUD.

Goal: every physical control on the surface is accounted for in the HUD —
even when empty, even when bound to a non-device mapping, even after a mode
switch — and the wire format is pinned by tests on both sides.

## Decisions

- **Empty slots: dense both, sender-fills.** Sender emits one `SLOT` per cell
  position for *both* dials and buttons. Empty slots use the existing
  `||0|0|1` sentinel (empty name, range 0..1, value 0). Wire becomes
  self-describing per burst; receiver no longer depends on `LAYOUT` for slot
  array sizing within a burst. The legitimately-unnamed-mapped-slot edge
  case is accepted as not occurring in practice (no Live param has empty
  name; no mapping leaves alias unset for an unnamed param).
- **Extract `source_modules/hud_protocol.py`.** Pure encode/decode + a small
  parser. `hud_client.py` becomes a thin UDP transport that calls into it.
  Other senders (`gen.py` debug pretty-printer, `bin/hud_sim.py`) route
  through the same module.
- **Generalize burst content.** `Remote.device_update()` is split into a
  generic `Remote.refresh_burst(device_name, cells)` that takes a per-cell
  payload list (label + value/min/max for dials, label + state for
  buttons), regardless of mapping type. Device-specific assembly is moved
  out of `Remote` and into the call sites that already know about the
  active mode.
- **Burst on mode change.** `goto_mode()` calls `refresh_burst()` after
  re-installing listeners. The mode's bindings are walked to assemble the
  cell payload.
- **Dense `LAYOUT`.** Today `gen.py` builds `hud_cell_map` from controller
  groups then overrides with device cells only. Extend the override step to
  cover *all* mapping types so every physical cell is in `LAYOUT` with the
  correct `start` (no `-1` placeholders for cells that are actually bound
  in some mode).

## Implementation

### Phase 1 — Protocol extraction + dense symmetric wire

**New file: `source_modules/hud_protocol.py`**

- Pure functions: `encode_layout(cells) -> str`, `encode_device(name)`,
  `encode_slot(kind, index, name, value, vmin, vmax)`,
  `encode_update(...)`, `encode_commit(count)`, `encode_ping()`.
- A `parse(line) -> Message` returning a tagged dataclass union
  (`LayoutMsg`, `DeviceMsg`, `SlotMsg`, `UpdateMsg`, `CommitMsg`, `PingMsg`,
  `UnknownMsg`). Mirrors the Swift `WireMessage` enum.
- A constant `EMPTY_SLOT = SlotPayload(name='', value=0, vmin=0, vmax=1)`
  used by senders so the sentinel lives in one place.

**Modify: `source_modules/hud_client.py`**

- `HudClient` and `NullHudClient` keep the same public surface
  (`send_layout`, `send_device`, `send_slot`, `send_update`, `commit`,
  `send_ping`) but bodies delegate to `hud_protocol.encode_*`. `_send`
  stays.

**Modify: `source_modules/helpers.py:329-365` (`Remote.device_update`)**

- Split into `refresh_burst(device_name, dial_cells, button_cells)` where
  each cell is a list-of-slots (dense). Empty slots use
  `hud_protocol.EMPTY_SLOT`.
- Inside the burst, emit `SLOT|dial` for every dial position
  (sender-fills), not just `i > 0`. The "skip Device On" rule moves into
  the caller that builds `dial_cells` for device mappings.
- `device_update` becomes a thin wrapper that builds the dense cell lists
  from `real_parameters` + `switch_entries` and delegates to
  `refresh_burst`. Behavior preserved for current call sites.

**Modify: redirect ad-hoc senders**

- `bin/hud_sim.py` and `ableton_control_surface_as_code/gen.py`
  `print_hud_layout` and the generated surface file's raw `DEVICE|...`
  print all import and use `hud_protocol.encode_*`.

### Phase 2 — Mode-aware bursts

**Codegen: `gen.py` + `gen_code.py`**

- Extend `hud_cell_map` construction in `gen.py:140-156` so non-device
  mapping types contribute to `hud_layout`. Each mapping type's
  `*WithMidi` model already knows its physical cells; expose
  `hud_cells` on every mapping type that doesn't already (mixer,
  transport, track-nav, device-nav, functions, parameter-pager).
- For each mode, generate a `mode_{name}_hud_cells()` function that
  returns the dense per-cell payload for that mode's bindings (labels +
  current values for mixer/functions/etc.; for the device cells, defer to
  the existing device-parameter resolution).
- The generated mode setup functions register their cell-payload builder
  alongside the listener-add function in `self._modes[name]`.

**Runtime: `templates/surface_name/modules/main_component.py:127-141`
(`goto_mode`)**

- After `add_listeners_fn()`, call
  `self._helpers.refresh_hud_for_mode(next_mode_name)`. New `Helpers`
  method assembles the dense cell payload by calling the registered
  builder, picks up the currently focused device name, and invokes
  `Remote.refresh_burst()`.

**Runtime: device-focus path stays separate.** When the selected device
changes (`selected_device_changed`), the existing
`update_remote_parameters` path still fires — but it now also walks the
*current mode's* non-device cells so the burst is complete, not just
device parameters.

### Phase 3 — Tests

**Python: new `tests/test_hud_protocol.py`** (wire-byte tests)

- Roundtrip: every `encode_*` parses back to an equal message.
- Pin exact bytes for each message type incl. the `EMPTY_SLOT` sentinel.
- Multi-message datagram split on `\n`.
- Malformed: bad int/float, wrong field count, unknown verb → `UnknownMsg`.

**Python: extend `tests/test_helpers.py`**

- `Remote.refresh_burst()` emits dense `SLOT|dial` for every position.
- Mode-change path emits a burst with non-device cells populated (mocked
  `Helpers` exposing a fake mode with mixer/functions cells).
- Existing `TestRemoteBurstSuppression` and `TestHudLayoutSeparation` are
  ported to the new entrypoint.

**Swift: extend `Tests/WireProtocolTests/WireProtocolTests.swift`**
(repo at `/Users/ck/current/ableton_hud`)

- Pin the dense-dial wire shape: a burst with empty `SLOT|dial` entries
  parses and produces the expected sparse-after-COMMIT result.
- A burst that contains *only* `SLOT|dial` (no buttons) and a layout with
  no button cell publishes empty `buttonSlots`.
- Confirm `SLOT|button|...||0|0|1` is parsed as an empty-name slot, not
  rejected.

## Critical files

- `source_modules/hud_protocol.py` *(new)*
- `source_modules/hud_client.py`
- `source_modules/helpers.py` (`Remote`, `Helpers`)
- `ableton_control_surface_as_code/gen.py` (`hud_cell_map`, mode wiring)
- `ableton_control_surface_as_code/gen_code.py` (per-mapping-type
  `hud_cells` exposure, mode HUD-builder generation)
- `templates/surface_name/modules/main_component.py` (`goto_mode`)
- `tests/test_hud_protocol.py` *(new)*, `tests/test_helpers.py`
- `bin/hud_sim.py` (route through `hud_protocol`)
- *(separate repo)* `Tests/WireProtocolTests/WireProtocolTests.swift`
- `hud_protocol.md` — replace the UNSTABLE section with the new contract;
  document `EMPTY_SLOT` sentinel and dense-symmetric rule.

## Verification

1. `poetry run pytest tests/test_hud_protocol.py tests/test_helpers.py` —
   green.
2. `poetry run python ableton_control_surface_as_code/gen.py
   live_surfaces/launch_control/ck_launch_control_16.nt` — generates
   without error.
3. In the generated surface dir, `./deploy.sh`, restart Ableton, tail
   logs (`./bin/tail_logs.sh`).
4. With the HUD app running, focus a device → confirm dials populate
   (including empty slots for unmapped positions) and buttons render.
5. Press the mode button to enter shift mode → HUD updates within one
   burst to show mixer volume/pan/sends labels and current values, and
   functions row labels. Press again → returns to main mode bindings.
6. Run `bin/hud_sim.py` to send a synthetic burst against a live HUD
   and confirm the dense-symmetric sentinel renders as an empty slot
   (not a "0" labeled cell).
7. In `/Users/ck/current/ableton_hud`, `swift test` — green.

## Open scope notes

- `DEVICE|<name>` header semantics in non-device-dominant modes (e.g.,
  shift mode where dials are mixer-bound) — keep current behavior (focused
  Live device name) for now. Renaming the header to a mode-aware label is a
  wire change and out of scope.
- `LAYOUT` is still sent once at init. With dense-symmetric slots the
  receiver no longer needs `pendingCells` to size a burst, so re-sending
  `LAYOUT` on layout change isn't required by this plan; revisit only if a
  controller swap is added later.
