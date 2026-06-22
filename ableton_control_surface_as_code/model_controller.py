import itertools
import sys
from dataclasses import dataclass
from enum import Enum
from itertools import groupby
from typing import Optional, List, Union

from pydantic import BaseModel, Field, model_validator

from ableton_control_surface_as_code.core_model import LayoutAxis, EncoderType, MidiType, RangeV2, MidiCoords, \
    EncoderMode, ButtonBehaviour
from ableton_control_surface_as_code.encoder_coords import EncoderCoords, EncoderRefinement
from ableton_control_surface_as_code.gen_error import GenError, ErrorCode


class ControlGroupPartV2(BaseModel):
    layout: LayoutAxis
    number: int
    type: EncoderType
    midi_channel: int
    midi_type: MidiType
    midi_range_raw: str = Field(alias='midi_range')
    row_parts_raw: Optional[str] = Field(None, alias='row_parts')
    under: Optional[int] = Field(None)
    right_of: Optional[int] = Field(None)
    rows: Optional[int] = Field(None)
    columns: Optional[int] = Field(None)
    hud: bool = Field(default=True)

    @model_validator(mode='after')
    def validate_midi_range(self):
        if self.layout == LayoutAxis.row and self.row_parts_raw is not None:
            raise ValueError(f"Row layout must not have row_parts")

        if self.layout == LayoutAxis.row_part and self.row_parts_raw is None:
            raise ValueError(f"Row-part layout must have row_parts")

        if self.layout == LayoutAxis.grid:
            if self.rows is None or self.columns is None:
                raise ValueError(
                    "Grid layout must declare both 'rows' and 'columns' "
                    "(needed to index buttons as row::col)")
            if self.row_parts_raw is not None:
                raise ValueError("Grid layout must not have row_parts")
        elif self.rows is not None or self.columns is not None:
            raise ValueError("'rows'/'columns' are only valid on a grid layout")

        return self

    @property
    def _midi_list(self):

        if RangeV2.is_valid_range(self.midi_range_raw):
            if self.midi_type.is_note():
                raise ValueError(f"Ranges of notes not supported for note types:{self.midi_range_raw}")
            else:
                [a, b] = self.midi_range_raw.split("-")
            return RangeV2.model_validate({'from': int(a), 'to': int(b)}).as_inclusive_list()
        elif self.midi_type.is_note():
            raw = self.midi_range_raw.strip()
            # A bare 'NOTE-NOTE' (no commas, not itself a note name) is a
            # chromatic range, e.g. 'C2-DS4'.
            if "," not in raw and raw not in note_values and "-" in raw:
                span = _split_note_range(raw)
                if span is None:
                    raise ValueError(f"Note range is invalid: {raw}")
                lo, hi = span
                if hi < lo:
                    raise ValueError(f"Note range must be increasing: {raw}")
                return list(range(lo, hi + 1))
            values = [v.strip() for v in raw.split(",")]
            missing = list(filter(lambda x: x not in note_values, values))
            if len(missing) > 0:
                raise ValueError(f"Note values are invalid: {missing}")
            return list(map(note_values.get, values))
        else:
            values = [v.strip() for v in self.midi_range_raw.split(",")]
            return list(map(int, values))

    def info_string(self):
        return f"midi channel: {self.midi_channel}, midi no: {self.number}, midi type:{self.midi_type.value}, parts:{self.row_parts_raw}, range:{self.midi_range_raw} type:{self.type.value}"

    def build_midi_coords(self, encoder_mode: EncoderMode) -> List[MidiCoords]:
        info = self.info_string() + f", from {self.layout.value} {self.number}"
        return [MidiCoords(
            channel=self.midi_channel,
            type=self.midi_type,
            number=midi_number,
            encoder_type=self.type,
            encoder_mode=encoder_mode,
            source_info=info + f", position {i - 1}",
            encoder_refs=list()
        ) for i, midi_number in enumerate(self._midi_list)]


class ControllerRawV2(BaseModel):
    control_groups: List[ControlGroupPartV2]
    light_colors: dict[str, int] = dict()
    encoder_mode: EncoderMode = Field(alias='encoder-mode', default=EncoderMode.Absolute)
    button_behaviour: ButtonBehaviour = Field(alias='button-behaviour', default=ButtonBehaviour.momentary)


