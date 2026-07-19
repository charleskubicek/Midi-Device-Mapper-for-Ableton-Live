# Electron Mapping Editor UI — Plan

## Context

Users currently hand-write NestedText mapping files (e.g. `live_surfaces/grid/ck_grid.nt`) that bind controller coordinates to Ableton concepts, referencing a controller `.nt` file they already have (e.g. `controller_grid.nt`). This plan adds a visual Electron app in `./ui`: a canvas on the left renders the physical controller; users select controls (single, ranges, rows, grid regions), apply a mapping type (device, mixer, …), and configure details in an inspector on the right. The app writes new mapping `.nt` files that `gen.py` accepts, and can invoke generate/deploy.

**Confirmed decisions:** new-files-only authoring (no round-trip of hand-written files — comments would be lost); Electron + React + TypeScript + electron-vite; long-lived Python sidecar over JSON-lines stdio; full v1 coverage of all 8 mapping types + modes/shift modes. Undo/redo from day 1. Feedback/outputs blocks omitted in v1 (`parameter_mappings_file` exposed as a file picker only).

## Architecture

```
Electron main ── spawns ──► python -m ableton_control_surface_as_code.ui_api (poetry venv, cwd=repo root)
  │  fs access, dialogs, fs.watch on controller file, generate/deploy invocation
  │  JSON-lines protocol: {"id", "method", "params"} → {"id", "ok", "result|error"}
preload (contextBridge, nodeIntegration off) ──► renderer (React + zustand store)
```

- **Sidecar** (`ableton_control_surface_as_code/ui_api.py`, new): stdin read-eval loop. Methods: `ping`, `load_controller(path)` (→ resolved groups with `grid_row/grid_col`, light_colors, button_behaviour), `validate(mapping_text, mapping_dir)`, `parse_nt(text)`, `list_functions(dir)` (wraps the AST arity inspection in `model_functions.py:104-123`), `schema_info()` (exports `CLIP_ACTIONS`, transport/nav key lists so TS never hardcodes them), `generate(mapping_path)` (wraps `generate`, `gen.py:390`, capturing stdout/stderr).
  - Reuses `read_controller` (`model_v2.py:434`) and `build_validated_model` (`model_v2.py:450-473`) — pure, string-in, aggregates ALL problems via `ProblemAccumulator`.
  - **Trap:** `NestedTextError.terminate()` at `model_v2.py:426,442` raises SystemExit — `ui_api` pre-parses with `nt.loads` in its own try/except and wraps every dispatch in `except (SystemExit, Exception)` so the loop never dies. Missing controller file → structured problem, not a crash.
  - Main restarts the sidecar with backoff on exit; in-flight requests rejected; UI shows an "engine offline" pill (editing/saving still work; generate disabled).
- **Serialization is TS-side** (`ui/src/shared/serializer.ts`): the emitted NT subset is trivial (string scalars, dicts, lists, 4-space indent). Correctness enforced by golden tests: every serialized doc must survive sidecar `parse_nt` and Python `read_root`/`build_validated_model` acceptance. Python stays the parse authority; TS only writes.
- **Structured error locations** (small in-repo change): extend `ProblemAccumulator` (`gen_error.py:21`) entries to optionally carry `(mode_name, coord_string)`, threaded through by `ui_api` only; CLI output unchanged. This makes error→UI correlation reliable instead of regex-only.

## Document model (`ui/src/shared/document.ts`)

Discriminated union mirroring the schema; `id: nanoid` per mapping is UI-only, never serialized.

```ts
type CoordAtom = { form: 'row'|'grid-flat'; group; from; to }
              | { form: 'grid-cell'; group; gridRow; from; to };
interface CoordExpr { atoms: CoordAtom[]; refinements: ('momentary'|'mode-2'|'map_mode_absolute')[] }
// device: track selected|master|named; device selected|named; encoders/encoder-list
//   (range + exactly-one-of parameters|slots), on-off, button/button-list (slots incl. literal switchN)
// mixer: track + wells volume/pan/mute/solo/arm (single coord) + sends (ordered multi-coord)
// transport: play-stop, record-session, record-arrangement, loop, midi-arrange-overdub (verified model_transport.py:11-15)
// track-nav: left/right; device-nav: left/right/first/last/first-last
// functions: name→coord dict (+ builtin hud_toggle); parameter-pager: encoders/buttons × inc/dec
// clip: 24 actions from CLIP_ACTIONS via schema_info
interface MappingDocument { controllerPath; abletonDir; hud: 'on'|'device_only'|'off';
  showHudOn: 'selection'|'controller-nav'; modeButton?: {button; type: 'shift'|'switch'};
  modes: Mode[]; modeless: boolean; parameterMappingsFile?; remoteOn? }
```

