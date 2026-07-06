 # Architectural Integrity Review: the post-handoff era

**Scope:** the 68 commits from `a56737a` ("add claude.", 2026-05-04) to `296bf73` (HEAD, 2026-06-30).
**Question:** did agent-written code maintain the structural and architectural integrity of the
codebase that preceded it?
**Method:** before/after comparison of module structure, pattern conformance of new features,
churn analysis, code reading of the five highest-churn files, test-suite inspection, and the
project's own `.quality/` dashboard history. The dirty working tree was excluded; this reviews
committed code only.

---

## Verdict

**The architecture held, and in several dimensions improved — but the code carries a
distinctive residue that makes it harder to *trust*, which is exactly the problem you're
feeling.** The macro-structure (config → models → codegen → templates → runtime modules) is
intact and new features slot into it correctly. Tests went from 53 to 474. What eroded is not
the architecture but the *hygiene at the edges*: encapsulation leaks, fossilized debugging
narration, permanent "temporary" instrumentation, and exception-swallowing that demonstrably
hid at least one real bug that is still in HEAD (see Finding 1).

A fair calibration note: the pre-handoff baseline was not pristine — it had TODOs,
commented-out blocks, `print`-based warnings, and typos (`_lisetenr`, `decleration`, `deivce`
all predate the handoff; the agent matched existing names rather than renaming, which is
arguably correct behavior). The agent's code is on average *more* documented and *far* more
tested than the baseline. The risk profile changed rather than simply degrading.

---

## 1. What held, and what improved

### 1.1 Pattern conformance of new features — good
The core architectural pattern (one `model_<type>.py` per mapping type: Pydantic config model →
`build_*_model_v2` → `*WithMidi` → template functions in `gen_code.py` → dispatch dict) was
followed faithfully by every new mapping type:

- `model_clip.py` is a model citizen: a frozen `ClipActionSpec` table as single source of
  truth, a `field_validator` that rejects typo'd action names loudly at generate time, and the
  standard `ClipWithMidi` / `build_clip_model_v2` shape.
- `model_parameter_pager.py`, `model_custom_devices.py`, `model_composition.py` follow suit.
- The discriminated union in `model_v2.py` was extended properly, and
  `KNOWN_MAPPING_TYPES` is now *derived* from the union (`model_v2.py:359`) so error messages
  can't drift from the real type set — a genuinely nice touch.
- The if/elif type dispatch was replaced with a `_MAPPING_BUILDERS` registry
  (`model_v2.py:315`) mirroring the existing `template_to_code` dict in `gen.py`.

