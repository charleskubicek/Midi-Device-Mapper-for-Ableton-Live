# from ableton_control_surface_as_code import gen

import unittest
from difflib import Differ
from unittest.mock import patch

from autopep8 import fix_code

from ableton_control_surface_as_code.gen import generate_code_as_template_vars, create_code_model
from ableton_control_surface_as_code.gen_code import generate_parameter_listener_action
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi, ModeType, ModeButtonWithMidi
from tests.builders import build_mixer_with_midi, build_midi_device_mapping, midi_coords_ch2_cc_50_knob, build_functions_with_midi
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

    def test_per_mode_assignment_vars_emitted(self):
        m = ModeGroupWithMidi(
            mappings=[("mode_1", [build_mixer_with_midi(api_fn='pan')]),
                      ("mode_2", [build_mixer_with_midi(api_fn='volume')])],
            mode_button=ModeButtonWithMidi(on_colors=[], button=midi_coords_ch2_cc_50_knob(), type=ModeType.Switch))

        res = generate_code_as_template_vars(m)

        for key in ('code_slot_assignments_by_mode', 'code_switch_slot_assignments_by_mode'):
            d = eval(res[key])  # rendered as a Python dict literal
            self.assertEqual(set(d.keys()), {'mode_1', 'mode_2'})

    def test_deprecated_toggle_emits_stderr_warning(self):
        import io
        from contextlib import redirect_stderr
        from ableton_control_surface_as_code.gen import warn_deprecated_toggle
        from ableton_control_surface_as_code.encoder_coords import Toggle

        toggle_coord = midi_coords_ch2_cc_50_knob().with_encoder_refs([Toggle.instance()])
        fn = build_functions_with_midi()
        fn.midi_maps[0].midi_coords = [toggle_coord]
        m = ModeGroupWithMidi(mappings=[("mode_1", [fn])], mode_button=None)

        buf = io.StringIO()
        with redirect_stderr(buf):
            warn_deprecated_toggle(m, "some_file.nt")
        out = buf.getvalue()
        self.assertIn("toggle", out)
        self.assertIn("can be removed", out)
        self.assertIn("some_file.nt", out)

    def test_no_toggle_emits_no_warning(self):
        import io
        from contextlib import redirect_stderr
        from ableton_control_surface_as_code.gen import warn_deprecated_toggle

        m = ModeGroupWithMidi(mappings=[("mode_1", [build_functions_with_midi()])], mode_button=None)
        buf = io.StringIO()
        with redirect_stderr(buf):
            warn_deprecated_toggle(m, "some_file.nt")
        self.assertEqual(buf.getvalue(), "")

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

        # R8: behaviour is injected as DATA constants the template consumes, not
        # as Python source built in gen.py. The compositor's region listener is
        # configured by REGION_CONFIG; standalone surfaces get REGION_CONFIG=None
        # and the wiring (always present + syntax-checked in the template) is gated off.
        self.assertIn("REGION_CONFIG = {'dial_offset': 16, 'button_offset': 8,", comp_src)
        self.assertIn("RegionState(self._hud_client,", comp_src)
        self.assertIn("dial_offset=REGION_CONFIG['dial_offset']", comp_src)
        self.assertIn("self._remote.set_region_state(self._region_state)", comp_src)
        # The region re-emit must bypass the primary's show-hud-on gate, so it
        # routes through reemit_combined_burst (not the trigger-gated
        # selected_device_changed). Otherwise the parks region never shows under
        # launch_control's 'controller-nav' trigger.
        self.assertIn("on_commit=self._helpers.reemit_combined_burst", comp_src)
        # The compositor talks to the real HUD (no retarget): HUD_TARGET=None.
        self.assertIn("HUD_TARGET = None", comp_src)
        # App-view dismissals forward a ViewLeft event through Helpers (the
        # HudVisibility table) — never a raw send_hide() that would leave the
        # Python-side dismiss mirror stale.
        self.assertIn("self._helpers.hud_view_left()", comp_src)
        self.assertNotIn("self._hud_client.send_hide()", comp_src)
        # The compositor must NOT inherit launch_control's 'controller-nav'
        # trigger: that suppresses + sends HIDE on selection, which races the
        # parks-driven combined COMMIT and makes values flash then vanish.
        self.assertIn("hud_trigger='selection'", comp_src)

        # The two surfaces agree on the region port; the forwarder retargets its
        # HUD client at it via the HUD_TARGET data constant, and runs no region.
        import re
        port = re.search(r"REGION_CONFIG = \{'dial_offset': 16, 'button_offset': 8, 'port': (\d+)\}", comp_src).group(1)
        self.assertIn(f"HUD_TARGET = ('127.0.0.1', {port})", fwd_src)
        self.assertIn("REGION_CONFIG = None", fwd_src)

        # Combined cells: parks buttons are offset past launch_control's (button
        # start indices 8-15) and tagged section 1, but keep their OWN grid
        # (grid_col 0) — the HUD renders section 1 as an independent block to the
        # right of section 0.
        self.assertIn("(0, 0, 'button', 2, 8, 1)", comp_src)


if __name__ == '__main__':
    unittest.main()
