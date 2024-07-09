from typing import Literal, Optional, List

from pydantic import BaseModel, Field

from ableton_control_surface_as_code.core_model import MidiCoords, parse_coords, DeviceNavAction, ButtonProviderBaseModel
from ableton_control_surface_as_code.model_controller import ControllerV2


class DeviceNavMappings(BaseModel):
    left_raw: Optional[str] = Field(default=None, alias='left')
    right_raw: Optional[str] = Field(default=None, alias='right')
    first_raw: Optional[str] = Field(default=None, alias='first')
    last_raw: Optional[str] = Field(default=None, alias='last')

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


class DeviceNavMidiMapping(ButtonProviderBaseModel):
    type: Literal['device-nav'] = 'device-nav'
    midi_coords: List[MidiCoords]
    action: DeviceNavAction

    def __init__(self, midi_coords: MidiCoords, action: DeviceNavAction):
        super().__init__(midi_coords=list(midi_coords), action=action)

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def short_info_string(self):
        return f"dn_{self.action.value}"

    def create_controller_element(self):
        return self.only_midi_coord.create_controller_element()

    def template_function_name(self):
        return self.action.template_call

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_{self.action.value}")


class DeviceNavWithMidi(BaseModel):
    type: Literal['device-nav'] = 'device-nav'
    midi_maps: list[DeviceNavMidiMapping]


def build_device_nav_model_v2(controller:ControllerV2, mapping: DeviceNav) -> DeviceNavWithMidi:
    midi_maps = []
    for action, enc in mapping.mappings.as_list():
        midi_coords, _ = controller.build_midi_coords(enc)
        midi_maps.append(DeviceNavMidiMapping(midi_coords=midi_coords, action=action))

    return DeviceNavWithMidi(midi_maps=midi_maps)
