from typing import Literal, Optional, List

from pydantic import BaseModel, Field

from ableton_control_suface_as_code.core_model import Direction, MidiCoords, parse_coords


class TrackNavMappings(BaseModel):
    left_raw: Optional[str] = Field(alias='left')
    right_raw: Optional[str] = Field(alias='right')

    def as_list(self):
        res = []
        if self.right_raw is not None:
            res.append((Direction.inc, parse_coords(self.right_raw)))

        if self.right_raw is not None:
            res.append((Direction.dec, parse_coords(self.left_raw)))

        return res


class TrackNav(BaseModel):
    type: Literal['track-nav'] = "track-nav"
    mappings: TrackNavMappings


class TrackNavMidiMapping(BaseModel):
    type: Literal['track-nav'] = 'track-nav'
    midi_coords: List[MidiCoords]
    direction: Direction

    def __init__(self, midi_coords: MidiCoords, direction: Direction):
        super().__init__(midi_coords=[midi_coords], direction=direction)

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__track_nav_{self.direction.value}"

    def template_function_name(self):
        if self.direction == Direction.inc:
            return 'self.track_nav_inc()'
        else:
            return 'self.track_nav_dec()'


class TrackNavWithMidi(BaseModel):
    type: Literal['track-nav'] = 'track-nav'
    midi_maps: list[TrackNavMidiMapping]


def build_track_nav_model_v2(controller, mapping: TrackNav) -> TrackNavWithMidi:
    midi_maps = []
    for dir, enc in mapping.mappings.as_list():
        midi_coords, _ = controller.build_midi_coords(enc)
        midi_maps.append(TrackNavMidiMapping.model_construct(midi_coords=midi_coords, direction=dir))

    return TrackNavWithMidi.model_construct(midi_maps=midi_maps)
