# Review: Refactoring Backlog R4–R10 (last 7 commits) — verdict + follow-up plan

## Context

The user asked whether the refactoring-backlog work (e8309af..7b19a7c, items R4–R10 of
`ai-coding/plans/refactoring-backlog-plan.md`) genuinely improved single-responsibility
and code hygiene, after the implementing agent's closing comment admitted the
`god_classes` metric didn't move. This review checked the actual diffs, the resulting
modules, and the `.quality` dashboard history — not just the agent's summary.

## Verdict: genuinely better, with one oversold item (R10) and a deferred cleanup tail

### What's real

- **R9 split is structural, not cosmetic.** `helpers.py` went 1,182 → 685 LOC.
  `ParameterResolver` (555 LOC) is pure as the plan demanded — constructor takes data +
  a `log` callable, no manager/remote/sockets. `HudPresenter` does no Live writes.
  The resolve / present / Live-glue seams match the plan's design exactly.
- **R8 done as designed.** String-built `_region_setup_code` is gone; the template now
  has real, syntax-checked wiring gated on `REGION_CONFIG = $region_config` and
  `HUD_TARGET = $hud_target`; the four override kwargs collapsed into
  `CompositionOverrides` (gen.py:322).
- **R7 delivered.** Max params 14 → 9; `PageInfo` killed the 4-vs-6-tuple arity sniff;
  `SurfaceConfig` groups Helpers' constructor config; `Remote.refresh_burst(snapshot)`.
- **R4–R6 delivered** (clip dict with validating error message, `slots.py` leaf module
  — deferred imports 14 → 5, switch rename).
- Tests 319 → 346, all green; quality history recorded per item.
- **The agent's god_classes explanation is honest and correct.** ClipActions is
  pre-existing; ParameterResolver is one cohesive concern that trips a ≥15-method
  heuristic. The flat metric does not mean the split failed.

### What's not as claimed

1. **R10 is roughly half-implemented but committed as done.** `HudVisibility` defines
   7 events; production fires only 2 (`DeviceFocus`, `UserToggle`). `ModeChange`,
   `ViewLeft`, `RegionCommit`, `RegionHide`, `ControlTouched` are unit-tested but never
   constructed outside `tests/test_hud_visibility.py`:
   - Template app-view listeners still call `send_hide()` directly
     (`templates/surface_name/modules/main_component.py:143,151,160`) — plan step 3 —
     and don't update the Python-side `dismissed` mirror, so the "single owner of
     show/hide intent" docstring is false: after a view-left dismiss the mirror is stale.
   - `RegionState` keeps its own HIDE/PING rules + race comments (step 4 — legitimately
     deferred per plan, but step 3 was not hardware-gated).
   - `emit_burst` (hud_presenter.py:95–108) still contains the inline suppress/HIDE
     branch and mutates `dismissed` directly; `refresh_for_mode`/`emit_current_burst`
     bypass the table entirely (no `ModeChange` event).
   - The `combined=True` policy flag is tested but never passed; gen.py:436–446 still
     uses the `HudTrigger.Selection` force-override — the same policy now exists twice,
     one copy dead.
   - hud_presenter.py:8–10 docstring still says "R10 will replace…" — stale.
2. **Encapsulation inversion in the R9 seam.** Methods moved verbatim kept their
   underscores, so `HudPresenter` and `Helpers` call `_resolver._resolve_encoder`,
   `_resolve_switch`, `_lom_slot_payload`, `_encoder_pages_count`, `_page_label_for`
   cross-class. The plan specified a public resolver API (`resolve_encoder`,
   `encoder_pages_count`, …). The boundary exists; the interface contradicts it.
3. **R9 phases 4–5 only token-done.** `test_helpers.py` is still 1,172 lines of
   fake-heavy tests; the new direct test files are ~80 lines each. Helpers carries
   ~15 pass-through delegators + property shims (`_encoder_page`, `_hud_dismissed`,
   the `_remote` setter that syncs `presenter._remote` "for tests") that exist **only**
   for the old test suite — no template or codegen path uses them (verified by grep).
   This is what keeps Helpers at 43 methods.
4. Core LOC rose 6,022 → 6,374 and big-modules 5 → 6 — expected for extraction, but the
   "tighten" phase that pays it back was skipped.

## Recommended follow-up work (if the user wants it executed)

Ordered; each is independently committable, `./build.sh` before each commit per CLAUDE.md.

- **F1 — Finish R10 wiring (M).** Route `ModeChange` through `decide()` in
  `refresh_for_mode`; move `emit_burst`'s suppress/HIDE else-branch into the Decision
  handling so `dismissed` is mutated only inside `HudVisibility.decide`; template
  listeners forward `ViewLeft` via a `helpers` hook instead of raw `send_hide()`
  (keeps the mirror in sync). Regenerate + redeploy; user restarts Live. Fix the stale
  hud_presenter docstring. RegionState routing + `combined` override removal stay
  deferred (hardware-gated, per plan) — but delete or wire the dead `combined` flag,
  don't leave both copies.
- **F2 — Public resolver API (S).** Rename the externally-consumed resolver methods to
  drop underscores (`resolve_encoder`, `resolve_switch`, `lom_slot_payload`,
  `encoder_pages_count`, `button_pages_count`, `page_label_for`, `standard_banks`,
  `resolve_param_by_name`); update HudPresenter/Helpers/tests. Mechanical.
- **F3 — R9 phase 4/5 for real (M).** Retarget `test_helpers.py`'s resolver/presenter
  tests at the units directly; delete the test-only pass-throughs from Helpers
  (verified unused by generated code). This is the change that actually shrinks the
  Helpers god-class.

## Verification

- `poetry run pytest` green at every step.
- F1: regenerate `live_surfaces/launch_control` + lc_parks, deploy, restart Live,
  `./bin/tail_logs.sh` clean; manual check that browser-open still dismisses the HUD
  and that hud_toggle re-shows after a view-left dismiss (the newly-synced mirror).
- F2/F3: byte-diff regenerated surfaces — must be identical (runtime-module renames
  don't appear in generated identifiers).
- `./build.sh`: F3 should finally move `god_classes` (Helpers drops under both
  thresholds) and `long_param_functions`.
