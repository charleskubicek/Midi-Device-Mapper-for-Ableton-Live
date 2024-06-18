from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional, List

from pydantic import BaseModel, Field


class ControlTypeEnum(str, Enum):
    knob = 'knob'
    button = 'button'
    slider = 'slider'

    def is_button(self):
        return self == ControlTypeEnum.button

    def is_encoder(self):
        return self != ControlTypeEnum.button

    @classmethod
    def create_from_first_char(cls, str):
        for control_type in cls:
            if control_type.value[0] == str[0]:
                return control_type
        raise ValueError(f"No ControlTypeEnum starts with {str[0]} from {str}")


class LayoutEnum(str, Enum):
    row = 'row'
    col = 'col'


class EncoderCoords(BaseModel):
    row: int
    col: Optional[int]
    cols: Optional[List[int]]

    def debug_string(self):
        if self.col:
            return f"r{self.row}c{self.col}"
        return f"r{self.row}c{self.cols}"


class MidiTypeEnum(str, Enum):
    midi = 'midi'
    CC = 'CC'

    def ableton_name(self):
        if self == MidiTypeEnum.midi:
            return 'MIDI_NOTE_TYPE'
        return 'MIDI_CC_TYPE'


class MidiCoords(BaseModel):
    channel: int
    type: MidiTypeEnum
    number: int



class DeviceMidiMapping(BaseModel):
    type: Literal['device'] = 'device'
    midi_channel: int
    midi_number: int
    midi_type: MidiTypeEnum
    parameter: int
    comment: Optional[str] = Field(default=None, alias='|')

    def debug_string(self):
        return f"ch{self.midi_channel - 1},no{self.midi_number},{self.midi_type.value},p{self.parameter}"


class MixerMidiMapping(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_channel: int
    midi_number: int
    midi_type: MidiTypeEnum
    controller_type: ControlTypeEnum
    api_function: str
    selected_track: Optional[bool]
    tracks: Optional[List[str]]
    encoder_coords: EncoderCoords

    # TDDO validate tracks is only present if selected_track is not and vv

    def debug_string(self):
        return f"ch{self.midi_channel - 1}_{self.midi_number}_{self.midi_type.value}__cds_{self.encoder_coords.debug_string()}__api_{self.api_function}"


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: str
    device: str
    midi_range_maps: list[DeviceMidiMapping]


class MixerWithMidi(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_maps: list[MixerMidiMapping]
