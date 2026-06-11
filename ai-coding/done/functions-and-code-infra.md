# Functions & Code Infrastructure Plan

## Context

Generated surfaces increasingly depend on shared Python beyond the templated
runtime. A user's `functions.py` (e.g. `live_surfaces/ec4/functions.py`) imports
helper modules (`parsers`, `sample_categories`, `synth_categories`) and bundles
large reusable classes (`ClipOps`, `Patterns`, `Arranger`, `Bounce`,
`NameGuesser`, etc.) inline. There is no shared home for these, and no guarantee
they get deployed into Ableton alongside the generated surface.

Separately, output-publishing code has accreted inside `main_component.py` and
`helpers.py`: the OSC client classes live in `helpers.py`, the OSC targets are
hard-coded in the `main_component.py` template, and the `remote_on: bool` flag is
a blunt on/off switch that cannot describe *what* to publish or *where*.

This plan does four things:
1. Create a shared, auto-deployed **extensions** package for reusable
   `functions.py` dependencies.
2. Extract the **OSC client** out of `helpers.py` into its own module
   (`osc_client.py`), mirroring `hud_client.py` / `ec4_client.py`.
3. Generalise `remote_on` into an **`outputs:` list** in config so a surface
   declares which output sinks it publishes to and with what targets.
4. Fix the **deploy path** so nested module subdirectories (extensions, and OSC)
   actually reach Ableton.

The unifying idea: the HUD wire protocol, OSC, and EC4 readouts are all the same
kind of thing — *output sinks driven off the parameter-update path*. This plan
moves toward a single, config-declared list of those sinks. The only hook today
is "publish parameter outputs"; the `outputs:` list is the seam where future
hook types can be added later.

---

## Folder layouts (before → after)

### `source_modules/` (the canonical copied-into-every-surface tree)

Before:
```
source_modules/
├── __init__.py
├── clip_actions.py
├── ec4_client.py
├── helpers.py            # OSCClient/OSCMultiClient/NullOSCClient live at the bottom
├── hud_client.py
├── hud_protocol.py
├── listener.py
├── nav.py
├── region_listener.py
├── region_state.py
└── pythonosc/            # vendored OSC lib
    └── …
```

After (§1 adds `extensions/`, §2 adds `osc_client.py`):
```
source_modules/
├── __init__.py
├── clip_actions.py
├── ec4_client.py
├── osc_client.py         # NEW (§2) — OSCClient/OSCMultiClient/NullOSCClient moved here
├── helpers.py            # Remote stays; OSC classes removed, re-imported from .osc_client
├── hud_client.py
├── hud_protocol.py
├── listener.py
├── nav.py
├── region_listener.py
├── region_state.py
├── pythonosc/
│   └── …
└── extensions/           # NEW (§1) — shared library for user functions.py imports
    ├── __init__.py
    ├── parsers.py
    ├── sample_categories.py
    ├── synth_categories.py
    ├── arranger.py
    └── css_lib.py
```

### User surface dir `live_surfaces/ec4/` (source the user edits)

Before — extension files sit loose next to the mapping and are picked up by the
`glob('*.py')` copy in `gen.py:365`:
```
live_surfaces/ec4/
├── ck_ec4.nt              # mapping (gains `outputs:`, drops `remote_on`)
├── ec4.nt                 # controller
├── functions.py           # `from . import parsers` (private copies)
├── parsers.py             ─┐
├── sample_categories.py    │  moved INTO source_modules/extensions/
├── synth_categories.py     │
├── arranger.py             │
├── css_lib.py             ─┘
└── generate.sh
```

After — the private extension copies are gone; `functions.py` imports the shared
package instead:
```
live_surfaces/ec4/
├── ck_ec4.nt
├── ec4.nt
├── functions.py           # `from .extensions import parsers, sample_categories, …`
└── generate.sh
```

### Generated + deployed surface `…/ck_ec4/modules/`

