# Architectural Integrity Fixes (review items 1-3)

Source: `ai-coding/design/architectural-integrity-review-2026-07-01.md`, section 4,
recommendations 1-3.

## 1. Fix the HELLO handler bug (Finding 1, HIGH)

`templates/surface_name/surface_name.py`'s `HELLO` command handler calls:
```python
self.main_component._remote.init_layout(self.main_component._helpers._hud_cells)
```
`_hud_cells` lives on `Remote`, not `Helpers` — `AttributeError` every time, silently
swallowed by `tick()`'s catch-all `except Exception`. The identical bug pattern was
independently reintroduced in the in-progress `source_modules/hud_arbiter.py:124`
(`main._remote.init_layout(main._helpers._hud_cells)`), confirming the private
reach-through is the root cause, not a one-off typo.

**Fix:**
- Add a public `Remote.resend_layout()` that re-emits the stored `_hud_cells` (mirrors
  the existing re-emit-in-`refresh_burst` logic already in `init_layout`/`refresh_burst`).
- Replace both call sites (`surface_name.py` HELLO handler, `hud_arbiter.py` reelect)
  with `main._remote.resend_layout()` — no more reaching through `_remote` into
  `_helpers`'s private state.
- Add a generation-level "template↔runtime contract" test: render `surface_name.py`
  and `main_component.py` with real vars, collect every `self.main_component.<attr>`
  / `self._helpers.<attr>` / `self._remote.<attr>` access the templates make, and
  assert the attribute exists on the corresponding runtime class (`MainComponent`,
  `Helpers`, `Remote`) via `getattr`/`hasattr` static inspection, so this whole bug
  class is caught at generation time instead of silently at runtime.

## 2. Make `verify_python=True` failures fatal (Finding "verification gap", recommendation 2)

`ableton_control_surface_as_code/gen.py:template_file` prints a red warning on a
syntax error from `get_python_code_error` but still writes the file and returns 0.

**Fix:** raise (fail generation) when `verify_python=True` and `get_python_code_error`
returns an error, instead of printing and continuing.

## 3. Sweep the fossils (one mechanical cleanup commit)

Scoped strictly to what the review names, not a broader style pass:

- `source_modules/helpers.py:355` — `except (TypeError, Exception):` → `except Exception:`
  (`Exception` already subsumes `TypeError`; dead alternative).
- Bug-1/Bug-2 comment references (meaningless outside the debugging session that
  coined them) — reword to state the actual invariant, not the bug nickname:
  - `templates/surface_name/modules/main_component.py:244-247, 310, 339-340, 349`
  - `source_modules/helpers.py:186-189`
- R-number references to the now-moved `ai-coding/plans/` → `done/` backlog:
  - `ableton_control_surface_as_code/gen.py:247` ("R3 step 5")
  - `ableton_control_surface_as_code/hud_layout.py:14` ("R3")
  - `source_modules/helpers.py:210` ("R10")
  - `source_modules/hud_presenter.py:1, 8, 46` ("R9"/"R10")
  Plan-name citations like `(hud-owner-election-plan)` were also stripped per the
  review's explicit callout and CLAUDE.md's rule against referencing the current
  fix/task in comments (they belong in commit messages / PR descriptions, not code).
- `**legacy` kwargs shim on `Helpers.__init__` (`source_modules/helpers.py:83-88`) —
  kept only so tests don't need `SurfaceConfig(...)`. Migrate all test call sites in
  `tests/test_helpers.py`, `tests/test_show_hud_on.py`, `tests/test_hud_toggle.py`,
  `tests/test_param_name_resolution.py` to construct `SurfaceConfig` explicitly, then
  drop the `**legacy` parameter and the `if config is None` branch.
- `on_device_burst` bridge in `Remote.refresh_burst` (`source_modules/helpers.py:646-655`)
  — the `hasattr(sink, 'on_burst')` fallback exists for sinks implementing only the
  old `on_device_burst` signature. No current sink (`Ec4Client`/`NullEc4Client`) is in
  that position; both implement `on_burst`. Drop the branch, call `sink.on_burst(snapshot)`
  unconditionally.
- Commented-out dead code in `gen.py`: the two commented `template_file(...)` calls
  for `modules/helpers.py`/`modules/nav.py` (no longer templated), and the two
  commented `exit(-1)`/`sys.exit(e.error_code)` lines after the `__main__` block.

## Test plan (TDD)

- New test asserting `Remote.resend_layout()` re-sends stored cells (and no-ops when
  empty), covering the fixed HELLO/hud_arbiter call sites.
- New generation-level contract test (rendered template attrs vs. runtime classes).
- New test that a template with a syntax error raises via `template_file(..., verify_python=True)`.
- Update `test_helpers.py`'s `test_config_object_matches_legacy_kwargs`-style test to
  drop the legacy path once removed (or delete it if it becomes redundant).
- Full suite must pass; `./build.sh` before commit.
