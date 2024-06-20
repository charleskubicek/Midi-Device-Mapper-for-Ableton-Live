import sys
from pathlib import Path
from typing import Optional, Union, List, Literal, Annotated

from pydantic import BaseModel, Field, model_validator, TypeAdapter, ConfigDict
from typing_extensions import Self

from ableton_control_suface_as_code.core_model import DeviceMidiMapping, MixerMidiMapping, EncoderType, \
    LayoutAxis, MidiType, DeviceWithMidi, MixerWithMidi, EncoderCoords, MidiCoords

from ableton_control_suface_as_code import nested_text as nt


class RangeV2(BaseModel):
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

    def item_at(self, index: int):
        if index < 0 or index >= len(self.as_inclusive_list()):
            raise ValueError(f"Index {index} out of range for {self.as_list()}")
        return self.as_inclusive_list()[index]


class ControlGroupV2(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range_raw: str = Field(alias='midi_range')

    @property
    def midi_range(self):
        try:
            [s, e] = self.midi_range_raw.split("-")
            return RangeV2.model_construct(from_=int(s), to=int(e))
        except ValueError as e:
            print(f"Error parsing {self.midi_range_raw}")
            exit(-1)


class ControllerV2(BaseModel):
    control_groups: List[ControlGroupV2]
    on_led_midi: int
    off_led_midi: int

    def find_group(self, row_col: int):
        for group in self.control_groups:
            print(f"group.number = {group.number} ({row_col})")
            if group.number == row_col:
                return group

        group_numbers = [group.number for group in self.control_groups]
        print(f"Didn't find group number for {row_col}, group numbers were {group_numbers}")

        return None

    def build_zero_based_midi_coords(self, coords) -> ([MidiCoords], EncoderType):
        print(f"enc_str = {coords}")
        for group in self.control_groups:
            if group.number == int(coords.row):
                res = []
                for col in coords.range_inclusive:
                    no = group.midi_range.item_at(col - 1)
                    res.append(MidiCoords.model_construct(
                        channel=group.midi_channel,
                        number=no,
                        type=group.midi_type))

                return res, group.type

        print("Didn't find any coords for {enc_str}")
        sys.exit(1)


class RowMapV2(BaseModel):
    row: Union[int, None]
    # col: int | None
    range_raw: str = Field(alias='range')
    parameters_raw: str = Field(alias='parameters')

    @property
    def range(self) -> RangeV2:
        a, b = self.range_raw.split("-")
        return RangeV2.model_construct(from_=int(a), to=int(b))

    @property
    def parameters(self) -> RangeV2:
        a, b = self.parameters_raw.split("-")
        return RangeV2.model_construct(from_=int(a), to=int(b))

    @model_validator(mode='after')
    def verify_square(self) -> Self:
        # if self.row is None and self.col is None:
        #     raise ValueError('row and col cannot both be None')
        # if self.row is not None and self.col is not None:
        #     raise ValueError('row and col cannot both be set')

        return self


## Mapping Types

class DeviceV2(BaseModel):
    type: Literal['device']
    track: str
    device: str
    ranges: list[RowMapV2]


class MixerMappingsV2(BaseModel):
    volume_raw: Optional[str] = Field(default=None, alias="volume")
    pan_raw: Optional[str] = Field(default=None, alias="pan")
    mute_raw: Optional[str] = Field(default=None, alias="mute")
    solo_raw: Optional[str] = Field(default=None, alias="solo")
    arm_raw: Optional[str] = Field(default=None, alias="arm")
    sends_raw: Optional[str] = Field(default=None, alias="sends")
    #
    # @model_validator(mode='after')
    # def verify_correct_ranges(self) -> Self:
    #     single_controllers = ['volume', 'pan', 'mute', 'solo', 'arm']
    #
    #     d = self.as_parsed_dict()
    #     for sc in single_controllers:
    #         if sc in d and '-' in d[sc]:
    #             raise ValueError(f"{sc} can't have a range value")


    def parse_coords(self, raw):
        if raw is None:
            return None

        [row_raw, col] = raw.split(":")
        row = int(row_raw.removeprefix("row_"))

        if '-' in col:
            [start, end] = col.split("-")
            return EncoderCoords.model_construct(row=row, col=int(start), row_range_end=int(end))
        else:
            return EncoderCoords.model_construct(row=row, col=int(col), row_range_end=int(col))

    def as_parsed_dict(self):
        return {key.removesuffix('_raw'): self.parse_coords(value) for key, value in self.model_dump().items() if
                value is not None}


class MixerV2(BaseModel):
    type: Literal['mixer'] = "mixer"
    track: str
    mappings: MixerMappingsV2


# Mapping = TypeAdapter(Annotated[
#                           Union[MixerV2, DeviceV2],
#                           Field(discriminator="type"),
#                       ])


class MappingsV2(BaseModel):
    controller: str
    mappings: List[Union[MixerV2, DeviceV2]]


#
# Models used for code generation
#


def build_mode_model_v2(mappings: List[Union[DeviceV2, MixerV2]], controller: ControllerV2) -> List[Union[
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
            mappings_with_midi.append(build_device_model_v2(controller, mapping))
        if mapping.type == "mixer":
            mappings_with_midi.append(build_mixer_model_v2(controller, mapping))

    return mappings_with_midi


def build_mixer_model_v2(controller, mapping: MixerV2):
    track = mapping.track
    mixer_maps = []
    for api_name, enc_coords in mapping.mappings.as_parsed_dict().items():
        coords_list, type = controller.build_zero_based_midi_coords(enc_coords)


        mixer_maps.append(MixerMidiMapping.with_multiple_args(
            midi_coords_list=coords_list,
            encoder_type=type,
            api_function=api_name,
            selected_track=True,
            tracks=None,
            encoder_coords=enc_coords))

    for m in mixer_maps:
        print("mixer: ", [(x.number, x.channel, x.type.name) for x in m.midi_coords], m.api_function, f"row:{m.encoder_coords.row}-{m.encoder_coords.row_range_end}, col:{m.encoder_coords.col}")

    return MixerWithMidi(midi_maps=mixer_maps)


def build_device_model_v2(controller, mapping):
    midi_range_mappings = []
    for rm in mapping.ranges:
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
        track=mapping.track,
        device=mapping.device,
        midi_range_maps=midi_range_mappings)


def read_mapping(mapping_path):
    try:

        def normalize_key(key, parent_keys):
            return '_'.join(key.lower().split())

        data = nt.loads(mapping_path, normalize_key=normalize_key)
        return MappingsV2.model_validate(data)
    except nt.NestedTextError as e:
        e.terminate()


def read_controller(controller_path):
    try:

        def normalize_key(key, parent_keys):
            return '_'.join(key.lower().split())

        data = nt.loads(controller_path, normalize_key=normalize_key)
        return ControllerV2.model_validate(data)
    except nt.NestedTextError as e:
        e.terminate()


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