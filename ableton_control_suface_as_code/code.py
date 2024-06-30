import ast
from dataclasses import dataclass, field
from string import Template

from ableton_control_suface_as_code.core_model import MixerWithMidi, TrackInfo, ButtonProviderBaseModel, MidiCoords
from ableton_control_suface_as_code.model_device import DeviceWithMidi
from ableton_control_suface_as_code.model_device_nav import DeviceNavWithMidi
from ableton_control_suface_as_code.model_functions import FunctionsWithMidi
from ableton_control_suface_as_code.model_track_nav import TrackNavWithMidi
from ableton_control_suface_as_code.model_v2 import ModeGroupWithMidi


@dataclass
class GeneratedModeCode:
    array_defs: [(str, [MidiCoords])] = field(default_factory=list)
    setup: [str] = field(default_factory=list)
    creation: [MidiCoords] = field(default_factory=list)
    listener_fns: [str] = field(default_factory=list)
    setup_listeners: [str] = field(default_factory=list)
    remove_listeners: [str] = field(default_factory=list)

    def print_all(self):
        print("Array Defs:")
        print("\n".join(self.array_defs))
        print("Setup:")
        print("\n".join(self.setup))
        print("Creation:")
        print("\n".join(self.creation))
        print("Listener Fns:")
        print("\n".join(self.listener_fns))
        print("Setup Listeners:")
        print("\n".join(self.setup_listeners))
        print("Remove Listeners:")
        print("\n".join(self.remove_listeners))

    @classmethod
    def merge_all(cls, codes:[]):
        if len(codes) == 0:
            return GeneratedCode([], [], [], [], [], [])
        if len(codes) == 1:
            return codes[0]
        else:
            first = codes[0]
            for c in codes[1:]:
                first = first.merge(c)
            return first

    def merge(self, other):
        return GeneratedModeCode(
            self.array_defs + other.array_defs,
            self.setup + other.setup,
            self.creation + other.creation,
            self.listener_fns + other.listener_fns,
            self.setup_listeners + other.setup_listeners,
            self.remove_listeners + other.remove_listeners
        )


@dataclass
class GeneratedCode:
    setup_new:[MidiCoords] = field(default_factory=list)
    setup: [str] = field(default_factory=list)
    creation: [str] = field(default_factory=list)
    listener_fns: [str] = field(default_factory=list)
    setup_listeners: [str] = field(default_factory=list)
    remove_listeners: [str] = field(default_factory=list)

    def print_all(self):
        print("Setup:")
        print("\n".join(self.setup))
        print("Creation:")
        print("\n".join(self.creation))
        print("Listener Fns:")
        print("\n".join(self.listener_fns))
        print("Setup Listeners:")
        print("\n".join(self.setup_listeners))
        print("Remove Listeners:")
        print("\n".join(self.remove_listeners))

    @classmethod
    def merge_all(cls, codes:[]):
        if len(codes) == 0:
            return GeneratedCode([], [], [], [], [], [])
        if len(codes) == 1:
            return codes[0]
        else:
            first = codes[0]
            for c in codes[1:]:
                first = first.merge(c)
            return first

    def merge(self, other):
        return GeneratedCode(
            self.setup_new + other.setup_new,
            self.setup + other.setup,
            self.creation + other.creation,
            self.listener_fns + other.listener_fns,
            self.setup_listeners + other.setup_listeners,
            self.remove_listeners + other.remove_listeners
        )

def mode_template(modes_with_midi: [ModeGroupWithMidi]) -> GeneratedModeCode:
    mode_dict_lines = "\n\t".join([f"'{m.mode.name}': {m.mode.next}," for m in modes_with_midi])
    return Template("""
self._modes = {
    $mode_dict_lines
}

    """).substitute(mode_dict_lines=mode_dict_lines).split("\n")


def generate_lom_listener_action(parameter, lom, fn_name, debug_st) -> [str]:
    return Template("""
def ${fn_name}(self, value):
    device = $lom
    self.device_parameter_action(device, $parameter, value, "$fn_name")    
    """).substitute(parameter=parameter, lom=lom, fn_name=fn_name, comment=debug_st).split("\n")


def generate_button_listener_function_action(fn_name, callee, debug_st) -> [str]:
    return Template("""
# $comment   
def ${fn_name}(self, value):
    if self.manager.debug:
        self.log_message(f"${fn_name} ($comment) callee = ${callee}, value is {value}")

    $callee  
    """).substitute(callee=callee, fn_name=fn_name, comment=debug_st).split("\n")


def mixer_mode_templates(mixer_with_midi: MixerWithMidi, mode_name:str) -> GeneratedModeCode:

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
                creation=[midi_map.only_midi_coord],
                setup_listeners=[midi_map.listener_setup_code()],
                remove_listeners=[midi_map.listener_remove_code()]
            ))

    return codes

