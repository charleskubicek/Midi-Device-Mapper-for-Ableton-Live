# Productizing Ableton Control Surface as Code — Roadmap

## Context

This is currently a **personal developer tool** that generates Ableton MIDI Remote Scripts from
NestedText config files, plus a native macOS HUD overlay that shows live, device-aware parameter
names. The owner believes the **dynamic mapping + HUD** is genuinely valuable and uncommon, but
that **configuring it is painful** — cryptic errors, no presets, terminal-only workflow.

This document is **analysis and a phased roadmap, not an implementation plan**. Nothing is built yet.

### Decisions locked with the user
- **Platform: macOS-only.** Accepted. Keeps the HUD as the headline feature with no per-OS rewrite.
  Trade-off owned: forgoes the ~half of Ableton users on Windows.
- **Buyer: tiered / open-core.** Apache-2.0 generator stays open for technical musicians; the
  polished HUD app + (later) GUI is the paid layer for everyone else.
- **Sequencing:** Phase 1 = presets + validation + error overhaul + real installer (cheapest path
  to "someone other than me can use it"). **Phase 2 = the configurable GUI surface editor** (the
  expensive bet, explicitly the next thing after Phase 1).

---

## Honest assessment: where it stands today

**Already strong (the moat):**
- **Wire protocol** between Python and HUD — 481-line normative spec, ~900 lines of tests across
  Python + Swift, per-source framing, atomic bursts, sticky-dismiss. Production-grade.
  (`hud_protocol.md`, `source_modules/hud_client.py`, `ableton_hud/.../WireProtocol.swift`)
- **HUD Swift app** — polished borderless overlay, not a prototype; bulletproof burst state machine
  (621 Swift test lines). Multi-surface composition is ~90% there (Phase 3 in their own numbering).
- **Dynamic device-param resolution** — "Best of Bank" curated params, standard Macro banks, unknown
  fallback, M4L macro-selector handling, paging. Uses Live's stable `original_name` so user renames
  don't break mappings. **This is the real differentiator.** (`source_modules/helpers.py`)
- **Code generator** — clean, ~35 test files, self-contained output (vendors `source_modules/` +
  `pythonosc` into each surface; no runtime path deps inside Ableton).

**The sharp edges (what blocks "product"):**
- **Cryptic errors.** Bad encoder coords surface as raw Lark `UnexpectedCharacters` exceptions;
  bad config keys surface as raw Pydantic `ValidationError`. Some errors are excellent (coord
  out-of-range, duplicate MIDI with source files) — quality is *inconsistent*.
  (`core_model.py:278`, `model_v2.py`, `model_controller.py:198`)
