import unittest

from ableton_control_surface_as_code.behavior_doc import build_behavior_doc, coord_label
from ableton_control_surface_as_code.core_model import MidiCoords, EncoderType, EncoderMode, TrackInfo
from ableton_control_surface_as_code.encoder_coords import Momentary
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi
from ableton_control_surface_as_code.model_device import DeviceWithMidi, DeviceParameterMidiMapping
from ableton_control_surface_as_code.model_functions import FunctionsWithMidi, FunctionsMidiMapping
from tests.builders import build_1_group_controller, build_functions_with_midi


def _button(number=51, refs=None):
    return MidiCoords(channel=1, type="CC", number=number, encoder_type=EncoderType.button,
                      encoder_mode=EncoderMode.Absolute, source_info="tests", encoder_refs=refs or [])


class TestBehaviorDoc(unittest.TestCase):
    def test_method_call_button_default_is_press_once(self):
        m = ModeGroupWithMidi(mappings=[("main", [build_functions_with_midi()])], mode_button=None)
        doc = build_behavior_doc(m, surface_name="surf")
        self.assertIn("fires once, on press", doc)
        self.assertIn("functions", doc)
        self.assertIn("# Button behavior — surf", doc)

    def test_momentary_function_documented_as_both_edges(self):
        fn = FunctionsWithMidi(midi_maps=[FunctionsMidiMapping(
            midi_coords=[_button(refs=[Momentary.instance()])],
            function_name="back8", parameter_len=0)])
        m = ModeGroupWithMidi(mappings=[("main", [fn])], mode_button=None)
        doc = build_behavior_doc(m)
        self.assertIn("press *and* release", doc)
        self.assertIn("`momentary`", doc)

    def test_device_param_button_default_toggles(self):
        dev = DeviceWithMidi(track=TrackInfo.selected(), device="selected",
                             midi_maps=[DeviceParameterMidiMapping(midi_coords=[_button()], parameter=3)])
        m = ModeGroupWithMidi(mappings=[("main", [dev])], mode_button=None)
        doc = build_behavior_doc(m)
        self.assertIn("toggles the parameter", doc)
        self.assertIn("device parameter 3", doc)

    def test_knob_param_is_not_listed(self):
        knob = MidiCoords(channel=1, type="CC", number=21, encoder_type=EncoderType.knob,
                          encoder_mode=EncoderMode.Absolute, source_info="tests", encoder_refs=[])
        dev = DeviceWithMidi(track=TrackInfo.selected(), device="selected",
                             midi_maps=[DeviceParameterMidiMapping(midi_coords=[knob], parameter=1)])
        m = ModeGroupWithMidi(mappings=[("main", [dev])], mode_button=None)
        doc = build_behavior_doc(m)
        self.assertIn("No buttons mapped", doc)

    def test_coord_label_reverse_maps_via_controller(self):
        controller = build_1_group_controller(midi_range="21-28")
        mc = controller.control_groups[0].midi_coords[2]  # row-1:3
        self.assertEqual(coord_label(controller, mc), "row-1:3")

    def test_coord_label_falls_back_without_controller(self):
        self.assertEqual(coord_label(None, _button(number=55)), "ch1/CC55")


if __name__ == "__main__":
    unittest.main()
