from dataclasses import dataclass
import ast
from dataclasses import dataclass
from string import Template

from ableton_control_suface_as_code.core_model import DeviceWithMidi, MixerWithMidi, MidiCoords


@dataclass
class GeneratedCode:
    setup: [str]
    creation: [str]
    listener_fns: [str]
    setup_listeners: [str]
    remove_listeners: [str]

    def merge(self, other):
        return GeneratedCode(
            self.setup + other.setup,
            self.creation + other.creation,
            self.listener_fns + other.listener_fns,
            self.setup_listeners + other.setup_listeners,
            self.remove_listeners + other.remove_listeners
        )


def generate_listener_action(parameter, lom, fn_name, debug_st) -> [str]:
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

def button_element(midi_coords:MidiCoords):
    return f"ConfigurableButtonElement(True, {midi_coords.type.ableton_name()}, {midi_coords.ableton_channel()}, {midi_coords.number})"

def encoder_element(midi_coords:MidiCoords):
    return f"EncoderElement({midi_coords.type.ableton_name()}, {midi_coords.ableton_channel()}, {midi_coords.number}, Live.MidiMap.MapMode.absolute)"


def mixer_templates(mixer_with_midi:MixerWithMidi) -> GeneratedCode:

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
            if midi_map.selected_track:
                #TODO fix momentary/toggle
                bn = f"button_{midi_map.info_string()}"
                creation.append(f"self.{bn} = {button_element(midi_map.midi_coords[0])}")
                creation.append(f"self.{bn}.set_on_off_values(self.led_on, self.led_off)")

                setup_listeners.append(f"self.mixer.selected_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(self.{bn})")
                remove_listeners.append(f"self.mixer.selected_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(None)")
            else:
                print("Button on number track not implemented")
        else:
            if midi_map.selected_track:
                if midi_map.api_function == "sends":
                    sends_var = f"send_controls_{midi_map.info_string()}"
                    sends_len = len(midi_map.midi_coords)
                    creation.append(f"self.{sends_var} = [None] * {sends_len}")

                    #TODO sends lenth max of midi range or actual sends size

                    for i, midi in enumerate(midi_map.midi_coords):
                        creation.append(f"self.{sends_var}[{i}] = {encoder_element(midi)}")

                    setup_listeners.append(f"self.mixer.selected_strip().set_send_controls(self.{sends_var})")
                    remove_listeners.append(f"self.mixer.selected_strip().set_send_controls(None)")
                else:
                    cn = f"encodr_{midi_map.info_string()}"

                    creation.append(f"self.{cn} = {encoder_element(midi_map.midi_coords[0])}")
                    setup_listeners.append(f"self.mixer.selected_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(self.{cn})")
                    remove_listeners.append(f"self.mixer.selected_strip().set_{midi_map.api_function}_{midi_map.api_control_type}(None)")




    return GeneratedCode(
        setup, creation, listener_fns, setup_listeners, remove_listeners
    )

def device_templates(device_with_midi: DeviceWithMidi):

    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    lom = build_live_api_lookup_from_lom(device_with_midi.track, device_with_midi.device)

    for g in device_with_midi.midi_range_maps:
        enc_name = f"encoder_{g.info_string()}"
        enc_listener_name = f"encoder_{g.info_string()}_value"

        creation.append(f"self.{enc_name} = {encoder_element(g.midi_coords)}")
        setup_listeners.append(f"self.{enc_name}.add_value_listener(self.{enc_listener_name})")
        remove_listeners.append(f"self.{enc_name}.remove_value_listener(self.{enc_listener_name})")
        listener_fns.extend(generate_listener_action(g.parameter, lom, enc_listener_name, g.info_string()))

    return GeneratedCode(
        [], creation, listener_fns, setup_listeners, remove_listeners
    )


def is_valid_python(code):
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def build_live_api_lookup_from_lom(track, device):
    """"
        tracks.selected.device.selected
        tracks.1.device.1.


        self.manager.song().view.tracks[0].view.devices[0]
        self.manager.song().view.selected_track.view.selected_device
    """

    if track.isnumeric():
        track_st = f"tracks[{int(track)-1}]"
    elif track == 'selected':
        track_st = 'selected_track'
    else:
        print(f"can't parse track: {track}")
        exit(1)

    if device.isnumeric():
        device_st = f"devices[{int(device)-1}]"
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