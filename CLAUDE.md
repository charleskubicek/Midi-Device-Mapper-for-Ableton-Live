# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

This is a code generator that takes NestedText (`.nt`) config files describing a MIDI controller layout and desired Ableton Live mappings, then produces Python control surface scripts that Ableton can load. Users never write Python — they write config files and this tool generates the Ableton MIDI Remote Script.

**Pipeline:** `.nt` mapping file → `gen.py` → Python control surface directory → `deploy.sh` → Ableton Live

## Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_gen.py

# Run a single test
poetry run pytest tests/test_gen.py::TestClassName::test_method_name

# Generate a control surface from a mapping file
poetry run python ableton_control_surface_as_code/gen.py live_surfaces/launch_control/ck_launch_control_16.nt

# Tail Ableton logs
./bin/tail_logs.sh
```

## Deployment

generating a script creates a new live surface in a directory in the same folder as the mapping, with the same name as the mapping file stem (e.g. `ck_launch_control_16/`) under /live_surfaces.
To deploy to Ableton, run `./deploy.sh`, in the generated folder, which copies all live surfaces to the Ableton MIDI Remote Scripts directory. After running this,
a live_surface called will be deployd to `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/ck_launch_control_16`
Ableton Life will need to be restarted, and the logs can be tailed with `./bin/tail_logs.sh` to confirm the new control surface is loading correctly, or to see failure messages.


## Architecture

### Config Files (input)
Two NestedText files per controller setup, typically in `live_surfaces/<controller-name>/`:
- **controller file** (e.g. `controller_lc.nt`): Describes the physical controller — rows of knobs/buttons/sliders with their MIDI channel, type (CC/note), and MIDI number ranges. Defines `light_colors`.
- **mapping file** (e.g. `ck_launch_control_16.nt`): References the controller file and maps encoder coordinates (e.g. `row-1:3`, `row-2:1-8`) to Ableton functions. Supports `modes` (switchable via a mode button) or flat `mappings`. Mapping types: `device`, `mixer`, `transport`, `track-nav`, `device-nav`, `functions`.

### Code Generation Pipeline (`ableton_control_surface_as_code/`)
1. **`gen.py`** — entry point; parses config, calls model builders, renders templates, copies output to a named directory
2. **`model_v2.py`** — parses the mapping `.nt` file into `RootV2` / `ModeGroupWithMidi`; resolves controller coords to `MidiCoords`
3. **`model_controller.py`** — parses the controller `.nt` file into `ControllerV2` with `ControlGroupPartV2` entries
4. **`core_model.py`** — shared Pydantic models: `MidiCoords`, `MixerMidiMapping`, `EncoderType`, `MidiType`, `TrackInfo`, etc.
5. **`encoder_coords.py`** — Lark grammar that parses the encoder coordinate syntax (`row-1:1-8`, `row-2:3 toggle`, etc.) into `EncoderCoords` with optional `EncoderRefinement`s (toggle, mode, map_mode_absolute)
6. **`model_mixer.py`, `model_device.py`, `model_transport.py`, `model_track_nav.py`, `model_device_nav.py`, `model_functions.py`** — one module per mapping type; each builds its `*WithMidi` model by resolving encoder coords → MIDI coords
7. **`gen_code.py`** — converts `*WithMidi` models into `GeneratedCode` dataclasses (Python code strings for init, listeners, setup/remove); templates are dispatched via `template_to_code` dict keyed on mapping type

### Templates & Output
- `templates/` contains Python template files with `$variable` substitutions (Python `string.Template`)
- `templates/surface_name/` is the per-surface structure: `__init__.py`, `surface_name.py`, `modules/main_component.py`
- `source_modules/` contains shared runtime Python modules (helpers, nav, listener, pythonosc) copied into every generated surface
- Generated output lands in the same directory as the mapping file, in a subdirectory named after the mapping file stem

### Live Surfaces
`live_surfaces/` contains real controller configs:
- `launch_control/` — Novation Launch Control XL with shift modes, device/mixer/function mappings
- `parks/` — Parks tool controller

### Modes / FSM
The mode system is a finite state machine: a single mode button cycles through named modes. Each mode has its own set of mappings. Shift-type modes work differently (held, not toggled). `ModeGroupWithMidi` in `model_v2.py` holds the FSM; `gen.py` renders the mode setup/teardown code.
