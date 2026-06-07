# Two MIDI controllers, one composed HUD — shipped solution

Status: **implemented and working** (2026-06-07). This doc records the design we
actually shipped. An earlier "HUD composes two surfaces" (multi-source protocol)
design was built first, found too fragile (startup-order LAYOUT races, an
active-group selection bug, `show-hud-on` foot-guns, and silent `:5006` clobber
when the wrong surface was loaded), and replaced by what's below.

## Goal & constraint

Run a main controller (launch_control) and a small second controller (parks) at
once and see **both** in one HUD overlay, parks' controls beside launch_control's.

Hard constraint: an Ableton control surface binds to exactly **one** MIDI input
port, so one script cannot read both controllers' MIDI. Two surfaces must exist.

## Solution: primary drives the whole HUD; secondary forwards its region

Ableton's focused device is **global** (`appointed_device`), so both surfaces see
the same device. We exploit that:

- The **HUD is single-source** — exactly one process ever sends to it
  (`127.0.0.1:5006`). No source/group/order on the wire; the receiver is a plain
  single-state machine.
- A **composition config** (`live_surfaces/lc_parks/lc_parks.nt`) declares a
  PRIMARY mapping and a display-only SECONDARY mapping. Generating it emits
  **two namespaced surfaces into the composition folder**:
  - `ck_lc_parks__launch_control` — the **compositor** (primary). Owns
    launch_control's MIDI port, drives the entire HUD.
  - `ck_lc_parks__parks` — the **forwarder** (secondary). Owns parks' MIDI port;
    instead of sending to the HUD it forwards its resolved region to the
    compositor over UDP.
- The compositor merges the forwarded parks region into its own burst and emits
  one combined grid to the HUD (parks offset to the right).

### Why forwarding, not "bake the secondary into the primary"

Each controller resolves the focused device **differently** — a different
parameter window, mapping table, and button→param indices (e.g. on `Wavetable`
launch_control shows its params on the dials while parks shows `Osc 1 On`,
`Sub On`, … on its buttons). Forwarding lets each controller resolve *itself*;
the compositor just places the result. Baking would mean merging two different
resolution schemes/tables into one surface — that's where the bugs live.

### Why namespaced surfaces (the key robustness fix)

Every surface defaults to HUD `:5006`, and single-source means the last `COMMIT`
wins. If the secondary is generated as an ordinary surface it sends to `:5006`
and **silently clobbers** the compositor's combined burst. Worse, the same
output dir could mean two things (standalone → `:5006`, or forwarder → region
port). Emitting the secondary under a composition-namespaced name
(`ck_lc_parks__parks`, **no dashes — Ableton won't load those**) makes it
unambiguously the forwarder; it can never collide with a standalone build of the
same mapping.

## Implementation

### Config + dispatch
- `live_surfaces/lc_parks/lc_parks.nt` — `primary:` + `secondary:` (mapping +
  placement), optional `region-port:`.
- `ableton_control_surface_as_code/model_composition.py` — `CompositionRoot`
  (pydantic + nestedtext), `read_composition`, `is_composition_file`.
- `gen.generate()` dispatches on `is_composition_file` →
  `generate_composition()`.

### Compositor (`ck_lc_parks__launch_control`)
- `HudClient()` → `:5006` (the only HUD sender).
- Combined layout: `hud_layout.combine_layouts(primary_cells, secondary_cells)`
  offsets the secondary right (grid_col + width + gap) and bumps its wire indices
  past the primary's dial/button counts. Baked via `generate_code_as_template_vars(hud_cells_override=…)`.
- `RegionListener` (`source_modules/region_listener.py`) binds the region port;
  feeds `RegionState` (`region_state.py`), which caches the secondary's slots
  **remapped** to the combined wire space.
- The burst path (`Remote.refresh_burst`, `set_region_state`) appends the cached
  secondary payloads so the parks region rides along in the one combined burst.
- Forced `show-hud-on='selection'` (override): launch_control is `controller-nav`,
  which would suppress+HIDE on selection and race the parks-driven COMMIT (values
  flash then vanish). Selection shows cleanly; device-nav still shows.
- `Helpers.reemit_combined_burst` (wired as `RegionState` `on_commit`): a parks
  COMMIT re-emits a full combined burst for the current device, bypassing the
  trigger gate and the same-device guard. A parks UPDATE is relayed directly
  (remapped). A parks HIDE clears the region **without** re-bursting (a COMMIT
  would re-show the HUD and defeat auto-dismiss).

### Forwarder (`ck_lc_parks__parks`)
- `HudClient(host='127.0.0.1', port=<region-port>)` — same wire protocol, just
  pointed at the compositor instead of the HUD. Resolves its own region; bursts
  and live UPDATEs both flow for free.

### Single-source HUD protocol
- `source_modules/hud_protocol.py` ↔ `ableton_hud/.../WireProtocol.swift` — no
  source/group/order; `VERB|<payload…>`. Kept in lockstep.
- `DeviceState.swift` is a single state machine; `HUDView.swift` renders one
  combined grid (cells already carry the offset grid_col).

## Key files
- Config/parse: `live_surfaces/lc_parks/lc_parks.nt`, `model_composition.py`
- Codegen: `gen.py` (`generate_composition`, `_generate_surface`,
  `_region_setup_code`), `hud_layout.py` (`combine_layouts`/`offset_layout`)
- Runtime: `source_modules/region_state.py`, `region_listener.py`,
  `helpers.py` (`set_region_state`, region append, `reemit_combined_burst`),
  `hud_client.py`, `templates/surface_name/modules/main_component.py`
- HUD app: `WireProtocol.swift`, `DeviceState.swift`, `HUDView.swift`,
  `HUDOverlayManager.swift`

## Operating it
1. `poetry run python ableton_control_surface_as_code/gen.py live_surfaces/lc_parks/lc_parks.nt`
2. Deploy, restart Ableton.
3. In Preferences → Link/MIDI enable **only** `ck_lc_parks__launch_control` (on
   launch_control's port) and `ck_lc_parks__parks` (on parks' port). Do **not**
   also enable standalone `ck_launch_control_16` / `ck_parkstool_buttons` — they
   send to `:5006` and clobber.
4. Debug by tailing `/tmp/ableton_hud_debug.log` (every datagram the HUD
   receives). One `LAYOUT` + combined bursts, no competing no-dial bursts.

## Verification
- `poetry run pytest -q --ignore=tests/test_custom_mappings.py` (the lone
  `test_custom_mappings.py` failure is committed-broken on master, unrelated).
  Covers `test_composition.py`, `test_hud_layout.py`, `test_region_listener.py`,
  `test_hud_protocol.py`, `test_hud_client.py`, `test_gen.py` (composition).
- `swift test --package-path ableton_hud` — single-source round-trip + combined-grid.

## Out of scope / follow-ups
- One HUD panel = one composed pair at a time.
- Live parks feedback rides the forwarder, so it's live (not lagged).
- parks controller grid metadata (`under:`/`right_of:`) for tidy intra-region
  stacking is a separate concern from the merge mechanism.
