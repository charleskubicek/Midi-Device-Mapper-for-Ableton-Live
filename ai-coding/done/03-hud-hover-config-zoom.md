# HUD hover config + zoom

## Context

The AbletonHUD overlay (`/Users/ck/current/ableton_hud`) is a fixed-size, borderless `NSPanel` that auto-dismisses 7 seconds after a `commit`. There is currently no way for the user to configure it at runtime, and hovering over it does not pause the auto-hide. We want:

1. While the mouse is over the HUD, surface an inline config UI (visible only on hover).
2. The first config controls are **zoom presets** at 100% / 110% / 120% / 130% (i.e. baseline + the user's requested 10/20/30 % increases).
3. While the mouse is over the HUD it must not disappear — auto-dismiss is paused on hover-enter and resumed on hover-exit.

This is local to the HUD app; nothing in the Python generator side needs to change.

## Approach

### 1. Track hover state in `HUDOverlayManager`

`HUDOverlayManager.swift` currently owns the panel and the dismiss timer. Add a `@Published var isMouseOver: Bool` to a small `@MainActor` `ObservableObject` (e.g. `HUDChrome`) that the manager owns and that `HUDView` observes.

In `createPanel()` (line 92), after the panel exists, install an `NSTrackingArea` on `panel.contentView` with options `[.activeAlways, .mouseEnteredAndExited, .inVisibleRect]`. Override `mouseEntered`/`mouseExited` via a small `NSView` subclass placed as a transparent overlay sibling of the hosting view (or by subclassing `NSHostingView` — the subclass route is simpler and more robust against SwiftUI rebuilds).

On `mouseEntered`: set `chrome.isMouseOver = true` and `dismissTimer?.invalidate(); dismissTimer = nil`.
On `mouseExited`: set `chrome.isMouseOver = false` and re-arm the 7-second timer (extract the existing block at line 78 into a private `armDismissTimer()` for reuse).

Update `show()` so that if `chrome.isMouseOver` is already true (e.g. a commit fires while hovering), it does **not** arm the timer.

### 2. Persist zoom in `HUDChrome`

Add `@Published var zoom: Double` (default 1.0), backed by `UserDefaults` key `"hudZoomLevel"` alongside the existing `kSavedPosition` (line 8). Allowed values: 1.0, 1.1, 1.2, 1.3.

When zoom changes, after the SwiftUI relayout completes, call `panel.setContentSize(hostingController.view.fittingSize)` so the panel grows/shrinks to fit. The existing resize logic in `show()` (line 67–70) already handles this pattern — extract it to a private `resyncSize()` and call it from a Combine sink on `chrome.$zoom`.

### 3. Add the config overlay in `HUDView`

`HUDView.swift` (line 16) currently returns the `VStack` device+grid wrapped by background. Wrap that body in a `ZStack` and overlay a `ConfigBar` view in the top-right corner that is shown only when `chrome.isMouseOver`:

```
ZStack(alignment: .topTrailing) {
    mainContent
    if chrome.isMouseOver { ConfigBar(chrome: chrome) }
}
```

Implementation note: `.scaleEffect` does not change the view's reported size, so applying it directly will not enlarge the panel. The existing `.fixedSize()` at line 36 must be removed and replaced with an explicit frame `width: baseSize.width * zoom, height: baseSize.height * zoom` combined with `.scaleEffect(chrome.zoom, anchor: .topLeading)` on the inner content. `baseSize` is captured once via a `GeometryReader` measurement of the unscaled content (or hard-coded to ~960×280 from the HUD's CLAUDE.md if measurement is awkward).

`ConfigBar` is a small `HStack` of four buttons labelled `100%`, `110%`, `120%`, `130%`, each setting `chrome.zoom` to the corresponding value. Use `.buttonStyle(.borderless)`, small rounded background, white-on-dark to match the HUD aesthetic. Keep the bar a horizontal container so future config controls (opacity, position lock, etc.) can be added later.

### 4. Don't let the config bar steal focus from drag

The panel uses `isMovableByWindowBackground = true` (line 119). Buttons inside SwiftUI views will swallow the click correctly; the rest of the chrome remains draggable. No change needed, but verify after wiring up.

## Critical files

- `/Users/ck/current/ableton_hud/Sources/AbletonHUD/HUDOverlayManager.swift` — tracking area, hover state, timer pause, zoom resize, new `HUDChrome` injection
- `/Users/ck/current/ableton_hud/Sources/AbletonHUD/HUDView.swift` — hover-conditional `ConfigBar` overlay, scale wrapper
- New: `/Users/ck/current/ableton_hud/Sources/AbletonHUD/HUDChrome.swift` — `ObservableObject` holding `isMouseOver` and `zoom`, with UserDefaults persistence for zoom

No changes needed in `AbletonHUDCore`, `WireProtocol`, `DeviceState`, or anything in the Python generator side.

## Verification

1. `swift build` — compiles clean.
2. `swift test` — existing core tests still pass (no core changes).
3. `./create-app-bundle.sh && pkill -f AbletonHUD; sleep 0.5; open AbletonHUD.app`
4. With Ableton (or the fake simulator) frontmost and HUD showing data:
   - Move mouse over HUD → config bar appears in top-right; HUD stays visible past 7 s.
   - Move mouse away → config bar disappears; 7-second timer re-arms and HUD hides.
   - Click 110% / 120% / 130% → HUD grows by that factor and panel resizes to fit; setting persists across `pkill`+relaunch.
   - Click 100% → returns to baseline.
   - Drag the panel by its background while config bar is hidden → still movable; saved position still restored.
   - Press Esc → still dismisses immediately.
