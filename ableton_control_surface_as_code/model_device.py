import itertools
import re
from dataclasses import dataclass
from typing import Literal, List, Optional, Dict, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, RowMapV2_1, parse_coords, RangeV2, parse_multiple_coords
from ableton_control_surface_as_code.encoder_coords import EncoderCoords


MODE_SLOT_NAMES = [f"switch{i}" for i in range(1, 9)]


@dataclass
class HudCell:
    grid_row: int
    grid_col: int
    kind: str       # 'dial' or 'button'
    count: int
    start_index: int


def is_mode_slot(name: str) -> bool:
    return name in MODE_SLOT_NAMES


def parse_slot_token(token: str) -> str:
    token = token.strip()
    if token.startswith("slot") and token[4:].isdigit():
        return token
    if token in MODE_SLOT_NAMES:
        return token
    if token.isdigit():
        n = int(token)
        if n < 1:
            raise ValueError(f"Slot index {n} out of range; must be >= 1")
        return f"slot{n}"
    raise ValueError(f"Unknown slot token: {token!r}")


def parse_continuous_slot_list(raw: str) -> List[str]:
    result: List[str] = []
    for chunk in [c.strip() for c in raw.split(",") if c.strip()]:
        if "-" in chunk and not chunk.startswith("slot"):
            lo_s, hi_s = chunk.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo > hi:
                raise ValueError(f"Invalid slot range {chunk!r}: {lo} > {hi}")
            result.extend(parse_slot_token(str(n)) for n in range(lo, hi + 1))
        else:
            result.append(parse_slot_token(chunk))

    bad = [s for s in result if s in MODE_SLOT_NAMES]
    if bad:
        raise ValueError(
            f"{bad} are cycle-type slots and cannot appear under encoders.slots; "
            "place them under mode-buttons instead"
        )
    return result


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


class ModeButtonEntry(BaseModel):
    coord: EncoderCoords
    slot: _SWITCH_LITERAL

    @field_validator('coord', mode='before')
    @classmethod
    def _parse_coord(cls, value):
        return parse_coords(value)


class ModeButtonMidiMapping(BaseModel):
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
    mode_button_maps: List[ModeButtonMidiMapping] = Field(default_factory=list)
    # encoder_index -> slot_name; populated when user wrote `slots:` in their mapping.
    slot_assignments: List[Tuple[int, str]] = Field(default_factory=list)
    encoder_slot_count: int = 8
    hud_cells: List[HudCell] = Field(default_factory=list)


class DeviceEncoderMappings(BaseModel):
    encoders: Optional[RowMapV2_1] = Field(None, alias='encoders')
    encoder_list: List[RowMapV2_1] = Field([], alias='encoder-list')
    on_off: Optional[EncoderCoords] = Field(None, alias='on-off')
    mode_buttons: List[ModeButtonEntry] = Field(default_factory=list, alias='mode-buttons')
    switch1: Optional[EncoderCoords] = Field(None, alias='switch1')
    switch2: Optional[EncoderCoords] = Field(None, alias='switch2')
    switch3: Optional[EncoderCoords] = Field(None, alias='switch3')
    switch4: Optional[EncoderCoords] = Field(None, alias='switch4')
    switch5: Optional[EncoderCoords] = Field(None, alias='switch5')
    switch6: Optional[EncoderCoords] = Field(None, alias='switch6')
    switch7: Optional[EncoderCoords] = Field(None, alias='switch7')
    switch8: Optional[EncoderCoords] = Field(None, alias='switch8')
    switch_list: List[SwitchListEntry] = Field(default_factory=list, alias='switch-list')

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

    mode_button_maps: List[ModeButtonMidiMapping] = []
    for entry in device.mappings.mode_buttons:
        midi_coord = controller.build_midi_coords(entry.coord)[0][0]
        mode_button_maps.append(ModeButtonMidiMapping(
            midi_coords=midi_coord,
            slot=entry.slot,
        ))
    for slot_name, coord in device.mappings.switch_entries():
        if coord is not None:
            midi_coord = controller.build_midi_coords(coord)[0][0]
            mode_button_maps.append(ModeButtonMidiMapping(
                midi_coords=midi_coord,
                slot=slot_name,
            ))
    if device.mappings.switch_list:
        switch_index = 1
        for entry in device.mappings.switch_list:
            for ec in entry.encoder_coords_list:
                midis, _ = controller.build_midi_coords(ec)
                for midi_coord in midis:
                    mode_button_maps.append(ModeButtonMidiMapping(
                        midi_coords=midi_coord,
                        slot=f"switch{switch_index}",
                    ))
                    switch_index += 1

    slot_groups = [e for e in device.mappings.encoders_all() if e.uses_slots]
    total_slots = sum(len(e.slots) for e in slot_groups)
    encoder_slot_count = total_slots if total_slots > 0 else 8

    # Build HUD grid cells from slot groups
    hud_cells: List[HudCell] = []
    dial_start = 0
    for e in slot_groups:
        m = re.match(r'row-(\d+)', e.range_raw)
        row_num = int(m.group(1)) if m else 1
        gr, gc = controller.grid_position_for(row_num)
        count = len(e.slots)
        hud_cells.append(HudCell(grid_row=gr, grid_col=gc, kind='dial', count=count, start_index=dial_start))
        dial_start += count

    switch_maps = [m for m in mode_button_maps if m.slot.startswith('switch')]
    if switch_maps:
        switch_row = None
        for slot_name, coord in device.mappings.switch_entries():
            if coord is not None and slot_name.startswith('switch'):
                switch_row = int(coord.row)
                break
        if switch_row is None and device.mappings.switch_list:
            m = re.match(r'row-(\d+)', device.mappings.switch_list[0].range_raw)
            if m:
                switch_row = int(m.group(1))
        if switch_row is not None:
            gr, gc = controller.grid_position_for(switch_row)
            hud_cells.append(HudCell(grid_row=gr, grid_col=gc, kind='button', count=len(switch_maps), start_index=0))

    return DeviceWithMidi(
        track=device.track,
        device=device.device,
        midi_maps=midi_maps,
        mode_button_maps=mode_button_maps,
        slot_assignments=slot_assignments,
        encoder_slot_count=encoder_slot_count,
        hud_cells=hud_cells,
    )
