import unittest

from pydantic import ValidationError

from ableton_control_surface_as_code.core_model import RowMapV2_1
from ableton_control_surface_as_code.gen_code import (
    code_from_slot_assignments,
    device_templates,
    dict_variable_decleration_block,
    functions_templates,
    GeneratedCode,
    GeneratedCodes,
)
from ableton_control_surface_as_code.core_model import (
    MidiCoords, EncoderType, EncoderMode, TrackInfo,
)
from ableton_control_surface_as_code.encoder_coords import Momentary, Toggle
from ableton_control_surface_as_code.model_device import (
    DeviceWithMidi as DeviceWithMidiModel, DeviceParameterMidiMapping,
)
from ableton_control_surface_as_code.model_functions import (
    FunctionsWithMidi, FunctionsMidiMapping,
)
from ableton_control_surface_as_code.model_controller import ControllerV2
from ableton_control_surface_as_code.model_device import (
    DeviceEncoderMappings,
    DeviceV2,
    build_device_model_v2_1,
    parse_continuous_slot_list,
    parse_slot_token,
)
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part, build_control_group


class TestSlotParsing(unittest.TestCase):
    def test_range_shorthand_expands_to_slot_names(self):
        self.assertEqual(
            parse_continuous_slot_list("1-8"),
            [f"slot{i}" for i in range(1, 9)],
        )

    def test_mixed_individual_and_range(self):
        self.assertEqual(
            parse_continuous_slot_list("1,slot3,5-7"),
            ["slot1", "slot3", "slot5", "slot6", "slot7"],
        )

    def test_canonical_names_pass_through(self):
        self.assertEqual(parse_slot_token("slot1"), "slot1")
        self.assertEqual(parse_slot_token("switch1"), "switch1")

    def test_bare_int_expands(self):
        self.assertEqual(parse_slot_token("3"), "slot3")

    def test_rejects_switch_in_continuous_list(self):
        with self.assertRaises(ValueError) as cm:
            parse_continuous_slot_list("1,switch1,3")
        self.assertIn("switch1", str(cm.exception))

    def test_no_upper_limit_on_slot_index(self):
        # slots are just indices into device parameters; no arbitrary cap
        self.assertEqual(parse_slot_token("100"), "slot100")

    def test_rejects_zero(self):
        with self.assertRaises(ValueError):
            parse_slot_token("0")

    def test_rejects_unknown_token(self):
        with self.assertRaises(ValueError):
            parse_slot_token("garbage")


class TestRowMapV2_1ExclusiveFields(unittest.TestCase):
    def test_slots_only_is_valid(self):
        m = RowMapV2_1(range="row-1:1-4", slots="1-4")
        self.assertTrue(m.uses_slots)
        self.assertEqual(m.slots, ["slot1", "slot2", "slot3", "slot4"])

    def test_parameters_only_is_valid(self):
        m = RowMapV2_1(range="row-1:1-4", parameters="1-4")
        self.assertFalse(m.uses_slots)

    def test_both_slots_and_parameters_rejected(self):
        with self.assertRaises(ValidationError):
            RowMapV2_1(range="row-1:1-4", parameters="1-4", slots="1-4")

    def test_neither_rejected(self):
        with self.assertRaises(ValidationError):
            RowMapV2_1(range="row-1:1-4")


class TestSlotAssignmentsCodegen(unittest.TestCase):
    def test_emits_flat_tuple_list(self):
        lines = code_from_slot_assignments([(1, "slot1"), (2, "slot2"), (3, "slot3")])
        self.assertEqual(lines, ["(1, 'slot1')", "(2, 'slot2')", "(3, 'slot3')"])

    def test_mode_slots_excluded(self):
        lines = code_from_slot_assignments([(1, "slot1"), (2, "switch1")])
        self.assertEqual(lines, ["(1, 'slot1')"])

    def test_empty_input_emits_nothing(self):
        self.assertEqual(code_from_slot_assignments([]), [])


class TestDictVariableDeclerationBlock(unittest.TestCase):
    """The per-mode blocks rendered into the `code_*_parameter_mappings`
    list literals. Each element is one mode's already-comma-joined tuples."""

    def _is_valid_list_literal(self, body):
        # The block is spliced between `[` and `]` in the template; eval it the
        # same way to prove two adjacent mode-blocks don't read as a tuple call.
        return eval(f"[{body}]")

    def test_two_non_empty_modes_are_comma_separated(self):
        body = dict_variable_decleration_block(
            ["(0, 'switch1'),\n\t\t\t(1, 'switch2')", "(0, 'switch1'),\n\t\t\t(1, 'switch2')"]
        )
        self.assertEqual(
            self._is_valid_list_literal(body),
            [(0, 'switch1'), (1, 'switch2'), (0, 'switch1'), (1, 'switch2')],
        )

    def test_empty_mode_block_is_dropped(self):
        body = dict_variable_decleration_block(["(1, 'slot1')", ""])
        self.assertEqual(self._is_valid_list_literal(body), [(1, 'slot1')])

    def test_all_empty_emits_nothing(self):
        self.assertEqual(dict_variable_decleration_block(["", ""]), "")

    def test_empty_list_emits_nothing(self):
        self.assertEqual(dict_variable_decleration_block([]), "")


