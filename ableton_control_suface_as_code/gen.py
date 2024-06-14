from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from string import Template
from typing import TypedDict

from pydantic import BaseModel, Field, validator, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Self
import ast

class ControlTypeEnum(str, Enum):
    knob = 'knob'
    button = 'button'
    slider = 'slider'


class LayoutEnum(str, Enum):
    row = 'row'
    col = 'col'


class MidiTypeEnum(str, Enum):
    midi = 'midi'
    CC = 'CC'

    def ableton_name(self):
        if self == MidiTypeEnum.midi:
            return 'MIDI_NOTE_TYPE'
        return 'MIDI_CC_TYPE'


class Range(BaseModel):
    from_: int = Field(alias='from')
    to: int

    def __len__(self):
        return len(self.as_range())

    def as_range(self):
        return range(self.from_, self.to)

    def as_inclusive_range(self):
        return range(self.from_, self.to + 1)

    def as_list(self):
        return list(self.as_range())

    def as_inclusive_list(self):
        return list(self.as_inclusive_range())

    def is_present(self, value: int):
        return value in range(1, len(self.as_range()) + 1)


class MidiMapping(BaseModel):
    midi_channel: int
    midi_number: int
    midi_type: MidiTypeEnum
    parameter: int


class ControlGroup(BaseModel):
    layout: LayoutEnum
    number: int
    type: ControlTypeEnum
    midi_channel: int
    midi_type: MidiTypeEnum
    midi_range: Range


class Controller(BaseModel):
    control_groups: list[ControlGroup]

    def find_group(self, row_col: int):
        for group in self.control_groups:
            # print(f"group.number = {group.number} ({row_col})")
            if group.number == row_col:
                return group

        group_numbers = [group.number for group in self.control_groups]
        print(f"Didn't find group number for {row_col}, group numbers were {group_numbers}")

        return None


class RowMap(BaseModel):
    row: int | None
    # col: int | None
    range: Range
    parameters: Range

    @model_validator(mode='after')
    def verify_square(self) -> Self:
        # if self.row is None and self.col is None:
        #     raise ValueError('row and col cannot both be None')
        # if self.row is not None and self.col is not None:
        #     raise ValueError('row and col cannot both be set')

        return self


class Device(BaseModel):
    type: str
    lom: str
    range_maps: list[RowMap]


class DeviceWithMidi(BaseModel):
    device: Device
    midi_range_maps: list[MidiMapping]


controller = {
    'on_led_midi': '77',
    'off_led_midi': '78',
    'control_groups': [
        {'layout': 'row',
         'number': 1,
         'type': 'knob',
         'midi_channel': 2,
         'midi_type': "CC",
         'midi_range': {'from': 21, 'to': 28}
         },
        {'layout': 'col',
         'number': 2,
         'type': 'button',
         'midi_channel': 2,
         'midi_type': "CC",
         'midi_range': {'from': 29, 'to': 37}
         },
        {'layout': 'col',
         'number': 3,
         'type': 'button',
         'midi_channel': 2,
         'midi_type': "CC",
         'midi_range': {'from': 38, 'to': 45}
         }
    ],
    'toggles': [
        'r2-4'
    ]
}
mode_mappings = {
    'mode_selector': 'r1-1',
    'shift': True,
    'modes': [
        {
            'name': 'device',
            'color': 'red',
            'mappings': []
        }
    ]
}
test_mappings = [
    {
        'type': 'mixer',
        'track': 'selected',
        'mappings': {
            'volume': "r2-3",
            'pan': "r2-4",
            'sends': [
                {'1': "r2-4"},
                {'2': "r3-4"},
                {'3': "r2-5"},
                {'4': "r3-5"},
            ]
        }
    },
    {
        'type': 'transport',
        'mappings': {
            'play/stop': "r2-3",
            'pan': "r2-4",
        }
    },
    {
        'type': 'function',
        'controller': "r2-3",
        'function': 'functions.volume',
        'value_mapper': {
            'max': 30,
            'min': 12
        }
    },
    {
        'type': 'nav-device',
        'left': "r2-3",
        'right': "r2-4"
    },
    {
        'type': 'nav-track',
        'left': "r2-3",
        'right': "r2-4"
    },
    {
        'type': 'lom',
        'controller': "r2-3",
        'function': 'track.master.device.utility',
        'value_mapper': {
            'max': 30,
            'min': 12
        }
    },
    {
        'type': 'device',
        'lom': 'tracks.master.device.Mono',
        'controller': 'r5-1',
        'parameter': 0,
        'toggle': False
    },
    {
        'type': 'device',
        'lom': 'tracks.master.device.#1',
        'controller': 'r5-1',
        'parameter': 0,
        'toggle': True
    }
]

device_mapping = {
    'type': 'device',
    'lom': 'tracks.selected.device.selected',
    'range_maps': [
        {
            "row": 2,
            "range": {'from': 1, 'to': 8},  # inclusive
            "parameters": {'from': 1, 'to': 8},
        },
        {
            "row": 3,
            "range": {'from': 1, 'to': 8},
            "parameters": {'from': 9, 'to': 16},
        }
    ]
}


