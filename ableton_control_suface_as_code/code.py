import ast
from dataclasses import dataclass, field
from string import Template
from typing import List

from ableton_control_suface_as_code.core_model import MixerWithMidi, TrackInfo, ButtonProviderBaseModel, MidiCoords
from ableton_control_suface_as_code.model_device import DeviceWithMidi
from ableton_control_suface_as_code.model_device_nav import DeviceNavWithMidi
from ableton_control_suface_as_code.model_functions import FunctionsWithMidi
from ableton_control_suface_as_code.model_track_nav import TrackNavWithMidi


@dataclass
class GeneratedModeCode:
    array_defs: [(str, [MidiCoords])] = field(default_factory=list)
    init: [str] = field(default_factory=list)
    control_defs: [MidiCoords] = field(default_factory=list)
    listener_fns: [str] = field(default_factory=list)
    setup_listeners: [str] = field(default_factory=list)
    remove_listeners: [str] = field(default_factory=list)

    @classmethod
    def merge_all(cls, codes: []):
        if len(codes) == 0:
            return GeneratedModeCode([], [], [], [], [], [])
        if len(codes) == 1:
            return codes[0]
        else:
            first = codes[0]
            for c in codes[1:]:
                first = first.merge(c)
            return first

    def merge(self, other):
        # check other is a GeneratedModeCode
        if not isinstance(other, GeneratedModeCode):
            raise ValueError(f"Can't merge with {other}")

        return GeneratedModeCode(
            self.array_defs + other.array_defs,
            self.init + other.init,
            self.control_defs + other.control_defs,
            self.listener_fns + other.listener_fns,
            self.setup_listeners + other.setup_listeners,
            self.remove_listeners + other.remove_listeners
        )


def generate_lom_listener_action(parameter, lom, fn_name, debug_st) -> [str]:
    return Template("""
def ${fn_name}(self, value):
    device = $lom
    self.device_parameter_action(device, $parameter, value, "$fn_name")    
    """).substitute(parameter=parameter, lom=lom, fn_name=fn_name, comment=debug_st).split("\n")


def generate_control_value_listener_function_action(fn_name, callee, debug_st) -> [str]:
    return Template("""
# $comment   
def ${fn_name}(self, value):
    if self.manager.debug:
        self.log_message(f"${fn_name} ($comment) callee = ${callee}, value is {value}")

    $callee  
    """).substitute(callee=callee, fn_name=fn_name, comment=debug_st).split("\n")


def mixer_mode_templates(mixer_with_midi: MixerWithMidi, mode_name: str) -> GeneratedModeCode:
    codes = GeneratedModeCode()

    for midi_map in mixer_with_midi.midi_maps:
        if midi_map.api_function == "sends":
            var_name = f"{midi_map.midi_coords[0].controller_variable_name()}_{mode_name}_sends"

            codes = codes.merge(GeneratedModeCode(
                array_defs=[(var_name, midi_map.midi_coords)],
                setup_listeners=[midi_map.listener_setup_code(var_name)],
                remove_listeners=[midi_map.listener_remove_code()]
            ))
        else:
            codes = codes.merge(GeneratedModeCode(
                control_defs=[midi_map.only_midi_coord],
                setup_listeners=[midi_map.listener_setup_code()],
                remove_listeners=[midi_map.listener_remove_code()]
            ))

    return codes


def device_mode_templates(device_with_midi: DeviceWithMidi, mode_name: str):
    codes = GeneratedModeCode()

    lom = build_live_api_lookup_from_lom(device_with_midi.track, device_with_midi.device)

    for mm in device_with_midi.midi_range_maps:
        enc_name = mm.controller_variable_name()
        enc_listener_name = mm.controller_listener_fn_name(mode_name)

        codes = codes.merge(GeneratedModeCode(
            control_defs=[mm.midi_coords],
            setup_listeners=[f"self.{enc_name}.add_value_listener(self.{enc_listener_name})"],
            remove_listeners=[f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})"],
            listener_fns=generate_lom_listener_action(mm.parameter, lom, enc_listener_name, mm.info_string())
        ))

    return codes


def button_listener_function_caller_mode_templates(midi_map: ButtonProviderBaseModel, mode_name: str):
    button_name = midi_map.controller_variable_name()
    button_listener_name = midi_map.controller_listener_fn_name(mode_name)

    return GeneratedModeCode(
        control_defs=[midi_map.only_midi_coord],
        setup_listeners=[f"self.{button_name}.add_value_listener(self.{button_listener_name})"],
        remove_listeners=[f"self.{button_name}.remove_value_listener(self.{button_listener_name})"],
        listener_fns=generate_control_value_listener_function_action(button_listener_name,
                                                                     midi_map.template_function_name(),
                                                                     midi_map.info_string())
    )


def map_controllers(mode_name, midi_maps: List[ButtonProviderBaseModel]):
    codes = [button_listener_function_caller_mode_templates(m, mode_name) for m in midi_maps]
    return GeneratedModeCode.merge_all(codes)


def track_nav_mode_templates(track_nav_with_midi: TrackNavWithMidi, mode_name) -> GeneratedModeCode:
    return map_controllers(mode_name, track_nav_with_midi.midi_maps)


def device_nav_mode_templates(deivce_nav_with_midi: DeviceNavWithMidi, mode_name) -> GeneratedModeCode:
    return map_controllers(mode_name, deivce_nav_with_midi.midi_maps)


def functions_mode_templates(functions_with_midi: FunctionsWithMidi, mode_name) -> GeneratedModeCode:
    return map_controllers(mode_name, functions_with_midi.midi_maps)


def is_valid_python(code):
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def build_live_api_lookup_from_lom(track: TrackInfo, device):
    """"
        tracks.selected.device.selected
        tracks.1.device.1.


        self.manager.song().view.tracks[0].view.devices[0]
        self.manager.song().view.selected_track.view.selected_device
    """

    # if track.isnumeric():
    #     track_st = f"tracks[{int(track)-1}]"
    # elif track == 'selected':
    #     track_st = 'selected_track'
    # else:
    #     print(f"can't parse track: {track}")
    #     exit(1)
    track_st = track.name.lom_name

    if device.isnumeric():
        device_st = f"devices[{int(device) - 1}]"
    elif device == 'selected':
        device_st = 'selected_device'
    else:
        print(f"can't parse device: {device}")
        exit(1)

    return f"self.manager.song().view.{track_st}.view.{device_st}"


def snake_to_camel(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def class_function_code_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    tab_block = "    "
    return f"\n{tab_block}".join(lines) + "\n"


def class_function_body_code_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    tab_block = "    "
    return f"\n{tab_block}{tab_block}" + f"\n{tab_block}{tab_block}".join(lines) + "\n"