After regeneration the new modules appear automatically (extensions/ via the
copytree branch in `gen.py:368-373`; osc_client.py as a plain file copy):
```
ck_ec4/
├── __init__.py
├── ck_ec4.py
├── deploy.sh             # §1 fix: recursively copies the whole modules/ tree
└── modules/
    ├── main_component.py # imports OSC classes from .osc_client now
    ├── helpers.py
    ├── osc_client.py     # NEW
    ├── ec4_client.py
    ├── hud_client.py
    ├── functions.py      # imports from .extensions
    ├── …
    ├── pythonosc/        # already deployed via hardcoded paths today
    │   └── …
    └── extensions/       # NEW — MUST be reached by deploy.sh (§1 blocker)
        ├── __init__.py
        ├── parsers.py
        ├── sample_categories.py
        ├── synth_categories.py
        ├── arranger.py
        └── css_lib.py
```

The `extensions/` box is exactly what the current `deploy.sh` would miss — it
enumerates `modules/*.py` + `modules/pythonosc/**` only. Hence the §1 recursive-copy fix.

---

## 1. Shared extensions package — `source_modules/extensions/`

**Goal:** a versioned in-repo library that every generated surface receives
automatically, so a user's `functions.py` can `from .extensions import parsers`
instead of carrying private copies.

- Create `source_modules/extensions/` as a package (`__init__.py` + modules).
  Seed it by moving the currently-private helpers out of the ec4 surface dir:
  `parsers.py`, `sample_categories.py`, `synth_categories.py`, `arranger.py`,
  `css_lib.py` (all currently loose in `live_surfaces/ec4/`). Note: `functions.py`
  only imports `parsers`, `sample_categories`, `synth_categories` today — verify
  whether `arranger.py` / `css_lib.py` are actually imported before moving; drop
  any genuinely-dead file rather than promoting it into the shared library.
- `gen.py` already recursively copies `source_modules/*` into the surface's
  `modules/` (`gen.py:368-373`, the `shutil.copytree(..., dirs_exist_ok=True)`
  branch), so `extensions/` lands at `modules/extensions/` with **no gen.py
  change required**.
- Update `live_surfaces/ec4/functions.py` imports from `from . import parsers`
  (etc.) to `from .extensions import parsers`. Leave the large inline classes
  (`ClipOps`, `Patterns`, `Arranger`, …) in `functions.py` for now; migrating
  those into `extensions/` is a follow-up, not part of this round.

**Critical deploy fix (blocker):** `templates/deploy.sh` hard-codes the copy of
`modules/*.py` plus exactly `modules/pythonosc/` and `modules/pythonosc/parsing/`.
A new `modules/extensions/` subdir would **not** be deployed. Change `deploy.sh`
to recursively copy the entire `modules/` tree (e.g. `cp -R modules/ "$DEST/"` or
a `find`-based copy) instead of enumerating known subdirs. This also future-proofs
any further nested packages. Verify the generated `deploy.sh` for the ec4 and
launch_control surfaces after regeneration.

Files: `source_modules/extensions/` (new), `templates/deploy.sh`,
`live_surfaces/ec4/functions.py`.

---

## 2. Extract the OSC client — `source_modules/osc_client.py`

**Goal:** OSC sending becomes its own module like `hud_client.py` and
`ec4_client.py`, rather than living at the bottom of `helpers.py`.

- Move `NullOSCClient`, `OSCClient`, `OSCMultiClient` (`helpers.py:1187-1214`)
  into a new `source_modules/osc_client.py`. Move the `SimpleUDPClient` import
  and the `ArgValue` type they depend on along with them (check `helpers.py`
  imports for `from .pythonosc... import SimpleUDPClient` and `ArgValue`).
- `Remote` stays in `helpers.py` (it is the output orchestrator and is coupled to
  the burst/HUD logic). It already receives the OSC client by constructor
  injection, so it only needs the import to resolve.
- Update imports:
  - `templates/surface_name/modules/main_component.py:8` — currently
    `from .helpers import Helpers, OSCMultiClient, OSCClient, Remote, NullOSCClient`.
    Split to keep `Helpers, Remote` from `.helpers` and import the OSC classes
    from `.osc_client`.
  - If `helpers.py` references the OSC classes internally, re-import them there
    from `.osc_client` to avoid breaking existing references.

Files: `source_modules/osc_client.py` (new), `source_modules/helpers.py`,
`templates/surface_name/modules/main_component.py`.

---

## 3. Generalise `remote_on` → `outputs:` list

**Goal:** replace the boolean + hard-coded IPs with a declarative list of output
sinks, modelled on the existing `feedback:` mechanism.

