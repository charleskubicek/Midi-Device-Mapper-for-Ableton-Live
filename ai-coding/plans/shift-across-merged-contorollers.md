# Plan: Shift across merged controllers (lc_parks)

> Deliverable: this plan written to `ai-coding/plans/shift-across-merged-contorollers.md`
> (the existing repo file the user named, verbatim).

## Context

The `lc_parks` composition merges two physical controllers — **primary** (launch_control)
and **secondary** (parks) — into a single Ableton surface with one unified HUD. The
primary owns the HUD; the secondary forwards its resolved HUD region to the primary over
UDP (`region_port`, secondary → primary, one-way).

Today the primary has a shift mode (`main_mode` ↔ `shift_mode`); the **secondary has no
modes**. The goal: **holding shift on the primary also switches the secondary into its
shift mappings**, so the user gets shifted functions on *both* halves from one button, and
the HUD repaints both halves. The secondary is on its own MIDI port and can never see the
primary's shift note, so we must add a **reverse channel** (primary → secondary) carrying
the active mode name; the secondary then switches its own listeners and re-forwards its
region, which repaints the combined HUD.

Decisions (confirmed with user):
- Secondary modes are declared with a normal `modes:` block in the **secondary mapping**.
- Validation requires the secondary's modes to be **shift-type with identical mode names
  in the same order** as the primary.
- The secondary has **no usable physical mode-button** — it switches *only* on the
  forwarded signal (headless FSM).

## Design overview

```
User holds PRIMARY shift
  → primary mode_button_listener → goto_mode('shift_mode')
        → repaints primary half + sends combined burst
        → ModeSender: "SETMODE|shift_mode" --UDP--> secondary mode_port
  → secondary ModeListener.tick() → main_component.goto_mode('shift_mode')
        → swaps secondary's MIDI listeners to shift mappings
        → refresh_hud_for_mode → re-forwards region to primary
  → primary RegionState COMMIT → reemit_combined_burst → HUD repaints BOTH halves
Release → primary goto_mode('main_mode') → same path back.
```

A new UDP port (`mode_port`, primary → secondary) mirrors the existing `region_port`
plumbing. Mode **name** is forwarded (not a bool) so it stays correct under the
identical-names validation and generalizes past two modes.

## Workstreams

### A. Reverse mode-link transport (new)
- New `source_modules/mode_link.py`:
  - `ModeSender(host, port)` — tiny UDP line sender (model on `HudClient`'s socket
    setup). `send_mode(name)` emits one datagram.
  - `ModeListener(manager, target, port, name)` — non-blocking UDP receiver, a near-copy
    of `source_modules/region_listener.py` (`schedule_message(1, tick)` poll loop). On a
    `SETMODE|<name>` line it calls `target.goto_mode(name)`.
- Wire verb: add `encode_set_mode(name)` → `"SETMODE|<name>"` and a parser to
  `source_modules/hud_protocol.py`. Use a **distinct verb** from the existing boolean
  `MODE|shift|normal` (that one is secondary→primary and is ignored by `RegionState`;
  do not overload it). Both new modules are copied into every surface by the existing
  `source_modules/` copy step, same as `region_*`.

### B. Headless FSM in generated code (codegen)
The secondary declares `modes:` with **no `mode-button:`**. Current codegen breaks this in
several places — fix all of them so the with-button path is byte-for-byte unchanged:

