# Code Review — Custom Device Mapping Refactor + AbletonHUD

## Context

The recent uncommitted work substantially refactored the device-mapping pipeline:

- `source_modules/helpers.py` was rewritten (~330 lines). The old `CustomMappings` / `ParameterNumberGroup` / `SelectedDeviceParameterPaging` model was replaced by a leaner `Helpers` that holds a flat `_device_table` plus per-target paging (`_encoder_page`, `_button_page`) and resolves parameters lazily via `_resolve_encoder` / `_resolve_switch`.
- `gen_code.py` no longer embeds per-class dispatch tables in generated code — it now emits a single `self._helpers.switch_slot_action(...)` call per switch button and `self._helpers.device_parameter_action(...)` per encoder.
- `model_device.py` / `model_v2.py` carry the schema/template-vars changes; `family_intents.py` retains family loading but is no longer the runtime authority.
- `templates/surface_name/modules/main_component.py` now passes `slot_assignments`, `switch_slot_assignments`, `parameter_mappings_raw`, `encoder_slot_count`, `hud_cells` to `Helpers`.
- The companion Swift project at `/Users/ck/current/ableton_hud` gained `LAYOUT` and `PING` wire commands plus dynamic-grid rendering and saved-position support.

The refactor is sound, tests pass (83), and the new code is much smaller. But the rewrite introduced new boundaries that aren't all defended yet, and the existing test patterns need a few targeted additions to lock in the new behaviour. This review focuses on **edge-case defense** and **unit tests that match the established conventions** in `tests/test_helpers.py` (unittest.TestCase, `FakeParameter`/`FakeDevice` dataclasses, `Mock()` for manager/remote) and the Swift `WireProtocolTests.swift` style.

---

## Part 1 — Python: edge-case fixes

Listed in priority order. File:line refs are against the current uncommitted state.

### 1.1 `update_remote_parameters` assumes `device.parameters[0]` exists
`source_modules/helpers.py:254` — `on_off = ParameterMapping.on_off().with_real_param(device.parameters[0])` will `IndexError` on an empty-parameter device (rare in practice but possible for some M4L/rack cases observed during gathering). Guard with `if device.parameters:`.

### 1.2 `_resolve_encoder` / `_resolve_switch` silently return None on out-of-bounds JSON
`helpers.py:106-107` and `:126-127`. If `custom_device_mappings.json` declares `"number": 999` and the device has 10 parameters, the encoder is silently unmapped. Add a single `self.log_message(...)` so this surfaces in `tail_logs.sh` rather than disappearing.

### 1.3 `_resolve_switch` JSON entry with `min` without `max` (or vice versa) falls into `pulse`, not an error
`helpers.py:128` — `has_range = 'min' in b and 'max' in b`. A half-specified entry silently downgrades behaviour. Either log a warning at load time in `_build_device_table` (`helpers.py:41-50`) or in `_resolve_switch`. Schema validation belongs at load time so the warning fires once per session, not once per press.

### 1.4 `_cycle` with `cmin == cmax` is a silent no-op
`helpers.py:203-211` — `if steps < 2: return`. A user remapping a quantized param to a fixed range will quietly stop cycling. Log once when this is hit (gated on `self._manager.debug`).

