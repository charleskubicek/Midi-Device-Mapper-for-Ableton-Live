import re
from abc import ABC
from enum import Enum
from typing import Literal, Optional, List, Union

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

    def is_note(self):
        return self == MidiType.note

    def ableton_name(self):
        if self == MidiType.note:
            return 'MIDI_NOTE_TYPE'
        return 'MIDI_CC_TYPE'


class MidiCoords(BaseModel):
    channel: int
    type: MidiType
    number: int
    encoder_type: EncoderType

    def ableton_channel(self):
        return self.channel - 1

    def create_button_element(self):
        print(f"self.type = {self.type}")
        return f"ConfigurableButtonElement(True, {self.type.ableton_name()}, {self.ableton_channel()}, {self.number})"

    def create_encoder_element(self):
        return f"EncoderElement({self.type.ableton_name()}, {self.ableton_channel()}, {self.number}, Live.MidiMap.MapMode.absolute)"

    def __init__(self, channel, number, type, encoder_type):
        super().__init__(channel=channel, type=type, number=number, encoder_type=encoder_type)

    def create_controller_element(self):
        if self.encoder_type.is_button():
            return self.create_button_element()
        else:
            return self.create_encoder_element()

    def controller_variable_name(self):
        return f"{self.encoder_type.value}_{self.info_string()}"

    def controller_listener_fn_name(self, suffix):
        return f"{self.encoder_type.value}_{self.info_string()}_{suffix}value"

    def info_string(self):
        return f"ch{self.channel}_{self.number}_{self.type.value}"

    def variable_initialisation(self):
        return f"self.{self.controller_variable_name()} = {self.create_controller_element()}"


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
    api_function: str
    track_info: TrackInfo
    encoder_coords: EncoderCoords  # For debugging

    @property
    def only_midi_coord(self) -> MidiCoords:
        if len(self.midi_coords) > 1:
            raise ValueError(f"Expected only one midi coord but got {len(self.midi_coords)}")
        return self.midi_coords[0]

    @property
    def first_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

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

    @property
    def _api_name_in_listener_code(self):
        if self.api_function == "sends":
            return "send"
        return self.api_function

    # TDDO validate tracks is only present if selected_track is not and vv

    def listener_setup_code(self, var_name=None):
        track_strip = self.track_info.name.mixer_strip_name
        api = self._api_name_in_listener_code
        var = self.first_midi_coord.controller_variable_name() if var_name is None else var_name

        return f"self.mixer.{track_strip}_strip().set_{api}_{self.api_control_type}(self.{var})"

    def listener_remove_code(self):
        track_strip = self.track_info.name.mixer_strip_name
        api = self._api_name_in_listener_code

        return f"self.mixer.{track_strip}_strip().set_{api}_{self.api_control_type}(None)"


class MixerWithMidi(BaseModel):
    type: Literal['mixer'] = 'mixer'
    midi_maps: list[MixerMidiMapping]


class ButtonProviderBaseModel(ABC, BaseModel):
    def info_string(self):
        pass

    def create_controller_element(self):
        pass

    def controller_variable_name(self):
        pass

    def controller_listener_fn_name(self, mode_name):
        pass

    def template_function_name(self):
        pass

    def only_midi_coord(self) -> MidiCoords:
        pass

    def variable_initialisation(self):
        return f"self.{self.controller_variable_name()} = {self.create_controller_element()}"


def parse_coords(raw) -> EncoderCoords | None:
    if raw is None:
        return None

    try:
        [row_raw, col] = raw.split(":")
        row = int(row_raw.removeprefix("row_"))

        if '-' in col:
            [start, end] = col.split("-")
            return EncoderCoords(row=row, col=int(start), row_range_end=int(end))
        else:
            return EncoderCoords(row=row, col=int(col), row_range_end=int(col))
    except Exception as e:
        print(f"Failed to parse '{raw}' due to {e}")
        raise e


class RangeV2(BaseModel):
    from_: int = Field(alias='from')
    to: int

    @staticmethod
    def is_valid_range(s):
        # Regular expression pattern to match 1 to 3 digits, followed by a hyphen, followed by 1 to 3 digits
        pattern = r'^\d{1,3}-\d{1,3}$'
        return bool(re.match(pattern, s))

    @staticmethod
    def parse(value):
        if '-' in value:
            [a, b] = value.split("-")
            return RangeV2.model_validate({'from': int(a), 'to': int(b)})
        # elif ',' in value:
        #     values = value.split(",")
        #     return RangeV2.model_validate({'from': int(a), 'to': int(b)})

    @property
    def first_index(self):
        return self.from_

    def __len__(self):
        return len(self._as_range())

    def as_inclusive_list(self):
        return list(self._as_inclusive_range())

    def as_inclusive_zero_based_range(self):
        return range(self.from_ - 1, self.to)

    def _as_range(self):
        return range(self.from_, self.to)

    def _as_inclusive_range(self):
        return range(self.from_, self.to + 1)


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
    #
    # @model_validator(mode='after')
    # def verify_square(self) -> Self:
    #     # if self.row is None and self.col is None:
    #     #     raise ValueError('row and col cannot both be None')
    #     # if self.row is not None and self.col is not None:
    #     #     raise ValueError('row and col cannot both be set')
    #
    #     return self
