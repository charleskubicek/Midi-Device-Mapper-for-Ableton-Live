import itertools
from typing import Literal, List, Optional, Dict, Tuple

from pydantic import BaseModel, Field, field_validator

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, RowMapV2_1, parse_coords, RangeV2
from ableton_control_surface_as_code.encoder_coords import EncoderCoords
from ableton_control_surface_as_code.family_intents import (
    parse_slot_token,
    is_mode_slot,
    MODE_SLOT_NAMES,
)


class DeviceParameterMidiMapping(BaseModel):
    midi_coords: List[MidiCoords]
    parameter: int
    slot: Optional[str] = None  # set when this mapping was driven by a `slots:` list

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords[0]

    def short_info_string(self):
        if self.slot:
            return f"{self.slot}"
        return f"p {self.parameter}"

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        suffix = self.slot if self.slot else f"p{self.parameter}"
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_{suffix}")


class DeviceParameterPageNav(BaseModel):
    inc: EncoderCoords
    dec: EncoderCoords
    export_to_mode: str = Field(alias='export-to-mode')

    @field_validator('dec', mode='before')
    @classmethod
    def parameter_paging_dec(cls, value):
        return parse_coords(value) if value is not None else None

    @field_validator('inc', mode='before')
    @classmethod
    def parameter_paging_inc(cls, value):
        return parse_coords(value) if value is not None else None


class DeviceParameterPageNavMidi(BaseModel):
    inc: MidiCoords
    dec: MidiCoords
    export_to_mode: str = Optional[str]


class ModeButtonEntry(BaseModel):
    coord: EncoderCoords
    slot: Literal['mode', 'modMode']

    @field_validator('coord', mode='before')
    @classmethod
    def _parse_coord(cls, value):
        return parse_coords(value)


class ModeButtonMidiMapping(BaseModel):
    midi_coords: MidiCoords
    slot: str  # 'mode' or 'modMode'

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords

    def short_info_string(self):
        return f"{self.slot}-cycle"

    def info_string(self):
        return f"ch{self.midi_coords.channel}_no{self.midi_coords.number}_{self.midi_coords.type.value}__{self.short_info_string()}"

    def controller_variable_name(self):
        return self.midi_coords.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.midi_coords.controller_listener_fn_name(f"_mode_{mode_name}_{self.slot}")


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_maps: List[DeviceParameterMidiMapping]
    mode_button_maps: List[ModeButtonMidiMapping] = Field(default_factory=list)
    # encoder_index -> slot_name; populated when user wrote `slots:` in their mapping.
    slot_assignments: List[Tuple[int, str]] = Field(default_factory=list)
    parameter_page_nav: Optional[DeviceParameterPageNavMidi] = None

    @property
    def has_paging_export(self):
        return self.parameter_page_nav is not None and self.parameter_page_nav.export_to_mode is not None


class DeviceEncoderMappings(BaseModel):
    encoders: Optional[RowMapV2_1] = Field(None, alias='encoders')
    encoder_list: List[RowMapV2_1] = Field([], alias='encoder-list')
    on_off: Optional[EncoderCoords] = Field(None, alias='on-off')
    mode_buttons: List[ModeButtonEntry] = Field(default_factory=list, alias='mode-buttons')
    parameter_paging: Optional[DeviceParameterPageNav] = Field(None, alias='parameter-paging')

    def encoders_all(self) -> List[RowMapV2_1]:
        if self.encoders is None:
            return self.encoder_list
        else:
            return [self.encoders] + self.encoder_list

    @field_validator('on_off', mode='before')
    @classmethod
    def parse_on_off(cls, value):
        return parse_coords(value) if value is not None else None


class DeviceV2(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    mappings: DeviceEncoderMappings

    @field_validator("track", mode='before')
    @classmethod
    def parse_track(cls, value):
        return TrackInfo.parse_track(value)


def build_device_model_v2_1(controller, device: DeviceV2, root_dir) -> DeviceWithMidi:
    midi_maps: List[DeviceParameterMidiMapping] = []
    slot_assignments: List[Tuple[int, str]] = []
    parameter_page_nav = None

    encoder_index = 0
    for encoders in device.mappings.encoders_all():
        if encoders.uses_slots:
            slot_list = encoders.slots
            for mcs in encoders.multi_encoder_coords:
                midis, _ = controller.build_midi_coords(mcs)
                if len(midis) != len(slot_list):
                    print(
                        f"Length of midis ({len(midis)}) and slots ({len(slot_list)}) don't match"
                    )
                for m, slot in zip(midis, slot_list):
                    encoder_index += 1
                    midi_maps.append(DeviceParameterMidiMapping(
                        midi_coords=[m],
                        parameter=encoder_index,
                        slot=slot,
                    ))
                    slot_assignments.append((encoder_index, slot))
        else:
            param_list = encoders.parameters.as_inclusive_list()
            iterator, _ = itertools.tee(param_list)
            for mcs in encoders.multi_encoder_coords:
                midis, _ = controller.build_midi_coords(mcs)
                if len(midis) != len(param_list):
                    print(
                        f"Length of midis ({len(midis)}) and parameters ({len(param_list)}) don't match"
                    )
                for m, p in zip(midis, iterator):
                    midi_maps.append(DeviceParameterMidiMapping(
                        midi_coords=[m],
                        parameter=p,
                    ))

    if device.mappings.on_off:
        midi_maps.append(DeviceParameterMidiMapping(
            midi_coords=controller.build_midi_coords(device.mappings.on_off)[0],
            parameter=0,
        ))

    if device.mappings.parameter_paging is not None:
        parameter_page_nav = DeviceParameterPageNavMidi(
            inc=controller.build_midi_coords(device.mappings.parameter_paging.inc)[0][0],
            dec=controller.build_midi_coords(device.mappings.parameter_paging.dec)[0][0],
            export_to_mode=device.mappings.parameter_paging.export_to_mode,
        )

    mode_button_maps: List[ModeButtonMidiMapping] = []
    for entry in device.mappings.mode_buttons:
        midi_coord = controller.build_midi_coords(entry.coord)[0][0]
        mode_button_maps.append(ModeButtonMidiMapping(
            midi_coords=midi_coord,
            slot=entry.slot,
        ))

    return DeviceWithMidi(
        track=device.track,
        device=device.device,
        midi_maps=midi_maps,
        mode_button_maps=mode_button_maps,
        slot_assignments=slot_assignments,
        parameter_page_nav=parameter_page_nav,
    )
