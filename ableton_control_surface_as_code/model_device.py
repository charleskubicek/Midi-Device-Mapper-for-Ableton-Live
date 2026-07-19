from typing import Literal, List, Optional, Dict, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from ableton_control_surface_as_code.core_model import MidiCoords, TrackInfo, RowMapV2_1, parse_coords, RangeV2, parse_multiple_coords, ButtonBehaviour
from ableton_control_surface_as_code.encoder_coords import EncoderCoords
from ableton_control_surface_as_code.gen_error import GenError, ErrorCode

# One bar of sixteenths — the drum sequencer edits only bar 1 at this resolution.
STEPS_PER_BAR = 16
# Re-exported for backwards compatibility; these now live in the leaf `slots`
# module so `core_model` can use them without importing this model module.
from ableton_control_surface_as_code.slots import (  # noqa: F401
    SWITCH_SLOT_NAMES, is_switch_slot, parse_slot_token, parse_continuous_slot_list,
    parse_button_slot_list,
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


class SwitchMidiMapping(BaseModel):
    midi_coords: MidiCoords
    slot: int  # 1-based device switch-slot index

    @property
    def only_midi_coord(self) -> MidiCoords:
        return self.midi_coords

    def short_info_string(self):
        return f"button{self.slot}-cycle"

    def info_string(self):
        return f"ch{self.midi_coords.channel}_no{self.midi_coords.number}_{self.midi_coords.type.value}__{self.short_info_string()}"

    def controller_variable_name(self):
        return self.midi_coords.controller_variable_name()

    def controller_listener_fn_name(self, mode_name):
        return self.midi_coords.controller_listener_fn_name(f"_mode_{mode_name}_button{self.slot}")


class ButtonRowMap(BaseModel):
    """`button:` / `button-list:` entry — mirrors `RowMapV2_1` but for device
    switch (button) slots: a `range` of controller coords paired with a
    `slots` list of 1-based device switch-slot integers, one per control."""
    range_raw: str = Field(alias='range')
    slots_raw: str = Field(alias='slots')

    @property
    def multi_encoder_coords(self) -> List[EncoderCoords]:
        return parse_multiple_coords(self.range_raw)

    @property
    def button_slots(self) -> List[int]:
        return parse_button_slot_list(self.slots_raw)


class DrumRangeMap(BaseModel):
    """A `pads:` / `sequencer:` / `velocities:` block — just a `range:`. The
    pad/step index is implied by position within the range (0-based), so unlike
    an `encoders:` block there is no `parameters:`/`slots:` list. These blocks
    are inert unless the focused device is a drum rack; see
    `ai-coding/plans/drum_rack.md`."""
    range_raw: str = Field(alias='range')

    class Config:
        extra = 'forbid'

    @property
    def multi_encoder_coords(self) -> List[EncoderCoords]:
        return parse_multiple_coords(self.range_raw)


class DrumPadMidiMapping(BaseModel):
    """One pad button -> its 0-based position in the visible 4x4 bank."""
    midi_coords: MidiCoords
    index: int


class DrumStepMidiMapping(BaseModel):
    """One sequencer button -> the 0-based step it toggles."""
    midi_coords: MidiCoords
    step: int


class DrumVelocityMidiMapping(BaseModel):
    """One velocity encoder -> the 0-based step whose note velocity it sets."""
    midi_coords: MidiCoords
    step: int


class DeviceWithMidi(BaseModel):
    type: Literal['device'] = 'device'
    track: TrackInfo
    device: str
    midi_maps: List[DeviceParameterMidiMapping]
    switch_maps: List[SwitchMidiMapping] = Field(default_factory=list)
    # encoder_index -> slot_name; populated when user wrote `slots:` in their mapping.
    slot_assignments: List[Tuple[int, str]] = Field(default_factory=list)
    encoder_slot_count: int = 8
    # Drum-rack roles (inert unless the focused device is a drum rack). A control
    # may also carry a macro/switch role above; codegen resolves the overlap into
    # a single dispatching listener (drum wins on a drum rack).
    pad_maps: List[DrumPadMidiMapping] = Field(default_factory=list)
    step_maps: List[DrumStepMidiMapping] = Field(default_factory=list)
    velocity_maps: List[DrumVelocityMidiMapping] = Field(default_factory=list)


class DeviceEncoderMappings(BaseModel):
    encoders: Optional[RowMapV2_1] = Field(None, alias='encoders')
    encoder_list: List[RowMapV2_1] = Field([], alias='encoder-list')
    on_off: Optional[EncoderCoords] = Field(None, alias='on-off')
    button: Optional[ButtonRowMap] = Field(None, alias='button')
    button_list: List[ButtonRowMap] = Field([], alias='button-list')
    # Drum-rack blocks (inert unless the focused device is a drum rack).
    pads: Optional[DrumRangeMap] = None
    sequencer: Optional[DrumRangeMap] = None
    velocities: Optional[DrumRangeMap] = None

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
                        "'encoders:' (or 'encoder-list:'/'button:'/'button-list:') "
                        "block, not directly under 'mappings:'.")
            raise ValueError(
                f"Unknown device mapping key(s): {unknown}. Valid keys: "
                f"encoders, encoder-list, on-off, button, button-list, "
                f"pads, sequencer, velocities.{hint}")
        return data

    def encoders_all(self) -> List[RowMapV2_1]:
        if self.encoders is None:
            return self.encoder_list
        else:
            return [self.encoders] + self.encoder_list

    def buttons_all(self) -> List[ButtonRowMap]:
        if self.button is None:
            return self.button_list
        else:
            return [self.button] + self.button_list

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
    for buttons in device.mappings.buttons_all():
        slot_list = buttons.button_slots
        for ec in buttons.multi_encoder_coords:
            midis, _ = controller.build_midi_coords(ec)
            # Per-group, like the encoder slots branch: the slot list restarts
            # for each coord-group, so each group must match the slot count
            # on its own.
            if len(midis) != len(slot_list):
                raise GenError(
                    f"device mapping for '{device.device}': the button range "
                    f"covers {len(midis)} control(s) but {len(slot_list)} slot(s) "
                    f"were listed — these counts must match",
                    ErrorCode.SEMANTIC_VALIDATION,
                )
            for midi_coord, slot in zip(midis, slot_list):
                switch_maps.append(SwitchMidiMapping(
                    midi_coords=midi_coord,
                    slot=slot,
                ))

    slot_groups = [e for e in device.mappings.encoders_all() if e.uses_slots]
    total_slots = sum(len(e.slots) for e in slot_groups)
    encoder_slot_count = total_slots if total_slots > 0 else 8

    pad_maps, step_maps, velocity_maps = _build_drum_maps(controller, device)

    return DeviceWithMidi(
        track=device.track,
        device=device.device,
        midi_maps=midi_maps,
        switch_maps=switch_maps,
        slot_assignments=slot_assignments,
        encoder_slot_count=encoder_slot_count,
        pad_maps=pad_maps,
        step_maps=step_maps,
        velocity_maps=velocity_maps,
    )


