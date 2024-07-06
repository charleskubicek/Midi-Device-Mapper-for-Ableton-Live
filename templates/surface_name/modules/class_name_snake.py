from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement

# from _Framework.EncoderElement import *

functions_loaded_error = None

try:
    from .functions import Functions
except Exception as e:
    functions_loaded_error = e

class $class_name_camel(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "$class_name_snake"

        self.manager = manager

        self.mixer = MixerComponent(124, 24)
        # self.setup_controls()
        # self.setup_listeners()

        if functions_loaded_error is not None:
            self.log_message(f"Error loading functions: {functions_loaded_error}")
        else:
            self.functions = Functions(self)

        self._modes = {}
        self._song = self.manager.song()

        $code_setup

        self.log_message(f"$class_name_snake finish init.")


    def remove_all_listeners(self, modes_only=False):
        $code_remove_listeners


    def setup_controls(self):
        $code_creation


$code_setup_listeners

    def log_message(self, message):
        self.manager.log_message(message)

    def device_nav_left(self):
        NavDirection = Live.Application.Application.View.NavDirection
        self._scroll_device_chain(NavDirection.left)

    def device_nav_right(self):
        NavDirection = Live.Application.Application.View.NavDirection
        self._scroll_device_chain(NavDirection.right)

    def _scroll_device_chain(self, direction):
        view = self.manager.application().view
        if not view.is_view_visible('Detail') or not view.is_view_visible('Detail/DeviceChain'):
            view.show_view('Detail')
            view.show_view('Detail/DeviceChain')
        else:
            view.scroll_view(direction, 'Detail/DeviceChain', False)


    def track_nav_inc(self):
        all_tracks = len(self._song.tracks)
        selected_track = self._song.view.selected_track  # Get the currently selected track

        self.manager.log_message(f"Selected track name is {selected_track.name}")

        if selected_track.name == "Master":
            self.manager.log_message("Can't increment from Master")

        next_index = list(self._song.tracks).index(selected_track) + 1  # Get the index of the selected track

        if next_index < all_tracks:
            self._song.view.selected_track = self._song.tracks[next_index]

    def track_nav_dec(self):
        selected_track = self._song.view.selected_track  # Get the currently selected track

        if selected_track.name == "Master":
            next_index = len(list(self._song.tracks)) - 1
        else:
            next_index = list(self._song.tracks).index(selected_track) - 1  # Get the index of the selected track

        if next_index >= 0:
            self._song.view.selected_track = self._song.tracks[next_index]


    def device_nav_first(self):
        NavDirection = Live.Application.Application.View.NavDirection
        devices = self._song.view.selected_track.devices

        for i in range(0, len(devices) + 3):
            self._scroll_device_chain(NavDirection.left)

    def device_nav_last(self):
        NavDirection = Live.Application.Application.View.NavDirection
        devices = self._song.view.selected_track.devices

        for i in range(0, len(devices) + 3):
            self._scroll_device_chain(NavDirection.right)

        self._scroll_device_chain(NavDirection.left)


    def device_parameter_action(self, device, parameter_no, value, fn_name, toggle=False):
        if device is None:
            return

        if len(device.parameters) < parameter_no:
            self.log_message(f"{parameter_no} too large, max is {len(device.parameters)}")
            return

        min = device.parameters[parameter_no].min
        max = device.parameters[parameter_no].max

        will_fire = not toggle or (toggle and value == 127)

        if toggle:
            current_value = device.parameters[parameter_no].value
            next_value = max if current_value == min else min
        else:
            next_value = self.normalise(value, min, max)

        if self.manager.debug:
            self.log_message(f"{fn_name}: selected_device:{device.name}, trigger value:{value}, next value:{next_value}")
            self.log_message(f"Device param min:{min}, max: {max}, will_fire:{will_fire}, current value is {device.parameters[parameter_no].value}")

        if will_fire:
            self.log_message(f"Setting to = {float(next_value)}")
            device.parameters[parameter_no].value = next_value

        self.log_message(f"Value is {device.parameters[parameter_no].value}")


    $code_listener_fns

    def goto_mode(self, next_mode_name):
        self.log_message(f'switching to {next_mode_name}')
        next_mode = self._modes[next_mode_name]
        self.log_message(f'next mode: {next_mode}')
        self.remove_all_listeners(modes_only=True)
        self._modes[next_mode_name]['add_listeners_fn']()

        if next_mode['color'] is not None:
            self.mode_button.send_value(next_mode['color'])
        else:
            self.mode_button.send_value(0)

        self.current_mode = next_mode

    def value_is_max(self, value, max):
        return value == max

    def normalise(self, midi_value, min_value, max_value):
        """
        Maps a MIDI value (0-127) to the given range [min_value, max_value].

        :param midi_value: int, The input MIDI value (0-127)
        :param min_value: int, The minimum value of the target range
        :param max_value: int, The maximum value of the target range
        :return: int, The mapped value within the range [min_value, max_value]
        """
        if min_value == max_value:
            return min_value

        # Normalize the MIDI value to a 0-1 range
        normalized_value = midi_value / 127.0

        # Map the normalized value to the target range
        mapped_value = min_value + normalized_value * (max_value - min_value)

        # Ensure the mapped value is within the target range
        mapped_value = round(mapped_value)
        return int(max(min_value, min(mapped_value, max_value)))

    def find_device(self, track_name, device_name):
        track = self.find_track(track_name)
        if track is not None:
            return self.find_device_on_track(track, device_name)

    def find_track(self, track_name):
        if track_name == "selected":
            return self.song().view.selected_track
        elif track_name == "master":
            return self.song().master_track
        elif track_name.isnumeric():
            return self.song().tracks[int(track_name)-1]


        for track in self.song().tracks:
            if track is not None and track.name == track_name:
                return track

        return None

    def find_device_on_track(self,  track, device_name):
        if device_name.isnumeric():
            return track.devices[int(device_name)-1]

        for device in track.devices:
            if device is not None and device.name == device_name:
                return device

        return None

    def mode_button_listener(self, value):
        self.log_message(f'mode_button_listener: {value}, current mode is {self.current_mode}')

        if value == 127:# and self._modes[current_mode['next_mode_name']]['is_shift'] is not True:
            self.goto_mode(self.current_mode['next_mode_name'])
        elif value == 0 and self.current_mode['is_shift']:
            self.goto_mode(self.current_mode['next_mode_name'])