Currently OSC targets are hard-coded in the template
(`main_component.py:48-52`, `127.0.0.1` and `192.168.68.84:5005`) and gated by
`$remote_on`. Replace with config-driven construction.

**Config (`.nt`):**
```
outputs:
    -
        type: osc
        targets:
            - { host: 127.0.0.1 }
            - { host: 192.168.68.84, port: 5005 }
```

**Model (`model_v2.py`):** mirror `FeedbackSinkDef` (`model_v2.py:95-106`):
- Add an `OutputSinkType` enum (`osc`) and an `OutputSinkDef` model with `type`
  and type-specific fields (for `osc`: a `targets` list of `{host, port=5005}`).
- Add `outputs: List[OutputSinkDef] = []` to both `RootV2` and
  `RootV2ModesOrModeless`, and thread it through `buildRootV2`
  (`model_v2.py:114, 130, 144-148`).
- **Back-compat:** keep `remote_on` parseable. If `outputs` is empty and
  `remote_on` is `true`, synthesise the legacy default OSC sink (localhost +
  the existing LAN target) so current configs keep working. Mark `remote_on`
  deprecated in docs.

**Codegen (`gen.py`):** following the `feedback_sink_ctors` pattern
(`gen.py:171-176`), render an `osc_clients` template var — a comma-separated list
of `OSCClient(host=..., port=...)` expressions built from `outputs`. Drop the
`'remote_on'` template var (`gen.py:349`) or keep it only for the back-compat
synthesis above.

**Template (`main_component.py`):** replace the `if $remote_on:` block
(lines 46-52) with:
```python
self._osc_client = NullOSCClient()
_osc_targets = [$osc_clients]
if _osc_targets:
    self._osc_client = OSCMultiClient(_osc_targets)
```

Files: `ableton_control_surface_as_code/model_v2.py`,
`ableton_control_surface_as_code/gen.py`,
`templates/surface_name/modules/main_component.py`, plus
`docs/mapping_file.md` and `docs/user_manual.md` (document `outputs:`, deprecate
`remote_on`).

---

## 4. Note on the broader "hook" question

The `outputs:` list is intentionally the same shape as `feedback:`. Both are
"sinks driven off the device/parameter burst". A later consolidation could merge
them under one list with a sink-type discriminator and a shared sink interface
(`on_device_burst` / `parameter_updated`), with EC4/HUD/OSC all implementing it.
**Out of scope for this round** — but `outputs:` is named and structured so that
merge is non-breaking later. Do not collapse `feedback:` and `outputs:` yet.

---

## Testing / Verification

TDD loop per CLAUDE.md — write failing tests first.

1. **Unit (model):** `tests/` — parse a config with an `outputs:` osc block and
   assert `OutputSinkDef` targets resolve; assert the `remote_on: true` back-compat
   path synthesises the legacy sink; assert empty/absent `outputs` → no OSC.
2. **Unit (codegen):** assert `generate_code_as_template_vars` emits the expected
   `osc_clients` expression string for a given `outputs` list.
3. **Generation smoke:** regenerate ec4 and launch_control:
   ```
   poetry run python ableton_control_surface_as_code/gen.py live_surfaces/ec4/ck_ec4.nt
   poetry run python ableton_control_surface_as_code/gen.py live_surfaces/launch_control/ck_launch_control_16.nt
   ```
   Confirm the generated `modules/` contains `osc_client.py` and `extensions/`,
   and that generated `functions.py` imports resolve.
4. **Deploy check:** run the generated `deploy.sh` (dry-run / inspect) and confirm
   `modules/extensions/` and `modules/osc_client.py` reach the Ableton scripts
   dir. Then **let the user redeploy + restart Ableton** (per CLAUDE.md) and tail
   `./bin/tail_logs.sh` to confirm the surface loads with no import errors.
5. **Full suite:** `poetry run pytest`.

## Rollout order

1. Extract `osc_client.py` (§2) — pure refactor, keeps tests green.
2. Fix `deploy.sh` recursion (§1 blocker).
3. Add `extensions/` package + repoint ec4 `functions.py` (§1).
4. Add `outputs:` model + codegen + template, with `remote_on` back-compat (§3).
5. Docs.
