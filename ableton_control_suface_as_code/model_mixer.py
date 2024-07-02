from typing import Optional, Literal, Self

from pydantic import BaseModel, Field, model_validator

from ableton_control_suface_as_code.core_model import parse_coords, TrackInfo, NamedTrack, MixerMidiMapping, \
    MixerWithMidi


class MixerMappingsV2(BaseModel):
    volume_raw: Optional[str] = Field(default=None, alias="volume")
    pan_raw: Optional[str] = Field(default=None, alias="pan")
    mute_raw: Optional[str] = Field(default=None, alias="mute")
    solo_raw: Optional[str] = Field(default=None, alias="solo")
    arm_raw: Optional[str] = Field(default=None, alias="arm")
    sends_raw: Optional[str] = Field(default=None, alias="sends")

    @model_validator(mode='after')
    def verify_correct_ranges(self) -> Self:
        single_controllers = ['volume', 'pan', 'mute', 'solo', 'arm']

        d = self.as_parsed_dict()
        for sc in single_controllers:
            if sc in d and '-' in d[sc]:
                raise ValueError(f"{sc} can't have a range value")

        return self

    def as_parsed_dict(self):
        return {key.removesuffix('_raw'): parse_coords(value) for key, value in self.model_dump().items() if
                value is not None}


class MixerV2(BaseModel):
    type: Literal['mixer'] = "mixer"
    track_raw: str = Field(alias='track')
    mappings: MixerMappingsV2

    # def __init__(self, track:str, mappings: MixerMappingsV2):
    #     super().__init__(track_raw=track, mappings=mappings)

    @property
    def track_info(self) -> TrackInfo:
        if self.track_raw == "selected":
            return TrackInfo(name=NamedTrack.selected)
        if self.track_raw == "master":
            return TrackInfo(name=NamedTrack.master)
        else:
            exit(1)


def build_mixer_model_v2(controller, mapping: MixerV2):
    mixer_maps = []
    for api_name, enc_coords in mapping.mappings.as_parsed_dict().items():
        coords_list, type = controller.build_midi_coords(enc_coords)

        mixer_maps.append(MixerMidiMapping(
            midi_coords=coords_list,
            controller_type=type,
            api_function=api_name,
            track_info=mapping.track_info,
            encoder_coords=enc_coords))

    for m in mixer_maps:
        coords_ = [(x.channel, x.channel, x.type.name) for x in m.midi_coords]
        row_info = f"row:{m.encoder_coords.row}-{m.encoder_coords.row_range_end}"
        print("mixer: ", coords_, m.api_function, row_info, f"col:{m.encoder_coords.col}")

    return MixerWithMidi(midi_maps=mixer_maps)
