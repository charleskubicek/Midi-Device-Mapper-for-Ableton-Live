# Phase 1 Prototype Spec — Device Mapping

**Note on sourcing:** this spec assumes the reader has access to **only** `docs/user_manual.md`
(included below in §3 as direct quotes/extracts) and nothing else from this codebase — no source
code, no other docs, no real device-parameter catalogs. Every domain term and every piece of
sample data here is taken verbatim from that manual. Where the manual doesn't give enough sample
data to make a convincing prototype, that's called out explicitly as a placeholder (§6) rather
than invented.

**No UI is prescribed yet.** This document defines *what the prototype must let someone do*, as
user stories, not how it should look. The interface does not need to follow any particular
platform's conventions (it is not required to look like a Mac app) — pick whatever interface
patterns best serve the stories below.

---

## 1. What this tool is (for context only)

Per the manual: this is a system that compiles plain-text configuration files into **Python
control surface scripts** that Ableton Live loads natively. A person never writes that Python
themselves — they write two config files, and the compiler ("`gen.py`") generates the code:

1. **A controller file** — describes the physical hardware: rows/groups of knobs, buttons, or
   sliders, each with a MIDI channel, type (CC or note), and a range of MIDI numbers.
2. **A mapping file** — references the controller file and binds physical controls (by coordinate,
   e.g. `row-1:3`) to Ableton actions: device parameters, mixer controls, transport, navigation, or
   custom functions. Mappings are grouped into named **modes** (e.g. a "shift" button can swap to a
   second mode while held).

Once compiled, a `deploy.sh` script copies the generated files into Ableton's MIDI Remote Scripts
folder, and Ableton (after a restart, or instantly via a live-reload command) loads it as a
control surface.

That's the entire mental model needed. Nothing below requires any other source.

## 2. Scope of this prototype ("Phase 1")

- The **controller file and mapping file already exist** — a user has them in hand. This
  prototype loads and visualizes them; it does not create a controller file from scratch or do
  MIDI learn.
- Only **one mode** is in scope — treat the mapping file as if it has a single mode (the manual
  notes that if a mapping file omits `modes:`, the compiler wraps flat `mappings:` into one
  default mode — that's the shape to assume here).
- Of all the mapping types the manual describes (`device`, `mixer`, `functions`, `track-nav`,
  `device-nav`, `transport`, `parameter-pager`, `clip`), **only `device` mappings are editable**
  in this prototype. Every other mapping type that exists in the loaded files should be visible,
  for context, but not editable.
- **Deploying to Ableton Live is simulated.** The prototype cannot actually run `gen.py` or copy
  files into an Ableton install — it should walk through the same steps the manual describes
  (compile → `deploy.sh` → restart/reload → confirm via logs) as a guided, mocked sequence that
  ends in believable success messaging.

## 3. Domain concepts (verbatim from the manual)

These are the only domain facts available — treat this as the full glossary:

- **Coordinate grammar**: physical controls are addressed by strings like `row-1:3` (row 1,
  column 3), `row-1:1-8` (a range), or `row-1:5-7,row-2:5-7` (multiple ranges concatenated).
- **`device` mapping** controls a device's parameters for a track (`track: selected` or a
  specific track) and device (`device: selected` or a specific device). Its sub-keys:
  - **`encoder-list`** — maps one or more coordinate ranges to a list of **slots** (1-based
    positions), e.g. `{ range: row-1:1-8, slots: 1-8 }`.
  - **`on-off`** — a single button coordinate that toggles the device's on/off activator.
  - **`button` / `button-list`** — mirrors `encoder-list` but for device *switch* slots (e.g.
    `{ range: row-3:5-8, slots: 1-4 }`).
