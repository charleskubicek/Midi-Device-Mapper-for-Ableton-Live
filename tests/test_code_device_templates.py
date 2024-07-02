import unittest

from ableton_control_suface_as_code.code import device_mode_templates
from ableton_control_suface_as_code.core_model import TrackInfo
from ableton_control_suface_as_code.model_device import DeviceWithMidi
from tests.builders import build_device_midi_mapping


class TestDeviceModeTemplates(unittest.TestCase):

    def test_device_mode_templates(self):
        device_with_midi = DeviceWithMidi(track=TrackInfo.selected(), device="selected",
                                                          midi_maps=[
                                                              build_device_midi_mapping(midi_number=21,parameter=1),
                                                              build_device_midi_mapping(midi_number=22,parameter=2),
                                                              build_device_midi_mapping(midi_number=23,parameter=3),
                                                              build_device_midi_mapping(midi_number=24,parameter=4),
                                                          ])
        result = device_mode_templates(device_with_midi, 'mode_1')
        all_functions = "\n".join(result.listener_fns)

        self.assertEqual(result.remove_listeners[0],
                         "self.knob_ch2_21_CC.remove_value_listener(self.knob_ch2_21_CC__mode_mode_1_p1value)")
        self.assertEqual(result.control_defs[0].number, 21)
        self.assertEqual(result.control_defs[1].number, 22)
        self.assertEqual(len(result.control_defs), 4)
        self.assertTrue('self.device_parameter_action(device, 1, value, ' in all_functions)
        self.assertTrue('self.device_parameter_action(device, 2, value, ' in all_functions)
        self.assertTrue('self.device_parameter_action(device, 3, value, ' in all_functions)
        self.assertFalse('self.device_parameter_action(device, 5, value, ' in all_functions)
        self.assertFalse('self.device_parameter_action(device, 0, value, ' in all_functions)

        self.assertEqual(len(result.remove_listeners), 4)
        self.assertEqual(len(result.control_defs), 4)
        self.assertEqual(len(result.setup_listeners), 4)
        self.assertEqual(len(result.listener_fns), 20)