# Phase 1 — Config Validation & Error Messages (detailed, test-first)

## Context

Productizing this tool (see `productization-roadmap.md`) is gated on **authoring pain**, not the
runtime moat. The runtime (HUD, wire protocol, dynamic param resolution) is already strong; what
blocks "someone other than the author can use this" is that bad configs fail with cryptic errors,
and many mistakes only surface when Ableton tries to load the generated surface.

### Key finding — it is NOT NestedText's fault
We traced where cryptic errors actually originate. There are three layers, and they fail very
differently:

1. **NestedText parse** (`nt.loads`) — *already good.* `read_root`/`read_controller` catch
   `nt.NestedTextError` and call `e.terminate()`, which prints line/column with context
   (`model_v2.py:296`, `:304`). NestedText refuses to type-guess; its errors are a strength.
2. **Pydantic structural validation** — `RootV2ModesOrModeless(**data)` (`model_v2.py:295`) is
   *inside* the `try`, but raises `ValidationError`, which is **not** a `NestedTextError`, so the
   `except` never catches it. It surfaces as a raw multi-line Pydantic dump. **Worst structural
   error, and it's a missing `except`.**
3. **Lark encoder-coord grammar** (`row-1:1-8 toggle`) — `parse_coords` prints a line then
   re-raises the raw Lark exception (`core_model.py:281`). **Most-hit cryptic error.** Note this
   mini-language lives inside *string values*, so it is format-independent — swapping NestedText
   would not touch it.

**Decision: keep NestedText.** Two of three pain sources are format-independent; a migration fixes
roughly none of them and costs a rewrite. YAML is a downgrade (silent type coercion, Norway
problem); TOML fits the deep nested mode/mapping shape poorly. Once Phase 2's GUI emits config, the
format becomes a serialization target and the question dissolves. The leverage is in **wrapping
errors** and **validating early**, not in the serializer.

---

## Approach: outside-in, tests first

Per the repo's TDD convention (`CLAUDE.md` → Development), we write **failing tests first** that
assert on the *user-facing behaviour* — "given this broken config, the user sees this readable
message, before any codegen runs" — then implement to green. Tests are the spec for what counts as
a good error. Work outside-in: start from the whole-config integration case the user actually hits,
then drive down into model unit tests for each edge case.

The existing patterns to follow:
- `tests/test_encoder_coords.py` — plain `unittest`, parse-and-assert. Extend with failure cases.
- `tests/custom_assertions.py` — add a shared `assertRaisesGenError(code, *substrings)` helper.
- `GenError(message, error_code)` (`gen_error.py`) — the **one** exception type all validation
  should raise. Today only `model_v2.py:199` uses it; the work is to route every validation through
  it with stable error codes.
- `tests/builders.py` — reuse/extend builders so failure-case configs are cheap to construct.

### Custom assertion helper (write this first)
```python
# tests/custom_assertions.py
def assert_gen_error(self, fn, code=None, *must_contain):
    with self.assertRaises(GenError) as ctx:
        fn()
    msg = str(ctx.exception)
    if code is not None:
        self.assertEqual(ctx.exception.error_code, code)
    for frag in must_contain:
        self.assertIn(frag, msg)   # message must name the offending thing + a fix/example
```
Every error test asserts **(a) it's a `GenError` (not a raw Lark/Pydantic/ValueError leak), (b) a
stable error code, (c) the message contains the offending token AND either valid options or a
correct example.** Asserting on substrings — not exact strings — keeps tests robust to wording.

---

## Workstream A — Encoder-coord grammar errors (highest user-facing impact)

Wrap `parse_coords` / `parse_multiple_coords` (`core_model.py:278-291`): catch Lark's
`UnexpectedInput` / `UnexpectedCharacters` / `UnexpectedToken`, raise `GenError` with the raw input,
the column if available, the grammar shape, and a correct example. Thread the *source location*
(which mapping key the coord string came from) through so the message says where.

### Edge-case catalogue → unit tests (`tests/test_encoder_coords.py`)
Each row is a test: input → expected `GenError` fragments.

