import unittest
from unittest.mock import Mock

from pathlib import Path
import shutil


helpers_file = Path(__file__).resolve().parent.parent / 'templates' / 'surface_name' / 'modules' / 'helpers.py'
helpers_tmp_file = Path(__file__).resolve().parent / 'helpers_cp.py'
shutil.copy(helpers_file, helpers_tmp_file)

from .helpers_cp import CustomMappings


class TestCustomMappings(unittest.TestCase):

    def setUp(self):
        self.mappings = {
            "OriginalSimpler": {"Transpose": 3, "Volume": 30}
        }
        self.custom_mappings = CustomMappings(self.mappings)

    def test_has_user_defined_parameters_true(self):
        device = Mock(spec=Device)
        device.class_name = "OriginalSimpler"
        result = self.custom_mappings.has_user_defined_parameters(device)
        self.assertTrue(result)

    def test_has_user_defined_parameters_false(self):
        device = Mock(spec=Device)
        device.class_name = "UnknownDevice"
        result = self.custom_mappings.has_user_defined_parameters(device)
        self.assertFalse(result)

    def test_find_user_defined_parameters_or_defaults_with_mappings(self):
        device = Mock(spec=Device)
        device.class_name = "OriginalSimpler"
        device.parameters = []
        result = self.custom_mappings.find_user_defined_parameters_or_defaults(device)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Transpose")
        self.assertEqual(result[1].name, "Volume")

    def test_find_user_defined_parameters_or_defaults_without_mappings(self):
        device = Mock(spec=Device)
        device.class_name = "UnknownDevice"
        default_parameters = [Parameter(name="DefaultParam")]
        device.parameters = default_parameters
        result = self.custom_mappings.find_user_defined_parameters_or_defaults(device)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "DefaultParam")

    def test_find_parameter_with_mappings(self):
        device = Mock(spec=Device)
        device.class_name = "OriginalSimpler"
        parameters = [
            Parameter(name="Param0"),
            Parameter(name="Param1"),
            Parameter(name="Param2"),
            Parameter(name="Transpose"),
            Parameter(name="Param4")
        ]
        device.parameters = parameters
        result = self.custom_mappings.find_parameter(device, 0, 3)
        self.assertEqual(result.name, "Transpose")

    def test_find_parameter_without_mappings(self):
        device = Mock(spec=Device)
        device.class_name = "UnknownDevice"
        parameters = [
            Parameter(name="Param0"),
            Parameter(name="Param1")
        ]
        device.parameters = parameters
        result = self.custom_mappings.find_parameter(device, 1, 0)
        self.assertEqual(result.name, "Param1")

if __name__ == '__main__':
    unittest.main()