- **Slots are not fixed to one named parameter.** What a slot actually controls depends on which
  device is currently selected/focused in Ableton, resolved via a curated mapping table
  (`custom_device_mappings.json`). For a given device, that table lists, in order, the
  parameters considered most useful — the manual calls this curation **"Best of Bank" (BOB)** —
  and optionally **grouped encoders**, where one control's target switches depending on the
  current value of another parameter (the manual's example: an LFO control that targets "Rate"
  or "Time" depending on the device's `LFO T Mode` setting).
- If a device has more parameters than physical controls, a **`parameter-pager`** mapping lets
  `inc`/`dec` buttons page through additional banks — **out of scope for this prototype** (treat
  every device as showing only its first/BOB page).
- Other mapping types present in a file but **not editable** here: `mixer` (volume, pan, mute,
  solo, arm, sends), `functions` (custom Python actions bound to buttons), `track-nav` /
  `device-nav` (selection movement), `transport` (play/record/loop), `clip` (clip-detail
  controls).
- **Build & deploy** (per the manual, §6): compile with
  `poetry run python ableton_control_surface_as_code/gen.py <mapping>.nt`; this "builds a custom
  python control surface package inside the mapping directory." Then run `./deploy.sh` inside
  that generated folder, which "moves the generated surface files to the Ableton directory."
  After deploying, Ableton needs to load the new surface (restart, or — per §6's "Live Reloading"
  — running `python update.py reload` to apply changes to an already-running Ableton without a
  restart). The manual gives one example deploy destination:
  `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/` — fine to
  reuse as the example destination, but treat it as one example path, not a platform requirement
  for the prototype's own UI.

---

## 4. User stories

These are organized by the natural flow through the tool, but the prototype doesn't need to
implement them as separate screens — group or sequence them however best fits whatever interface
is designed.

### Loading and understanding an existing setup

- **As a user**, I want to load my existing controller file and mapping file, so that the tool
  shows me what I already have without me re-describing it.
- **As a user**, I want to see every physical control my controller defines (each row/group of
  knobs, buttons, or sliders), so that I recognize my actual hardware in the tool.
- **As a user**, I want to see which mode is active (treating the file as having one mode for
  now), so that I understand which set of mappings I'm looking at.
- **As a user**, I want to see what every control in that mode currently does — whether it's a
  device parameter, a mixer control, a function, a navigation action, or transport — so that I
  have a complete picture of my mapping, even though I can only edit the device ones.
- **As a user**, I want non-device mappings (mixer, functions, nav, transport) to be clearly
  marked as "not editable here," so that I don't waste time trying to change them and don't
  mistake this prototype for the full editor.

### Understanding device mappings

- **As a user**, I want to see, for each control involved in a `device` mapping, which **slot**
  it's assigned to (e.g. "slot 3"), so that I understand the underlying assignment independent of
  any specific device.
- **As a user**, I want an explanation, in plain language, of *why* a slot's name isn't fixed
  (because it depends on whatever device is currently selected), so that the "slot" concept makes
  sense rather than seeming broken or incomplete.

### Previewing against a real device

- **As a user**, I want to choose a device to "preview" my mapping against, so that I can see
  real parameter names instead of abstract slot numbers.
- **As a user**, I want every device-mapped control's label to update immediately when I change
  the previewed device, so that I can compare how the same physical layout serves different
  devices without re-mapping anything.
- **As a user**, I want a slot that the previewed device doesn't have a parameter for (because
  the device exposes fewer parameters than I have controls) to be visibly different from an
  assigned slot, so that I don't mistake "nothing here" for a real mapping.
- **As a user**, when a control's target depends on another parameter's current value (a grouped
  encoder, e.g. switching between "Rate" and "Time"), I want to see which target is currently
  active for that group, so that I understand it's context-sensitive rather than ambiguous.

### Editing the device mapping

- **As a user**, I want to change which coordinate range covers a given list of slots, so that I
  can rewire which physical knobs/buttons drive which slots.
- **As a user**, I want to change which slots a coordinate range is assigned to, so that I can
  reorder or renumber the mapping.