def mixer_templates(mixer_with_midi: MixerWithMidi) -> GeneratedCode:
    setup = []
    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    for midi_map in mixer_with_midi.midi_maps:
        if midi_map.controller_type.is_button():
            # if midi_map.selected_track:
            if midi_map.track_info.is_selected():
                # TODO fix momentary/toggle
                bn = f"button_{midi_map.info_string()}"
                creation.append(f"self.{bn} = {midi_map.midi_coords[0].create_button_element()}")
                creation.append(f"self.{bn}.set_on_off_values(self.led_on, self.led_off)")

                setup_listeners.append(
                    f"self.mixer.selected_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(self.{bn})")
                remove_listeners.append(
                    f"self.mixer.selected_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(None)")
            else:
                print("Button on number track not implemented")
        else:
            track_strip = f"{midi_map.track_info.name.mixer_strip_name}_strip()"
            if midi_map.api_function == "sends":
                sends_var = f"send_controls_{midi_map.info_string()}"
                sends_len = len(midi_map.midi_coords)
                creation.append(f"self.{sends_var} = [None] * {sends_len}")

                # TODO sends lenth max of midi range or actual sends size

                for i, midi in enumerate(midi_map.midi_coords):
                    creation.append(f"self.{sends_var}[{i}] = {midi.create_encoder_element()}")

                setup_listeners.append(
                    f"self.mixer.{track_strip}.set_send_controls(self.{sends_var})")
                remove_listeners.append(
                    f"self.mixer.{track_strip}.set_send_controls(None)")
            else:
                cn = f"encodr_{midi_map.info_string()}"

                creation.append(f"self.{cn} = {midi_map.midi_coords[0].create_encoder_element()}")
                setup_listeners.append(
                    f"self.mixer.{track_strip}.set_{midi_map.api_function}_{midi_map.api_control_type}(self.{cn})")
                remove_listeners.append(
                    f"self.mixer.{track_strip}.set_{midi_map.api_function}_{midi_map.api_control_type}(None)")

    return GeneratedCode(
        [], setup, creation, listener_fns, setup_listeners, remove_listeners
    )

def device_mode_templates(device_with_midi: DeviceWithMidi, mode_name:str):
    #
    # creation = []
    # listener_fns = []
    # setup_listeners = []
    # remove_listeners = []

    codes = GeneratedModeCode()

    lom = build_live_api_lookup_from_lom(device_with_midi.track, device_with_midi.device)

    for mm in device_with_midi.midi_range_maps:
        # creation.append(mm.midi_coords)
        enc_name = mm.controller_variable_name()
        enc_listener_name = mm.controller_listener_fn_name(mode_name)
        #
        # setup_listeners.append(f"self.{enc_name}.add_value_listener(self.{enc_listener_name})")
        # remove_listeners.append(f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})")
        # listener_fns.extend(generate_lom_listener_action(mm.parameter, lom, enc_listener_name, mm.info_string()))

        codes = codes.merge(GeneratedModeCode(
            creation=[mm.midi_coords],
            setup_listeners=[f"self.{enc_name}.add_value_listener(self.{enc_listener_name})"],
            remove_listeners=[f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})"],
            listener_fns=generate_lom_listener_action(mm.parameter, lom, enc_listener_name, mm.info_string())
        ))

    return codes
    #
    # return GeneratedModeCode(
    #     [], [], creation, listener_fns, setup_listeners, remove_listeners
    # )




def button_listener_function_caller_mode_templates(midi_map: ButtonProviderBaseModel, mode_name:str):

    button_name = midi_map.controller_variable_name()
    button_listener_name = midi_map.controller_listener_fn_name(mode_name)

    return GeneratedModeCode(
        creation=[midi_map.only_midi_coord],
        setup_listeners=[f"self.{button_name}.add_value_listener(self.{button_listener_name})"],
        remove_listeners=[f"self.{button_name}.remove_value_listener(self.{button_listener_name})"],
        listener_fns=generate_button_listener_function_action(button_listener_name, midi_map.template_function_name(), midi_map.info_string())
    )


def device_templates(device_with_midi: DeviceWithMidi):
    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    lom = build_live_api_lookup_from_lom(device_with_midi.track, device_with_midi.device)

    for mm in device_with_midi.midi_range_maps:
        enc_name = f"encoder_{mm.info_string()}"
        enc_listener_name = f"encoder_{mm.info_string()}_value"

        creation.append(f"self.{enc_name} = {mm.midi_coords.create_encoder_element()}")
        setup_listeners.append(f"self.{enc_name}.add_value_listener(self.{enc_listener_name})")
        remove_listeners.append(f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})")
        listener_fns.extend(generate_lom_listener_action(mm.parameter, lom, enc_listener_name, mm.info_string()))

    return GeneratedCode(
        [], [], creation, listener_fns, setup_listeners, remove_listeners
    )

def button_listener_function_caller_templates(midi_map: ButtonProviderBaseModel):
    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    button_name = f"button_{midi_map.info_string()}"
    button_listener_name = f"button_{midi_map.info_string()}_value"

    creation.append(f"self.{button_name} = {midi_map.create_controller_element()}")
    setup_listeners.append(f"self.{button_name}.add_value_listener(self.{button_listener_name})")
    remove_listeners.append(f"self.{button_name}.remove_value_listener(self.{button_listener_name})")
    listener_fns.extend(generate_button_listener_function_action(button_listener_name, midi_map.template_function_name(), midi_map.info_string()))

    return GeneratedCode(
        [], [], creation, listener_fns, setup_listeners, remove_listeners
    )


def track_nav_templates(track_nav_with_midi: TrackNavWithMidi) -> GeneratedCode:
    codes = [button_listener_function_caller_templates(m) for m in track_nav_with_midi.midi_maps]
    return GeneratedCode.merge_all(codes)


def device_nav_templates(deivce_nav_with_midi: DeviceNavWithMidi) -> GeneratedCode:
    codes = [button_listener_function_caller_templates(m) for m in deivce_nav_with_midi.midi_maps]
    return GeneratedCode.merge_all(codes)


def functions_templates(functions_with_midi: FunctionsWithMidi) -> GeneratedCode:
    codes = [button_listener_function_caller_templates(m) for m in functions_with_midi.midi_maps]
    return GeneratedCode.merge_all(codes)

def functions_mode_templates(functions_with_midi: FunctionsWithMidi, mode_name) -> GeneratedCode:
    codes = [button_listener_function_caller_mode_templates(m, mode_name) for m in functions_with_midi.midi_maps]
    return GeneratedCode.merge_all(codes)


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
