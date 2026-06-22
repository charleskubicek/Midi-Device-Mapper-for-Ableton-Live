from abc import ABC
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from lark import Lark
from pydantic import BaseModel
from lark import Transformer


class EncoderRefinement(ABC, BaseModel):
    def name(self) -> str:
        pass

    def decorator(self, next):
        pass


class Toggle(EncoderRefinement, BaseModel):
    def name(self): return "toggle"

    def decorator(self, next):
        pass

    @staticmethod
    def instance():
        return Toggle()


class Momentary(EncoderRefinement, BaseModel):
    def name(self): return "momentary"

    def decorator(self, next):
        pass

    @staticmethod
    def instance():
        return Momentary()


class Mode(EncoderRefinement, BaseModel):
    def name(self): return "mode"

    def decorator(self, next):
        pass

    @staticmethod
    def instance():
        return Mode()



class MapModeAbsolute(EncoderRefinement, BaseModel):
    def name(self): return "map_mode_absolute"

    # def decorator(self, next):
    #     pass

    @staticmethod
    def instance():
        return MapModeAbsolute()


@dataclass
class EncoderRefinements:
    refs: List[EncoderRefinement]

    def has_toggle(self):
        return any(ref.name() == "toggle" for ref in self.refs)

    def has_momentary(self):
        return any(ref.name() == "momentary" for ref in self.refs)

    def has_map_mode_absolute(self):
        return any(ref.name() == "map_mode_absolute" for ref in self.refs)


class EncoderCoords(BaseModel):
    row: int
    range_: Tuple[int, int]
    axis_kind: str = "row"
    grid_row: Optional[int] = None
    encoder_refs: List[EncoderRefinement] = field(default_factory=list)

    @property
    def range_inclusive(self):
        return range(self.range_[0], self.range_[1] + 1)


grammar = '''
    multi : coords_list+ refinements
    single : coords_list refinements
    
    row : "row"
    col : "col"
    grid : "grid"
    axis : row | col | grid
    axis_no : NUMBER
    range: NUMBER | (NUMBER "-" NUMBER)
    grid_cell: NUMBER "::" range
    coords: axis "-" axis_no ":" (grid_cell | range)
    coords_list: coords  ("," coords)*
    toggle : "toggle"
    momentary : "momentary"
    mode: "mode-2"
    map_mode_absolute : "map_mode_absolute"
    min_max: "min_max(" NUMBER "," NUMBER ")"
    # refinements: (toggle | min_max)*
    refinements: (toggle|momentary|map_mode_absolute|mode)*
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
'''
full_parser = Lark(grammar, start='multi')
small_parser = Lark(grammar, start='single')


@dataclass
class MinMax:
    from_: int
    to: int


@dataclass
class GridCell:
    """A 2D grid coordinate parsed from `row::colrange` (the part after the
    single `:` axis separator). `row` is 1-indexed from the top; `cols` is the
    inclusive (lo, hi) column range."""
    row: int
    cols: Tuple[int, int]


class MyTransformer(Transformer):

    def __init__(self, full=False):
        super().__init__()

    def axis_no(self, items):
        return int(items[0])

    def axis(self, items):
        return str(items[0])

    def range(self, key_value):
        k, *v = key_value
        if len(v) == 0:
            return int(k), int(k)
        else:
            return int(k), int(v[0])

    def coords_list(self, items):
        return items

    def coords(self, items):
        return items

    def refinements(self, items):
        return items

    def min_max(self, v):
        return MinMax(int(v[0]), int(v[1]))

    def grid_cell(self, items):
        return GridCell(int(items[0]), items[1])

    @staticmethod
    def _coords_from(axis, axis_no, payload, refs):
        # payload is either a flat (lo, hi) range or a 2D GridCell.
        if isinstance(payload, GridCell):
            return EncoderCoords(row=axis_no, range_=payload.cols, axis_kind=axis,
                                 grid_row=payload.row, encoder_refs=refs)
        return EncoderCoords(row=axis_no, range_=payload, axis_kind=axis, encoder_refs=refs)

    def single(self, values):
        [mains, refs] = values
        for main in mains:
            [axis, axis_no, payload] = main
            return self._coords_from(axis, axis_no, payload, refs)

    def multi(self, values):
        result = []
        [mains, refs] = values
        for main in mains:
            [axis, axis_no, payload] = main
            result.append(self._coords_from(axis, axis_no, payload, refs))

        return result

    col = lambda self, _: "col"
    row = lambda self, _: "row"
    grid = lambda self, _: "grid"
    toggle = lambda self, _: Toggle.instance()
    momentary = lambda self, _: Momentary.instance()
    mode = lambda self, _: Mode.instance()
    map_mode_absolute = lambda self, _: MapModeAbsolute.instance()


def parse(raw) -> EncoderCoords:
    parsed_tree = small_parser.parse(raw)
    return MyTransformer().transform(parsed_tree)


def parse_multiple(raw) -> List[EncoderCoords]:
    parsed_tree = full_parser.parse(raw)
    return MyTransformer(full=True).transform(parsed_tree)
