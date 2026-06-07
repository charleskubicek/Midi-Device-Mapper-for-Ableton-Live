# Two MIDI controllers, one composed HUD

## Context

The user runs a main MIDI controller (launch_control) and wants to use a small second
controller (parks) at the same time, seeing **both** in a single HUD overlay — the small
one's controls beside the main one's. Crucially this must be **configurable per topology**:
the user declares *which* active control scripts may merge (launch_control + parks, but
not ec4), and the secondary is a **cut-down** surface that only exports the buttons the
user wants on the HUD.

### Architecture decision
- **Merge in codegen (one surface):** *rejected* — an Ableton control surface binds to
  exactly **one** MIDI input port (Preferences > Link/MIDI is single-input per surface
  row; generated `surface_name.py` declares no port and relies on that binding). Two USB
  devices = two ports; the script can't see the second.
- **HUD composes two surfaces (chosen):** keep two normal surface scripts, each on its own
  port (no MIDI merge). Each emits the existing UDP HUD protocol to `127.0.0.1:5006`. The
  HUD tags senders by **source**, holds **per-source** state, and composes members of a
  declared **merge group** as side-by-side **regions** of one overlay.

### Confirmed constraints
1. **HUD is single-source today.** No sender id on the wire; `DeviceState` is a singleton
   — a second sender's `DEVICE`/`COMMIT` burst *wipes* the first's. This is the core bug to
   fix.
2. **Ableton's focused device is global** (`appointed_device`, `main_component.py:68`). Both
   selection-following surfaces emit bursts for the **same** device. That's fine — the
   secondary just shows whatever its own (cut-down) mapping binds for that device; both
   regions update live on device change.

### Config decisions (from the user)
- **All config lives in / near `live_surfaces/`.** Introduce a new shared
  **`live_surfaces/_Global/`** folder (also the future home for shared `functions.py` &
  infra per `ai-coding/plans/functions-and-code-infra.md` — out of scope here but the
  folder is the same idea).
- **`live_surfaces/_Global/merged_controllers.nt`** declares merge topologies: which source
  ids compose into one overlay, and their order/placement.
- **The cut-down secondary is an ordinary user-authored mapping** that only maps the
  buttons to export (e.g. `parks_buttons.nt`). That generated surface is what the user
  loads in Ableton for parks. **No special "export-only" codegen mode** — it's just a
  normal surface whose mapping happens to contain only buttons.
- **The HUD stays config-free.** The merge topology is consumed at **codegen time** and
  baked into each generated surface (its `source`, `group`, `order`). The HUD composes
  sources by the `group`/`order` they advertise on the wire — it never reads
  `merged_controllers.nt` or any live_surfaces path. ec4 is a *feedback sink*, not a HUD
  UDP source, so it's naturally excluded; group ids make exclusion explicit for any true
  HUD source you don't want merged.

## Design

### `merged_controllers.nt` (new, in `_Global`)
NestedText, parsed with the existing `nestedtext` + pydantic pattern (cf.
`model_controller.py`). Shape:
```
merges:
  - name: lc_parks           # group id advertised on the wire
    members:
      - source: main         # launch_control's hud_source
        order: 0
      - source: parks_btns   # the cut-down parks surface's hud_source
        order: 1
```
A surface's `source` defaults to its mapping-file stem, overridable via `hud_source:` in
the mapping. At generation time gen.py looks up the surface's source in the merges; if it's
a member it stamps `group` + `order`, else `group` defaults to standalone (group == its own
source, order 0) → renders as a lone region exactly like today.

### Wire protocol — source on every message; group/order on LAYOUT
Add **source id as field[1]** on **every** message (self-attributing under UDP
interleaving). `LAYOUT` additionally carries **group** and **order** (sent once; HUD
remembers per source).

| message | new form |
|---|---|
| LAYOUT | `LAYOUT\|<src>\|<group>\|<order>\|<n>\|(gr,gc,kind,count,start)×n` → `expected = 5 + n*5` |
| DEVICE | `DEVICE\|<src>\|<name>` (≥3) |
| SLOT / UPDATE | `SLOT\|<src>\|<kind>\|<idx>\|<name>\|<val>\|<min>\|<max>` (8) |
| COMMIT | `COMMIT\|<src>\|<count>` (3) |
| PING / HIDE | `PING\|<src>` / `HIDE\|<src>` (2) |
| MODE | `MODE\|<src>\|<shift\|normal>` (≥3) |
| PAGE | `PAGE\|<src>\|<4 counts>[\|<enc_label>\|<btn_label>]` (6 or 8) |

Defaults: `source='main'`, `group='main'`, `order=0`. Clean break (no back-compat branch);
all surfaces regenerated + HUD rebuilt together. **Keep `hud_protocol.py` and
`WireProtocol.swift` field arithmetic in lockstep** — a mismatch silently degrades to
`UnknownMsg` across the UDP boundary.

### HUD app (Swift) — multi-source compose by group
- Route every message by `src` into a **per-source** state (today's `DeviceState` fields,
  one set per source). `DEVICE`/`COMMIT` mutate only that source → no clobber.
