from typing import Literal, Optional, List

from pydantic import BaseModel, Field

from ableton_control_suface_as_code.core_model import MidiCoords, parse_coords, DeviceNavAction


class DeviceNavMappings(BaseModel):
    left_raw: Optional[str] = Field(alias='left')
    right_raw: Optional[str] = Field(alias='right')
    first_raw: Optional[str] = Field(alias='first')
    last_raw: Optional[str] = Field(alias='last')

    def as_list(self):
        res = []
        if self.right_raw is not None:
            res.append((DeviceNavAction.right, parse_coords(self.right_raw)))

        if self.right_raw is not None:
            res.append((DeviceNavAction.left, parse_coords(self.left_raw)))

        if self.first_raw is not None:
            res.append((DeviceNavAction.first, parse_coords(self.first_raw)))

        if self.last_raw is not None:
            res.append((DeviceNavAction.last, parse_coords(self.last_raw)))

        return res


class DeviceNav(BaseModel):
    type: Literal['device-nav'] = "device-nav"
    mappings: DeviceNavMappings


class DeviceNavMidiMapping(BaseModel):
    type: Literal['device-nav'] = 'device-nav'
    midi_coords: List[MidiCoords]
    action: DeviceNavAction

    def __init__(self, midi_coords: MidiCoords, action: DeviceNavAction):
        super().__init__(midi_coords=list(midi_coords), action=action)

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__device_nav_{self.action.value}"

    def template_function_name(self):
        return self.action.template_call


class DeviceNavWithMidi(BaseModel):
    type: Literal['device-nav'] = 'device-nav'
    midi_maps: list[DeviceNavMidiMapping]


def build_device_nav_model_v2(controller, mapping: DeviceNav) -> DeviceNavWithMidi:
    midi_maps = []
    for action, enc in mapping.mappings.as_list():
        midi_coords, _ = controller.build_midi_coords(enc)
        midi_maps.append(DeviceNavMidiMapping(midi_coords=midi_coords, action=action))

    return DeviceNavWithMidi.model_construct(midi_maps=midi_maps)