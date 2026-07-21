# Shared functions file plan

## Status: IMPLEMENTED (2026-07-21)

Mechanism + migration done; build gate green (789 passed). Awaiting user
redeploy (CLAUDE.md: user restarts Ableton). Not committed.

- Shared source: `live_surfaces/shared/ck_functions.py` (was grid's — the
  canonical newest superset; the other three were stale subsets, verified by
  diff: grid is a strict content-superset).
- `functions_file:` added to 5 mappings (launch_control, parks, ec4, grid×2).
- Deleted 4 stale `functions.py` copies + 10 dead siblings (arranger/css_lib/
  parsers/sample_categories/synth_categories in launch_control+parks) + a stray
  Syncthing sync-conflict file. Generated dirs pruned of stale top-level
  siblings (they now come only from `modules/extensions/`).
- All 6 generatable surfaces materialise byte-identical `modules/functions.py`.
- `ec4/ck_ec4.nt` does NOT generate — PRE-EXISTING config clash (functions/
  device/pager share MIDI notes), confirmed against pristine HEAD; unrelated.
- Minor quality delta: `unreferenced_defs 0→1` (`extensions/parsers.py`
  `remove_prefix`) — latent dead code surfaced by the canonical swap; left as-is.

## Problem

`functions.py` is hand-maintained in four near-identical copies
(`live_surfaces/{launch_control,parks,ec4,grid}/functions.py`, ~1130 lines each,
~95% identical). Editing a function means editing it in four places.

## Why it happens (diagnosis)

Two distinct copies exist:

1. **Generated per-surface copy — necessary, keep it.** Ableton loads each
   surface as an isolated package with no shared `sys.path`. The loader
   hard-requires a *local* module named exactly `functions.py` with class
   `Functions`:
   - `templates/surface_name/surface_name.py:21` → `from .modules import functions`
   - `templates/surface_name/surface_name.py:87` → `(parent / 'functions.py').exists()`
   - `templates/surface_name/surface_name.py:325-326` → `importlib.reload(modules.functions)`
   - `templates/surface_name/modules/main_component.py:25` → `from .functions import Functions`

2. **Source copy — the real duplication, fixable.** `functions.py` is sourced
   *per-mapping* by the `*.py` glob at `gen.py:497` (copies every `.py` next to
   the mapping into `modules/`). It is the **last member of its helper cluster
   still sourced this way** — its deps (`parsers`, `sample_categories`,
   `synth_categories`, `css_lib`) were already promoted to the shared
   `source_modules/extensions/` package (ec4/grid import `from .extensions import
   parsers`; launch_control/parks still use byte-identical local siblings).

**User decision (2026-07-21):** the divergence between the four copies
(grid's `TrackNav`, launch_control/parks' `@hud_name` decorators, import style)
is accidental drift → collapse into **one shared superset file**.

## Design

Author one shared `ck_functions.py`; the generator materializes it as each
surface's `modules/functions.py` (authored name is free; generated name must
stay `functions.py` per loader constraint above).

### 1. Shared source file
- New: `live_surfaces/shared/ck_functions.py` — superset of the four:
  - include grid's `TrackNav` class,
  - keep all `@hud_name(...)` decorators (harmless on unmapped functions),
  - unify imports on `from .extensions import parsers, sample_categories, synth_categories`
    and `from .hud_name import hud_name` (both resolve from `source_modules/`,
    copied into every surface).
- Unused functions in the superset are inert: the AST lookup
  (`FunctionLookup.inspect_python_file`) only resolves functions actually
  referenced by a mapping.

### 2. Mapping config key
- Add optional `functions_file:` to the mapping `.nt`, resolved **relative to
  the mapping file**, mirroring the existing `controller:` /
  `parameter_mappings_file:` path-reference pattern.
- Backward compatible: if absent, fall back to `functions.py` next to the
  mapping (current behaviour).

### 3. Redirect the two coupling points
- `model_functions.py:162` — `FunctionLookup.inspect_python_file` should read the
  **resolved functions-file path**, not hardcoded `root_dir / "functions.py"`.
  Thread the resolved path through `build_functions_model_v2`.
- `gen.py` — copy the resolved functions file into `modules/functions.py`
  explicitly (materialize under the loader-required name). Keep the `*.py` glob
  for any other genuinely-local `.py`, but the shared functions file comes from
  the configured path, not the glob.

### 4. Cleanup (after green)
- Point all four mappings at `../shared/ck_functions.py`.
- Delete the four per-surface `functions.py` source copies.
- Delete the dead local sibling helpers in launch_control/parks
  (`parsers.py`, `sample_categories.py`, `synth_categories.py` — verified
  byte-identical to `source_modules/extensions/`).

## TDD loop

1. **Failing unit test** — `functions_file:` in a mapping points at a shared
   file; `FunctionLookup` resolves a function defined *only* in that shared file
   (fails today: looks next to the mapping).
2. **Failing integration test** — generate a surface with `functions_file:` set;
   assert `modules/functions.py` exists and equals the shared file contents; and
   a function from the shared file is wired into the generated listener code.
3. **Backward-compat test** — mapping with no `functions_file:` and a local
   `functions.py` still generates identically (regression guard).
4. Implement config parse → resolve → redirect inspection + copy. Green.
5. Cleanup step 4 above; regenerate all surfaces; confirm build + full suite.

## Open sub-decision (default chosen, easy to change)
Where the shared file physically lives. Default: `live_surfaces/shared/`
(outside `source_modules/` so its `source_modules` glob doesn't also copy it
under its own name; the generator copies it explicitly as `functions.py`).
Alternative: put it in `source_modules/` and special-case the rename — rejected
as more surprising.

## Risks
- A surface that mapped a function whose behaviour genuinely differed between
  copies would change. Mitigated: user confirmed drift is accidental; the
  superset keeps every function, and the cleanup regenerates + runs the full
  suite before commit.
- Loader still needs the class named `Functions` — unchanged, superset keeps it.
