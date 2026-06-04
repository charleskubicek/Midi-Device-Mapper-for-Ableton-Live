import unittest

from pydantic import ValidationError

from ableton_control_surface_as_code.core_model import RowMapV2_1
from ableton_control_surface_as_code.model_controller import ControllerV2
from ableton_control_surface_as_code.model_device import DeviceV2, \
    build_device_model_v2_1, DeviceEncoderMappings, SwitchListEntry
from tests.custom_assertions import CustomAssertions
from tests.test_gen_build_model_v2 import build_raw_controller_v2, build_control_group_part, build_control_group


class TestDevice(unittest.TestCase, CustomAssertions):
    def test_build_device_model_v2(self):
        controller = ControllerV2.build_from(build_raw_controller_v2())

        dev = DeviceV2(
            track='selected',
            device='selected',
            mappings=DeviceEncoderMappings(encoders=RowMapV2_1(range="row-1:2-5", parameters="1-4")),
        )

        res = build_device_model_v2_1(controller, dev, root_dir="")

        self.assertEqual(res.midi_maps[0].midi_coords[0].number, 22)
        self.assertEqual(res.midi_maps[0].parameter, 1)

        self.assertEqual(res.midi_maps[3].midi_coords[0].number, 25)
        self.assertEqual(res.midi_maps[3].parameter, 4)

    def test_build_device_model_v2_with_multiple_ranges(self):
        controller = ControllerV2.build_from(build_raw_controller_v2(groups=[
            build_control_group_part("21-28", 1),
            build_control_group_part("31-38", 2)
        ]))

        dev = DeviceV2(
            track='selected',
            device='selected',
            mappings=DeviceEncoderMappings(encoders=RowMapV2_1(range="row-1:2-5,row-2:2-5", parameters="1-8")),
        )

        res = build_device_model_v2_1(controller, dev, root_dir="")

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

        dev = DeviceV2(
            track='master',
            device='MC',
            mappings=DeviceEncoderMappings(encoders=RowMapV2_1(range="row-1:1", parameters="6")),
        )

        res = build_device_model_v2_1(controller, dev, root_dir="")

        self.assertEqual(res.midi_maps[0].midi_coords[0].number, 21)


class TestSwitchList(unittest.TestCase):
    def _controller(self):
        return ControllerV2.build_from(build_raw_controller_v2(groups=[
            build_control_group('21-28', number=1),
            build_control_group('31-38', number=2),
        ]))

    def test_single_range_maps_to_switch_slots(self):
        controller = self._controller()
        dev = DeviceV2.model_validate({
            'track': 'selected',
            'device': 'selected',
            'mappings': {
                'encoder-list': [{'range': 'row-1:1-4', 'slots': '1-4'}],
                'switch-list': [{'range': 'row-2:1-4'}],
            },
        })
        res = build_device_model_v2_1(controller, dev, root_dir="")

        switch_maps = [m for m in res.mode_button_maps if m.slot.startswith('switch')]
        self.assertEqual(len(switch_maps), 4)
        self.assertEqual(switch_maps[0].slot, 'switch1')
        self.assertEqual(switch_maps[1].slot, 'switch2')
        self.assertEqual(switch_maps[2].slot, 'switch3')
        self.assertEqual(switch_maps[3].slot, 'switch4')
        self.assertEqual(switch_maps[0].midi_coords.number, 31)
        self.assertEqual(switch_maps[3].midi_coords.number, 34)

    def test_multi_range_merges_in_order(self):
        controller = self._controller()
        dev = DeviceV2.model_validate({
            'track': 'selected',
            'device': 'selected',
            'mappings': {
                'encoder-list': [{'range': 'row-1:1-4', 'slots': '1-4'}],
                'switch-list': [
                    {'range': 'row-2:1-2'},
                    {'range': 'row-2:3-4'},
                ],
            },
        })
        res = build_device_model_v2_1(controller, dev, root_dir="")

        switch_maps = [m for m in res.mode_button_maps if m.slot.startswith('switch')]
        self.assertEqual(len(switch_maps), 4)
        slots = [m.slot for m in switch_maps]
        self.assertEqual(slots, ['switch1', 'switch2', 'switch3', 'switch4'])
        self.assertEqual(switch_maps[0].midi_coords.number, 31)
        self.assertEqual(switch_maps[2].midi_coords.number, 33)

    def test_switch_list_and_explicit_switch_raises(self):
        with self.assertRaises((ValueError, ValidationError)):
            DeviceV2.model_validate({
                'track': 'selected',
                'device': 'selected',
                'mappings': {
                    'encoder-list': [{'range': 'row-1:1-4', 'slots': '1-4'}],
                    'switch-list': [{'range': 'row-2:1-4'}],
                    'switch1': 'row-2:1',
                },
            })
