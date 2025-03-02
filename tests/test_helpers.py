import unittest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import shutil

from source_modules.helpers import Helpers, Remote, NullOSCClient

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.manager = Mock()
        self.manager.debug = True
        self.helpers = Helpers(self.manager, Remote(NullOSCClient()))

    def test_device_parameter_action(self):
        device = Mock()
        device.name = "Test Device"
        device.class_name = "OriginalSimpler"
        device.parameters = [Mock(min=0.0, max=1.0, value=0.1) for _ in range(50)]

        parameter_no = 3 # transpose
        value = 64.0
        midi_no = 23
        fn_name = "test_fn"
        toggle = False

        self.helpers.device_parameter_action(device, parameter_no, midi_no, value, fn_name, toggle)

        self.manager.log_message.assert_called()
        self.assertAlmostEqual(device.parameters[parameter_no].value, 0.5, places=1)


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