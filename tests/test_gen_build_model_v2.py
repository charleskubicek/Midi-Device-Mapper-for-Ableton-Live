import unittest

from ableton_control_suface_as_code.core_model import LayoutAxis
from ableton_control_suface_as_code.model_v2 import build_mode_model_v2, DeviceV2, ControllerV2, RowMapV2, RangeV2, \
    ControlGroupV2, ControllerRawV2, ControlGroupPartV2


def build_control_group_part(midi_range='21-28', number=1, layout=LayoutAxis.row, row_parts='1-2'):
    return ControlGroupPartV2(
        layout=layout,
        number=number,
        type='knob',
        midi_channel=2,
        midi_type="CC",
        midi_range=midi_range,
        row_parts=row_parts
    )

def build_raw_controller_v2(groups=[build_control_group_part()]):
    return ControllerRawV2(
        on_led_midi =1,
        off_led_midi=1,
        control_groups=groups

    )