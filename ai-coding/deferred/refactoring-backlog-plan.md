# Refactoring Backlog

Source: retrospective review of `a56737a..HEAD` (2026-05-04 → 2026-06-08, 40 commits,
~23.6k insertions). Each refactor below has its own motivation, design, steps, test
strategy, risk, and size. They are ordered for execution: cheap/safety items first,
structural items last, because the structural ones are easier once the noise is gone.

**Ground rules for every item**
- TDD loop per CLAUDE.md: failing test → change → integration check.
- Never commit with a failing test.
- Run `./build.sh` before and after each item so the quality dashboard records the delta.
- Items are sized S (≤1 session), M (1–2 sessions), L (multi-session, land in phases).

**Suggested order:** R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10
(dead code and loud failures first; god-class split and HUD state machine last —
they benefit from the smaller surface area the early items create).

---

## R1. Delete dead code from the churn window — size S

### Why
Leftovers from removed/superseded features actively mislead:
- `validate_exports` (`gen.py:93-103`) has no callers — leftover from the export
  experiment.
- `DeviceWithMidi.hud_cells` + the `HudCell` dataclass + the regex block that builds
  them (`model_device.py:15-21, 287-311`) have **no consumers**. They look like the
  source of HUD geometry but were superseded by `hud_layout.allocate_global_layout`.
  The `re.match(r'row-(\d+)', e.range_raw)` logic is exactly the kind of fragile
  coupling we don't want someone to "fix" later.
- `write_templates`' `functions_path` parameter (`gen.py:232`) is computed by the
  caller and never used.
- `ControlGroup.__init__` assigns `self.hud = hud` twice (`model_controller.py`).
- `_LEGACY_OSC_OUTPUTS` hardcodes a LAN IP `192.168.68.84` (`model_v2.py:130-133`) —
  config data living in code. Keep the back-compat shim but source the targets from
  one clearly-marked constant at the top of the file, or drop the second target if
  the remote box is no longer in use.

### Steps
1. Confirm zero references for each item (`grep -rn` across tracked files including
   templates — generated code references functions textually).
2. Delete `validate_exports`; delete `HudCell`, `DeviceWithMidi.hud_cells`, and the
   grid/regex block in `build_device_model_v2_1`; remove `encoder_slot_count`'s
   sibling only if unused (it IS used — keep).
3. Drop the `functions_path` param from `write_templates` and its caller.
4. Fix the duplicate `self.hud` assignment.
5. Decide on `_LEGACY_OSC_OUTPUTS` (ask: is 192.168.68.84 still live?).
6. Full test run; regenerate one surface (`live_surfaces/launch_control`) and diff
   the output directory against a pre-change generation — must be byte-identical.

### Tests
No new tests; this is deletion. The byte-identical regeneration diff is the gate.

### Risk
Low. The regeneration diff catches anything that was actually load-bearing.

---

## R2. Fail loudly instead of silently dropping/defaulting — size S

### Why
Two spots contradict the Phase-1 "accumulate problems, fail readably" work:
- `GeneratedCodes.merge` resolves two non-empty `custom_parameter_mappings` lists via
  `one_non_empty_array_or_none`, which **prints** "both arrays are non-empty, using
  first" and drops one (`gen_code.py:40-49`). A second `device` mapping with `slots:`
  in the same mode silently loses its slot assignments.
- `compute_grid_positions` caps at 20 iterations and silently leaves unresolved
  `under:`/`right_of:` references at `(0,0)` (`model_controller.py`). A typo'd row
  reference produces a wrong HUD layout with no error.

