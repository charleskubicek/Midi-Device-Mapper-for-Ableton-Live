# Suppress HUD while editing in clip view (Detail/Clip)

> **Superseded** (2026-07-19, never implemented) by
> [`hud-summon-only-plan.md`](./hud-summon-only-plan.md), which absorbs the
> `ClipViewChanged` design and goes further (summon-only visibility).

## Context

Entering clip view already dismisses the HUD: clicking a clip flips `Detail/DeviceChain` to not-visible, `_on_detail_changed` (templates/surface_name/modules/main_component.py:250) fires `hud_view_left()` → sticky `HIDE`. But the dismissal doesn't survive bursts: while still in clip view, any `DeviceFocus` (selection poll — e.g. clicking a clip on another track), `ModeChange`, or `RegionCommit` classifies to `Decision.EMIT_BURST` in `source_modules/hud_visibility.py`, which clears `dismissed` and re-shows the HUD over the clip editor.

Goal: while `Detail/Clip` is visible, the HUD stays hidden — bursts still flow to OSC/LED sinks silently. The FSM already models this outcome as `Decision.EMIT_SILENT_AND_HIDE`.

**Agreed semantics** (confirmed with user):
- Explicit controller device-nav (`DeviceFocus(source='nav')`) **does** show the HUD even in clip view (clear user intent). Same for `UserToggle` (hud_toggle button).
- Leaving clip view does **not** auto-re-show; HUD stays hidden until the next normal trigger.
- Always-on behavior, hardcoded like the existing three view listeners — no `.nt` schema change.

## Design

Add clip-view state to the single decision owner, `HudVisibility`, fed by a fourth app-view listener.

### 1. `source_modules/hud_visibility.py`
- New event: `@dataclass(frozen=True) class ClipViewChanged: visible: bool`
- New state: `self.clip_view_active = False` in `__init__`.
- `_classify` changes:
  - `ClipViewChanged(visible=True)`: set `clip_view_active`; return `Decision.HIDE` (idempotent with the existing DeviceChain-driven hide, and covers cases where DeviceChain listener doesn't fire).
  - `ClipViewChanged(visible=False)`: clear `clip_view_active`; return `Decision.NOTHING` (stay hidden).
  - While `clip_view_active`: `DeviceFocus(source='selection')`, `ModeChange`, `RegionCommit` → `Decision.EMIT_SILENT_AND_HIDE` instead of `EMIT_BURST`. `DeviceFocus(source='nav')` and `UserToggle` keep their normal classification (nav override).
- Note: state mutation for `clip_view_active` happens in `_classify`/`decide` for this event (it's input state, not a Decision outcome — `apply()` stays purely about `dismissed`). Include the flag in the `_fine` trace line.

### 2. `source_modules/hud_presenter.py` + `source_modules/helpers.py`
- New plumbing method mirroring `hud_view_left()` (helpers.py:522) / `view_left()` (hud_presenter.py:200): e.g. `helpers.hud_clip_view_changed(visible)` → `presenter.clip_view_changed(visible)` → `self._visibility.decide(ClipViewChanged(visible))`; if the decision is `HIDE`, call `self._remote.hide()`.
- Verify the `ModeChange` path (`refresh_for_mode`, hud_presenter.py:~219) honors `EMIT_SILENT_AND_HIDE` — the DeviceFocus burst path already has a `suppress_hud` branch in `Remote.refresh_burst` (helpers.py:~645). If the mode path currently assumes `EMIT_BURST` unconditionally, route its decision through the same suppress branch.

### 3. Template `templates/surface_name/modules/main_component.py`
Follow the existing pattern exactly:
- `_register_app_view_listeners` (line 161): add `add_is_view_visible_listener('Detail/Clip', self._on_clip_view_changed)` in its own try/except. Also seed initial state right after registration: read `is_view_visible('Detail/Clip')` and forward it, so a surface (re)loaded while a clip is open starts suppressed.
- `remove_app_view_listeners` (line 212): matching `remove_is_view_visible_listener('Detail/Clip', ...)`.
- New callback `_on_clip_view_changed`: read `self._app_view.is_view_visible('Detail/Clip')`, `self.fine(...)` trace, forward both True and False to `self._helpers.hud_clip_view_changed(visible)` (both directions matter — False lifts suppression).

`source_modules/*.py` are copied verbatim into every generated surface, so no gen.py/model changes are needed.

## TDD order

1. Failing unit tests for the `HudVisibility` table (extend the existing hud_visibility tests in `tests/`): clip-view-enter hides; selection/mode/region bursts are silent while active; nav and toggle still burst; clip-view-exit is NOTHING and next selection burst shows again.
2. Implement `hud_visibility.py`.
3. Failing tests for presenter plumbing (`clip_view_changed` calls hide on HIDE; mode refresh goes silent when suppressed), then implement helpers/presenter.
4. Template change + any generation snapshot/integration test that asserts the generated `main_component.py` registers the `Detail/Clip` listener.

## Verification

- `poetry run pytest` (all tests, per CLAUDE.md).
- `./build.sh` before committing; report quality change.
- Regenerate ck_grid: `poetry run python ableton_control_surface_as_code/gen.py live_surfaces/grid/ck_grid.nt`; then let the user run `./deploy.sh` and restart Live (per CLAUDE.md, user redeploys).
- Live check via `./bin/tail_logs.sh`: open a clip, click clips across tracks — expect `[vis]` trace lines showing `decision=emit_silent_and_hide` and no HUD; press device-nav on the controller — HUD appears; close clip view — HUD stays hidden until next selection.

## Known facts / caveats

- `'Detail/Clip'` is a valid identifier for `add_is_view_visible_listener` (verified empirically in Live 12.4.1: `available_main_views()` includes it; Detail listeners fire reliably).
- `Detail/Clip` and `Detail/DeviceChain` flip together when switching detail panes; listener fire order between the two callbacks is not guaranteed — both handlers are directional and idempotent, so order doesn't matter.
- Swift side needs no change: as long as Python never emits a `DEVICE`/`COMMIT` burst while suppressed, the sticky `dismissed` flag in `DeviceState.swift` keeps the overlay hidden; `EMIT_SILENT_AND_HIDE` sends `HIDE` plus data to non-HUD sinks only.
