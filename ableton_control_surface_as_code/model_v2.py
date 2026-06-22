from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union, List, Optional, Tuple, Annotated, get_args

from nestedtext import nestedtext as nt
from prettytable import PrettyTable
from pydantic import BaseModel, model_validator, Extra, Field, ValidationError

from ableton_control_surface_as_code.core_model import MixerWithMidi, MidiCoords, parse_coords, MidiType
from ableton_control_surface_as_code.gen_error import GenError, ErrorCode, ProblemAccumulator
from ableton_control_surface_as_code.model_controller import ControllerRawV2, ControllerV2, \
    validate_controller_semantics
from ableton_control_surface_as_code.model_device import DeviceWithMidi, DeviceV2, build_device_model_v2_1
from ableton_control_surface_as_code.model_device_nav import DeviceNav, DeviceNavWithMidi, build_device_nav_model_v2
from ableton_control_surface_as_code.model_functions import build_functions_model_v2, Functions, FunctionsWithMidi
from ableton_control_surface_as_code.model_mixer import MixerV2, build_mixer_model_v2
from ableton_control_surface_as_code.model_parameter_pager import (
    ParameterPagerV2, ParameterPagerWithMidi, build_parameter_pager_model_v2,
)
from ableton_control_surface_as_code.model_track_nav import TrackNav, TrackNavWithMidi, \
    build_track_nav_model_v2
from ableton_control_surface_as_code.model_transport import Transport, TransportWithMidi, build_transport_model
from ableton_control_surface_as_code.model_clip import Clip, ClipWithMidi, build_clip_model_v2

AllMappingTypes = List[Annotated[Union[
    MixerV2,
    DeviceV2,
    TrackNav,
    DeviceNav,
    Functions,
    Transport,
    ParameterPagerV2,
    Clip,
], Field(discriminator='type')]]

AllMappingWithMidiTypes = List[Union[
    DeviceWithMidi,
    MixerWithMidi,
    TrackNavWithMidi,
    DeviceNavWithMidi,
    FunctionsWithMidi,
    TransportWithMidi,
    ParameterPagerWithMidi,
    ClipWithMidi,
]]


@dataclass
class ModeData:
    name: str
    next: str
    is_shift: bool
    color: Optional[str]


class ModeType(str, Enum):
    Shift = 'shift'
    Switch = 'switch'


class HudMode(str, Enum):
    On = 'on'
    Off = 'off'
    DeviceOnly = 'device_only'


class HudTrigger(str, Enum):
    """When the HUD burst is allowed to fire. Orthogonal to HudMode (which is
    *content*): this is *when it shows*.
      - Selection: follows Live's selected device (the 1.5s poll) — the default.
      - ControllerNav: only a controller device-nav action shows the HUD;
        selection changes from the mouse / track-select stay silent."""
    Selection = 'selection'
    ControllerNav = 'controller-nav'


class ModeButton(BaseModel):
    button: str
    type: ModeType = ModeType.Switch
    on_color: Optional[str] = None


class ModeDef(BaseModel, frozen=True):
    name: str
    on_color: Optional[str] = None
    mappings: AllMappingTypes
    is_fake_wrapper_mode: bool = False

    @classmethod
    def empty_with_one_mode(cls, mappings: AllMappingTypes):
        return cls(name="fake_mode", on_color="0", mappings=mappings, is_fake_wrapper_mode=True)


class FeedbackSinkType(str, Enum):
    Ec4Text = 'ec4_text'


class FeedbackSinkDef(BaseModel, frozen=True):
    """A generic runtime feedback sink — an output target driven on device /
    mode / control-remap changes (e.g. the EC4 text readouts). The HUD has its
    own dedicated path; these are additional sinks listed under `feedback:`."""
    type: FeedbackSinkType

    class Config:
        extra = 'forbid'


class OutputSinkType(str, Enum):
    OSC = 'osc'


class OSCTarget(BaseModel):
    host: str
    port: int = 5005

    class Config:
        extra = 'forbid'


class OutputSinkDef(BaseModel):
    """A declared output sink — a target that receives parameter-update publishes."""
    type: OutputSinkType
    targets: List[OSCTarget] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


