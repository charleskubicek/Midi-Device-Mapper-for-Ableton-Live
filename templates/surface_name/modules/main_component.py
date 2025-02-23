from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement
from .helpers import Helpers
# from _Framework.EncoderElement import *

functions_loaded_error = None

try:
    from .functions import Functions
except Exception as e:
    functions_loaded_error = e

class MainComponent(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "main_component"

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

        code_custom_parameter_mappings = { 
            $code_custom_parameter_mappings
        }

        self._helpers = Helpers(self.manager, code_custom_parameter_mappings
                                )

        self._song.add_appointed_device_listener(self.on_device_selected)


        self.log_message(f"main_component finish init.")
        self._previous_values = {}


    def remove_all_listeners(self, modes_only=False):
        $code_remove_listeners

    def debug(self):
        return self.manager.debug

    def setup_controls(self):
        $code_creation


$code_setup_listeners

    def log_message(self, message):
        self.manager.log_message(message)

    def selected_device(self):
        return self._song.view.selected_track.view.selected_device

    def device_nav_left(self):
        NavDirection = Live.Application.Application.View.NavDirection
        self._scroll_device_chain(NavDirection.left)
        self._helpers.selected_device_changed(self.selected_device())

    def device_nav_right(self):
        NavDirection = Live.Application.Application.View.NavDirection
        self._scroll_device_chain(NavDirection.right)
        self._helpers.selected_device_changed(self.selected_device())

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

        self._helpers.selected_device_changed(self.selected_device())

    def track_nav_dec(self):
        selected_track = self._song.view.selected_track  # Get the currently selected track

        if selected_track.name == "Master":
            next_index = len(list(self._song.tracks)) - 1
        else:
            next_index = list(self._song.tracks).index(selected_track) - 1  # Get the index of the selected track

        if next_index >= 0:
            self._song.view.selected_track = self._song.tracks[next_index]

        self._helpers.selected_device_changed(self.selected_device())


    def device_nav_first_last(self):
        devices = self._song.view.selected_track.devices

        if len(devices) == 0:
            return

        if self.selected_device() != devices[0]:
            self.device_nav_first()
        else:
            self.device_nav_last()

    def device_nav_first(self):
        NavDirection = Live.Application.Application.View.NavDirection
        devices = self._song.view.selected_track.devices

        for i in range(0, len(devices) + 3):
            self._scroll_device_chain(NavDirection.left)

        self._helpers.selected_device_changed(self.selected_device())

    def device_nav_last(self):
        NavDirection = Live.Application.Application.View.NavDirection
        devices = self._song.view.selected_track.devices

        for i in range(0, len(devices) + 3):
            self._scroll_device_chain(NavDirection.right)

        self._scroll_device_chain(NavDirection.left)

        self._helpers.selected_device_changed(self.selected_device())

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

    def device_parameter_action(self, device, parameter_no, midi_no, value, fn_name, toggle=False):
        self._helpers.device_parameter_action(device, parameter_no, midi_no, value, fn_name, toggle)

    def find_device(self, track_name, device_name):
        return self._helpers.find_device(self._song, track_name, device_name)


    def mode_button_listener(self, value):
        self.log_message(f'mode_button_listener: {value}, current mode is {self.current_mode}')

        if value == 127:# and self._modes[current_mode['next_mode_name']]['is_shift'] is not True:
            self.goto_mode(self.current_mode['next_mode_name'])
        elif value == 0 and self.current_mode['is_shift']:
            self.goto_mode(self.current_mode['next_mode_name'])

    def on_device_selected(self):
        self._helpers.selected_device_changed(self.selected_device())

    def on_selected_track_changed(self):
        ### This is called when the selected track changes
        self._helpers.selected_device_changed(self.selected_device())