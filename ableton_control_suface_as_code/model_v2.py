import sys
from dataclasses import dataclass
from operator import itemgetter
from typing import Optional, Union, List, Literal

from pydantic import BaseModel, Field, model_validator, field_validator
from typing_extensions import Self

from ableton_control_suface_as_code import nested_text as nt
from ableton_control_suface_as_code.core_model import DeviceMidiMapping, MixerMidiMapping, EncoderType, \
    LayoutAxis, MidiType, DeviceWithMidi, MixerWithMidi, EncoderCoords, MidiCoords, TrackInfo, NamedTrack, parse_coords
from ableton_control_suface_as_code.model_device_nav import DeviceNav, DeviceNavWithMidi, build_device_nav_model_v2
from ableton_control_suface_as_code.model_track_nav import TrackNav, TrackNavWithMidi, \
 build_track_nav_model_v2


class RangeV2(BaseModel):
    from_: int = Field(alias='from')
    to: int

    @staticmethod
    def parse(value):
        [a, b] = value.split("-")
        return RangeV2.model_validate({'from': int(a), 'to': int(b)})

    @property
    def first(self):
        return self.from_

    def __len__(self):
        return len(self.as_range())

    def as_range(self):
        return range(self.from_, self.to)

    def as_inclusive_range(self):
        return range(self.from_, self.to + 1)

    def as_inclusive_zero_based_range(self):
        return range(self.from_-1, self.to)

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


