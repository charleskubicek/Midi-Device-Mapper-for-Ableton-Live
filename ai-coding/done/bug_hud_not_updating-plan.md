# Bug: HUD stale on device-replace, then crashes permanently dead

## Symptom

With Wavetable focused the HUD showed its mappings. Inserting a Drift device to
*replace* Wavetable: (1) the HUD kept showing Wavetable's mappings, then (2) it
flickered and went permanently dead — moving between devices/tracks and the
"show HUD" button all did nothing. Live log showed the same error repeated 26×:

```
File ".../ck_grid/modules/hud_presenter.py", line 92, in emit_burst
  f"[burst] emit_burst device={getattr(device, 'name', None)!r} "
Boost.python ArgumentError: None.None(WavetableDevice)
did not match C++ signature: None(TPyHandle<ADevice>)
```

## Root cause

Replacing a device leaves the old `WavetableDevice` as a **dead Boost.Python
handle**; any attribute access (`.name`, `.parameters`) raises
`ArgumentError` — which subclasses `TypeError`, NOT `AttributeError`, so
`getattr(device, 'name', None)` does **not** swallow it. Two defects combined:

- **A — no device-replace event.** Only `add_appointed_device_listener` was
  wired; an in-place replace doesn't reliably fire it → stale Wavetable content.
  (`Track.devices` was never observed; `on_selected_track_changed` existed but
  was never registered.)
- **B — dead-handle crash + no recovery.** A burst against the pinned dead
  handle threw; `_last_selected_device` stayed dead, so the same-device guard
  (`helpers.selected_device_changed`), `ParameterResolver.ensure_focused`, and
  the show-HUD toggle all kept re-throwing/short-circuiting → permanent death.

## Fix (implemented)

**1. Crash-safety (fixes "permanently gone").** Shared dead-handle guards in
`source_modules/param_resolver.py`, mirroring the existing `_attr` pattern:
`_safe_device_attr`, `_device_alive`, and a fail-OPEN `_same_device`.
- `hud_presenter.emit_burst` bails (`remote.hide()` + return) on a dead device.
- `helpers.selected_device_changed` uses `_same_device` (short-circuits only when
  the previous device is *live and equal*), plus a dead-*new*-device guard so a
  transiently-freed selection is dropped, never pinned.
- `param_resolver.ensure_focused` uses `_same_device` (dead prev → treat as
  changed → reset). Fail-open is what lets a session self-recover.

**2. Event-driven resync.** `templates/surface_name/modules/main_component.py`
now registers the selected-track listener and observes the selected track's
`Track.devices` chain (`_attach_track_devices_listener` /
`_teardown_track_devices_listener` / `_on_track_devices_changed`), re-attached on
track change and torn down on disconnect. A replace now funnels
`selected_device_changed(live_device)` → fresh burst. (No heartbeat: a periodic
burst would clear the sticky `dismissed` flag and resurrect a HUD the user hid.)

## Tests

- `test_param_resolver.py` — liveness primitives + `ensure_focused` fail-open
  (dead prev, raising-eq prev, idempotence preserved) + anti-vacuous check.
- `test_hud_presenter.py` — `emit_burst` on dead device (both eq variants) no-ops
  + hides; None still no-op-no-hide; live device still full burst.
- `test_helpers.py` — recovery from dead pinned `_last_selected_device`; no
  over-fire on same live device; dead-new-device dropped; teardown-race burst.

Fakes model the real failure: attribute access raises a **TypeError** subclass
(not AttributeError), so `getattr` defaults can't shield them.

Non-vacuity proven empirically: neutering `_device_alive` to `return True`
(simulating pre-fix) fails 5 of the new tests (both presenter dead-device tests,
the teardown-race, the dead-new-device drop, and the `_device_alive` primitive).
Note the plain-`_DeadDevice` recovery test passes even pre-fix (identity `__eq__`
returns False → the old guard already proceeded); the `_DeadDeviceRaisingEq`
variant + presenter tests carry the non-vacuous weight.

## Verification

- `./build.sh` — 566 passed. Quality: `loc_total +269` (fix + tests); no
  god-class/complexity/config-drift regressions.
- Generated `ck_grid/modules/main_component.py` py-compiles with the new wiring.
- End-to-end (user redeploys + restarts Ableton): focus Wavetable → replace with
  Drift → HUD updates to Drift, no `ArgumentError` in `./bin/tail_logs.sh`;
  dismissed HUD does not auto-resurrect on unrelated chain churn.

## Caveat

If Live already disabled the `ck_grid` script after the 26 repeated exceptions,
that session needs an Ableton reload — the guards prevent recurrence but can't
revive an already-disabled script.
