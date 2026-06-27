# HUD ↔ Surface Protocol Instrumentation Plan

## Why this plan exists

Two field-reported bugs in the HUD ↔ control-surface communication:

1. **HUD flashes then hides on device move** — moving between devices makes the
   HUD appear and immediately remove itself.
2. **HUD out of step with the shift button** — the HUD's shift/mode display
   drifts from the actual held-shift state.

There is a working *hypothesis* for each (see "Suspects" below), but the advisor
flagged that the diagnosis rests on **circular reasoning** — e.g. "`scroll_view()`
must fire the listener synchronously, because that's what would make the bug
happen." We do not actually know the event ordering across the UDP boundary.

**This plan is observation-only. It adds toggleable `fine`/trace logging across
both the Python surface and the Swift HUD so we can capture the real event order,
then diagnose. It changes no behaviour and applies no fix.** The fix is a
separate, evidence-driven plan written *after* a trace is captured.

The user's instruction: *"instrument the python and swift code significantly,
add all 'debug' or 'fine' logs that can be turned on and off."*

---

## Suspects (to confirm / refute with the trace — NOT to fix yet)

- **Bug 1.** Every `device_nav_*` in `main_component.py` calls
  `self._nav.device_nav_*()` (which calls Live's `view.scroll_view()`) and then
  `selected_device_changed(..., source='nav')`. *If* `scroll_view()` fires the
  `appointed_device` listener synchronously, `on_device_selected` runs first with
  `source='selection'` → under `hud_trigger='controller-nav'` that is
  `EMIT_SILENT_AND_HIDE` → a `HIDE` is sent and `_last_selected_device` advances;
  the explicit `source='nav'` call then hits the same-device guard and no-ops.
  Net: HIDE with no re-show. `device_nav_first/last` loops `scroll_view`, firing
  this repeatedly. **Unverified: whether the listener fires sync, async, or at
  all on this path.**
- **Bug 2.** `goto_mode` (and/or `mode_button_listener` on shift release) may
  interleave with `on_device_selected` and/or send `MODE` in a transient
  inverted order: on shift release `mode_button_listener` calls
  `goto_mode(...)` (which sends `send_mode(next_mode.is_shift)`) and *then*
  `send_mode(False)` — a possible shift→normal flip the HUD latches wrongly.
  **Unverified: the actual MODE send order and whether a stray HIDE lands
  between the mode burst and the user reading it.**

Both suspects share one mechanism: `on_device_selected` firing at the wrong
moment and a `HIDE` overriding an intentional burst. The trace must capture
exact ordering on **both** sides of the wire.

---

## Design principles

- **No behaviour change.** Only add gated log statements + the toggle plumbing.
  `EMIT_SILENT_AND_HIDE`, the `dismissed` mirror, the listeners — all untouched.
- **Off by default, runtime-toggleable**, separate from the existing `debug`
  flag (which gates `_on_selected_parameter_changed` and would flood if reused).
- **Within-side log sequence is the reliable ordering signal.** Each side is
  single-threaded, so log order = execution order — that is what answers both
  bugs (nav→listener nesting on Python; `MODE`/`send_mode` call sequence). Both
  sides also log the **raw wire line** plus a wall-clock timestamp for *coarse*
  cross-side alignment, but sub-millisecond cross-side ordering is not resolvable
  by wall clock and the diagnosis does not depend on it — both bugs are
  answerable from the Python log alone.
- **Greppable.** One consistent tag, `[hudtrace]`, with a sub-tag per component
  (`[hudtrace nav]`, `[hudtrace vis]`, `[hudtrace recv]`, …).
- **Single mental model of "what fired and what it decided."** Every
  `HudVisibility` decision logs `event → (dismissed_before) → decision →
  (dismissed_after)`; every `DeviceState.apply` case logs the same shape on the
  Swift side.

---

## Part A — Python surface instrumentation

### A1. The toggle
- Add a `self.fine` flag on the manager in `templates/surface_name/surface_name.py`
  (default `False`, beside `self.debug` at line ~42).
- Add a `hudtrace` command to the dispatch (~line 302): `hudtrace` flips
  `self.fine`, logs and ACKs the new state. Also add `hudtrace` to
  `templates/update.py`'s `choices` list so `python update.py hudtrace` works.
- The Swift side has its **own** independent switch (Part B2 / Part C) — no wire
  message is involved, so the protocol under test is untouched.

### A2. The helper
- Add `MainComponent.fine(self, msg)` that no-ops unless `self.manager.fine`,
  else `self.log_message(f"[hudtrace] {msg}")`.
- Thread a `fine` callback into the components that touch the protocol the same
  way `log=self.log_message` is already threaded (`helpers.py` passes `log` into
  `HudPresenter`, `Remote`, `Doctor`). Add a parallel `fine=` arg, defaulting to
  a no-op so existing call sites and tests stay green.

### A3. Instrumentation points (entry/exit + decisive state)
- **`helpers.py` `Helpers.selected_device_changed` (THE funnel — most important
  Python point for Bug 1).** Both `device_nav_*` and `on_device_selected` pass
  through here, and this is where the same-device guard short-circuits. On every
  entry log: the device, the `source`, and **whether the same-device guard
  short-circuited** (the telltale: nav fires → `selected_device_changed(
  source='selection')` reaches a real `EMIT_SILENT_AND_HIDE` → then the explicit
  `selected_device_changed(source='nav')` no-ops on the guard). Without the
  guard-result + source logged here, the trace shows a HIDE but never proves
  *why* — Part E's diagnosis depends on this line.
- **`main_component.py`**
  - `device_nav_left/right/first/last`, `track_nav_inc/dec`: log entry,
    `selected_device` name **before and after** the `_nav` call, and the
    `source` passed onward. A synchronous listener fire inside `scroll_view`
    then shows up as `on_device_selected`'s line appearing **between** the
    before/after lines — read it off log *sequence* (single-threaded), no
    counter needed.
  - `on_device_selected`: log entry + resolved `selected_device`.
  - `on_selected_track_changed`.
  - App-view listeners `_on_doc_view_changed`, `_on_browser_visibility_changed`,
    `_on_detail_changed`: log entry, the `is_view_visible(...)` result, and the
    fact that `hud_view_left()` is being called (the other two HIDE paths the
    Bug-1 hypothesis ignored).
  - `goto_mode`: log entry, `next_mode_name`, `is_shift`, and the **order** of
    `refresh_hud_for_mode` → `send_mode(is_shift)` → `mode_sender.send_mode`.
  - `mode_button_listener`: log `value`, `current_mode`, and which branch ran
    (the shift-release `goto_mode(...)` + `send_mode(False)` double-send).
- **`hud_visibility.py`** — `HudVisibility.decide`: log `event`, `trigger`,
  `dismissed`-before, `decision`, `dismissed`-after. This is the single most
  important line for both bugs.
- **`hud_presenter.py`** — `emit_burst` (device name, `suppress_hud`),
  `on_device_focus` (source, decision), `view_left` (decision),
  `reemit_combined_burst`, `refresh_for_mode`, and **every** call that reaches
  `self._remote.hide()`.
- **`helpers.py` `Remote`** — `hide()`, `refresh_burst()` (entry + `_in_burst`
  transitions), `device_update` entry, `send_mode`.
- **`hud_client.py`** — gate one fine line in the `_send` chokepoint logging the
  exact wire line sent (the send-side half of the correlation). `NullHudClient`
  stays silent.

---

## Part B — Swift HUD instrumentation

### B1. Leveled logging facility
- Promote `hudLog` (in `UDPListener.swift`) to take a level:
  `hudLog(_ msg: String, level: HudLogLevel = .info)`. Keep existing `.info`
  call sites always-on. Add a global `var hudFineEnabled = false` (atomic /
  main-actor) gating `.fine`. Move `hudLog` somewhere shared (its own small
  file) so `DeviceState` (Core target) can call it — or, since Core has no
  AppKit, expose a `DeviceState.fineLog` closure injected by the app target so
  Core stays dependency-free.

### B2. Toggle mechanism (file sentinel — implemented)
- **The HUD is launched via `open AbletonHUD.app`** (`restart.sh`), which inherits
  neither the shell environment nor `UserDefaults.standard`'s domain — so an env
  var / defaults key armed in a terminal would silently do nothing. The robust,
  launch-agnostic switch is a **file sentinel**: tracing is on while
  `/tmp/ableton_hud_fine` exists (`touch` on, `rm` off).
- `refreshHudFineEnabled()` re-reads the sentinel; the recv loop calls it once
  per datagram, so a touch/rm toggles at runtime within one message (no relaunch,
  symmetric with the Python `hudtrace` command). `HUD_FINE=1` remains a fallback
  for `swift run`. Nothing is added to the wire protocol under test. See Part C.

### B3. Instrumentation points
- **`UDPListener.recvLoop`**: already logs raw bytes; add a `.fine` line per
  *parsed* `WireMessage` (verb + key fields) right before dispatch.
- **`DeviceState.apply`**: a `.fine` line on **every** case with the decisive
  state — `.device` (name, `dismissed` cleared), `.commit` (count, `dismissed`
  cleared, pending→published sizes), `.hide` (`dismissed` set), `.mode`
  (`isShiftMode` before→after), `.update`. This is the receiver-side crux for
  both bugs.
- **`HUDOverlayManager`**: `commitReceived` and `hideRequested` handlers
  (including the "all active sources dismissed / keeping panel" branch),
  `show()`, `hide()`, `armDismissTimer` set + fire.
- **`isVisible`**: log its value at each show/hide decision point.

---

## Part C — The toggle: two independent switches (recommended)

Because the thing under investigation **is** the wire protocol, add **no** new
wire message:

- **Python:** `update.py hudtrace` flips `manager.fine` (Part A1).
- **Swift:** the `/tmp/ableton_hud_fine` file sentinel (Part B2) — `touch` on,
  `rm` off, runtime, launch-agnostic.

Arm both before reproducing (`touch /tmp/ableton_hud_fine`, `update.py
hudtrace`). Both are runtime on/off and neither adds surface area to the protocol
we're trying to prove reliable.

> **Alternative (only if two-switch friction actually bites):** a `LOG|fine|on`
> wire verb so one `hudtrace` command flips both sides — parsed in
> `WireProtocol.swift` → `.logLevel`, applied in `DeviceState` with no display
> change, sent via `hud_client.send_log`. Adds one tested message to the wire.
> Not the default; revisit after the first trace if needed.

---

## Part D — Tests (TDD per CLAUDE.md: failing test → impl → integration)

- **Python**: gate test — a `fine()` helper with the flag off emits nothing; on,
  emits a `[hudtrace]`-tagged line.
- **Swift**: a gate test that `hudLog(..., level: .fine)` is suppressed when
  `hudFineEnabled == false` and emitted when true (refactor `hudLog` to a
  testable form if needed).
- Existing `test_helpers.py` burst-suppression and `WireProtocolTests` parser
  tests must stay green (the new `fine=` args default to no-op; no wire change in
  the default path).
- *(Only if the `LOG` wire-verb alternative is taken)* add `encode_log`
  round-trip + `LOG|fine|on` → `.logLevel` parse + display-state-isolation
  tests.

---

## Part E — Capture & diagnose (the actual payoff — next session)

1. `./build.sh`, regenerate + `./deploy.sh`, rebuild HUD (`./restart.sh`),
   restart Ableton.
2. `update.py hudtrace on`. Reproduce **both** bugs deliberately:
   move across devices (incl. first/last), and toggle shift several times.
3. Collect both logs: Ableton (`./bin/tail_logs.sh`) +
   `/tmp/ableton_hud_debug.log`. Interleave by timestamp.
4. Read the evidence against the two suspects:
   - Bug 1: does `on_device_selected` fire (and at what nesting depth) inside
     `scroll_view`, with `source='selection'` → `EMIT_SILENT_AND_HIDE` → `HIDE`,
     before the `source='nav'` call no-ops on the same-device guard? Or is one
     of the app-view listeners the real HIDE source?
   - Bug 2: what is the real `MODE` send order on shift press vs release, and
     does a `HIDE` land between the mode burst and steady state? Does
     `DeviceState.isShiftMode` end up inverted vs. the physical button?
5. **Only then** write `hud-protocol-fix-plan.md`. Fix candidates to weigh
   against evidence (do not pre-commit): a `_nav_active` re-entrancy guard
   around the nav methods; correcting the `MODE` send ordering; the larger
   "fully stateless intent" redesign (drop the Python `dismissed` mirror, let
   Swift own visibility). The advisor already cautioned that naively replacing
   `EMIT_SILENT_AND_HIDE` with a pure-silent decision is a **regression** (a
   later `UPDATE` would patch stale slots into a HUD still showing the previous
   device) — so that path is explicitly out of scope until the trace justifies a
   safe alternative.

---

## Non-goals

- No behaviour change; no bug fix; no removal of `EMIT_SILENT_AND_HIDE` or the
  `dismissed` mirror in this plan.
- No new dismiss/visibility policy. Observation only.

## Files touched (instrumentation + toggle only)

- `templates/surface_name/surface_name.py` — `fine` flag + `hudtrace` command
- `templates/surface_name/modules/main_component.py` — `fine()` helper + nav /
  listener / mode trace points
- `templates/update.py` — `hudtrace` in command `choices`
- `source_modules/helpers.py` — `selected_device_changed` funnel trace (the
  Bug-1 crux), `Remote.hide/refresh_burst/device_update/send_mode`, `fine=`
  threading
- `source_modules/hud_visibility.py`, `hud_presenter.py`, `hud_client.py` —
  gated trace lines (`decide` event→decision, burst/hide paths, `_send` line)
- `ableton_hud/Sources/AbletonHUDCore/DeviceState.swift` — leveled fine logs on
  every `apply` case (injected fine-log closure to keep Core AppKit-free)
- `ableton_hud/Sources/AbletonHUD/UDPListener.swift`, `HUDOverlayManager.swift`
  — leveled `hudLog` + `HUD_FINE` toggle + show/hide/timer trace
- tests — Python `fine()` gate, Swift `hudLog` level gate
- *(LOG-verb alternative only)* `hud_protocol.py`, `WireProtocol.swift`,
  `hud_protocol.md`
