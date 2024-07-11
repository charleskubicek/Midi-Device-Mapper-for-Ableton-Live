import itertools
import sys
from dataclasses import dataclass
from itertools import groupby
from typing import Optional, List, Union

from pydantic import BaseModel, Field, model_validator

from ableton_control_surface_as_code.core_model import LayoutAxis, EncoderType, MidiType, RangeV2, MidiCoords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords, EncoderRefinement


class ControlGroupPartV2(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range_raw: str = Field(alias='midi_range')
    row_parts_raw: Optional[str] = Field(None, alias='row_parts')

    @model_validator(mode='after')
    def validate_midi_range(self):
        if self.layout == LayoutAxis.row and self.row_parts_raw is not None:
            raise ValueError(f"Row layout must not have row_parts")

        if self.layout == LayoutAxis.row_part and self.row_parts_raw is None:
            raise ValueError(f"Row-part layout must have row_parts")

        return self

    def has_multiple_parts(self):
        return self.row_parts_raw is not None

    def is_range_a_list(self):
        return ',' in self.midi_range_raw

    @property
    def row_parts(self) -> RangeV2:
        return RangeV2.parse(self.row_parts_raw)

    @property
    def _midi_list(self):

        if RangeV2.is_valid_range(self.midi_range_raw):
            if self.midi_type.is_note():
                raise ValueError(f"Ranges of notes not supported for note types:{self.midi_range_raw}")
            else:
                [a, b] = self.midi_range_raw.split("-")
            return RangeV2.model_validate({'from': int(a), 'to': int(b)}).as_inclusive_list()
        else:
            values = [v.strip() for v in self.midi_range_raw.split(",")]
            if self.midi_type.is_note():
                missing = list(filter(lambda x: x not in note_values, values))
                if len(missing) > 0:
                    raise ValueError(f"Note values are invalid: {missing}")
                return list(map(note_values.get, values))
            else:
                return list(map(int, values))

    def info_string(self):
        return f"midi channel: {self.midi_channel}, midi no: {self.number}, midi type:{self.midi_type.value}, parts:{self.row_parts_raw}, range:{self.midi_range_raw} type:{self.type.value}"

    def build_midi_coords(self):
        info = self.info_string() + f", from {self.layout.value} {self.number}"
        return [MidiCoords(
            channel=self.midi_channel,
            type=self.midi_type,
            number=midi_number,
            encoder_type=self.type,
            source_info=info + f", position {i-1}",
            encoder_refs=list()
        ) for i, midi_number in enumerate(self._midi_list)]


class ControlGroupAggregateV2:
    def __init__(self, parts: List[ControlGroupPartV2]):
        # TODO verify parts are the same row
        # TODO verify parts haven't been used with range arrays
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

    def midi_range_for(self, r: range):
        return self.midi_coords[r.start:r.stop]

    def _sort_parts(self, parts):
        if len(parts) == 1:
            return parts
        else:
            return sorted(parts, key=lambda x: x.row_parts.first_index)

    def build_midi_coords(self, parts: List[ControlGroupPartV2]) -> List[MidiCoords]:
        list_of_lists = [part.build_midi_coords() for part in parts]
        return list(itertools.chain.from_iterable(list_of_lists))


class ControlGroupV2(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range_raw: str = Field(alias='midi_range')

    # TODO not used?
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
    light_colors: dict[str, int]


@dataclass
class ControllerV2:
    control_groups: List[ControlGroupAggregateV2]
    light_colors: dict[str, int]

    @staticmethod
    def build_from(c: ControllerRawV2):
        c.control_groups.sort(key=lambda x: x.number)
        control_groups = [ControlGroupAggregateV2(list(group)) for key, group in
                          groupby(c.control_groups, lambda x: x.number)]

        return ControllerV2(control_groups, c.light_colors)

    def find_group(self, row_col: int):
        for group in self.control_groups:
            print(f"group.number = {group.number} ({row_col})")
            if group.number == row_col:
                return group

        group_numbers = [group.number for group in self.control_groups]
        print(f"Didn't find group number for {row_col}, group numbers were {group_numbers}")

        return None

    def light_color_for(self, name: str) -> Optional[int]:
        if name is None:
            return None
        if name not in self.light_colors:
            raise ValueError(f"Light color {name} not found in {self.light_colors}")
        return self.light_colors[name]

    def build_midi_coords(self, coords: Union[EncoderCoords, List[EncoderCoords]]) -> ([MidiCoords], EncoderType):
        '''
        Given midi coordinate(s), return the midi values for the value/range
        :param coords:
        :return:
        '''

        encoder_coors_list = [coords] if isinstance(coords, EncoderCoords) else coords
        res_midi = []
        res_type = None

        for coords in encoder_coors_list:
            for group in self.control_groups:
                if group.number == int(coords.row):
                    for col in coords.range_inclusive:
                        midi_range_index = col - 1
                        midi_coords = group.midi_item_at(midi_range_index)
                        res_midi.append(midi_coords.with_encoder_refs(coords.encoder_refs))
                        res_type = group.type

        if res_type is None:
            print(f"Didn't find any coords for {coords} in {self.control_groups}")
            sys.exit(1)
        else:
            return res_midi, res_type


PITCH_DICTIONARY_C3 = {0: "C-2", 1: "CS-2", 2: "D-2", 3: "DS-2", 4: "E-2", 5: "F-2", 6: "FS-2", 7: "G-2", 8: "GS-2",
                       9: "A-2", 10: "AS-2", 11: "B-2", 12: "C-1", 13: "CS-1", 14: "D-1", 15: "DS-1", 16: "E-1",
                       17: "F-1", 18: "FS-1", 19: "G-1", 20: "GS-1", 21: "A-1", 22: "AS-1", 23: "B-1", 24: "C0",
                       25: "CS0", 26: "D0", 27: "DS0", 28: "E0", 29: "F0", 30: "FS0", 31: "G0", 32: "GS0", 33: "A0",
                       34: "AS0", 35: "B0", 36: "C1", 37: "CS1", 38: "D1", 39: "DS1", 40: "E1", 41: "F1", 42: "FS1",
                       43: "G1", 44: "GS1", 45: "A1", 46: "AS1", 47: "B1", 48: "C2", 49: "CS2", 50: "D2", 51: "DS2",
                       52: "E2", 53: "F2", 54: "FS2", 55: "G2", 56: "GS2", 57: "A2", 58: "AS2", 59: "B2", 60: "C3",
                       61: "CS3", 62: "D3", 63: "DS3", 64: "E3", 65: "F3", 66: "FS3", 67: "G3", 68: "GS3", 69: "A3",
                       70: "AS3", 71: "B3", 72: "C4", 73: "CS4", 74: "D4", 75: "DS4", 76: "E4", 77: "F4", 78: "FS4",
                       79: "G4", 80: "GS4", 81: "A4", 82: "AS4", 83: "B4", 84: "C5", 85: "CS5", 86: "D5", 87: "DS5",
                       88: "E5", 89: "F5", 90: "FS5", 91: "G5", 92: "GS5", 93: "A5", 94: "AS5", 95: "B5", 96: "C6",
                       97: "CS6", 98: "D6", 99: "DS6", 100: "E6", 101: "F6", 102: "FS6", 103: "G6", 104: "GS6",
                       105: "A6", 106: "AS6", 107: "B6", 108: "C7", 109: "CS7", 110: "D7", 111: "DS7", 112: "E7",
                       113: "F7", 114: "FS7", 115: "G7", 116: "GS7", 117: "A7", 118: "AS7", 119: "B7", 120: "C8",
                       121: "CS8", 122: "D8", 123: "DS8", 124: "E8", 125: "F8", 126: "FS8", 127: "G8"}

note_values = {v: k for k, v in PITCH_DICTIONARY_C3.items()}
