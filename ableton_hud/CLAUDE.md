# CLAUDE.md

See @../hud_protocol.md for the wire protocol, controller layout model, and all parameter-resolution logic. This file covers the Swift side only.

## Commands

```bash
./create-app-bundle.sh   # release build + bundle
swift build              # debug binary only
swift test               # unit tests
pkill -f AbletonHUD; sleep 0.5; open AbletonHUD.app  # quick restart
log stream --predicate 'subsystem == "com.local.AbletonHUD"'  # tail logs
./restart.sh # rebuild and restart.
```



## Debugging

Read log files, kill and restart the app, change focus to ableton , ask the user to trigger the relevant action in Ableton, then check logs again for expected/actual behavior.

## Architecture

Two targets share code via a testable core:

### `AbletonHUDCore` — no AppKit, fully unit-testable

**`WireProtocol.swift`** — pure parser. Splits a pipe-delimited line into a `WireMessage` enum (`layout`, `device`, `slot`, `update`, `commit`, `ping`, `unknown`). Never crashes on malformed input.

**`DeviceState.swift`** — `ObservableObject` with a two-buffer burst model:
- `LAYOUT` → stores cells in `pendingCells` (not committed until `COMMIT`; persists across device changes since `DEVICE` does not clear it)
- `DEVICE` → clears `pendingDials`, `pendingButtons`, `pendingName`
- `SLOT` → writes into pending dials or buttons by index
- `COMMIT` → atomically swaps pending → published: sizes `dialSlots`/`buttonSlots` from `pendingCells` counts, fills from pending maps, fires `commitReceived`
- `UPDATE` → immediate single-slot live update, no burst needed

### `AbletonHUD` — AppKit + SwiftUI executable

**`UDPListener.swift`** — `NWListener` on `127.0.0.1:5006`. Decodes UTF-8, splits on `\n`, feeds to `WireProtocol` → `DeviceState` on `@MainActor`.

**`HUDOverlayManager.swift`** — manages a borderless `NSPanel` at `.floating` level with transparent background. Shows only when `AbletonFocusMonitor.isAbletonFrontmost`. Esc key dismisses.

**`AbletonFocusMonitor.swift`** — `NSWorkspace` activation/deactivation notifications, matching bundle-id prefix `com.ableton.live`.

**`HUDView.swift`** — SwiftUI view driven entirely by `DeviceState`:
- Builds a 2-D grid from `hudCells` (row/col coordinates)
- Each cell renders as a horizontal `HStack` of `DialSlotView` or `ButtonSlotView`
- `DialSlotView` — arc dial (36 pt circle, 5/6 sweep), label below; dim when slot is nil
- `ButtonSlotView` — rounded rect (36×20), filled when `value > midpoint`, italic label below; dim when slot is nil
- Cells with `startIndex = -1` receive a nil slot and render as inactive placeholders

see @layout_principles.md for past issues when creating layouts.

## Tests

`Tests/WireProtocolTests/` covers `WireProtocol` (malformed input, unknown commands) and `DeviceState` burst logic (clean burst, overlapping bursts, stragglers, LAYOUT persistence across device changes).
