import itertools
from typing import Literal, List

from pydantic import BaseModel, Field

from ableton_control_suface_as_code.core_model import MidiCoords, TrackInfo, NamedTrack, RowMapV2_1


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


class DeviceV2_1(BaseModel):
    type: Literal['device'] = 'device'
    track_raw: str = Field(alias='track')
    device: str
    ranges: list[RowMapV2_1]

    @property
    def track_info(self) -> TrackInfo:
        if self.track_raw == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if self.track_raw == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            exit(1)


def build_device_model_v2_1(controller, device:DeviceV2_1) -> DeviceWithMidi:
    midi_range_mappings = []

    for rnge in device.ranges:
        iterator = rnge.parameters.as_inclusive_list()
        iterator, _ = itertools.tee(iterator)

        for mcs in rnge.multi_encoder_coords:
            midis, _ = controller.build_midi_coords(mcs)

            ## TODO Warn here if the lenght of the midis and parameters aren't the same size
            for m, p in zip(midis, iterator):
                midi_range_mappings.append(DeviceMidiMapping(
                    midi_coords=[m],
                    parameter=p
                ))

    return DeviceWithMidi(
        track=device.track_info,
        device=device.device,
        midi_maps=midi_range_mappings)