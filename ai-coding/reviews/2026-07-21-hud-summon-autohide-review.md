# Review: HUD summon + input-driven auto-hide (commit 83a699b)

Scope: everything in commit 83a699b (`hud-summon-only-plan`,
`hud-input-autohide-plan`, and the absorbed `hide-hud-in-clip-view-plan`) —
Python source_modules, template, codegen, Swift HUD app, scripts, docs, tests
on both sides. Working tree was clean at review time.

## Verdict

Technically sound overall, and the two big design moves are right:

- **`HudVisibility` as the single decision owner.** The event × trigger matrix
  is pure, table-driven, and unit-tested; the `[vis] decide` trace line is
  exactly the diagnostic this subsystem needed.
- **HUD-arbitrated TOGGLE.** Recognising that Python fundamentally *cannot*
  mirror true visibility (two autonomous Swift hide paths) and moving the
  toggle decision to the side that owns the truth is the correct call, and the
  wire design (marker + fresh burst, COMMIT decides) is clean.
- **Input monitor over view enumeration.** The spike-first approach paid off;
  `InputDismissPolicy` keeps the testable rule out of AppKit; lazy Accessibility
  prompting and the stable codesigning cert are both thoughtful touches.

But the commit left behind a cluster of dead code from the TOGGLE redesign, two
real behaviour bugs, and a handful of doc drift. Findings below, ordered by
severity. Items 1–2 and the cleanups are already planned in
[`hud-hide-on-empty-track-plan.md`](../plans/hud-hide-on-empty-track-plan.md).

## Bugs

### 1. Track-nav to an empty track never hides (CONFIRMED — the reported bug)

`Helpers.selected_device_changed` (`source_modules/helpers.py:214`) early-returns
on `device is None` *before* the visibility table runs. Controller track-nav
produces no mac input (monitor blind) and no device (Python hide skipped), so a
summoned HUD stays frozen on the previous track's device. Confirmed with the
user: repro is controller track-nav onto device-less tracks. Fix planned
(route the None case through `DeviceFocus(source)`; hide on
`EMIT_SILENT_AND_HIDE`; deliberate no-op under `selection`).

### 2. `reemit_combined_burst` discards its decision (lc_parks clip gate dead)

`hud_presenter.py:224`: `decide(RegionCommit())` returns
`EMIT_SILENT_AND_HIDE` while clip view is open — asserted in
`test_hud_visibility` — but the presenter ignores it and calls
`emit_burst(device, suppress_hud=False)`, which re-applies `EMIT_BURST` and
clears `dismissed`. The summon plan's follow-up ("the compositor now suppresses
its RegionCommit while a clip is open") is therefore not true in production.
The FSM-level test gives false confidence; there is no presenter-level test.
One-line fix, planned.

### 4. `TOGGLE` is undocumented in hud_protocol.md

The commit adds two wire messages but documents only `AUTOHIDE`. The doc calls
itself the full spec and still says "There are eleven message types" (actual
count with TOGGLE: fourteen). Add a `TOGGLE` section (emission point:
`Remote.send_toggle` immediately before the fresh burst; receiver arbitration:
`pendingToggle`/`toggleWasVisible`, COMMIT decides) and fix the count — or drop
the count sentence entirely so it can't rot again. Also pre-existing in this
file: the `PAGE` section is duplicated verbatim.

## Design risks to validate on hardware (flag, don't silently ship)

### 5. Mode/shift press resurrects a dismissed HUD (mirror drift)

After a toggle-off or an input-monitor hide, Python's mirror reads *shown*
(`emit_current_burst` applied `EMIT_BURST`; the monitor has no back-channel).
A shift/mode press within the idle window then classifies `ModeChange` →
`EMIT_BURST` and re-summons. `_sync_idle_dismiss` only covers the idle-timer
hide. On the grid surface shift is pressed constantly. If it annoys in
practice, the fix that eliminates the whole mirror class is a "repaint-only"
burst variant arbitrated by the HUD (show only if currently visible) — the
same trick TOGGLE used. Awaiting hardware verdict; out of scope of the current
fix plan.

### 6. Known gaps already documented in the plan (agreed, not re-litigating)

- Toggle on a device-less track emits a label-only burst (empty device name →
  `isVisible` stays false) — nothing shows.