_LEGACY_OSC_OUTPUTS = [OutputSinkDef(type=OutputSinkType.OSC, targets=[
    OSCTarget(host='127.0.0.1'),
])]


class RootV2(BaseModel):
    controller: str
    mode_button: Optional[ModeButton]
    modes: List[ModeDef]
    ableton_dir: str
    remote_on: bool = Field(default=False)
    parameter_mappings_file: Optional[str] = None
    hud: HudMode = HudMode.On
    show_hud_on: HudTrigger = HudTrigger.ControllerNav
    feedback: List[FeedbackSinkDef] = Field(default_factory=list)
    outputs: List[OutputSinkDef] = Field(default_factory=list)

    class Config:
        extra = 'forbid'


class RootV2ModesOrModeless(BaseModel):
    controller: str
    mappings: AllMappingTypes = []
    mode_button: Optional[ModeButton] = Field(default=None, alias='mode-button')
    modes: Optional[List[ModeDef]] = None
    ableton_dir: str
    remote_on: bool = Field(default=False)
    parameter_mappings_file: Optional[str] = None
    hud: HudMode = HudMode.On
    show_hud_on: HudTrigger = Field(default=HudTrigger.ControllerNav, alias='show-hud-on')
    feedback: List[FeedbackSinkDef] = Field(default_factory=list)
    outputs: List[OutputSinkDef] = Field(default_factory=list)

    def buildRootV2(self):
        model_modes = [ModeDef.empty_with_one_mode(self.mappings)] if self.modes is None else self.modes

        # Back-compat: synthesise legacy OSC targets when remote_on: true and no
        # explicit outputs: list is provided.
        outputs = self.outputs
        if not outputs and self.remote_on:
            outputs = _LEGACY_OSC_OUTPUTS

        return RootV2(
            controller=self.controller,
            modes=model_modes,
            mode_button=self.mode_button,
            ableton_dir=self.ableton_dir,
            remote_on=self.remote_on,
            parameter_mappings_file=self.parameter_mappings_file,
            hud=self.hud,
            show_hud_on=self.show_hud_on,
            feedback=self.feedback,
            outputs=outputs,
        )


class ModeButtonWithMidi(BaseModel):
    on_colors: List[Tuple[str, Optional[int]]]
    button: MidiCoords
    type: ModeType = ModeType.Switch


class ModeGroupWithMidi(BaseModel):
    mappings: List[Tuple[str, AllMappingWithMidiTypes]]
    mode_button: Optional[ModeButtonWithMidi]

    def first_mode_name(self):
        return self.mappings[0][0]

    def is_shift(self):
        return self.mode_button is not None and self.mode_button.type == ModeType.Shift

    def has_modes(self):
        return len(self.mappings) > 1

    def fsm(self):
        if self.mode_button is not None:
            mode_names = [name for name, _ in self.mode_button.on_colors]
            colors = [str(clr) for _, clr in self.mode_button.on_colors]
            is_shift = self.is_shift()
        elif self.has_modes():
            # Headless FSM: a composition secondary declares modes but no
            # physical mode-button — its FSM is driven remotely (mode_link).
            # Derive the mode order from the mappings; there is no button to
            # colour and no local shift gesture to interpret.
            mode_names = [name for name, _ in self.mappings]
            colors = [str(None)] * len(mode_names)
            is_shift = False
        else:
            return []

        return [ModeData(
            name=name,
            next=mode_names[i + 1] if i + 1 < len(mode_names) else mode_names[0],
            is_shift=is_shift,
            color=colors[i],
        ) for i, name in enumerate(mode_names)]


def validate_mappings(mappings: AllMappingWithMidiTypes, mode_name: str = "", acc=None):
    seen = {}
    mode_prefix = f" in mode '{mode_name}'" if mode_name else ""
    for withMidi in mappings:
        for midi_maps in withMidi.midi_maps:
            mcs = midi_maps.midi_coords
            for mc in mcs:
                if mc.ch_num in seen:
                    (pmc, previous) = seen[mc.ch_num]
                    message = (
                        f"Clashing mappings{mode_prefix}: {withMidi.type} and {previous.type} both use chanel:{mc.channel} no:{mc.number} type:{mc.type.value}"
                        + f"\n from source 1: {mc.source_info}"
                        + f"\n from source 2: {pmc.source_info}")
                    if acc is not None:
                        acc.add(message)
                    else:
                        raise GenError(message, ErrorCode.CLASHING_MAPPINGS)
                else:
                    seen[mc.ch_num] = (mc, withMidi)