1. `ableton_control_surface_as_code/model_v2.py` `ModeGroupWithMidi.fsm()` (~207):
   when `mode_button is None` but `has_modes()`, derive the FSM from `self.mappings`
   (each tuple's first element **is** the mode name) instead of `mode_button.on_colors`;
   `is_shift=True` for the composition secondary, `color=None`. Today it returns `[]`,
   which is why a button-less modes block generates an empty `_modes` dict → runtime
   `KeyError`.
2. `gen.py` `generate_code_as_template_vars` (~141–150): when there is no physical mode
   button, still emit the `_modes` state dict + `creation_template`, but **skip**
   `self.mode_button.add_value_listener(...)` and the `mode_button` element creation.
3. `gen.py` `setup_template` (27), `remove_listeners_template` (54): make the
   `self.mode_button` lines conditional on a physical button existing (the secondary has
   none — do **not** fall back to the default note-8/9 button, which would spray stray
   MIDI out the parks port on every shift).
4. `templates/surface_name/modules/main_component.py` `goto_mode` (211): guard the
   `self.mode_button.send_value(...)` calls (218–221) behind `if self.mode_button is not
   None`. **This is the critical landmine** — `goto_mode` runs on the secondary's
   reverse-channel-driven switch; an unguarded `send_value` is an `AttributeError`.

### C. Composition wiring (gen.py)
In `generate_composition` (`gen.py` ~416) and the `_generate_surface` injections
(mirror `_region_setup_code` ~403):
- Derive `mode_port` as a single source of truth (like `region_port`). Use a different
  offset (e.g. `generate_5_digit_number(comp_stem) + 4`) and **assert at generation time**
  it collides with neither `region_port` (`+3`) nor either surface's own udp/osc ports.
- Primary surface: inject `self._mode_sender = ModeSender('127.0.0.1', <mode_port>)`.
- Secondary surface: inject `self._mode_listener = ModeListener(self.manager, self,
  port=<mode_port>, name="...-mode")` so its `goto_mode` is driven remotely.
- `templates/.../main_component.py` `goto_mode`: after `self.current_mode = next_mode`,
  forward when present:
  ```python
  if getattr(self, '_mode_sender', None) is not None:
      self._mode_sender.send_mode(next_mode['name'])
  ```
  Add `_mode_sender` / `_mode_listener` as template vars defaulting to empty so
  standalone (non-composition) surfaces are wholly unaffected.

### D. Validation (model_composition / generate_composition)
Before generating, parse primary + secondary roots and accumulate readable `GenError`s
(follow the existing `ProblemAccumulator` pattern in `model_v2.build_validated_model`):
- Primary **must** declare a shift mode-button (`ModeGroupWithMidi.is_shift()`), else:
  "lc_parks primary must declare a `type: shift` mode-button to drive the secondary."
- Secondary **must** declare `modes:` whose names equal the primary's, same order:
  "secondary modes [a, b] must match primary modes [main_mode, shift_mode] (identical
  names, same order) so the forwarded shift maps 1:1."
- If the secondary declares its own `mode-button:`, reject it (user chose "purely driven"):
  "secondary must not declare a mode-button; its shift is driven by the primary."

### E. Make lc_parks usable (config)
Add a `shift_mode` mapping-set to the secondary parks mapping
(`live_surfaces/parks/ck_parkstool_buttons.nt`) with mode names matching the primary
(`main_mode`, `shift_mode`) and **no** `mode-button:`. The actual shifted parks bindings
are the user's to choose; include a minimal placeholder set and confirm content with them.

## Critical files
- `source_modules/mode_link.py` (new), `source_modules/hud_protocol.py`
- `ableton_control_surface_as_code/model_v2.py` (`fsm()`)
- `ableton_control_surface_as_code/gen.py` (`setup_template`, `remove_listeners_template`,
  `generate_code_as_template_vars`, `_region_setup_code` sibling, `generate_composition`)
- `ableton_control_surface_as_code/model_composition.py` (validation surface)
- `templates/surface_name/modules/main_component.py` (`goto_mode`, init injections)
- `live_surfaces/parks/ck_parkstool_buttons.nt`

## Risks / product notes
- **Poll latency (flag per CLAUDE.md / [[flag-product-contradictions]]):** the reverse
  channel polls via `schedule_message(1, tick)`, so there's a brief window after pressing
  primary-shift before the secondary's *MIDI mappings* swap. For the HUD this is
  invisible. For *control input*, a parks control hit in that window could land on the
  pre-shift mapping. For a held gesture this is likely masked by reaction time, but it is
  surfaced here rather than assumed away — verify manually (below).
