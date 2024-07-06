from abc import ABC
from dataclasses import dataclass
from typing import Optional, List

from lark import Lark
from pydantic import BaseModel

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
    value : coords+ all
    
    row : "row"
    col : "col"
    axis : row | col
    axis_no : NUMBER
    range: NUMBER | (NUMBER "-" NUMBER)
    coords: axis "_" axis_no ":" range
    toggle : "toggle"
    min_max: "min_max(" NUMBER "," NUMBER ")"
    # all: (toggle | min_max)*
    all: toggle*
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
'''
full_parser = Lark(grammar, start='value')
# small_parser = Lark(grammar, start='range')

# # input_string = "row-3:4"
# input_string = "row_3:1"
input_string = "row_3:1-4 toggle"
# input_string = "4"
# # input_string = "row-3"
#
# # Parse the input string
# parsed_tree = small_parser.parse(input_string)
parsed_tree = full_parser.parse(input_string)
# # parser.parse(input_string_1)
# # print( parsed_tree.pretty() )

from lark import Transformer

@dataclass
class Range:
    from_:int
    to:int

@dataclass
class MinMax:
    from_:int
    to:int


class MyTransformer(Transformer):
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

    def coords(self, items):
        return items

    def all(self, items):
        return items

    def min_max(self, v):
        return MinMax(int(v[0]), int(v[1]))

    def value(self, values):
        [main, refs] = values
        [axis, axis_no, range] = main
        return EncoderCoords(axis_no, range[0], range[1], encoder_refs=refs)

    col = lambda self, _: "col"
    row = lambda self, _: "row"
    toggle = lambda self, _: Toggle.instance()


def parse(raw) -> EncoderCoords:
    parsed_tree = full_parser.parse(raw)
    return MyTransformer().transform(parsed_tree)

# print(parser.parse(input_string))
# print()
print(MyTransformer().transform(parsed_tree))
# EncoderCoords()

# print(f"parsed_tree = {parsed_tree}")
#
# # Convert the parse tree into data classes
# value_object = parse_tree(parsed_tree)
#
# print(value_object)
# # Transform the parse tree into data classes
# # value_object = transformer.transform(parse_tree)
#
# # print(value_object.definition)
#
# # print( l.parse("row_3") )
# # print( l.parse("row_3:10") )
# # print( l.parse(" row_3:4 toggle") )
# # print( l.parse(" row_3:4 min_max(12, 15)") )
# tree = l.parse(" row-3:4 toggle min_max(12, 15)")
# print(tree)
