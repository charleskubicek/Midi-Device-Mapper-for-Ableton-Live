from enum import Enum
from typing import Optional, Union, List, Literal, Annotated

from pydantic import BaseModel, Field, validator, field_validator, model_validator, TypeAdapter
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Self


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
    comment: Optional[str] = Field(default=None, alias='|')

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
    comment: Optional[str] = Field(default=None, alias='|')

    def debug_string(self):
        # c3,n30,cc
        return f"ch{self.midi_channel - 1},no{self.midi_number},{self.midi_type.value}"


class ControlGroup(BaseModel):
    layout: LayoutEnum
    number: int
    type: ControlTypeEnum
    midi_channel: int
    midi_type: MidiTypeEnum
    midi_range: Range
    comment: Optional[str] = Field(default=None, alias='|')


class Controller(BaseModel):
    control_groups: list[ControlGroup]
    comment: Optional[str] = Field(default=None, alias='|')

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
    comment: Optional[str] = Field(default=None, alias='|')

    @model_validator(mode='after')
    def verify_square(self) -> Self:
        # if self.row is None and self.col is None:
        #     raise ValueError('row and col cannot both be None')
        # if self.row is not None and self.col is not None:
        #     raise ValueError('row and col cannot both be set')

        return self


class Device(BaseModel):
    type: Literal['device']
    lom: str
    range_maps: list[RowMap]
    comment: Optional[str] = Field(default=None, alias='|')


class DeviceWithMidi(BaseModel):
    device: Device
    midi_range_maps: list[MidiMapping]



class MixerMappings(BaseModel):
    volume: str
    pan: str
    mute: str
    solo: str
    sends: List[str]


class Mixer(BaseModel):
    type: Literal['mixer']
    track: str
    mappings: MixerMappings


# Mapping = TypeAdapter(Annotated[
#                           Union[Mixer, Device],
#                           Field(discriminator="type"),
#                       ])

class Mappings(BaseModel):
    controller: str
    mappings: List[Union[Mixer, Device]]
    comment: Optional[str] = Field(default=None, alias='|')


class MixerWithMidi(BaseModel):
    mixer: Mixer
    midi_range_maps: list[MidiMapping]



def build_mode_model(mappings: List[Union[Device, Mixer]], controller: Controller):
    """
    Returns a model of the mapping with midi info attached

    :param mappings:
    :param controller:
    :return:
    """

    mappings_with_midi = []

    for mapping in mappings:

        if mapping.type == "device":
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

            mappings_with_midi.append(DeviceWithMidi(device=mapping, midi_range_maps=midi_range_mappings))
        if mapping.type == "mixer":
            pass


    return mappings_with_midi


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
