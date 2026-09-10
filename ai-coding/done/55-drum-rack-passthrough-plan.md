# Drum-rack MIDI pass-through

## The problem

With **no** control surface loaded, pressing a Grid button while a drum rack is
focused does exactly what we want: the pad **sounds** *and* Live **selects** it.

With `ck_grid` loaded, nothing sounds. Commenting out the `pads:` block in
`ck_grid.nt` did not fix it, and could not have:

```
button:
    range: grid-1:1-16     # <- still claims notes 36-51
    slots: 1-16
```

`grid-1:1-16` is notes 36–51 (`C1-DS2`, `controller_grid.nt` group 1) — which is
exactly the drum rack's visible-bank pad range, hence the perfect native
behaviour. Those buttons are still bound as the device *switch* slots, so they
still have value listeners, so `_Framework` still forwards their MIDI to the
script and Live never routes it to the track.

## The mechanism (verified against Live 12's `_Framework`)

`InputControlElement.install_connections` (`_Framework/InputControlElement.py`):

```python
if self.script_wants_forwarding():
    self._is_being_forwarded = install_forwarding(self)

def script_wants_forwarding(self):
    return not self._suppress_script_forwarding and self._input_signal_listener_count > 0 \
        or self._report_input
```

So an element is consumed by the script only while it is forwarded. Two facts
make `suppress_script_forwarding` the right lever:

1. Its setter calls `self._request_rebuild()`, i.e. Live re-runs `build_midi_map`
   and drops the element from the forwarding registry.
2. `request_rebuild_midi_map` is injected `.everywhere()` by
   `ControlSurface.__init__`, so the plain `ConfigurableButtonElement(...)`
   constructions in generated `setup_controls()` do get a real rebuild callback
   (not the `nop` default).

Unforwarded, unmapped MIDI then reaches the track input — subject to **Track**
being ticked for the Grid's input row in Live's MIDI preferences.

Setting `suppress_script_forwarding` is preferred over removing value listeners:
it is orthogonal to the mode FSM's listener bookkeeping, and it survives a mode
switch (re-adding listeners while suppressed leaves
`script_wants_forwarding()` False on both sides of `_listeners_update`, so no
spurious rebuild).

## Why this must be per-mode

`ck_grid.nt` binds `grid-1:1-16` twice:

- `main_mode`: device switch `button:` slots 1-16 — this is the row we want to
  release to Live.
- `shift_mode`: `sequencer: range: grid-1:1-16` — the 16-step drum sequencer,
  which only works *because* the script consumes those notes.

A surface-wide "release everything when a drum rack is focused" would kill the
step sequencer, and (if widened to grid-4, notes 59–74) would stranding the user
on the drum rack with no working shift/nav buttons. So pass-through is declared
**per mode**, and re-asserted on every mode change.

Knobs are deliberately *not* candidates: CC messages don't play pads, so passing
them through buys nothing and costs the `velocities:` per-step editing.

## Config

New optional key, valid inside a mode (and at root, where it becomes the default
for modes that don't declare their own — which is also how a modeless mapping
declares it):

```
modes:
    -
        name: main_mode
        drum-rack-passthrough: grid-1:1-16      # or a list of ranges
        mappings: ...
```

Accepts a single coord string or a list of them. Ranges use the normal
`encoder_coords` syntax and resolve through `controller.build_midi_coords`.

Semantics: *while the focused device is a drum rack and this mode is active,
these controls are released — the script stops consuming their MIDI and every
mapping on them is inert.* Otherwise they behave exactly as mapped.

## Implementation

1. **`model_v2.py`**
   - `ModeDef.drum_rack_passthrough: Optional[List[str]]` (alias
     `drum-rack-passthrough`), normalised from `str | list[str]`.
   - `RootV2` / `RootV2ModesOrModeless`: same key at root, `List[str]`, used as
     the per-mode default and threaded through `empty_with_one_mode`.
   - `ModeGroupWithMidi.drum_passthrough: Dict[str, List[MidiCoords]]`, resolved
     in `read_root_v2` via `controller.build_midi_coords(parse_coords(...))`.
   - No clash-check change: these coords are *not* new bindings.

2. **`gen.py` / `generate_code_as_template_vars`** — emit
   - `drum_passthrough_by_mode`: `{mode_name: [element_attr_name, ...]}` using
     `MidiCoords.controller_variable_name()`.
   - `drum_passthrough_default_mode`: first mode name, for the pre-`goto_mode`
     and modeless cases where `self.current_mode` is unset.

3. **`templates/surface_name/modules/main_component.py`** — store both, and add:

   ```python
   def sync_drum_passthrough(self):
       active = self.drum_rack.is_active()
       wanted = set(self._drum_passthrough_by_mode.get(mode_name, ())) if active else set()
       for name in self._drum_passthrough_all:      # union across modes
           element = getattr(self, name, None)
           ...
           element.suppress_script_forwarding = (name in wanted)
   ```

   Idempotent by construction (assign the boolean, never toggle) — the
   `_Framework` setter no-ops when unchanged, so no rebuild storm from the
   1.5s `update_selected_device` poll.

   Call sites: `goto_mode` (mode change), `on_device_selected`,
   `on_selected_track_changed`, `_on_track_devices_changed` (device focus), and
   `update_selected_device` (the existing 1.5s poll, as the self-healing
   backstop — same rationale as the HUD-arbiter tick).

4. **`live_surfaces/grid/ck_grid.nt`** — `drum-rack-passthrough: grid-1:1-16`
   under `main_mode`; drop the now-superseded commented-out `pads:` block and
   explain why (native pass-through does selection *and* audition, which
   `pads:`/`select_pad` never could).

## Tests (TDD order)

Runtime suppression itself is not unit-testable outside Ableton (it is one
attribute assignment on a `_Framework` element). Everything up to that boundary
is:

1. `model_v2`: a mode declaring `drum-rack-passthrough` resolves to the right 16
   `MidiCoords`; string and list forms are equivalent; root-level applies as the
   default; absent key -> empty.
2. `gen`: `drum_passthrough_by_mode` maps mode name -> the right element attr
   names, and only for the declaring mode.
3. End-to-end: the drum-rack fixture surface builds and the rendered
   `main_component` body still parses (`ast.parse`), with the dict present.

## Known gaps (deliberate, flagged)

- **HUD labels.** While pass-through is active the grid-1 cells still show their
  device switch-slot labels, but the buttons play pads. Making the HUD show pad
  names in that state is a separate change.
- **Rebuild latency — needs a Live session to settle.**
  `request_rebuild_midi_map` is asynchronous, so a press in the gap lands on the
  old routing. Releasing controls is harmless (a late pad press just does what it
  did before). *Reclaiming* is the case to check: grabbing shift with a drum rack
  focused un-suppresses grid-1, and until the rebuild lands a step tap still plays
  the pad rather than toggling the step — and `step_event` acts on the release
  edge, so that tap is lost, not delayed. Most scripts (Push's note/session mode
  switch) rely on this same call and feel instant, so one tick is the expectation;
  confirm against `[drum] pass-through mode=shift_mode released=0` in the logs. If
  it does drop taps, the fix is a mode-entry grace period, not a different lever.
- **Live MIDI prefs.** Pass-through only produces sound if **Track** is enabled
  for the Grid's input port row.
