import unittest

from ableton_control_surface_as_code.gen_code import mixer_templates, track_nav_templates, GeneratedCodes
from ableton_control_surface_as_code.core_model import EncoderType, \
    TrackInfo
from tests.builders import build_mixer_with_multiple_mappings, build_track_nav_with_midi_button
from tests.custom_assertions import CustomAssertions


class TestTrackNavTemplates(unittest.TestCase, CustomAssertions):
    def test_track_nav(self):
        track_nav = build_track_nav_with_midi_button()

        result = GeneratedCodes.merge_all(track_nav_templates(track_nav, "1"))

        print(result.listener_fns[2])

        self.assertEqual(result.setup_listeners[0], "self.button_ch2_50_CC.add_value_listener(self.button_ch2_50_CC__mode_1_inc_listener)")
        self.assertTrue("def button_ch2_50_CC__mode_1_inc_listener(self, value)" in result.listener_fns[2], f"code was {result.listener_fns[2]}")


class TestMixerTemplates(unittest.TestCase, CustomAssertions):
    def test_mixer_with_buttons(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='solo', enocder_type=EncoderType.button)

        result = GeneratedCodes.merge_all(mixer_templates(mixer_with_midi, "1"))

        self.assertEqual(result.control_defs[0].channel, 2)

        self.assert_string_in_one('self.mixer.selected_strip().set_solo_button(self.', result.setup_listeners)
        self.assert_string_in_one('self.mixer.selected_strip().set_solo_button(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def test_mixer_with_knob(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='volume', enocder_type=EncoderType.slider)

        result = GeneratedCodes.merge_all(mixer_templates(mixer_with_midi, "1"))

        self.assertEqual(result.control_defs[0].number, 50)
        self.assert_string_in_one('self.mixer.selected_strip().set_volume_control(self.', result.setup_listeners)
        self.assert_string_in_one('self.mixer.selected_strip().set_volume_control(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])


    def test_master_volume(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='volume',
                                                            enocder_type=EncoderType.slider, track_info=TrackInfo.master())

        result = GeneratedCodes.merge_all(mixer_templates(mixer_with_midi, "1"))

        self.assertEqual(result.control_defs[0].number, 50)
        self.assert_string_in_one('self.mixer.master_strip().set_volume_control(self.', result.setup_listeners)
        self.assert_string_in_one('self.mixer.master_strip().set_volume_control(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def test_mixer_sends(self):
        mixer_with_midi = build_mixer_with_multiple_mappings(2, [50, 51, 52], 'CC', api_fn='sends', enocder_type=EncoderType.knob)

        result = result = GeneratedCodes.merge_all(mixer_templates(mixer_with_midi, "1"))

        self.assertEqual(len(result.array_defs), 1)
        self.assertEqual(len(result.array_defs[0][1]), 3)
        self.assertEqual(result.array_defs[0][1][0].number, 50)

        self.assert_string_in_one('self.mixer.selected_strip().set_send_controls(self.', result.setup_listeners)
        self.assert_string_in_one('self.mixer.selected_strip().set_send_controls(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def build_mixer_with_one_mapping(self, chan=2, no=50, type="CC", api_fn="pan",
                                     enocder_type=EncoderType.knob, track_info=TrackInfo.selected()):
        return build_mixer_with_multiple_mappings(chan, [no], type, api_fn, enocder_type, track_info)

if __name__ == '__main__':
    unittest.main()