class TestDeviceWithMidiEncoderSlotCount(unittest.TestCase):
    def _build(self, mappings_raw, rows=1):
        groups = [build_control_group_part(number=i, midi_range=f"{21 + (i-1)*8}-{28 + (i-1)*8}") for i in range(1, rows + 1)]
        controller = ControllerV2.build_from(build_raw_controller_v2(groups=groups))
        dev = DeviceV2.model_validate({"track": "selected", "device": "selected", "mappings": mappings_raw})
        return build_device_model_v2_1(controller, dev, root_dir="")

    def test_single_encoder_row_of_8(self):
        dwm = self._build({"encoders": {"range": "row-1:1-8", "slots": "1-8"}})
        self.assertEqual(dwm.encoder_slot_count, 8)

    def test_two_encoder_rows_of_8_gives_16(self):
        dwm = self._build({"encoder-list": [
            {"range": "row-1:1-8", "slots": "1-8"},
            {"range": "row-2:1-8", "slots": "9-16"},
        ]}, rows=2)
        self.assertEqual(dwm.encoder_slot_count, 16)

    def test_single_row_of_4(self):
        dwm = self._build({"encoders": {"range": "row-1:1-4", "slots": "1-4"}})
        self.assertEqual(dwm.encoder_slot_count, 4)


class TestDeviceTemplatesWithSlots(unittest.TestCase):
    def test_continuous_slot_listener_calls_device_parameter_action(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())
        dev = DeviceV2(
            track="selected",
            device="selected",
            mappings=DeviceEncoderMappings(
                encoders=RowMapV2_1(range="row-1:1-4", slots="1-4"),
            ),
        )
        device_with_midi = build_device_model_v2_1(controller, dev, root_dir="")
        result = GeneratedCodes.merge_all(device_templates(device_with_midi, "main"))

        all_fns = "\n".join(result.listener_fns)
        self.assertIn("self.device_parameter_action(device, 1, 21, value,", all_fns)
        self.assertIn("self.device_parameter_action(device, 4, 24, value,", all_fns)
        # slot list emitted as a flat tuple list
        joined = "\n".join(result.custom_parameter_mappings)
        self.assertIn("(1, 'slot1')", joined)
        self.assertIn("(4, 'slot4')", joined)

    def test_mode_button_listener_calls_switch_slot_action(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())
        dev = DeviceV2(
            track="selected",
            device="selected",
            mappings=DeviceEncoderMappings.model_validate({
                "encoders": {"range": "row-1:1-4", "slots": "1-4"},
                "mode-buttons": [{"coord": "row-1:5", "slot": "switch1"}],
            }),
        )
        device_with_midi = build_device_model_v2_1(controller, dev, root_dir="")
        result = GeneratedCodes.merge_all(device_templates(device_with_midi, "main"))
        all_fns = "\n".join(result.listener_fns)

        self.assertIn('self._helpers.switch_slot_action(device, "switch1", value,', all_fns)


class TestMergeConcatenatesParameterMappings(unittest.TestCase):
    def test_merge_concatenates_two_non_empty_custom_mappings(self):
        one = GeneratedCode(custom_parameter_mappings=["(1, 'slot1')"])
        other = GeneratedCode(custom_parameter_mappings=["(2, 'slot2')"])
        merged = GeneratedCodes.merge(one, other)
        self.assertEqual(merged.custom_parameter_mappings,
                         ["(1, 'slot1')", "(2, 'slot2')"])

    def test_merge_concatenates_two_non_empty_switch_mappings(self):
        one = GeneratedCode(switch_parameter_mappings=["(0, 'switch1')"])
        other = GeneratedCode(switch_parameter_mappings=["(1, 'switch2')"])
        merged = GeneratedCodes.merge(one, other)
        self.assertEqual(merged.switch_parameter_mappings,
                         ["(0, 'switch1')", "(1, 'switch2')"])

    def test_two_device_mappings_with_slots_both_survive_merge(self):
        controller = ControllerV2.build_from(build_raw_controller_v2(groups=[
            build_control_group(midi_range='21-28', number=1),
            build_control_group(midi_range='31-38', number=2),
        ]))
        dev1 = DeviceV2(
            track="selected", device="selected",
            mappings=DeviceEncoderMappings(
                encoders=RowMapV2_1(range="row-1:1-4", slots="1-4")),
        )
        dev2 = DeviceV2(
            track="selected", device="selected",
            mappings=DeviceEncoderMappings(
                encoders=RowMapV2_1(range="row-2:1-4", slots="5-8")),
        )
        dwm1 = build_device_model_v2_1(controller, dev1, root_dir="")
        dwm2 = build_device_model_v2_1(controller, dev2, root_dir="")
        codes = device_templates(dwm1, "main") + device_templates(dwm2, "main")
        result = GeneratedCodes.merge_all(codes)
        joined = "\n".join(result.custom_parameter_mappings)
        self.assertIn("'slot1'", joined)  # from dev1
        self.assertIn("'slot8'", joined)  # from dev2 — previously dropped


