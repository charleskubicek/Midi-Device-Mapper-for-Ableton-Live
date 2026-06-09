import ast
import unittest

from ableton_control_surface_as_code.core_model import EncoderType, MidiType
from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from ableton_control_surface_as_code.gen_code import clip_templates
from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_clip import Clip, ClipWithMidi, build_clip_model_v2
from ableton_control_surface_as_code.model_controller import (
    ControllerV2, ControllerRawV2, ControlGroupPartV2,
)
from ableton_control_surface_as_code.model_transport import build_transport_model, Transport, TransportMappings
from ableton_control_surface_as_code.model_v2 import (
    validate_mappings, ModeGroupWithMidi, ModeType, ModeButtonWithMidi,
)
from source_modules.clip_actions import clamp, absolute_to_range
from tests.builders import midi_coords_ch2_cc_50_knob
from tests.custom_assertions import CustomAssertions


def _controller(encoder_mode='absolute', midi_range='21-28'):
    return ControllerV2.build_from(ControllerRawV2(**{
        'light_colors': {},
        'encoder-mode': encoder_mode,
        'control_groups': [ControlGroupPartV2(
            layout='row', number=1, type=EncoderType.knob,
            midi_channel=2, midi_type=MidiType.CC, midi_range=midi_range)],
    }))


def _clip(mappings: dict) -> Clip:
    return Clip(mappings=mappings)


class TestClipRuntimeMath(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(11, 0, 10), 10)

    def test_absolute_to_range_maps_endpoints_and_midpoint(self):
        # gain 0..1
        self.assertAlmostEqual(absolute_to_range(0, 0.0, 1.0), 0.0)
        self.assertAlmostEqual(absolute_to_range(127, 0.0, 1.0), 1.0)
        # pitch_coarse -48..48 with int cast
        self.assertEqual(absolute_to_range(0, -48, 48, "int"), -48)
        self.assertEqual(absolute_to_range(127, -48, 48, "int"), 48)
        self.assertEqual(absolute_to_range(64, -48, 48, "int"), 0)


class TestClipModelBuild(unittest.TestCase):
    def test_builds_encoder_and_button_maps(self):
        clip = _clip({
            'gain': 'row-1:1',
            'loop-start-inc': 'row-1:2',
            'looping': 'row-1:3',
            'move-loop-forward': 'row-1:4',
        })
        result = build_clip_model_v2(_controller(), clip)

        self.assertIsInstance(result, ClipWithMidi)
        actions = {m.action for m in result.midi_maps}
        self.assertEqual(actions, {'gain', 'loop-start-inc', 'looping', 'move-loop-forward'})

        by_action = {m.action: m for m in result.midi_maps}
        self.assertTrue(by_action['gain'].is_encoder())
        self.assertFalse(by_action['loop-start-inc'].is_encoder())
        self.assertFalse(by_action['looping'].is_encoder())
        self.assertEqual(by_action['gain'].runtime_call(), 'set_gain')
        self.assertEqual(by_action['loop-start-inc'].runtime_call(), 'loop_start_inc')
        self.assertEqual(by_action['move-loop-forward'].runtime_call(), 'move_loop_forward')

    def test_encoder_builds_on_absolute_controller(self):
        # Absolute encoders are the supported mode (bounded props mapped 0..127 -> range).
        result = build_clip_model_v2(_controller(encoder_mode='absolute'), _clip({'gain': 'row-1:1'}))
        self.assertEqual(result.midi_maps[0].action, 'gain')

    def test_nudge_action_is_treated_as_encoder_control(self):
        result = build_clip_model_v2(_controller(), _clip({'move-loop': 'row-1:1'}))
        mm = result.midi_maps[0]
        self.assertEqual(mm.kind, 'nudge')
        self.assertEqual(mm.runtime_call(), 'nudge_move_loop')

    def test_unknown_key_is_rejected(self):
        # Typos like "start-loop-inc" must fail loudly, not be silently dropped.
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            _clip({'start-loop-inc': 'row-1:1'})

    def test_unknown_key_message_names_valid_actions(self):
        # The error should name the offending key and list valid actions, which
        # the old bare extra='forbid' error did not do.
        from pydantic import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            _clip({'start-loop-inc': 'row-1:1'})
        msg = str(ctx.exception)
        self.assertIn('start-loop-inc', msg)
        self.assertIn('loop-start-inc', msg)  # a real action, listed as valid


