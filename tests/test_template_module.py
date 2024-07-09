import importlib
import os
import shutil
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from tests.test_code_mixer_template import CustomAssertions

@dataclass
class FakeParameter:
    min:float = 0
    max:float = 127
    value = 0


@dataclass
class FakeDevice:
    parameters: List[FakeParameter] = field(default_factory=list)
    name = "Test Device"




class FakeManager:
    def debug(self):
        return True

    def log_message(self, msg):
        print(msg)


class TestTemplate(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        template_module = self.load_template_file_for_testing()

        self.helpers = template_module.Helpers(FakeManager())

    def tearDown(self):
        # Remove the temporary directory after the test
        shutil.rmtree(self.test_dir)

    def test_sets_correct_parameter(self):
        device = FakeDevice([FakeParameter(), FakeParameter()])
        self.helpers.device_parameter_action(device, 1, 40, "test")

        self.assertEqual(device.parameters[0].value, 0)
        self.assertEqual(device.parameters[1].value, 40)


    def test_sets_toggle_correctly(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0)])

        self.helpers.device_parameter_action(device, 1, 0, "test", toggle=True)
        self.assertEqual(device.parameters[1].value, 0.0)
        self.helpers.device_parameter_action(device, 1, 127, "test", toggle=True)
        self.assertEqual(device.parameters[1].value, 1.0)


    def load_template_file_for_testing(self):
        self.test_dir = tempfile.mkdtemp()
        # Path to the template file
        # self.template_file = os.path.join(self.test_dir, 'template_to_test.py')
        self.template_file = Path(self.test_dir, 'template_to_test.py')
        print(f"self.template_file = {self.template_file}")
        # Write the content of the template file to the temporary directory
        helpers_file = Path("../templates/surface_name/modules/helpers.py")
        self.template_file.write_text(helpers_file.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("template_to_test", self.template_file)
        template_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(template_module)
        return template_module