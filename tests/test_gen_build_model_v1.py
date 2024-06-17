import unittest
from ableton_control_suface_as_code.model_v1 import RangeV1, ControlGroupV1, \
    ControllerV1, RowMapV1, DeviceV1, build_mode_model_v1
from ableton_control_suface_as_code.core_model import ControlTypeEnum, LayoutEnum, MidiTypeEnum


class TestBuildModeModel(unittest.TestCase):

    def test_build_mode_model(self):
        device_with_midi = build_mode_model_v1([self.build_mode_model()], self.build_controller())
        self.assertEqual(len(device_with_midi[0].midi_range_maps), 16)  # 9 parameters for each of the 2 rows

    def build_controller(self):
        self.controller = {
            'control_groups': [
                {
                    'layout': 'row',
                    'number': 1,
                    'type': 'knob',
                    'midi_channel': 2,
                    'midi_type': "CC",
                    'midi_range': {'from': 21, 'to': 28}
                },
                {
                    'layout': 'col',
                    'number': 2,
                    'type': 'button',
                    'midi_channel': 2,
                    'midi_type': "CC",
                    'midi_range': {'from': 29, 'to': 36}
                },
            ],
        }

        return ControllerV1.model_validate(self.controller)

    def build_mode_model(self):
        return DeviceV1.model_construct(
            type="device",
            lom="tracks.selected.device.selected",
            range_maps=[
                RowMapV1.model_construct(
                    row=2,
                    range=RangeV1.model_construct(from_=1, to=8),
                    parameters=RangeV1.model_construct(from_=1, to=8)
                ),
                RowMapV1.model_construct(
                    row=1,
                    range=RangeV1.model_construct(from_=1, to=8),
                    parameters=RangeV1.model_construct(from_=9, to=16)
                )
            ])


    def test_build_mode_model_empty_device(self):
        empty_device_mapping = DeviceV1.model_construct(
            type="device",
            lom="tracks.selected.device.selected",
            range_maps=[])

        device_with_midi = build_mode_model_v1([DeviceV1.model_validate(empty_device_mapping)], self.build_controller())
        self.assertEqual(len(device_with_midi[0].midi_range_maps), 0)

    # def test_build_mode_model_empty_controller(self):
    #     empty_controller = Controller.model_construct(control_groups=[])
    #
    #     device_with_midi = build_mode_model(self.build_mode_model(), empty_controller)
    #     self.assertEqual(len(device_with_midi.midi_range_maps), 0)

    def test_build_mode_model_mismatched_ranges(self):
        mismatched_device_mapping = {
            'type': 'device',
            'lom': 'tracks.selected.device.selected',
            'range_maps': [
                {
                    "row": 2,
                    "range": {'from': 1, 'to': 10},  # 10 parameters, but the controller only has 9
                    "parameters": {'from': 1, 'to': 10},
                },
            ]
        }
        with self.assertRaises(AssertionError):
            build_mode_model_v1([DeviceV1.model_validate(mismatched_device_mapping)], self.build_controller())


if __name__ == '__main__':
    unittest.main()
