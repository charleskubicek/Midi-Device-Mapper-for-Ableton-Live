"""The mode button gets a HUD label (hud-quick-fixes-plan §1).

`collect_mode_labels` walks a mode's *mappings*; the mode button is not a
mapping, so its cell rendered as the empty-slot sentinel in every mode. It is
the one control whose meaning never changes with the mode, so it carries the
same label in all of them.
"""
import ast
import unittest
from pathlib import Path

from ableton_control_surface_as_code.core_model import EncoderType, MidiType
from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_controller import (
    ControllerV2, ControllerRawV2, ControlGroupPartV2,
)
from ableton_control_surface_as_code.model_v2 import HudMode, build_validated_model

_CONTROLLER = """
light_colors:
    off: 12
    red_low: 13
    green_full: 60

control_groups:
    -
        layout: grid
        number: 1
        type: button
        midi_channel: 1
        midi_type: note
        midi_range: C1-DS2
        rows: 4
        columns: 4
    -
        layout: grid
        number: 2
        type: button
        midi_channel: 1
        midi_type: note
        midi_range: B2-D4
        rows: 4
        columns: 4
        right_of: 1
"""

_HEADER = """
controller: controller.nt
ableton_dir: /Applications/Ableton Live 12 Suite.app
remote_on: false
hud: on
show-hud-on: selection
"""

_MAPPING = """
mode-button:
    button: grid-2:4::1
    type: $mode_type
modes:
    -
        name: main_mode
        on_color: red_low
        mappings:
            -
                type: mixer
                track: selected
                mappings:
                    mute: grid-2:1
    -
        name: shift_mode
        on_color: green_full
        mappings:
            -
                type: mixer
                track: selected
                mappings:
                    solo: grid-2:2
"""

# grid-2 is the second button block: its cells start at button wire index 16,
# and grid row 4 / col 1 is offset 12 within the block.
_MODE_BUTTON_SLOT = ('button', 28)


def _controller():
    return ControllerV2.build_from(ControllerRawV2(**{
        'light_colors': {},
        'control_groups': [
            ControlGroupPartV2(layout='grid', number=1, type=EncoderType.button,
                               midi_channel=1, midi_type=MidiType.note,
                               midi_range='C1-DS2', rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type=EncoderType.button,
                               midi_channel=1, midi_type=MidiType.note,
                               midi_range='B2-D4', rows=4, columns=4, right_of=1),
        ],
    }))


def _labels(mode_type='shift', **kwargs):
    _root, _c, modes = build_validated_model(
        _HEADER + _MAPPING.replace('$mode_type', mode_type), Path('.'),
        resolve_controller=lambda root: (_CONTROLLER, 'controller.nt'),
        mapping_source='test mapping')
    vars = generate_code_as_template_vars(modes, controller=_controller(), **kwargs)
    return ast.literal_eval(vars['mode_hud_labels'])


class TestModeButtonLabel(unittest.TestCase):

    def test_shift_button_is_labelled_in_every_mode(self):
        labels = _labels('shift')
        for mode in ('main_mode', 'shift_mode'):
            self.assertEqual(('Shift', ''), labels[mode][_MODE_BUTTON_SLOT],
                             f"mode {mode} is missing the shift label")

    def test_switch_mode_button_reads_mode(self):
        labels = _labels('switch')
        self.assertEqual(('Mode', ''), labels['main_mode'][_MODE_BUTTON_SLOT])

    def test_device_only_hud_still_has_no_static_labels(self):
        # device_only means "only the focused device's parameters"; the mode
        # button is chrome, so it stays out just like every other static label.
        labels = _labels('shift', hud_mode=HudMode.DeviceOnly)
        self.assertEqual({}, labels['main_mode'])

    def test_a_mapping_cannot_share_the_mode_button_coord(self):
        # Why the label can be assigned unconditionally: a mapping on the
        # mode-button coord is rejected at validation time, so the label can
        # never clobber a real binding.
        mapping = _MAPPING.replace('$mode_type', 'shift').replace(
            "                    solo: grid-2:2",
            "                    solo: grid-2:4::1")
        with self.assertRaises(GenError) as ctx:
            build_validated_model(
                _HEADER + mapping, Path('.'),
                resolve_controller=lambda root: (_CONTROLLER, 'controller.nt'),
                mapping_source='test mapping')
        self.assertIn("mode-button", str(ctx.exception))
