import unittest
from difflib import Differ

from autopep8 import fix_code

from ableton_control_surface_as_code.core_model import TrackInfo
# from ableton_control_surface_as_code import gen
from ableton_control_surface_as_code.gen import generate_mode_code_in_template_vars
from ableton_control_surface_as_code.gen_code import generate_lom_listener_action, build_live_api_lookup_from_lom
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi
from builders import build_mixer_with_midi

differ = Differ()


def diff(a, b):
    return ''.join(differ.compare(a.split("\n"), b.split("\n")))


class TestGen(unittest.TestCase):

    def test_generate_code_in_template_vars(self):
        mixer_with_midi = build_mixer_with_midi(api_fn='pan')

        m = ModeGroupWithMidi(mappings={ "mode_1": [mixer_with_midi]})

        res = generate_mode_code_in_template_vars(m)
        self.assertGreater(len(res['code_creation']), 1)

    def test_generate_lister_fn(self):
        n = 1
        parameter = 2

        expected_output = """
def fn(self, value):
    device = lom_value
    self.device_parameter_action(device, 2, value, "fn")
    """

        expected_output = fix_code(expected_output)
        generated = fix_code("\n".join(generate_lom_listener_action(parameter, "lom_value", 'fn', "dbg")))

        print(generated)

        self.assertEqual(generated, expected_output, diff(generated, expected_output))


    # def test_build_live_api_lookup_from_lom(self):
    #     # expected_output = "self.manager.song().view.tracks[0].view.devices[1]"
    #     # result = build_live_api_lookup_from_lom("1", "2")
    #     # self.assertEqual(result, expected_output)
    #
    #     expected_output = "self.manager.song().view.selected_track.view.selected_device"
    #     result = build_live_api_lookup_from_lom(TrackInfo.selected(), "selected")
    #     self.assertEqual(result, expected_output)
    #

if __name__ == '__main__':
    unittest.main()
