import sys
from typing import Optional, Union, List, Literal, Annotated

from pydantic import BaseModel, Field, model_validator, TypeAdapter
from typing_extensions import Self

from ableton_control_suface_as_code.core_model import DeviceMidiMapping, MixerMidiMapping, EncoderType, \
    LayoutAxis, MidiType, DeviceWithMidi, MixerWithMidi, MidiCoords


class RangeV1(BaseModel):
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

    def item_at(self, index: int):
        if index < 0 or index >= len(self.as_inclusive_list()):
            raise ValueError(f"Index {index} out of range for {self.as_list()}")
        return self.as_inclusive_list()[index]


class ControlGroupV1(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range: RangeV1
    comment: Optional[str] = Field(default=None, alias='|')


class ControllerV1(BaseModel):
    control_groups: list[ControlGroupV1]
    comment: Optional[str] = Field(default=None, alias='|')

    def find_group(self, row_col: int):
        for group in self.control_groups:
            # print(f"group.number = {group.number} ({row_col})")
            if group.number == row_col:
                return group

        group_numbers = [group.number for group in self.control_groups]
        print(f"Didn't find group number for {row_col}, group numbers were {group_numbers}")

        return None

    def find_from_coords(self, enc_str) -> (MidiCoords, EncoderType):
        print(f"enc_str = {enc_str}")
        row, col = enc_str[1:].split("-")
        for group in self.control_groups:
            if group.number == int(row):
                no = group.midi_range.item_at(int(col) - 1)
                return (MidiCoords(
                    channel=group.midi_channel,
                    number=no,
                    type=group.midi_type),
                        group.type)

        print("Didn't find any coords for {enc_str}")
        sys.exit(1)


class RowMapV1(BaseModel):
    row: int | None
    # col: int | None
    range: RangeV1
    parameters: RangeV1
    comment: Optional[str] = Field(default=None, alias='|')

    @model_validator(mode='after')
    def verify_square(self) -> Self:
        # if self.row is None and self.col is None:
        #     raise ValueError('row and col cannot both be None')
        # if self.row is not None and self.col is not None:
        #     raise ValueError('row and col cannot both be set')

        return self


## Mapping Types

class DeviceV1(BaseModel):
    type: Literal['device']
    lom: str
    range_maps: list[RowMapV1]
    comment: Optional[str] = Field(default=None, alias='|')


class MixerMappingsV1(BaseModel):
    volume: Optional[str] = Field(default=None)
    pan: Optional[str] = Field(default=None)
    mute: Optional[str] = Field(default=None)
    solo: Optional[str] = Field(default=None)
    arm: Optional[str] = Field(default=None)
    sends: Optional[List[str]] = Field(default=None)

    # validate mute/solo/arm are buttons and sends/pan/vol are knobs/sliders


class MixerV1(BaseModel):
    type: Literal['mixer'] = 'mixer'
    track: str
    mappings: MixerMappingsV1


Mapping = TypeAdapter(Annotated[
                          Union[MixerV1, DeviceV1],
                          Field(discriminator="type"),
                      ])


class MappingsV1(BaseModel):
    controller: str
    mappings: List[Union[MixerV1, DeviceV1]]
    comment: Optional[str] = Field(default=None, alias='|')


#
# Models used for code generation
#


def build_mode_model_v1(mappings: List[Union[DeviceV1, MixerV1]], controller: ControllerV1) -> List[Union[
    DeviceWithMidi, MixerWithMidi]]:
    """
    Returns a model of the mapping with midi info attached

    :param mappings:
    :param controller:
    :return:
    """

    mappings_with_midi = []

    for mapping in mappings:

        if mapping.type == "device":
            mappings_with_midi.append(build_device_model(controller, mapping))
        if mapping.type == "mixer":
            mappings_with_midi.append(build_mixer_model(controller, mapping))

    return mappings_with_midi


def build_mixer_model(controller, mapping: MixerV1):
    track = mapping.track
    mixer_maps = []
    for api_name, enc in mapping.mappings.dict().items():
        if enc is None:
            continue
        elif api_name == 'sends':
            continue
        else:
            coords, type = controller.find_from_coords(enc)
            mixer_maps.append(MixerMidiMapping(
                midi_channel=coords.channel,
                midi_number=coords.number,
                midi_type=coords.type,
                controller_type=type,
                api_function=api_name,
                selected_track=True,
                tracks=None,
                encoder_coords=enc
            ))

    return MixerWithMidi(midi_maps=mixer_maps)


def build_device_model(controller, mapping):
    midi_range_mappings = []
    for rm in mapping.range_maps:
        group = controller.find_group(rm.row)
        assert len(rm.range) <= len(
            group.midi_range), f"rm.range of {len(rm.range)} is too long for group, max is {len(group.midi_range)} ({rm.range}) to group ({group.midi_range})"
        group_midi_list = group.midi_range.as_inclusive_range()
        print(f"group_midi_list = {group_midi_list}")

        for device_range_index in rm.range.as_inclusive_range():
            print(f"device_range_index = {device_range_index}")
            midi_range_mappings.append(DeviceMidiMapping(
                midi_channel=group.midi_channel,
                midi_number=group_midi_list[device_range_index - 1],
                midi_type=group.midi_type,
                parameter=rm.parameters.as_inclusive_list()[device_range_index - 1]
            ))

    return DeviceWithMidi(
        lom=mapping.lom,
        midi_range_maps=midi_range_mappings)


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
