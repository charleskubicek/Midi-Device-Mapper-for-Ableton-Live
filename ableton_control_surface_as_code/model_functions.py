from pathlib import Path
from typing import Literal, List, Dict

from pydantic import BaseModel, Field

from ableton_control_surface_as_code.core_model import MidiCoords, parse_coords, ButtonProviderBaseModel
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class Functions(BaseModel):
    type: Literal['functions'] = "functions"
    mappings_raw: Dict[str, str] = Field(alias='mappings')

    @property
    def mappings(self) -> Dict[str, EncoderCoords]:
        return {key: parse_coords(value) for key, value in self.mappings_raw.items() if value is not None}


class FunctionsMidiMapping(ButtonProviderBaseModel):
    type: Literal['functions'] = 'functions'
    midi_coords: List[MidiCoords]
    function_name: str
    parameter_len:int = 0

    def info_string(self):
        return f"function_{self.function_name}_{self.only_midi_coord.info_string()}"

    def short_info_string(self):
        return f"f_{self.function_name[:10]}"

    def create_controller_element(self):
        return self.only_midi_coord.create_controller_element()

    @property
    def only_midi_coord(self) -> MidiCoords:
        if len(self.midi_coords) != 1:
            raise ValueError(f'More than one midi coord found for function mapping: {self.midi_coords}')
        return self.midi_coords[0]

    def template_function_call(self):
        fn = self.function_name
        if self.parameter_len == 2:
            fn = f"{fn}(value, previous_value)"
        elif self.parameter_len == 1:
            fn = f"{fn}(value)"
        else:
            fn = f"{fn}()"

        return f"self.functions.{fn}"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_fn_{self.function_name}")


class FunctionsWithMidi(BaseModel):
    type: Literal['functions'] = 'functions'
    midi_maps: list[FunctionsMidiMapping]

import ast

class FunctionLookup:

    @staticmethod
    def get_functions_from_class(class_node):
        functions = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                params = [arg.arg for arg in node.args.args]
                functions.append((function_name, params))
        return functions

    @staticmethod
    def inspect_python_file(file_path, fn_name):
        with open(file_path, "r") as file:
            tree = ast.parse(file.read())

        classes = {}
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                if class_name == 'Functions':
                    functions = FunctionLookup.get_functions_from_class(node)
                    for function_name, params in functions:
                        print(f"function_name = {function_name}: {params}")

                        if function_name == fn_name:
                            # return len(params) == 2
                            return len(params) - 1

        raise ValueError(f"Function {fn_name} not found in {file_path}")


def build_functions_model_v2(controller, mapping: Functions, root_dir:Path) -> FunctionsWithMidi:
    midi_maps = []
    for fn, enc in mapping.mappings.items():
        midi_coords, _ = controller.build_midi_coords(enc)

        function_param_count = FunctionLookup.inspect_python_file(root_dir / "functions.py", fn)
        midi_maps.append(FunctionsMidiMapping(midi_coords=midi_coords, function_name=fn, parameter_len=function_param_count))

    return FunctionsWithMidi(midi_maps=midi_maps)
