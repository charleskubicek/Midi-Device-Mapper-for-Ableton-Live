# Plan: Single-owner HUD election for co-loaded control surfaces

## Context

**Problem.** When two independently-generated control surfaces are loaded in
Ableton Live at the same time, the floating HUD flashes on then instantly
hides. Root cause (confirmed across the Python sender and the Swift HUD app):

- The HUD protocol is **single-sender by design** — datagrams carry no source
  identity (`hud_protocol.md`: "The HUD has exactly one sender"). The Swift
  receiver (`ableton_hud/.../DeviceState.swift`) is one global state machine
  with no per-source arbitration; `HUDOverlayManager.swift` even has comments
  describing multi-source logic that was never implemented.
- Every standalone surface's `HUD_TARGET` is `None`, so both fall back to the
  same fixed sink `127.0.0.1:5006` (`templates/surface_name/modules/main_component.py:58-63`).
- Both surfaces install `application.view` listeners against **global** Live
  view state. Surface A's device burst shows the HUD; surface B — reacting to
  the same global view event — emits `HIDE`, which sets a *sticky* global
  `dismissed` flag and tears down the panel A just showed. Interleaved bursts
  also corrupt the shared pending buffers.

**Chosen fix.** These are genuinely independent setups (user confirmed), not a
pair meant for the existing `lc_parks` compositor. So we make the config
non-destructive by **electing a single HUD owner at runtime**: only one loaded
surface talks to `127.0.0.1:5006` at a time; the others go silent on the HUD.
This kills *both* failure modes by construction (no cross-surface `HIDE`, no
burst interleaving) with **no change to the Swift HUD app or the wire protocol**.

**How we access sibling surfaces at runtime (verified, not assumed).**
Disassembling Ableton's shipped `_Framework/ControlSurface.pyc` shows the base
class our surfaces subclass maintains a shared registry of live instances:
`CS_LIST_KEY = 'control_surfaces'`; `get_control_surfaces()` lazily creates and
returns `__builtins__['control_surfaces']` (a plain list); `publish_control_surface(self)`
is called inside `ControlSurface.__init__` and appends the real instance;
`self._control_surfaces` is a property returning that list; `disconnect()` removes
`self`. The registry lives on `__builtins__` — the single object shared across
every module in one CPython process — which both *proves* all Remote Scripts run
in one interpreter and gives us `self._control_surfaces`: a ready-made list of
the actual sibling instances whose Python attributes we can read directly. (This
is the same mechanism Ableton's own `AutoArmComponent` uses to coordinate across
surfaces.)

So we **enumerate siblings via the inherited `self._control_surfaces`** (proven
to hold live instances), and use Live's observable
`Live.Application.get_application().control_surfaces` only as the *trigger* to
re-run election when surfaces load/unload. Owner = the eligible sibling with the
smallest stable key (the baked-in surface name — deterministic across sessions,
unlike load order).

**How we identify HUD-enabled surfaces.** We tag each generated instance with a
flat marker attribute and read it back off the siblings:

- Each generated surface tags itself in `__init__`:
  `self._acsac_hud_enabled = $hud_mode_on`, a codegen boolean literal that is
  `True` only when HUD mode is on (`hud_mode != HudMode.Off` — the same
  condition gen.py already uses to pick `HudClient` vs `NullHudClient`).
- Election reads each entry defensively: `getattr(cs, '_acsac_hud_enabled', False)`.
  - Non-generated surfaces (Push, factory scripts) lack the attribute → `False`
    → excluded.
  - Generated surfaces with HUD **Off** (`NullHudClient`) → `False` → excluded.
    Critical: a Null surface must never win ownership and silence a real one.
  - Generated surfaces with HUD **on** → `True` → eligible.
- A flat boolean on the instance (not sniffing `main_component._hud_client`
  type) is deliberate: it's present the moment the instance exists, avoiding a
  load-order race where a sibling's `main_component` isn't built yet when the
  observer fires. `publish_control_surface` runs inside `super().__init__()`, so
  a sibling is briefly registered before it sets its marker — we set the marker
  first thing after `super().__init__()` to shrink that window, and election is
  self-correcting (re-runs on every `control_surfaces` change).

**Intended outcome.** Two (or more) generated HUD surfaces can be loaded
together with no flicker; the HUD shows the owner's mappings; a one-line notice
in Ableton's message pane explains that N HUD surfaces are loaded and which one
owns the HUD. Ownership re-elects automatically when surfaces load/unload.

## Design decisions (resolved)

- **Independent setups**, not a composition → election, not the compositor.
- **One owner** (smallest stable surface-name key among eligible siblings).
  Accepted cost: the non-owner controller
  shows nothing on the HUD while both are loaded.
- **Warning goes surface-side**, via `self.show_message()` — flagged product
  contradiction: the HUD is a separate macOS process and *cannot* write
  Ableton's message pane; only Python control-surface code can. Only the owner
  writes the message (the pane is a single global slot; two writers would
  clobber each other).
- No HUD-side multi-source detection in v1 — with election the HUD never sees
  two sources, so it could never fire. It would be redundant with election.

## Implementation

### 1. Gate the HUD client (`source_modules/hud_client.py`)
Add a runtime enable gate so a non-owner suppresses *all* HUD output (including
`HIDE`, which is the flicker trigger) from a single chokepoint:
- `HudClient`: add `self._enabled = True`; `set_enabled(self, flag)`; in
  `_sendto` return early when `not self._enabled`. (Gate in `_sendto`, not
  `_send`, so burst buffering still no-ops cleanly.)
- `NullHudClient`: add `set_enabled(self, flag): pass` to keep interfaces
  identical (generated code never branches on client type).

