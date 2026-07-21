# Summon-only HUD: hidden unless asked for, auto-hide off-device

## Context

The HUD currently shows on every device selection (`show-hud-on: selection` in
`ck_grid.nt`) and keeps getting in the way in clip view and the browser. Goal
(TODO.md item 3): the HUD is **hidden most of the time** — it appears only when
*summoned* — and **auto-hides whenever anything other than a device is
focused**. This goes further than, and **supersedes**,
`hide-hud-in-clip-view-plan.md` (unimplemented; its `ClipViewChanged` design is
absorbed here).

**Agreed semantics (user):**
- Summon = `hud_toggle` button (already bound: `ck_grid.nt` grid-4:4::2) **and**
  explicit controller device-nav (`DeviceFocus(source='nav')`) — same override
  agreed in the clip-view plan. Mouse/track selection never shows it.
- Close = existing Swift idle auto-dismiss timer, OR focusing any non-device
  view (clip view, browser, Session↔Arranger doc switch), OR pressing
  `hud_toggle` again. Knob activity keeps it alive while it's up (existing
  PING/UPDATE timer resets).

## Existing machinery (reuse, don't rebuild)

- `source_modules/hud_visibility.py` — `HudVisibility` FSM is the single
  decision owner; events `DeviceFocus/ModeChange/UserToggle/ViewLeft/
  RegionCommit/ControlTouched`; `trigger` field already switches policy
  (`selection` vs `controller-nav`).
- `source_modules/hud_presenter.py` — `emit_burst(suppress_hud=…)` already
  implements silent bursts + `HIDE` (`EMIT_SILENT_AND_HIDE`); `toggle()`,
  `view_left()`, `refresh_for_mode()` route through the FSM.
- Template `templates/surface_name/modules/main_component.py` — three app-view
  listeners already send ViewLeft (doc-view switch, browser show, DeviceChain
  hidden). See memory: Browser listener only fires on show/hide toggle, not on
  focus-click; Detail listeners are reliable.
- Swift `DeviceState.swift` sticky `dismissed` flag + overlay auto-dismiss timer.
- `HudTrigger` enum in `ableton_control_surface_as_code/model_v2.py:68`,
  threaded through `gen.py` (`hud_trigger`, forced to `Selection` for the
  lc_parks compositor — compositor is explicitly out of scope and unaffected).

## Design

### 1. New trigger value: `show-hud-on: summon`

- `model_v2.py`: add `Summon = 'summon'` to `HudTrigger`; update the
  missing-key error text (line ~479) and `docs/mapping_file.md`.
- `ck_grid.nt`: `show-hud-on: selection` → `show-hud-on: summon` (update the
  comment block listing the options).

### 2. `hud_visibility.py` — policy under `trigger == 'summon'`

- `__init__`: `self.dismissed = (trigger == 'summon')` — hidden by default at
  surface startup.
- New event + state (absorbed from the clip-view plan):
  `@dataclass(frozen=True) class ClipViewChanged: visible: bool`;
  `self.clip_view_active = False`. `visible=True` → set flag, return `HIDE`;
  `visible=False` → clear flag, return `NOTHING` (leaving clip view never
  auto-re-shows). Include the flag in the `_fine` trace line.
- `_classify` under `summon`:
  - `DeviceFocus('nav')` → `EMIT_BURST` (summons, even in clip view).
  - `DeviceFocus('selection')` → `EMIT_BURST` only if currently shown
    (`not dismissed` — a visible HUD must repaint to the new device, never go
    stale) **and** `not clip_view_active`; otherwise `EMIT_SILENT_AND_HIDE`.
  - `ModeChange` → same rule as selection: repaint if shown, silent if hidden.
    (Today ModeChange always shows; under summon a mode press must not summon.)
  - `UserToggle` → unchanged flip (`EMIT_BURST` if dismissed else `HIDE`).
  - `ViewLeft` → `HIDE` (unchanged).
- `_classify` under `selection`/`controller-nav`: while `clip_view_active`,
  `DeviceFocus('selection')`, `ModeChange`, `RegionCommit` →
  `EMIT_SILENT_AND_HIDE` (the original clip-view-plan behaviour, kept for
  non-summon surfaces).

### 3. Presenter/helpers plumbing

- `hud_presenter.py`: `refresh_for_mode` currently ignores the decision — route
  it through the suppress branch (`emit_burst(suppress_hud=decision is
  Decision.EMIT_SILENT_AND_HIDE)`), mirroring `on_device_focus`.