def validate_controller_semantics(raw: ControllerRawV2, acc=None) -> None:
    """Catch out-of-spec MIDI values at generation time. When an accumulator is
    passed, append problems to it (the orchestrator raises once); otherwise
    raise immediately so standalone callers still see the error."""
    problems = []
    for g in raw.control_groups:
        where = g.info_string()
        if not (1 <= g.midi_channel <= 16):
            problems.append(
                f"{where}: MIDI channel {g.midi_channel} out of range (must be 1-16)")
        try:
            numbers = g._midi_list
        except Exception:
            numbers = []  # invalid note names etc. are reported by their own path
        bad = [n for n in numbers if not (0 <= n <= 127)]
        if bad:
            problems.append(
                f"{where}: MIDI number(s) {bad} out of range (must be 0-127)")
        if g.layout == LayoutAxis.grid and g.rows is not None and g.columns is not None:
            if g.rows * g.columns != len(numbers):
                problems.append(
                    f"{where}: grid is {g.rows}x{g.columns} = {g.rows * g.columns} "
                    f"cells but the MIDI range has {len(numbers)} control(s)")
    if not problems:
        return
    if acc is not None:
        acc.extend(problems)
    else:
        raise GenError(
            "Invalid controller:\n" + "\n".join(f"  - {p}" for p in problems),
            ErrorCode.SEMANTIC_VALIDATION)


class ControlGroup:
    def __init__(self, midi_coords, number, type, grid_row=0, grid_col=0, hud=True,
                 columns=None, rows=None):
        self.midi_coords = midi_coords
        self._number = number
        self._type = type
        self.grid_row = grid_row
        self.grid_col = grid_col
        self.hud = hud
        self.columns = columns
        self.rows = rows

    @property
    def type(self):
        return self._type

    @property
    def number(self):
        return self._number

    def midi_item_at(self, index: int) -> MidiCoords:
        if index < 0 or index >= len(self.midi_coords):
            raise ValueError(f"Index {index} out of range for {len(self.midi_coords)}")
        return self.midi_coords[index]


def flatten(nested_list): return [item for sublist in nested_list for item in sublist]