class ControlGroupPartV2(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range_raw: str = Field(alias='midi_range')
    row_parts_raw:Optional[str] = Field(None, alias='row_parts')

    @property
    def row_parts(self) -> RangeV2:
        return RangeV2.parse(self.row_parts_raw)

    def row_parts_to_midi_list(self):
        return zip(self.row_parts.as_inclusive_list(), RangeV2.parse(self.midi_range_raw).as_inclusive_list())

    def midi_list(self):
        return RangeV2.parse(self.midi_range_raw).as_inclusive_list()


class ControlGroupAggregateV2:
    def __init__(self, parts: List[ControlGroupPartV2]):
        #TODO verify parts are the same row
        self.parts = self._sort_parts(parts)
        self.midi_coords = self.build_midi_coords(parts)


    @property
    def type(self):
        return self.parts[0].type

    ## assert numbers are the same
    @property
    def number(self):
        return self.parts[0].number

    def midi_item_at(self, index: int) -> MidiCoords:
        if index < 0 or index >= len(self.midi_coords):
            raise ValueError(f"Index {index} out of range for {len(self.midi_coords)}")
        return self.midi_coords[index]

    def midi_range_for(self, r:range):
        return self.midi_coords[r.start:r.stop]

    def _sort_parts(self, parts):
        if len(parts) == 1:
            return parts
        else:
            return sorted(parts, key=lambda x: x.row_parts.first)

    def build_midi_coords(self, parts:List[ControlGroupPartV2]):
        res = []
        for part in parts:
            for midi_number in part.midi_list():
                res.append(MidiCoords(
                    channel=part.midi_channel,
                    type=part.midi_type,
                    number=midi_number))

        return res


    @property
    def midi_range(self):
        try:
            s = self.parts[0].midi_range_raw.split("-")[0]
            e = self.parts[-1].midi_range_raw.split("-")[1]
            return RangeV2.model_validate({'from': int(s), 'to': int(e)})
        except ValueError as e:
            print(f"Error parsing midi range")
            raise e


class ControlGroupV2(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range_raw: str = Field(alias='midi_range')


    def to_midi_coords(self, midi_number) -> MidiCoords:
        return MidiCoords(
            channel=self.midi_channel,
            type=self.midi_type,
            number=midi_number)

    @property
    def midi_range(self):
        try:
            [s, e] = self.midi_range_raw.split("-")
            return RangeV2.model_validate({'from': int(s), 'to': int(e)})
        except ValueError as e:
            print(f"Error parsing {self.midi_range_raw}")
            exit(-1)


class ControllerRawV2(BaseModel):
    control_groups: List[ControlGroupPartV2]
    on_led_midi: int
    off_led_midi: int

from itertools import groupby

@dataclass
class ControllerV2:
    control_groups: List[ControlGroupAggregateV2]
    on_led_midi: int
    off_led_midi: int

    @staticmethod
    def build_from(c:ControllerRawV2):
        c.control_groups.sort(key=lambda x:x.number)
        control_groups = [ControlGroupAggregateV2(list(group)) for key, group in groupby(c.control_groups, lambda x:x.number)]

        return ControllerV2(control_groups, c.on_led_midi, c.off_led_midi)

    def find_group(self, row_col: int):
        for group in self.control_groups:
            print(f"group.number = {group.number} ({row_col})")
            if group.number == row_col:
                return group

        group_numbers = [group.number for group in self.control_groups]
        print(f"Didn't find group number for {row_col}, group numbers were {group_numbers}")

        return None

    def build_midi_coords(self, coords: EncoderCoords) -> ([MidiCoords], EncoderType):
        '''
        Given midi coordinate(s), return the midi values for the value/range
        :param coords:
        :return:
        '''
        print(f"enc_str = {coords}")
        for group in self.control_groups:
            if group.number == int(coords.row):
                res = []
                print(f"  Looking in range {coords.range_inclusive}")
                for col in coords.range_inclusive:
                    midi_range_index = col - 1
                    midi_coords = group.midi_item_at(midi_range_index)
                    res.append(midi_coords)

                return res, group.type

        print(f"Didn't find any coords for {coords} in {self.control_groups}")
        sys.exit(1)


class RowMapV2(BaseModel):
    row: Union[int, None]
    # col: int | None
    range_raw: str = Field(alias='range')
    parameters_raw: str = Field(alias='parameters')

    @property
    def range(self) -> RangeV2:
        return RangeV2.parse(self.range_raw)

    @property
    def parameters(self) -> RangeV2:
        return RangeV2.parse(self.parameters_raw)

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
    track_raw: str = Field(alias='track')
    device: str
    ranges: list[RowMapV2]

    @property
    def track_info(self) -> TrackInfo:
        if self.track_raw == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if self.track_raw == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            exit(1)


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

    def as_parsed_dict(self):
        return {key.removesuffix('_raw'): parse_coords(value) for key, value in self.model_dump().items() if
                value is not None}


class MixerV2(BaseModel):
    type: Literal['mixer'] = "mixer"
    track_raw: str = Field(alias='track')
    mappings: MixerMappingsV2

    # def __init__(self, track:str, mappings: MixerMappingsV2):
    #     super().__init__(track_raw=track, mappings=mappings)

    @property
    def track_info(self) -> TrackInfo:
        if self.track_raw == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if self.track_raw == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            exit(1)


# Mapping = TypeAdapter(Annotated[
#                           Union[MixerV2, DeviceV2],
#                           Field(discriminator="type"),
#                       ])


class MappingsV2(BaseModel):
    controller: str
    mappings: List[Union[MixerV2, DeviceV2, TrackNav, DeviceNav]]


#
# Models used for code generation
#


def build_mode_model_v2(mappings: List[Union[DeviceV2, MixerV2, TrackNav, DeviceNav]], controller: ControllerV2) -> (
        List)[Union[DeviceWithMidi, MixerWithMidi, TrackNavWithMidi, DeviceNavWithMidi]]:
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
        if mapping.type == "track-nav":
            mappings_with_midi.append(build_track_nav_model_v2(controller, mapping))
        if mapping.type == "device-nav":
            mappings_with_midi.append(build_device_nav_model_v2(controller, mapping))

    return mappings_with_midi


def build_mixer_model_v2(controller, mapping: MixerV2):
    mixer_maps = []
    for api_name, enc_coords in mapping.mappings.as_parsed_dict().items():
        coords_list, type = controller.build_midi_coords(enc_coords)

        mixer_maps.append(MixerMidiMapping(
            midi_coords=coords_list,
            controller_type=type,
            api_function=api_name,
            track_info=mapping.track_info,
            encoder_coords=enc_coords))

    for m in mixer_maps:
        coords_ = [(x.channel, x.channel, x.type.name) for x in m.midi_coords]
        row_info = f"row:{m.encoder_coords.row}-{m.encoder_coords.row_range_end}"
        print("mixer: ", coords_, m.api_function, row_info, f"col:{m.encoder_coords.col}")

    return MixerWithMidi(midi_maps=mixer_maps)


def build_device_model_v2(controller, mapping):
    midi_range_mappings = []
    for rm in mapping.ranges:
        group = controller.find_group(rm.row)
        assert len(rm.range) <= len(
            group.midi_range), f"rm.range of {len(rm.range)} is too long for group, max is {len(group.midi_range)} ({rm.range}) to group ({group.midi_range})"

        # Go back go the group to find the midi values. We have to switch to zero based
        # because the group is 0 based
        midis = group.midi_range_for(rm.range.as_inclusive_zero_based_range())

        for m, p in zip(midis, rm.parameters.as_inclusive_list()):
            midi_range_mappings.append(DeviceMidiMapping(
                midi_coords=m,
                parameter=p
            ))

    return DeviceWithMidi(
        track=mapping.track_info,
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
        return ControllerV2.build_from(ControllerRawV2.model_validate(data))
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
