from dataclasses import dataclass
from typing import Union, List, Self, Optional

from pydantic import BaseModel, model_validator, Field

from nestedtext import nestedtext as nt
from ableton_control_suface_as_code.core_model import MixerWithMidi, MidiCoords, parse_coords
from ableton_control_suface_as_code.model_controller import ControllerRawV2, ControllerV2
from ableton_control_suface_as_code.model_device import DeviceWithMidi, build_device_model_v2, DeviceV2
from ableton_control_suface_as_code.model_device_nav import DeviceNav, DeviceNavWithMidi, build_device_nav_model_v2
from ableton_control_suface_as_code.model_functions import build_functions_model_v2, Functions, FunctionsWithMidi
from ableton_control_suface_as_code.model_mixer import MixerV2, build_mixer_model_v2
from ableton_control_suface_as_code.model_track_nav import TrackNav, TrackNavWithMidi, \
    build_track_nav_model_v2

class ModeMappingsV2(BaseModel):
    mappings: List[Union[MixerV2, DeviceV2, TrackNav, DeviceNav, Functions]] = []

@dataclass
class ModeData:
    name: str
    next: str
    is_shift: bool
    color: Optional[str]

class ModeGroupV2(BaseModel):
    name: str
    button: str = None
    type: str = None
    on_color: Optional[str] = None
    off_color: Optional[str] = None
    mode_1: List[Union[MixerV2, DeviceV2, TrackNav, DeviceNav, Functions]]
    mode_2: List[Union[MixerV2, DeviceV2, TrackNav, DeviceNav, Functions]]

    @property
    def mappings(self):
        return self.mode_1 + self.mode_2


class RootV2(BaseModel):
    controller: str
    mappings: List[Union[MixerV2, DeviceV2, TrackNav, DeviceNav, Functions]] = []
    mode: Optional[ModeGroupV2] = None

    @model_validator(mode='after')
    def mode_or_mapping(self) -> Self:
        if self.mode is None and len(self.mappings) == 0:
            raise ValueError('no mappings or modes')

        if self.mode is not None and len(self.mappings) > 0:
            raise ValueError('cannot have both mappings and modes')

        return self

class ModeMappingsV2(BaseModel):
    mode: ModeGroupV2
    button: MidiCoords
    on_color: Optional[int] = None
    off_color: Optional[int] = None

class ModeGroupWithMidi(BaseModel):
    mode_mappings: Optional[ModeMappingsV2]
    mappings: dict[str, List[Union[DeviceWithMidi, MixerWithMidi, TrackNavWithMidi, DeviceNavWithMidi, FunctionsWithMidi]]]

    def has_modes(self):
        return self.mode_mappings is not None

    def is_shift(self):
        return self.mode.type is not None and self.mode.type == 'shift'

    def first_mode_name(self):
        return "mode_1"

    def fsm(self):
        return [
            ModeData(
                name="mode_1",
                next="mode_2",
                is_shift=self.is_shift(),
                color=self.off_color
            ),
            ModeData(
                name="mode_2",
                next="mode_1",
                is_shift=self.is_shift(),
                color=self.on_color
            )
        ]


def build_mappings_model_with_mode(mode:ModeGroupV2, controller:ControllerV2) -> ModeGroupWithMidi:

    mapping_1 = build_mappings_model_v2(mode.mode_1, controller)
    mapping_2 = build_mappings_model_v2(mode.mode_2, controller)

    # return [to_mode_with_midi(mode) for mode in modes]

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


def read_root_v2(root:RootV2, controller:ControllerV2) -> Union[RootV2, ModeGroupWithMidi]:
    if root.mode is not None:
        return build_mappings_model_with_mode(root.mode, controller)
    else:
        return ModeGroupWithMidi(
            mode_mappings=None,
            mappings={
                'mode_1': build_mappings_model_v2(root.mappings, controller)
            }
        )