def _midi(encoder_type=EncoderType.button, refs=None, number=51, channel=1):
    return MidiCoords(channel=channel, type="CC", number=number, encoder_type=encoder_type,
                      encoder_mode=EncoderMode.Absolute, source_info="tests",
                      encoder_refs=refs or [])


def _functions_with_midi(refs=None):
    return FunctionsWithMidi(midi_maps=[FunctionsMidiMapping(
        midi_coords=[_midi(EncoderType.button, refs)],
        function_name="toggle", parameter_len=0)])


def _device_with_midi(encoder_type=EncoderType.button, refs=None):
    return DeviceWithMidiModel(
        track=TrackInfo.selected(), device="selected",
        midi_maps=[DeviceParameterMidiMapping(
            midi_coords=[_midi(encoder_type, refs)], parameter=1)])


class TestMethodCallButtonPressBehavior(unittest.TestCase):
    """Method-call buttons (functions/nav/transport) act once on press by default;
    `momentary` opts back into fire-on-both-edges."""

    def _fns(self, refs=None):
        result = GeneratedCodes.merge_all(functions_templates(_functions_with_midi(refs), "main"))
        return "\n".join(result.listener_fns)

    def test_default_button_is_press_once(self):
        code = self._fns(refs=[])
        # press-once routes through the hardware-aware edge guard, not a raw 127 check
        self.assertIn("self._helpers.should_act_on_edge(value)", code)
        self.assertNotIn("if True:", code)

    def test_momentary_button_fires_both_edges(self):
        code = self._fns(refs=[Momentary.instance()])
        self.assertIn("if True:", code)
        self.assertNotIn("should_act_on_edge", code)

    def test_toggle_keyword_is_now_a_no_op_default(self):
        # `toggle` no longer changes anything — same press-only code as default.
        self.assertEqual(self._fns(refs=[Toggle.instance()]), self._fns(refs=[]))

    def test_toggle_and_momentary_together_momentary_wins(self):
        code = self._fns(refs=[Toggle.instance(), Momentary.instance()])
        self.assertIn("if True:", code)


class TestDeviceParamButtonPressBehavior(unittest.TestCase):
    def _fns(self, encoder_type=EncoderType.button, refs=None):
        result = GeneratedCodes.merge_all(device_templates(_device_with_midi(encoder_type, refs), "main"))
        return "\n".join(result.listener_fns)

    def test_button_default_latches(self):
        self.assertIn("toggle=True", self._fns(EncoderType.button, refs=[]))

    def test_button_momentary_holds(self):
        self.assertIn("toggle=False", self._fns(EncoderType.button, refs=[Momentary.instance()]))

    def test_knob_never_latches(self):
        self.assertIn("toggle=False", self._fns(EncoderType.knob, refs=[]))
        # the is_button() gate: a knob must stay continuous even with momentary
        self.assertIn("toggle=False", self._fns(EncoderType.knob, refs=[Momentary.instance()]))

    def test_slider_never_latches(self):
        self.assertIn("toggle=False", self._fns(EncoderType.slider, refs=[]))


class TestSwitchSlotPressGuard(unittest.TestCase):
    def test_switch_dispatch_is_press_guarded(self):
        from ableton_control_surface_as_code.model_controller import ControllerV2
        from ableton_control_surface_as_code.model_device import (
            DeviceEncoderMappings, DeviceV2, build_device_model_v2_1,
        )
        controller = ControllerV2.build_from(build_raw_controller_v2())
        dev = DeviceV2(
            track="selected", device="selected",
            mappings=DeviceEncoderMappings.model_validate({
                "encoders": {"range": "row-1:1-4", "slots": "1-4"},
                "mode-buttons": [{"coord": "row-1:5", "slot": "switch1"}],
            }),
        )
        device_with_midi = build_device_model_v2_1(controller, dev, root_dir="")
        result = GeneratedCodes.merge_all(device_templates(device_with_midi, "main"))
        all_fns = "\n".join(result.listener_fns)
        # the switch_slot_action call must be guarded by the hardware-aware edge check
        self.assertIn("self._helpers.should_act_on_edge(value)", all_fns)
        guard_idx = all_fns.index("self._helpers.should_act_on_edge(value)")
        call_idx = all_fns.index("self._helpers.switch_slot_action")
        self.assertLess(guard_idx, call_idx)


class TestDoctorObserveHook(unittest.TestCase):
    def test_method_call_button_emits_button_event(self):
        result = GeneratedCodes.merge_all(functions_templates(_functions_with_midi(), "main"))
        self.assertIn("self._helpers.button_event(", "\n".join(result.listener_fns))

    def test_device_param_button_emits_button_event(self):
        result = GeneratedCodes.merge_all(device_templates(_device_with_midi(EncoderType.button), "main"))
        self.assertIn("self._helpers.button_event(", "\n".join(result.listener_fns))

    def test_knob_param_does_not_emit_button_event(self):
        result = GeneratedCodes.merge_all(device_templates(_device_with_midi(EncoderType.knob), "main"))
        self.assertNotIn("button_event", "\n".join(result.listener_fns))


if __name__ == "__main__":
    unittest.main()
