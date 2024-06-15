from dataclasses import dataclass
import ast
from dataclasses import dataclass
from string import Template

from ableton_control_suface_as_code.model import DeviceWithMidi


@dataclass
class EncoderCode:
    creation: [str]
    listener_fns: [str]
    setup_listeners: [str]
    remove_listeners: [str]


def generate_listener_action(n, parameter, lom, debug_st) -> [str]:
    return Template("""
# $comment   
def encoder_${n}_value(self, value):
    selected_device = $lom
    if selected_device is None:
        return

    if self.manager.debug:
        self.log_message(f"encoder_${n}_value ($comment) selected_device = {selected_device.name}, value is {value}")
    
    selected_device = self.manager.song().view.selected_track.view.selected_device

    if len(selected_device.parameters) < $parameter:
        self.log_message(f"${parameter} too large, max is {len(selected_device.parameters)}")
        return

    selected_device.parameters[$parameter].value = value    
    """).substitute(n=n, parameter=parameter, lom=lom, comment=debug_st).split("\n")


def encoder_template(device_with_midi: DeviceWithMidi):
    encoder_count = 0

    creation = []
    listener_fns = []
    setup_listeners = []
    remove_listeners = []

    lom = build_live_api_lookup_from_lom(device_with_midi.device.lom)

    for g in device_with_midi.midi_range_maps:
        creation.append(
            f"self.encoder_{encoder_count} = EncoderElement({g.midi_type.ableton_name()}, {g.midi_channel-1}, {g.midi_number}, Live.MidiMap.MapMode.relative_binary_offset)")
        setup_listeners.append(f"self.encoder_{encoder_count}.add_value_listener(self.encoder_{encoder_count}_value)")
        remove_listeners.append(
            f"self.encoder_{encoder_count}.remove_value_listener(self.encoder_{encoder_count}_value)")
        listener_fns.extend(generate_listener_action(encoder_count, g.parameter, lom, g.debug_string()))
        encoder_count += 1

    return EncoderCode(
        creation, listener_fns, setup_listeners, remove_listeners
    )


def is_valid_python(code):
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def build_live_api_lookup_from_lom(lom):
    """"
        tracks.selected.device.selected
        tracks.1.device.1.


        self.manager.song().view.tracks[0].view.devices[0]
        self.manager.song().view.selected_track.view.selected_device
    """

    [_, track, _, device] = lom.split(".")

    if track.isnumeric():
        track_st = f"tracks[{track}]"
    elif track == 'selected':
        track_st = 'selected_track'
    else:
        print(f"can't parse track: {track}")
        exit(1)

    if device.isnumeric():
        device_st = f"devices[{device}]"
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
    tab_block = "    "
    return f"\n{tab_block}".join(lines) + "\n"

def class_function_body_code_block(lines: [str]):
    tab_block = "    "
    return f"\n{tab_block}{tab_block}".join(lines) + "\n"