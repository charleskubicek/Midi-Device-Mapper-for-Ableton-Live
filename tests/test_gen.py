import unittest
from difflib import Differ

from autopep8 import fix_code

from ableton_control_suface_as_code.code import generate_lom_listener_action, build_live_api_lookup_from_lom
from ableton_control_suface_as_code.core_model import MidiType, MixerWithMidi, \
    MidiCoords, MixerMidiMapping, EncoderType, EncoderCoords, TrackInfo
from ableton_control_suface_as_code.model_device import DeviceMidiMapping, DeviceWithMidi
# from ableton_control_suface_as_code import gen
from ableton_control_suface_as_code.gen import device_mode_templates, generate_mode_code_in_template_vars
from ableton_control_suface_as_code.model_v2 import ModeGroupWithMidi
from tests.builders import build_mixer_with_midi, build_midi_device_mapping, build_device_midi_mapping
from builders import build_mixer_with_midi

differ = Differ()


def diff(a, b):
    return ''.join(differ.compare(a.split("\n"), b.split("\n")))


class TestGen(unittest.TestCase):

    def test_generate_code_in_template_vars(self):
        mixer_with_midi = build_mixer_with_midi(api_fn='pan')

        m = ModeGroupWithMidi(mappings={ "mode_1": [mixer_with_midi]})

        res = generate_mode_code_in_template_vars(m)
        self.assertGreater(len(res['code_creation']), 1)

    def test_generate_lister_fn(self):
        n = 1
        parameter = 2

        expected_output = """
def fn(self, value):
    device = lom_value
    self.device_parameter_action(device, 2, value, "fn")
    """

        expected_output = fix_code(expected_output)
        generated = fix_code("\n".join(generate_lom_listener_action(parameter, "lom_value", 'fn', "dbg")))

        print(generated)

        self.assertEqual(generated, expected_output, diff(generated, expected_output))

    def test_encoder_template(self):
        # device_with_midi = build_mode_model_v1([DeviceV1.model_validate(device_mapping)], ControllerV1.model_validate(controller))
        device_with_midi = DeviceWithMidi.model_construct(track=TrackInfo.selected(), device="selected",
                                                          midi_range_maps=[
                                                              build_device_midi_mapping(midi_number=21,parameter=1),
                                                              build_device_midi_mapping(midi_number=22,parameter=2),
                                                              build_device_midi_mapping(midi_number=23,parameter=3),
                                                              build_device_midi_mapping(midi_number=24,parameter=4),
                                                          ])
        result = device_mode_templates(device_with_midi, 'mode_1')

        self.assertEqual(result.remove_listeners[0],
                         "self.knob_ch2_21_CC.remove_value_listener(self.knob_ch2_21_CC__mode_mode_1_p1value)")
        self.assertEqual(result.control_defs[0].number, 21)
        self.assertEqual(result.control_defs[1].number, 22)
        self.assertEqual(len(result.control_defs), 4)
        print(result.listener_fns[3])
        self.assertTrue(
            'self.device_parameter_action(device, 1, value, "knob_ch2_21_CC__mode_mode_1_p1value")' in result.listener_fns[
                3].strip(),
            f"code was {result.listener_fns[3]}")

        self.assertEqual(len(result.remove_listeners), 4)
        self.assertEqual(len(result.control_defs), 4)
        self.assertEqual(len(result.setup_listeners), 4)
        self.assertEqual(len(result.listener_fns), 20)

    def test_build_live_api_lookup_from_lom(self):
        # expected_output = "self.manager.song().view.tracks[0].view.devices[1]"
        # result = build_live_api_lookup_from_lom("1", "2")
        # self.assertEqual(result, expected_output)

        expected_output = "self.manager.song().view.selected_track.view.selected_device"
        result = build_live_api_lookup_from_lom(TrackInfo.selected(), "selected")
        self.assertEqual(result, expected_output)


if __name__ == '__main__':
    unittest.main()
