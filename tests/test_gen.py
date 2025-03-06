import unittest
from difflib import Differ

from autopep8 import fix_code

# from ableton_control_surface_as_code import gen
from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from ableton_control_surface_as_code.gen_code import generate_parameter_listener_action
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi
from tests.builders import build_mixer_with_midi
from tests.custom_assertions import CustomAssertions

differ = Differ()


def diff(a, b):
    return ''.join(differ.compare(a.split("\n"), b.split("\n")))


class TestGen(unittest.TestCase, CustomAssertions):

    def test_generate_code_in_template_vars(self):
        mixer_with_midi = build_mixer_with_midi(api_fn='pan')

        m = ModeGroupWithMidi(mappings={ "mode_1": [mixer_with_midi]})

        res = generate_code_as_template_vars(m)
        self.assertGreater(len(res['code_creation']), 1)

    def test_generate_lister_fn(self):
        n = 1
        parameter = 2

        expected_output = """
def fn(self, value):
    device = lom_value
    self.device_parameter_action(device, 2, 22, value, "fn")
    """

        expected_output = fix_code(expected_output)
        generated = fix_code("\n".join(generate_parameter_listener_action(
            parameter, 22, "lom_value", 'selected',  'fn',False, "dbg")))

        print(generated)

        expected_call = 'self.device_parameter_action(device, 2, 22, value, "fn", toggle=False'
        self.assert_string_in(expected_call, generated)

        expected_device = 'device = self.find_device("lom_value", "selected")'
        self.assert_string_in(expected_device, generated)

if __name__ == '__main__':
    unittest.main()
