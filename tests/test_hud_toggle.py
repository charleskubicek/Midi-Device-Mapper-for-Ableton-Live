import unittest
from pathlib import Path
from unittest.mock import Mock

from source_modules.helpers import Helpers, SurfaceConfig
from ableton_control_surface_as_code.core_model import MidiCoords, EncoderType, EncoderMode
from ableton_control_surface_as_code.gen_code import functions_templates
from ableton_control_surface_as_code.model_functions import (
    Functions,
    FunctionsMidiMapping,
    build_functions_model_v2,
    RESERVED_BUILTIN_FUNCTIONS,
)
from tests.builders import build_1_group_controller
from tests.custom_assertions import CustomAssertions


def _builtin_mapping(number=21):
    return FunctionsMidiMapping(
        midi_coords=[MidiCoords(channel=2, type="CC", number=number,
                                encoder_type=EncoderType.button,
                                encoder_mode=EncoderMode.Absolute,
                                source_info="tests", encoder_refs=[])],
        function_name="hud_toggle",
        parameter_len=0,
        builtin=True,
    )


class TestHudToggleReserved(unittest.TestCase):
    def test_hud_toggle_is_reserved(self):
        self.assertIn("hud_toggle", RESERVED_BUILTIN_FUNCTIONS)

    def test_build_skips_user_file_lookup_for_builtin(self):
        # hud_toggle is NOT in functions.py — the user-file lookup would raise.
        # The builtin path must skip it and still resolve.
        controller = build_1_group_controller()
        functions = Functions(mappings={"hud_toggle": "row-1:1"})

        model = build_functions_model_v2(controller, functions, root_dir=Path("/nonexistent"))

        self.assertEqual(len(model.midi_maps), 1)
        m = model.midi_maps[0]
        self.assertTrue(m.builtin)
        self.assertEqual(m.parameter_len, 0)
        self.assertEqual(m.function_name, "hud_toggle")


class TestHudToggleCodegen(unittest.TestCase, CustomAssertions):
    def test_template_function_call_routes_to_helpers(self):
        m = _builtin_mapping()
        self.assertEqual(m.template_function_call(), "self._helpers.toggle_hud()")

    def test_user_function_call_unchanged(self):
        m = FunctionsMidiMapping(
            midi_coords=[MidiCoords(channel=2, type="CC", number=21,
                                    encoder_type=EncoderType.button,
                                    encoder_mode=EncoderMode.Absolute,
                                    source_info="tests", encoder_refs=[])],
            function_name="my_fn",
            parameter_len=0,
        )
        self.assertEqual(m.template_function_call(), "self.functions.my_fn()")

    def test_generated_listener_calls_helpers_toggle_and_not_user_functions(self):
        from ableton_control_surface_as_code.model_functions import FunctionsWithMidi
        midi = FunctionsWithMidi(midi_maps=[_builtin_mapping()])

        result = functions_templates(midi, "mode_1")[0]
        body = "\n".join(result.listener_fns)

        self.assertIn("self._helpers.toggle_hud()", body)
        self.assertNotIn("self.functions.hud_toggle", body)

    def test_builtin_fires_press_only(self):
        # Without a press-once guard the callee fires on press AND release,
        # flipping the toggle twice per press. The builtin must route through the
        # hardware-aware edge guard (press-only on momentary, one-per-press on toggle).
        from ableton_control_surface_as_code.model_functions import FunctionsWithMidi
        midi = FunctionsWithMidi(midi_maps=[_builtin_mapping()])

        result = functions_templates(midi, "mode_1")[0]
        body = "\n".join(result.listener_fns)

        self.assertIn("self._helpers.should_act_on_edge(value)", body)
        self.assertNotIn("if True:", body)


class TestToggleHudRuntime(unittest.TestCase):
    def _helpers(self):
        # no slot/switch assignments and no focused device → toggle_hud's show
        # path emits the label-only burst directly on the (mock) remote.
        return Helpers(
                   Mock(),
                   Mock(),
                   SurfaceConfig(
                       slot_assignments=[],
                       switch_slot_assignments=[],
                       parameter_mappings_raw={"devices": []},
                   ),
               )

    def test_first_press_hides(self):
        h = self._helpers()
        h._remote.reset_mock()

        h.toggle_hud()

        self.assertTrue(h._presenter.hud_dismissed)
        h._remote.hide.assert_called_once()
        h._remote.device_update.assert_not_called()

    def test_second_press_reshows_and_clears_intent(self):
        h = self._helpers()
        h.toggle_hud()            # hide
        h._remote.reset_mock()

        h.toggle_hud()            # show

        self.assertFalse(h._presenter.hud_dismissed)
        h._remote.hide.assert_not_called()
        h._remote.device_update.assert_called_once()

    def test_label_only_burst_resets_intent(self):
        # A mode burst with no focused device clears the Swift sticky flag;
        # intent must re-sync so the toggle direction doesn't invert.
        h = self._helpers()
        h.toggle_hud()            # dismissed = True
        self.assertTrue(h._presenter.hud_dismissed)

        h.refresh_hud_for_mode("mode_1", None)

        self.assertFalse(h._presenter.hud_dismissed)

    def test_device_focus_burst_resets_intent(self):
        # The inversion-fix path: HUD dismissed, then a *device* burst (the
        # common "select another device while hidden" case) must reset intent.
        # This exercises the reset at the tail of update_remote_parameters.
        from dataclasses import dataclass, field

        @dataclass
        class _Dev:
            parameters: list = field(default_factory=lambda: [
                type("P", (), {"name": "On/Off", "min": 0, "max": 1, "value": 1,
                               "original_name": "On/Off", "is_quantized": True})()
            ])
            name: str = "EQ Eight"
            class_name: str = "Eq8"

        h = self._helpers()
        h._last_selected_device = _Dev()
        h.toggle_hud()            # dismissed = True
        self.assertTrue(h._presenter.hud_dismissed)

        h.update_remote_parameters()   # device-focus burst

        self.assertFalse(h._presenter.hud_dismissed)


if __name__ == "__main__":
    unittest.main()
