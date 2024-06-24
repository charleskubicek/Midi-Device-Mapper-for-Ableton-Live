from enum import Enum
from typing import Literal, Optional, List

from pydantic import BaseModel, model_validator


class EncoderType(str, Enum):
    knob = 'knob'
    button = 'button'
    slider = 'slider'

    def is_button(self):
        return self == EncoderType.button

    def is_encoder(self):
        return self != EncoderType.button

    @classmethod
    def create_from_first_char(cls, str):
        for control_type in cls:
            if control_type.value[0] == str[0]:
                return control_type
        raise ValueError(f"No ControlTypeEnum starts with {str[0]} from {str}")


class LayoutAxis(str, Enum):
    row = 'row'
    row_part = 'row-part'
    col = 'col'


class NamedTrack(str, Enum):
    master = 'master'
    selected = 'selected'

    @property
    def is_master(self):
        return self == NamedTrack.master

    @property
    def is_selected(self):
        return self == NamedTrack.selected

    @property
    def lom_name(self):
        if self.is_master:
            return None
        return 'selected_track'

    @property
    def mixer_strip_name(self):
        if self.is_master:
            return 'master'
        return 'selected'


class TrackInfo(BaseModel):
    name: Optional[NamedTrack]
    list: Optional[List[int]]

    @classmethod
    def selected(cls):
        return cls(name=NamedTrack.selected)

    @classmethod
    def master(cls):
        return cls(name=NamedTrack.master)

    def __init__(self, name=None, list=None):
        super().__init__(name=name, list=list)

    def is_selected(self):
        return self.name is not None and self.name.is_selected

    def is_multi(self):
        return self.list is not None


class EncoderCoords(BaseModel):
    row: int
    col: int
    row_range_end: int

    @model_validator(mode='after')
    def range_is_in_bound(self) -> 'EncoderCoords':
        if self.row_range_end < self.col:
            raise ValueError('row_range_end must be greater than col')
        return self


    @property
    def is_range(self):
        return self.row_range_end != self.col

    @property
    def range_inclusive(self):
        return range(self.col, self.row_range_end + 1)

    def list_inclusive(self):
        return list(self.range_inclusive)

    @classmethod
    def from_row_col(cls, row, col):
        return cls(row=row, col=col, row_range_end=col)

    def debug_string(self):
        return f"r{self.row}c{self.col}"


class MidiType(str, Enum):
    note = 'note'
    CC = 'CC'

    def ableton_name(self):
        if self == MidiType.note:
            return 'MIDI_NOTE_TYPE'
        return 'MIDI_CC_TYPE'


class MidiCoords(BaseModel):
    channel: int
    type: MidiType
    number: int

    def ableton_channel(self):
        return self.channel - 1

    def create_button_element(self):
        return f"ConfigurableButtonElement(True, {self.type.ableton_name()}, {self.ableton_channel()}, {self.number})"

    def create_encoder_element(self):
        return f"EncoderElement({self.type.ableton_name()}, {self.ableton_channel()}, {self.number}, Live.MidiMap.MapMode.absolute)"

    # def __init__(self, channel, number, type):
    #     super().__init__(channel=channel, type=type, number=number)


class DeviceMidiMapping(BaseModel):
    type: Literal['device'] = 'device'
    midi_coords: MidiCoords
    parameter: int

    @classmethod
    def from_coords(cls, midi_channel, midi_number, midi_type, parameter):
        return cls(midi_coords=MidiCoords(channel=midi_channel, type=midi_type, number=midi_number), parameter=parameter)
    # def __init__(self, midi_channel, midi_number, midi_type, parameter):
    #     super().__init__({'midi_coords': MidiCoords(midi_channel, midi_type, midi_number), 'parameter' :parameter})

    def info_string(self):
        return f"ch{self.midi_coords.channel}_no{self.midi_coords.number}_{self.midi_coords.type.value}__p{self.parameter}"


class Direction(Enum):
    inc = 'inc'
    dec = 'dec'

class DeviceNavAction(Enum):
    left = 'left', 'self.device_nav_left()'
    right = 'right', 'self.device_nav_right()'
    first = 'first', 'self.device_nav_first()'
    last = 'last', 'self.device_nav_last()'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.template_call = args[1]
        return obj

    # def tmplate_call(self):
    #     return self.template_call

#
# The data in this class has been zerobased
#
class MixerMidiMapping(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_coords: List[MidiCoords]
    controller_type: EncoderType
    api_function: str
    track_info: TrackInfo
    encoder_coords: EncoderCoords

    def encoders_debug_string(self):
        return self.encoder_coords.debug_string()

    # def __init__(self,
    #              midi_coords: MidiCoords,
    #              encoder_type: EncoderType,
    #              api_function,
    #              encoder_coords: EncoderCoords,
    #              track_info: TrackInfo):
    #     super().__init__(
    #         # type='mixer',
    #         midi_coords=list(midi_coords),
    #         controller_type=encoder_type,
    #         api_function=api_function,
    #         encoder_coords=encoder_coords,
    #         track_info=track_info
    #     )

    @classmethod
    def with_multiple_args(cls,
                           midi_coords_list: List[MidiCoords],
                           encoder_type: EncoderType,
                           api_function,
                           encoder_coords: EncoderCoords,
                           track_info: TrackInfo):
        return MixerMidiMapping(
            midi_coords=midi_coords_list,
            controller_type=encoder_type,
            api_function=api_function,
            encoder_coords=encoder_coords,
            track_info=track_info
        )

    @property
    def midi_channel(self):
        return self.midi_coords[0].channel

    @property
    def midi_number(self):
        return self.midi_coords[0].number

    @property
    def midi_type(self):
        return self.midi_coords[0].type

    @property
    def api_control_type(self):
        if self.api_function in ['solo', 'mute', 'arm']:
            return 'button'
        elif self.api_function == 'sends':
            return 'controls'
        else:
            return 'control'

    # TDDO validate tracks is only present if selected_track is not and vv

    def info_string(self):
        return f"ch{self.midi_channel}_{self.midi_number}_{self.midi_type.value}__cds_{self.encoders_debug_string()}__api_{self.api_function}"


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_range_maps: List[DeviceMidiMapping]


class MixerWithMidi(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_maps: List[MixerMidiMapping]


def parse_coords(raw) -> EncoderCoords:
    if raw is None:
        return None

    [row_raw, col] = raw.split(":")
    row = int(row_raw.removeprefix("row_"))

    if '-' in col:
        [start, end] = col.split("-")
        return EncoderCoords(row=row, col=int(start), row_range_end=int(end))
    else:
        return EncoderCoords(row=row, col=int(col), row_range_end=int(col))
