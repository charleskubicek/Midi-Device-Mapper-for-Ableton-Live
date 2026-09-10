# Plan: `switch-list` mapping type

## Goal

Replace repetitive individual `switch1:`…`switchN:` entries with a compact list-of-ranges form:

```yaml
# Before
switch1: row-5:1
switch2: row-5:2
switch3: row-5:3
switch4: row-5:4

# After
switch-list:
    -
        range: row-5:1-4
```

Multiple ranges are merged in order:

```yaml
switch-list:
    -
        range: row-5:1-4
    -
        range: row-6:1-2
# → switch1..switch6 across both rows
```

## Constraints

- If `switch-list` and any explicit `switch1:`…`switch8:` coexist in the same mapping, raise a `ValueError`.
- Numbering always starts at `switch1`; no offset option.

## Changes

### 1. `model_device.py`

#### Add `SwitchListEntry` model

```python
class SwitchListEntry(BaseModel):
    range_raw: str = Field(alias='range')

    @property
    def encoder_coords_list(self) -> List[EncoderCoords]:
        from .core_model import parse_multiple_coords
        return parse_multiple_coords(self.range_raw)
```

#### Update `DeviceEncoderMappings`

- Add field: `switch_list: List[SwitchListEntry] = Field(default_factory=list, alias='switch-list')`
- Add `model_validator(mode='after')`: if `switch_list` is non-empty and any of `switch1`…`switch8` is set → raise `ValueError("Cannot mix 'switch-list' with explicit switch1..switch8 entries")`

#### Update `build_device_model_v2_1`

After the existing `switch_entries()` loop, add a branch that processes `device.mappings.switch_list`:
- Flatten all `SwitchListEntry.encoder_coords_list` → resolve each coord → single MIDI coord
- Zip with `switch1`, `switch2`, … → `ModeButtonMidiMapping` entries appended to `mode_button_maps`

#### Update HUD cell building (`switch_maps` path)

Currently finds the first switch's row from `switch_entries()`. Extend to also check `switch_list[0].range_raw` when `switch_entries()` yields nothing.

### 2. Tests

- `tests/test_model_device.py` (new or existing):
  - `switch-list` single range → correct `ModeButtonMidiMapping` entries
  - `switch-list` multi-range → entries merged in order
  - `switch-list` + explicit `switch1:` → `ValueError`
- Update `ck_ec4.nt` to use `switch-list` as a smoke-test usage example

## File Checklist

- [ ] `ableton_control_surface_as_code/model_device.py`
- [ ] `tests/test_model_device.py` (or equivalent)
- [ ] `live_surfaces/ec4/ck_ec4.nt` (update to use new syntax)
