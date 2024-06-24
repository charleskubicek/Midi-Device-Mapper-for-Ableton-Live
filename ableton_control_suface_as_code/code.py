import ast
from dataclasses import dataclass
from string import Template

from ableton_control_suface_as_code.core_model import DeviceWithMidi, MixerWithMidi, TrackInfo
from ableton_control_suface_as_code.model_device_nav import DeviceNavWithMidi
from ableton_control_suface_as_code.model_track_nav import TrackNavMidiMapping, TrackNavWithMidi


@dataclass
class GeneratedCode:
    setup: [str]
    creation: [str]
    listener_fns: [str]
    setup_listeners: [str]
    remove_listeners: [str]

    def creation_line(self, line:str):
        self.creation.append(line)
        return self

    def add_setup_lines(self, lines: [str]):
        self.setup.extend(lines)
        return self

    def setup_listener_line(self, line:str):
        self.setup_listeners.append(line)
        return self

    def remove_listener_line(self, line:str):
        self.setup_listeners.append(line)
        return self

    @classmethod
    def merge_all(cls, codes:[]):
        if len(codes) == 0:
            return GeneratedCode([], [], [], [], [])
        if len(codes) == 1:
            return codes[0]
        else:
            first = codes[0]
            for c in codes[1:]:
                first = first.merge(c)
            return first

    def merge(self, other):
        return GeneratedCode(
            self.setup + other.setup,
            self.creation + other.creation,
            self.listener_fns + other.listener_fns,
            self.setup_listeners + other.setup_listeners,
            self.remove_listeners + other.remove_listeners
        )


def generate_lom_listener_action(parameter, lom, fn_name, debug_st) -> [str]:
    return Template("""
# $comment   
def ${fn_name}(self, value):
    selected_device = $lom
    if selected_device is None:
        return

    if self.manager.debug:
        self.log_message(f"${fn_name} ($comment) selected_device = {selected_device.name}, value is {value}")
    
    selected_device = self.manager.song().view.selected_track.view.selected_device

    if len(selected_device.parameters) < $parameter:
        self.log_message(f"${parameter} too large, max is {len(selected_device.parameters)}")
        return

    selected_device.parameters[$parameter].value = value    
    """).substitute(parameter=parameter, lom=lom, fn_name=fn_name, comment=debug_st).split("\n")


def generate_button_listener_function_action(fn_name, callee, debug_st) -> [str]:
    return Template("""
# $comment   
def ${fn_name}(self, value):
    if self.manager.debug:
        self.log_message(f"${fn_name} ($comment) callee = ${callee}, value is {value}")

    $callee  
    """).substitute(callee=callee, fn_name=fn_name, comment=debug_st).split("\n")


# def button_element(midi_coords:MidiCoords):
#     return f"ConfigurableButtonElement(True, {midi_coords.type.ableton_name()}, {midi_coords.ableton_channel()}, {midi_coords.number})"

# def encoder_element(midi_coords:MidiCoords):
#     return f"EncoderElement({midi_coords.type.ableton_name()}, {midi_coords.ableton_channel()}, {midi_coords.number}, Live.MidiMap.MapMode.absolute)"


def mixer_templates(mixer_with_midi: MixerWithMidi) -> GeneratedCode:
    setup = []
    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    setup.extend([
        "self.led_on = 120",
        "self.led_off = 0"
    ])

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
            if midi_map.api_function == "sends":
                sends_var = f"send_controls_{midi_map.info_string()}"
                sends_len = len(midi_map.midi_coords)
                creation.append(f"self.{sends_var} = [None] * {sends_len}")

                # TODO sends lenth max of midi range or actual sends size

                for i, midi in enumerate(midi_map.midi_coords):
                    creation.append(f"self.{sends_var}[{i}] = {midi.create_encoder_element()}")

                setup_listeners.append(
                    f"self.mixer.{midi_map.track_info.name.mixer_strip_name}_strip().set_send_controls(self.{sends_var})")
                remove_listeners.append(
                    f"self.mixer.{midi_map.track_info.name.mixer_strip_name}_strip().set_send_controls(None)")
            else:
                cn = f"encodr_{midi_map.info_string()}"

                creation.append(f"self.{cn} = {midi_map.midi_coords[0].create_encoder_element()}")
                setup_listeners.append(
                    f"self.mixer.{midi_map.track_info.name.mixer_strip_name}_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(self.{cn})")
                remove_listeners.append(
                    f"self.mixer.{midi_map.track_info.name.mixer_strip_name}_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(None)")

    return GeneratedCode(
        setup, creation, listener_fns, setup_listeners, remove_listeners
    )


def button_listener_function_caller_templates(midi_map: TrackNavMidiMapping):
    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    button_name = f"button_{midi_map.info_string()}"
    button_listener_name = f"button_{midi_map.info_string()}_value"

    creation.append(f"self.{button_name} = {midi_map.only_midi_coord.create_button_element()}")
    setup_listeners.append(f"self.{button_name}.add_value_listener(self.{button_listener_name})")
    remove_listeners.append(f"self.{button_name}.remove_value_listener(self.{button_listener_name})")
    listener_fns.extend(generate_button_listener_function_action(button_listener_name, midi_map.template_function_name(), midi_map.info_string()))

    return GeneratedCode(
        [], creation, listener_fns, setup_listeners, remove_listeners
    )


def track_nav_templates(track_nav_with_midi: TrackNavWithMidi) -> GeneratedCode:
    codes = [button_listener_function_caller_templates(m) for m in track_nav_with_midi.midi_maps]
    return GeneratedCode.merge_all(codes)


def device_nav_templates(deivce_nav_with_midi: DeviceNavWithMidi) -> GeneratedCode:
    codes = [button_listener_function_caller_templates(m) for m in deivce_nav_with_midi.midi_maps]
    return GeneratedCode.merge_all(codes)


def device_templates(device_with_midi: DeviceWithMidi):
    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    lom = build_live_api_lookup_from_lom(device_with_midi.track, device_with_midi.device)

    for g in device_with_midi.midi_range_maps:
        enc_name = f"encoder_{g.info_string()}"
        enc_listener_name = f"encoder_{g.info_string()}_value"

        creation.append(f"self.{enc_name} = {g.midi_coords.create_encoder_element()}")
        setup_listeners.append(f"self.{enc_name}.add_value_listener(self.{enc_listener_name})")
        remove_listeners.append(f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})")
        listener_fns.extend(generate_lom_listener_action(g.parameter, lom, enc_listener_name, g.info_string()))

    return GeneratedCode(
        [], creation, listener_fns, setup_listeners, remove_listeners
    )


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
    return f"\n{tab_block}{tab_block}".join(lines) + "\n"
