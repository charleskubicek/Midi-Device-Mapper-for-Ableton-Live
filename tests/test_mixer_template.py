import unittest

from ableton_control_suface_as_code.code import mixer_templates
from ableton_control_suface_as_code.model import MixerV1, MixerMappingsV1
from ableton_control_suface_as_code.mappings_model import MixerWithMidi
from tests.builders import MixerMidiMappingBuilder

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
    def test_mixer_with_midi_has_midi_maps(self):
        mixer_with_midi = self.builder(2, 50, 'CC', 'selected', MixerMappingsV1(pan="r1-2"))

        result = mixer_templates(mixer_with_midi)

        self.assertStringInOne('ButtonElement(True, MIDI_CC_TYPE, 1, 50)', result.creation)
        self.assertStringInOne('set_on_off_values(self.led_on, self.led_off)', result.creation)

        self.assertStringIn('self.led_off = 0', result.setup)
        self.assertStringInOne('self.mixer.selected_strip().set_volume_button(self.button', result.setup_listeners)
        self.assertStringInOne('self.mixer.selected_strip().set_volume_button(None)', result.remove_listeners)
        self.assertEqual(result.listener_fns , [])

    def builder(self, chan=2, no=50, type="CC", track='selected', mappings=MixerMappingsV1(pan="r1-2")):
        midi_mapping = MixerMidiMappingBuilder().midi_info(chan, no, type).build()
        mixer = MixerV1(track=track, mappings=mappings)
        mixer_with_midi = MixerWithMidi(mixer=mixer, midi_maps=[midi_mapping])
        return mixer_with_midi


if __name__ == '__main__':
    unittest.main()