- Knob-turn after an input-hide won't re-show (dismissed HUD ignores `UPDATE`);
  hinges on whether automation playback emits `UPDATE`s — unverified premise,
  check before changing.
- Clicking *on* a device (macro, bank arrow) still hides — accepted trade-off.

## Minor / theoretical

- **TOGGLE rides a separate datagram from its burst.** If the burst datagram is
  lost after TOGGLE arrives, `pendingToggle` stays armed and the next unrelated
  COMMIT wrongly hides. Near-theoretical on loopback UDP; sending TOGGLE inside
  the burst buffer (after `begin_burst`) would make arbitration atomic for free.
- **Idle-sync vs mouse-over pause.** Hovering the HUD pauses the Swift timer,
  but Python's `seconds_since_last_send` keeps counting — after 7s of hover,
  the mirror thinks *dismissed* while the panel is visible. Consequence is mild
  (a mode press goes silent instead of repainting). Not worth machinery.
- **Swift idle window is a hardcoded `7`** (`HUDOverlayManager.swift:146`) with
  a lockstep comment pointing at `IDLE_DISMISS_SECONDS`. Fine for two files;
  would not survive a third consumer — consider a shared constant in
  AbletonHUDCore if one ever appears.
- **`docs/mapping_file.md` wording:** says the app "prompts on first launch";
  actually the prompt is lazy — first `AUTOHIDE|1` arrival. Also names the
  permission "Input Monitoring / Accessibility"; the spike showed the operative
  grant for `NSEvent` key monitors is **Accessibility** (that's what the code
  requests). Worth tightening so future debugging trusts the doc.

## Simplification opportunities (dead code from the TOGGLE redesign)

All planned in `hud-hide-on-empty-track-plan.md` item 4:

- **`UserToggle` is dead in production.** `toggle()` no longer calls
  `decide(UserToggle())`. The FSM row survives only because tests use it to
  reach the "shown" state (use `DeviceFocus('nav')` instead). Remove event +
  row + dedicated tests.
- **`_sync_idle_dismiss` in `on_device_focus` is a no-op.** No `DeviceFocus`
  rule reads `dismissed` anymore (summon-selection became always-silent — the
  guarded comment above the call describes the *old* repaint-if-shown rule).
  Keep only the `refresh_for_mode` call site (ModeChange does branch on it).
- **Stale docstrings:** `hud_visibility.py:16` wiring status (drop UserToggle,
  add ClipViewChanged), `hud_presenter.py:9` (same), `_sync_idle_dismiss`
  docstring ("next UserToggle flips on a single press").
- **`view_gated`** is a pure alias of `clip_view_active` since the browser-gate
  removal; inline it.
- **`AbletonHUDApp.swift:32`** stale comment: `// SPIKE: log-only global input
  probe` — it's the production monitor.

## What's good (keep doing this)

- **Test discipline.** The FSM matrix tests read as a spec; the TOGGLE ordering
  test (`test_marker_precedes_burst`) pins the one ordering that matters; wire
  encode (Python) and parse (Swift) are tested symmetrically including
  malformed input (`AUTOHIDE|2`, trailing fields → `.unknown`); the codegen
  test asserts both presence of the clip listener *and* absence of the removed
  browser gate; the injected-clock activity tests cover the subtle cases
  (disabled send doesn't stamp, burst flush counts once).
- **Comments explain constraints, not mechanics** — e.g. why a suppressed burst
  must also send HIDE, why dial index alignment forbids squashing Nones, why
  TOGGLE captures visibility before DEVICE clears `dismissed`.
- **The codesigning scripts** solve the real TCC-reset problem minimally, warn
  instead of failing when the cert is absent, and document the one-time
  re-grant step. The OpenSSL-3-PKCS12 workaround note will save someone an
  hour.
- **Backwards compatibility on the wire**: old receivers parse both new verbs
  as `.unknown`; suppressed bursts stay byte-identical for non-summon surfaces.

## Test gaps (add with the fixes)

1. Helpers-level: `selected_device_changed(None)` hides under
   `summon`/`controller-nav`, no-ops under `selection` (bug 1 — failing test
   first).
2. Presenter-level: `reemit_combined_burst` honours the clip gate (bug 2).
3. Swift: Esc → sticky (bug 3): after Esc, an `UPDATE` must not re-show.
