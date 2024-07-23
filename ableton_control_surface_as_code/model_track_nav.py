from typing import Literal, Optional, List, Tuple

from pydantic import BaseModel, Field

from ableton_control_surface_as_code.core_model import Direction, MidiCoords, parse_coords, ButtonProviderBaseModel
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class TrackNavMappings(BaseModel):
    left_raw: Optional[str] = Field(alias='left')
    right_raw: Optional[str] = Field(alias='right')

    def as_list(self) -> List[Tuple[Direction, EncoderCoords]]:
        res = []

        if self.right_raw is not None:
            res.append((Direction.inc, parse_coords(self.right_raw)))

        if self.right_raw is not None:
            res.append((Direction.dec, parse_coords(self.left_raw)))

        return res


class TrackNav(BaseModel):
    type: Literal['track-nav'] = "track-nav"
    mappings: TrackNavMappings


class TrackNavMidiMapping(ButtonProviderBaseModel):
    type: Literal['track-nav'] = 'track-nav'
    midi_coords: List[MidiCoords]
    direction: Direction

    @classmethod
    def from_single_coord(cls, midi_coord:MidiCoords, direction: Direction):
        return TrackNavMidiMapping(midi_coords=[midi_coord], direction=direction)

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def short_info_string(self):
        return f"tn_{self.direction.value}"

    def create_controller_element(self):
        return self.only_midi_coord.create_controller_element()

    def template_function_name(self):
        if self.direction == Direction.inc:
            return 'self.track_nav_inc()'
        else:
            return 'self.track_nav_dec()'

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_{self.direction .value}")

class TrackNavWithMidi(BaseModel):
    type: Literal['track-nav'] = 'track-nav'
    midi_maps: list[TrackNavMidiMapping]


def build_track_nav_model_v2(controller, mapping: TrackNav) -> TrackNavWithMidi:
    midi_maps = []
    for dir, enc in mapping.mappings.as_list():
        midi_coords, _ = controller.build_midi_coords(enc)
        midi_maps.append(TrackNavMidiMapping(midi_coords=midi_coords, direction=dir))

    return TrackNavWithMidi(midi_maps=midi_maps)
