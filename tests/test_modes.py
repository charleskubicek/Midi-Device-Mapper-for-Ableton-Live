import unittest
from ableton_control_surface_as_code.core_model import MidiCoords, EncoderType, MidiType
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi, ModeType, ModeButtonWithMidi
from tests.builders import midi_coords_ch2_cc_50_knob, build_midi_device_mapping


class TestModes(unittest.TestCase):

    def test_fsm_function(self):

        mode_mappings = [
            ("mode_1", [build_midi_device_mapping(param=1)]),
            ("mode_2", [build_midi_device_mapping(param=1)])
        ]
        on_colours = [
            ("mode_1", 0),
            ("mode_2", 1)
        ]

        mode_group = ModeGroupWithMidi(
            mappings=mode_mappings,
            mode_button=ModeButtonWithMidi(button=midi_coords_ch2_cc_50_knob(), on_colors=on_colours, type=ModeType.Switch))

        expected_output = mode_group.fsm()

        self.assertEqual(expected_output[0].next, 'mode_2')
        self.assertEqual(expected_output[1].next, 'mode_1')
        self.assertEqual(expected_output[0].is_shift, False)
        self.assertEqual(expected_output[1].is_shift, False)
        self.assertEqual(expected_output[0].color, "0")
        self.assertEqual(expected_output[1].color, "1")

    def test_headless_fsm_without_mode_button(self):
        # A composition secondary declares modes but no physical mode-button; its
        # FSM is driven remotely. fsm() must still yield wired mode data (derived
        # from the mappings), with no colour and no local shift gesture.
        mode_mappings = [
            ("main_mode", [build_midi_device_mapping(param=1)]),
            ("shift_mode", [build_midi_device_mapping(param=1)]),
        ]
        mode_group = ModeGroupWithMidi(mappings=mode_mappings, mode_button=None)

        fsm = mode_group.fsm()
        self.assertEqual([m.name for m in fsm], ["main_mode", "shift_mode"])
        self.assertEqual(fsm[0].next, "shift_mode")
        self.assertEqual(fsm[1].next, "main_mode")
        self.assertEqual(fsm[0].color, "None")
        self.assertFalse(fsm[0].is_shift)

    def test_single_mode_without_button_has_empty_fsm(self):
        mode_group = ModeGroupWithMidi(
            mappings=[("only", [build_midi_device_mapping(param=1)])], mode_button=None)
        self.assertEqual(mode_group.fsm(), [])
