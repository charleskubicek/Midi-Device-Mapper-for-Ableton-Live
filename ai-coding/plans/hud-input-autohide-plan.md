# Input-driven HUD auto-hide: the controller shows it, the GUI hides it

## Context

`show-hud-on: summon` (hud-summon-only-plan) hides the HUD by default and
summons it via `hud_toggle` / controller device-nav. Auto-hide was built by
*enumerating* non-device views (clip, browser, doc-switch) and hiding on each.
That approach is fundamentally limited: Live's Python API observes model/view
**state changes, not input**, and there is **no signal for the browser gaining
focus** when it is docked open (verified — see the `live-view-listener-behavior`
memory). We were chasing an unbounded list of "non-device places" with a tool
that can't see most of them.

**Reframe.** The HUD means "I'm tweaking a device *with the hardware*." It should
hide the moment the user switches to working in Live's GUI — any mouse click or
keystroke in Ableton, regardless of *where*. That single rule replaces the whole
enumeration. The signal lives in the **Swift HUD app** (a native macOS process
that can observe global input), not in the Live sandbox.

**Model:**
- **Controller (MIDI) activity** → show / keep alive (existing summon path:
  device-nav + `hud_toggle`; knob/button traffic re-arms the timer).
- **Mac mouse/keyboard activity while Ableton is frontmost** → sticky-hide
  (`DeviceState.timerDismiss`). Clean separation: MIDI never triggers the mac
  monitor; mac input never masquerades as controller activity.

## Scope decisions (settled)

1. **Gate to `trigger == 'summon'`.** A *universal* monitor contradicts the
   `selection` semantic (clicking a device to select it would hide the HUD meant
   to show it) — which the lc_parks compositor forces. The HUD can't know the
   trigger, so the surface sends a wire flag; the HUD defaults the flag **false**
   until `AUTOHIDE|1` arrives (pre-handshake / non-summon surfaces never
   input-hide). Re-emitted with LAYOUT for restart-resilience.
2. **Summon `DeviceFocus('selection')` becomes always-silent** (drop the
   repaint-if-shown branch from hud-summon-only-plan). More robust and matches
   that plan's literal prose ("mouse/track selection never shows it"). **Bonus /
   graceful degradation:** a mouse *device-selection* then hides via the Python
   path even if the OS permission is denied — so the mac monitor is only
   load-bearing for clicks that *don't* change the device (clips, browser,
   mixer, transport).
3. **Remove the broken browser gate** (`BrowserChanged` / `browser_active` /
   `hud_browser_changed` / the template browser listener). Superseded by the
   monitor. **Keep** the clip-view gate + doc-view listener: reliable,
   permission-free, and they still serve the non-summon surfaces the monitor
   won't touch.

## Spike first (before building the plumbing)

The permission/monitor behavior is empirically murky and everything else stacks
on it. **Confirm via a log-only spike** (`GlobalInputMonitor`, no wire flag, no
Python change) using the CLAUDE.md HUD debug loop (restart HUD, user clicks/types
in Ableton, read logs). Resolve:
- Does **mouse-down** arrive with no permission grant?
- Does **keyDown** fire, and which TCC bucket gates it — **Accessibility**
  (`AXIsProcessTrusted`, historically what `NSEvent` global keyboard monitors
  need) or **Input Monitoring** (`CGRequestListenEventAccess`, governs
  CGEventTap/IOHID)? Match the permission API to the monitor API.
- Are the HUD's **own panel clicks** delivered to a *global* monitor at all
  (global monitors receive events posted to *other* apps), i.e. is an over-HUD
  exclusion even necessary?

Permission mechanism below is **to confirm via spike**, not committed.

### Spike findings (confirmed 2026-07-20, Live 12 + macOS)

- **Mouse-down needs NO permission** — `.leftMouseDown`/`.rightMouseDown` fired
  with `axTrusted=false, listenPreflight=false`.
- **keyDown needs the grant** — fired only after granting; both Accessibility
  (`AXIsProcessTrusted`) and Input Monitoring (`CGPreflightListenEventAccess`)
  read `true` after the user granted both. Request Accessibility (the classic
  requirement for `NSEvent` global key monitors) via
  `AXIsProcessTrustedWithOptions(prompt:)`; mouse still works if denied.
- **`abletonFrontmost` gates correctly** — events read `true` only while Ableton
  is focused, so hiding on input while another app is frontmost is avoidable.
- **HUD's own panel clicks never reached the global monitor** (`overHud` stayed
  false throughout) — global monitors only see events posted to *other* apps, so
  dragging/clicking the HUD can't dismiss it. Keep the `!overHud` guard as cheap
  insurance anyway.
