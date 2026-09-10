# Shift-summons-HUD + configurable idle timeout

Follows on from `ai-coding/done/hud-summon-only-plan.md`. Two independent but
mutually-reinforcing changes on the `show-hud-on: summon` surface (`ck_grid`).

## Requirements (agreed with user)

1. **Configurable idle timeout.** The Swift 7s idle-dismiss becomes a per-surface
   config value, `hud-idle-timeout: <seconds>`, **default 120**. Numeric only —
   no `off` sentinel; a very large value (e.g. `86400`) is "effectively never".
2. **Shift also summons the HUD.** The `type: shift` mode-button keeps being a
   held mode key (press → enter shift mode, release → base mode). *Additionally*,
   on the **press** it shows the HUD if hidden and repaints it if already shown —
   it never hides it (that's the "same role as the on/off key **if the HUD is
   off**" part; `hud_toggle` still hides-when-visible, shift does not).
   - **Release:** HUD **stays up**, repainting to base-mode labels (matches the
     toggle model; not a held spotlight). It then hides on idle timeout / mac
     input / `hud_toggle` / clip-view as today.

## Why the two couple (the non-obvious bit)

Python's `_sync_idle_dismiss` (`hud_presenter.py:308`) assumes *"`IDLE_DISMISS_
SECONDS` of silence ⇒ the Swift timer fired ⇒ mark the mirror `dismissed`."* The
timeout constant therefore has **one source of truth consumed on both sides**:
the Swift `armDismissTimer` window AND the Python idle-sync window. They must move
together or the mirror desyncs and the summoned HUD goes stale on the next
mode/selection event — which is exactly the shift-release repaint path change 2
introduces. So the configured value is threaded to both.

## Design

### A. Config → model → gen (idle timeout)

- `core_model.py`/`model_v2.py` `RootV2`: add `hud_idle_timeout: int =
  Field(120, alias='hud-idle-timeout')` next to `show_hud_on`. Not in the
  required-key check (`model_v2.py:492`) — it has a default. Validate `> 0` (a
  `GenError` on `<= 0`, pointing at the 86400 idiom).
- Thread through `to_gen()` (`model_v2.py:206` region) → `generate_code_as_
  template_vars` (`gen.py:120`, add `hud_idle_timeout` param, default 120) →
  `code_vars['hud_idle_timeout']` (plain int, `gen.py:270` region). Compositor
  override path (`gen.py:486`, `GenOverrides`) leaves it at the mapping's value
  (no forced override needed — only `hud_trigger` is forced).
- Template `main_component.py:106` region (SurfaceConfig construction): pass
  `hud_idle_timeout=$hud_idle_timeout`.
- `docs/mapping_file.md`: document the key + default.

### B. Runtime threading (Python)

- `helpers.py` `SurfaceConfig`: add `hud_idle_timeout: int = 120`.
- `helpers.py` `Helpers.__init__`: pass `hud_idle_timeout=config.hud_idle_timeout`
  into `HudPresenter(...)`, and hand it to the Remote so it reaches Swift:
  add `Remote.set_idle_timeout(seconds)` mirroring `set_autohide_on_input`
  (store on `self._hud_idle_timeout`, re-emit with LAYOUT in `init_layout` /
  `resend_layout` / `refresh_burst` for restart-resilience, send once now).
- `hud_client.py`: `send_idle_timeout(seconds)` → `encode_idle_timeout`.
  `NullHudClient` no-op.
- `hud_protocol.py`: `IDLE_DISMISS_SECONDS = 7` stays as the *fallback default
  constant name* but is superseded; add `DEFAULT_IDLE_TIMEOUT = 120` and
  `encode_idle_timeout(seconds) -> "IDLETIMEOUT|<seconds>"`.
- `hud_presenter.py`: `HudPresenter.__init__` gains `idle_timeout=DEFAULT_IDLE_
  TIMEOUT`; `_sync_idle_dismiss` compares against `self._idle_timeout` instead of
  the module constant `IDLE_DISMISS_SECONDS`.

### C. Runtime threading (Swift)

- `WireProtocol.swift`: new `case idleTimeout(Int)`; parse `"IDLETIMEOUT"` →
  `.idleTimeout(Int(fields[1]) ?? 120)`. Unknown/short lines fall through to
  `.unknown` (old-receiver safe).
- `DeviceState.swift`: `@Published var idleTimeoutSeconds: Int = 120`; in
  `apply`, `case .idleTimeout(let s): idleTimeoutSeconds = s`.
- `HUDOverlayManager.armDismissTimer`: read `DeviceState.shared.idleTimeoutSeconds`
  instead of the literal `7` (`HUDOverlayManager.swift:146`). No behavioural
  gate needed — always arms; the value alone controls the window.
- `hud_protocol.md`: document the `IDLETIMEOUT` message and update the "dismiss
  window" section (no longer a hard-coded 7 on either side; it's config-driven,
  default 120, single source = the `.nt` key).

### D. Shift summons the HUD

- Presenter: add `summon_for_mode(mode_name, device)` — identical to
  `refresh_for_mode` **except** it forces a non-suppressed burst (always
  `EMIT_BURST`): sets `_current_mode_name`, fires `ModeChange` for the mirror,
  then `emit_current_burst(device, suppress_hud=False)`. A non-suppressed
  `COMMIT` unconditionally clears Swift's `dismissed`, so this shows-if-hidden /
  repaints-if-shown and **never hides** — no new wire marker, no reliance on the
  flaky Python mirror. (Rejected `toggle()`: it hides-if-visible.)
- `helpers.py`: `refresh_hud_for_mode_summon(mode_name, device)` wrapper calling
  `self._presenter.summon_for_mode(...)`, mirroring `refresh_hud_for_mode`.
- Template `goto_mode(next_mode_name, summon=False)`: when `summon` is true call
  `refresh_hud_for_mode_summon` instead of `refresh_hud_for_mode`
  (`main_component.py:390`). Default `False` keeps release / switch-cycle /
  remote-mode-link callers byte-identical.
- Template `mode_button_listener`: on the **shift-press** branch
  (`value == 127 and in_base`, `main_component.py:425-426`) call
  `self.goto_mode(self.current_mode['next_mode_name'], summon=True)`. Release
  branch stays `goto_mode(self._first_mode)` (summon=False) → HUD stays up and
  repaints to base labels because the mirror is now `dismissed=False`. Switch-type
  branch unchanged.
- Scope: only the shift-press path forces summon. Under `selection`/`controller-
  nav` triggers ModeChange already shows, so forcing a burst there is harmless
  and consistent; no trigger gate needed.

## TDD order

1. `tests/test_hud_presenter.py`: `summon_for_mode` emits a non-suppressed burst
   even when `dismissed` (mirror starts summon-dismissed) and clears `dismissed`;
   contrast with `refresh_for_mode` staying silent. Implement `summon_for_mode`.
2. `tests/test_hud_presenter.py`: `_sync_idle_dismiss` honours an injected
   `idle_timeout` (e.g. 120) not the old 7 — with an injected clock, 90s idle
   does NOT sync, 130s does. Implement the `idle_timeout` param.
3. `tests/test_hud_protocol.py`: `encode_idle_timeout(120) == "IDLETIMEOUT|120"`.
   Implement encoder + `hud_client.send_idle_timeout` + `Remote.set_idle_timeout`
   (+ re-emit-with-LAYOUT test in `tests/test_helpers.py`).
4. `tests/test_show_hud_on.py` / generation test: `hud-idle-timeout` parsed
   (default 120 when absent; `<= 0` raises `GenError`); generated
   `main_component.py` carries the value into `SurfaceConfig`; `goto_mode`
   signature has `summon=False` and the shift-press call site passes
   `summon=True`.
5. Swift `Tests/WireProtocolTests`: `IDLETIMEOUT|120` parses to
   `.idleTimeout(120)`; malformed → `.unknown`; `DeviceState.apply(.idleTimeout)`
   sets `idleTimeoutSeconds`. Implement parser + DeviceState + armDismissTimer read.

## Verification

- `poetry run pytest`; `swift test`; `./build.sh` before commit (mention THIS
  plan in the commit message). `./ableton_hud/restart.sh`.
- Regenerate `ck_grid`; user redeploys + restarts Live. With `python update.py
  hudtrace` + `./bin/tail_logs.sh`:
  - Hold shift (HUD off) → HUD appears with shift-mode labels. Release → HUD
    stays, flips to base labels. Idle past the configured window (or press a mac
    key) → hides.
  - Set `hud-idle-timeout: 5`, regenerate → HUD hides ~5s after last traffic;
    `hud_toggle` re-shows on one press (idle-sync uses the same 5s).
  - Set a large value → HUD lingers indefinitely until mac input / toggle.

## Out of scope

- lc_parks compositor stays `selection`-triggered; it has no physical shift
  mode-button (mode driven remotely), so the shift-summon path doesn't apply. It
  inherits the `hud-idle-timeout` default (120) unless its config sets the key.