class TestClipTemplates(unittest.TestCase, CustomAssertions):
    def _midi(self, mappings):
        return build_clip_model_v2(_controller(), _clip(mappings))

    def test_encoder_listener_calls_clip_actions_with_value(self):
        result = clip_templates(self._midi({'gain': 'row-1:1'}), 'mode_1')[0]
        self.assert_string_in_one('self.clip_actions.set_gain(value)', result.listener_fns)

    def test_button_listener_gates_on_value_max(self):
        result = clip_templates(self._midi({'looping': 'row-1:3'}), 'mode_1')[0]
        self.assert_string_in_one('if self._helpers.value_is_max(value, 127):', result.listener_fns)
        self.assert_string_in_one('self.clip_actions.toggle_looping()', result.listener_fns)

    def test_inc_dec_button_listener(self):
        result = clip_templates(self._midi({'loop-start-inc': 'row-1:2'}), 'mode_1')[0]
        self.assert_string_in_one('self.clip_actions.loop_start_inc()', result.listener_fns)

    def test_nudge_listener_steps_by_direction(self):
        result = clip_templates(self._midi({'move-loop': 'row-1:5'}), 'mode_1')[0]
        self.assert_string_in_one('if value > previous_value:', result.listener_fns)
        self.assert_string_in_one('self.clip_actions.nudge_move_loop(1.0)', result.listener_fns)
        self.assert_string_in_one('self.clip_actions.nudge_move_loop(-1.0)', result.listener_fns)

    def test_nudge_first_event_only_sets_baseline(self):
        result = clip_templates(self._midi({'move-loop': 'row-1:5'}), 'mode_1')[0]
        # baseline init to None, and the listener returns early on the first event
        self.assert_string_in_one("self._previous_values['knob_ch2_25_CC__mode_mode_1_clip_move_loop_listener'] = None",
                                  result.setup_listeners)
        self.assert_string_in_one('if previous_value is None:', result.listener_fns)

    def test_setup_and_remove_listeners_generated(self):
        result = clip_templates(self._midi({'loop-end-dec': 'row-1:2'}), 'mode_1')[0]
        self.assertEqual(len(result.control_defs), 1)
        self.assert_string_in_one('add_value_listener', result.setup_listeners)
        self.assert_string_in_one('remove_value_listener', result.remove_listeners)


class TestClipEnforcement(unittest.TestCase):
    def test_clip_clashing_with_transport_on_same_coord_raises(self):
        controller = _controller()
        clip = build_clip_model_v2(controller, _clip({'looping': 'row-1:1'}))
        transport = build_transport_model(
            controller, Transport(mappings=TransportMappings(**{'play-stop': 'row-1:1'})))

        with self.assertRaises(GenError):
            validate_mappings([clip, transport], mode_name='main')


class TestClipHudLabels(unittest.TestCase):
    def test_clip_controls_get_prefixed_hud_labels(self):
        from ableton_control_surface_as_code.hud_layout import (
            allocate_global_layout, collect_mode_labels,
        )
        controller = _controller()
        clip = build_clip_model_v2(controller, _clip({
            'gain': 'row-1:1',
            'looping': 'row-1:3',
        }))
        cells = allocate_global_layout(controller)
        labels = collect_mode_labels(controller, [clip], cells)

        self.assertIn('clip: gain', labels.values())
        self.assertIn('clip: loop on', labels.values())


class TestClipIntegration(unittest.TestCase, CustomAssertions):
    def test_full_codegen_emits_valid_clip_listeners(self):
        clip = build_clip_model_v2(_controller(), _clip({
            'gain': 'row-1:1',
            'pitch-coarse': 'row-1:2',
            'looping': 'row-1:3',
            'loop-start-inc': 'row-1:4',
            'sync-loop-and-markers': 'row-1:5',
        }))

        modes = ModeGroupWithMidi(
            mappings=[("mode_1", [clip])],
            mode_button=ModeButtonWithMidi(on_colors=[], button=midi_coords_ch2_cc_50_knob(),
                                           type=ModeType.Switch))

        res = generate_code_as_template_vars(modes)
        listener_block = res['code_listener_fns']
        if isinstance(listener_block, (list, tuple)):
            listener_block = "\n".join(listener_block)

        self.assert_string_in('self.clip_actions.set_gain(value)', listener_block)
        self.assert_string_in('self.clip_actions.set_pitch_coarse(value)', listener_block)
        self.assert_string_in('self.clip_actions.toggle_looping()', listener_block)
        self.assert_string_in('self.clip_actions.loop_start_inc()', listener_block)
        self.assert_string_in('self.clip_actions.sync_loop_and_markers()', listener_block)

        # The generated listener functions must be syntactically valid Python.
        ast.parse(_dedent_class_body(listener_block))


def _dedent_class_body(block: str) -> str:
    # Listener fns are rendered as class-body methods (indented). Wrap them in a
    # class so they parse as a unit.
    indented = "\n".join("    " + line if line.strip() else line for line in block.split("\n"))
    return "class _C:\n" + indented


if __name__ == '__main__':
    unittest.main()
