# Plan: `show-hud-on:` — gate the HUD burst by trigger source

## Why
The HUD pops up too often. Root cause: `surface_name.py:46` polls the selected device
every 1.5s → `update_selected_device()` → `Helpers.selected_device_changed()` → full HUD
burst. *Any* change to Live's selected device (mouse click, track select, anything) is
detected by the poll and shows the HUD, indistinguishably from a deliberate controller-nav
press. The user wants the HUD to appear only when they navigate with the controller's
device-nav buttons.

## Axis clarification (do not conflate)
This is a **trigger** axis, orthogonal to the two that already exist:
- `hud: on|device_only|off` — **content**: full mode-labels / raw device params / kill switch.
  (`device_only` only blanks label overlays — `gen.py:152`.) Keep `hud: off` as the single
  kill switch. Do NOT add a `never` to `show-hud-on`.
- dismiss/timeout axis — auto-dismiss timer + app-view HIDE listeners
  (`main_component.py:78-136`) + the in-flight `hud_toggle` button. This plan does NOT touch
  lingering; it only fixes the *pop-in on selection*.

## Decision (user-confirmed)
New key: **`show-hud-on:`** with two values:
- `selection` — **default**, current behavior. HUD follows Live's selected device (poll path).
- `controller-nav` — HUD burst fires ONLY from controller **device-nav** actions
  (`device_nav_left/right/first/last`). **track-nav is excluded** (user choice) — stepping
  tracks via the controller stays silent.

Composes with `hud_toggle` (separate plan): in `controller-nav` mode, a mouse-navigated
device shows nothing until the user presses the bound `hud_toggle` button to summon it.

## Implementation gate point
The thing to suppress is the **burst** (`Remote.refresh_burst` → `send_device/send_slot/
commit`), NOT `selected_device_changed`. The poll path must keep running param remap +
group-selector listener attach so encoders still control the newly-selected device; only the
HUD wire output is gated. `selected_device_changed` is called by both the poll and the nav
handlers and currently can't tell them apart — thread the trigger source through.

### Approach
1. **Model** (`model_v2.py`): add `class HudTrigger(str, Enum): Selection='selection';
   ControllerNav='controller-nav'`. Add `show_hud_on: HudTrigger = HudTrigger.Selection`
   (alias `show-hud-on`) to `RootV2` and `RootV2ModesOrModeless`; pass through in
   `buildRootV2`. `extra='forbid'` is already set, so the alias must be wired correctly.
2. **gen.py**: read `mappings.show_hud_on`; render a template var (e.g.
   `$hud_trigger = 'selection'|'controller-nav'`) into `main_component.py`.
3. **Runtime gating** — thread an explicit source flag rather than guessing:
   - `Helpers.selected_device_changed(device, source='selection')`. Pass
     `source='nav'` from the device-nav handlers, default `'selection'` from the poll
     (`update_selected_device`) and other callers.
   - Store `self._hud_trigger` (from the template var) on `MainComponent`/`Helpers`.
   - Gate: emit the HUD burst when `hud_trigger == 'selection'` OR `source == 'nav'`.
     Otherwise run the remap/listener work but skip the burst. Cleanest seam: pass a
     `suppress_hud: bool` down to `Remote.device_update` / `refresh_burst`, OR compute
     "should_burst" in `selected_device_changed` and call a remap-only path when false.
   - The device-nav handlers in `main_component.py:175-200`: only
     `device_nav_left/right/first/last` pass `source='nav'`. `track_nav_inc/dec` keep the
     default (silent in controller-nav mode).
4. **Off interaction**: when `hud: off`, the client is already `NullHudClient` — gating is a
   no-op, fine. No special-casing.

## Naming collisions avoided
- value `controller-nav` (NOT `device-nav`) — `device-nav` is an existing **mapping type**.
- key follows Live's "selected device" concept, NOT `device-view` (= `Detail/DeviceChain`,
  used in dismiss listeners).

## TDD order
1. Failing tests first (`tests/test_show_hud_on.py`):
   - parse: `show-hud-on: controller-nav` → `RootV2.show_hud_on == HudTrigger.ControllerNav`;
     default (key absent) → `Selection`; bad value → validation error.
   - gen: generated `main_component.py` carries the trigger var; device-nav handlers pass the
     nav source.
   - runtime (unit, with a fake hud client): `selected_device_changed(dev, 'selection')` under
     `controller-nav` trigger → no `send_device`; `selected_device_changed(dev, 'nav')` →
     `send_device` called once. Under `selection` trigger → both fire. Confirm param remap
     still runs in the suppressed case (e.g. `update_remote_parameters` still invoked).
2. Implement model → gen → runtime until green.
3. Full `poetry run pytest`.
4. Wire into a real surface only if the user asks: set `show-hud-on: controller-nav` in
   `live_surfaces/launch_control/ck_launch_control_16.nt`. Let the user redeploy/restart Live.

## Second HUD path — the live UPDATE wake (resolved during impl)
There are TWO paths to the HUD, not one. Gating the burst is not enough:
`Remote.parameter_updated` → `send_update` fires on every knob/button operation,
ungated. Per `hud_protocol.md`, `UPDATE` is a *show path* while the Swift `dismissed`
flag is clear — so in controller-nav mode, after a mouse-select (burst suppressed but no
HIDE), turning a knob would wake the HUD and patch now-stale slots by index.
**Fix:** when a burst is suppressed, also `self._remote.hide()`. HIDE sets the sticky
`dismissed` flag so UPDATE/PING can't resurrect it; the next device-nav burst
(DEVICE/COMMIT) clears it and repaints fresh. We set `_hud_dismissed=True` to keep
hud_toggle intent in sync. Net behavior: mouse-selecting a device hides the HUD until you
device-nav (or press hud_toggle). Feedback sinks (EC4) still update regardless.

## Out of scope
- The lingering/auto-dismiss timer (separate axis).
- `hud_toggle` button (separate plan — but ship together for usability).
- Widening `controller-nav` to include track-nav or general encoder touches (deferred; the
  value name leaves room to broaden behavior without a rename).
