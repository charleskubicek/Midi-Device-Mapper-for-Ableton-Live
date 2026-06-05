# Plan: `is_enabled` indicator in HUD (grey arc for disabled encoders)

## Problem

Ableton devices have parameters that become enabled/disabled conditionally based on
other parameter values (e.g. turning Corpus "off" disables tone-shaping encoders).
The HUD has no way to show this — encoders always render with a cyan arc even when
the parameter is inactive.

## Design Decision

A declarative JSON field (`controls_enabled_of`) on button entries in
`custom_device_mappings.json` specifies which encoder parameters a given button
controls the enabled state of. When that button is pressed, the runtime re-reads
`is_enabled` on the dependent parameters and sends UPDATEs. This avoids:
- Listening for state changes on all mapped parameters (no `add_state_listener` needed)
- Sending UPDATEs on every encoder turn (only the controlling button triggers them)
- Global traffic amplification (bounded to N dependent encoders per press)

The `enabled` field on the wire is read at three points, all piggybacked on
existing traffic:
1. **Burst** (device focus / mode / page change) — already iterates all params
2. **UPDATE** (knob turn) — reads `is_enabled` for the turned parameter only
3. **Dependent UPDATEs** — only when a button with `controls_enabled_of` is pressed

## Wire Format Change

SLOT and UPDATE get a 7th field `enabled` (0 or 1):

```
SLOT|dial|0|Freq|440.0|20.0|20000.0|1
UPDATE|button|2|On/Off|0.0|0.0|1.0|0
```

Old 7-field messages are backward-compatible on the receiver (default `enabled = true`).

## Phase 1: Wire Protocol (Python + Swift)

### Python sender side

| File | Change |
|------|--------|
| `source_modules/hud_protocol.py:27` | `SlotPayload`: add `enabled: bool = True` |
| `source_modules/hud_protocol.py:34` | `EMPTY_SLOT`: add `enabled: True` |
| `source_modules/hud_protocol.py:50` | `encode_slot()`: add 7th positional arg `enabled` |
| `source_modules/hud_protocol.py:54` | `encode_slot_payload()`: unpack `payload.enabled` |
| `source_modules/hud_protocol.py:58` | `encode_update()`: add 7th positional arg `enabled` |
| `source_modules/hud_protocol.py:123-137` | `_parse_slot_fields()`: accept 8 total fields, parse `fields[7]` as int→bool |
| `source_modules/hud_client.py:34` | `send_slot()`: add `enabled=True` param |
| `source_modules/hud_client.py:37` | `send_update()`: add `enabled=True` param |
| `source_modules/hud_client.py:53-54` | `NullHudClient`: mirror signatures |

### Swift receiver side

| File | Change |
|------|--------|
| `ableton_hud/Sources/AbletonHUDCore/WireProtocol.swift:~3` | `Slot` struct: add `public let enabled: Bool` |
| `ableton_hud/Sources/AbletonHUDCore/WireProtocol.swift:~88` | `parse()`: accept 8 fields for SLOT/UPDATE, default to `true` for 7-field |
| `ableton_hud/Sources/AbletonHUD/HUDView.swift:~133` | `DialSlotView`: foreground arc uses `Color.gray` when `!slot.enabled`, `Color.cyan` when enabled |
| `ableton_hud/Sources/AbletonHUD/HUDView.swift:~165` | `ButtonSlotView`: optionally reduce opacity for disabled buttons |

### Tests

- `tests/test_hud_protocol.py`: round-trip encode/decode with `enabled`, test 7-field backward compat
- `ableton_hud/Tests/WireProtocolTests/`: parse 8-field SLOT, parse old 7-field defaults to true

## Phase 2: JSON Schema — `controls_enabled_of`

**File: `model_custom_devices.py:41-45`**

Add optional field to `CustomButtonEntry`:
```python
controls_enabled_of: Optional[List[int]] = None
```

No extra validation needed — runtime handles missing/nonexistent params gracefully.

## Phase 3: Runtime — Read and send `is_enabled`

**File: `source_modules/helpers.py`**

### (a) Burst: `_build_dial_payloads()` (~line 485)

