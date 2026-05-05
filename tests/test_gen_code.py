import unittest

from pydantic import ValidationError

from ableton_control_surface_as_code.core_model import RowMapV2_1
from ableton_control_surface_as_code.family_intents import (
    parse_continuous_slot_list,
    parse_slot_token,
)
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
)
from tests.test_gen_build_model_v2 import build_raw_controller_v2


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
        self.assertEqual(parse_slot_token("switch2"), "switch2")

    def test_bare_int_expands(self):
        self.assertEqual(parse_slot_token("3"), "slot3")

    def test_rejects_switch1_in_continuous_list(self):
        with self.assertRaises(ValueError) as cm:
            parse_continuous_slot_list("1,switch1,3")
        self.assertIn("switch1", str(cm.exception))
        self.assertIn("mode-buttons", str(cm.exception))

    def test_rejects_switch2_in_continuous_list(self):
        with self.assertRaises(ValueError):
            parse_continuous_slot_list("switch2")

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            parse_slot_token("9")

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
    def test_emits_one_entry_per_supported_class(self):
        # slot1 in family-intents covers ~36 device classes; assert a few we know about.
        lines = code_from_slot_assignments([(1, "slot1")])
        joined = "\n".join(lines)
        self.assertIn("'Compressor2':", joined)
        self.assertIn("'Eq8':", joined)
        # Compressor2 slot1 is Dry/Wet at parameter 9.
        self.assertIn("'c_idx': 1, 'd_idx': 9, 'alias': 'Dry/Wet'", joined)

    def test_classes_lacking_a_slot_get_no_entry_for_it(self):
        # slot8 is sparse; assert classes are only present when they support the slot.
        lines = code_from_slot_assignments([(1, "slot8")])
        # Expect the dict to be small. None of the major classes (Compressor2, Eq8) have slot8.
        joined = "\n".join(lines)
        self.assertNotIn("'Compressor2':", joined)

    def test_mode_slots_excluded_from_dict(self):
        # switch1 is handled by mode-buttons; should not show up in the per-class dict.
        lines = code_from_slot_assignments([(1, "slot1"), (2, "switch1")])
        joined = "\n".join(lines)
        # switch1's parameter 10 (Compressor2's "Model") shouldn't show as a c_idx=2 entry.
        # All entries should have c_idx=1.
        self.assertIn("'c_idx': 1, 'd_idx': 9, 'alias': 'Dry/Wet'", joined)
        self.assertNotIn("'c_idx': 2", joined)

    def test_empty_input_emits_nothing(self):
        self.assertEqual(code_from_slot_assignments([]), [])


class TestDeviceTemplatesWithSlots(unittest.TestCase):
    def test_continuous_slot_listener_dispatches_via_custom_mappings(self):
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
        # Listener still calls device_parameter_action with the encoder index;
        # the slot dispatch happens via the runtime custom_mappings dict.
        self.assertIn("self.device_parameter_action(device, 1, 21, value,", all_fns)
        self.assertIn("self.device_parameter_action(device, 4, 24, value,", all_fns)
        # The custom_parameter_mappings should include classes the slots cover.
        joined_mappings = "\n".join(result.custom_parameter_mappings)
        self.assertIn("'Compressor2':", joined_mappings)
        self.assertIn("'c_idx': 1, 'd_idx': 9, 'alias': 'Dry/Wet'", joined_mappings)

    def test_mode_button_listener_uses_cycle_helper(self):
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

        self.assertIn("self._helpers.device_param_cycle(device,", all_fns)
        # Cycle table should include Compressor2's switch1 (param 10, range 0..2).
        self.assertIn("'Compressor2': ('cycle', (10, 0, 2))", all_fns)


if __name__ == "__main__":
    unittest.main()
