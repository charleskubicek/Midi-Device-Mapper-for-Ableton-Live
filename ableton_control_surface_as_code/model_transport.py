from typing import Literal, Optional, List

from pydantic import BaseModel, Field

from ableton_control_surface_as_code.core_model import Direction, MidiCoords, parse_coords, ButtonProviderBaseModel
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class TransportMappings(BaseModel):
    play_stop_raw: Optional[str] = Field(alias="play-stop", default=None)
    record_session_raw: Optional[str] = Field(alias="record-session", default=None)
    record_arrangement_raw: Optional[str] = Field(alias="record-arrangement", default=None)
    loop_raw: Optional[str] = Field(alias="loop", default=None)
    midi_arrange_overdub_raw: Optional[str] = Field(alias="midi-arrange-overdub", default=None)

    def as_parsed_dict(self) -> dict[str, EncoderCoords]:
        return {key: parse_coords(value)
                for key, value in self.model_dump().items() if value is not None}


class Transport(BaseModel):
    type: Literal['transport'] = "transport"
    mappings: TransportMappings


class TransportMidiMapping(ButtonProviderBaseModel):
    type: Literal['transport'] = 'transport'
    midi_coords: List[MidiCoords]
    api_call: str

    def function_call_for(self, key):
        if key == "play_stop_raw":
            return "self.song().is_playing"
        if key == "record_session_raw":
            return "self.song().session_record"
        if key == "record_arrangement_raw":
            return "self.song().record_mode"
        if key == "loop_raw":
            return "self.song().loop"
        if key == "midi_arrange_overdub_raw":
            return "self.song().arrangement_overdub"
        if key == "metronome_raw":
            return "self.song().metronome"

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def short_info_string(self):
        return f"t {self.api_call}"

    def create_controller_element(self):
        return self.only_midi_coord.create_controller_element()

    def template_function_name(self):
        return f"{self.function_call_for(self.api_call)} = not {self.function_call_for(self.api_call)}"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_{self.api_call}")


class TransportWithMidi(BaseModel):
    type: Literal['transport'] = 'transport'
    midi_maps: list[TransportMidiMapping]


def build_transport_model(controller, mapping: Transport):
    mixer_maps = []
    for api_call, enc_coords in mapping.mappings.as_parsed_dict().items():
        coords_list, type = controller.build_midi_coords(enc_coords)

        mixer_maps.append(TransportMidiMapping(
            midi_coords=coords_list,
            api_call=api_call))

    return TransportWithMidi(midi_maps=mixer_maps)
