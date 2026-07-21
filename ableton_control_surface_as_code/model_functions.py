from pathlib import Path
from typing import Literal, List, Dict, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from ableton_control_surface_as_code.core_model import MidiCoords, parse_multiple_coords, ButtonProviderBaseModel
from ableton_control_surface_as_code.encoder_coords import EncoderCoords

_SWITCH_KEYS = {'switch1', 'switch2'}

# Reserved function names that route to a built-in surface method instead of the
# user's functions.py class. `hud_toggle` toggles the HUD's dismiss state — it lives
# on the surface (which holds the HUD client / helpers), so it is intercepted here
# rather than looked up in functions.py.
RESERVED_BUILTIN_FUNCTIONS = {'hud_toggle'}

# Maps a reserved builtin name to the call expression emitted into the generated
# listener. These run on main_component, which exposes self._helpers.
_BUILTIN_CALLS = {
    'hud_toggle': 'self._helpers.toggle_hud()',
}


class Functions(BaseModel):
    type: Literal['functions'] = "functions"
    mappings_raw: Dict[str, str] = Field(alias='mappings')

    @model_validator(mode='after')
    def reject_switch_keys(self):
        bad = _SWITCH_KEYS & self.mappings_raw.keys()
        if bad:
            raise ValueError(
                f"{', '.join(sorted(bad))} cannot be used in a 'functions' mapping — "
                "put them inside a 'device' mapping alongside 'encoders' instead"
            )
        return self

    @property
    def mappings(self) -> Dict[str, List[EncoderCoords]]:
        return {key: parse_multiple_coords(value) for key, value in self.mappings_raw.items() if value is not None}


class FunctionsMidiMapping(ButtonProviderBaseModel):
    type: Literal['functions'] = 'functions'
    midi_coords: List[MidiCoords]
    function_name: str
    parameter_len:int = 0
    builtin: bool = False
    hud_name: Optional[str] = None
    hud_glyph: Optional[str] = None

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
        if self.builtin:
            return _BUILTIN_CALLS[self.function_name]

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

# Decorator the user can put on a Functions method to name its HUD cell, e.g.
# `@hud_name("Audio -> Simpler")`. It's a runtime no-op (see
# source_modules/hud_name.py); the generator reads the string statically here.
_HUD_NAME_DECORATOR = 'hud_name'


class FunctionLookup:

    @staticmethod
    def _hud_name_from_decorators(node) -> Tuple[Optional[str], Optional[str]]:
        """Return (name, glyph) from an `@hud_name("Name", "sf.symbol")` decorator
        on the given function def. `glyph` comes from the optional 2nd positional
        arg or a `glyph=` keyword; both None if the def isn't decorated."""
        for dec in node.decorator_list:
            if (isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == _HUD_NAME_DECORATOR
                    and dec.args
                    and isinstance(dec.args[0], ast.Constant)):
                name = dec.args[0].value
                glyph = None
                if len(dec.args) >= 2 and isinstance(dec.args[1], ast.Constant):
                    glyph = dec.args[1].value
                for kw in dec.keywords:
                    if kw.arg == 'glyph' and isinstance(kw.value, ast.Constant):
                        glyph = kw.value.value
                return name, glyph
        return None, None

    @staticmethod
    def get_functions_from_class(class_node):
        functions = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                params = [arg.arg for arg in node.args.args]
                hud_name, hud_glyph = FunctionLookup._hud_name_from_decorators(node)
                functions.append((function_name, params, hud_name, hud_glyph))
        return functions

    @staticmethod
    def inspect_python_file(file_path, fn_name) -> Tuple[int, Optional[str], Optional[str]]:
        """Return (parameter_len, hud_name, hud_glyph) for `fn_name` in the file's
        `Functions` class. parameter_len excludes `self`; hud_name/hud_glyph are
        the `@hud_name(...)` label and SF Symbol if present, else None."""
        with open(file_path, "r") as file:
            tree = ast.parse(file.read())

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == 'Functions':
                functions = FunctionLookup.get_functions_from_class(node)
                for function_name, params, hud_name, hud_glyph in functions:
                    if function_name == fn_name:
                        return len(params) - 1, hud_name, hud_glyph

        raise ValueError(f"Function {fn_name} not found in {file_path}")


def build_functions_model_v2(controller, mapping: Functions, root_dir: Path,
                             functions_path: Optional[Path] = None) -> FunctionsWithMidi:
    # `functions_path` lets a surface point at one shared functions file (e.g.
    # ../shared/ck_functions.py) instead of a per-surface copy; when unset we
    # fall back to functions.py next to the mapping (see
    # ai-coding/plans/shared-functions-file-plan.md).
    functions_path = functions_path if functions_path is not None else root_dir / "functions.py"

    midi_maps = []
    for fn, encs in mapping.mappings.items():
        midi_coords, _ = controller.build_midi_coords(encs)

        if fn in RESERVED_BUILTIN_FUNCTIONS:
            # Built-in: no entry in functions.py — skip the user-file lookup and
            # route to a surface method (see _BUILTIN_CALLS / template_function_call).
            parameter_len, builtin, hud_name, hud_glyph = 0, True, None, None
        else:
            parameter_len, hud_name, hud_glyph = FunctionLookup.inspect_python_file(functions_path, fn)
            builtin = False

        # One listener per physical button (comma-listed coords bind one function
        # to several buttons).
        for mc in midi_coords:
            midi_maps.append(FunctionsMidiMapping(midi_coords=[mc], function_name=fn,
                                                  parameter_len=parameter_len, builtin=builtin,
                                                  hud_name=hud_name, hud_glyph=hud_glyph))

    return FunctionsWithMidi(midi_maps=midi_maps)
