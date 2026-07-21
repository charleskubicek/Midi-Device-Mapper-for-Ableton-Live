# MIDI Device Mapper for Ableton

[![Build Status](https://github.com/charleskubicek/Midi-Device-Mapper-for-Ableton/actions/workflows/python-app.yml/badge.svg)](https://github.com/charleskubicek/Midi-Device-Mapper-for-Ableton/actions/workflows/python-app.yml)

Download the latest release [here](https://github.com/charleskubicek/Midi-Device-Mapper-for-Ableton-Live/releases/latest).

User guide is available [here](./guide.md).

This repository contains a MIDI mapping tool designed for Ableton Live, allowing for customised MIDI device mappings to Ableton live.

Mappings are made in a file between MIDI controls (buttons, sliders and controllers) and many Ableton functions.

Specific features include:

- **Multiple Modes**: Switch between various control modes, offering flexibility in device and track management.
- **Smart Synth Zoning**: Fixed semantic 32-pot and 16-button layouts for enrolled synthesizers (Wavetable, Drift, Operator, Analog) with zone color coding and area-based button matrices.
- **User and Transport Functions**: Customizable user functions alongside transport controls like play, stop, and record.
- **Device and Track Navigation**: Directly navigate to named top-level devices or tracks by name.
- **Custom Encoder Ranges**: Define custom min/max ranges for encoder values for finer control.
- **Python Functions**: The ultimate customisation—call any function of the Ableton API combined with your own workflow logic, with custom HUD labels and SF Symbol icons (`@hud_name`).
- **HUD Overlay**: A companion macOS app (`ableton_hud`) shows a transparent floating overlay with real-time dial/button assignments, summon & input-driven auto-hide modes, zone color tinting, and grid dividers.