### 2. Election helper (new `source_modules/hud_arbiter.py`)
Keep the decision **pure and testable**, separate from Live wiring:
- `elect_hud_owner(surfaces, me) -> bool` — pure. Given the sibling list (from
  `self._control_surfaces`; may contain `None` and non-generated surfaces) and
  `me`, filter to eligible surfaces (`getattr(cs, '_acsac_hud_enabled', False)`
  true) and return whether `me` is the one with the smallest stable key
  (`getattr(cs, '_acsac_surface_name', '')`). Stable key, not list index, so
  ownership is deterministic across sessions/load order. Read siblings
  defensively with `getattr(..., default)` (a sibling may be a different
  generated version).
- `count_hud_surfaces(surfaces) -> (count, owner_name)` — for the warning text.
- A thin `HudArbiter` class holding a reference to the surface (`manager`) that:
  - `reelect()`: computes ownership, calls `hud_client.set_enabled(is_owner)`;
    if it just *became* owner, triggers a fresh full burst so the HUD reflects
    the new owner (reuse the existing `HELLO` refresh path:
    `main_component._remote.init_layout(...)` + `helpers.update_remote_parameters()`);
    if `count > 1` and owner, `manager.show_message(...)` + `log_message`.
  - `register()` / `unregister()`: add/remove the `control_surfaces` observer.

### 3. Wire into the surface (`templates/surface_name/surface_name.py`)
- Immediately after `super().__init__()`, tag the instance for sibling
  discovery: `self._acsac_hud_enabled = $hud_mode_on` (True only when HUD is on;
  a `NullHudClient`/HUD-Off surface must not win ownership and silence a real
  one) and `self._acsac_surface_name = "$surface_name"` (stable election key).
  Set these before any other init work so the window where a registered sibling
  is unmarked is minimal.
- Enumerate siblings via the inherited `self._control_surfaces` registry;
  observe `Live.Application.get_application().control_surfaces` only to trigger
  re-election on load/unload.
- After `init_modules()`, create `self._hud_arbiter = HudArbiter(self)` and
  `register()` its `control_surfaces` observer.
- **Bootstrapping / observer-reliability (advisor's landmine, twice):** `self`
  may not be in `control_surfaces` yet during its own `__init__`; a second
  surface loads after the first; and the observer method name
  (`add_control_surfaces_listener`) is a guessed Live API that cannot be
  verified without a running Ableton session -- if wrong, registration fails
  silently (logged + swallowed) and ownership never transfers, silently
  reintroducing the original clash. So correctness must **not** depend on the
  observer firing: `_hud_arbiter_tick` reschedules `reelect()` every 15 ticks
  (~1.5s), the same recurring-tick pattern already used by
  `update_main_component_with_selected_device`. The observer is a best-effort
  fast path (near-instant transfer when it works); the recurring tick is the
  guarantee (convergence within ~1.5s regardless). `HudArbiter._last_notice`
  gates the message-pane notice on change so the 15-tick loop doesn't spam it.
- In `disconnect()`, `self._hud_arbiter.unregister()` before the socket close /
  `super().disconnect()`.
- Verify the exact observer method name at implementation time
  (`add_control_surfaces_listener` / `remove_...` per Live's observable naming)
  using `./bin/tail_logs.sh`; confirm it fires when a sibling loads/unloads.

### 4. Generation (`ableton_control_surface_as_code/gen.py`)
- Add a `hud_mode_on` template var (`hud_mode != HudMode.Off`) → `$hud_mode_on`
  literal, alongside the existing `hud_client_class` computation (~gen.py:210).

## Tests (TDD — failing tests first)
- **Unit (pure):** `tests/test_hud_arbiter.py` — `elect_hud_owner` picks the
  eligible surface with the smallest `_acsac_surface_name`; ignores `None`
  slots and non-tagged surfaces; a HUD-Off (untagged/False) surface never
  wins; single surface always owns; order in the sibling list doesn't matter
  (name is the key, not position).
- **Unit:** `HudClient.set_enabled(False)` suppresses `send_*`/`send_hide`;
  `set_enabled(True)` restores; `NullHudClient.set_enabled` is a no-op.
- **Generation:** a generated surface contains the arbiter wiring, the
  `_acsac_hud_enabled` tag, and (for HUD-Off) the tag is `False`.

## Verification (end-to-end)
1. `poetry run pytest` green; `./build.sh` before any commit and report quality
   delta (per CLAUDE.md).
2. Generate two distinct HUD-enabled surfaces (e.g. `launch_control` and
   `ec4`), user deploys both and restarts Live with both selected in Prefs.
3. De-risk the registry first: on init, `log_message` the contents of
   `self._control_surfaces` and each sibling's `_acsac_hud_enabled` /
   `_acsac_surface_name`, to confirm empirically (in this Live version) that
   siblings appear and their markers are readable before relying on it.
4. `./bin/tail_logs.sh`: confirm each logs its elected role; the message pane
   shows the "N HUD surfaces loaded; <owner> owns the HUD" notice from the owner
   only. Confirm the HUD **shows and stays** (no instant hide) on device focus.
5. Toggle: switch devices/tracks and change views — HUD must not flicker.
   Deselect the owner surface in Prefs → remaining surface re-elects, takes
   over, and pushes a fresh burst (HUD reflects the new owner).
6. Regression: load a **single** surface — behaves exactly as today (it always
   owns; no spurious warning).

## Notes
- On implementation, also copy this plan to
  `ai-coding/plans/hud-owner-election-plan.md` (CLAUDE.md convention) and
  reference it in the commit message.
- No Swift/HUD-app or `hud_protocol.md` changes required.
