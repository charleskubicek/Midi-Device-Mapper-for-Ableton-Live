import keyword
import re
from abc import ABC
from enum import Enum
from typing import Literal, Optional, List

from pydantic import BaseModel, Field

from .encoder_coords import EncoderCoords, EncoderRefinement, parse, parse_multiple

def make_valid_identifier(name):
    # Step 1: Replace invalid characters with underscores
    valid_chars = []
    for char in name:
        if char.isalnum() or char == '_':
            valid_chars.append(char)
        else:
            valid_chars.append('_')

    # Step 2: Ensure the identifier does not start with a digit
    if valid_chars[0].isdigit():
        valid_chars.insert(0, '_')

    # Create the valid identifier string
    identifier = ''.join(valid_chars)

    # Step 3: Ensure the identifier is not a reserved keyword
    if keyword.iskeyword(identifier):
        identifier = f'{identifier}_'

    return identifier

class EncoderMode(str, Enum):
    Absolute = 'absolute'
    Relative = 'relative'

    @property
    def ableton_midi_map_mode(self):
        if self == EncoderMode.Absolute:
            return 'absolute'
        return 'relative_smooth_two_compliment'


class EncoderType(str, Enum):
    knob = 'knob'
    button = 'button'
    slider = 'slider'

    def is_button(self):
        return self == EncoderType.button

    def is_encoder(self):
        return self != EncoderType.button


class LayoutAxis(str, Enum):
    row = 'row'
    row_part = 'row-part'
    col = 'col'


class NamedTrack(str, Enum):
    master = 'master'
    selected = 'selected'

    @property
    def mixer_strip_name(self):
        if self == NamedTrack.master:
            return 'master'
        return 'selected'


class TrackInfo(BaseModel):
    name: Optional[NamedTrack] = None

    @staticmethod
    def selected():
        return TrackInfo(name=NamedTrack.selected)

    @staticmethod
    def master():
        return TrackInfo(name=NamedTrack.master)

    @staticmethod
    def parse_track(value):
        if value == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if value == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            raise ValueError(f"Invalid track value: '{value}'")


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
    encoder_mode: EncoderMode
    source_info: Optional[str] = None
    encoder_refs: List[EncoderRefinement] = []

    def with_encoder_refs(self, encoder_refs=None):
        return MidiCoords(channel=self.channel, type=self.type, number=self.number, encoder_type=self.encoder_type,
                          encoder_mode=self.encoder_mode, source_info=self.source_info, encoder_refs=encoder_refs)

    @property
    def ch_num(self):
        return f"{self.channel}_{self.number}"

    def ableton_channel(self):
        return self.channel - 1

    def create_button_element(self):
        return f"ConfigurableButtonElement(True, {self.type.ableton_name()}, {self.ableton_channel()}, {self.number})"

    def create_encoder_element(self):
        return f"EncoderElement({self.type.ableton_name()}, {self.ableton_channel()}, {self.number}, Live.MidiMap.MapMode.{self.encoder_mode.ableton_midi_map_mode})"

    def create_controller_element(self):
        if self.encoder_type.is_button():
            return self.create_button_element()
        else:
            return self.create_encoder_element()

    def controller_variable_name(self):
        return f"{self.encoder_type.value}_{self.info_string()}"

    def controller_listener_fn_name(self, suffix):
        return make_valid_identifier(f"{self.encoder_type.value}_{self.info_string()}_{suffix}value")

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
    first_last = 'first-last', 'self.device_nav_first_last()'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        obj.template_call = args[1]
        return obj


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

    def short_info_string(self):
        return f"mix {self.api_function[:10]}"

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


# TODO bring some implementations up
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


def parse_coords(raw) -> EncoderCoords:
    try:
        return parse(raw)
    except Exception as e:
        print(f"Failed to parse '{raw}' due to {e}")
        raise e


def parse_multiple_coords(raw) -> List[EncoderCoords]:
    try:
        return parse_multiple(raw)
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
        else:
            return RangeV2.model_validate({'from': int(value), 'to': int(value)})

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


class RowMapV2_1(BaseModel):
    range_raw: str = Field(alias='range')
    parameters_raw: str = Field(alias='parameters')

    @property
    def multi_encoder_coords(self) -> list[EncoderCoords]:
        return parse_multiple_coords(self.range_raw)

    @property
    def parameters(self) -> RangeV2:
        return RangeV2.parse(self.parameters_raw)
