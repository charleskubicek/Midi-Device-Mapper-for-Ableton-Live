import unittest

from ableton_control_surface_as_code.gen_code import functions_templates
from tests.builders import build_functions_with_midi
from tests.custom_assertions import CustomAssertions


class TestFunctionsTemplates(unittest.TestCase, CustomAssertions):
    def test_function_generated(self):
        midi = build_functions_with_midi(channel=1, number=51, type="CC", function="toggle")

        result = functions_templates(midi, "mode_1")

        self.assert_string_in_one('def button_ch1_51_CC__mode_mode_1_fn_toggle_listener(self, value):', result.listener_fns)

