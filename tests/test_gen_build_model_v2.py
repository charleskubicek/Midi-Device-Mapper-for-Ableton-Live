import unittest

from ableton_control_suface_as_code.model_v2 import build_mode_model_v2, DeviceV2, ControllerV2, RowMapV2, RangeV2, \
    ControlGroupV2


class TestBuildModeModelV2(unittest.TestCase):

    # def test_build_mode_model(self):
    #     device_with_midi = build_mode_model_v2([self.build_mode_model_v2()], self.build_controller())
    #     self.assertEqual(len(device_with_midi[0].midi_range_maps), 16)  # 9 parameters for each of the 2 rows

    def build_controller_v2(self):
        return ControllerV2.model_construct(
            on_led_midi =1,
            off_led_midi=1,
            control_groups=[ControlGroupV2.model_construct(
                layout='row',
                number=1,
                type='knob',
                midi_channel=int,
                midi_type="CC",
                midi_range='21-28'
            )],

        )
        #
        # self.controller = {
        #     'control_groups': [
        #         {
        #             'layout': 'row',
        #             'number': 1,
        #             'type': 'knob',
        #             'midi_channel': 2,
        #             'midi_type': "CC",
        #             'midi_range': {'from': 21, 'to': 28}
        #         },
        #         {
        #             'layout': 'col',
        #             'number': 2,
        #             'type': 'button',
        #             'midi_channel': 2,
        #             'midi_type': "CC",
        #             'midi_range': {'from': 29, 'to': 36}
        #         },
        #     ],
        # }

        # return ControllerV2.model_validate(self.controller)

    def build_mode_model_v2(self):
        return DeviceV2.model_construct(
            type="device",
            device='selected',
            track='selected',
            range_maps=[
                RowMapV2.model_construct(
                    row=2,
                    range=RangeV2.model_construct(from_=1, to=8),
                    parameters=RangeV2.model_construct(from_=1, to=8)
                ),
                RowMapV2.model_construct(
                    row=1,
                    range=RangeV2.model_construct(from_=1, to=8),
                    parameters=RangeV2.model_construct(from_=9, to=16)
                )
            ])


    # def test_build_mode_model_empty_device(self):
    #     empty_device_mapping = DeviceV2.model_construct(
    #         type="device",
    #         device='selected',
    #         track='selected',
    #         range_maps=[])
    #
    #     device_with_midi = build_mode_model_v2([DeviceV2.model_validate(empty_device_mapping)], self.build_controller())
    #     self.assertEqual(len(device_with_midi[0].midi_range_maps), 0)

    # def test_build_mode_model_empty_controller(self):
    #     empty_controller = Controller.model_construct(control_groups=[])
    #
    #     device_with_midi = build_mode_model(self.build_mode_model(), empty_controller)
    #     self.assertEqual(len(device_with_midi.midi_range_maps), 0)

    def test_build_mode_model_mismatched_ranges(self):
        mismatched_device_mapping = {
            'type': 'device',
            'device': 'selected',
            'track': 'selected',
            'ranges': [
                {
                    "row": 1,
                    "range": "1-10",  # 10 parameters, but the controller only has 8
                    "parameters": "1-10",
                },
            ]
        }
        with self.assertRaises(AssertionError):
            device = DeviceV2.model_validate(mismatched_device_mapping)
            build_mode_model_v2(
                [device],
                self.build_controller_v2())


if __name__ == '__main__':
    unittest.main()
