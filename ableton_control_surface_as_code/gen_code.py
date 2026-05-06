import ast
import keyword
from dataclasses import dataclass, field
from string import Template
from typing import List, Tuple

from ableton_control_surface_as_code.core_model import MixerWithMidi, ButtonProviderBaseModel, MidiCoords
from ableton_control_surface_as_code.encoder_coords import EncoderRefinements
from ableton_control_surface_as_code.family_intents import (
    load_family_intents,
    is_mode_slot,
)
from ableton_control_surface_as_code.model_device import DeviceWithMidi, ModeButtonMidiMapping
from ableton_control_surface_as_code.model_device_nav import DeviceNavWithMidi
from ableton_control_surface_as_code.model_functions import FunctionsWithMidi
from ableton_control_surface_as_code.model_track_nav import TrackNavWithMidi
from ableton_control_surface_as_code.model_transport import TransportWithMidi

_family_intents = load_family_intents()


@dataclass
class GeneratedCode:
    array_defs: [(str, [MidiCoords])] = field(default_factory=list)
    init: [str] = field(default_factory=list)
    control_defs: [MidiCoords] = field(default_factory=list)
    listener_fns: [str] = field(default_factory=list)
    setup_listeners: [str] = field(default_factory=list)
    remove_listeners: [str] = field(default_factory=list)
    custom_parameter_mappings: [str] = field(default_factory=list)
    switch_parameter_mappings: [str] = field(default_factory=list)

    def midi_coords_exists_in_control_defs(self, midi_coords: MidiCoords) -> bool:
        return any([c == midi_coords for c in self.control_defs])

    def any_midi_coords_exists_in_control_defs(self, midi_coords: [MidiCoords]) -> bool:
        return any([self.midi_coords_exists_in_control_defs(c) for c in midi_coords])

    def common_midi_coords_in_control_defs(self, other: 'GeneratedCode') -> [MidiCoords]:
        return [c for c in self.control_defs if other.midi_coords_exists_in_control_defs(c)]

    def common_midi_coords_in_any_control_defs(self, other: ['GeneratedCode']) -> [MidiCoords]:
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
    def common_midi_coords_in_control_defs(cls, one: [GeneratedCode], to: [GeneratedCode]) -> [MidiCoords]:
        listoflists = [o.common_midi_coords_in_any_control_defs(to) for o in one]
        return sum(listoflists, [])

    @classmethod
    def merge(cls, one: GeneratedCode, other: GeneratedCode) -> GeneratedCode:
        if not isinstance(other, GeneratedCode):
            raise ValueError(f"Can't merge with {other}")

        custom_parameter_mappings = one_non_empty_array_or_none(
            one.custom_parameter_mappings, other.custom_parameter_mappings)
        switch_parameter_mappings = one_non_empty_array_or_none(
            one.switch_parameter_mappings, other.switch_parameter_mappings)

        return GeneratedCode(
            one.array_defs + other.array_defs,
            one.init + other.init,
            one.control_defs + other.control_defs,
            one.listener_fns + other.listener_fns,
            one.setup_listeners + other.setup_listeners,
            one.remove_listeners + other.remove_listeners,
            custom_parameter_mappings,
            switch_parameter_mappings,
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
                # Each coord in the array_def is referenced as `self.<knob>`, so
                # the corresponding EncoderElement must be declared in setup_controls.
                control_defs=list(midi_map.midi_coords),
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

    for mb in device_with_midi.mode_button_maps:
        codes.append(_mode_button_template(mb, mode_name, device_with_midi.track.name.value, device_with_midi.device))

    if device_with_midi.parameter_page_nav is not None:
        if device_with_midi.parameter_page_nav.export_to_mode is not None:
            if device_with_midi.parameter_page_nav.export_to_mode == mode_name:
                codes.extend(code_for_parameter_paging(device_with_midi.parameter_page_nav, mode_name))
            else:
                print(
                    f"Not generating parmeter_paging on mode {mode_name} as it's being exported to {device_with_midi.parameter_page_nav.export_to_mode}")

    custom_mappings = code_from_slot_assignments(device_with_midi.slot_assignments)
    switch_mappings = code_from_switch_slot_assignments(device_with_midi.mode_button_maps)
    codes.append(GeneratedCode(custom_parameter_mappings=custom_mappings,
                               switch_parameter_mappings=switch_mappings))

    return codes


def _mode_button_template(mb: ModeButtonMidiMapping, mode_name: str, track: str = "selected", device: str = "selected") -> 'GeneratedCode':
    btn_name = mb.controller_variable_name()
    btn_listener_name = mb.controller_listener_fn_name(mode_name)

    fn = _switch_action_dispatch_fn(btn_listener_name, mb.slot, track, device).split("\n")

    return GeneratedCode(
        control_defs=[mb.only_midi_coord],
        setup_listeners=[f"self.{btn_name}.add_value_listener(self.{btn_listener_name})",
                         f"self._previous_values['{btn_listener_name}'] = 0"],
        remove_listeners=[f"self.{btn_name}.remove_value_listener(self.{btn_listener_name})"],
        listener_fns=fn,
    )


def _switch_action_dispatch_fn(fn_name: str, slot: str, track: str, device: str) -> str:
    """
    Build a per-class dispatch table for one switch slot. The table value is
    (action, payload) where payload's shape depends on the action:
        cycle        -> (param_no:int, cmin:int, cmax:int)
        pulse|inc|dec|random -> param_name:str
        group_random -> tuple[str, ...] of parameter names
    Each branch defers the actual work to a runtime helper.
    """
    table = _family_intents.get(slot, {})
    rows = {}
    for cls, entry in table.items():
        if entry.action == "cycle":
            if not entry.is_cycle:
                continue
            rows[cls] = ("cycle", (entry.parameter_number, entry.cycle_min, entry.cycle_max))
        elif entry.action in ("pulse", "inc", "dec", "random"):
            if not entry.parameter_name:
                continue
            rows[cls] = (entry.action, entry.parameter_name)
        elif entry.action == "group_random":
            if not entry.parameter_names:
                continue
            rows[cls] = ("group_random", tuple(entry.parameter_names))

    table_literal = repr(rows)

    return Template("""
def ${fn_name}(self, value):
    self.log_message(f"calling : ${fn_name}")
    #if value != 127:
    #    return
    device = self.find_device("${track}", "${device}")
    if device is None:
        self.log_message(f"device not found: ${track} - ${device}")
        return
    table = ${table_literal}
    # class_name first so audio families (Compressor2, Amp, ...) win;
    # device.name as fallback covers Max4Live (MxDeviceMidiEffect) and racks
    # (InstrumentGroupDevice) where class_name is too generic to identify the device.
    entry = table.get(device.class_name) or table.get(device.name)
    if entry is None:
        self.log_message(f"${slot} not supported for {device.class_name} / {device.name}")
        return
    action, payload = entry
    if action == "cycle":
        param_no, cmin, cmax = payload
        self._helpers.device_param_cycle(device, param_no, cmin, cmax, "$fn_name")
    elif action == "pulse":
        self._helpers.device_param_pulse(device, payload, "$fn_name")
    elif action == "inc":
        self._helpers.device_param_inc(device, payload, "$fn_name")
    elif action == "dec":
        self._helpers.device_param_dec(device, payload, "$fn_name")
    elif action == "random":
        self._helpers.device_param_random(device, payload, "$fn_name")
    elif action == "group_random":
        self._helpers.device_params_group_random(device, payload, "$fn_name")
    """).substitute(
        fn_name=fn_name,
        track=track,
        device=device,
        table_literal=table_literal,
        slot=slot,
    )


def code_from_slot_assignments(slot_assignments: List[Tuple[int, str]]) -> List[str]:
    """
    Given the user's encoder_index -> slot_name list for one device mapping, emit the
    per-device-class parameter mappings dict entries that the runtime expects.

    For each device class in the family-intents JSON, emit the entries for the slots
    that class supports. Classes with no slot support contribute no entries.
    """
    if not slot_assignments:
        return []

    per_class: dict = {}
    for c_idx, slot in slot_assignments:
        if is_mode_slot(slot):
            continue  # mode slots are handled by mode-buttons, not in this dict
        slot_table = _family_intents.get(slot, {})
        for class_name, entry in slot_table.items():
            per_class.setdefault(class_name, []).append({
                'c_idx': c_idx,
                'd_idx': entry.parameter_number,
                'alias': entry.parameter_name,
            })

    return [f"'{class_name}': {entries!r}" for class_name, entries in sorted(per_class.items())]


def code_from_switch_slot_assignments(mode_button_maps) -> List[str]:
    """
    Build the per-device-class switch-slot parameter mapping dict entries.
    Only processes mode_button_maps entries with slot names starting with 'switch'.
    Returns List[str] lines for the code_switch_parameter_mappings dict.
    """
    per_class: dict = {}
    seen: set = set()  # avoid duplicate (class, switch_idx) entries across modes
    for mb in mode_button_maps:
        if not mb.slot.startswith('switch'):
            continue
        switch_idx = int(mb.slot.replace('switch', '')) - 1  # 0-indexed
        for class_name, entry in _family_intents.get(mb.slot, {}).items():
            key = (class_name, switch_idx)
            if key in seen:
                continue
            seen.add(key)
            per_class.setdefault(class_name, []).append({
                'switch_idx': switch_idx,
                'd_idx': entry.parameter_number,
                'alias': entry.parameter_name,
            })

    return [f"'{class_name}': {entries!r}" for class_name, entries in sorted(per_class.items())]


# TODO Unit tests
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


