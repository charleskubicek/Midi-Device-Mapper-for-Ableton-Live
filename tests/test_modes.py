import unittest
from pathlib import Path

from ableton_control_surface_as_code.core_model import MidiCoords, EncoderType, MidiType
from ableton_control_surface_as_code.model_v2 import ModeGroupWithMidi, ModeType, ModeButtonWithMidi
from tests.builders import midi_coords_ch2_cc_50_knob, build_midi_device_mapping

_TEMPLATE = (Path(__file__).resolve().parent.parent
             / 'templates' / 'surface_name' / 'modules' / 'main_component.py')


def _mode_button_listener_src():
    """The mode_button_listener method text sliced from the surface template.

    The raw template holds `$variable` substitutions (not valid Python), so we
    slice by text rather than parsing: from `def mode_button_listener` to the
    next method at the same indent. This method itself carries no substitutions."""
    src = _TEMPLATE.read_text()
    start = src.index("    def mode_button_listener(self, value):")
    rest = src[start:]
    nxt = rest.index("\n    def ", 1)
    return rest[:nxt]


class TestShiftSelfHealing(unittest.TestCase):
    """Guards the fix for the dropped-note-off shift inversion: the shift path
    must be LEVEL-driven (press => be in shift, release => be in base), which is
    idempotent per level and re-syncs after a lost/duplicated MIDI edge. The old
    'advance to next mode on every edge' logic inverted permanently on one missed
    release, so it must not come back."""

    def test_shift_branch_is_level_driven_and_idempotent(self):
        body = _mode_button_listener_src()
        self.assertIn("self.current_mode['is_shift']", body)
        # Idempotent guards: only act when the level disagrees with the state.
        self.assertIn("in_base", body)
        self.assertIn("if in_base:", body)
        self.assertIn("if not in_base:", body)
        # Release returns to the base mode directly (not "next"), so it's correct
        # regardless of how the FSM arrived.
        self.assertIn("self.goto_mode(self._first_mode)", body)

    def test_release_no_longer_unconditionally_advances(self):
        # The fragile pattern was `elif value == 0 and self.current_mode['is_shift']:`
        # followed by goto_mode(next). Ensure that exact shape is gone.
        body = _mode_button_listener_src()
        self.assertNotIn("elif value == 0 and self.current_mode['is_shift']:", body)


class TestModes(unittest.TestCase):

    def test_fsm_function(self):

        mode_mappings = [
            ("mode_1", [build_midi_device_mapping(param=1)]),
            ("mode_2", [build_midi_device_mapping(param=1)])
        ]
        on_colours = [
            ("mode_1", 0),
            ("mode_2", 1)
        ]

        mode_group = ModeGroupWithMidi(
            mappings=mode_mappings,
            mode_button=ModeButtonWithMidi(button=midi_coords_ch2_cc_50_knob(), on_colors=on_colours, type=ModeType.Switch))

        expected_output = mode_group.fsm()

        self.assertEqual(expected_output[0].next, 'mode_2')
        self.assertEqual(expected_output[1].next, 'mode_1')
        self.assertEqual(expected_output[0].is_shift, False)
        self.assertEqual(expected_output[1].is_shift, False)
        self.assertEqual(expected_output[0].color, "0")
        self.assertEqual(expected_output[1].color, "1")

    def test_headless_fsm_without_mode_button(self):
        # A composition secondary declares modes but no physical mode-button; its
        # FSM is driven remotely. fsm() must still yield wired mode data (derived
        # from the mappings), with no colour and no local shift gesture.
        mode_mappings = [
            ("main_mode", [build_midi_device_mapping(param=1)]),
            ("shift_mode", [build_midi_device_mapping(param=1)]),
        ]
        mode_group = ModeGroupWithMidi(mappings=mode_mappings, mode_button=None)

        fsm = mode_group.fsm()
        self.assertEqual([m.name for m in fsm], ["main_mode", "shift_mode"])
        self.assertEqual(fsm[0].next, "shift_mode")
        self.assertEqual(fsm[1].next, "main_mode")
        self.assertEqual(fsm[0].color, "None")
        self.assertFalse(fsm[0].is_shift)

    def test_single_mode_without_button_has_empty_fsm(self):
        mode_group = ModeGroupWithMidi(
            mappings=[("only", [build_midi_device_mapping(param=1)])], mode_button=None)
        self.assertEqual(mode_group.fsm(), [])
