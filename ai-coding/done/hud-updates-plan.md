# HUD updates — show all mappings, label buttons, refresh encoders on shift

## The three reported problems

1. **I need to see all visible mappings on the HUD.**
2. **Buttons currently have no words at all; encoders have.**
3. **Going into a shift mode should update *all* slots; encoder text is not updated.**

## Root-cause analysis

There are three distinct causes, all in the HUD burst-assembly path.

### Cause A — `hud: device_only` zeroes every non-device label

`live_surfaces/launch_control/ck_launch_control_16.nt` sets `hud: device_only`.
In `gen.py:165`, `HudMode.DeviceOnly` produces `mode_hud_labels = {mode: {}}` —
i.e. **no** static labels for mixer / functions / nav / transport cells. With no
labels, every non-device cell (all the buttons, and the mixer encoders in
shift_mode) renders blank. This is the direct cause of #2 ("buttons have no
words") and a contributor to #1.

→ Fix: change the config to `hud: on` so non-device cells get their labels.

### Cause B — device-slot assignments are global, not per-mode

`slot_assignments` (encoder→device-param) and `switch_slot_assignments`
(button→device-switch) are flattened across **all** modes in `gen.py` (the
`for name, code_model in mode_codes.items()` loop appends every mode's mappings
into one global list). `HudPresenter.emit_burst` then resolves that **global**
set against the focused device on *every* burst, regardless of the active mode.

Consequences:

- In `shift_mode`, encoders 1–16 are still resolved as device params (they were
  device-bound in `main_mode`), so the encoder cells show stale device-parameter
  names. The shift_mode mixer labels (`volume`/`pan`/`sends`) live in
  `mode_hud_labels[shift_mode]` but `_overlay_labels` only fills **EMPTY** slots
  — the device-resolved slots aren't empty, so the labels never apply. → cause
  of #3.
- Symmetrically, in `main_mode` the buttons `row-3:5-8` are `functions`, but the
  global `switch_slot_assignments` (switch1–4 from shift_mode's device mapping)
  resolve them as device switches, again blocking the function labels. → another
  facet of #2.

→ Fix: make the device slot/switch assignments **per-mode** so `emit_burst`
only resolves the encoders/switches that are device-bound *in the active mode*.
Everything else falls through to EMPTY and the mode's static labels overlay
correctly.

### Why per-mode (B) + labels-on (A) is sufficient

With per-mode device assignments, in any mode each wire slot is exactly one of:

- device-bound *in this mode* → live device param (from `slot_assignments_by_mode`)
- non-device-bound *in this mode* → static label (from `mode_hud_labels`)
- unbound *in this mode* → EMPTY sentinel

So `_overlay_labels` keeps its current "fill EMPTY only" semantics — no override
hack needed. Encoders unbound in shift_mode (1–4) correctly go blank instead of
showing stale device names.

## Implementation (TDD)

### 1. Codegen — emit per-mode assignment dicts (`gen.py`)

In `generate_code_as_template_vars`, while looping modes, capture each mode's
`merge.custom_parameter_mappings` and `merge.switch_parameter_mappings` into
`{mode_name: [tuple-strings]}` dicts (these are already per-mode; today they are
only flattened). Render them as Python dict literals into two new template vars:
`code_slot_assignments_by_mode`, `code_switch_slot_assignments_by_mode`. Keep the
existing flat vars (still used for the global `button_switch_count` paging math).

### 2. Template + config plumbing

- `templates/surface_name/modules/main_component.py`: build the two by-mode
  dicts and pass them into `SurfaceConfig`.
- `helpers.py` `SurfaceConfig`: add `slot_assignments_by_mode`,
  `switch_slot_assignments_by_mode` (default `None`).
- `Helpers.__init__`: forward them to `HudPresenter`. Keep the flat
  `switch_slot_assignments` for `button_switch_count`.

### 3. Runtime — `HudPresenter` selects the active mode's assignments

- Constructor accepts `slot_assignments_by_mode` / `switch_slot_assignments_by_mode`.
- `_active_slot_assignments()` / `_active_switch_slot_assignments()` return the
  current mode's list, falling back to the flat global list when the mode isn't
  in the dict (modeless surfaces, pre-`goto_mode`).
- `emit_burst` uses the active accessors instead of the raw flat lists.

### 4. Config change

`ck_launch_control_16.nt`: `hud: device_only` → `hud: on`.

### 5. Tests

- `test_hud_presenter.py`: an encoder device-bound in mode A but not mode B is
  resolved (in `real_params`) in A and absent in B; same for a switch. A
  shift-style mode with a dial label overlays the (now-empty) encoder.
- `test_gen.py` / codegen: the by-mode template vars are produced and contain
  the expected per-mode tuples.

### 6. Regenerate + build

Regenerate the launch_control surface so the committed generated code matches the
new template, then run `./build.sh`. User redeploys/restarts Ableton.