def build_mode_model(mapping: Device, controller: Controller):
    """
    Returns a model of the mapping with midi info attached

    :param mapping:
    :param controller:
    :return:
    """

    midi_range_mappings = []

    for rm in mapping.range_maps:
        group = controller.find_group(rm.row)
        assert len(rm.range) <= len(
            group.midi_range), f"rm.range of {len(rm.range)} is too long for group, max is {len(group.midi_range)} ({rm.range}) to group ({group.midi_range})"
        group_midi_list = group.midi_range.as_inclusive_range()
        print(f"group_midi_list = {group_midi_list}")

        for device_range_index in rm.range.as_inclusive_range():
            print(f"device_range_index = {device_range_index}")
            midi_range_mappings.append(MidiMapping(
                midi_channel=group.midi_channel,
                midi_number=group_midi_list[device_range_index - 1],
                midi_type=group.midi_type,
                parameter=rm.parameters.as_inclusive_list()[device_range_index - 1]
            ))

    return DeviceWithMidi(device=mapping, midi_range_maps=midi_range_mappings)


@dataclass
class EncoderCode:
    creation: [str]
    listener_fns: [str]
    setup_listeners: [str]
    remove_listeners: [str]


@dataclass
class Vars:
    surface_name: str
    class_name_snake: str
    class_name_camel: str
    encoder_code: EncoderCode


def generate_listener_action(n, parameter, lom):
    return Template("""
def encoder_${n}_value(self, value):
    selected_device = $lom
    if selected_device is None:
        return

    self.log_message(f"encoder_${n}_value selected_device = {selected_device.name}, value is {value}")
    selected_device = self.manager.song().view.selected_track.view.selected_device

    if len(selected_device.parameters) < $parameter:
        self.log_message(f"${parameter} too large, max is {len(selected_device.parameters)}")
        return

    selected_device.parameters[$parameter].value = value    
    """).substitute(n=n, parameter=parameter, lom=lom)


def encoder_template(device_with_midi: DeviceWithMidi):
    encoder_count = 0

    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    lom = build_live_api_lookup_from_lom(device_with_midi.device.lom)

    for g in device_with_midi.midi_range_maps:
        creation.append(
            f"self.encoder_{encoder_count} = EncoderElement({g.midi_type}, {g.midi_channel}, {g.midi_number}, Live.MidiMap.MapMode.relative_binary_offset)")
        setup_listeners.append(f"self.encoder_{encoder_count}.add_value_listener(self.encoder_{encoder_count}_value)")
        remove_listeners.append(
            f"self.encoder_{encoder_count}.remove_value_listener(self.encoder_{encoder_count}_value)")
        listener_fns.append(generate_listener_action(g.midi_number, g.parameter, lom))
        encoder_count += 1

    return EncoderCode(
        creation, listener_fns, setup_listeners, remove_listeners
    )


def function_body_code_block(lines: [str]):
    tab_block = "    "
    return f"\n{tab_block}{tab_block}".join(lines) + "\n"


def is_valid_python(code):
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True

def build_live_api_lookup_from_lom(lom):
    """"
        tracks.selected.device.selected
        tracks.1.device.1.


        self.manager.song().view.tracks[0].view.devices[0]
        self.manager.song().view.selected_track.view.selected_device
    """

    [_, track, _, device] = lom.split(".")

    if track.isnumeric():
        track_st = f"tracks[{track}]"
    elif track == 'selected':
        track_st = 'selected_track'
    else:
        print(f"can't parse track: {track}")
        exit(1)

    if device.isnumeric():
        device_st = f"devices[{device}]"
    elif device == 'selected':
        device_st = 'selected_device'
    else:
        print(f"can't parse device: {device}")
        exit(1)

    return f"self.manager.song().view.{track_st}.view.{device_st}"

def function_code_block(lines: [str]):
    return f"\n".join(lines) + "\n"


def gen(template_path: Path, target: Path, vars: dict):
    root_dir = Path(target, vars['surface_name'])
    root_dir.mkdir(exist_ok=True)

    device_with_midi = build_mode_model(Device.model_validate(device_mapping), Controller.model_validate(controller))
    encoder_code = encoder_template(device_with_midi)
    vars['encoder_code_creation'] = function_body_code_block(encoder_code.creation)
    vars['encoder_code_remove_listeners'] = function_body_code_block(encoder_code.remove_listeners)
    vars['encoder_code_setup_listeners'] = function_body_code_block(encoder_code.setup_listeners)
    vars['encoder_code_listener_fns'] = function_code_block(encoder_code.listener_fns)

    template_file(root_dir, template_path, vars, "__init__.py", "__init__.py")
    template_file(root_dir, template_path, vars, f'modules/class_name_snake.py',
                  f"modules/{vars['class_name_snake']}.py", verify_python=True)
    template_file(root_dir, template_path, vars, 'surface_name.py', f"{vars['surface_name']}.py")


def template_file(root_dir, template_path, vars: dict, source_file_name, target_file_name, verify_python=False):
    target_file = root_dir / target_file_name
    target_file.parent.mkdir(exist_ok=True)
    new_text = Template((template_path / 'surface_name' / source_file_name).read_text()).substitute(
        vars)

    if verify_python:
        if not is_valid_python(new_text):
            print(f"Code failed validation for file {target_file}")
        else:
            print("Code passed validation")

    target_file.write_text(new_text)


if __name__ == '__main__':
    surface_name = 'ck_test_surface'
    target_dir = Path('out')
    # (target_dir / 'ck_test_surface').rmdir()
    vars = {
        'surface_name': 'surface_name',
        'class_name_snake': 'control_mappings',
        'class_name_camel': 'ControlMappings'
    }

    gen(Path(f'templates'), target_dir, vars)