### Design
- `merge`: decide the real semantics. If two slot-bearing device mappings per mode is
  legal, concatenate. If not, raise `GenError(..., ErrorCode.SEMANTIC_VALIDATION)`
  naming both sources. (Recommendation: concatenate `slot_assignments`-derived lists;
  they're per-mapping data, not exclusive alternatives.)
- `compute_grid_positions`: after the resolution loop, if `remaining` is non-empty,
  report each unresolved group ("row-5: right_of: 9 — no row 9 exists") through the
  `ProblemAccumulator` when one is passed, else raise.

### Steps (TDD)
1. Failing test: mode with two `device` mappings each carrying `slots:` → assert both
   appear in generated `code_slot_assignments` (or assert the GenError, per decision).
2. Failing test: controller with `under: 99` → assert readable accumulated error.
3. Implement; remove `one_non_empty_array_or_none` if concatenation wins.

### Risk
Low–medium: if any existing surface accidentally relied on the drop, generation will
now fail loudly — which is the point. Regenerate all live_surfaces to check.

---

## R3. One `LayoutCell` type + a `SlotAddress` value type — size M

### Why
The wire-index space is the most fragile area in the codebase (41 call sites):
- `hud_protocol.py:23` declares `LayoutCell = Tuple[int, int, str, int, int]`
  (5 elements) while `encode_layout` two lines below unpacks **6** — the alias went
  stale when `section` was added.
- `hud_layout.py:20` declares a second, 6-element `LayoutCell`.
- `helpers.py` defensively slices `cell[:5]` in `_build_dial_payloads` /
  `_build_button_payloads`.
- Slot addressing is bare ints plus `(kind, wire_idx)` tuples; comments warn that
  `None` placeholder alignment is load-bearing (`helpers.py:855-875`).
- `hud_protocol.md` flags button-slot emission rules as "unstable / under review" —
  don't redesign behaviour on top of untyped tuples.

### Design
- One `LayoutCell` dataclass (frozen, slots) in `source_modules/hud_protocol.py`
  (the wire-format owner): `grid_row, grid_col, kind, count, start, section=0`.
  `hud_layout.py` imports it (codegen side may import from source_modules — gen.py
  already does for `encode_layout`).
- `SlotAddress` frozen dataclass: `kind: str ('dial'|'button'), index: int`. Use it
  for `mode_hud_labels` keys, `find_wire_index` returns, and `_overlay_labels`.
- Wire format unchanged: `encode_layout` consumes the dataclass; `parse` still
  produces it. The `repr()` baked into templates must stay `eval`-able inside Live —
  give `LayoutCell` a repr that reconstructs (dataclass default repr is fine since
  the class ships in `hud_protocol.py`, which is imported by `helpers.py`).
- Behaviour-neutral: no index semantics change.

### Steps (TDD)
1. Tests pinning current wire bytes for `encode_layout` (already exist in
   `test_hud_protocol.py` — extend if any cell shape is unpinned).
2. Introduce the dataclass in `hud_protocol.py`; keep tuple-acceptance shims
   (`LayoutCell.from_raw(tuple_or_cell)`) during migration.
3. Migrate producers: `allocate_global_layout`, `offset_layout`, `combine_layouts`.
4. Migrate consumers: `helpers._build_dial_payloads`, `_build_button_payloads`,
   `print_hud_layout`, `find_wire_index`, `Remote.init_layout`.
5. Check the template substitution path: `'hud_cells': repr(hud_cells_raw)` in
   `gen.py` → generated `main_component.py` → `Helpers(hud_cells=...)`. Generate a
   surface, import its `main_component` namespace-free? (can't import Live code —
   instead assert the substituted literal `eval()`s against a stub module providing
   `LayoutCell`). Simplest: keep the baked literal as **plain tuples** at the
   template boundary and convert via `LayoutCell.from_raw` inside `Helpers.__init__`
   — zero eval-context risk.
6. Delete the stale 5-tuple alias; remove `cell[:5]` slices.
7. Introduce `SlotAddress` for label keys and `find_wire_index`; update
   `collect_mode_labels`, `_overlay_labels`, `code_from_switch_slot_assignments`.
8. Deploy + restart Live once at the end (manual): HUD must render identically for
   launch_control and lc_parks.

### Risk
Medium: the repr/eval boundary into generated code. Mitigated by step 5's
tuples-at-the-boundary decision.

---

## R4. Replace `ClipMappings`' 22 parallel fields with a validated dict — size S

### Why
`model_clip.py:63-94` declares one Pydantic field per clip action — a hand-maintained
second copy of `CLIP_ACTIONS`. Adding a clip action requires editing two places that
must agree; `model_config = ConfigDict(extra='forbid')` is the only thing keeping
them honest.

### Design
```python
class Clip(BaseModel):
    type: Literal['clip'] = 'clip'
    mappings: Dict[str, str]

    @field_validator('mappings')
    def _known_actions(cls, v):
        unknown = set(v) - set(CLIP_ACTIONS)
        if unknown:
            raise ValueError(f"Unknown clip action(s): {sorted(unknown)} — "
                             f"expected one of: {', '.join(sorted(CLIP_ACTIONS))}")
        return v
```
`as_parsed_dict` becomes a one-liner over the dict. Error quality must not regress:
the unknown-key message should list valid actions (better than today's bare
`extra='forbid'` error).

### Steps (TDD)
1. Tests: valid mapping parses identically (compare `build_clip_model_v2` output
   before/after); typo `start-loop-inc` produces a message naming valid keys.
2. Replace the model; delete the 22 fields.
3. Regenerate the surface that uses clip mappings; diff output — identical.

### Risk
Low. NestedText gives `Dict[str, str]` naturally.

---

## R5. Invert the `core_model` → `model_device` dependency — size S

### Why
`core_model.RowMapV2_1.slots` does `from .model_device import
parse_continuous_slot_list` *inside the property* — the core module depending on a
leaf, hidden behind a deferred import. `gen.py` has four more function-level imports
(`hud_layout`, `model_composition`, `hud_protocol`, `HudTrigger`) signalling the same
cycle pressure. Deferred imports are now a tracked quality metric; this item drives
it down.

### Design
- New `ableton_control_surface_as_code/slots.py`: move `MODE_SLOT_NAMES`,
  `is_mode_slot`, `parse_slot_token`, `parse_continuous_slot_list` out of
  `model_device.py`. Both `core_model` and `model_device` import from it (leaf
  module, no internal deps).
- Hoist `gen.py`'s function-level imports to module top where no real cycle exists
  (check each: `model_composition` and `hud_layout` import nothing from `gen`).

### Steps
1. Move functions verbatim + re-export from `model_device` for any external callers
   (check `gen_code.py:9` imports `is_mode_slot` from `model_device` — repoint).
2. Hoist gen.py imports; run tests.
3. Quality gate: `deferred_imports` metric should drop.

### Risk
Low — mechanical.

---

## R6. Rename device-mapping "mode buttons" → "switches" — size S/M

### Why
Two unrelated concepts share the name "mode":
1. The surface FSM (`ModeButton`, `ModeDef`, `goto_mode`, mode_button template) —
   switches *which mapping set is active*.
2. Device-mapping switch cyclers (`ModeButtonEntry`, `ModeButtonMidiMapping`,
   `mode_button_maps`, `MODE_SLOT_NAMES`) — cycle a *device parameter* through
   values. `model_device.py:104` even comments `# 'switch1' or 'switch2'` on a field
   of a class called `ModeButtonMidiMapping`.
The config vocabulary already says `switch1..8` / `switch-list`; only the internals
disagree.

### Design
Internal renames only — **no config-file syntax change** (the `mode-buttons:` alias
in `DeviceEncoderMappings` stays accepted, documented as deprecated):
- `ModeButtonEntry` → `SwitchEntry`
- `ModeButtonMidiMapping` → `SwitchMidiMapping`
- `mode_button_maps` → `switch_maps`
- `MODE_SLOT_NAMES` → `SWITCH_SLOT_NAMES`, `is_mode_slot` → `is_switch_slot`
- `_mode_button_template` (gen_code) → `_switch_template`
Leave the FSM names untouched — "mode" then means exactly one thing.

### Steps
1. Mechanical rename (IDE/sed), one commit, no behaviour change.
2. Generated-output diff for a surface using switches: listener fn names embed
   `mb.slot` (`switch1`), not the class name — output should be identical. If any
   generated identifier changes, pin it first with a golden test, then decide.
3. Grep docs (`docs/`, `hud_protocol.md`) for stale terminology.

### Risk
Low, but verify generated identifiers don't shift (they shouldn't — names derive
from slot strings and midi coords).

