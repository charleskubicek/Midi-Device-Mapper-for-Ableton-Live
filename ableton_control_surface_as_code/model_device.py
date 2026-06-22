from typing import Literal, List, Optional, Dict, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, RowMapV2_1, parse_coords, RangeV2, parse_multiple_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords
from ableton_control_surface_as_code.gen_error import GenError, ErrorCode
# Re-exported for backwards compatibility; these now live in the leaf `slots`
# module so `core_model` can use them without importing this model module.
from ableton_control_surface_as_code.slots import (  # noqa: F401
    SWITCH_SLOT_NAMES, is_switch_slot, parse_slot_token, parse_continuous_slot_list,
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


_SWITCH_LITERAL = Literal['switch1', 'switch2', 'switch3', 'switch4',
                           'switch5', 'switch6', 'switch7', 'switch8']


class SwitchEntry(BaseModel):
    coord: EncoderCoords
    slot: _SWITCH_LITERAL

    @field_validator('coord', mode='before')
    @classmethod
    def _parse_coord(cls, value):
        return parse_coords(value)


class SwitchMidiMapping(BaseModel):
    midi_coords: MidiCoords
    slot: str  # 'switch1' or 'switch2'

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


class SwitchListEntry(BaseModel):
    range_raw: str = Field(alias='range')

    @property
    def encoder_coords_list(self) -> List[EncoderCoords]:
        return parse_multiple_coords(self.range_raw)


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_maps: List[DeviceParameterMidiMapping]
    switch_maps: List[SwitchMidiMapping] = Field(default_factory=list)
    # encoder_index -> slot_name; populated when user wrote `slots:` in their mapping.
    slot_assignments: List[Tuple[int, str]] = Field(default_factory=list)
    encoder_slot_count: int = 8


class DeviceEncoderMappings(BaseModel):
    encoders: Optional[RowMapV2_1] = Field(None, alias='encoders')
    encoder_list: List[RowMapV2_1] = Field([], alias='encoder-list')
    on_off: Optional[EncoderCoords] = Field(None, alias='on-off')
    mode_buttons: List[SwitchEntry] = Field(default_factory=list, alias='mode-buttons')
    switch1: Optional[EncoderCoords] = Field(None, alias='switch1')
    switch2: Optional[EncoderCoords] = Field(None, alias='switch2')
    switch3: Optional[EncoderCoords] = Field(None, alias='switch3')
    switch4: Optional[EncoderCoords] = Field(None, alias='switch4')
    switch5: Optional[EncoderCoords] = Field(None, alias='switch5')
    switch6: Optional[EncoderCoords] = Field(None, alias='switch6')
    switch7: Optional[EncoderCoords] = Field(None, alias='switch7')
    switch8: Optional[EncoderCoords] = Field(None, alias='switch8')
    switch_list: List[SwitchListEntry] = Field(default_factory=list, alias='switch-list')

    @model_validator(mode='before')
    @classmethod
    def _reject_unknown_keys(cls, data):
        """Unknown keys under `mappings:` used to be silently ignored, so a
        misplaced control (e.g. `parameters:`/`slots:`, which belong *inside* an
        `encoders:` block) left those controls unmapped with no error. Reject
        them with a message that names the valid keys and the likely fix."""
        if not isinstance(data, dict):
            return data
        valid = set()
        for name, f in cls.model_fields.items():
            valid.add(name)
            if f.alias:
                valid.add(f.alias)
        unknown = [k for k in data if k not in valid]
        if unknown:
            row_map_keys = {'range', 'parameters', 'slots'}
            hint = ""
            if any(k in row_map_keys for k in unknown):
                hint = (" Note: 'range'/'parameters'/'slots' go *inside* an "
                        "'encoders:' (or 'encoder-list:') block, not directly "
                        "under 'mappings:'.")
            raise ValueError(
                f"Unknown device mapping key(s): {unknown}. Valid keys: "
                f"encoders, encoder-list, on-off, switch1-8, switch-list, "
                f"mode-buttons.{hint}")
        return data

    @field_validator('switch1', 'switch2', 'switch3', 'switch4',
                     'switch5', 'switch6', 'switch7', 'switch8', mode='before')
    @classmethod
    def parse_switch(cls, value):
        return parse_coords(value) if value is not None else None

    @model_validator(mode='after')
    def _no_mix_switch_list_and_explicit(self):
        if self.switch_list:
            explicit = [name for name, coord in self.switch_entries() if coord is not None]
            if explicit:
                raise ValueError(
                    f"Cannot mix 'switch-list' with explicit switch entries: {explicit}"
                )
        return self

    def switch_entries(self) -> List[Tuple[str, Optional[EncoderCoords]]]:
        return [(f"switch{i}", getattr(self, f"switch{i}")) for i in range(1, 9)]

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

    encoder_index = 0
    for encoders in device.mappings.encoders_all():
        if encoders.uses_slots:
            slot_list = encoders.slots
            for mcs in encoders.multi_encoder_coords:
                midis, _ = controller.build_midi_coords(mcs)
                # NOTE: per-group on purpose (unlike the parameters branch, which
                # compares totals): the slot list restarts for each coord-group,
                # so each group must match the slot count on its own.
                if len(midis) != len(slot_list):
                    raise GenError(
                        f"device mapping for '{device.device}': the encoder range "
                        f"covers {len(midis)} control(s) but {len(slot_list)} slot(s) "
                        f"were listed — these counts must match",
                        ErrorCode.SEMANTIC_VALIDATION,
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
            # A range may span several coord-groups (e.g. "row-1:2-5,row-2:2-5");
            # the parameter list is shared across the whole span, so compare the
            # TOTAL control count to the parameter count once, not per group.
            all_midis = []
            for mcs in encoders.multi_encoder_coords:
                midis, _ = controller.build_midi_coords(mcs)
                all_midis.extend(midis)
            if len(all_midis) != len(param_list):
                raise GenError(
                    f"device mapping for '{device.device}': the encoder range "
                    f"covers {len(all_midis)} control(s) but {len(param_list)} "
                    f"parameter(s) were listed — these counts must match",
                    ErrorCode.SEMANTIC_VALIDATION,
                )
            for m, p in zip(all_midis, param_list):
                midi_maps.append(DeviceParameterMidiMapping(
                    midi_coords=[m],
                    parameter=p,
                ))

    if device.mappings.on_off:
        midi_maps.append(DeviceParameterMidiMapping(
            midi_coords=controller.build_midi_coords(device.mappings.on_off)[0],
            parameter=0,
        ))

    switch_maps: List[SwitchMidiMapping] = []
    for entry in device.mappings.mode_buttons:
        midi_coord = controller.build_midi_coords(entry.coord)[0][0]
        switch_maps.append(SwitchMidiMapping(
            midi_coords=midi_coord,
            slot=entry.slot,
        ))
    for slot_name, coord in device.mappings.switch_entries():
        if coord is not None:
            midi_coord = controller.build_midi_coords(coord)[0][0]
            switch_maps.append(SwitchMidiMapping(
                midi_coords=midi_coord,
                slot=slot_name,
            ))
    if device.mappings.switch_list:
        switch_index = 1
        for entry in device.mappings.switch_list:
            for ec in entry.encoder_coords_list:
                midis, _ = controller.build_midi_coords(ec)
                for midi_coord in midis:
                    switch_maps.append(SwitchMidiMapping(
                        midi_coords=midi_coord,
                        slot=f"switch{switch_index}",
                    ))
                    switch_index += 1

    slot_groups = [e for e in device.mappings.encoders_all() if e.uses_slots]
    total_slots = sum(len(e.slots) for e in slot_groups)
    encoder_slot_count = total_slots if total_slots > 0 else 8

    return DeviceWithMidi(
        track=device.track,
        device=device.device,
        midi_maps=midi_maps,
        switch_maps=switch_maps,
        slot_assignments=slot_assignments,
        encoder_slot_count=encoder_slot_count,
    )
