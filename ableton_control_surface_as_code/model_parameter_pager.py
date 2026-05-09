from typing import Literal, Optional, List

from pydantic import BaseModel, field_validator

from ableton_control_surface_as_code.core_model import MidiCoords, parse_coords, ButtonProviderBaseModel
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class _IncDec(BaseModel):
    inc: EncoderCoords
    dec: EncoderCoords

    @field_validator('inc', 'dec', mode='before')
    @classmethod
    def _parse(cls, value):
        return parse_coords(value) if value is not None else None


class ParameterPagerV2(BaseModel):
    type: Literal['parameter-pager'] = 'parameter-pager'
    encoders: Optional[_IncDec] = None
    buttons: Optional[_IncDec] = None


class ParameterPagerMidiMapping(ButtonProviderBaseModel):
    type: Literal['parameter-pager'] = 'parameter-pager'
    midi_coords: List[MidiCoords]
    target: Literal['encoder', 'button']
    direction: Literal['inc', 'dec']

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def short_info_string(self):
        return f"pager_{self.target}_{self.direction}"

    def create_controller_element(self):
        return self.only_midi_coord.create_controller_element()

    def template_function_call(self):
        return f"self._helpers.parameter_page_{self.direction}('{self.target}')"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(
            f"_mode_{mode_name}_pager_{self.target}_{self.direction}")


class ParameterPagerWithMidi(BaseModel):
    type: Literal['parameter-pager'] = 'parameter-pager'
    midi_maps: List[ParameterPagerMidiMapping]


def build_parameter_pager_model_v2(controller, pager: ParameterPagerV2) -> ParameterPagerWithMidi:
    midi_maps: List[ParameterPagerMidiMapping] = []

    for target, block in (('encoder', pager.encoders), ('button', pager.buttons)):
        if block is None:
            continue
        for direction, coord in (('inc', block.inc), ('dec', block.dec)):
            midi_coords, _ = controller.build_midi_coords(coord)
            midi_maps.append(ParameterPagerMidiMapping(
                midi_coords=midi_coords,
                target=target,
                direction=direction,
            ))

    return ParameterPagerWithMidi(midi_maps=midi_maps)