def print_model_with_mappings(model: ControllerV2, mappings):
    def key(mc: MidiCoords):
        return (mc.ch_num, mc.type.value, mc.channel)

    actions = {}

    for withMidi in mappings:
        for midi_map in withMidi.midi_maps:
            mcs = midi_map.midi_coords
            for mc in mcs:
                actions[key(mc)] = midi_map.short_info_string()

    def padded(f: MidiType):
        if f.is_note():
            return f" {f.value} "
        else:
            return f"  {f.value}  "

    for row in model.control_groups:
        print(f"Row {row.number}")
        table = PrettyTable(header=False)
        table.add_row(['Col '] + [i for i, _ in enumerate(row.midi_coords)])
        table.add_row(['Num '] + [col.number for col in row.midi_coords])
        table.add_row(['Type'] + [padded(col.type) for col in row.midi_coords])
        table.add_row(['Chan'] + [col.channel for col in row.midi_coords])
        table.add_row(['Actn'] + [actions.get(key(col), "-")[:10] for col in row.midi_coords])

        print(table)


def read_root_v2(root: RootV2, controller: ControllerV2, root_dir: Path, acc=None) -> ModeGroupWithMidi:
    mappings = [(mode_dev.name,
                 build_mappings_model_v2(mode_dev.mappings, controller, root_dir,
                                         mode_name=mode_dev.name, acc=acc))
                for mode_dev in root.modes]

    if root.mode_button is None:
        mode_button = None
    else:
        def _build_mode_button():
            return ModeButtonWithMidi(
                on_colors=[(mode_dev.name, controller.light_color_for(mode_dev.on_color)) for mode_dev in root.modes],
                button=controller.build_midi_coords(parse_coords(root.mode_button.button))[0][0],
                type=root.mode_button.type)
        mode_button = acc.capture(_build_mode_button) if acc is not None else _build_mode_button()

    return ModeGroupWithMidi(
        mappings=mappings,
        mode_button=mode_button
    )


_MAPPING_BUILDERS = {
    "device": lambda c, m, d: build_device_model_v2_1(c, m, d),
    "mixer": lambda c, m, d: build_mixer_model_v2(c, m),
    "track-nav": lambda c, m, d: build_track_nav_model_v2(c, m),
    "device-nav": lambda c, m, d: build_device_nav_model_v2(c, m),
    "functions": lambda c, m, d: build_functions_model_v2(c, m, d),
    "transport": lambda c, m, d: build_transport_model(c, m),
    "parameter-pager": lambda c, m, d: build_parameter_pager_model_v2(c, m),
    "clip": lambda c, m, d: build_clip_model_v2(c, m),
}


def build_mappings_model_v2(mappings: AllMappingTypes, controller: ControllerV2,
                            root_dir: Path, mode_name: str = "", acc=None) -> AllMappingWithMidiTypes:
    """
    Returns a model of the mapping with midi info attached.

    When an accumulator is passed, a per-mapping build failure (e.g. an
    out-of-range coord) is recorded and that mapping is skipped, so sibling
    mappings — and other modes/files — still get validated in the same pass.
    """

    mappings_with_midi = []

    for mapping in mappings:
        builder = _MAPPING_BUILDERS.get(mapping.type)
        if builder is None:
            continue
        if acc is not None:
            built = acc.capture(lambda: builder(controller, mapping, root_dir))
            if built is not None:
                mappings_with_midi.append(built)
        else:
            mappings_with_midi.append(builder(controller, mapping, root_dir))

    print_model_with_mappings(controller, mappings_with_midi)
    validate_mappings(mappings_with_midi, mode_name=mode_name, acc=acc)

    return mappings_with_midi


# Mapping union members — derived so the error text can never drift from the
# actual set of supported mapping types. AllMappingTypes is
# List[Annotated[Union[...], Field(discriminator='type')]].
_MAPPING_MEMBERS = get_args(get_args(get_args(AllMappingTypes)[0])[0])
KNOWN_MAPPING_TYPES = [m.model_fields['type'].default for m in _MAPPING_MEMBERS]


