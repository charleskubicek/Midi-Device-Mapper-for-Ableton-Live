import unittest

from ableton_control_suface_as_code.gen_code import mixer_mode_templates, track_nav_mode_templates
from ableton_control_suface_as_code.core_model import EncoderType, \
    TrackInfo
from tests.builders import build_mixer_with_multiple_mappings, build_track_nav_with_midi_button


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

class TestTrackNavTemplates(unittest.TestCase, CustomAssertions):
    def test_track_nav(self):
        track_nav = build_track_nav_with_midi_button()

        result = track_nav_mode_templates(track_nav, "1")

        print(result.listener_fns[2])

        self.assertEqual(result.setup_listeners[0], "self.button_ch2_50_CC.add_value_listener(self.button_ch2_50_CC__mode_1_incvalue)")
        self.assertTrue("def button_ch2_50_CC__mode_1_incvalue(self, value)" in result.listener_fns[2], f"code was {result.listener_fns[2]}")


class TestMixerTemplates(unittest.TestCase, CustomAssertions):
    def test_mixer_with_buttons(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='solo', enocder_type=EncoderType.button)

        result = mixer_mode_templates(mixer_with_midi, "1")

        self.assertEqual(result.control_defs[0].channel, 2)

        self.assertStringInOne('self.mixer.selected_strip().set_solo_button(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_solo_button(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def test_mixer_with_knob(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='volume', enocder_type=EncoderType.slider)

        result = mixer_mode_templates(mixer_with_midi, "1")

        self.assertEqual(result.control_defs[0].number, 50)
        self.assertStringInOne('self.mixer.selected_strip().set_volume_control(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_volume_control(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])


    def test_master_volume(self):
        mixer_with_midi = self.build_mixer_with_one_mapping(2, 50, 'CC', api_fn='volume',
                                                            enocder_type=EncoderType.slider, track_info=TrackInfo.master())

        result = mixer_mode_templates(mixer_with_midi, "1")

        self.assertEqual(result.control_defs[0].number, 50)
        self.assertStringInOne('self.mixer.master_strip().set_volume_control(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.master_strip().set_volume_control(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def test_mixer_sends(self):
        mixer_with_midi = build_mixer_with_multiple_mappings(2, [50, 51, 52], 'CC', api_fn='sends', enocder_type=EncoderType.knob)

        result = mixer_mode_templates(mixer_with_midi, "1")

        self.assertEqual(len(result.array_defs), 1)
        self.assertEqual(len(result.array_defs[0][1]), 3)
        self.assertEqual(result.array_defs[0][1][0].number, 50)

        self.assertStringInOne('self.mixer.selected_strip().set_send_controls(self.', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_send_controls(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def build_mixer_with_one_mapping(self, chan=2, no=50, type="CC", api_fn="pan",
                                     enocder_type=EncoderType.knob, track_info=TrackInfo.selected()):
        return build_mixer_with_multiple_mappings(chan, [no], type, api_fn, enocder_type, track_info)

if __name__ == '__main__':
    unittest.main()