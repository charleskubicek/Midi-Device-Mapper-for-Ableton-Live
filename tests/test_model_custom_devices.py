import unittest
from pydantic import ValidationError

from ableton_control_surface_as_code.model_custom_devices import (
    validate_custom_device_mappings,
    CustomDeviceMappings,
)


class TestCustomDeviceMappings(unittest.TestCase):
    def test_plain_encoder_parses(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{"number": 1, "name": "Bass"}], "buttons": []}]}
        self.assertEqual(validate_custom_device_mappings(raw), raw)

    def test_grouped_encoder_parses(self):
        raw = {"devices": [{
            "className": "AutoFilter2",
            "encoders": [{
                "controlledBy": "LFO T Mode",
                "group": [
                    {"number": 15, "activeWhen": [0]},
                    {"number": 16, "activeWhen": [1]},
                    {"number": 17, "activeWhen": [2, 3]},
                    {"number": 18, "activeWhen": [4]},
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
                    {"number": 10, "activeWhen": [0, 1]},
                    {"number": 11, "activeWhen": [1, 2]},
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

    def test_missing_active_when_rejected(self):
        raw = {"devices": [{
            "className": "X",
            "encoders": [{
                "controlledBy": "Mode",
                "group": [{"number": 10}],
            }],
            "buttons": [],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)


if __name__ == '__main__':
    unittest.main()
