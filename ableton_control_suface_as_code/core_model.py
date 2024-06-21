from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, List

from pydantic import BaseModel, Field


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
    name:Optional[NamedTrack]
    list:Optional[List[int]]

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

    @property
    def is_range(self):
        return self.row_range_end != self.col

    @property
    def range_inclusive(self):
        return range(self.col, self.row_range_end + 1)

    def list_inclusive(self):
        return list(self.range_inclusive)

    def __init__(self, row, col=None, row_range_end=None):
        super().__init__(row=row, col=col, row_range_end=row_range_end)

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

    def __init__(self, channel, number, type):
        super().__init__(channel=channel, type=type, number=number)


class DeviceMidiMapping(BaseModel):
    type: Literal['device'] = 'device'
    midi_channel: int
    midi_number: int
    midi_type: MidiType
    parameter: int

    @property
    def midi_coords(self) -> MidiCoords:
        return MidiCoords(channel=self.midi_channel, number=self.midi_number, type=self.midi_type)


    def info_string(self):
        return f"ch{self.midi_channel}_no{self.midi_number}_{self.midi_type.value}__p{self.parameter}"


#
# The data in this class has been zerobased
#
class MixerMidiMapping(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_coords:List[MidiCoords]
    controller_type: EncoderType
    api_function: str
    track_info: TrackInfo
    encoder_coords: EncoderCoords

    def encoders_debug_string(self):
        return self.encoder_coords.debug_string()

    def __init__(self,
                 midi_coords:MidiCoords,
                 encoder_type:EncoderType,
                 api_function,
                 encoder_coords:EncoderCoords,
                 track_info:TrackInfo):
        super().__init__(
            type='mixer',
            midi_coords=[midi_coords],
            controller_type=encoder_type,
            api_function=api_function,
            encoder_coords=encoder_coords,
            track_info=track_info
        )

    @classmethod
    def with_multiple_args(cls,
                 midi_coords_list:List[MidiCoords],
                 encoder_type:EncoderType,
                 api_function,
                 encoder_coords:EncoderCoords,
                 track_info:TrackInfo):
        return MixerMidiMapping.model_construct(
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
    midi_range_maps: list[DeviceMidiMapping]


class MixerWithMidi(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_maps: list[MixerMidiMapping]
