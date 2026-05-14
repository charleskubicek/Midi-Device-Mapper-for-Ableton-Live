"""Schema tests for name-keyed custom device mappings.

After the index→name migration, `name` is required on encoders, group
members, and param-kind buttons; `number` is no longer accepted.

Kept separate from the legacy `test_model_custom_devices.py` so the diff
during the migration is clear.
"""

import unittest
from pydantic import ValidationError

from ableton_control_surface_as_code.model_custom_devices import (
    CustomDeviceMappings,
    validate_custom_device_mappings,
)


class TestNameSchema(unittest.TestCase):
    def test_encoder_name_required(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{}], "buttons": []}]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)

    def test_button_param_name_required(self):
        raw = {"devices": [{
            "className": "Amp", "encoders": [],
            "buttons": [{"type": "param"}],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)

    def test_group_member_name_required(self):
        raw = {"devices": [{
            "className": "AutoFilter2",
            "encoders": [{
                "controlledBy": "LFO T Mode",
                "group": [{"activeWhen": [0]}],
            }],
            "buttons": [],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)

    def test_legacy_number_field_rejected(self):
        """`number` is no longer authoritative — emitting it should fail
        validation (extra='forbid') so old configs are caught loudly."""
        raw = {"devices": [{
            "className": "Amp",
            "encoders": [{"number": 1, "name": "Bass"}],
            "buttons": [],
        }]}
        with self.assertRaises(ValidationError):
            CustomDeviceMappings.model_validate(raw)

    def test_plain_named_encoder_parses(self):
        raw = {"devices": [{
            "className": "Amp",
            "encoders": [{"name": "Bass", "display": "B"}],
            "buttons": [{"name": "Amp Type"}],
        }]}
        validate_custom_device_mappings(raw)

    def test_named_group_parses(self):
        raw = {"devices": [{
            "className": "AutoFilter2",
            "encoders": [{
                "controlledBy": "LFO T Mode",
                "group": [
                    {"name": "L Rate", "activeWhen": [0]},
                    {"name": "L Attack", "activeWhen": [1, 2]},
                ],
            }],
            "buttons": [],
        }]}
        validate_custom_device_mappings(raw)

    def test_lom_buttons_still_parse(self):
        raw = {"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": [
                {"lom_property": "playback_mode", "type": "enum"},
                {"lom_property": "pad_slicing", "type": "bool"},
                {"lom_function": "crop", "type": "function"},
            ],
        }]}
        validate_custom_device_mappings(raw)


if __name__ == '__main__':
    unittest.main()
