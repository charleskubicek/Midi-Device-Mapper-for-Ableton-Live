from ableton_control_suface_as_code.core_model import LayoutAxis
from ableton_control_suface_as_code.model_controller import ControlGroupPartV2, ControllerRawV2


def build_control_group(midi_range='21-28', number=1, layout=LayoutAxis.row, midi_type='CC'):
    return ControlGroupPartV2(
        layout=layout,
        number=number,
        type='knob',
        midi_channel=2,
        midi_type=midi_type,
        midi_range=midi_range,
        row_parts=None
    )

def build_control_group_part(midi_range='21-28', number=1, layout=LayoutAxis.row_part, row_parts='1-2'):
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
        light_colors={},
        control_groups=groups

    )