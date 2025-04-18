from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union, List, Optional, Tuple

from nestedtext import nestedtext as nt
from prettytable import PrettyTable
from pydantic import BaseModel, model_validator, Extra, Field

from ableton_control_surface_as_code.core_model import MixerWithMidi, MidiCoords, parse_coords, MidiType
from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_controller import ControllerRawV2, ControllerV2
from ableton_control_surface_as_code.model_device import DeviceWithMidi, DeviceV2, build_device_model_v2_1
from ableton_control_surface_as_code.model_device_nav import DeviceNav, DeviceNavWithMidi, build_device_nav_model_v2
from ableton_control_surface_as_code.model_functions import build_functions_model_v2, Functions, FunctionsWithMidi
from ableton_control_surface_as_code.model_mixer import MixerV2, build_mixer_model_v2
from ableton_control_surface_as_code.model_track_nav import TrackNav, TrackNavWithMidi, \
    build_track_nav_model_v2
from ableton_control_surface_as_code.model_transport import Transport, TransportWithMidi, build_transport_model

AllMappingTypes = List[Union[
    MixerV2,
    DeviceV2,
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


@dataclass
class ModeData:
    name: str
    next: str
    is_shift: bool
    color: Optional[str]


class ModeType(str, Enum):
    Shift = 'shift'
    Switch = 'switch'


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


class RootV2(BaseModel):
    controller: str
    mode_button: Optional[ModeButton]
    modes: List[ModeDef]
    ableton_dir: str

    class Config:
        extra = 'forbid'


class RootV2ModesOrModeless(BaseModel):
    controller: str
    mappings: AllMappingTypes = []
    mode_button: Optional[ModeButton] = Field(default=None, alias='mode-button')
    modes: Optional[List[ModeDef]] = None
    ableton_dir: str

    def buildRootV2(self):
        model_modes = [ModeDef.empty_with_one_mode(self.mappings)] if self.modes is None else self.modes

        return RootV2(
            controller=self.controller,
            modes=model_modes,
            mode_button=self.mode_button,
            ableton_dir=self.ableton_dir)


class ModeButtonWithMidi(BaseModel):
    on_colors: List[Tuple[str, int]]
    button: MidiCoords
    type: ModeType = ModeType.Switch


class ModeGroupWithMidi(BaseModel):
    mappings: List[Tuple[str, AllMappingWithMidiTypes]]
    mode_button: Optional[ModeButtonWithMidi]

    # on_colors: List[Tuple[str,int]]
    # button: Optional[MidiCoords]
    # type: Optional[ModeType] = ModeType.Switch

    def first_mode_name(self):
        return self.mappings[0][0]

    def is_shift(self):
        return self.mode_button is not None and self.mode_button.type == ModeType.Shift

    def has_modes(self):
        return len(self.mappings) > 1

    def fsm(self):
        if self.mode_button is None:
            return []

        mode_names = [clr[0] for clr in self.mode_button.on_colors]
        return [ModeData(
            name=name,
            next=mode_names[i + 1] if i + 1 < len(mode_names) else mode_names[0],
            is_shift=self.is_shift(),
            color=str(clr)
        )
            for i, (name, clr) in enumerate(self.mode_button.on_colors)]


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


def read_root_v2(root: RootV2, controller: ControllerV2, root_dir: Path) -> ModeGroupWithMidi:
    mappings = [(mode_dev.name, build_mappings_model_v2(mode_dev.mappings, controller, root_dir))
                for mode_dev in root.modes]

    if root.mode_button is None:
        mode_button = None
    else:
        mode_button = ModeButtonWithMidi(
            on_colors=[(mode_dev.name, controller.light_color_for(mode_dev.on_color)) for mode_dev in root.modes],
            button=controller.build_midi_coords(parse_coords(root.mode_button.button))[0][0],
            type=root.mode_button.type)

    return ModeGroupWithMidi(
        mappings=mappings,
        mode_button=mode_button
    )


def build_mappings_model_v2(mappings: AllMappingTypes, controller: ControllerV2,
                            root_dir: Path) -> AllMappingWithMidiTypes:
    """
    Returns a model of the mapping with midi info attached

    :param mappings:
    :param controller:
    :return:
    """

    mappings_with_midi = []

    for mapping in mappings:

        if mapping.type == "device":
            mappings_with_midi.append(build_device_model_v2_1(controller, mapping, root_dir))
        if mapping.type == "mixer":
            mappings_with_midi.append(build_mixer_model_v2(controller, mapping))
        if mapping.type == "track-nav":
            mappings_with_midi.append(build_track_nav_model_v2(controller, mapping))
        if mapping.type == "device-nav":
            mappings_with_midi.append(build_device_nav_model_v2(controller, mapping))
        if mapping.type == "functions":
            mappings_with_midi.append(build_functions_model_v2(controller, mapping, root_dir))
        if mapping.type == "transport":
            mappings_with_midi.append(build_transport_model(controller, mapping))

    print_model_with_mappings(controller, mappings_with_midi)
    validate_mappings(mappings_with_midi)

    return mappings_with_midi


def read_root(mapping_path) -> RootV2:
    try:
        data = nt.loads(mapping_path)
        return RootV2ModesOrModeless(**data).buildRootV2()
    except nt.NestedTextError as e:
        e.terminate()


def read_controller(controller_path) -> ControllerV2:
    try:
        data = nt.loads(controller_path)
        return ControllerV2.build_from(ControllerRawV2.model_validate(data))
    except nt.NestedTextError as e:
        e.terminate()
