from dataclasses import dataclass

from lark import Lark, Transformer, Tree

from ableton_control_suface_as_code.core_model import EncoderCoords, EncoderRefinement, Toggle


parser = Lark('''
    value : axis "_" axis_no ":" range all
    
    row : "row"
    col : "col"
    axis : row | col
    axis_no : NUMBER
    range: NUMBER | (NUMBER "-" NUMBER)
    toggle : "toggle"
    min_max: "min_max(" NUMBER "," NUMBER ")"
    # all: (toggle | min_max)*
    all: toggle*
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
''', start='value')

# # input_string = "row-3:4"
# input_string = "row_3:1"
input_string = "row_3:1-4 toggle"
# # input_string = "row-3"
#
# # Parse the input string
parsed_tree = parser.parse(input_string)
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

    def all(self, items):
        return items

    def min_max(self, v):
        return MinMax(int(v[0]), int(v[1]))

    def value(self, v):
        [axis, axis_no, range, *refs] = v
        return EncoderCoords(axis_no, range[0], range[1], encoder_refs=refs[0])

    col = lambda self, _: "col"
    row = lambda self, _: "row"
    toggle = lambda self, _: Toggle.instance()

def parse(raw) -> EncoderCoords:
    parsed_tree = parser.parse(raw)
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
