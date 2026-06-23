"""Multi-button same-mapping: binding one logical action to several physical
buttons via a comma-separated coord list (e.g. `right: row-1:1, row-1:2`).

See ai-coding/plans/multi-button-same-mapping-plan.md.
"""
import unittest
from pathlib import Path

from ableton_control_surface_as_code.core_model import Direction
from ableton_control_surface_as_code.gen_code import track_nav_templates
from ableton_control_surface_as_code.model_track_nav import TrackNav, TrackNavMappings, build_track_nav_model_v2
from ableton_control_surface_as_code.model_device_nav import DeviceNav, DeviceNavMappings, build_device_nav_model_v2, \
    DeviceNavAction
from ableton_control_surface_as_code.model_functions import Functions, build_functions_model_v2
from ableton_control_surface_as_code.model_transport import Transport, TransportMappings, build_transport_model
from ableton_control_surface_as_code.model_mixer import MixerV2, MixerMappingsV2, build_mixer_model_v2
from tests.builders import build_1_group_controller
from tests.custom_assertions import CustomAssertions


class TestMultiButtonTrackNav(unittest.TestCase, CustomAssertions):
    def test_right_bound_to_two_buttons(self):
        mapping = TrackNav(mappings=TrackNavMappings(**{'right': 'row-1:1, row-1:2', 'left': None}))
        result = build_track_nav_model_v2(build_1_group_controller(), mapping)

        inc_maps = [m for m in result.midi_maps if m.direction == Direction.inc]
        self.assertEqual(2, len(inc_maps))
        self.assertEqual([21, 22], sorted(m.only_midi_coord.number for m in inc_maps))

    def test_left_only_binds_to_left_coord(self):
        # Regression: the dec branch used to be guarded by `right_raw`, so a
        # left-only config silently produced no dec mapping.
        mapping = TrackNav(mappings=TrackNavMappings(**{'right': None, 'left': 'row-1:3'}))
        result = build_track_nav_model_v2(build_1_group_controller(), mapping)

        dec_maps = [m for m in result.midi_maps if m.direction == Direction.dec]
        self.assertEqual(1, len(dec_maps))
        self.assertEqual(23, dec_maps[0].only_midi_coord.number)

    def test_two_buttons_generate_two_listeners(self):
        mapping = TrackNav(mappings=TrackNavMappings(**{'right': 'row-1:1, row-1:2', 'left': None}))
        with_midi = build_track_nav_model_v2(build_1_group_controller(), mapping)

        codes = track_nav_templates(with_midi, "mode_1")
        setup_lines = [line for c in codes for line in c.setup_listeners if 'add_value_listener' in line]
        self.assertEqual(2, len(setup_lines))
        self.assertEqual(2, len(set(setup_lines)))


class TestMultiButtonDeviceNav(unittest.TestCase, CustomAssertions):
    def test_right_bound_to_two_buttons(self):
        mapping = DeviceNav(mappings=DeviceNavMappings(**{'right': 'row-1:1, row-1:2'}))
        result = build_device_nav_model_v2(build_1_group_controller(), mapping)

        right_maps = [m for m in result.midi_maps if m.action == DeviceNavAction.right]
        self.assertEqual(2, len(right_maps))
        self.assertEqual([21, 22], sorted(m.only_midi_coord.number for m in right_maps))


class TestMultiButtonFunctions(unittest.TestCase, CustomAssertions):
    def test_builtin_function_bound_to_two_buttons(self):
        # hud_toggle is a reserved builtin, so no functions.py lookup is needed.
        mapping = Functions(mappings={'hud_toggle': 'row-1:1, row-1:2'})
        result = build_functions_model_v2(build_1_group_controller(), mapping, Path('/tmp'))

        self.assertEqual(2, len(result.midi_maps))
        self.assertTrue(all(m.function_name == 'hud_toggle' for m in result.midi_maps))
        self.assertEqual([21, 22], sorted(m.only_midi_coord.number for m in result.midi_maps))


class TestMultiButtonTransport(unittest.TestCase, CustomAssertions):
    def test_play_stop_bound_to_two_buttons(self):
        mapping = Transport(mappings=TransportMappings(**{'play-stop': 'row-1:1, row-1:2'}))
        result = build_transport_model(build_1_group_controller(), mapping)

        self.assertEqual(2, len(result.midi_maps))
        self.assertTrue(all(m.api_call == 'play_stop_raw' for m in result.midi_maps))
        self.assertEqual([21, 22], sorted(m.only_midi_coord.number for m in result.midi_maps))


class TestMultiButtonMixer(unittest.TestCase, CustomAssertions):
    def test_mute_bound_to_two_buttons(self):
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(mute="row-1:1, row-1:2"))
        result = build_mixer_model_v2(build_1_group_controller(), mixer)

        mute_maps = [m for m in result.midi_maps if m.api_function == 'mute']
        self.assertEqual(2, len(mute_maps))
        self.assertEqual([21, 22], sorted(m.only_midi_coord.number for m in mute_maps))

    def test_sends_stays_a_single_array_mapping(self):
        # sends maps knob N -> send index N, so it must NOT be expanded.
        mixer = MixerV2(track='selected', mappings=MixerMappingsV2(sends="row-1:5-8"))
        result = build_mixer_model_v2(build_1_group_controller(midi_range='21-28'), mixer)

        sends_maps = [m for m in result.midi_maps if m.api_function == 'sends']
        self.assertEqual(1, len(sends_maps))
        self.assertEqual(4, len(sends_maps[0].midi_coords))


if __name__ == '__main__':
    unittest.main()