### 1.2 Decomposition — good, and self-initiated
`helpers.py` (the runtime facade, touched in 30 of 68 commits — the #1 churn file) was heading
toward god-file status mid-period. The R1–R10 refactoring backlog commits (`e8309af`…`2496fc3`)
extracted it into layered pieces with clean dependency direction:

- `param_resolver.py` — pure resolution + paging math, no Live coupling
- `hud_presenter.py` — burst assembly, no Live writes
- `hud_visibility.py` — show/hide intent as one explicit decision table
- `helpers.py` — remains the Live-coupled facade

New concerns landed in new leaf modules (`slots.py`, `hud_layout.py`, `region_state.py`,
`mode_link.py`, `clip_actions.py`) rather than being bolted onto existing ones. No file
exploded: the worst growth is `helpers.py` 446→699 and `gen.py` 296→615 lines, against ~25 new
purpose-specific modules.

### 1.3 Testing — transformed
53 tests → 474, running in 0.8s with zero I/O. Test quality is decent: dataclass fakes
(`FakeParameter`, `FakeDevice`) rather than deep mock chains, docstrings that state the
behavioral contract being pinned, and regression tests named after the bug they pin
(`TestButtonEdgeGuard: "the fix for the toggle-hardware-fires-every-other-press regression"`).
Validation errors got a real product treatment (`ProblemAccumulator` collecting all config
problems into one readable error instead of failing on the first).

### 1.4 Self-governance infrastructure
The agent built its own oversight: `build.sh` → `scripts/quality_check.py` →
`.quality/dashboard.md` with trend history per commit; a plans discipline
(`ai-coding/plans/` → `done/`) that was actually followed; commit messages that reference the
plan. Docs went from nothing to 940 lines (`user_manual.md`, `mapping_file.md`,
`custom_device_mappings.md`).

---

## 2. Where integrity eroded

Ordered by severity.

### Finding 1 — A live bug hidden by exception swallowing (HIGH)
`templates/surface_name/surface_name.py:250`, the `HELLO` command handler:

```python
self.main_component._remote.init_layout(self.main_component._helpers._hud_cells)
```

`Helpers` has **no** `_hud_cells` attribute — it lives on `Remote` (`helpers.py:555`) and
`HudPresenter`. Every `HELLO` datagram therefore raises `AttributeError`, which is silently
eaten by the catch-all `except Exception` at the bottom of `tick()` and logged as a generic
line. The feature (HUD re-handshake on restart) is dead; nobody noticed because the layout is
*also* re-emitted at the head of every burst, masking the failure.

This one finding encapsulates the systemic pattern: **untested template code + private
attribute reach-through + broad exception swallowing = a bug that works around itself.** The
templates are the only part of the system with no direct test coverage (they're
`string.Template` text, exercised only via generation smoke tests), and it is precisely where
the bug lives.

### Finding 2 — Encapsulation leaks that contradict the agent's own refactorings (MEDIUM)
Commit `e63f2a2` is titled *"public ParameterResolver API"*. Yet `helpers.py:6-10` imports
four underscore-private names from that same module:

```python
from .param_resolver import (..., _device_table_key, _build_device_table,
    _default_device_banks, _default_bank_names)
```

Likewise the surface template reaches `self.main_component._helpers`,
`self.main_component._remote` (`surface_name.py:250, 339, 346`) — the generated shell driving
the component through its privates. The refactorings drew boundaries; subsequent commits
stepped over them. This is the clearest evidence that the agent optimizes each commit locally
and does not defend boundaries it drew three commits ago.

### Finding 3 — Debugging narration fossilized as permanent comments (MEDIUM)
A pervasive style issue with real maintenance cost. Comments throughout refer to plan file
names, backlog ticket IDs, and hypotheses from specific debugging sessions:

- `helpers.py:186-189`: *"THE funnel: … where Bug 1's nav-then-listener race is decided"*
- `main_component.py:244-247, 310, 339`: *"the Bug 1 ordering signal"*, *"Bug 2 is suspected
  to be a MODE send-ordering / stray-HIDE interleave"*
- `gen.py:243`, `helpers.py` passim: *"(R3 step 5)"*, *"(R10)"*, *"(R9)"*
- Plan-name citations: *"(hud-protocol-instrumentation-plan)"*, *"(momentary-vs-toggle…)"*

"Bug 1" and "Bug 2" are meaningless to any reader outside the session that coined them; the
R-numbers refer to a backlog file that has since moved to `done/`. These comments narrate the
*process* of writing the code rather than stating constraints the code can't show. They will
mislead precisely when they're needed most — during the next debugging session.

### Finding 4 — "Temporary" instrumentation is now permanent (MEDIUM)
- `helpers.py:201`: *"TEMP diag (operator-paging-dead-param-plan): … Remove once root cause is
  confirmed"* — an always-on log line. The named plan exists in neither `plans/` nor `done/`,
  so the removal trigger is orphaned.
- `param_resolver.py:133, 190`: two more TEMP diag blocks from the same investigation.
- The `fine()` `[hudtrace]` channel: fine as a gated facility, but its call sites annotate
  Bug-1/Bug-2 attribution logic at nearly every nav/mode/listener function in
  `main_component.py`, roughly doubling the visual weight of those methods.

The runtime is generally very log-heavy (`[switch]` logs every press with a ~200-char line at
`helpers.py:293, 317`). Defensible inside Live where logs are the only debugger — but there is
no distinction between permanent operational logging and leftover investigation output.

### Finding 5 — Defensive `except Exception` as house style (MEDIUM)
The runtime modules wrap nearly every Live interaction in broad try/except-log-continue. In
Live's embedded Python that's a legitimate survival strategy *at the top-level event
boundary*, but it's applied indiscriminately, and it directly enabled Finding 1. One instance
is plainly confused code: `helpers.py:358`:

```python
except (TypeError, Exception):
```

`Exception` subsumes `TypeError`; the clause is a fossil of an edit that changed intent
mid-flight and was never re-read.

### Finding 6 — Back-compat shims in a repo with zero external consumers (LOW-MEDIUM)
- `Helpers.__init__(…, **legacy)` (`helpers.py:83-88`): keyword back-compat kept so *tests*
  don't need updating — inverted priorities; the tests exist to serve the code.
- `helpers.py:638-646`: sinks "implementing only `on_device_burst` are bridged **for one
  release**" — this project has no releases; the bridge is immortal.
- `RootV2ModesOrModeless` legacy-OSC synthesis is fine (real config back-compat), but the
  pattern shows the agent defaults to *adding* compatibility layers instead of migrating the
  handful of internal call sites it owns.

### Finding 7 — Complexity concentrating in `gen.py` (LOW-MEDIUM, trending worse)
`gen.py` doubled (296→615 lines) and now mixes: template-var assembly, mode-FSM rendering,
composition orchestration, semantic validation, deprecation warnings, CLI entry, and ASCII-art
layout printing. `generate_code_as_template_vars` is the codebase's worst function by the
project's own dashboard — **CC 34, 7 parameters** — and it absorbs a new parameter or branch
with nearly every feature (`hud_cells_override`, `feedback`, `outputs`, pager-preview…). The
same accretion pattern shows in `Helpers.parameter_page_inc`/`parameter_page_dec`
(`helpers.py:399-467`): ~70 lines that are mirror-image duplicates differing in a sign and a
comparison, and in three near-identical clip listener generators in `gen_code.py:323-374`.

### Finding 8 — Measurement without a remediation loop (LOW)
The quality dashboard is genuinely good — and its trend lines show the limits of
self-oversight: *Duplicate function groups: 2 → 2 → 2 → … → 2* across ten runs; *Functions >
4 params: 20, flat*; *CC max: 32 → 34, creeping*; *Max params: 9 → 11*. The dashboard's own
header says metrics are "trend data for deciding when the next batch of work should be a
cleanup," but nothing consumes the trend. The R1–R10 backlog happened once (prompted); the
instrument has not triggered a cleanup since.

### Finding 9 — Type discipline is two-tier (LOW)
The codegen side is rigorous (Pydantic models, discriminated unions, frozen dataclasses). The
runtime side is not: `SurfaceConfig` (`helpers.py:52-79`) declares eleven fields, nine of them
`Any = None`. Understandable — the runtime must run on Live's bundled Python — but the
contrast means the *data crossing the codegen→runtime boundary* (the most fragile interface in
the system, per Finding 1) is exactly where types are weakest.

---

## 3. The verification gap (why you couldn't verify quality)

Your instinct — "features work but I can't verify the code" — matches the evidence. The commit
history shows a recurring *fix-after-ship* rhythm: `7ef07ed` "Fix multi-mode switch-mapping
list literal concatenation", `c9bf599` "Fix toggle-hardware regression", `5e1887c` "Fix
composed HUD never showing", `d6e9a62` "Fix lc_parks composed HUD". Each fix commit is a
regression that 400+ passing tests did not catch, because they all live in the same blind
spot:

**The test suite covers the generator and the runtime logic (with fakes), but nothing covers
the seam: the `string.Template` files and the generated code actually executing against
Live.** Templates are checked only by `get_python_code_error` (an AST syntax parse) — which
prints a red warning and *continues* rather than failing generation. Finding 1's bug is
syntactically valid, attribute-wrong, and invisible to every check in the repo.

So the honest summary of code quality is: **the parts the agent could test, it tested well and
they held up; the parts only Ableton can execute drifted, and the swallow-everything error
style meant drift didn't announce itself.**

---

## 4. Recommendations, prioritized

1. **Fix the `HELLO` handler** (`surface_name.py:250` → route through a public method, e.g.
   `Remote` re-emitting its own stored `_hud_cells`). Add a generation-level test that
   renders the template with real vars and asserts every `self.main_component.<attr>` /
   `._helpers.<attr>` referenced in templates exists on the target classes — a cheap
   "template↔runtime contract" test that closes the whole class of bug.
2. **Make `verify_python=True` failures fatal** in `gen.py:template_file`. A generator whose
   output fails its own syntax check should not exit 0.
3. **Sweep the fossils** (one mechanical cleanup commit): TEMP diags, Bug-1/Bug-2 and
   R-number comment references, `except (TypeError, Exception)`, the `**legacy` shim and the
   `on_device_burst` bridge, commented-out code in `gen.py:314-319, 614-615`.
4. **Ban private cross-module imports** — either promote the four `param_resolver`
   underscore functions to public names or move their use inside the resolver. Add the check
   to `quality_check.py` so the dashboard enforces the boundary the refactor drew.
5. **Close the remediation loop**: give the dashboard teeth — a small set of ratchets
   (duplicate groups may not increase; CC max may not increase) that fail `build.sh`, since
   CLAUDE.md already gates commits on it. Trends you must react to beat trends you may read.
6. **Split `generate_code_as_template_vars`** next time it needs a change (don't do it
   speculatively): the natural seams are already visible — HUD/label assembly, mode/FSM code,
   sink construction.

## 5. Bottom line

The agent behaved like a very prolific mid-level engineer with an excellent memory for *your*
patterns and no shame about leaving its scaffolding up. Architectural intent was preserved and
in places strengthened (decomposition, validation, tests, docs, self-measurement). The
degradation is concentrated in exactly the places a reviewer without runtime access can't see:
the template/Live seam, exception paths, and the difference between code written to ship and
code written to debug. Items 1–4 above are a day of cleanup; item 5 is what changes the
trajectory.