- **Late validation.** Many mistakes (mode-name collisions, MIDI #/channel out of range, param
  index beyond a device's count) only fail at Ableton load time, not at generation.
- **No presets.** The 3 real controllers (Launch Control, Parks, EC4) are bespoke personal setups
  with 40KB of user-specific `functions.py`, not reusable templates. New controller = write `.nt`
  from scratch.
- **Install is broken for outsiders.** `guide.md` references `requirements.txt` (doesn't exist) and
  `mapping.yaml` (real format is `.nt`); real flow needs Poetry + `poetry run`. README promises a
  downloadable release but CI ships source ZIPs only — the PyInstaller `mdma` binary config exists
  but is never invoked. (`pyproject.toml:25-30`, `.github/workflows/python-release.yml:85-102`)
- **Hardcoded Ableton path** baked into generated `deploy.sh` at generation time.

**Recurring cost to price in:** the curated per-device parameter banks (`live_device_banks.py`,
`device_parameters.nt`) are the moat but are **scraped per Live version**. New Live releases =
ongoing content maintenance, not a one-time build.

---

## Phase 1 — Make it usable by someone other than you (the wedge)

Goal: a technical musician downloads one thing, picks their controller from a list, and gets a
working device+HUD surface without reading Python tracebacks. No GUI yet.

### 1.1 Error-message overhaul
- Wrap the Lark parser: catch `UnexpectedInput`/`UnexpectedCharacters` in `parse_coords`
  (`core_model.py:278`) and emit a plain-English message with the expected grammar shape and a
  correct example (`row-1:1-8`, `col-2:3 toggle`).
- Catch the top-level Pydantic `ValidationError` in `read_root` (`model_v2.py:293`) and reformat
  to: which file, which key, what was expected (reuse the enum list already in the model). Mirror
  the NestedText `e.terminate()` style already used.
- Audit every `raise` across `gen.py` / `model_*.py` for one consistent `GenError` type carrying
  source-file + line context (the pattern at `model_v2.py:199` and `model_controller.py:198` is the
  bar to bring the rest up to).

### 1.2 Full pre-generation validation pass
A single validation stage that runs after parse, before codegen, and reports *all* problems at once:
- MIDI channel 1–16, MIDI number 0–127, contiguous/listed ranges sane.
- Mode names unique.
- Param indices within the target device's known param count (where the device is in the banks).
- Already-good checks to keep: coord-out-of-range, duplicate MIDI coords, color-not-found,
  unknown function, mixed slots/params, clip `extra='forbid'`.

### 1.3 Controller preset library
- Convert Launch Control / Parks / EC4 into **parameterized starter templates**: separate the
  reusable controller spec + sensible default mappings from the user's bespoke `functions.py`.
- A "starter" mapping per controller that maps device (selected) + mixer + transport + nav with no
  custom functions — works out of the box, edit to taste.
- Establish the pattern/format so adding a 4th controller is config, not surgery.

### 1.4 Real install / distribution
- Decide CLI packaging: either ship the `mdma` PyInstaller binary (uncomment/wire the CI steps at
  `python-release.yml:85-102`) or document a clean `pipx install`. Pick one; make the README true.
- Fix `guide.md` to match reality (`.nt`, `poetry run`, correct invocation, no phantom
  `requirements.txt`).
- Make `ableton_dir` resolve at deploy time, not bake into generated `deploy.sh` — detect the Live
  app or prompt, so a generated surface is relocatable.
- Package the **HUD app** as a signed/notarized `.app` (or DMG) — this is the paid artifact in the
  open-core split; it must install without Xcode.

### 1.5 Tier boundary
- Generator + presets stay Apache-2.0 (open, for hackers).
- Paid layer = the notarized HUD app (and later the GUI). No license server needed for v1 — a paid
  download is enough to start; revisit activation only if piracy becomes real.

**Phase 1 exit criteria:** a non-author technical musician installs the HUD app, runs the CLI
against a bundled preset for a controller they own, deploys, and sees the live HUD — and any config
mistake they make is reported in plain English before Ableton ever loads.

---

## Phase 2 — The configurable GUI surface editor (explicit next step)

Goal: remove the last hard requirement (hand-writing `.nt` + knowing MIDI internals) so
**non-technical** musicians are reachable. This is essentially a new application; treat it as a
distinct, funded effort after Phase 1 ships.

Shape (to be designed properly when we get there, not committed now):
- **Visual controller grid**: pick a controller from the preset library (or define rows/cols), then
  drag mapping types (device / mixer / transport / nav / function / clip) onto cells. The grid is
  the `.nt` controller spec made visual.
- **MIDI learn**: twist a knob → the editor captures channel/CC/note, eliminating the #1 source of
  hand-error and the need to read controller datasheets.
- **Device-param discovery**: query a running Ableton (via the existing UDP/update channel back to
  the surface, see `update.py`) to list what a selected device actually exposes, so users pick
  "Filter Freq" from a list instead of guessing index 50.
- **Live preview against the real HUD**: the editor speaks the same UDP wire protocol, so the HUD
  previews a layout before any code is generated.
- **The GUI emits `.nt`** and calls the same `gen.py` pipeline — the generator stays the single
  source of truth; the GUI is a front end, not a fork. This keeps Phase 1's validation/errors
  reused rather than reimplemented.
- Likely a native macOS app (consistent with the macOS-only decision and the existing Swift HUD
  codebase) so the HUD and editor can share rendering and the UDP layer.

**Phase 2 exit criteria:** a musician who has never opened a terminal or read a MIDI spec can map a
controller, preview it on the HUD, and deploy.

---

## Explicitly deferred / not now
- **Windows support** (HUD overlay + focus monitoring rewrite). Out, per platform decision.
- **Live live-values for non-device slots** (mixer faders/transport show labels, static `0` bars) —
  known issue; ship with caveat, wire later.
- **Multi-surface side-by-side HUD** (their Phase 3) — ~90% done; finish opportunistically, not a
  gate.
- **License/activation server** — only if piracy proves material.

---

## Verification (how we'd know each phase works)
- **Phase 1 unit/integration:** add tests that feed deliberately broken configs (bad coord syntax,
  out-of-range MIDI, dup mode names, bad param index) and assert a single readable error listing all
  problems — following the existing TDD-first convention in `tests/`. Extend HUD value tests to the
  non-device caveat boundary.
- **Phase 1 end-to-end:** fresh machine (no repo checkout), install the HUD `.app` + CLI binary,
  generate from a bundled preset, `deploy.sh`, restart Live, confirm via `./bin/tail_logs.sh` the
  surface loads and the HUD shows live device params on focus change.
- **Phase 2:** usability test with a non-technical musician doing the full map→preview→deploy loop
  unaided; GUI-emitted `.nt` must pass the same validation suite as hand-written config.
