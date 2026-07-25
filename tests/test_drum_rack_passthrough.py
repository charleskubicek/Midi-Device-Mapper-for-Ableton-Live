"""Drum-rack MIDI pass-through (ai-coding/plans/drum-rack-passthrough-plan.md).

While a drum rack is focused, the controls listed under `drum-rack-passthrough`
stop being forwarded to the script, so their notes reach Live's track input and
play + select drum pads natively. These tests cover everything up to the
_Framework boundary: config parsing, coord resolution, and the element names
baked into the generated surface. The runtime assignment
(`element.suppress_script_forwarding = ...`) can only be exercised inside
Ableton, so the template is asserted structurally instead.
"""
import ast
import unittest
from pathlib import Path

from ableton_control_surface_as_code.behavior_doc import build_behavior_doc
from ableton_control_surface_as_code.core_model import EncoderType, MidiType
from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_controller import (
    ControllerV2, ControllerRawV2, ControlGroupPartV2,
)
from ableton_control_surface_as_code.model_v2 import build_validated_model

_TEMPLATE = (Path(__file__).resolve().parent.parent
             / 'templates' / 'surface_name' / 'modules' / 'main_component.py')

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
        type: knob
        midi_channel: 1
        midi_type: CC
        midi_range: 16-31
        rows: 4
        columns: 4
        right_of: 1
    -
        layout: grid
        number: 3
        type: button
        midi_channel: 1
        midi_type: note
        midi_range: B2-D4
        rows: 4
        columns: 4
        right_of: 2
"""

_HEADER = """
controller: controller.nt
ableton_dir: /Applications/Ableton Live 12 Suite.app
remote_on: false
hud: on
show-hud-on: selection
"""


def _controller():
    return ControllerV2.build_from(ControllerRawV2(**{
        'light_colors': {},
        'control_groups': [
            ControlGroupPartV2(layout='grid', number=1, type=EncoderType.button,
                               midi_channel=1, midi_type=MidiType.note,
                               midi_range='C1-DS2', rows=4, columns=4),
            ControlGroupPartV2(layout='grid', number=2, type=EncoderType.knob,
                               midi_channel=1, midi_type=MidiType.CC,
                               midi_range='16-31', rows=4, columns=4, right_of=1),
            ControlGroupPartV2(layout='grid', number=3, type=EncoderType.button,
                               midi_channel=1, midi_type=MidiType.note,
                               midi_range='B2-D4', rows=4, columns=4, right_of=2),
        ],
    }))


def _build(mapping_text):
    return build_validated_model(
        _HEADER + mapping_text, Path('.'),
        resolve_controller=lambda root: (_CONTROLLER, 'controller.nt'),
        mapping_source='test mapping')


# grid-1 is notes 36-51 on channel 1 — the drum rack's visible-bank pad range.
_GRID_1_NOTES = list(range(36, 52))
_GRID_1_ELEMENTS = [f"button_ch1_{n}_note" for n in _GRID_1_NOTES]

_TWO_MODES = """
mode-button:
    button: grid-3:4::1
    type: shift
modes:
    -
        name: main_mode
        on_color: red_low
        drum-rack-passthrough: grid-1:1-16
        mappings:
            -
                type: device
                track: selected
                device: selected
                mappings:
                    button:
                        range: grid-1:1-16
                        slots: 1-16
    -
        name: shift_mode
        on_color: green_full
        mappings:
            -
                type: device
                track: selected
                device: selected
                mappings:
                    sequencer:
                        range: grid-1:1-16
"""


class TestPassthroughConfig(unittest.TestCase):

    def test_absent_key_means_no_passthrough(self):
        _root, _controller_v2, modes = _build("""
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            button:
                range: grid-1:1-16
                slots: 1-16
""")
        self.assertEqual({}, {k: v for k, v in modes.drum_passthrough.items() if v})

    def test_mode_key_resolves_to_the_declared_coords(self):
        _root, _controller_v2, modes = _build(_TWO_MODES)

        main = modes.drum_passthrough['main_mode']
        self.assertEqual(_GRID_1_NOTES, [mc.number for mc in main])
        self.assertTrue(all(mc.channel == 1 for mc in main))
        self.assertTrue(all(mc.type == MidiType.note for mc in main))

        # The sequencer mode keeps consuming those notes — it needs them.
        self.assertEqual([], modes.drum_passthrough.get('shift_mode', []))

    def test_string_and_list_forms_are_equivalent(self):
        _r1, _c1, one = _build(_TWO_MODES)
        _r2, _c2, many = _build(_TWO_MODES.replace(
            "        drum-rack-passthrough: grid-1:1-16\n",
            "        drum-rack-passthrough:\n            - grid-1:1-8\n            - grid-1:9-16\n"))
        self.assertEqual([mc.number for mc in one.drum_passthrough['main_mode']],
                         [mc.number for mc in many.drum_passthrough['main_mode']])

    def test_root_level_key_covers_a_modeless_mapping(self):
        _root, _controller_v2, modes = _build("""
