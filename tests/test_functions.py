import unittest

from ableton_control_suface_as_code.code import functions_templates
from ableton_control_suface_as_code.model_functions import FunctionsWithMidi
from tests.test_mixer_template import CustomAssertions


class TestFunctionsTemplates(unittest.TestCase, CustomAssertions):
    def test_function_generated(self):
        midi = FunctionsWithMidi(midi_maps=[{
            "midi_coords": [
                {"channel": 1, "type": "note", "number": 51}
            ],
            "function": "toggle"
        }])
        result = functions_templates(functions_with_midi=midi)


        self.assertStringInOne('def button_function_toggle_ch1_51_note_value(self, value)', result.listener_fns)
        self.assertStringInOne("MIDI_NOTE_TYPE", result.creation)