---

## R7. `BurstSnapshot` — shrink the burst-path signatures — size M

### Why
- `Remote.device_update` takes **14 parameters** (`helpers.py:1110`).
- `Helpers.__init__` takes 12.
- `refresh_burst`'s `page_info` is "either a 4-tuple or a 6-tuple" (`helpers.py:1047`)
  — arity-sniffing at the callee.
- Feedback sinks receive positional args (`on_device_burst(device_name,
  dial_payloads, button_payloads)`) with no room to grow (EC4 ignoring buttons is
  already an interface wart).

### Design
Frozen dataclass in `hud_protocol.py` (it's payload, not transport):
```python
@dataclass(frozen=True)
class PageInfo:
    enc_page: int = 1; enc_total: int = 1
    btn_page: int = 1; btn_total: int = 1
    enc_label: str = ''; btn_label: str = ''

@dataclass(frozen=True)
class BurstSnapshot:
    device_name: str
    dials: List[Tuple[int, SlotPayload]]      # later: List[Tuple[SlotAddress, ...]]
    buttons: List[Tuple[int, SlotPayload]]
    page: PageInfo
    suppress_hud: bool = False
```
- `Remote.refresh_burst(snapshot)`; `device_update` builds a snapshot.
- Sink interface becomes `on_burst(snapshot)`; keep `on_device_burst` shim on
  `Ec4Client` for one release of generated surfaces, or regenerate everything at once
  (preferred — surfaces are regenerable artifacts).
- Helpers config: group the constructor's static config into a `SurfaceConfig`
  dataclass built in the template (`slot_assignments`, `switch_slot_assignments`,
  `parameter_mappings_raw`, `encoder_slot_count`, `hud_cells`, `mode_hud_labels`,
  `hud_trigger`) — the template then passes one object plus the two collaborators.

### Steps (TDD)
1. Pin current wire output for a full burst (exists in `test_hud_client.py` /
   `test_hud_protocol.py`; extend for the 6-tuple page path).
2. Introduce `PageInfo`; kill the arity sniff.
3. Introduce `BurstSnapshot`; migrate `Remote` + `Helpers` + `Ec4Client` + tests.
4. Update `main_component.py` template for the `SurfaceConfig` change; regenerate and
   redeploy all surfaces (user restarts Live).

### Risk
Medium: touches the template boundary → full regenerate/redeploy needed. Wire format
itself unchanged.

---

## R8. Compositor: inject data, not code — size M

### Why
`_region_setup_code` (`gen.py:403-413`) builds Python source as a string with a
comment warning that continuation lines must carry their own 8-space indentation.
`_generate_surface` has grown four override kwargs (`hud_client_args`,
`region_setup`, `hud_cells_override`, `hud_trigger_override`) — a composed surface's
behaviour can't be read from its mapping file or its template; it's spread across
codegen call sites.

### Design
Template contains the real (always-present, syntax-checked) wiring, gated on a data
constant:
```python
# main_component.py template
REGION_CONFIG = $region_config   # None | {'dial_offset': 16, 'button_offset': 8, 'port': 23456}
...
if REGION_CONFIG is not None:
    self._region_state = RegionState(self._hud_client,
        dial_offset=REGION_CONFIG['dial_offset'],
        button_offset=REGION_CONFIG['button_offset'],
        on_commit=self._helpers.reemit_combined_burst)
    self._remote.set_region_state(self._region_state)
    self._region_listener = RegionListener(self.manager, self._region_state,
        port=REGION_CONFIG['port'], name="$surface_name-region")
```
Same for the HUD client target: `hud_client_args` becomes
`HUD_TARGET = ('127.0.0.1', 5006)` substituted as a tuple. Collapse the four kwargs
into one optional `composition_overrides: CompositionOverrides` dataclass
(`hud_target, region_config, hud_cells, hud_trigger`) so `_generate_surface`'s
signature stops growing.

### Steps (TDD)
1. Golden test: generate lc_parks composition, capture both surfaces'
   `main_component.py`; assert the region wiring + forwarder target are present.
2. Move wiring into the template; replace string-building with the dict/None
   substitution.
3. Introduce `CompositionOverrides`; thread through `generate_composition`.
4. Regenerate lc_parks; behavioural check is the existing composition tests +
   a manual deploy.

### Risk
Medium: lc_parks is the only consumer and is race-sensitive; behaviour must be
byte-equivalent at the wire level. The golden-file diff is the gate.

---

## R9. Split `Helpers` into resolver / presenter / facade — size L (phased)

### Why
`source_modules/helpers.py` is 1,182 lines. `Helpers` owns: BOB/standard-bank/
fallback parameter resolution with M4L + Rack disambiguation; two name indices with
strict-vs-display semantics (`helpers.py:185-223`); group-selector listeners; page
math that couples encoder and button paging; enum cycling via `Live` module
introspection; switch semantics (min_max/cycle/pulse/enum/bool/function); HUD dismiss
intent; burst assembly; and track/device finding. The resolver half is pure logic
that is only testable today through fakes of the whole surface (see
`tests/test_helpers.py`, 1,179 lines, mostly setup).

### Design
Three units, all in `source_modules/` (copied into surfaces automatically by
`gen.py`'s glob):

1. **`param_resolver.py` — `ParameterResolver`** (pure; constructor takes data + a
   `log` callable, no manager/remote/sockets):
   - state: device table, name indices, banks, `_encoder_page`, `_button_page`,
     `_banks_per_page`, `_button_switch_count`
   - api: `focus(device)` (reset indices+pages), `resolve_encoder(device, c_idx)`,
     `resolve_switch(device, idx)`, `encoder_pages_count`, `button_pages_count`,
     `page_label_for`, `page_inc/dec(target) -> bool changed`,
     `group_selector_names(device)`, `has_user_defined_parameters`,
     `fallback_*`, `_lom_slot_payload` stays with switch resolution.
   - moves verbatim: `_build_device_table`, `_device_table_key`, M4L/RACK constants,
     `_load_bundled_banks`, `_ensure_name_index`, `_resolve_*`, `_standard_*`,
     `_first_standard_page`, `_enum_members`, `_resolve_live_enum_class`,
     `_enum_index_of`.

2. **`hud_presenter.py` — `HudPresenter`** (owns HUD intent + burst assembly):
   - state: `_hud_dismissed`, `_current_mode_name`, `_mode_hud_labels`, `_hud_cells`,
     `_hud_trigger`
   - api: `on_device_focus(device, source)` (suppress decision),
     `emit_burst(device)`, `refresh_for_mode(mode_name, device)`, `toggle()`,
     `reemit_combined_burst()`, `_emit_current_burst`
   - collaborates with `ParameterResolver` (read) and `Remote` (write).
   - R10 (visibility state machine) will later replace its inline suppress/HIDE
     branching; keep the seams aligned with R10's event names.

3. **`Helpers` (facade, stays in `helpers.py`)** — Live-coupled glue:
   - keeps every method the generated code calls, **unchanged signatures**:
     `device_parameter_action`, `switch_slot_action`, `selected_device_changed`,
     `refresh_hud_for_mode`, `toggle_hud`, `reemit_combined_burst`,
     `parameter_page_inc/dec`, `value_is_max`, `normalise`, `find_device`,
     `find_track`, `find_device_on_track`, `show_message`, `log_message`
   - keeps Live-API side effects: group-selector listener attach/teardown,
     `_log_device_focus`, `show_message` calls, actually writing `parameter.value`
     in `device_parameter_action` / `switch_slot_action` / `_cycle` / `_pulse` /
     `_toggle_bool_property` / `_cycle_enum_property` / `_call_device_function`.
   - `Remote` stays in `helpers.py` for now (R7 already slimmed its signatures).

   Phase 1 changes **no template line**: `Helpers.__init__` keeps its signature and
   constructs the two new objects internally.

### Steps (phased, each phase green + committed)
1. **Characterisation pass**: inventory `test_helpers.py` coverage against the
   resolver method list; add missing pins (paging across BOB+banks boundaries,
   M4L/Rack disambiguation, `min_max` on quantized params, display-name fallback).
2. **Extract `ParameterResolver`**: move methods verbatim; `Helpers` delegates
   (`self._resolver = ParameterResolver(...)`; thin pass-throughs). Tests green.
3. **Extract `HudPresenter`**: move dismiss/mode-label/burst-assembly; `Helpers`
   delegates. Tests green. Manual deploy check (HUD behaviour identical).
4. **Retarget tests**: new `test_param_resolver.py` / `test_hud_presenter.py` hitting
   the units directly with plain data (no manager fakes); `test_helpers.py` shrinks
   to facade integration tests.
5. **Tighten**: remove pass-through state duplication; quality gate should show
   `god_classes` and `helpers.py` LOC drop.

### Risk
Highest of the backlog — this code runs inside Live's embedded Python. Mitigations:
verbatim moves per phase, no behaviour edits in the same commit, deploy+restart
verification after phases 2 and 3 (`./bin/tail_logs.sh` for import errors — new
modules ride along automatically via the `source_modules` glob).

---

## R10. HUD visibility as one explicit state machine — size L (after R9)

### Why
"Is the HUD visible, and may this event show it?" is decided in six places:
1. the suppress branch in `Helpers.update_remote_parameters` (HIDE-on-suppressed,
   `helpers.py:901-914`),
2. `toggle_hud` (`helpers.py:953-961`),
3. `refresh_hud_for_mode` / `_emit_current_burst` (burst clears dismissal),
4. the three app-view listeners in the `main_component.py` template (doc-view,
   Browser, Detail/DeviceChain),
5. `RegionState`'s HIDE/PING rules (`region_state.py:61-74`),
6. the Swift side's sticky dismissed flag (cleared by DEVICE/COMMIT, set by HIDE).
Each carries a prose comment explaining a race it dodges (HIDE vs combined COMMIT,
PING-can't-resurrect, dismiss-direction inversion). The feature history shows the
cost: auto-dismiss → close button → `shift_dismisses_hud` → `hud_toggle` →
`show-hud-on` → compositor force-override, four redesigns of one concern.

### Design
Pure, table-driven decision object in `source_modules/hud_visibility.py`:
```python
class HudVisibility:
    """Mirrors the Swift sticky-dismiss flag. Single owner of show/hide intent."""
    def __init__(self, trigger):  # 'selection' | 'controller-nav'
        self.dismissed = False

    def decide(self, event) -> Decision: ...
```
- **Events** (frozen dataclasses or enum + payload): `DeviceFocus(source)` with
  source in `{'nav', 'selection'}`, `ModeChange`, `UserToggle`, `ViewLeft`
  (doc-view switch / browser opened / detail hidden), `RegionCommit`, `RegionHide`,
  `ControlTouched` (the per-listener ping).
- **Decisions**: `EMIT_BURST` (clears dismissed), `EMIT_SILENT_AND_HIDE` (the
  suppressed-selection path: data flows to OSC/feedback sinks, HUD gets HIDE),
  `HIDE`, `PING`, `NOTHING`.
- The full event×policy matrix is written out as a unit-tested table — the three
  race invariants become named test cases instead of comments:
  `test_ping_never_resurrects_dismissed`, `test_region_hide_does_not_reburst`,
  `test_burst_resyncs_dismiss_intent`.
- Consumers: `HudPresenter` (from R9) asks `decide()` and acts; the template's
  app-view listeners forward `ViewLeft` instead of calling `send_hide()` directly;
  `RegionState` forwards `RegionCommit`/`RegionHide` decisions through the same
  object on the compositor.
- **Compositor policy**: model the lc_parks force-to-`selection` override
  (`gen.py:450-459`) as an explicit policy flag (`combined=True`) in the table, so
  the rationale lives in a tested rule, not a codegen comment. Revisit whether the
  HIDE-race actually requires `selection` once `RegionCommit` is an event the
  machine sees — it may be expressible as "RegionCommit while trigger=controller-nav
  → EMIT_BURST", removing the override entirely. Flag to user before changing
  observed behaviour (per CLAUDE.md planning rule).

### Steps (TDD)
1. Write the decision-table tests first — encode today's exact behaviour, including
   the warts (suppressed-selection sends HIDE; mode change always shows).
2. Implement `HudVisibility`; wire `HudPresenter` to it (replace inline branches).
3. Move the template listeners to event-forwarding; regenerate + deploy.
4. Compositor: route `RegionState` decisions through it; then (separate commit,
   user-approved) attempt removal of the `hud_trigger_override` and verify on
   hardware that values no longer flash-and-vanish.

### Risk
High on step 4 only (cross-process timing observable only on hardware). Steps 1–3
are behaviour-preserving with the table as the spec.

---

## Verification matrix (applies across items)

| Gate | When |
|---|---|
| `poetry run pytest` green | every step |
| Byte-diff regenerated surfaces vs pre-change | R1, R3, R4, R6, R8 |
| `./build.sh` dashboard delta recorded | end of every item |
| Deploy + restart Live + `./bin/tail_logs.sh` clean | R3, R7, R8, R9 (phases 2–3), R10 |
| lc_parks composed HUD manual check | R8, R10 |

## Quality-gate tie-in

Each item should move a tracked metric (see `./build.sh` / `.quality/dashboard.md`):
R1 → `unreferenced_top_level_defs`, `dead_code`; R2 → (guard, no metric);
R3 → `wide_tuples`; R4 → `module LOC (model_clip)`; R5 → `deferred_imports`;
R6 → `concern naming` (manual); R7 → `long_param_functions`, `max_params`;
R8 → `deferred_imports`, gen.py LOC; R9 → `god_classes`, `helpers.py` LOC,
`cc_functions_over_10`; R10 → `concern_spread.hud`.
