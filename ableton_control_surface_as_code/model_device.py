import itertools
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, List, Optional, Dict, Any

from pydantic import BaseModel, Field, validator, field_validator
from nestedtext import nestedtext as nt

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, NamedTrack, RowMapV2_1, parse_coords, \
    RangeV2
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


class DeviceParameterMidiMapping(BaseModel):
    midi_coords: List[MidiCoords]
    parameter: int

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


@dataclass
class CustomDeviceParameter:
    name: str
    alias: Optional[str] = None
    button: Optional[str] = None

    def alias_str(self):
        return self.name if self.alias is None else self.alias

    @classmethod
    def parse(cls, raw_str):
        '''
        parse name and alias from a string in the form Ve Attack; alias=Attack;
        :param raw_str:
        :return:
        '''
        if ';' not in raw_str:
            return cls(raw_str, None)
        else:
            # Extract name (before the semicolon)
            name_part, *rest = raw_str.split(";", 1)
            name = name_part.strip()

            # Extract alias using regex
            alias_match = re.search(r"alias=([^;]+)", raw_str)
            alias = alias_match.group(1).strip() if alias_match else None

            # Extract toggle using regex
            button_match = re.search(r"button=([^;]+)", raw_str)
            button = button_match.group(1).strip() if button_match else None

            return cls(name=name, alias=alias, button=button)


class DeviceCustomParameterMidiMapping(BaseModel):
    index: int
    device_parameter: CustomDeviceParameter

    @property
    def non_zeroed_index(self):
        return self.index + 1


class DeviceCustomParameterGroupMidiMapping(BaseModel):
    name: str
    parameters: list[DeviceCustomParameterMidiMapping]


class DeviceNamedCustomParameterMidiMapping(BaseModel):
    midi_coords: MidiCoords
    device_parameter: CustomDeviceParameter

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords

    def short_info_string(self):
        return f"midi {self.midi_coords.info_string()}"

    def info_string(self):
        return f"ch{self.only_midi_coord.channel}_no{self.only_midi_coord.number}_{self.only_midi_coord.type.value}__{self.short_info_string()}"

    def controller_variable_name(self):
        return self.only_midi_coord.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.only_midi_coord.controller_listener_fn_name(f"_mode_{mode_name}_p{self.midi_coords.info_string()}")


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_maps: List[DeviceParameterMidiMapping]
    custom_device_mappings: Dict[str, List[DeviceCustomParameterMidiMapping]] = Field({})
    custom_parameter_groups: Dict[str, List[DeviceCustomParameterGroupMidiMapping]] = Field({})
    group_name_to_range: Dict[str, RangeV2] = Field({})
    parameter_page_nav: Optional[DeviceParameterPageNavMidi]

    @property
    def has_paging_export(self):
        return self.parameter_page_nav is not None and self.parameter_page_nav.export_to_mode is not None


class DeviceEncoderMappings(BaseModel):
    encoders: RowMapV2_1 = Field(None, alias='encoders')
    encoder_list: List[RowMapV2_1] = Field([], alias='encoder-list')
    on_off: Optional[EncoderCoords] = Field(None, alias='on-off')
    parameter_paging: Optional[DeviceParameterPageNav] = Field(None, alias='parameter-paging')

    def encoders_all(self):
        if self.encoders is None:
            return self.encoder_list
        else:
            return [self.encoders] + self.encoder_list

    ## TODO assert encoders or encoder_list

    @field_validator('on_off', mode='before')
    @classmethod
    def parse_on_off(cls, value):
        return parse_coords(value) if value is not None else None


class CustomParameterGroup(BaseModel):
    name: str
    parameters: list[CustomDeviceParameter]

    @field_validator("parameters", mode="before")
    @classmethod
    def parse_parameters(cls, value: List[str]):
        return [CustomDeviceParameter.parse(item) for item in value]


class CustomParameterMapping(BaseModel):
    device_name: str = Field(alias='device-name')
    exclusive: Optional[bool] = Field(default=False)
    parameter_mappings_raw: list[str] = Field(alias='parameters', default=[])
    named_parameter_mappings_raw: dict[str, str] = Field(alias='parameters-map', default={})
    parameter_mappings_group: list[CustomParameterGroup] = Field(alias='parameter-groups', default=[])

    # TODO verify either parameter_mappings_raw or named_parameter_mappings_raw is empty


