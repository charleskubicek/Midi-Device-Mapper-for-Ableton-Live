import unittest
from dataclasses import dataclass, field
# from typing import List
from unittest.mock import Mock


from source_modules.helpers import Helpers, Remote, NullOSCClient, CustomMappings


@dataclass
class FakeParameter:
    min: float = 0
    max: float = 127
    value: float = 0
    name: str = "p1"


@dataclass
class FakeDevice:
    parameters: list[FakeParameter] = field(default_factory=list)
    name = "Test Device"
    class_name = "Test Device"


class FakeManager:
    def debug(self):
        return True

    def log_message(self, msg):
        print(msg)

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.manager = Mock()
        self.manager.debug = True
        self.manager.log_message.side_effect = lambda x:print(x)
        self.remote_mock = Mock()
        self.mappings = {
            # 3 values for the first 3 encoders on the midi device, Each maps to
            # controller on the ableton device and an alias is applied to each.
            "Simpler": [(0, (2, 'a', None)), (1, (5, 'b', 'toggle')), (2, (4, 'c', None))]
        }

        self.helpers = Helpers(self.manager, self.remote_mock, self.mappings, {"OriginalSimpler": "Simpler"})

    def test_device_parameter_action(self):
        device = Mock()
        device.name = "Simpler"
        device.class_name = "OriginalSimpler"
        device.parameters = [Mock(min=0.0, max=1.0, value=0.1, name=f"param {i}") for i in range(50)]

        parameter_no = 3 # mapped to parameter 4
        value = 64.0
        midi_no = 23
        fn_name = "test_fn"
        toggle = False

        self.helpers.device_parameter_action(device, parameter_no, midi_no, value, fn_name, toggle)

        self.assertAlmostEqual(device.parameters[4].value, 0.5, places=1)
        result = self.remote_mock.parameter_updated.call_args[0]

        self.assertEqual(result[0], device.parameters[4])
        self.assertEqual(result[1], 'c')
        self.assertEqual(result[2], 3)
        self.assertAlmostEqual(result[3], 0.5, places=1)

    def test_sets_correct_parameter_between_0_and_1(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0, value=0.0)])
        self.helpers.device_parameter_action(device, 1, 22, 64.0, "test")

        self.assertEqual(device.parameters[0].value, 0)
        self.assertAlmostEqual(device.parameters[1].value, 0.5, places=2)

    def test_sets_toggle_correctly_for_toggle_button_when_on(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0, value=0.0)])

        self.helpers.device_parameter_action(device, 1, 22, 127, "test", toggle=True)
        self.assertEqual(device.parameters[1].value, 1.0)
        self.helpers.device_parameter_action(device, 1, 22, 0, "test", toggle=True)
        self.assertEqual(device.parameters[1].value, 1.0)

    def test_sets_toggle_correctly_for_toggle_button_when_off(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0, value=0.0)])

        self.helpers.device_parameter_action(device, 1, 22, 127, "test", toggle=False)
        self.assertEqual(1.0, device.parameters[1].value)
        self.helpers.device_parameter_action(device, 1, 22, 0, "test", toggle=False)
        self.assertEqual(0, device.parameters[1].value)

    def test_normalise_within_range(self):
        self.assertAlmostEqual(self.helpers.normalise(65, 0.0, 1.0), 0.5, places=1)
        self.assertAlmostEqual(self.helpers.normalise(0, 0.0, 1.0), 0.0)
        self.assertAlmostEqual(self.helpers.normalise(127, 0.0, 1.0), 1.0)

    def test_normalise_below_min(self):
        self.assertAlmostEqual(self.helpers.normalise(-1, 0.0, 1.0), 0.0)

    def test_normalise_above_max(self):
        self.assertAlmostEqual(self.helpers.normalise(128, 0.0, 1.0), 1.0)

    def test_normalise_with_different_range(self):
        self.assertAlmostEqual(int(self.helpers.normalise(64, 0.0, 10.0)), 5)
        self.assertAlmostEqual(int(self.helpers.normalise(0, -10.0, 10.0)), -10)
        self.assertAlmostEqual(int(self.helpers.normalise(64, -10.0, 10.0)), 0)
        self.assertAlmostEqual(int(self.helpers.normalise(127, -10.0, 10.0)), 10)


if __name__ == '__main__':
    unittest.main()