def _resolve_drum_range(controller, range_map: DrumRangeMap) -> List[MidiCoords]:
    all_midis: List[MidiCoords] = []
    for ec in range_map.multi_encoder_coords:
        midis, _ = controller.build_midi_coords(ec)
        all_midis.extend(midis)
    return all_midis


def _validate_drum_count(name: str, midis: List[MidiCoords], allowed: set):
    if len(midis) not in allowed:
        allowed_str = " or ".join(str(a) for a in sorted(allowed))
        raise GenError(
            f"device drum '{name}' range covers {len(midis)} control(s) but must "
            f"cover exactly {allowed_str}",
            ErrorCode.SEMANTIC_VALIDATION,
        )


def _validate_drum_type(name: str, midis: List[MidiCoords], want_button: bool):
    want = "button" if want_button else "knob/slider"
    for mc in midis:
        if want_button != mc.encoder_type.is_button():
            got = "button" if mc.encoder_type.is_button() else mc.encoder_type.value
            raise GenError(
                f"device drum '{name}' range must be {want}-type controls but "
                f"resolves to a {got} control (ch{mc.channel} no{mc.number})",
                ErrorCode.SEMANTIC_VALIDATION,
            )


def _build_drum_maps(controller, device: 'DeviceV2'):
    """Build the optional drum-rack roles (pads/sequencer/velocities). Each takes
    just a range; the pad/step index is the 0-based position within it. These are
    inert at runtime unless the focused device is a drum rack."""
    pad_maps: List[DrumPadMidiMapping] = []
    if device.mappings.pads is not None:
        midis = _resolve_drum_range(controller, device.mappings.pads)
        _validate_drum_count('pads', midis, {16})
        _validate_drum_type('pads', midis, want_button=True)
        pad_maps = [DrumPadMidiMapping(midi_coords=mc, index=i) for i, mc in enumerate(midis)]

    step_maps: List[DrumStepMidiMapping] = []
    if device.mappings.sequencer is not None:
        # Toggle hardware emits an alternating 127/0 per press, so a step would
        # only toggle on every second physical tap — the step sequencer needs one
        # clean edge per tap, i.e. momentary buttons. Flag it at gen time rather
        # than shipping a surface that silently misbehaves.
        if controller.button_behaviour == ButtonBehaviour.toggle:
            raise GenError(
                "device 'sequencer' requires momentary buttons (each tap must send "
                "one clean edge), but the controller declares button-behaviour: "
                "toggle, which alternates 127/0 so only every second tap would "
                "register. Use a momentary controller, or remove the sequencer block.",
                ErrorCode.SEMANTIC_VALIDATION,
            )
        midis = _resolve_drum_range(controller, device.mappings.sequencer)
        _validate_drum_count('sequencer', midis, {8, 16})
        _validate_drum_type('sequencer', midis, want_button=True)
        step_maps = [DrumStepMidiMapping(midi_coords=mc, step=i) for i, mc in enumerate(midis)]

    velocity_maps: List[DrumVelocityMidiMapping] = []
    if device.mappings.velocities is not None:
        midis = _resolve_drum_range(controller, device.mappings.velocities)
        _validate_drum_count('velocities', midis, {8, 16})
        _validate_drum_type('velocities', midis, want_button=False)
        velocity_maps = [DrumVelocityMidiMapping(midi_coords=mc, step=i) for i, mc in enumerate(midis)]

    return pad_maps, step_maps, velocity_maps