`hud`/`show-hud-on` are non-optional in TS (set in the New File wizard, defaults `on`/`selection`) so the `read_root` hard-fail (`model_v2.py:416-424`) can't occur for app-authored files. `toggle` refinement is deprecated — never emitted or offered.

**coordBuilder** (`ui/src/shared/coordBuilder.ts`): selection (set of `{group, index}` cells, click-order preserved) → minimal `CoordAtom[]`:
- contiguous row run → `row-1:3-6`; rectangular grid region → one `grid-N:r::a-b` per grid row, comma-joined; full grid → flat `grid-1:1-16`; non-contiguous/multi-group → one atom per run in selection order.
- Inverse `cellsOf(CoordExpr, controller)` powers badges, occupancy, and clash pre-checks.
- Descending drags normalize ascending (grammar has no descending ranges); for order-sensitive wells (sends, slots, transport auto-fill) the inspector's reorderable pick-order list is the truth.

## Canvas (`ui/src/renderer/canvas/`)

SVG. Groups bucketed by `grid_row`, ordered by `grid_col` (same as `print_ascii_layout`, `gen.py:367` — positions come pre-resolved from the sidecar, no reimplementation of `under`/`right_of`). Glyphs: knob=circle, button=rounded square, slider=pill; tooltip shows coord + MIDI.

- **Selection:** click / shift-click (extend run) / cmd-click (toggle, non-contiguous) / marquee drag (rect region in grids, span in rows) / row-header = whole row / grid-header = whole grid / per-grid-row gutter handles. Status bar live-previews the computed coord string (teaches the grammar).
- **Badges:** mapped cells get type-colored fill + glyph (D, Mx, Fn, T, Cl…); clicking a mapped cell opens that mapping in the inspector.
- **Mode layers:** canvas shows the active mode tab; optional ghost overlay renders other modes' occupancy at low opacity. Mode-button cell has a permanent ring in all modes.
- **Clashes:** TS pre-check (cellsOf over current mode) → red outline instantly; sidecar clash detection (`model_v2.py:251`) is authoritative in the problems panel.

## Inspector (`ui/src/renderer/inspector/`)

Flow: select cells → type palette (types incompatible with the selection disabled with reason, e.g. "transport needs buttons") → mapping created pre-filled → inspector. Central `wellSpec` table declares `accepts: button|encoder|any` per well; pick-on-canvas dims non-matching cells. Every well also accepts typed coord strings (validated by TS parser) and exposes relevant refinement toggles (momentary for buttons, map_mode_absolute for encoders).

- **device:** track/device segmented controls; Parameters|Slots radio (exclusivity by construction); slots default `1-N`; "+ add range" converts `encoders`→`encoder-list` (same for buttons); "continue from N" helper for shift-band slots like `5-16`; live count badge "8 controls ↔ 12 slots ✗".
- **mixer:** five single-coord wells (type-enforced) + ordered `sends` list (drag to reorder = send order).
- **transport / track-nav / device-nav:** labeled button wells; multi-button selection auto-fills in spatial order with confirm.
- **functions:** name combobox fed by `list_functions` + `hud_toggle`; free text allowed with "not in functions.py" warning.
- **parameter-pager:** inc/dec wells ×2; 2-button selection pre-fills left=dec/right=inc.
- **clip:** grouped table of 24 actions (encoder/nudge/button kinds from `schema_info`) with "fill from selection" for matching kinds.

## Modes UX

Mode tabs above canvas; `+` on a modeless doc converts to modes and requires a mode-button before validation passes. Mode-button assignment is a button-only pick flow; `shift|switch` toggle with inline explanation; warn if `shift` with >2 modes. `on_color` swatch dropdown from controller `light_colors` (heuristic name→RGB chips). Rename inline (uniqueness checked, mirrors `_validate_mode_names`). Delete mode → confirm with "delete N mappings" or "move to other mode" (clash pre-check before commit); deleting to 1 mode offers modeless conversion. Mappings claiming the mode-button cell are flagged.

## Validation loop

