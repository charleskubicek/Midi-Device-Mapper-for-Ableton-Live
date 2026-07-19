import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ableton_control_surface_as_code.gen_code import functions_templates
from ableton_control_surface_as_code.model_functions import FunctionLookup
from tests.builders import build_functions_with_midi
from tests.custom_assertions import CustomAssertions


class TestFunctionsTemplates(unittest.TestCase, CustomAssertions):
    def test_function_generated(self):
        midi = build_functions_with_midi(channel=1, number=51, type="CC", function="toggle")

        result = functions_templates(midi, "mode_1")[0]

        self.assert_string_in_one('def button_ch1_51_CC__mode_mode_1_fn_toggle_listener(self, value):', result.listener_fns)


class TestHudNameDecorator(unittest.TestCase):
    """The generator reads an `@hud_name("...")` decorator on a Functions method
    statically and uses the string as that button's HUD label."""

    def _inspect(self, source, fn_name):
        with TemporaryDirectory() as d:
            path = Path(d) / "functions.py"
            path.write_text(textwrap.dedent(source))
            return FunctionLookup.inspect_python_file(path, fn_name)

    def test_no_decorator_yields_none_hud_name(self):
        parameter_len, hud_name = self._inspect(
            """
            class Functions:
                def back8(self):
                    pass
            """, "back8")
        self.assertEqual(parameter_len, 0)
        self.assertIsNone(hud_name)

    def test_decorator_label_is_extracted(self):
        parameter_len, hud_name = self._inspect(
            """
            class Functions:
                @hud_name("Back 8")
                def back8(self):
                    pass
            """, "back8")
        self.assertEqual(parameter_len, 0)
        self.assertEqual(hud_name, "Back 8")

    def test_decorator_coexists_with_a_value_parameter(self):
        parameter_len, hud_name = self._inspect(
            """
            class Functions:
                @hud_name("Set X")
                def set_x(self, value):
                    pass
            """, "set_x")
        self.assertEqual(parameter_len, 1)
        self.assertEqual(hud_name, "Set X")