| # | Input | Why it breaks | Message must contain |
|---|---|---|---|
| A1 | `row 1:1-8` | space instead of `-` after axis | `row 1:1-8`, `row-N:M`, example `row-1:1-8` |
| A2 | `row-1:1..8` | `..` range instead of `-` | `..`, `use 'M-N'`, example |
| A3 | `Row-1:1-8` | capitalised axis | `Row`, `row`/`col` |
| A4 | `row-1` | missing `:range` | `row-1`, `:` , example |
| A5 | `row-1:` | empty range | range required |
| A6 | `row-1:8-1` | descending range (parses, semantically bad) | `8-1`, "start ≤ end" — see Workstream C |
| A7 | `row-1:1-8 togle` | misspelled refinement | `togle`, valid refinements `toggle, mode-2, map_mode_absolute` |
| A8 | `row-1:1-8 toggle toggle` | duplicate refinement | dedupe or warn |
| A9 | `col-2:3` | valid `col` axis (positive control) | parses to `EncoderCoords` |
| A10 | `row-1:1-8,row-2:1-8` via `parse_coords` (single) | list passed to single parser | "expected a single coord, got a list", point to `parse_multiple` |
| A11 | `` (empty string) | empty | "empty coordinate" |
| A12 | `row--1:1` / `row-0:1` | zero/negative axis | axis ≥ 1 — Workstream C |

Keep the existing positive tests (A9-style) green; add a `test_parse_errors` block. Note the grammar
also references `min_max(...)` (commented out, `encoder_coords.py:87-88`) and `mode-2` — tests
should pin current behaviour so cleanup doesn't silently change it.

---

## Workstream B — Pydantic structural validation

Add `except ValidationError` alongside the NestedText one in `read_root` **and** `read_controller`
(`model_v2.py:292-305`). Translate to `GenError`: walk `e.errors()`, render each as
`file → key path → what was expected`. The enum members are already in the models (mapping `type`,
clip actions), so the message can list valid values for free.

### Edge-case catalogue → unit tests (`tests/test_gen_build_model_v2.py`, `test_controller.py`)
Drive these through `read_root(<nt string>)` so the test exercises the real entry point.

| # | Broken config | Today | Must become |
|---|---|---|---|
| B1 | `type: devcie` (typo) | raw `ValidationError`, enum dump | `GenError`: "unknown mapping type 'devcie' — expected one of: device, mixer, transport, track-nav, device-nav, functions, parameter-pager, clip" + which mode |
| B2 | mapping missing required `type` | raw | "mapping in mode 'X' is missing required key 'type'" |
| B3 | clip mapping with unknown action key | caught (`extra='forbid'`) but as raw | route through `GenError`, list valid clip actions |
| B4 | `mode-button` missing `button` | raw | names the missing key + where |
| B5 | controller group missing `midi_channel` | raw | names file, group index, key |
| B6 | `midi_type: cc` (lowercase) | enum error | "expected CC or note (got 'cc')" |
| B7 | top-level not a dict (file is a bare list) | raw `TypeError` | "expected a mapping at top level of <file>" |

Assert via the shared helper — `GenError`, code, and the fragment naming the bad key + the valid set.

---

## Workstream C — Semantic validation (a single pre-codegen pass)