drum-rack-passthrough: grid-1:1-16
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            button:
                range: grid-1:1-16
                slots: 1-16
""")
        coords = [c for cs in modes.drum_passthrough.values() for c in cs]
        self.assertEqual(_GRID_1_NOTES, [mc.number for mc in coords])

    def test_root_level_key_is_the_default_for_modes_that_dont_declare_one(self):
        text = _TWO_MODES.replace(
            "        drum-rack-passthrough: grid-1:1-16\n", "")
        _root, _controller_v2, modes = _build("drum-rack-passthrough: grid-1:1-16\n" + text)
        self.assertEqual(_GRID_1_NOTES,
                         [mc.number for mc in modes.drum_passthrough['main_mode']])
        self.assertEqual(_GRID_1_NOTES,
                         [mc.number for mc in modes.drum_passthrough['shift_mode']])

    def test_bad_coords_are_reported_as_a_config_error(self):
        with self.assertRaises(GenError) as ctx:
            _build(_TWO_MODES.replace("drum-rack-passthrough: grid-1:1-16",
                                      "drum-rack-passthrough: grid-1:1-99"))
        self.assertIn("grid-1", str(ctx.exception))


class TestPassthroughCodegen(unittest.TestCase):

    def test_element_names_are_baked_per_mode(self):
        _root, controller, modes = _build(_TWO_MODES)
        vars = generate_code_as_template_vars(modes, controller=controller)

        by_mode = ast.literal_eval(vars['drum_passthrough_by_mode'])
        self.assertEqual(_GRID_1_ELEMENTS, by_mode['main_mode'])
        self.assertEqual([], by_mode.get('shift_mode', []))
        self.assertEqual("'main_mode'", vars['drum_passthrough_default_mode'])

    def test_no_passthrough_yields_an_empty_table(self):
        _root, controller, modes = _build(_TWO_MODES.replace(
            "        drum-rack-passthrough: grid-1:1-16\n", ""))
        vars = generate_code_as_template_vars(modes, controller=controller)
        by_mode = ast.literal_eval(vars['drum_passthrough_by_mode'])
        self.assertEqual([], [n for names in by_mode.values() for n in names])


class TestPassthroughBehaviorDoc(unittest.TestCase):
    """BEHAVIOR.md documents what one press does — and on a drum rack these
    buttons do something entirely different from the table row above, so the doc
    would be actively misleading without saying so."""

    def test_released_controls_are_documented(self):
        _root, controller, modes = _build(_TWO_MODES)
        doc = build_behavior_doc(modes, controller=controller, surface_name='surf')
        self.assertIn("drum rack", doc.lower())
        self.assertIn("main_mode", doc)
        self.assertIn("row-1:1", doc)

    def test_no_section_when_nothing_is_released(self):
        _root, controller, modes = _build(_TWO_MODES.replace(
            "        drum-rack-passthrough: grid-1:1-16\n", ""))
        doc = build_behavior_doc(modes, controller=controller)
        self.assertNotIn("pass-through", doc.lower())


class TestPassthroughRuntimeTemplate(unittest.TestCase):
    """The generated surface must actually apply the table. Structural asserts:
    the runtime effect (Live dropping the element from its forwarding registry)
    only exists inside Ableton."""

    def _template(self):
        return _TEMPLATE.read_text()

    def test_template_suppresses_forwarding_rather_than_dropping_listeners(self):
        src = self._template()
        self.assertIn("suppress_script_forwarding", src)

    def test_sync_is_called_on_mode_and_device_changes(self):
        src = self._template()
        for caller in ("def goto_mode(", "def on_device_selected(",
                       "def on_selected_track_changed(", "def _on_track_devices_changed(",
                       "def update_selected_device("):
            start = src.index(caller)
            nxt = src.find("\n    def ", start + 1)
            body = src[start:nxt if nxt != -1 else len(src)]
            self.assertIn("sync_drum_passthrough", body,
                          f"{caller} must re-assert drum pass-through")


if __name__ == '__main__':
    unittest.main()
