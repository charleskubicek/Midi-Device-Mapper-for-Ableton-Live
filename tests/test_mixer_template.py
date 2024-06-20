import unittest

from ableton_control_suface_as_code.code import mixer_templates
from ableton_control_suface_as_code.core_model import MixerWithMidi, MixerMidiMapping, MidiCoords, EncoderType, \
    EncoderCoords


class CustomAssertions:
    def assertStringIn(self, sub, st):
        if sub not in st:
            raise self.failureException(f"{sub} not in {st}")


    def assertStringInOne(self, sub, sts:[str]):
        found = False
        for st in sts:
            if sub in st:
                return

        if not found:
            raise self.failureException(f"{sub} not in {sts}")


class TestMixerTemplates(unittest.TestCase, CustomAssertions):
    def test_mixer_with_buttons(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='solo', enocder_type=EncoderType.button)

        result = mixer_templates(mixer_with_midi)

        self.assertStringInOne('ConfigurableButtonElement(True, MIDI_CC_TYPE, 1, 50)', result.creation)
        self.assertStringInOne('set_on_off_values(self.led_on, self.led_off)', result.creation)

        self.assertStringIn('self.led_off = 0', result.setup)
        self.assertStringInOne('self.mixer.selected_strip().set_solo_button(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_solo_button(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def test_mixer_with_knob(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='volume', enocder_type=EncoderType.slider)

        result = mixer_templates(mixer_with_midi)

        self.assertEqual("self.encodr_ch1_50_CC__cds_r1c2__api_volume = EncoderElement(MIDI_CC_TYPE, 1, 50, Live.MidiMap.MapMode.relative_binary_offset)", result.creation[0])
        self.assertStringInOne('self.mixer.selected_strip().set_volume_control(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_volume_control(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def test_mixer_sends(self):
        mixer_with_midi = self.build_mixer_with_multiple_mappings(2, [50, 51, 52], 'CC', api_fn='sends', enocder_type=EncoderType.knob)

        result = mixer_templates(mixer_with_midi)

        self.assertStringInOne("sends[0] = EncoderElement(MIDI_CC_TYPE, 1, 50", result.creation)
        self.assertStringInOne("sends[1] = EncoderElement(MIDI_CC_TYPE, 1, 51", result.creation)
        self.assertStringInOne("sends[2] = EncoderElement(MIDI_CC_TYPE, 1, 52", result.creation)

        self.assertStringInOne('self.mixer.selected_strip().set_send_controls(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_send_controls(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def build_mixer_with_one_mapping(self, chan=2, no=50, type="CC", api_fn="pan", enocder_type=EncoderType.knob):
        return self.build_mixer_with_multiple_mappings(chan, [no], type, api_fn, enocder_type)

    def build_mixer_with_multiple_mappings(self, chan=2, nos=[], type="CC", api_fn="pan", enocder_type=EncoderType.knob):
        return MixerWithMidi.model_construct(
            midi_maps=[MixerMidiMapping.with_multiple_args(
                [MidiCoords(chan, no, type) for no in nos],
                enocder_type,
                api_fn,
                encoder_coords=EncoderCoords(1, 2, 1+ len(nos) - 1),
                selected_track=True
            )])

if __name__ == '__main__':
    unittest.main()