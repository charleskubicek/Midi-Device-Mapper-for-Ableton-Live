from typing import Literal, List, Dict

from pydantic import BaseModel, Field

from ableton_control_suface_as_code.core_model import MidiCoords, parse_coords, EncoderCoords, \
    ButtonProviderBaseModel


class Functions(BaseModel):
    type: Literal['functions'] = "functions"
    mappings_raw: Dict[str, str] = Field(alias='mappings')

    @property
    def mappings(self) -> Dict[str, EncoderCoords]:
        return {key: parse_coords(value) for key, value in self.mappings_raw.items() if value is not None}


class FunctionsMidiMapping(ButtonProviderBaseModel):
    type: Literal['functions'] = 'functions'
    midi_coords: List[MidiCoords]
    function: str

    def info_string(self):
        return f"function {self.function}, {self.midi_coords}"

    def create_button_element(self):
        return self.only_midi_coord.create_button_element()

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def template_function_name(self):
        return f"self.functions.{self.function}(self)"


class FunctionsWithMidi(BaseModel):
    type: Literal['functions'] = 'functions'
    midi_maps: list[FunctionsMidiMapping]


def build_functions_model_v2(controller, mapping: Functions) -> FunctionsWithMidi:
    midi_maps = []
    for fn, enc in mapping.mappings.items():
        midi_coords, _ = controller.build_midi_coords(enc)
        midi_maps.append(FunctionsMidiMapping(midi_coords=midi_coords, function=fn))

    return FunctionsWithMidi(midi_maps=midi_maps)