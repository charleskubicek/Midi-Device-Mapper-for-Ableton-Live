# Hide the HUD when track-nav lands on a device-less track

## Context

Follow-up to `hud-summon-only-plan.md` / `hud-input-autohide-plan.md`
(commit 83a699b). Confirmed bug: with the HUD summoned, moving between tracks
via **controller track-nav** to a track whose `view.selected_device` is `None`
(empty track, return/master, fresh track) leaves the HUD frozen on the previous
track's device.

**Root cause** (confirmed with user 2026-07-21): `Helpers.selected_device_changed`
(`source_modules/helpers.py:214`) early-returns when `device is None` — *before*
the `HudVisibility` table ever runs. No decision, no `HIDE` datagram. This is
the one path with no safety net:

- Controller track-nav generates no mac input → the Swift `GlobalInputMonitor`
  can't see it (it only covers mouse clicks / keystrokes).
- The Python hide (`DeviceFocus('selection')` → `EMIT_SILENT_AND_HIDE` →
  `remote.hide()`) only fires when there is a live device to route.

When the destination track *has* a device the existing path is correct — this
plan only fills the `None` hole.

## Design

### 1. `helpers.py` — route the None case through the visibility table

In `selected_device_changed`, split the current combined guard:

- `_same_device` short-circuit: unchanged.
- `device is None`: instead of the bare return, call a new presenter entry
  point (e.g. `HudPresenter.on_device_focus_lost(source)`); keep skipping the
  resolver reset / group-listener attach / burst (there is nothing to resolve).
- Leave `_last_selected_device` untouched in the None case, so the same-device
  guard on returning to the original track behaves exactly as today.

### 2. `hud_presenter.py` — `on_device_focus_lost(source)`

Fires `DeviceFocus(source)` through the table; if the decision is
`EMIT_SILENT_AND_HIDE`, call `self._remote.hide()`. No burst, no resolver.

- Under `summon` / `controller-nav`: selection-source classifies to
  `EMIT_SILENT_AND_HIDE` → HIDE goes out, mirror syncs. Bug fixed.
- Under `selection` (incl. the forced lc_parks compositor): classifies to
  `EMIT_BURST`, nothing to burst → deliberate no-op. Preserves the known
  "HIDE-on-select races the parks COMMIT" hazard avoidance; behaviour for
  `selection` surfaces is byte-identical on the wire.
- `source='nav'` classifies to `EMIT_BURST` → also a no-op (a nav that lands
  on nothing shows nothing; matches the documented empty-track toggle gap).

No `HudVisibility` change needed — the table already gives the right answers.

## Companion fixes (same commit, found in the same review)

### 3. `reemit_combined_burst` discards its decision (lc_parks clip gate)

`hud_presenter.py:224`: `decide(RegionCommit())` is computed (the FSM returns
`EMIT_SILENT_AND_HIDE` while clip view is open — asserted in
`test_hud_visibility`) and then thrown away; `emit_burst(device,
suppress_hud=False)` always shows. Route it like `on_device_focus`:

```python
decision = self._visibility.decide(RegionCommit())
self.emit_burst(device, suppress_hud=(decision is Decision.EMIT_SILENT_AND_HIDE))
```

### 4. Dead code from the TOGGLE redesign (pure simplification, no behaviour change)

- `UserToggle` is no longer fired in production (`toggle()` is HUD-arbitrated).
  Remove the event + its `_classify` row + its dedicated tests; tests that used
  `decide(UserToggle())` to reach the "shown" state switch to
  `decide(DeviceFocus('nav'))`.
- `_sync_idle_dismiss` call in `on_device_focus` is a no-op now (no
  `DeviceFocus` rule reads `dismissed` since summon-selection became
  always-silent). Drop the call + its stale repaint-if-shown comment. Keep the
  call in `refresh_for_mode` (ModeChange *does* branch on `dismissed`).
- Stale docs: `hud_visibility.py` header "wiring status" (drop UserToggle, add
  ClipViewChanged), `hud_presenter.py` module docstring (same), the
  `_sync_idle_dismiss` docstring ("next UserToggle flips on a single press").
- `view_gated` is a pure alias of `clip_view_active` since the browser-gate
  removal — inline it away.
- Stale comment in `AbletonHUDApp.swift`: `// SPIKE: log-only global input
  probe` — it's the production monitor.

## Explicitly out of scope

- **Mode press resurrects a dismissed HUD** (mirror drift after toggle-off /
  input-monitor hide + shift press within the idle window). Needs a hardware
  verdict on whether it actually annoys before choosing between living with it
  and a repaint-only burst variant (Swift-arbitrated, like TOGGLE). Flagged in
  the review; decide separately.
- TOGGLE riding a separate datagram from its burst (lost-burst leaves
  `pendingToggle` armed). Near-theoretical on loopback UDP.
- hud_protocol.md duplicated `PAGE` section (pre-existing doc cleanup).

## TDD order

1. Failing tests:
   - `tests/test_show_hud_on.py` (Helpers level): with a prior focused device,
     `selected_device_changed(None)` under `summon` and `controller-nav` sends
     `HIDE` and sets the dismissed mirror; under `selection` it stays a no-op
     (no hide, no burst).
   - `tests/test_hud_presenter.py`: `on_device_focus_lost('selection')` hides
     under summon; no-op under selection; `reemit_combined_burst` honours the
     clip gate (`clip_view_changed(True)` then region commit → `hide()`, burst
     suppressed).
2. Implement items 1–3.
3. Item 4 cleanup (tests stay green throughout; only test *helpers* change).
4. `poetry run pytest`; `./build.sh` (report quality change); `swift test` is
   unaffected but run it anyway (comment-only Swift change).
5. Regenerate `ck_grid`; user redeploys + restarts Live. Verify with `hudtrace`
   + `./bin/tail_logs.sh`: summon the HUD, track-nav to an empty track →
   `[vis] decide event=DeviceFocus(selection) … decision=emit_silent_and_hide`
   and the HUD hides; track-nav back to the device track → stays hidden until
   summoned (summon semantics).
