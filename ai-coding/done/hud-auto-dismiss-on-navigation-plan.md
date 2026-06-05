# Dismiss the HUD when the user navigates away from a device

## Context

The floating HUD overlay (`./ableton_hud`) shows the parameters of the currently
focused Ableton device. Today it hides only in two cases: the 7-second inactivity
timer expires, or Ableton stops being the frontmost macOS app
(`AbletonFocusMonitor`). The gap: when the user **stays inside Ableton** but clicks
away to do another task — opens the browser, switches between Session and
Arrangement, or moves off the device detail — the HUD lingers. The 7s timer is too
slow and keeps getting reset by `UPDATE`/`PING` traffic.

Goal: push an explicit *hide* from the Python control surface whenever the Live API
shows the user has navigated away from the device, and **over-index on hiding** —
the only thing that should bring the HUD back is (re)selecting a device, which
already fires a fresh burst.

## Approach

Two coordinated changes: a new `HIDE` wire verb, and Live `application.view`
listeners on the Python side that emit it. Critically, the receiver must make the
hide *sticky* so routine `UPDATE`/`PING`/refocus traffic doesn't resurrect the HUD.

### 1. New `HIDE` wire verb (sender)

- `source_modules/hud_protocol.py`: add `encode_hide() -> "HIDE"`, a `HideMsg`
  dataclass, parse `verb == 'HIDE'` (no fields), add `HideMsg` to the `Message`
  union. Mirror the trivial shape of `encode_ping`/`PingMsg`.
- `source_modules/hud_client.py`: add `HudClient.send_hide()` →
  `self._send(hud_protocol.encode_hide())`, and `NullHudClient.send_hide(self): pass`.

### 2. Sticky dismiss on the receiver (Swift — Core, so it's testable)

- `WireProtocol.swift`: add `case hide` to `WireMessage`; parse `"HIDE"`
  (require `fields.count == 1`, else `.unknown`). Unknown verbs already degrade
  safely, so an older app ignores `HIDE`.
- `DeviceState.swift`: add `@Published public var dismissed: Bool = false` and
  `public let hideRequested = PassthroughSubject<Void, Never>()`. In `apply`:
  - `.hide` → `dismissed = true`; `hideRequested.send()`
  - `.device` and `.commit` → `dismissed = false` (a new device burst means the
    user reselected a device → allow show). Because `apply` runs synchronously
    before the `.receive(on: RunLoop.main)` sinks, the flag is already cleared
    when `commitReceived` fires, so reselection still shows.
  - `.update` / `.ping` / `.page` / `.mode` / `.layout` → leave `dismissed`
    untouched (UPDATE still patches slot data so it's current when reshown).
- `HUDOverlayManager.swift`:
  - Subscribe to `DeviceState.shared.hideRequested` → `self.hide()`.
  - **Gate both show paths on `!DeviceState.shared.dismissed`:** the
    `commitReceived` sink (line ~33) and the `isAbletonFrontmost`-true refocus
    branch (line ~44). This closes the three resurrection paths (UPDATE during
    automation/LFO, PING from controller actions, app refocus with a non-empty
    `deviceName`).

### 3. Live view listeners (sender — `templates/surface_name/modules/main_component.py`)

In `MainComponent.__init__`, after the existing listeners, register
`application.view` listeners that call `self._hud_client.send_hide()`. Keep
callbacks **directional** — only hide on the away-transition, never on the toward-
device transition, so they can't race our own show burst:

- `add_focused_document_view_listener(self._on_doc_view_changed)` — Session ↔
  Arrangement switch. Unconditional hide (device selection never changes this).
- `add_is_view_visible_listener('Browser', self._on_browser_visibility_changed)` —
  hide **only when** `application.view.is_view_visible('Browser')` is True.
- `add_is_view_visible_listener('Detail/DeviceChain', self._on_detail_changed)` —
  hide **only when** that view becomes **hidden** (selecting a device makes it
  visible, so this won't fire a hide on selection).

Skip a selected-track trigger — it coincides with `appointed_device` and just
churns.

Wrap each registration in `try/except` and `log_message` on failure, so a wrong
identifier degrades gracefully instead of breaking surface load.

**Verify the API names empirically before hardcoding.** `focused_document_view`
is documented `get, observe` so its listener is safe, but
`add_is_view_visible_listener` and the identifier strings (`'Browser'`,
`'Detail/DeviceChain'`) are **not** in `dev-docs/Live.md`. Before/while wiring, use
the @update.py + `./bin/tail_logs.sh` debug path to log
`application.view.available_main_views()` and confirm the exact identifiers and
that the listener method exists on `application.view`.

### 4. Teardown

- Add `MainComponent.remove_app_view_listeners(self)` that removes the three
  listeners (guarded with try/except), and call it from
  `templates/surface_name/surface_name.py::disconnect` (line ~349) so a surface
  reload doesn't double-register.

## Files to change

- `source_modules/hud_protocol.py` — `HIDE` encode/parse + `HideMsg`
- `source_modules/hud_client.py` — `send_hide` on both clients
- `templates/surface_name/modules/main_component.py` — view listeners + callbacks + teardown method
- `templates/surface_name/surface_name.py` — call teardown from `disconnect`
- `ableton_hud/Sources/AbletonHUDCore/WireProtocol.swift` — `.hide` parse
- `ableton_hud/Sources/AbletonHUDCore/DeviceState.swift` — `dismissed` flag + `hideRequested`
- `ableton_hud/Sources/AbletonHUD/HUDOverlayManager.swift` — subscribe + gate show paths
- `hud_protocol.md` — document the `HIDE` verb and the dismissed-flag semantics

## Tests

- Python (`tests/test_hud_protocol.py`): `encode_hide` round-trips; `parse("HIDE")`
  → `HideMsg`; `"HIDE|x"` → `UnknownMsg`.
- Swift (`Tests/WireProtocolTests/`): `parse("HIDE")` → `.hide`; malformed →
  `.unknown`; `DeviceState` test — `.hide` sets `dismissed=true` and fires
  `hideRequested`; a subsequent `.commit`/`.device` clears `dismissed`; `.update`
  and `.ping` leave it set.

## Verification (end-to-end)

1. `poetry run pytest tests/test_hud_protocol.py` and (`cd ableton_hud && swift test`).
2. Regenerate the launch_control surface, `./deploy.sh`, restart Ableton; rebuild
   the HUD (`cd ableton_hud && ./restart.sh`).
3. Select a device → HUD shows. Then, with Ableton still frontmost:
   - open the Browser → HUD hides;
   - toggle Session ↔ Arrangement → HUD hides;
   - click a clip (Detail leaves DeviceChain) → HUD hides.
4. Start playback with an automated/modulated parameter on the selected device,
   hide via navigation, confirm the HUD **stays hidden** (no UPDATE/PING
   resurrection).
5. Reselect a device → HUD reappears.
6. Tail `./bin/tail_logs.sh` to confirm no listener-registration errors.
