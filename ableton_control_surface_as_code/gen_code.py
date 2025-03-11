import ast
import json
import keyword
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import List

from ableton_control_surface_as_code.core_model import MixerWithMidi, ButtonProviderBaseModel, MidiCoords
from ableton_control_surface_as_code.encoder_coords import EncoderRefinements
from ableton_control_surface_as_code.model_device import DeviceWithMidi
from ableton_control_surface_as_code.model_device_nav import DeviceNavWithMidi
from ableton_control_surface_as_code.model_functions import FunctionsWithMidi
from ableton_control_surface_as_code.model_track_nav import TrackNavWithMidi
from ableton_control_surface_as_code.model_transport import TransportWithMidi


@dataclass
class GeneratedCode:
    array_defs: [(str, [MidiCoords])] = field(default_factory=list)
    init: [str] = field(default_factory=list)
    control_defs: [MidiCoords] = field(default_factory=list)
    listener_fns: [str] = field(default_factory=list)
    setup_listeners: [str] = field(default_factory=list)
    remove_listeners: [str] = field(default_factory=list)
    custom_parameter_mappings: [str] = field(default_factory=list)

    def midi_coords_exists_in_control_defs(self, midi_coords: MidiCoords) -> bool:
        return any([c == midi_coords for c in self.control_defs])

    def any_midi_coords_exists_in_control_defs(self, midi_coords: [MidiCoords]) -> bool:
        return any([self.midi_coords_exists_in_control_defs(c) for c in midi_coords])

    def common_midi_coords_in_control_defs(self, other:'GeneratedCode') -> [MidiCoords]:
        return [c for c in self.control_defs if other.midi_coords_exists_in_control_defs(c)]

    def common_midi_coords_in_any_control_defs(self, other:['GeneratedCode']) -> [MidiCoords]:
        return [c for c in self.control_defs if any([o.midi_coords_exists_in_control_defs(c) for o in other])]


def one_non_empty_array_or_none(one, other):
    if len(one) > 0 and len(other) > 0:
        print("both arrays are non-empty, using first")
        return one
    elif len(one) > 0 and len(other) == 0:
        return one
    elif len(one) == 0 and len(other) > 0:
        return other

    return []


class GeneratedCodes:
    @classmethod
    def merge_all(cls, codes: [GeneratedCode]) -> GeneratedCode:
        if len(codes) == 0:
            return GeneratedCode()
        else:
            first = codes[0]
            for c in codes[1:]:
                first = cls.merge(first, c)
            return first

    @classmethod
    def common_midi_coords_in_control_defs(cls, one: [GeneratedCode], to:[GeneratedCode]) -> [MidiCoords]:
        listoflists = [o.common_midi_coords_in_any_control_defs(to) for o in one]
        return sum(listoflists,[])


    @classmethod
    def merge(cls, one: GeneratedCode, other: GeneratedCode) -> GeneratedCode:
        if not isinstance(other, GeneratedCode):
            raise ValueError(f"Can't merge with {other}")

        custom_parameter_mappings = one_non_empty_array_or_none(
            one.custom_parameter_mappings, other.custom_parameter_mappings)

        return GeneratedCode(
            one.array_defs + other.array_defs,
            one.init + other.init,
            one.control_defs + other.control_defs,
            one.listener_fns + other.listener_fns,
            one.setup_listeners + other.setup_listeners,
            one.remove_listeners + other.remove_listeners,
            custom_parameter_mappings,
        )


def is_valid_function_name(name):
    # Check if the string is a valid identifier
    if not name.isidentifier():
        return False

    # Check if the string is a reserved keyword
    if keyword.iskeyword(name):
        return False

    return True


def generate_parameter_listener_action(parameter, midi_no, track, device, fn_name, toggle: bool, debug_st) -> [str]:
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    return Template("""
def ${fn_name}(self, value):
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return
        

    self.device_parameter_action(device, $parameter, $midi_no, value, "$fn_name", toggle=$toggle)    
    """).substitute(parameter=parameter, midi_no=midi_no, track=track, device=device, toggle=toggle, fn_name=fn_name,
                    comment=debug_st).split("\n")


def generate_control_value_listener_function_action(fn_name, var_name, callee, toggle: bool, debug_st: str) -> [str]:
    if not is_valid_function_name(fn_name):
        raise ValueError(f"Invalid function name: {fn_name}")

    toggle_fn = "True"
    if toggle:
        toggle_fn = "self._helpers.value_is_max(value, 127)"

    return Template("""
# $comment   
def ${fn_name}(self, value):
    if self.manager.debug:
        self.log_message(f"${fn_name} ($comment) callee = ${callee}, value is {value}")
        
    previous_value = self._previous_values['$fn_name']
    self._previous_values['$fn_name'] = value

    if ${toggle_fn}:
        $callee
    """).substitute(callee=callee, var_name=var_name, fn_name=fn_name, comment=debug_st, toggle_fn=toggle_fn).split(
        "\n")


def mixer_templates(mixer_with_midi: MixerWithMidi, mode_name: str) -> [GeneratedCode]:
    codes = []

    for midi_map in mixer_with_midi.midi_maps:
        if midi_map.api_function == "sends":
            var_name = f"{midi_map.midi_coords[0].controller_variable_name()}_{mode_name}_sends"

            codes.append(GeneratedCode(
                array_defs=[(var_name, midi_map.midi_coords)],
                setup_listeners=[midi_map.listener_setup_code(var_name)],
                remove_listeners=[midi_map.listener_remove_code()]
            ))
        else:
            codes.append(GeneratedCode(
                control_defs=[midi_map.only_midi_coord],
                setup_listeners=[midi_map.listener_setup_code()],
                remove_listeners=[midi_map.listener_remove_code()]
            ))

    return codes