### 1.5 Eager logging at lines 175, 187, 201
Three `self.log_message(...)` calls fire on every switch press, regardless of `manager.debug`. The rest of the codebase guards verbose logs with `if self._manager.debug:` (see e.g. `_cycle`'s old call site pattern). Gate these to match the convention.

### 1.6 `switch_idx` 0-based vs `slot_name` 1-based ambiguity is undocumented
`helpers.py:179` converts `'switch1'` → `0`. The convention is fine but unwritten — add a one-line docstring on `_button_json_index` and on the `switch_slot_assignments` parameter explaining 0-based-on-the-wire vs 1-based-in-NT-files.

### 1.7 Identity fallback when device has zero quantized params
`helpers.py:137-139` — `if idx >= len(quantized): return None`. Already correct, but no test covers it; users will hit "switch press does nothing" on devices like Spectrum or Tuner with no quantized params. Consider a one-time `show_message` so the user knows the device has no buttons available.

### 1.8 `_build_device_table` has no validation
`helpers.py:41-50` accepts whatever JSON is passed. Add minimal validation: each device entry has `className`; each encoder/button has `number` (int) and `name` (str). Raise on schema errors at construction so generation crashes loudly rather than runtime crashes inside Ableton.

---

## Part 2 — Python: tests to add

Match existing patterns in `tests/test_helpers.py`:
- `unittest.TestCase` classes
- `FakeParameter` / `FakeDevice` dataclasses (already defined; reuse)
- `Mock()` for `manager` and `remote`
- Direct attribute assertion on `device.parameters[i].value`

Each item below is one new `TestCase` class to be appended to `tests/test_helpers.py` unless otherwise noted.

### 2.1 `TestEncoderResolutionEdgeCases`
- `test_encoder_out_of_bounds_param_number_in_json_returns_none` — JSON declares `number=99`, device has 5 params. Expect `device_parameter_action` to early-return without raising and without touching `remote.parameter_updated`.
- `test_encoder_with_empty_parameter_list_does_not_crash` — `FakeDevice(parameters=[])`. Calling `device_parameter_action` should be a no-op.
- `test_resolve_encoder_skips_index_zero_in_identity_fallback` — already implicitly covered, but add an explicit assertion that encoder 1 never resolves to `parameters[0]`.

### 2.2 `TestSwitchEdgeCases`
- `test_switch_with_only_min_in_json_falls_through_to_pulse` — JSON entry `{"number": 4, "min": 0}` (no max). Assert behaviour matches no-range pulse.
- `test_switch_zero_quantized_params_in_identity_fallback_is_noop` — device with no quantized params. `switch_slot_action` should not raise and not call `_cycle`.
- `test_cycle_with_equal_min_max_is_noop` — direct invocation of `self.helpers._cycle(param, 5, 5)`. Param value unchanged.
- `test_switch_with_non_int_min_max_in_param_falls_back_to_pulse` — `FakeParameter(min="bad", max=1.0, is_quantized=True)`. The `try/except` at line 192-197 should catch and pulse.

### 2.3 `TestPagerBoundaries` (extend existing `TestPager`)
- `test_button_page_inc_dec_within_bounds` (mirror of encoder test for button paging).
- `test_pages_count_with_no_device_table_entry_returns_one` — unknown device, both `_encoder_pages_count` and `_button_pages_count` return 1.
- `test_paging_resets_on_device_change` — change device via `selected_device_changed`, then `parameter_page_inc('encoder')`, change back: page should be 1 again.

### 2.4 `TestUpdateRemoteParametersHudPayload`
- `test_update_remote_parameters_emits_switch_entries_for_known_device` — assert `remote.device_update` is called with `switch_entries` containing `SwitchSlotMapping` for each declared button.
- `test_update_remote_parameters_falls_back_to_quantized_for_unknown_device` — class_name not in JSON, params include 2 quantized; expect 2 `SwitchSlotMapping` entries with `switch_idx=0,1`.
- `test_update_remote_parameters_with_empty_parameters_does_not_crash` — `FakeDevice(parameters=[])`. Should early-return per fix 1.1.
- `test_update_remote_parameters_passes_hud_layout` — assert `device_update` is called with `hud_layout=` kwarg matching the `hud_cells` passed to `Helpers.__init__`.

### 2.5 `TestDeviceTableValidation`
After fix 1.8 lands:
- `test_build_device_table_raises_on_missing_className`
- `test_build_device_table_raises_on_non_int_number`
- `test_build_device_table_handles_missing_buttons_key` (current behaviour — should not break)

### 2.6 `tests/test_gen_code.py` — switch dispatch
The new generated code should call `self._helpers.switch_slot_action(...)`. The agents noted this isn't asserted directly anywhere.
- Add `test_mode_button_template_emits_switch_slot_action` to a new or existing test class, asserting the generated string contains `self._helpers.switch_slot_action(device, "switch1", value, "<fn_name>")` for a switch1 mapping.

### 2.7 `tests/test_family_intents.py` (new file, matches `test_helpers.py` style)
- `test_load_custom_intents_converts_positional_arrays_to_slot_table` — round-trip a small JSON literal.
- `test_load_custom_intents_warns_when_fixed_device_has_more_than_8_encoders` — capture stdout/log.
- `test_load_custom_intents_button_with_max_gt_1_uses_cycle_action` and `test_button_without_min_max_uses_pulse_action`.

---

## Part 3 — Swift HUD: edge-case fixes

Refs against `/Users/ck/current/ableton_hud/Sources/...`.

### 3.1 No generation counter for interleaved DEVICE bursts
`DeviceState.swift:4-63`. If `DEVICE A → SLOT* → DEVICE B → SLOT* → COMMIT`, the COMMIT publishes B's pending dict — correct for the common case. But if the sender ever races (`DEVICE A → SLOT_A1 → DEVICE B → SLOT_B1 → COMMIT_A → COMMIT_B`), state corrupts. Probability on localhost UDP is low but non-zero.

Recommendation: add `private var generation = 0` incremented on every `DEVICE`. Each pending dict tagged with the gen at which it was created. `COMMIT` only publishes if pending matches current gen; otherwise drop. Log at debug.

### 3.2 Position persistence uses string-split rather than Codable
`HUDOverlayManager.swift:96-101, 127-137`. Format `"x|y"` parsed by `split(separator: "|")` — fragile to malformed UserDefaults edits, no schema versioning. Migrate to a `Codable` struct (`SavedFrame { x: Double, y: Double, width: Double?, height: Double? }`) stored as JSON Data. Backward-compat: read old format if present, write new format always.

### 3.3 `.max()!` on hudCells in `HUDView.swift:9`
Force-unwrap is technically guarded by the `!isEmpty` check above it, but a one-line comment (`// safe: guard above ensures non-empty`) avoids future readers second-guessing it. Or use `.max() ?? 0`.

### 3.4 No protocol-version field
The wire protocol has no version header. If a future change requires e.g. a different SLOT field order, parsers from older HUD bundles will silently render wrong data. Recommend (low priority): an optional `VERSION|<n>` line at burst start; absence implies v1.

### 3.5 Sparse debug logging in DeviceState
`DeviceState.swift` does not log DEVICE/SLOT/COMMIT transitions. The Python side logs aggressively; the HUD's silence makes "did the message arrive?" hard to answer. Add a guarded debug log in `apply()` (gated on a `Self.debug = false` flag or a launch arg).

### 3.6 `recvLoop` writes to `/tmp/ableton_hud_debug.log` from the recv thread
`UDPListener.swift:81`. File I/O on every datagram is OK at debug volumes but should be conditional on a debug flag rather than always-on.

### 3.7 `trimmingCharacters(in: .whitespaces)` on the name field
`WireProtocol.swift:97` strips intentional leading/trailing whitespace from parameter names. Probably fine for Ableton's actual names (none have padding), but worth a comment so it's not "fixed" later by accident.

---

## Part 4 — Swift HUD: tests to add

Match existing `WireProtocolTests.swift` style — XCTest class, hand-crafted byte arrays, `XCTAssertEqual`.

### 4.1 `LayoutParseTests` (new file or class within existing)
- `testLayoutWithSingleRowParses` — `LAYOUT|1|0|0|dial|8|0` round-trip.
- `testLayoutWithMultipleRowsAndKindsParses` — combined dial+button rows.
- `testMalformedLayoutWithBadKindReturnsUnknown`.
- `testMalformedLayoutWithNegativeIndicesReturnsUnknown`.
- `testLayoutWithExtraTrailingFieldsParses` (forward-compat).

### 4.2 `InterleavedBurstTests` (DeviceStateBurstTests extension)
After 3.1 lands:
- `testInterleavedDeviceBurstDoesNotCorruptState` — feed `DEVICE A; SLOT A0; DEVICE B; SLOT B0; COMMIT 1` and assert published state is B only, no leak from A.
- `testStrayCommitWithoutDeviceIsIgnored`.
- `testCommitWithMismatchedSlotCountStillPublishes` (current contract — formalize).

### 4.3 `RoundTripFromPythonSenderTests`
Mirror the Python `hud_client.py` byte sequences — copy a couple of real examples (one full burst per device class, one mid-stream UPDATE) into Swift literals and assert the parsed `DeviceState` matches the expected struct. This is the strongest bug catcher because it tests the actual wire-format contract.

### 4.4 `PositionPersistenceTests`
After 3.2 lands:
- `testSavedPositionRoundTripsThroughCodable`.
- `testLegacyStringFormatStillReads`.
- `testCorruptedUserDefaultsFallsBackToCenter`.

### 4.5 SwiftUI snapshot test for `HUDView` (optional, lower priority)
The repo doesn't have snapshot infra. Skip for now unless adding `swift-snapshot-testing` is desired.

---

## Part 5 — Pattern-alignment items

Small consistency fixes that don't change behaviour but tighten the code.

| Where | Item |
|---|---|
| `helpers.py:175,187,201` | Gate `log_message` on `self._manager.debug` to match the rest of the file |
| `helpers.py:80-96` | One-line docstrings on `_encoder_json_index`, `_button_json_index`, `_encoder_pages_count`, `_button_pages_count` documenting indexing convention |
| `helpers.py:54-69` | Constructor: replace 0/8/None defaults with explicit named arguments (style matches existing dataclass-heavy approach) |
| `gen_code.py` | Confirm there are no orphan helpers left from the old dispatch (search for `device_param_pulse`, `device_param_cycle` — references should be gone) |
| `templates/.../main_component.py:62` | The `parameter_mappings_raw=$parameter_mappings_raw` substitution happens before JSON serialisation — verify `gen.py` actually emits a Python literal there, not a JSON-string round-trip |

---

## Part 6 — Verification

After applying fixes from Parts 1 and 3:

1. **Python**: `poetry run pytest tests/ -v` — must remain green and the new tests from Part 2 must pass.
2. **Swift**: `cd /Users/ck/current/ableton_hud && swift test` — existing `WireProtocolTests` and `DeviceStateBurstTests` plus the new tests from Part 4 must pass.
3. **End-to-end smoke**:
   - `poetry run python ableton_control_surface_as_code/gen.py live_surfaces/launch_control/ck_launch_control_16.nt`
   - `./deploy.sh`
   - Restart Ableton, focus an Amp device, then a DrumBuss, then an unmapped M4L device.
   - `./bin/tail_logs.sh` — confirm no IndexErrors, the fallback log lines from fix 1.2 fire on the unmapped device, and the HUD shows continuous params on dials and quantized params on buttons.
4. **HUD bundle**: `cd /Users/ck/current/ableton_hud && ./create-app-bundle.sh && open AbletonHUD.app` — should still build cleanly with the test additions.

---

## Critical files

- `/Users/ck/current/ableton_control_suface_as_code/source_modules/helpers.py`
- `/Users/ck/current/ableton_control_suface_as_code/ableton_control_surface_as_code/gen_code.py`
- `/Users/ck/current/ableton_control_suface_as_code/ableton_control_surface_as_code/family_intents.py`
- `/Users/ck/current/ableton_control_suface_as_code/templates/surface_name/modules/main_component.py`
- `/Users/ck/current/ableton_control_suface_as_code/tests/test_helpers.py` (extend)
- `/Users/ck/current/ableton_control_suface_as_code/tests/test_family_intents.py` (new)
- `/Users/ck/current/ableton_hud/Sources/AbletonHUDCore/DeviceState.swift`
- `/Users/ck/current/ableton_hud/Sources/AbletonHUDCore/WireProtocol.swift`
- `/Users/ck/current/ableton_hud/Sources/AbletonHUD/HUDOverlayManager.swift`
- `/Users/ck/current/ableton_hud/Tests/WireProtocolTests/WireProtocolTests.swift` (extend)

---

## Suggested implementation order

1. Part 1 fixes 1.1–1.5 (defensive guards + logging gates) — tiny, low-risk.
2. Part 2 tests 2.1–2.4 to lock in current behaviour, including the new guards.
3. Part 3.1 (generation counter) + Part 4.2 tests in lockstep — most behaviour-changing item.
4. Part 1.8 + Part 2.5 + Part 2.7 (validation + tests) together.
5. Part 3.2 (Codable persistence) + Part 4.4.
6. Polish: Part 5 + remaining tests.
