from lark import Lark, Transformer, Tree

from dataclasses import dataclass
from typing import List, Union

from dataclasses import dataclass
from typing import List, Union


@dataclass
class Axis:
    value: str


@dataclass
class MinMax:
    min_value: float
    max_value: float


@dataclass
class Toggle:
    pass


@dataclass
class Range:
    start: float
    end: float


@dataclass
class Coord:
    axis: Axis
    index: Union[float, Range]


@dataclass
class Definition:
    coord: Coord
    refinements: List[Union[Toggle, MinMax]]


@dataclass
class Value:
    definition: Definition


def parse_axis(tree: Tree) -> Axis:
    return Axis(value=tree.children[0].value)


def parse_min_max(tree: Tree) -> MinMax:
    min_value = float(tree.children[0].value)
    max_value = float(tree.children[1].value)
    return MinMax(min_value=min_value, max_value=max_value)


def parse_toggle(tree: Tree) -> Toggle:
    return Toggle()


def parse_range(tree: Tree) -> Range:
    start = float(tree.children[0].value)
    end = float(tree.children[1].value)
    return Range(start=start, end=end)


def parse_coord(tree: Tree) -> Coord:
    axis = parse_axis(tree.children[0])
    if isinstance(tree.children[1], Tree) and tree.children[1].data == 'range':
        index = parse_range(tree.children[1])
    else:
        index = float(tree.children[1].value)
    return Coord(axis=axis, index=index)


def parse_refinements(tree: Tree) -> Union[Toggle, MinMax]:
    if tree.data == 'toggle':
        return parse_toggle(tree)
    elif tree.data == 'min_max':
        return parse_min_max(tree)


def parse_def(tree: Tree) -> Definition:
    coord = parse_coord(tree.children[0])
    refinements = [parse_refinements(child) for child in tree.children[1:]]
    return Definition(coord=coord, refinements=refinements)


def parse_tree(tree: Tree) -> Value:
    if tree.data == 'start':
        definition = parse_def(tree.children[0])
        return Value(definition=definition)


g1 = '''
            start: def
    
            row : "row"
            col : "col"
            axis : row | col
            toggle : "toggle"
            min_max: "min_max(" NUMBER "," NUMBER ")"
            refinements: toggle | min_max
            range: NUMBER ":" NUMBER
            coord: axis "-" NUMBER | axis "-" range
            def  : coord refinements*  
    
            %import common.NUMBER
            %import common.WS
            %ignore WS
         '''

parser = Lark('''
    value : axis "_" range all
    
    row : "row"
    col : "col"
    axis : row | col
    range: (NUMBER ":" NUMBER) | NUMBER
    toggle : "toggle"
    min_max: "min_max(" NUMBER "," NUMBER ")"
    all: (toggle | min_max)*
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
''', start='value')

# input_string = "row-3:4"
input_string = "row_3:4 toggle min_max(12, 15)"
# input_string = "row-3"

# Parse the input string
parsed_tree = parser.parse(input_string)
# parser.parse(input_string_1)
# print( parsed_tree.pretty() )

from lark import Transformer


class MyTransformer(Transformer):
    def axis(self, items):
        return str(items[0])

    def range(self, key_value):
        if len(key_value) == 1:
            return Range(int(key_value[0]), int(key_value[0]))

        k, v = key_value
        return Range(int(k), int(v))

    def all(self, items):
        return items

    def min_max(self, v):
        return MinMax(int(v[0]), int(v[1]))

    def value(self, v):
        return v

    col = lambda self, _: "col"
    row = lambda self, _: "row"
    toggle = lambda self, _: "toggle"


# print(parser.parse(input_string))
# print()
print(MyTransformer().transform(parsed_tree))

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
