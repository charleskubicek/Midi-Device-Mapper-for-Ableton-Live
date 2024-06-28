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

        self._song = self.manager.song()

        $code_setup


    def remove_all_listeners(self):
        $code_remove_listeners


    def setup_controls(self):
        $code_creation

        self.setup_listeners()

    def setup_listeners(self):
        self.log_message("Setting up listeners")
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
        view = self.manager.application.view
        if not view.is_view_visible('Detail') or not view.is_view_visible('Detail/DeviceChain'):
            view.show_view('Detail')
            view.show_view('Detail/DeviceChain')
        else:
            view.scroll_view(direction, 'Detail/DeviceChain', False)


    def track_nav_inc(self):
        all_tracks = len(self._song.tracks)
        selected_track = self._song.view.selected_track  # Get the currently selected track

        self.manager.log_message.info(f"Selected track name is {selected_track.name}")

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


    def device_parameter_action(self, device, parameter_no, value, fn_name):
        if device is None:
            return

        if len(device.parameters) < parameter_no:
            self.log_message(f"{parameter_no} too large, max is {len(device.parameters)}")
            return

        if self.manager.debug:
            self.log_message(f"{fn_name}: selected_device:{device.name}, value:{value}")
            self.log_message(f"Device param min:{device.parameters[parameter_no].min}, max: {device.parameters[parameter_no].max}")

        device.parameters[parameter_no].value = value


    $code_listener_fns
