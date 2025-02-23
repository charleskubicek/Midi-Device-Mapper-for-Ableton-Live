import itertools
from typing import Literal, List, Optional

from pydantic import BaseModel, Field, validator, field_validator

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, NamedTrack, RowMapV2_1, parse_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class DeviceMidiMapping(BaseModel):
    type: Literal['device'] = 'device'
    midi_coords: List[MidiCoords]
    parameter: int

    @classmethod
    def from_coords(cls, midi_channel, midi_number, midi_type, parameter):
        return cls(midi_coords=[MidiCoords(channel=midi_channel, type=midi_type, number=midi_number)],
                   parameter=parameter)

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def short_info_string(self):
        return f"p {self.parameter}"

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_p{self.parameter}")

# class DeviceCustomParameterMapping(BaseModel):
#     type: Literal['device'] = 'device'
#     midi_coord: MidiCoords
#     device_param_name: str



class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_maps: List[DeviceMidiMapping]
    custom_device_mappings: dict[str, dict[str, MidiCoords]]


class DeviceEncoderMappings(BaseModel):
    type: Literal['device'] = 'device'
    encoders: RowMapV2_1
    on_off: Optional[EncoderCoords] = Field(None, alias='on-off')

    @field_validator('on_off', mode='before')
    @classmethod
    def parse_on_off(cls, value):
        return parse_coords(value) if value is not None else None

class CustomParameterMapping(BaseModel):
    type: Literal['device'] = 'device'
    device_name:str = Field(alias='device-name')
    parameter_mappings_raw :dict[str, str] = Field(alias='parameter-mappings')

class DeviceV2(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    mappings: DeviceEncoderMappings
    custom_parameter_mappings: Optional[list[CustomParameterMapping]] = Field(None, alias='custom-parameter-mappings')

    @field_validator("track", mode='before')
    @classmethod
    def parse_track(cls, value):
        return TrackInfo.parse_track(value)

def build_device_model_v2_1(controller, device: DeviceV2) -> DeviceWithMidi:
    midi_maps = []
    custom_param_maps = {}

    iterator = device.mappings.encoders.parameters.as_inclusive_list()
    iterator, _ = itertools.tee(iterator)

    for mcs in device.mappings.encoders.multi_encoder_coords:
        midis, _ = controller.build_midi_coords(mcs)

        ## TODO Warn here if the lenght of the midis and parameters aren't the same size
        for m, p in zip(midis, iterator):
            midi_maps.append(DeviceMidiMapping(
                midi_coords=[m],
                parameter=p
            ))

    if device.mappings.on_off:
        midi_maps.append(DeviceMidiMapping(
            midi_coords=controller.build_midi_coords(device.mappings.on_off)[0],
            parameter=0
        ))

    for mapping in device.custom_parameter_mappings:
        device_name = mapping.device_name

        parsed_coords = { p_name: controller.build_midi_coords(parse_coords(encoder))[0][0]
         for p_name, encoder in mapping.parameter_mappings_raw.items()}


        custom_param_maps[device_name] = parsed_coords

    return DeviceWithMidi(
        track=device.track,
        device=device.device,
        midi_maps=midi_maps,
        custom_device_mappings=custom_param_maps)