- **Permission persistence required code-signing.** The bundle was ad-hoc signed,
  so TCC keyed the grant to the binary hash and every rebuild reset it. Fixed
  with a stable self-signed cert (`dev-codesign-setup.sh`) that
  `create-app-bundle.sh` now signs with; grant survives rebuilds (verified).

## Design (build after the spike confirms the model)

### Swift
- `GlobalInputMonitor`: `NSEvent.addGlobalMonitorForEvents(matching:
  [.leftMouseDown, .rightMouseDown, .keyDown])`. On event, dismiss iff
  `DeviceState.shared.autoHideOnInput && AbletonFocusMonitor.isAbletonFrontmost`
  (and not-over-HUD only if the spike shows HUD clicks are seen) →
  `DeviceState.timerDismiss()`.
- Extract the decision into a pure, testable helper
  (`shouldDismiss(enabled, abletonFrontmost, overHud) -> Bool`) in
  AbletonHUDCore; keep the AppKit/permission wiring thin.
- Request whichever permission the spike proves gates the events; if denied, log
  guidance (System Settings › Privacy). Feature degrades to decision 2's
  Python-side hide + the idle timer.

### Wire flag
- New message `AUTOHIDE|<0|1>`. Python `encode_autohide` /
  `HudClient.send_autohide`; Swift parser `.autoHide(Bool)` → `DeviceState`
  `autoHideOnInput` (published, default false). Emitted from `Remote` alongside
  LAYOUT (init + re-handshake + head of burst) so late-starting HUDs learn it.
- Surface sends `AUTOHIDE|1` iff `hud_trigger == 'summon'`.

### Python
- `hud_visibility.py`: summon `DeviceFocus('selection')` → `EMIT_SILENT_AND_HIDE`
  unconditionally. Delete `BrowserChanged` + `browser_active`; collapse
  `view_gated` back to `clip_view_active`.
- `hud_presenter.py` / `helpers.py` / template: delete the browser gate methods
  and the `Browser` app-view listener. (Clip + doc-view listeners stay.)

## TDD order

1. **Spike** (log-only), confirm the model with the user.
2. Swift: `WireProtocolTests` for `AUTOHIDE` parse + `DeviceState.autoHideOnInput`;
   a pure test for the dismiss-decision helper. Implement parser + monitor.
3. Python: `encode_autohide` + `HudClient.send_autohide` + re-emit tests;
   `test_hud_visibility` summon-selection-always-silent; remove browser-gate
   tests. Implement.
4. Generation test: a `summon` surface emits `AUTOHIDE|1`; `selection` /
   `controller-nav` do not.
5. Docs: `mapping_file.md` (summon auto-hides on any Ableton mouse/keyboard
   input; needs the OS permission), `hud_protocol.md` (new message + the
   confirmed permission note).

## Resolved during build

- **`hud_toggle` after an autonomous hide (two-press / show-only).** The Swift
  side hides on its own via *two* paths (idle timer + input monitor) without
  telling the Python mirror, so any Python-side decision (flip OR show-only)
  mis-fires. First attempt was summon show-only — rejected in testing (the button
  no longer hid the HUD). **Final: the HUD arbitrates the toggle** (`TOGGLE` wire
  message). `hud_toggle` sends a `TOGGLE` marker + a fresh burst; the HUD, the
  only owner of true visibility, hides if it was visible or shows the fresh data
  if not (`DeviceState`: `TOGGLE` captures `isVisible` before the burst's DEVICE
  clears `dismissed`; COMMIT decides). A true one-press toggle for every trigger,
  no back-channel needed, and it also subsumes the idle two-press. The Python
  `dismissed` mirror is best-effort after a toggle — the HUD is source of truth.
  Known gap: toggling on a track with **no device** emits a label-only burst
  (empty device name → HUD `isVisible` stays false), so nothing shows; tracked
  with the knob-turn item.

## Open behaviors to validate with the user (flag, don't silently ship)

- **Knob-turn after a click.** A dismissed HUD ignores `UPDATE`, so after a stray
  click hides it, *turning a knob won't bring it back* — only nav/toggle. In a
  DAW people click constantly; this may feel like the HUD keeps vanishing.
  **The fix hinges on an unverified premise: does automation playback actually
  emit HUD `UPDATE`s?** If not, `UPDATE` only ever comes from user knob-turns and
  letting it re-show is safe and fixes the feel. Check before deciding.
- **Clicking *on* a device** (macro, bank arrow) is device work but still hides —
  the monitor can't tell it from a clip click. The model accepts this; make sure
  the user sees it in testing.

## Supersedes / touches

- Supersedes the browser half of `hud-summon-only-plan.md` and its
  repaint-if-shown summon-selection rule.
- Compositor (forced `selection`) never sends `AUTOHIDE|1` → unaffected.