@dataclass
class ControllerV2:
    control_groups: List[ControlGroup]
    light_colors: dict[str, int]
    encoder_mode: EncoderMode
    button_behaviour: ButtonBehaviour = ButtonBehaviour.momentary

    @staticmethod
    def build_from(c: ControllerRawV2, acc=None):

        def compute_grid_positions(groups: List[ControlGroupPartV2]):
            # row_number → (grid_row, grid_col)
            positions = {}
            # representative per row number (first part encountered)
            rep = {g.number: g for g in reversed(groups)}
            remaining = set(rep.keys())
            # row 1 (or whichever has no under/right_of) is at (0,0)
            for num, g in rep.items():
                if g.under is None and g.right_of is None:
                    positions[num] = (0, 0)
                    remaining.discard(num)
                    break
            iterations = 0
            while remaining and iterations < 20:
                iterations += 1
                for num in list(remaining):
                    g = rep[num]
                    if g.under is not None and g.under in positions:
                        pr, pc = positions[g.under]
                        positions[num] = (pr + 1, pc)
                        remaining.discard(num)
                    elif g.right_of is not None and g.right_of in positions:
                        pr, pc = positions[g.right_of]
                        positions[num] = (pr, pc + 1)
                        remaining.discard(num)
            # Anything still in `remaining` that carries an under/right_of
            # reference could not be placed — a typo'd or circular row
            # reference. Origin-less leftovers (no under/right_of) are legitimate
            # extra origins and keep their (0,0) default, so don't report those.
            unresolved = []
            for num in remaining:
                g = rep[num]
                if g.under is not None:
                    kind, ref = 'under', g.under
                elif g.right_of is not None:
                    kind, ref = 'right_of', g.right_of
                else:
                    continue
                reason = ("no such row exists" if ref not in rep
                          else "that row itself was not placed "
                               "(circular reference, or it lost the origin slot to another row?)")
                unresolved.append(
                    f"row {num}: {kind}: {ref} — {reason}")
            return positions, unresolved

        def merge_groups(groups: List[ControlGroupPartV2], encoder_mode: EncoderMode, grid_pos) -> ControlGroup:
            midi_coords = flatten([g.build_midi_coords(encoder_mode) for g in groups])
            gr, gc = grid_pos
            return ControlGroup(midi_coords, groups[0].number, groups[0].type, grid_row=gr, grid_col=gc,
                                hud=groups[0].hud, columns=groups[0].columns, rows=groups[0].rows)

        c.control_groups.sort(key=lambda x: x.number)
        grid_positions, unresolved = compute_grid_positions(c.control_groups)
        if unresolved:
            if acc is not None:
                acc.extend(unresolved)
            else:
                raise GenError(
                    "Invalid controller grid layout:\n"
                    + "\n".join(f"  - {p}" for p in unresolved),
                    ErrorCode.SEMANTIC_VALIDATION)
        control_groups = [
            merge_groups(list(group), c.encoder_mode, grid_positions.get(key, (0, 0)))
            for key, group in groupby(c.control_groups, lambda x: x.number)
        ]

        return ControllerV2(control_groups, c.light_colors, c.encoder_mode, c.button_behaviour)

    def _grids(self) -> List[List[ControlGroup]]:
        """Group control groups into grids by control `type`, ordered by first
        appearance in spatial reading order (`(grid_row, grid_col)`, the same
        sort key used in hud_layout.allocate_global_layout). Each grid is a list
        of ControlGroups already in layout order. On the ec4 this yields
        grid-1 = knobs, grid-2 = buttons."""
        by_type, order = {}, []
        for g in sorted(self.control_groups, key=lambda g: (g.grid_row, g.grid_col)):
            if g.type not in by_type:
                by_type[g.type] = []
                order.append(g.type)
            by_type[g.type].append(g)
        return [by_type[t] for t in order]

    def _resolve_grid_coords(self, coords: EncoderCoords) -> ([MidiCoords], EncoderType):
        grids = self._grids()
        n = int(coords.row)
        if not (1 <= n <= len(grids)):
            raise GenError(
                f"Coordinate grid-{coords.row} refers to grid {n}, but the controller "
                f"has {len(grids)} grid(s) (valid: grid-1 to grid-{len(grids)})",
                ErrorCode.SEMANTIC_VALIDATION)
        grid = grids[n - 1]
        flat = flatten(g.midi_coords for g in grid)
        res_type = grid[0].type
        res_midi = []

        if coords.grid_row is not None:
            return self._resolve_grid_2d(coords, n, grid, flat), res_type

        for col in coords.range_inclusive:
            if col < 1 or col > len(flat):
                raise GenError(
                    f"Coordinate grid-{coords.row}:{col} is out of range — "
                    f"grid {n} has {len(flat)} item(s) (valid cols: 1-{len(flat)})",
                    ErrorCode.SEMANTIC_VALIDATION)
            res_midi.append(flat[col - 1].with_encoder_refs(coords.encoder_refs))
        return res_midi, res_type

    def _resolve_grid_2d(self, coords: EncoderCoords, n: int,
                         grid: List[ControlGroup], flat) -> [MidiCoords]:
        columns = grid[0].columns
        if columns is None:
            raise GenError(
                f"Coordinate grid-{coords.row}:{coords.grid_row}::… uses row::col "
                f"indexing, but grid {n} is not a 2D grid — add 'rows' and 'columns' "
                f"to its control group (layout: grid)",
                ErrorCode.SEMANTIC_VALIDATION)
        rows = grid[0].rows or (len(flat) // columns)
        r = coords.grid_row
        if not (1 <= r <= rows):
            raise GenError(
                f"Coordinate grid-{coords.row}:{r}::… is out of range — "
                f"grid {n} has {rows} row(s) (valid rows: 1-{rows})",
                ErrorCode.SEMANTIC_VALIDATION)
        res_midi = []
        for col in coords.range_inclusive:
            if not (1 <= col <= columns):
                raise GenError(
                    f"Coordinate grid-{coords.row}:{r}::{col} is out of range — "
                    f"grid {n} has {columns} column(s) (valid cols: 1-{columns})",
                    ErrorCode.SEMANTIC_VALIDATION)
            idx = (r - 1) * columns + (col - 1)
            res_midi.append(flat[idx].with_encoder_refs(coords.encoder_refs))
        return res_midi

    def grid_position_for(self, row_number: int):
        for g in self.control_groups:
            if g.number == row_number:
                return (g.grid_row, g.grid_col)
        return (0, 0)

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
            if coords.axis_kind == "grid":
                grid_midi, res_type = self._resolve_grid_coords(coords)
                res_midi.extend(grid_midi)
                continue
            for group in self.control_groups:
                if group.number == int(coords.row):
                    res_type = group.type

                    for col in coords.range_inclusive:
                        midi_range_index = col - 1
                        if midi_range_index < 0 or midi_range_index >= len(group.midi_coords):
                            raise GenError(
                                f"Coordinate row-{coords.row}:{col} is out of range — "
                                f"row {group.number} has {len(group.midi_coords)} item(s) (valid cols: 1-{len(group.midi_coords)})",
                                ErrorCode.SEMANTIC_VALIDATION
                            )
                        midi_coords = group.midi_item_at(midi_range_index)
                        res_midi.append(midi_coords.with_encoder_refs(coords.encoder_refs))

        if res_type is None:
            available = ", ".join(f"row-{g.number}" for g in self.control_groups)
            lo, hi = coords.range_
            range_str = f"{lo}" if lo == hi else f"{lo}-{hi}"
            raise GenError(
                f"Coordinate row-{coords.row}:{range_str} refers to row "
                f"{coords.row}, which the controller does not have (available: {available})",
                ErrorCode.SEMANTIC_VALIDATION)
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


def _split_note_range(raw):
    """Split 'C2-DS4' into (from_midi, to_midi). Note names may themselves
    contain '-' (negative octaves like 'C-2'), so pick the leftmost dash that
    yields two valid note names. Returns None if no such split exists."""
    s = raw.strip()
    for i, ch in enumerate(s):
        if ch != '-':
            continue
        left, right = s[:i], s[i + 1:]
        if left in note_values and right in note_values:
            return note_values[left], note_values[right]
    return None