A validation stage that runs **after parse + model build, before any `GeneratedCode`**, and reports
**all** problems at once (accumulate into a list, raise one `GenError` with a numbered summary —
don't fail on the first). This is the piece that moves errors from "Ableton load time" to
"generation time." Some of these checks already exist and are good; the work is to (a) centralise
them, (b) make sure they all raise `GenError`, (c) accumulate rather than fail-fast.

Already present and good — keep, route through the accumulator:
- coord out-of-range (`model_controller.py:198`) — clear, shows valid cols.
- duplicate MIDI coords across mappings (`model_v2.py:199`) — shows both source files.
- color-not-found (`model_controller.py:172`), invalid note name (`:48`), mixed slots/params
  (`model_device.py:164`), mixer single-vs-range (`model_mixer.py:19`), unknown function
  (`model_functions.py:138`).

Add (currently only fail at Ableton load time):

| Check | Rule | Edge-case tests |
|---|---|---|
| MIDI channel | 1 ≤ ch ≤ 16 | ch=0, ch=17, ch=−1 |
| MIDI number | 0 ≤ n ≤ 127 | n=128, n=−1; range `120-130` (partial overflow) |
| Range order | start ≤ end | `row-1:8-1` (ties to A6) |
| Axis number | ≥ 1 | `row-0`, `row--1` (ties to A12) |
| Mode-name uniqueness | names distinct | two modes both `main_mode` → "duplicate mode name 'main_mode'" |
| Range length vs slots | `range: row-1:1-8` + `slots: 1-4` mismatch | length mismatch named with both counts |
| Param index vs device bank | if device is in the curated bank, index < param count | index 50 on a 40-param device → warn/error with the cap |
| Duplicate coords *across modes* | currently only within-mode | same physical control bound twice in one mode |
| Controller ref exists | file resolves (`gen.py:311`) | missing controller file → clear path error (keep) |

### Edge-case unit tests (`tests/test_validation.py` — new file)
Outside-in: one integration test feeds a config with **three** distinct mistakes and asserts the
single `GenError` lists all three (proves accumulation, not fail-fast). Then one focused unit test
per row above. Use `tests/builders.py` to construct near-valid models and mutate one field per test.

Representative integration assertion:
```python
def test_reports_all_problems_at_once(self):
    cfg = broken_config(midi_channel=17, dup_mode="main_mode", coord="row-9:1")
    self.assert_gen_error(lambda: build_all(cfg), code=1,
        "channel 17", "duplicate mode name 'main_mode'", "row-9:1 is out of range")
```

---

## Workstream D — Editor support (cheap multiplier, optional within Phase 1)
- Generate a **JSON Schema** from the Pydantic models (`.model_json_schema()`), ship it, and document
  the VS Code `nestedtext`/`yaml`-schema association so users get autocomplete + inline validation
  while typing. This prevents errors rather than reporting them, and reuses the schema you already
  have. Test: a small unit test asserting the generated schema contains the mapping-type enum and
  required keys, so schema drift is caught.

---

## Implementation order (each step: failing tests → implement → green)
1. **Shared test helper** `assert_gen_error` + stable error-code constants. ✅ done (2c04de6)
2. **Workstream A** (coord grammar) — biggest felt win, self-contained. ✅ done (2c04de6)
3. **Workstream B** (Pydantic wrap) — small change, big structural-error win. ✅ done (2c04de6)
4. **Workstream C** (semantic pass) — the architectural piece; build the accumulator first, migrate
   existing checks into it, then add the new checks. ✅ accumulator + migration + range-vs-slots done
   (this commit). Deferred within C: param-index-vs-device-bank (needs curated bank data).
5. **Workstream D** (JSON Schema) — if time allows in Phase 1; otherwise first task of Phase 2 prep.
   ⏸️ deferred.

### Progress log
- **2c04de6** — foundation + Workstream A + B + first C checks (channel/number ranges, mode-name
  uniqueness, coord descending/zero-axis).
- **This commit** — Workstream C accumulator spine:
  - `ProblemAccumulator` (`gen_error.py`) collects problems and raises once.
  - `build_validated_model` (`model_v2.py`) is the top-level orchestrator: threads ONE accumulator
    through `read_root` (mode names) → `read_controller` (controller MIDI semantics) →
    `read_root_v2`/`build_mappings_model_v2` (per-mapping coord resolution + duplicate-mapping
    clash). Parse failures (NestedText/Pydantic) still raise immediately — nothing left to validate.
  - The three previously fail-fast raise-sites now append-to-accumulator when one is passed, and
    keep their standalone raise behaviour when called directly (existing unit tests stay green).
  - New check: device **range-length-vs-slots/parameters** mismatch was a silent `print`; now a named
    `GenError` ("covers N control(s) but M parameter(s)…"). Parameter check fixed to compare TOTALs
    across multi-coord ranges (was a per-group false positive that the silent print had masked).
  - `build_midi_coords` out-of-range / row-not-found converted from raw `ValueError`/`sys.exit(1)`
    to `GenError`, so they accumulate and read clearly.
  - `gen.py __main__` now catches `GenError`, prints the readable message to stderr, exits 1 (no
    Python traceback for user config errors).
  - **Dropped** the plan's "duplicate coords across modes" row: reusing a control across modes is the
    whole point of the mode FSM; the within-mode clash check (`validate_mappings`) already covers the
    real bug. Confirmed with the user.

## Non-goals for Phase 1
- No format migration (NestedText stays — see Context).
- No GUI (that's Phase 2; this validation layer is what the GUI will reuse to validate emitted `.nt`).
- No Windows.

## Verification (end-to-end)
- `poetry run pytest tests/test_encoder_coords.py tests/test_gen_build_model_v2.py tests/test_validation.py`
  — all new failure-case tests green; **no test asserts on a raw Lark/Pydantic string** (every error
  is a `GenError`).
- Manual: hand-break a real config (`live_surfaces/launch_control/ck_launch_control_16.nt`) in three
  ways, run `gen.py`, confirm one readable, numbered error listing all three — and that it never
  reaches codegen or Ableton.
- Regression: full `poetry run pytest` stays green (existing good errors keep their messages; assert
  on substrings so wording can still improve).
