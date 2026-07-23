# BeatSpark Learnings — Plan

Source: `docs/beatspark.py` (a read-only LOM telemetry/verification bridge for a
"learn Ableton" tutor app). It is not a controller-mapping script, so nothing is
copied wholesale — but four techniques and a body of LOM gotchas are worth
adopting. Line references are into `docs/beatspark.py`.

Rating = value-to-us × ease, as a single high/med/low priority.

---

## 1. `SCRIPT_VERSION` stale-script handshake — **HIGH**

**What it is.** A monotonic integer bumped on every edit to the remote script,
echoed in every ping→pong. The app compares the running value against the value
in the bundled-on-disk file and, on mismatch, shows a "relaunch Ableton" banner.
Old scripts send a bare pong the app reads as version 0. (lines 10–18, 331–335)

**Why we want it.** Ableton loads control surfaces only at startup. When the user
redeploys without restarting Live, the *old* generated code keeps running: OSC
still flows, but new handlers silently never answer. Our own CLAUDE.md already
concedes this ("Let the user redeploy so that they can restart ableton live
too") — today the failure is invisible.

**Use cases.**
- HUD shows a "surface out of date — restart Live" badge instead of the user
  chasing a phantom bug after a redeploy.
- `gen.py` stamps a build id/hash into the generated surface; the Swift HUD (or
  `doctor.py`) compares the running value against the on-disk build and warns.
- Catches the "I deployed but forgot to restart" class of support questions.

**Sketch.** `gen.py` writes a `SURFACE_BUILD` constant (content hash or
timestamp) into the generated surface. `hud_client` includes it in its LAYOUT /
keepalive; the HUD holds the value it last saw written to disk and flags drift.

---

## 2. Chunked OSC for large payloads — **MEDIUM**

**What it is.** macOS `net.inet.udp.maxdgram` defaults to 9216 bytes. They chunk
big JSON at 4096 bytes across `…-chunk <i> <total> <frag>` messages followed by a
`…-done <total>` sentinel, so a single logical reply survives the datagram limit.
(lines 943–999, `_DEVICE_PARAMS_CHUNK_BYTES`)

**Why we want it.** We push mapping data on every device-focus change. A device
with many params or long names could exceed the limit and drop the datagram with
`EMSGSIZE` — an intermittent, size-dependent failure that's painful to diagnose.

**Use cases.**
- Harden `hud_client` LAYOUT / device bursts against oversized payloads.
- Any future "dump all params on this track" style feature (catalog, debugging).

**Note.** Medium, not high: our current per-slot messages are small, so this is
insurance rather than a live bug. Adopt the *known limit* now (document it),
implement chunking only if/when a payload approaches it.

---

## 3. Tier-2 observable-attribute discovery — **MEDIUM**

**What it is.** A universal test for "is this a real control": an attribute counts
if `add_<attr>_listener` exists **and** the bare attribute exists
(`a[4:-9] in names`). This reaches controls that are **not** in
`device.parameters` — Wavetable wavetable category/index, Simpler
`playback_mode`/`slicing_style`, routing selectors — plus `_resolve_attr_list`
to map their int values to enum names via Live's naming conventions
(`<attr>_list` / `<attr>s` / `available_<attr>s`, `_index→_list`, `y→ies`,
strip positional `_N`). (lines 1321–1416)

**Why we want it.** Our mapping + HUD naming only sees `device.parameters` today.
Some of the most useful things to name or map (osc wavetable, playback mode) live
outside that list. This is the general key to them.

**Use cases.**
- HUD names non-parameter controls (e.g. "One Shot", "Slicing") instead of blanks.
- Future mapping type that targets device *attributes*, not just parameters.
- Discovery tooling: dump every listenable control on a selected device.

**Note.** Medium: clearly valuable, but only pays off once we decide to surface
non-parameter controls. Land it behind that decision, not speculatively.

---

## 4. Occurrence-based param disambiguation — **LOW**

**What it is.** `_find_device_param` recurses rack chains in chain order and picks
the *Nth* device when several share a param name (Chorus + Reverb both expose
"Dry/Wet"); `_chain_index_of` reports the owning device's top-level chain index so
a highlight can auto-scope to the right panel. (lines 737–796)

**Why we want it.** Mostly a cross-check against our own `param_resolver.py`. If we
have an equivalent already, this is confirmation; if we resolve by name only, the
occurrence + chain-order walk is the more robust pattern.

**Use cases.**
- Resolve duplicate param names deterministically in a mapping.
- Reorder-safe panel scoping without the author hardcoding a chain index.

**Note.** Low: our resolver may already cover this, and duplicate-name collisions
are an edge case in our configs. Audit `param_resolver.py` first; adopt only the
gap.

---

## LOM gotchas — reference to fold into `dev-docs`

Our `dev-docs/Live.md` is an auto-generated signature dump; none of the practical
traps below are in it. Rating here = how likely it bites us / how load-bearing.

| Gotcha | Detail | Lines | Rating |
|---|---|---|---|
| `value_items` raises on continuous params | "Only quantized parameters have value items"; `hasattr` is True for *all* params so can't guard — check `is_quantized` first | 629–632 | **HIGH** |
| Internal `min`/`max` often normalized 0..1 | Useless for newer devices; use `str_for_value(min/max)` for real display units | 822–830, 900–906 | **HIGH** |
| `class_name` vs `class_display_name` | Simpler=`OriginalSimpler`, Sampler=`MultiSampler`, Wavetable=`InstrumentVector`; human names only in `class_display_name` (corroborates our `device-class-names` memory) | 2911–2918 | **HIGH** |
| `get_notes_extended` pitch-range raise | Raises if `from_pitch + pitch_span > 128`; except-path silently returns 0. Also dual API: extended→MidiNote objects vs legacy `get_notes`→tuples | 2235–2245 | **MED** |
| Scale lives on `Song`, not `Clip` | `root_note`/`scale_name`/`scale_intervals`; intervals is *either* a 12-element bool mask *or* an offset list | 2774–2803 | **MED** |
| Routing values are objects | RoutingType/RoutingChannel with `.display_name`; options via `available_<attr>s` | 1292–1319 | **MED** |
| Arrangement automation unreadable | No envelope `value_at_time`; must sample the live value as `current_song_time` crosses the beat | 44–49, 673–716, 3055–3075 | **MED** |
| Wavetable mod matrix is invisible | Not in `device.parameters` *or* a11y tree; only `get_modulation_value(target, source)` + `visible_modulation_target_names`. Sources have no name; UI labels ≠ LOM names (Pitch/Transpose) | 1024–1170 | **LOW** |
| Arrangement clips ≠ clip_slots | Use `track.arrangement_clips`; locate the owning track via `canonical_parent` (parent, then grandparent) | 257–281, 2348–2404 | **LOW** |
| View-visibility strings | `focused_document_view` ∈ `Arranger`/`Session`; `is_view_visible('Detail/Clip' \| 'Detail/DeviceChain' \| 'Browser')` | 233–240, 419–435 | **LOW** |
| Track-kind detection | `is_foldable` (group), `group_track` (parent), `can_be_armed`, `has_midi_input`; `Song.is_modified` (Live 11+) | 2057, 2861–2886, 1912–1923 | **LOW** |

### Anti-patterns observed (do NOT emulate)
- Bare `try/except: pass` around nearly every LOM access — a symptom of running
  blind with no test harness. We have a generator + pytest; stay stricter.
- A duplicate method definition once silently *shadowed* the richer one (Python
  keeps the last def) — their own comment at 2727–2734.
- `disconnect()` (2945) tears down song listeners but never walks
  `_device_param_watchers` / `_track_watchers` teardowns — a latent leak.

---

## Suggested order

1. **#1 SCRIPT_VERSION** (high value, self-contained, fixes a known pain).
2. Fold the **HIGH gotchas** into a `dev-docs/lom-gotchas.md` companion doc.
3. **#3 Tier-2 discovery** when we commit to surfacing non-parameter controls.
4. **#2 chunking** as insurance if a payload nears the limit.
5. **#4** only after auditing `param_resolver.py` for the gap.