def build_mappings_model_v2(mappings: List[Union[DeviceV2, MixerV2, TrackNav, DeviceNav, Functions]],
                            controller: ControllerV2) -> (
        List)[Union[DeviceWithMidi, MixerWithMidi, TrackNavWithMidi, DeviceNavWithMidi, FunctionsWithMidi]]:
    """
    Returns a model of the mapping with midi info attached

    :param mappings:
    :param controller:
    :return:
    """

    mappings_with_midi = []

    for mapping in mappings:

        if mapping.type == "device":
            mappings_with_midi.append(build_device_model_v2(controller, mapping))
        if mapping.type == "mixer":
            mappings_with_midi.append(build_mixer_model_v2(controller, mapping))
        if mapping.type == "track-nav":
            mappings_with_midi.append(build_track_nav_model_v2(controller, mapping))
        if mapping.type == "device-nav":
            mappings_with_midi.append(build_device_nav_model_v2(controller, mapping))
        if mapping.type == "functions":
            mappings_with_midi.append(build_functions_model_v2(controller, mapping))

    return mappings_with_midi


def read_root(mapping_path):
    try:

        def normalize_key(key, parent_keys):
            return '_'.join(key.lower().split())

        data = nt.loads(mapping_path, normalize_key=normalize_key)
        return RootV2.model_validate(data)
    except nt.NestedTextError as e:
        e.terminate()


def read_controller(controller_path):
    try:

        def normalize_key(key, parent_keys):
            return '_'.join(key.lower().split())

        data = nt.loads(controller_path, normalize_key=normalize_key)
        return ControllerV2.build_from(ControllerRawV2.model_validate(data))
    except nt.NestedTextError as e:
        e.terminate()
#
#
# controller = {
#     'on_led_midi': '77',
#     'off_led_midi': '78',
#     'control_groups': [
#         {'layout': 'row',
#          'number': 1,
#          'type': 'knob',
#          'midi_channel': 2,
#          'midi_type': "CC",
#          'midi_range': {'from': 21, 'to': 28}
#          },
#         {'layout': 'col',
#          'number': 2,
#          'type': 'button',
#          'midi_channel': 2,
#          'midi_type': "CC",
#          'midi_range': {'from': 29, 'to': 37}
#          },
#         {'layout': 'col',
#          'number': 3,
#          'type': 'button',
#          'midi_channel': 2,
#          'midi_type': "CC",
#          'midi_range': {'from': 38, 'to': 45}
#          }
#     ],
#     'toggles': [
#         'r2-4'
#     ]
# }
# mode_mappings = {
#     'mode_selector': 'r1-1',
#     'shift': True,
#     'modes': [
#         {
#             'name': 'device',
#             'color': 'red',
#             'mappings': []
#         }
#     ]
# }
# test_mappings = [
#     {
#         'type': 'mixer',
#         'track': 'selected',
#         'mappings': {
#             'volume': "r2-3",
#             'pan': "r2-4",
#             'sends': [
#                 {'1': "r2-4"},
#                 {'2': "r3-4"},
#                 {'3': "r2-5"},
#                 {'4': "r3-5"},
#             ]
#         }
#     },
#     {
#         'type': 'transport',
#         'mappings': {
#             'play/stop': "r2-3",
#             'pan': "r2-4",
#         }
#     },
#     {
#         'type': 'function',
#         'controller': "r2-3",
#         'function': 'functions.volume',
#         'value_mapper': {
#             'max': 30,
#             'min': 12
#         }
#     },
#     {
#         'type': 'nav-device',
#         'left': "r2-3",
#         'right': "r2-4"
#     },
#     {
#         'type': 'nav-track',
#         'left': "r2-3",
#         'right': "r2-4"
#     },
#     {
#         'type': 'lom',
#         'controller': "r2-3",
#         'function': 'track.master.device.utility',
#         'value_mapper': {
#             'max': 30,
#             'min': 12
#         }
#     },
#     {
#         'type': 'device',
#         'lom': 'tracks.master.device.Mono',
#         'controller': 'r5-1',
#         'parameter': 0,
#         'toggle': False
#     },
#     {
#         'type': 'device',
#         'lom': 'tracks.master.device.#1',
#         'controller': 'r5-1',
#         'parameter': 0,
#         'toggle': True
#     }
# ]
#
# device_mapping = {
#     'type': 'device',
#     'lom': 'tracks.selected.device.selected',
#     'range_maps': [
#         {
#             "row": 2,
#             "range": {'from': 1, 'to': 8},  # inclusive
#             "parameters": {'from': 1, 'to': 8},
#         },
#         {
#             "row": 3,
#             "range": {'from': 1, 'to': 8},
#             "parameters": {'from': 9, 'to': 16},
#         }
#     ]
# }