def device_templates(device_with_midi: DeviceWithMidi, mode_name: str):
    codes = []

    for mm in device_with_midi.midi_maps:
        enc_name = mm.controller_variable_name()
        enc_listener_name = mm.controller_listener_fn_name(mode_name)
        enc_refs = EncoderRefinements(mm.only_midi_coord.encoder_refs)

        codes.append(GeneratedCode(
            control_defs=mm.midi_coords,
            setup_listeners=[f"self.{enc_name}.add_value_listener(self.{enc_listener_name})",
                             f"self._previous_values['{enc_listener_name}'] = 0"],
            remove_listeners=[f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})"],
            listener_fns=generate_parameter_listener_action(
                mm.parameter,
                mm.only_midi_coord.number,
                device_with_midi.track.name.value,
                device_with_midi.device,
                enc_listener_name,
                enc_refs.has_toggle(),
                mm.info_string())
        ))

    if device_with_midi.parameter_page_nav is not None:
        if device_with_midi.parameter_page_nav.export_to_mode is not None:
            if device_with_midi.parameter_page_nav.export_to_mode == mode_name:
                codes.extend(code_for_parameter_paging(device_with_midi.parameter_page_nav, mode_name))
            else:
                print(
                    f"Not generating parmeter_paging on mode {mode_name} as it's being exported to {device_with_midi.parameter_page_nav.export_to_mode}")

    print("Custom mappings")
    for dev_name, encoder_map in device_with_midi.custom_device_mappings.items():
        print("  ", dev_name)
        d = [(em.index,
              find_device_parameter_number_for_given_name(dev_name, em.device_parameter))
             for em in encoder_map]

        for m_no, (p_no, _) in d:
            name = "Unknown"
            for p_values in device_parameter_names[dev_name]['parameters']:
                if int(p_values['no']) == int(p_no):
                    name = p_values['name']

            print(f"     {m_no+1} / {p_no}: ({name})")

        code = f"'{dev_name}': " + str(d)
        codes.append(GeneratedCode(custom_parameter_mappings=[code]))

    return codes


def code_for_parameter_paging(parameter_page_nav, mode_name):
    codes = []
    for call_name, mm in [("inc", parameter_page_nav.inc),
                          ("dec", parameter_page_nav.dec)]:
        enc_name = mm.controller_variable_name()
        enc_listener_name = mm.controller_listener_fn_name(mode_name)

        codes.append(
            GeneratedCode(  ## TODO swap this with a CodeGenerator that delays the genreation to as late as possible
                control_defs=[mm],
                setup_listeners=[f"self.{enc_name}.add_value_listener(self.{enc_listener_name})",
                                 f"self._previous_values['{enc_listener_name}'] = 0"],
                remove_listeners=[f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})"],
                listener_fns=[Template(f"""
    def $enc_listener_name(self, value):
        self._helpers.device_parameter_page_$call_name()
    """).substitute(enc_listener_name=enc_listener_name, call_name=call_name)
                              ]
            )
        )

    return codes


def find_device_parameter_number_for_given_name(device_name, device_parameter):
    if device_name not in device_parameter_names:
        print("Device not found, no mappings created: ", device_name)

    for param in device_parameter_names[device_name]['parameters']:
        if param['name'] == device_parameter.name:
            return int(param['no']), device_parameter.alias_str()
    return None


def button_listener_function_caller_templates(midi_map: ButtonProviderBaseModel, mode_name: str):
    button_name = midi_map.controller_variable_name()
    button_listener_name = midi_map.controller_listener_fn_name(mode_name)
    enc_refs = EncoderRefinements(midi_map.only_midi_coord.encoder_refs)

    return GeneratedCode(
        control_defs=[midi_map.only_midi_coord],
        setup_listeners=[f"self.{button_name}.add_value_listener(self.{button_listener_name})",
                         f"self._previous_values['{button_listener_name}'] = 0"],
        remove_listeners=[f"self.{button_name}.remove_value_listener(self.{button_listener_name})"],
        listener_fns=generate_control_value_listener_function_action(button_listener_name,
                                                                     midi_map.controller_variable_name(),
                                                                     midi_map.template_function_call(),
                                                                     enc_refs.has_toggle(),
                                                                     midi_map.info_string())
    )


def map_controllers(mode_name, midi_maps: List[ButtonProviderBaseModel]):
    return [button_listener_function_caller_templates(m, mode_name) for m in midi_maps]


def track_nav_templates(track_nav_with_midi: TrackNavWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, track_nav_with_midi.midi_maps)


def device_nav_templates(deivce_nav_with_midi: DeviceNavWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, deivce_nav_with_midi.midi_maps)


def transport_templates(transport_with_midi: TransportWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, transport_with_midi.midi_maps)


def functions_templates(functions_with_midi: FunctionsWithMidi, mode_name) -> [GeneratedCode]:
    return map_controllers(mode_name, functions_with_midi.midi_maps)


def get_python_code_error(code):
    try:
        ast.parse(code)
    except SyntaxError as e:
        return e
    else:
        return None


def snake_to_camel(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def class_function_code_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    tab_block = "    "
    return f"\n{tab_block}".join(lines) + "\n"


def dict_variable_decleration_block(lines: [str]):
    tab_block = "    "

    if lines is None or lines == []:
        return ""
    else:
        return f"{tab_block}{tab_block}".join(lines) + "\n"


def class_function_body_code_block(lines: [str]):
    if lines is None or lines == []:
        return ""

    tab_block = "    "
    return f"\n{tab_block}{tab_block}" + f"\n{tab_block}{tab_block}".join(lines) + "\n"


file = Path("data/devices_12.json").read_text()
device_parameter_names = json.loads(file)
