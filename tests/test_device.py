import unittest

from pydantic import ValidationError

from ableton_control_surface_as_code.core_model import RowMapV2_1
from ableton_control_surface_as_code.model_controller import ControllerV2
from ableton_control_surface_as_code.model_device import DeviceV2, \
    build_device_model_v2_1, DeviceEncoderMappings, SwitchListEntry
from ableton_control_surface_as_code.slots import parse_continuous_slot_list
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

        switch_maps = [m for m in res.switch_maps if m.slot.startswith('switch')]
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

        switch_maps = [m for m in res.switch_maps if m.slot.startswith('switch')]
        self.assertEqual(len(switch_maps), 4)
        slots = [m.slot for m in switch_maps]
        self.assertEqual(slots, ['switch1', 'switch2', 'switch3', 'switch4'])
        self.assertEqual(switch_maps[0].midi_coords.number, 31)
        self.assertEqual(switch_maps[2].midi_coords.number, 33)

    def _ec4_button_controller(self):
        """Knobs on rows 1-4 (grid col 0), buttons on rows 5-8 (grid col 1)."""
        from ableton_control_surface_as_code.model_controller import ControlGroupPartV2
        groups = [
            ControlGroupPartV2(layout='row', number=1, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='0-3'),
            ControlGroupPartV2(layout='row', number=2, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='4-7', under=1),
            ControlGroupPartV2(layout='row', number=3, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='8-11', under=2),
            ControlGroupPartV2(layout='row', number=4, type='knob',
                               midi_channel=1, midi_type='CC', midi_range='12-15', under=3),
            ControlGroupPartV2(layout='row', number=5, type='button',
                               midi_channel=1, midi_type='CC', midi_range='40-43', right_of=1),
            ControlGroupPartV2(layout='row', number=6, type='button',
                               midi_channel=1, midi_type='CC', midi_range='44-47', under=5),
            ControlGroupPartV2(layout='row', number=7, type='button',
                               midi_channel=1, midi_type='CC', midi_range='48-51', under=6),
            ControlGroupPartV2(layout='row', number=8, type='button',
                               midi_channel=1, midi_type='CC', midi_range='52-55', under=7),
        ]
        return ControllerV2.build_from(build_raw_controller_v2(groups))

    def test_grid_switch_list_matches_multi_row_enumeration(self):
        controller = self._ec4_button_controller()

        grid_dev = DeviceV2.model_validate({
            'track': 'selected', 'device': 'selected',
            'mappings': {'switch-list': [{'range': 'grid-2:1-15'}]},
        })
        rows_dev = DeviceV2.model_validate({
            'track': 'selected', 'device': 'selected',
            'mappings': {'switch-list': [
                {'range': 'row-5:1-4'},
                {'range': 'row-6:1-4'},
                {'range': 'row-7:1-4'},
                {'range': 'row-8:1-3'},
            ]},
        })

        grid_res = build_device_model_v2_1(controller, grid_dev, root_dir="")
        rows_res = build_device_model_v2_1(controller, rows_dev, root_dir="")

        grid_switches = [m for m in grid_res.switch_maps if m.slot.startswith('switch')]
        rows_switches = [m for m in rows_res.switch_maps if m.slot.startswith('switch')]

        self.assertEqual(len(grid_switches), 15)
        self.assertEqual([m.slot for m in grid_switches], [m.slot for m in rows_switches])
        self.assertEqual([m.midi_coords.number for m in grid_switches],
                         [m.midi_coords.number for m in rows_switches])
        self.assertEqual(grid_switches[0].midi_coords.number, 40)
        self.assertEqual(grid_switches[14].midi_coords.number, 54)

    def test_slots_given_a_coordinate_raises_helpful_error(self):
        # 'slots:' wants device slot numbers (e.g. '1-16') or slot names, not a
        # controller coordinate like 'grid-1:1-16'. The old failure was a raw
        # int('grid') ValueError.
        with self.assertRaises(ValueError) as ctx:
            parse_continuous_slot_list("grid-1:1-16")
        msg = str(ctx.exception)
        self.assertIn("slot", msg.lower())
        self.assertIn("grid-1:1-16", msg)

    def test_unknown_mapping_key_raises_helpful_error(self):
        # 'parameters'/'slots' belong inside an 'encoders:' block, not directly
        # under 'mappings:'. Writing them at the mappings level used to be
        # silently dropped, leaving the encoders unmapped.
        with self.assertRaises((ValueError, ValidationError)) as ctx:
            DeviceV2.model_validate({
                'track': 'selected', 'device': 'selected',
                'mappings': {
                    'parameters': {'range': 'grid-1:1-16', 'slots': '1-16'},
                    'on-off': 'grid-2:3',
                },
            })
        msg = str(ctx.exception)
        self.assertIn('parameters', msg)
        self.assertIn('encoders', msg)

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
