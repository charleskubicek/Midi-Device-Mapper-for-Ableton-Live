import itertools
from typing import Literal, List, Optional

from pydantic import BaseModel, Field

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, NamedTrack, RowMapV2_1, parse_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class DeviceMidiMapping(BaseModel):
    type: Literal['device'] = 'device'
    midi_coords: List[MidiCoords]
    parameter: int

    @classmethod
    def from_coords(cls, midi_channel, midi_number, midi_type, parameter):
        return cls(midi_coords=[MidiCoords(channel=midi_channel, type=midi_type, number=midi_number)], parameter=parameter)

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


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_maps: List[DeviceMidiMapping]

class DeviceEncoderMappings(BaseModel):
    type: Literal['device'] = 'device'
    encoders: RowMapV2_1
    on_off_raw: Optional[str] = Field(None, alias='on-off')

    @property
    def on_off(self) -> Optional[EncoderCoords]:
        if self.on_off_raw is None:
            return None
        return parse_coords(self.on_off_raw)


class DeviceV2(BaseModel):
    type: Literal['device'] = 'device'
    track_raw: str = Field(alias='track')
    device: str
    mappings: DeviceEncoderMappings

    @property
    def track_info(self) -> TrackInfo:
        if self.track_raw == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if self.track_raw == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            exit(1)


def build_device_model_v2_1(controller, device:DeviceV2) -> DeviceWithMidi:
    midi_maps = []

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

    return DeviceWithMidi(
        track=device.track_info,
        device=device.device,
        midi_maps=midi_maps)