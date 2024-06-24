from typing import Literal, List

from pydantic import BaseModel, Field

from ableton_control_suface_as_code.core_model import MidiCoords, TrackInfo, NamedTrack, RowMapV2


class DeviceMidiMapping(BaseModel):
    type: Literal['device'] = 'device'
    midi_coords: MidiCoords
    parameter: int

    @classmethod
    def from_coords(cls, midi_channel, midi_number, midi_type, parameter):
        return cls(midi_coords=MidiCoords(channel=midi_channel, type=midi_type, number=midi_number), parameter=parameter)
    # def __init__(self, midi_channel, midi_number, midi_type, parameter):
    #     super().__init__({'midi_coords': MidiCoords(midi_channel, midi_type, midi_number), 'parameter' :parameter})

    def info_string(self):
        return f"ch{self.midi_coords.channel}_no{self.midi_coords.number}_{self.midi_coords.type.value}__p{self.parameter}"


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_range_maps: List[DeviceMidiMapping]


def build_device_model_v2(controller, mapping):
    midi_range_mappings = []
    for rm in mapping.ranges:
        group = controller.find_group(rm.row)
        assert len(rm.range) <= len(
            group.midi_range), f"rm.range of {len(rm.range)} is too long for group, max is {len(group.midi_range)} ({rm.range}) to group ({group.midi_range})"

        # Go back go the group to find the midi values. We have to switch to zero based
        # because the group is 0 based
        midis = group.midi_range_for(rm.range.as_inclusive_zero_based_range())

        for m, p in zip(midis, rm.parameters.as_inclusive_list()):
            midi_range_mappings.append(DeviceMidiMapping(
                midi_coords=m,
                parameter=p
            ))

    return DeviceWithMidi(
        track=mapping.track_info,
        device=mapping.device,
        midi_range_maps=midi_range_mappings)


class DeviceV2(BaseModel):
    type: Literal['device']
    track_raw: str = Field(alias='track')
    device: str
    ranges: list[RowMapV2]

    @property
    def track_info(self) -> TrackInfo:
        if self.track_raw == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if self.track_raw == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            exit(1)