- Group sources by their advertised `group`; render an `HStack` of per-source **region
  views** (today's grid extracted into a reusable view), members sorted by `order` →
  secondary sits beside primary. (One panel, one active overlay; standalone sources render
  as single-member groups.)
- One panel, one dismiss timer: any source's `PING`/`COMMIT` re-arms; per-source `HIDE`
  drops only that region; panel hides when no visible sources remain.

### Sender side (Python) — minimal
Each surface bakes its `source`/`group`/`order` into its `HudClient`; burst call sites in
`source_modules/helpers.py` are untouched.

## Phases (incremental, each independently testable)

### Phase 1 — Protocol source/group/order (TDD both sides)
- `source_modules/hud_protocol.py`: add `source` to every `encode_*`/`*Msg`; add
  `group`/`order` to layout; shift all field indices + length checks in `parse()`.
- `ableton_hud/Sources/AbletonHUDCore/WireProtocol.swift`: mirror exactly.
- Tests: `tests/test_hud_protocol.py` round-trip per message (source survives; bad length →
  Unknown); `ableton_hud/Tests/WireProtocolTests/` per-message round-trip + source/group/
  order extraction (`swift test` — target already exists).

### Phase 2 — Per-source HUD state (no clobber)
- Refactor `ableton_hud/Sources/AbletonHUDCore/DeviceState.swift`: extract per-device fields
  (`deviceName`, `dialSlots`, `buttonSlots`, `hudCells`, `pending*`, page/bank, `dismissed`)
  into `SourceState`; hold `sources: [String: SourceState]` + per-source `group`/`order`.
  `apply(message:)` dispatches to `sources[msg.source]` (created on first sight).
- Tests: interleave two sources, assert each retains its own slots (today's regression).

### Phase 3 — Compose regions by group + timer/HIDE
- `ableton_hud/Sources/AbletonHUD/HUDView.swift`: extract today's grid (lines ~25–32 build,
  ~84–155 render) into `SourceRegionView(state:)`; top-level = `HStack` over a group's
  members sorted by `order`.
- `ableton_hud/Sources/AbletonHUD/HUDOverlayManager.swift`: single panel + single dismiss
  timer; any source re-arms; per-source `HIDE` removes that region; hide when none visible.
- Manual verify (SwiftUI; no view-test harness).

### Phase 4 — Merge topology + codegen stamping (TDD)
- New `live_surfaces/_Global/` folder + `merged_controllers.nt`.
- New parser module (e.g. `ableton_control_surface_as_code/model_merges.py`) — pydantic +
  `nestedtext`, mirroring `model_controller.py` load style.
- Mapping schema (`model_v2.py`): optional `hud_source: str` (default = mapping stem).
- `gen.py`: locate `_Global/merged_controllers.nt` by walking up to `live_surfaces/`; look
  up this surface's source; compute `group`/`order` (standalone default); emit
  `hud_source`/`hud_group`/`hud_order` template vars from
  `generate_code_as_template_vars` (~line 173 return dict).
- `templates/surface_name/modules/main_component.py:52`:
  `self._hud_client = $hud_client_class(source=$hud_source, group=$hud_group, order=$hud_order)`.
- `source_modules/hud_client.py`: `HudClient.__init__(self, source='main', group='main',
  order=0, ...)`; prefix `source` in every `_send`; pass `group`/`order` in `send_layout`.
  `NullHudClient` signatures match.
- Tests: `tests/test_hud_merges.py` (parse topology, resolve group/order for a source) +
  extend `tests/test_gen.py` asserting the generated `main_component.py` carries the right
  source/group/order; `HudClient` unit test asserting emitted lines carry the source.

### Phase 5 — Cut-down secondary + end-to-end
- Author `live_surfaces/parks/parks_buttons.nt` (or similar): a normal mapping that maps
  ONLY the buttons to export, `hud_source: parks_btns`.
- Add the `lc_parks` merge to `_Global/merged_controllers.nt` with `main` + `parks_btns`.
- Generate both surfaces, deploy (`./deploy.sh`), restart Ableton, tail logs
  (`./bin/tail_logs.sh`); confirm one HUD shows launch_control + parks buttons side by
  side, both tracking the focused device. (User redeploys / restarts Ableton.)

## Reuse / key files
- Protocol is a pure mirrored pair: `source_modules/hud_protocol.py` ↔
  `WireProtocol.swift` — extend, don't rewrite.
- Sender wiring is one constructor line (`main_component.py:52`) + `HudClient`; burst call
  sites (`helpers.py refresh_burst` ~1023) untouched.
- HUD layout/wire-index allocation (`hud_layout.py`) is already per-controller, so each
  source's own LAYOUT is correct as-is; `LayoutCell` coords stay source-local (0,0-based) —
  side-by-side offset is the HStack's job, not a coordinate merge.
- Topology parsing reuses the `nestedtext` + pydantic pattern from `model_controller.py`.
- The cut-down secondary needs **no new code** — it's an ordinary buttons-only mapping.

## Verification
- **Python:** `poetry run pytest tests/test_hud_protocol.py tests/test_hud_merges.py
  tests/test_gen.py`. Generate both surfaces; diff emitted `main_component.py` for correct
  `source=`/`group=`/`order=`.
- **Swift protocol:** `cd ableton_hud && swift test` — round-trip + two-source no-clobber.
- **HUD view (manual):** run the HUD; with a small UDP script or the two deployed surfaces,
  send two sources in the same group and confirm side-by-side regions, live tracking,
  dismiss stays alive while either pings, per-source HIDE drops only its region; send a
  third source in a *different* group and confirm it does NOT merge in.
- **End-to-end:** deploy both, restart Ableton, navigate devices, confirm one HUD shows
  both controllers updating on selection change.

## Notes / flagged
- One HUD panel = one active composed group at a time. Multiple simultaneous merge groups
  on screen is out of scope (single overlay window today).
- Both regions show the **same device name** (global focus) — acceptable; can dedupe the
  header later.
- `_Global/` is shared infra also wanted by `functions-and-code-infra.md`; this plan only
  introduces the folder + `merged_controllers.nt`, not the shared-functions deployment.