def _format_validation_error(e: ValidationError, source: str) -> GenError:
    """Turn a raw Pydantic ValidationError into a readable, deduplicated summary.

    The mapping field is a discriminated union on `type`, so a wrong/missing type
    collapses to a single tag error instead of one error per union member.
    """
    valid = ", ".join(KNOWN_MAPPING_TYPES)
    lines = []
    for err in e.errors():
        loc = ".".join(str(p) for p in err['loc'])
        etype = err['type']
        if etype == 'union_tag_invalid':
            bad = err.get('ctx', {}).get('tag', err.get('input'))
            lines.append(f"  - {loc}.type: unknown mapping type {bad!r} — expected one of: {valid}")
        elif etype == 'union_tag_not_found':
            lines.append(f"  - {loc}: missing required key 'type' (expected one of: {valid})")
        else:
            lines.append(f"  - {loc or '(top level)'}: {err['msg']}")

    body = "\n".join(dict.fromkeys(lines)) or "  - (validation failed)"
    return GenError(f"Invalid config in {source}:\n{body}", ErrorCode.CONFIG_VALIDATION)


def _validate_mode_names(root: RootV2, acc=None) -> None:
    seen, dupes = set(), []
    for mode in root.modes:
        if mode.name in seen:
            dupes.append(mode.name)
        seen.add(mode.name)
    if not dupes:
        return
    message = (f"Duplicate mode name(s): {', '.join(sorted(set(dupes)))} — "
               f"each mode must have a unique name.")
    if acc is not None:
        acc.add(message)
    else:
        raise GenError(message, ErrorCode.SEMANTIC_VALIDATION)


def read_root(mapping_path, source: str = "mapping file", acc=None) -> RootV2:
    try:
        data = nt.loads(mapping_path)
        if not isinstance(data, dict):
            raise GenError(
                f"Invalid config in {source}: expected a mapping (key: value) at the "
                f"top level, got a {type(data).__name__}.", ErrorCode.CONFIG_VALIDATION)
        root = RootV2ModesOrModeless(**data).buildRootV2()
    except nt.NestedTextError as e:
        e.terminate()
    except ValidationError as e:
        raise _format_validation_error(e, source) from e
    _validate_mode_names(root, acc=acc)
    return root


def read_controller(controller_path, source: str = "controller file", acc=None) -> ControllerV2:
    try:
        data = nt.loads(controller_path)
        if not isinstance(data, dict):
            raise GenError(
                f"Invalid config in {source}: expected a mapping (key: value) at the "
                f"top level, got a {type(data).__name__}.", ErrorCode.CONFIG_VALIDATION)
        raw = ControllerRawV2.model_validate(data)
    except nt.NestedTextError as e:
        e.terminate()
    except ValidationError as e:
        raise _format_validation_error(e, source) from e
    validate_controller_semantics(raw, acc=acc)
    return ControllerV2.build_from(raw, acc=acc)


def build_validated_model(mapping_text, root_dir: Path, resolve_controller,
                          mapping_source: str = "mapping file"):
    """Top-level orchestrator for the validation pass.

    Parses + builds the whole config through one shared accumulator so EVERY
    semantic problem — spanning the mapping file and the controller file — is
    reported in a single error, instead of failing on the first one. Parse-level
    failures (NestedText / Pydantic) still raise immediately, since there is
    nothing further to validate once parsing fails.

    ``resolve_controller`` is called with the parsed root and must return
    ``(controller_text, controller_source)``; this lets the caller locate the
    controller file (its path lives inside the mapping) while keeping the
    orchestration testable with in-memory strings.

    Returns ``(root, controller, mode_with_midi)``.
    """
    acc = ProblemAccumulator()
    root = read_root(mapping_text, source=mapping_source, acc=acc)
    controller_text, controller_source = resolve_controller(root)
    controller = read_controller(controller_text, source=controller_source, acc=acc)
    mode_with_midi = read_root_v2(root, controller, root_dir, acc=acc)
    acc.raise_if_any()
    return root, controller, mode_with_midi
