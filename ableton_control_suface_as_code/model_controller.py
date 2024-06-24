import sys
from dataclasses import dataclass
from itertools import groupby
from typing import Optional, List

from pydantic import BaseModel, Field

from ableton_control_suface_as_code.core_model import LayoutAxis, EncoderType, MidiType, RangeV2, MidiCoords, \
    EncoderCoords


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


@dataclass
class ControllerV2:
    control_groups: List[ControlGroupAggregateV2]
    on_led_midi: int
    off_led_midi: int

    @staticmethod
    def build_from(c: ControllerRawV2):
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
