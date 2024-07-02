import unittest

from ableton_control_suface_as_code.code import functions_mode_templates
from ableton_control_suface_as_code.core_model import MidiCoords, EncoderType
from ableton_control_suface_as_code.model_functions import FunctionsWithMidi, FunctionsMidiMapping
from tests.builders import build_functions_with_midi
from tests.test_code_mixer_template import CustomAssertions


class TestFunctionsTemplates(unittest.TestCase, CustomAssertions):
    def test_function_generated(self):
        midi = build_functions_with_midi(channel=1, number=51, type="CC", function="toggle")

        result = functions_mode_templates(midi, "mode_1")

        self.assertStringInOne('def button_ch1_51_CC__mode_mode_1_fn_togglevalue(self, value):', result.listener_fns)