- New `clip_view_changed(visible)` on the presenter → `decide(ClipViewChanged)`;
  on `HIDE` call `self._remote.hide()`. Mirror method
  `hud_clip_view_changed(visible)` on `Helpers` next to `hud_view_left`
  (helpers.py:528).

### 4. Template — fourth app-view listener

In `templates/surface_name/modules/main_component.py`, exactly following the
existing three: `add_is_view_visible_listener('Detail/Clip',
self._on_clip_view_changed)` in `_register_app_view_listeners` (~line 161) with
its own try/except; seed initial state right after registration from
`is_view_visible('Detail/Clip')`; matching removal in
`remove_app_view_listeners` (~line 212). Callback forwards **both** directions
to `hud_clip_view_changed`.

### 5. Swift — idle timeout becomes sticky

Today the overlay timer merely hides the panel; the next `UPDATE` (e.g. playback
automation) re-shows it. Under summon that resurrects the HUD uninvited. Change:
when the auto-dismiss timer fires (`HUDOverlayManager`), also set
`DeviceState.dismissed = true` (same sticky flag `HIDE` sets). Bursts still
clear it, so `selection`-trigger surfaces keep their current feel (next
selection re-shows); only "timer hid it, then automation traffic" changes — for
every trigger, deliberately.

**Known mirror drift:** Python's `dismissed` mirror doesn't learn about the
Swift timer. Fix on the Python side so `hud_toggle` doesn't need two presses
after an idle hide: `HudPresenter` records `last_activity` (any burst /
UPDATE / PING send); `toggle()` treats the state as dismissed when
`now - last_activity > DISMISS_WINDOW` (mirror the Swift timer constant — read
its value from `HUDOverlayManager` and define a shared constant note in
`hud_protocol.md`). Pure, unit-testable (inject a clock).

## TDD order

1. Failing `tests/test_hud_visibility.py` matrix for `summon`: startup
   dismissed; selection/mode silent while hidden; selection/mode repaint while
   shown; nav + toggle summon (incl. inside clip view); ClipViewChanged
   enter/exit rules; existing `selection`/`controller-nav` rows unchanged except
   the clip-view suppression.
2. Implement `hud_visibility.py`.
3. Failing `tests/test_hud_presenter.py` / `tests/test_hud_toggle.py`:
   mode-refresh honours silent decision; `clip_view_changed` plumbing; idle-aware
   toggle with injected clock. Implement presenter/helpers.
4. `tests/test_show_hud_on.py` + generation test: `summon` accepted end-to-end;
   generated `main_component.py` registers/removes the `Detail/Clip` listener.
5. Swift: `swift test` — add a `DeviceState` test that a timer-driven dismiss
   (expose as a method, e.g. `timerDismiss()`) sets `dismissed` and that
   `UPDATE` no longer publishes visibility; implement in
   `HUDOverlayManager`/`DeviceState`.

## Verification

- `poetry run pytest`; `./build.sh` before commit (mention this plan in the
  commit message). `swift test` + `./ableton_hud/restart.sh`.
- Regenerate `ck_grid`, user redeploys + restarts Live. With `hudtrace` on
  (`python update.py hudtrace`) and `./bin/tail_logs.sh`:
  - Start Live: HUD stays hidden. Click devices with the mouse: hidden
    (`decision=emit_silent_and_hide`).
  - Press `hud_toggle`: HUD appears with current device; press again: hides.
  - While shown, mouse-select another device: HUD repaints (no stale panel).
  - Device-nav on the controller: HUD appears, including while a clip is open.
  - Open a clip / the browser / switch Session↔Arranger while shown: HUD hides;
    closing the clip does not re-show it.
  - Leave it idle past the dismiss window during playback with automation: it
    hides and stays hidden; one `hud_toggle` press brings it back.

## Follow-ups / out of scope

- lc_parks compositor stays `selection`-triggered (forced in `gen.py:601`). Its
  *trigger* is unchanged, but the `Detail/Clip` gate is in the shared template so
  the compositor now suppresses its `RegionCommit` while a clip is open — the
  same clip-gate extension plan item 2 applies to every `selection` surface
  (benign: the parks region hides over a clip and reappears on the next region
  commit; the no-clip path — seeded `False` at startup — is byte-unchanged, so
  the known "HIDE-on-select races the parks COMMIT" hazard is not reintroduced).
- Mark `hide-hud-in-clip-view-plan.md` superseded by this plan (header note).
