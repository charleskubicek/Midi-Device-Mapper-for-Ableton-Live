import unittest

from ableton_control_surface_as_code.gen_code import device_templates, GeneratedCodes
from ableton_control_surface_as_code.core_model import TrackInfo
from ableton_control_surface_as_code.model_device import DeviceWithMidi
from tests.builders import build_device_midi_mapping


class TestDeviceModeTemplates(unittest.TestCase):

    def test_device_mode_templates(self):
        device_with_midi = DeviceWithMidi(track=TrackInfo.selected(), device="selected",
                                                          midi_maps=[
                                                              build_device_midi_mapping(midi_number=21,parameter=1),
                                                              build_device_midi_mapping(midi_number=22,parameter=2),
                                                              build_device_midi_mapping(midi_number=23,parameter=3),
                                                              build_device_midi_mapping(midi_number=24,parameter=4),
                                                          ],
                                          custom_device_mappings={},
                                          parameter_page_nav=None)
        result = GeneratedCodes.merge_all(device_templates(device_with_midi, 'mode_1'))
        all_functions = "\n".join(result.listener_fns)
        print(all_functions)

        self.assertEqual(result.remove_listeners[0],
                         "self.knob_ch2_21_CC.remove_value_listener(self.knob_ch2_21_CC__mode_mode_1_p1_listener)")
        self.assertEqual(result.control_defs[0].number, 21)
        self.assertEqual(result.control_defs[1].number, 22)
        self.assertEqual(len(result.control_defs), 4)
        self.assertTrue('self.device_parameter_action(device, 1, 21, value, ' in all_functions)
        self.assertTrue('self.device_parameter_action(device, 2, 22, value, ' in all_functions)
        self.assertTrue('self.device_parameter_action(device, 3, 23, value, ' in all_functions)
        self.assertFalse('self.device_parameter_action(device, 5, value, ' in all_functions)
        self.assertFalse('self.device_parameter_action(device, 0, value, ' in all_functions)

        self.assertEqual(len(result.remove_listeners), 4)
        self.assertEqual(len(result.control_defs), 4)
        self.assertEqual(len(result.setup_listeners), 8)
        self.assertEqual(len(result.listener_fns), 40)