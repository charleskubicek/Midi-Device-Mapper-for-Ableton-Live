import unittest

from pydantic import ValidationError

from ableton_control_surface_as_code.core_model import RowMapV2_1
from ableton_control_surface_as_code.gen_code import (
    code_from_slot_assignments,
    device_templates,
    GeneratedCodes,
)
from ableton_control_surface_as_code.model_controller import ControllerV2
from ableton_control_surface_as_code.model_device import (
    DeviceEncoderMappings,
    DeviceV2,
    build_device_model_v2_1,
    parse_continuous_slot_list,
    parse_slot_token,
)
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part


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


if __name__ == "__main__":
    unittest.main()
