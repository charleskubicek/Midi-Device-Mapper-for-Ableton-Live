from typing import Optional, Literal

from pydantic import BaseModel, Field, model_validator, field_validator

from ableton_control_surface_as_code.core_model import TrackInfo, NamedTrack, MixerMidiMapping, \
    MixerWithMidi, parse_multiple_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords
from ableton_control_surface_as_code.model_controller import ControllerV2


class MixerMappingsV2(BaseModel):
    volume_raw: Optional[str] = Field(default=None, alias="volume")
    pan_raw: Optional[str] = Field(default=None, alias="pan")
    mute_raw: Optional[str] = Field(default=None, alias="mute")
    solo_raw: Optional[str] = Field(default=None, alias="solo")
    arm_raw: Optional[str] = Field(default=None, alias="arm")
    sends_raw: Optional[str] = Field(default=None, alias="sends")

    @model_validator(mode='after')
    def verify_correct_ranges(self):
        single_controllers = ['volume', 'pan', 'mute', 'solo', 'arm']

        d = self.as_parsed_dict()
        for sc in single_controllers:
            if sc in d and '-' in d[sc]:
                raise ValueError(f"{sc} can't have a range value")

        return self

    def as_parsed_dict(self):
        single_controllers = ['volume', 'pan', 'mute', 'solo', 'arm']

        return {key.removesuffix('_raw'): parse_multiple_coords(value)
                for key, value in self.model_dump().items() if value is not None}


class MixerV2(BaseModel):
    type: Literal['mixer'] = "mixer"
    track:TrackInfo = Field(alias='track')
    mappings: MixerMappingsV2

    @field_validator("track", mode='before')
    @classmethod
    def parse_track(cls, value):
        return TrackInfo.parse_track(value)


def build_mixer_model_v2(controller:ControllerV2, mapping: MixerV2):
    mixer_maps = []
    for api_name, enc_coords in mapping.mappings.as_parsed_dict().items():
        coords_list, type = controller.build_midi_coords(enc_coords)

        encoder_coors_list = [enc_coords] if isinstance(enc_coords, EncoderCoords) else enc_coords

        mixer_maps.append(MixerMidiMapping(
            midi_coords=coords_list,
            controller_type=type,
            api_function=api_name,
            track_info=mapping.track,
            encoder_coords=encoder_coors_list[0]))

    return MixerWithMidi(midi_maps=mixer_maps)
