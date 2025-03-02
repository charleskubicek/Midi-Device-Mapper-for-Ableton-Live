import unittest
from unittest.mock import Mock

from pathlib import Path
import shutil

from source_modules.helpers import CustomMappings


class TestCustomMappings(unittest.TestCase):

    def setUp(self):
        self.mappings = {
            "OriginalSimpler": [(21, 3), (22, 4)]
        }
        self.custom_mappings = CustomMappings(Mock(), self.mappings)

    def test_has_user_defined_parameters_true(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        result = self.custom_mappings.has_user_defined_parameters(device)
        self.assertTrue(result)

    def test_has_user_defined_parameters_false(self):
        device = Mock()
        device.class_name = "UnknownDevice"
        result = self.custom_mappings.has_user_defined_parameters(device)
        self.assertFalse(result)

    # https://remotify.io/device-parameters/device_params_live11.html
    def test_find_user_defined_parameters_including_param_zero_for_on_off(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        default_parameters = self.params()
        device.parameters = default_parameters
        result = self.custom_mappings.find_user_defined_parameters_or_defaults(device)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].name, "p1")
        self.assertEqual(result[1].name, "p4")
        self.assertEqual(result[2].name, "p5")

    def mock_param(self, name):
        param = Mock()
        param.name = name
        return param

    def params(self):
        return [self.mock_param(p) for p in ['p1', 'p2', 'p3', 'p4', 'p5']]

    def test_find_parameter_without_mappings(self):
        device = Mock()
        device.class_name = "UnknownDevice"
        device.parameters = self.params()
        result = self.custom_mappings.find_parameter(device, 1, 0)
        self.assertEqual(result.name, "Param1")


if __name__ == '__main__':
    unittest.main()