Mutation → 400 ms debounce → serialize → sidecar `validate` → problems panel + inline markers; stale responses discarded via revision counter. Correlation uses the new structured `(mode, coord)` fields, falling back to regex-matching coords/mode names out of messages. TS pre-validation (instant): type constraints, intra-mode clashes, mode-button collisions, slots/params exclusivity + count mismatch, empty wells, duplicate mode names. Save allowed with warnings; **Generate disabled while sidecar errors exist**.

## Edge cases (handled)

- Rebind of an already-mapped control → conflict chip: keep-both (error) / steal (removes from other mapping, deletes it if emptied) / cancel. Never silent.
- Controller file changed on disk → `fs.watch` → reload → unresolvable coords marked **orphaned** (amber, "needs re-pick" panel); document preserved. Same flow for "switch controller file". Controller parse failure → degraded list view + retry.
- `ableton_dir`: wizard scans `/Applications/Ableton Live*.app`; existence warning, not a block.
- Missing `functions.py` → offer stub generation (Functions class with `def name(self):` per bound name); `hud_toggle` exempt. `hud: off` + `hud_toggle` → info note.
- Empty mapping auto-pruned (undoable toast); empty mode blocks save with a warning.
- Save dialog defaults to `live_surfaces/<stem>/<stem>.nt`; `controller:` re-relativized to save location.
- Generate → sidecar `generate` (requires saved + clean), output in console drawer. Deploy → main runs **`bin/deploy.sh`** (repo root; copies all surfaces — verified, there is no per-surface deploy.sh). Prompt to let the user restart Ableton themselves per CLAUDE.md.

## File layout

```
ableton_control_surface_as_code/ui_api.py     # new sidecar
ableton_control_surface_as_code/gen_error.py  # additive: structured problem locations
tests/test_ui_api.py                          # pytest
ui/
  package.json  electron.vite.config.ts
  src/main/{index,sidecar,files,generate,ipc}.ts
  src/preload/index.ts
  src/shared/{document,coords,coordBuilder,serializer,wellSpec,prevalidate,correlate,protocol}.ts
  src/renderer/  App.tsx  store/{documentStore,selection}.ts
    canvas/{Canvas,GroupCard,ControlGlyph,Marquee,Badges}.tsx
    inspector/{Inspector,Device,Mixer,Transport,Nav,Functions,Pager,Clip}Inspector.tsx + CoordWell.tsx
    modes/{ModeTabs,ModeButtonPicker,ColorSwatch}.tsx
    panels/{ProblemsPanel,ConsoleDrawer,NewFileWizard}.tsx
  test/ (vitest) + test/golden/ (doc.json ↔ .nt pairs)
```

## Milestones (each runnable)

1. **M1 Sidecar + skeleton:** `ui_api.py` (`ping/load_controller/parse_nt/validate`) + pytest incl. NestedTextError-survival; electron-vite scaffold; render `controller_grid.nt` read-only.
2. **M2 Document + serializer:** TS model, serializer, coord parser/printer; golden tests recreating `ck_grid.nt`/`ck_launch_control_16.nt` content, accepted by `read_root`. New File wizard → save a minimal mixer mapping that `gen.py` accepts.
3. **M3 Selection + simple types:** full selection interactions, coordBuilder, type palette, mixer/transport/nav/functions inspectors, badges, wellSpec.
4. **M4 Device/pager/clip + modes:** device inspector (lists, exclusivity, count checks), pager, clip table, mode tabs/mode-button/on_color/ghost overlay/delete-rename.
5. **M5 Validation loop:** debounced sidecar validation, structured-location change in `gen_error.py`, problems panel, correlate, TS pre-validation, orphaned-coords flow.
6. **M6 Generate/deploy + polish:** console drawer, `bin/deploy.sh` invocation, functions.py stubs, undo/redo hardening, shortcuts.

## Verification

- **Python:** `poetry run pytest tests/test_ui_api.py` — every error class (coord syntax, out-of-range, clash, dup modes, count mismatch), NT-syntax-error survival, generate smoke. Full suite + `./build.sh` before any commit (per CLAUDE.md).
- **TS:** `vitest` — serializer round-trips for all 8 types/modes/refinements; coordBuilder property tests (`cellsOf(build(sel)) ≡ sel` incl. rectangles, multi-group); prevalidate; correlate against captured real error strings.
- **Golden contract (CI):** for each golden doc, `nt.loads(ts_serialize(doc)) == expected_json` AND `build_validated_model` accepts it.
- **End-to-end:** author a recreation of `ck_grid.nt` in the app, save, run `gen.py` on it, diff generated surface behavior docs against the hand-written original's output.
