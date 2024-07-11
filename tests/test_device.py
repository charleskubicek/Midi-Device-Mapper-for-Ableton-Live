import unittest

from ableton_control_surface_as_code.core_model import RowMapV2_1
from ableton_control_surface_as_code.model_controller import ControllerV2
from ableton_control_surface_as_code.model_device import DeviceV2_1, \
    build_device_model_v2_1
from tests.custom_assertions import CustomAssertions
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part


class TestDevice(unittest.TestCase, CustomAssertions):
    def test_build_device_model_v2(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())

        dev = DeviceV2_1(
            track='selected',
            device='selected',
            ranges=[RowMapV2_1(range="row-1:2-5", parameters="1-4")]
        )

        res = build_device_model_v2_1(controller, dev)

        self.assertEqual(res.midi_maps[0].midi_coords[0].number, 22)
        self.assertEqual(res.midi_maps[0].parameter, 1)

        self.assertEqual(res.midi_maps[3].midi_coords[0].number, 25)
        self.assertEqual(res.midi_maps[3].parameter, 4)

    def test_build_device_model_v2_with_multiple_ranges(self):
        controller = ControllerV2.build_from(build_raw_controller_v2(groups=[
            build_control_group_part("21-28", 1),
            build_control_group_part("31-38", 2)
        ]))

        dev = DeviceV2_1(
            track='selected',
            device='selected',
            ranges=[RowMapV2_1(range="row-1:2-5,row-2:2-5", parameters="1-8")]
        )

        res = build_device_model_v2_1(controller, dev)

        self.assertEqual(len(res.midi_maps), 8)

        self.assertEqual(res.midi_maps[0].midi_coords[0].number, 22)
        self.assertEqual(res.midi_maps[0].parameter, 1)

        self.assertEqual(res.midi_maps[3].midi_coords[0].number, 25)
        self.assertEqual(res.midi_maps[3].parameter, 4)

        self.assertEqual(res.midi_maps[4].midi_coords[0].number, 32)
        self.assertEqual(res.midi_maps[4].parameter, 5)

        self.assertEqual(res.midi_maps[7].midi_coords[0].number, 35)
        self.assertEqual(res.midi_maps[7].parameter, 8)
        self.assertEqual(res.midi_maps[3].parameter, 4)


    def test_build_device_model_v2_with_named_Device(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())

        dev = DeviceV2_1(
            track='master',
            device='MC',
            ranges=[RowMapV2_1(range="row-1:1", parameters="6")]
        )

        res = build_device_model_v2_1(controller, dev)

        self.assertEqual(res.midi_maps[0].midi_coords[0].number, 21)

