# from ableton_control_surface_as_code import gen

import unittest
from difflib import Differ
from unittest.mock import patch

from autopep8 import fix_code

from ableton_control_surface_as_code.gen import generate_code_as_template_vars, create_code_model
from ableton_control_surface_as_code.gen_code import generate_parameter_listener_action
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi, ModeType, ModeButtonWithMidi
from tests.builders import build_mixer_with_midi, build_midi_device_mapping, midi_coords_ch2_cc_50_knob
from tests.custom_assertions import CustomAssertions

differ = Differ()


def diff(a, b):
    return ''.join(differ.compare(a.split("\n"), b.split("\n")))


class TestGen(unittest.TestCase, CustomAssertions):

    def test_generate_code_in_template_vars(self):
        mixer_with_midi = build_mixer_with_midi(api_fn='pan')

        m = ModeGroupWithMidi(mappings=[("mode_1", [mixer_with_midi])],
                              mode_button=ModeButtonWithMidi(on_colors=[], button=midi_coords_ch2_cc_50_knob(), type=ModeType.Switch))

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
            parameter, 22, "lom_value", 'selected', 'fn', False, "dbg")))

        print(generated)

        expected_call = 'self.device_parameter_action(device, 2, 22, value, "fn", toggle=False'
        self.assert_string_in(expected_call, generated)

        expected_device = 'device = self.find_device("lom_value", "selected")'
        self.assert_string_in(expected_device, generated)

    def test_create_code_model(self):
        mode_mappings = [
            ("mode_1", [build_midi_device_mapping(param=1)]),
            ("mode_2", [build_midi_device_mapping(param=1)])
        ]

        modes = ModeGroupWithMidi(mappings=mode_mappings,
                                  mode_button=ModeButtonWithMidi(on_colors=[], button=midi_coords_ch2_cc_50_knob(), type=ModeType.Switch))

        with patch('ableton_control_surface_as_code.gen_code.GeneratedCodes') as MockGeneratedCodes:
            MockGeneratedCodes.common_midi_coords_in_control_defs.return_value = []
        result = create_code_model(modes)

        self.assertIn("mode_1", result)
        self.assertIn("mode_2", result)
        self.assertEqual(len(result["mode_1"]), 2, 'unsure why this is 2')
        self.assertEqual(len(result["mode_2"]), 2, 'unsure why this is 2')
        self.assertEqual(len(result["mode_1"][0].control_defs), 1)
        self.assertEqual(len(result["mode_1"][1].control_defs), 0)
        self.assertEqual(len(result["mode_2"][0].control_defs), 1)
        self.assertEqual(len(result["mode_2"][1].control_defs), 0)


class TestGenerateComposition(unittest.TestCase):
    """End-to-end: generating the lc_parks composition emits TWO surfaces —
    the compositor (combined grid + region listener, talks to the HUD) and the
    forwarder (HudClient retargeted at the shared region port). Writes the
    normal (untracked) build artifacts under live_surfaces/."""

    def test_emits_compositor_and_forwarder(self):
        from pathlib import Path
        from ableton_control_surface_as_code.gen import generate

        repo = Path(__file__).resolve().parent.parent
        generate(repo / "live_surfaces" / "lc_parks" / "lc_parks.nt")

        # Both surfaces are namespaced and emitted INTO the composition folder,
        # so the secondary can never collide with a standalone ck_parkstool_buttons.
        comp = repo / "live_surfaces" / "lc_parks"
        compositor = comp / "ck_lc_parks__launch_control" / "modules" / "main_component.py"
        forwarder = comp / "ck_lc_parks__parks" / "modules" / "main_component.py"
        self.assertTrue(compositor.exists())
        self.assertTrue(forwarder.exists())

        comp_src = compositor.read_text()
        fwd_src = forwarder.read_text()

        # Compositor talks to the real HUD and runs a region listener.
        self.assertIn("self._hud_client = HudClient()", comp_src)
        self.assertIn("RegionState(self._hud_client, dial_offset=16, button_offset=8", comp_src)
        self.assertIn("self._remote.set_region_state(self._region_state)", comp_src)
        # The region re-emit must bypass the primary's show-hud-on gate, so it
        # routes through reemit_combined_burst (not the trigger-gated
        # selected_device_changed). Otherwise the parks region never shows under
        # launch_control's 'controller-nav' trigger.
        self.assertIn("on_commit=self._helpers.reemit_combined_burst", comp_src)
        # The compositor must NOT inherit launch_control's 'controller-nav'
        # trigger: that suppresses + sends HIDE on selection, which races the
        # parks-driven combined COMMIT and makes values flash then vanish.
        self.assertIn("hud_trigger='selection'", comp_src)

        # The two surfaces agree on the region port; the forwarder targets it.
        import re
        port = re.search(r"RegionListener\(.*port=(\d+)", comp_src).group(1)
        self.assertIn(f"self._hud_client = HudClient(host='127.0.0.1', port={port})", fwd_src)

        # Combined grid: parks buttons are offset past launch_control's (button
        # start indices 8-15), and live to the right (grid_col 2).
        self.assertIn("(0, 2, 'button', 2, 8)", comp_src)


if __name__ == '__main__':
    unittest.main()
