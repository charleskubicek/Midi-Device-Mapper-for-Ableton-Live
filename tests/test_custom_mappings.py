import unittest
from unittest.mock import Mock

from source_modules.helpers import CustomMappings, Helpers, SelectedDeviceParameterPaging, ParameterMapping, \
    parse_custom_mappings


class TestCustomMappings(unittest.TestCase):

    def setUp(self):
        self.mappings = {
            "Simpler": [(1, ParameterMapping(2, 'a', None)), (2, ParameterMapping(5, 'b', 'toggle')), (3, ParameterMapping(4, 'c', None))]
            # "Simpler": [(0, (2, 'a', None)), (1, (5, 'b', 'toggle')), (2, (4, 'c', None))]
        }
        self.custom_mappings = CustomMappings(Mock(), self.mappings, {'OriginalSimpler': 'Simpler'})

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

    def test_filter_actual_parameters_with_custom_params_and_page_size(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        device.parameters = self.params(count=6)

        paging = SelectedDeviceParameterPaging(Mock(), page_size=2)

        # Assuming filter_actual_parameters is a method in CustomMappings
        # and it takes a page size as an argument
        real_params = Helpers.get_actual_parameters_from_device(Mock(), self.custom_mappings, paging, device)

        self.assertEqual(len(real_params), 2)
        self.assertEqual(real_params[0].param.name, "p2")
        self.assertEqual(real_params[1].param.name, "p5")
        # self.assertEqual(real_params[2].param.name, "p5")

        paging.device_parameter_page_inc(2)

        real_params = Helpers.get_actual_parameters_from_device(Mock(), self.custom_mappings, paging, device)

        self.assertEqual(len(real_params), 1)
        self.assertEqual(real_params[0].param.name, "p4")
        # self.assertEqual(real_params[1].param.name, "p4")

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
        result = self.custom_mappings.find_parameter(device, 1)
        self.assertEqual(result.param.name, "p1")

    def test_out_of_index_parameter_should_be_none(self):
        device = Mock()
        device.class_name = "UnknownDevice"
        device.parameters = self.params()
        result = self.custom_mappings.find_parameter(device, 10)
        self.assertIsNone(result)


    def test_out_of_index_parameter_for_deivce_with_mappings_should_be_none(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        device.parameters = self.params()
        result = self.custom_mappings.find_parameter(device, 10)
        self.assertIsNone(result)

    def test_find_parameter_with_mappings(self):
        device = Mock()
        device.class_name = "OriginalSimpler"
        device.parameters = self.params(6)
        result = self.custom_mappings.find_parameter(device, 1)
        self.assertEqual(result.param.name, "p2")
        self.assertEqual(result.alias, "a")

    def test_parse_custom_mappings(self):
        custom_mappings_raw = {
            "device1": [
                {"c_idx": 0, "d_idx": 1, "alias": "alias1"},
                {"c_idx": 1, "d_idx": 2, "alias": "alias2", "button": "button1"}
            ],
            "device2": [
                {"c_idx": 0, "d_idx": 3, "alias": "alias3"}
            ]
        }
        expected_result = {
            "device1": [(0, ParameterMapping(1, "alias1", None)), (1, ParameterMapping(2, "alias2", "button1"))],
            "device2": [(0, ParameterMapping(3, "alias3", None))]
        }
        self.assertEqual(parse_custom_mappings(custom_mappings_raw), expected_result)

    def test_parse_custom_mappings_empty(self):
        custom_mappings_raw = {}
        expected_result = {}
        self.assertEqual(parse_custom_mappings(custom_mappings_raw), expected_result)

    def test_parse_custom_mappings_device_empty(self):
        custom_mappings_raw = {
            "device1": []
        }
        expected_result = {
            "device1": []
        }
        self.assertEqual(parse_custom_mappings(custom_mappings_raw), expected_result)


if __name__ == '__main__':
    unittest.main()
