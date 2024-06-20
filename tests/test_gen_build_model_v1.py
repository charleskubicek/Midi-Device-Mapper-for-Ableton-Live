import unittest

from ableton_control_suface_as_code.model_v1 import RangeV1, ControllerV1, RowMapV1, DeviceV1, build_mode_model_v1


class TestBuildModeModel(unittest.TestCase):

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
