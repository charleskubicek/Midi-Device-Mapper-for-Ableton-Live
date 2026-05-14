import unittest
from pydantic import ValidationError

from ableton_control_surface_as_code.model_custom_devices import (
    validate_custom_device_mappings,
    CustomDeviceMappings,
)


class TestCustomDeviceMappings(unittest.TestCase):
    def test_plain_encoder_parses(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Bass"}], "buttons": []}]}
        self.assertEqual(validate_custom_device_mappings(raw), raw)

    def test_grouped_encoder_parses(self):
        raw = {"devices": [{
            "className": "AutoFilter2",
            "encoders": [{
                "controlledBy": "LFO T Mode",
                "group": [
                    {"name": "LFO Rate", "activeWhen": [0]},
                    {"name": "LFO Attack", "activeWhen": [1]},
                    {"name": "LFO Sample & Hold", "activeWhen": [2, 3]},
                    {"name": "LFO Stereo", "activeWhen": [4]},
                ],
            }],
            "buttons": [],
        }]}
        validate_custom_device_mappings(raw)

    def test_overlapping_active_when_rejected(self):
        raw = {"devices": [{
            "className": "X",
            "encoders": [{
                "controlledBy": "Mode",
                "group": [
                    {"name": "A", "activeWhen": [0, 1]},
                    {"name": "B", "activeWhen": [1, 2]},
                ],
            }],
            "buttons": [],
        }]}
        with self.assertRaises(ValidationError) as cm:
            CustomDeviceMappings.model_validate(raw)
        self.assertIn("appears in activeWhen", str(cm.exception))

    def test_empty_group_rejected(self):
        raw = {"devices": [{
            "className": "X",
            "encoders": [{"controlledBy": "Mode", "group": []}],
            "buttons": [],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)

    def test_lom_enum_button_parses(self):
        raw = {"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": [{"lom_property": "playback_mode", "type": "enum"}],
        }]}
        validate_custom_device_mappings(raw)

    def test_lom_bool_button_parses(self):
        raw = {"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": [{"lom_property": "pad_slicing", "type": "bool", "display": "Pad Slice"}],
        }]}
        validate_custom_device_mappings(raw)

    def test_lom_function_button_parses(self):
        raw = {"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": [{"lom_function": "crop", "type": "function"}],
        }]}
        validate_custom_device_mappings(raw)

    def test_named_param_button_parses(self):
        raw = {"devices": [{
            "className": "Amp",
            "encoders": [],
            "buttons": [{"name": "Amp Type"}],
        }]}
        validate_custom_device_mappings(raw)

    def test_lom_button_with_display_override(self):
        raw = {"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": [{"lom_property": "playback_mode", "type": "enum", "display": "Mode"}],
        }]}
        validate_custom_device_mappings(raw)

    def test_invalid_button_type_rejected(self):
        raw = {"devices": [{
            "className": "X",
            "encoders": [],
            "buttons": [{"lom_property": "foo", "type": "bogus"}],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)

    def test_missing_active_when_rejected(self):
        raw = {"devices": [{
            "className": "X",
            "encoders": [{
                "controlledBy": "Mode",
                "group": [{"name": "Foo"}],
            }],
            "buttons": [],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)


if __name__ == '__main__':
    unittest.main()
