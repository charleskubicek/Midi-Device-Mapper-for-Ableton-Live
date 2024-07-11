from abc import ABC
from dataclasses import dataclass, field
from typing import Optional, List

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


@dataclass
class EncoderRefinements:
    refs:List[EncoderRefinement]

    def has_toggle(self):
        return any(ref.name() == "toggle" for ref in self.refs)


@dataclass
class EncoderCoordsV2_1:
    row: int
    range_: [int, int]
    encoder_refs: List[EncoderRefinement] = field(default_factory=list)

    @property
    def range_inclusive(self):
        return range(self.range_[0], self.range_[1] + 1)



class EncoderCoords(BaseModel):
    row: int
    col: int
    row_range_end: int
    encoder_refs_raw: Optional[List[EncoderRefinement]] = None
    encoder_refs: List[EncoderRefinement] = list()

    @property
    def range_inclusive(self):
        return range(self.col, self.row_range_end + 1)

    def __init__(self, row, col=None, row_range_end=None, encoder_refs=None):
        super().__init__(row=row, col=col, row_range_end=row_range_end, encoder_refs=encoder_refs)


grammar = '''
    multi : coords_list+ refinements
    single : coords_list refinements
    
    row : "row"
    col : "col"
    axis : row | col
    axis_no : NUMBER
    range: NUMBER | (NUMBER "-" NUMBER)
    coords: axis "-" axis_no ":" range
    coords_list: coords  ("," coords)*
    toggle : "toggle"
    min_max: "min_max(" NUMBER "," NUMBER ")"
    # refinements: (toggle | min_max)*
    refinements: toggle*
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
'''
full_parser = Lark(grammar, start='multi')
small_parser = Lark(grammar, start='single')

@dataclass
class MinMax:
    from_:int
    to:int


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

    def single(self, values):
        [mains, refs] = values
        for main in mains:
            [axis, axis_no, range] = main
            return EncoderCoords(axis_no, range[0], range[1], encoder_refs=refs)


    def multi(self, values):
        result = []
        [mains, refs] = values
        for main in mains:
            [axis, axis_no, range] = main
            result.append(EncoderCoords(axis_no, range[0], range[1], encoder_refs=refs))

        return result

    col = lambda self, _: "col"
    row = lambda self, _: "row"
    toggle = lambda self, _: Toggle.instance()


def parse(raw) -> EncoderCoords:
    parsed_tree = small_parser.parse(raw)
    return MyTransformer().transform(parsed_tree)

def parse_multiple(raw) -> List[EncoderCoords]:
    parsed_tree = full_parser.parse(raw)
    return MyTransformer(full=True).transform(parsed_tree)