- **Eventual-consistency repaint:** the primary's own `goto_mode` bursts first (secondary
  cache still on old labels); the secondary's subsequent COMMIT triggers
  `reemit_combined_burst` with the new labels. Acceptable, but note the two-step repaint.
- **`refresh_hud_for_mode` scope:** it re-emits *non-device* (static) labels. Confirm the
  parks shift mappings qualify (button/switch/functions do); if any are device-bound they
  repaint on the next `selected_device_changed`, not instantly.

## Verification
TDD — failing tests first, then implement:
1. **Golden / regression:** assert the primary's generated `main_component.py` is
   **byte-identical before/after the `fsm()` change** (the with-button path must not move).
2. **Unit (model):** `fsm()` yields correct mode data for a button-less multi-mode group;
   composition validation rejects name-mismatch, non-shift primary, and a secondary
   mode-button.
3. **Unit (transport):** `mode_link` round-trips `SETMODE|<name>`; `ModeListener` calls
   `goto_mode` with the parsed name; `hud_protocol` encodes/parses the new verb.
4. **Integration (codegen):** generate lc_parks; assert primary `main_component.py` has the
   `ModeSender` + `goto_mode` forward; secondary has the `_modes` dict, `ModeListener`, a
   guarded `goto_mode`, and **no** physical mode-button listener; `mode_port` ≠
   `region_port` and surface ports.
5. **Manual (deploy):** user redeploys + restarts Ableton (`./bin/tail_logs.sh`). Hold
   primary shift → both HUD halves switch to shift labels; release → revert. Then **hold
   shift and immediately press a parks control**, confirm it hits the shift mapping (the
   latency check).

Run `poetry run pytest` green before any commit (never commit on a failing test).

---

## Implementation status (2026-06-12)

**Built + unit-tested (mechanism complete, all 417 tests green):**
- `SETMODE|<name>` wire verb in `hud_protocol.py` (+ `SetModeMsg`, parse).
- `source_modules/mode_link.py`: `ModeSender` (primary) + `ModeListener` (secondary, drives `goto_mode`).
- Headless FSM: `ModeGroupWithMidi.fsm()` derives modes with no mode-button; `gen.py` emits the
  `_modes` dict + `goto_mode` without a physical button; template `goto_mode` guards
  `self.mode_button` and forwards `self._mode_sender.send_mode(name)`.
- Composition wiring: `mode_port` (= region base +4), `CompositionOverrides.mode_link` (data var
  `MODE_LINK`, role sender/listener), `validate_composition_modes` (primary must be shift,
  secondary no mode-button, identical mode names/order). Injection uses the existing **data-var**
  pattern, not the `_region_setup_code` string the draft above described.

**Currently DORMANT:** the parks secondary declares no modes, so `MODE_LINK = None` in both
surfaces and nothing instantiates. `test_composition_codegen.py` protects this no-regression path;
the active path is covered by `test_modes` / `test_composition` / `test_mode_link`.

**Constraint discovered — secondary shift content must be NON-device:**
- Device-slot HUD labels are effectively **mode-invariant**: `emit_burst` resolves `switch_entries`
  from a single static `_switch_slot_assignments`; modes vary only the **`mode_hud_labels` overlay**
  (`device_update` → `_overlay_labels`, helpers.py:604).
- A secondary mapping **different device params per mode** (switch1-4 vs switch5-8) would not repaint
  per mode AND trips a **pre-existing** codegen bug: the two modes' `code_switch_slot_assignments`
  concatenate without a comma → a secondary that crashes on load. Orthogonal join bug — flag
  separately, do not refactor here.
- **Verified-good path:** a `functions`-based (non-device) secondary shift mode populates
  `mode_hud_labels`, which `_overlay_labels` patches in on mode change → HUD repaints correctly.

**Open (needs user):** what the parks buttons should DO in shift_mode — cannot be "different device
parameters". Either `functions` mappings (HUD-correct) or leave parks single-mode (dormant).