- **As a user**, I want to be told immediately if the number of physical controls in a range
  doesn't match the number of slots I've listed, so that I catch a mismatch before trying to
  compile it (the manual treats this kind of thing as a generation-time error today; I want to
  see it before that point).
- **As a user**, I want to designate one button as the device's on/off toggle, so that I can wire
  up `on-off` the same way the mapping file supports.

### Deploying

- **As a user**, I want to trigger a "deploy to Ableton Live" action from inside the tool, so
  that I don't have to drop to a terminal to run the compile/deploy commands myself.
- **As a user**, I want to see the deploy proceed through the real stages described in the manual
  — compiling, then copying files into Ableton's MIDI Remote Scripts location — so that the
  process feels like the real tool, not a black box.
- **As a user**, I want to be told plainly, at the end, that I need to restart Ableton (or use
  the live-reload command if Ableton is already running) to actually load the new mapping, so
  that I don't expect it to take effect with no further action.
- **As a user**, I want confirmation framed the way the manual frames it — "check the logs to
  confirm the surface loaded" — so that the guidance matches what I'd actually do.
- **As a user**, I want it to be obvious that this deploy is a simulation in this prototype (no
  real Ableton install is touched), so that I don't think something happened on my machine that
  didn't.

---

## 5. Sample data (taken directly from the manual's own examples)

Use these so the prototype shows real-looking content, sourced only from `docs/user_manual.md`:

**Controller** (manual §1 example):
- Row 1: knobs, MIDI channel 3, CC, range 21–28 (8 knobs).
- Row 2: knobs, MIDI channel 3, CC, numbers 29, 42, 43, 44, 45, 46, 47, 48 (8 knobs), positioned
  under row 1.
- Row 3: buttons, MIDI channel 9, note, numbers A-2, C-1, CS1, D1, C1, C3, F1, G1 (8 buttons),
  under row 2.
- Row 4: buttons, MIDI channel 3, CC, numbers 114, 115 (2 buttons), to the right of row 2.

**Mapping** (manual §2 example), treated as the single in-scope mode:
- Mode `main_mode` (LED color `red_low`):
  - `device` mapping, track: selected, device: selected.
    - `encoder-list`: range `row-1:1-8` → slots `1-8`.
    - `on-off`: `row-3:4`.
- (The manual's example also has a `shift_mode` with a `mixer` mapping — present in the file for
  context, but out of scope to edit, per §2 above.)

**Device parameter example** (manual §4, the only fully worked device example given) — use this
as the one "real" device in the preview dropdown:
- Device class `AutoFilter2`, device name **"Auto Filter"**.
  - Encoders: slot 1 → **Frequency** (display "Freq"), slot 2 → **Resonance** (display "Reso"),
    and a grouped encoder controlled by **LFO T Mode**: when `LFO T Mode` = 0, target slot 15
    displayed as **"L Rate"**; when = 1, target slot 16 displayed as **"L Time"**.
  - Buttons: slot 4 → **Filter Type**; slot 14 → **LFO T Mode** (a `min_max` toggle button —
    pressing it alternates the parameter between its minimum and maximum).

## 6. Placeholder note (explicitly flagged, not invented as fact)

The manual confirms that a full catalog of curated device parameter names lives in
`custom_device_mappings.json`, but that file's contents aren't part of this spec's source
material. To demonstrate the "switch device, labels change" story with more than one device,
add **one or two placeholder devices** to the preview dropdown (e.g. "Device B", "Device C")
with generic labels ("Param 1", "Param 2", …) — clearly distinguishable from the real "Auto
Filter" example, and understood as stand-ins to be replaced with real catalog data in a later
pass, not as accurate Ableton data.

## 7. Out of scope

MIDI learn; authoring a controller file from scratch; multiple/shift modes; parameter paging
(`parameter-pager`, standard banks beyond BOB); editing any mapping type other than `device`;
editing track/device targeting beyond "selected"; the floating HUD app and its live overlay;
Faderfox EC4 text feedback; a real (non-simulated) compile or deploy; any platform-specific UI
chrome.
