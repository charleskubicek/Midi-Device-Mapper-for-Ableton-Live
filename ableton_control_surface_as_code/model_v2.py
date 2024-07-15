from dataclasses import dataclass
from enum import Enum
from typing import Union, List, Optional

from nestedtext import nestedtext as nt
from prettytable import PrettyTable
from pydantic import BaseModel, model_validator, Extra

from ableton_control_surface_as_code.core_model import MixerWithMidi, MidiCoords, parse_coords, MidiType
from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_controller import ControllerRawV2, ControllerV2
from ableton_control_surface_as_code.model_device import DeviceWithMidi, DeviceV2_1, build_device_model_v2_1
from ableton_control_surface_as_code.model_device_nav import DeviceNav, DeviceNavWithMidi, build_device_nav_model_v2
from ableton_control_surface_as_code.model_functions import build_functions_model_v2, Functions, FunctionsWithMidi
from ableton_control_surface_as_code.model_mixer import MixerV2, build_mixer_model_v2
from ableton_control_surface_as_code.model_track_nav import TrackNav, TrackNavWithMidi, \
    build_track_nav_model_v2
from ableton_control_surface_as_code.model_transport import Transport, TransportWithMidi, build_transport_model

AllMappingTypes = List[Union[
    MixerV2,
    DeviceV2_1,
    TrackNav,
    DeviceNav,
    Functions,
    Transport
]]

AllMappingWithMidiTypes = List[Union[
    DeviceWithMidi,
    MixerWithMidi,
    TrackNavWithMidi,
    DeviceNavWithMidi,
    FunctionsWithMidi,
    TransportWithMidi
]]


class ModeMappingsV2(BaseModel):
    mappings: AllMappingTypes = []


@dataclass
class ModeData:
    name: str
    next: str
    is_shift: bool
    color: Optional[str]


class ModeType(str, Enum):
    Toggle = 'toggle'
    Switch = 'switch'


class ModeGroupV2(BaseModel):
    button: str
    type: Optional[ModeType] = ModeType.Switch
    on_color: Optional[str] = None
    off_color: Optional[str] = None
    mode_1: AllMappingTypes
    mode_2: AllMappingTypes

    class Config:
        extra = 'forbid'  #


class RootV2(BaseModel):
    controller: str
    mappings: AllMappingTypes = []
    modes: Optional[ModeGroupV2] = None

    @model_validator(mode='after')
    def mode_or_mapping(self):
        if self.modes is None and len(self.mappings) == 0:
            raise ValueError('no mappings or modes')

        if self.modes is not None and len(self.mappings) > 0:
            raise ValueError('cannot have both mappings and modes')

        return self

    class Config:
        extra = 'forbid'


class ModeMappingsV2(BaseModel):
    mode: ModeGroupV2
    button: MidiCoords
    on_color: Optional[int] = 0
    off_color: Optional[int] = 0

    def is_shift(self):
        return self.mode.type is not None and self.mode.type == 'shift'


class ModeGroupWithMidi(BaseModel):
    mode_mappings: Optional[ModeMappingsV2] = None
    mappings: dict[str, AllMappingWithMidiTypes]

    def has_modes(self):
        return self.mode_mappings is not None

    def is_shift(self):
        return self.mode_mappings.is_shift()

    def first_mode_name(self):
        return "mode_1"

    def fsm(self):
        return [
            ModeData(
                name="mode_1",
                next="mode_2",
                is_shift=self.mode_mappings.is_shift(),
                color=self.mode_mappings.on_color
            ),
            ModeData(
                name="mode_2",
                next="mode_1",
                is_shift=self.mode_mappings.is_shift(),
                color=self.mode_mappings.off_color
            )
        ]


def validate_mappings(mappings: AllMappingWithMidiTypes):
    seen = {}
    for withMidi in mappings:
        for midi_maps in withMidi.midi_maps:
            mcs = midi_maps.midi_coords
            for mc in mcs:
                if mc.ch_num in seen:
                    (pmc, previous) = seen[mc.ch_num]
                    raise GenError(
                        f"Clashing mappings in {withMidi.type} and {previous.type} to chanel:{mc.channel} no:{mc.number} type:{mc.type.value}"
                        + f"\n from source 1: {mc.source_info}"
                        + f"\n from source 2: {pmc.source_info}", 1)
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


def build_mappings_model_with_mode(mode: ModeGroupV2, controller: ControllerV2) -> ModeGroupWithMidi:
    mapping_1 = build_mappings_model_v2(mode.mode_1, controller)
    mapping_2 = build_mappings_model_v2(mode.mode_2, controller)

    return ModeGroupWithMidi(
        mode_mappings=ModeMappingsV2(
            mode=mode,
            button=controller.build_midi_coords(parse_coords(mode.button))[0][0],
            on_color=controller.light_color_for(mode.on_color),
            off_color=controller.light_color_for(mode.off_color)
        ),
        mappings={
            'mode_1': mapping_1,
            'mode_2': mapping_2,
        }
    )


def read_root_v2(root: RootV2, controller: ControllerV2) -> Union[RootV2, ModeGroupWithMidi]:
    if root.modes is not None:
        return build_mappings_model_with_mode(root.modes, controller)
    else:
        return ModeGroupWithMidi(
            mode_mappings=None,
            mappings={
                'mode_1': build_mappings_model_v2(root.mappings, controller)
            }
        )


def build_mappings_model_v2(mappings: AllMappingTypes, controller: ControllerV2) -> AllMappingWithMidiTypes:
    """
    Returns a model of the mapping with midi info attached

    :param mappings:
    :param controller:
    :return:
    """

    mappings_with_midi = []

    for mapping in mappings:

        if mapping.type == "device":
            mappings_with_midi.append(build_device_model_v2_1(controller, mapping))
        if mapping.type == "mixer":
            mappings_with_midi.append(build_mixer_model_v2(controller, mapping))
        if mapping.type == "track-nav":
            mappings_with_midi.append(build_track_nav_model_v2(controller, mapping))
        if mapping.type == "device-nav":
            mappings_with_midi.append(build_device_nav_model_v2(controller, mapping))
        if mapping.type == "functions":
            mappings_with_midi.append(build_functions_model_v2(controller, mapping))
        if mapping.type == "transport":
            mappings_with_midi.append(build_transport_model(controller, mapping))

    print_model_with_mappings(controller, mappings_with_midi)
    validate_mappings(mappings_with_midi)

    return mappings_with_midi


def read_root(mapping_path):
    try:
        data = nt.loads(mapping_path)
        return RootV2(**data)
    except nt.NestedTextError as e:
        e.terminate()


def read_controller(controller_path):
    try:
        data = nt.loads(controller_path)
        return ControllerV2.build_from(ControllerRawV2.model_validate(data))
    except nt.NestedTextError as e:
        e.terminate()
