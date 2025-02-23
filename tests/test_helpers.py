import unittest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import shutil


helpers_file = Path(__file__).resolve().parent.parent / 'templates' / 'surface_name' / 'modules' / 'helpers.py'
helpers_tmp_file = Path(__file__).resolve().parent / 'helpers_cp.py'
shutil.copy(helpers_file, helpers_tmp_file)

from .helpers_cp import Helpers

class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.manager = Mock()
        self.manager.debug = True
        self.helpers = Helpers(self.manager)

    def tearDown(self):
        # helpers_tmp_file.unlink()
        pass

    def test_device_parameter_action(self):
        device = Mock()
        device.name = "Test Device"
        device.class_name = "OriginalSimpler"
        device.parameters = [Mock(min=0.0, max=1.0, value=0.5) for _ in range(50)]

        parameter_no = 3 # transpose
        value = 64
        fn_name = "test_fn"
        toggle = False

        self.helpers.device_parameter_action(device, parameter_no, value, fn_name, toggle)

        self.manager.log_message.assert_called()
        self.assertEqual(device.parameters[parameter_no].value, 0.5)

if __name__ == '__main__':
    unittest.main()