Read `is_enabled` when creating `SlotPayload` during burst:
```python
SlotPayload(name, p.value, p.min, p.max, getattr(p, 'is_enabled', True))
```

### (b) Burst: `_build_button_payloads()` (~line 504)

Same for button slots.

### (c) Single UPDATE: `parameter_updated()` (~line 428)

Pass `enabled` through on live knob-turn UPDATEs:
```python
self._hud_client.send_update('dial', parameter_no - 1, name, param.value,
                              param.min, param.max, getattr(param, 'is_enabled', True))
```

### (d) Resolved switch info: `_resolve_switch()` (~line 184)

Include `controls_enabled_of` in the returned dict:
```python
'controls_enabled_of': b.get('controls_enabled_of'),
```

### (e) Dependent UPDATEs: `switch_slot_action()` (after line 278)

After toggling the parameter value, if `controls_enabled_of` is present:
- Rebuild the `real_parameters` list (same as `update_remote_parameters()` does)
- Iterate HUD layout cells, map wire indices to real parameters
- For any parameter whose `d_idx` is in `controls_enabled_of`, read `is_enabled`
  and send an UPDATE via `self._remote._hud_client.send_update()`

Pseudo-code:
```python
ceo = info.get('controls_enabled_of')
if ceo and device:
    dependent_nos = set(ceo)
    # Rebuild real_parameters (same order as burst)
    real_params = [ParameterMapping.on_off().with_real_param(device.parameters[0])]
    for c_idx, _ in sorted(self._slot_assignments):
        rp = self._resolve_encoder(device, c_idx)
        if rp is not None:
            real_params.append(rp)
    # Walk cells and send UPDATEs for dependent params
    for cell in (self._hud_cells or []):
        _gr, _gc, kind, count, start = cell
        if kind != 'dial' or start < 0:
            continue
        for i in range(count):
            wire_idx = start + i
            rp_idx = wire_idx + 1
            if rp_idx >= len(real_params):
                continue
            rp = real_params[rp_idx]
            p = rp.param
            try:
                d_idx = list(device.parameters).index(p)
            except ValueError:
                continue
            if d_idx not in dependent_nos:
                continue
            name = p.name if rp.alias is None else rp.alias
            self._remote._hud_client.send_update(
                'dial', wire_idx, name, p.value, p.min, p.max,
                getattr(p, 'is_enabled', True))
```

## Phase 4: Corpus JSON Entry

Edit `data/custom_device_mappings.json` — add `controls_enabled_of` to the
relevant Corpus button entries. Requires identifying which button parameter
numbers control which encoder groups.

Example (hypothetical — needs verification):
```json
{"number": 17, "name": "LFO On/Off", "controls_enabled_of": [20, 21, 23, 24, 25, 26]},
{"number": 27, "name": "Filter On/Off", "controls_enabled_of": [28, 29]}
```

## Tests

| File | Test |
|------|------|
| `tests/test_hud_protocol.py` | Round-trip encode/decode with `enabled=True/False`. 7-field backward compat. |
| `tests/test_helpers.py` | `FakeParameter` gets `is_enabled: bool = True`. `_build_dial_payloads()` includes `enabled` in payloads. `controls_enabled_of` triggers UPDATEs for dependent params. |
| `ableton_hud/Tests/WireProtocolTests/` | Parse 8-field SLOT. Old 7-field defaults `enabled = true`. Disabled dial renders grey arc. |

## Message Traffic Summary

| Trigger | Before | After |
|---------|--------|-------|
| Device focus / mode / page change | 1 burst | 1 burst (same message count, ~2 bytes larger per slot) |
| Knob turn | 1 UPDATE | 1 UPDATE (same) |
| Button press (no `controls_enabled_of`) | 1 PING | 1 PING (same) |
| Button press (with `controls_enabled_of`, N deps) | 1 PING | 1 PING + N UPDATEs |

## Known Risk: Stale State Between Bursts

Parameters enabled/disabled by a button that does NOT have `controls_enabled_of`
will show stale enabled state until the next burst. Acceptable because:
- Only known device with this pattern is Corpus
- The declarative field can be added to any button as new devices are discovered
- Alternative (global state listeners) would add significant runtime complexity
