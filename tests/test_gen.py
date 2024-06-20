import unittest
from difflib import Differ

from autopep8 import fix_code

from ableton_control_suface_as_code.code import generate_listener_action, build_live_api_lookup_from_lom
from ableton_control_suface_as_code.core_model import DeviceWithMidi, DeviceMidiMapping, MidiType, MixerWithMidi, \
    MidiCoords, MixerMidiMapping, EncoderType, EncoderCoords
# from ableton_control_suface_as_code import gen
from ableton_control_suface_as_code.gen import device_templates, generate_code_in_template_vars
from ableton_control_suface_as_code.model_v1 import ControllerV1, DeviceV1, build_mode_model_v1

differ = Differ()

def diff(a, b):
    return ''.join(differ.compare(a.split("\n"), b.split("\n")))

class TestGen(unittest.TestCase):

    def test_generate_code_in_template_vars(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(api_fn='pan')

        res = generate_code_in_template_vars([mixer_with_midi])
        self.assertGreater(len(res['code_creation']), 1)

    def build_mixer_with_one_mapping(self, api_fn="pan"):
        return MixerWithMidi.model_construct(
            midi_maps=[MixerMidiMapping(
                midi_coords=MidiCoords(2, 50, 'CC'),
                encoder_type=EncoderType.knob,
                api_function=api_fn,
                encoder_coords=EncoderCoords(1, 2, 2),
                selected_track=True
            )])

    def test_generate_lister_fn(self):
        n = 1
        parameter = 2

        expected_output = """
# dbg
def fn(self, value):
    selected_device = lom_value
    if selected_device is None:
        return

    if self.manager.debug:
        self.log_message(f"fn (dbg) selected_device = {selected_device.name}, value is {value}")

    selected_device = self.manager.song().view.selected_track.view.selected_device

    if len(selected_device.parameters) < 2:
        self.log_message(f"2 too large, max is {len(selected_device.parameters)}")
        return

    selected_device.parameters[2].value = value
    """

        expected_output = fix_code(expected_output)
        generated = fix_code("\n".join(generate_listener_action(parameter, "lom_value",'fn', "dbg")))

        print(generated)

        self.assertEqual(generated, expected_output, diff(generated, expected_output))


    def test_encoder_template(self):
        device_mapping = {
            'type': 'device',
            'lom': 'tracks.selected.device.selected',
            'range_maps': [
                {
                    "row": 1,
                    "range": {'from': 1, 'to': 2},
                    "parameters": {'from': 1, 'to': 2},
                },
                {
                    "row": 2,
                    "range": {'from': 1, 'to': 2},
                    "parameters": {'from': 3, 'to': 5},
                }
            ]
        }

        mixer = {
            'type': 'mixer',
            'track': 'selected',
            'mappings': [
                "pan: row_1:2",
            ]
        }

        controller = {
            'on_led_midi': '77',
            'off_led_midi': '78',
            'control_groups': [
                {'layout': 'row',
                 'number': 1,
                 'type': 'knob',
                 'midi_channel': 2,
                 'midi_type': "CC",
                 'midi_range': {'from': 21, 'to': 28}
                 },
                {'layout': 'col',
                 'number': 2,
                 'type': 'button',
                 'midi_channel': 2,
                 'midi_type': "CC",
                 'midi_range': {'from': 29, 'to': 37}
                 },
            ],
            'toggles':[
                'r2-4'
            ]
        }
        # device_with_midi = build_mode_model_v1([DeviceV1.model_validate(device_mapping)], ControllerV1.model_validate(controller))
        device_with_midi = DeviceWithMidi.model_construct(track="selected", device="selected", midi_range_maps=[
            DeviceMidiMapping.model_construct(midi_channel=2, midi_number=21, midi_type=MidiType.CC, parameter=1, control_type='knob'),
            DeviceMidiMapping.model_construct(midi_channel=2, midi_number=22, midi_type=MidiType.CC, parameter=2, control_type='knob'),
            DeviceMidiMapping.model_construct(midi_channel=2, midi_number=23, midi_type=MidiType.CC, parameter=3, control_type='knob'),
            DeviceMidiMapping.model_construct(midi_channel=2, midi_number=24, midi_type=MidiType.CC, parameter=4, control_type='knob')
        ])
        result = device_templates(device_with_midi)

        self.assertEqual(result.remove_listeners[0], "self.encoder_ch2_no21_CC__p1.remove_value_listener(self.encoder_ch2_no21_CC__p1_value)")
        self.assertEqual(result.creation[0], "self.encoder_ch2_no21_CC__p1 = EncoderElement(MIDI_CC_TYPE, 1, 21, Live.MidiMap.MapMode.absolute)")
        self.assertEqual(result.creation[1], "self.encoder_ch2_no22_CC__p2 = EncoderElement(MIDI_CC_TYPE, 1, 22, Live.MidiMap.MapMode.absolute)")
        self.assertEqual(result.setup_listeners[0], "self.encoder_ch2_no21_CC__p1.add_value_listener(self.encoder_ch2_no21_CC__p1_value)")
        self.assertTrue("def encoder_ch2_no21_CC__p1_value(self, value)" in result.listener_fns[2], f"code was {result.listener_fns[2]}")

        self.assertEqual(len(result.remove_listeners), 4)
        self.assertEqual(len(result.creation), 4)
        self.assertEqual(len(result.setup_listeners), 4)
        self.assertGreater(len(result.listener_fns), 40)


    def test_build_live_api_lookup_from_lom(self):
        expected_output = "self.manager.song().view.tracks[0].view.devices[1]"
        result = build_live_api_lookup_from_lom("1", "2")
        self.assertEqual(result, expected_output)

        expected_output = "self.manager.song().view.selected_track.view.selected_device"
        result = build_live_api_lookup_from_lom("selected", "selected")
        self.assertEqual(result, expected_output)


if __name__ == '__main__':
    unittest.main()