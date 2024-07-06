import unittest

from ableton_control_suface_as_code.core_model import RowMapV2_1
from ableton_control_suface_as_code.model_controller import ControllerV2
from ableton_control_suface_as_code.model_device import DeviceV2_1, \
    build_device_model_v2_1
from tests.test_code_mixer_template import CustomAssertions
from tests.test_gen_build_model_v2 import build_raw_controller_v2


class TestDevice(unittest.TestCase, CustomAssertions):
    def test_build_device_model_v2(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())

        dev = DeviceV2_1(
            track='selected',
            device='selected',
            ranges=[RowMapV2_1(range="row_1:2-5", parameters="1-4")]
        )

        res = build_device_model_v2_1(controller, dev)

        self.assertEqual(res.midi_maps[0].midi_coords[0].number, 22)
        self.assertEqual(res.midi_maps[0].parameter, 1)

        self.assertEqual(res.midi_maps[3].midi_coords[0].number, 25)
        self.assertEqual(res.midi_maps[3].parameter, 4)