class CustomParameterMappings(BaseModel):
    custom_parameter_mappings: list[CustomParameterMapping] = Field(alias='custom-parameter-mappings')


class DeviceV2(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    mappings: DeviceEncoderMappings
    custom_parameter_mappings: Optional[list[CustomParameterMapping]] = Field([], alias='custom-parameter-mappings')
    custom_parameter_mappings_file: Optional[str] = Field(None, alias='parameter-mappings-file')

    @field_validator("track", mode='before')
    @classmethod
    def parse_track(cls, value):
        return TrackInfo.parse_track(value)


def build_device_model_v2_1(controller, device: DeviceV2, root_dir) -> DeviceWithMidi:
    midi_maps = []
    custom_param_maps = {}
    custom_param_maps_2 = {}
    custom_param_groups = {}
    parameter_page_nav = None
    group_name_to_row = {}  # TODO support multiple rows per group

    for encoders in device.mappings.encoders_all():
        param_list = encoders.parameters.as_inclusive_list()
        iterator, _ = itertools.tee(param_list)

        # group_name_to_row[encoders.name] = int(encoders.range_raw.split(':')[0].split('-')[1])
        group_name_to_row[encoders.name] = encoders.parameters

        for mcs in encoders.multi_encoder_coords:
            midis, _ = controller.build_midi_coords(mcs)

            if len(midis) != len(param_list):
                print(f"Length of midis ({len(midis)}) and parameters ({len(param_list)}) don't match")

            for m, p in zip(midis, iterator):
                midi_maps.append(DeviceParameterMidiMapping(
                    midi_coords=[m],
                    parameter=p
                ))

    if device.mappings.on_off:
        midi_maps.append(DeviceParameterMidiMapping(
            midi_coords=controller.build_midi_coords(device.mappings.on_off)[0],
            parameter=0
        ))

    if device.mappings.parameter_paging is not None:
        parameter_page_nav = DeviceParameterPageNavMidi(
            inc=controller.build_midi_coords(device.mappings.parameter_paging.inc)[0][0],
            dec=controller.build_midi_coords(device.mappings.parameter_paging.dec)[0][0],
            export_to_mode=device.mappings.parameter_paging.export_to_mode)

    if device.custom_parameter_mappings_file is not None:
        data = nt.load(Path(root_dir) / device.custom_parameter_mappings_file)
        custom_mappings = CustomParameterMappings(**data).custom_parameter_mappings
    else:
        custom_mappings = device.custom_parameter_mappings if device.custom_parameter_mappings is not None else []

    for mapping in custom_mappings:
        device_name = mapping.device_name
        custom_param_groups[device_name] = []

        parsed_coords = [DeviceCustomParameterMidiMapping(
            index=p_no,
            device_parameter=CustomDeviceParameter.parse(p_name))
            for p_no, p_name in enumerate(mapping.parameter_mappings_raw)]

        parsed_custom_coords = [DeviceNamedCustomParameterMidiMapping(
            midi_coords=controller.build_midi_coords(parse_coords(midi_map))[0][0],
            device_parameter=CustomDeviceParameter.parse(p_name))
            for p_name, midi_map in mapping.named_parameter_mappings_raw.items()]

        for group in mapping.parameter_mappings_group:
            name = group.name

            custom_param_group = [DeviceCustomParameterMidiMapping(
                index=i,
                device_parameter=param)
                for i, param in enumerate(group.parameters)]

            group = DeviceCustomParameterGroupMidiMapping(
                name=name,
                parameters=custom_param_group)

            device_group = custom_param_groups.get(device_name, [])
            device_group.append(group)
            custom_param_groups[device_name] = device_group

        custom_param_maps[device_name] = parsed_coords
        custom_param_maps_2[device_name] = parsed_custom_coords

    return DeviceWithMidi(
        track=device.track,
        device=device.device,
        midi_maps=midi_maps,
        custom_device_mappings=custom_param_maps,
        custom_parameter_groups=custom_param_groups,
        group_name_to_range=group_name_to_row,
        parameter_page_nav=parameter_page_nav)
