import unittest
from unittest.mock import Mock

from pathlib import Path
import shutil

from source_modules.helpers import CustomMappings, Helpers, SelectedDeviceParameterPaging


class TestCustomMappings(unittest.TestCase):

    def setUp(self):
        self.mappings = {
            "OriginalSimpler": [(0, (2, 'a')), (1, (5, 'b')), (2, (4, 'c'))]
        }
        self.custom_mappings = CustomMappings(Mock(), self.mappings)

    def test_has_user_defined_parameters_true(self):
        result = self.custom_mappings.has_user_defined_parameters("OriginalSimpler")
        self.assertTrue(result)

    def test_has_user_defined_parameters_false(self):
        device = Mock()
        device.class_name = "UnknownDevice"
        result = self.custom_mappings.has_user_defined_parameters(device.class_name)
        self.assertFalse(result)

    # https://remotify.io/device-parameters/device_params_live11.html
    def test_find_user_defined_parameters_including_param_zero_for_on_off(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        default_parameters = self.params()
        device.parameters = default_parameters
        result = self.custom_mappings.user_defined_parameters_or_defaults(device)

        self.assertEqual(result.on_off, (0, 'On/Off'))
        self.assertEqual(result.parameters, [(2, 'a'), (5, 'b'), (4, 'c')])

        actual_parameters = result.parameters_and_aliasses_from_device_params(device.parameters, include_on_off=True)
        self.assertEqual(len(actual_parameters), 4)

        self.assertEqual(actual_parameters[0][0].name, "p0")
        self.assertEqual(actual_parameters[1][0].name, "p2")
        self.assertEqual(actual_parameters[2][0].name, "p5")
        self.assertEqual(actual_parameters[3][0].name, "p4")

    def test_filter_actual_parameters_with_custom_params_and_page_size(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        device.parameters = self.params(count=6)

        paging = SelectedDeviceParameterPaging(Mock(), page_size=2)

        # Assuming filter_actual_parameters is a method in CustomMappings
        # and it takes a page size as an argument
        real_params = Helpers.get_actual_parameters_from_device(Mock(), self.custom_mappings, paging, device)

        self.assertEqual(len(real_params), 3)
        self.assertEqual(real_params[0][0].name, "p0")
        self.assertEqual(real_params[1][0].name, "p2")
        self.assertEqual(real_params[2][0].name, "p5")

        paging.device_parameter_page_inc(2)

        real_params = Helpers.get_actual_parameters_from_device(Mock(), self.custom_mappings, paging, device)

        self.assertEqual(len(real_params), 2)
        self.assertEqual(real_params[0][0].name, "p0")
        self.assertEqual(real_params[1][0].name, "p4")

    def mock_param(self, name):
        param = Mock()
        param.name = name
        return param

    def params(self, count = 6):
        # return [self.mock_param(p) for p in ['p0', 'p1', 'p2', 'p3', 'p4', 'p5']]
        return [self.mock_param(f"p{i}") for i in range(0, count)]

    def test_find_parameter_without_mappings(self):
        device = Mock()
        device.class_name = "UnknownDevice"
        device.parameters = self.params()
        result, alias = self.custom_mappings.find_parameter(device, 1)
        self.assertEqual(result.name, "p1")


    def test_find_parameter_with_mappings(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        device.parameters = self.params(6)
        result, alias = self.custom_mappings.find_parameter(device, 1)
        self.assertEqual(result.name, "p2")
        self.assertEqual(alias, "a")


if __name__ == '__main__':
    unittest.main()
