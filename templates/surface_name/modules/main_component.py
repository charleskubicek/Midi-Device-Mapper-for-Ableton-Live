from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement
from .helpers import Helpers, OSCMultiClient, OSCClient, Remote, NullOSCClient
from .hud_client import HudClient
from .listener import OSCListener
from .nav import Nav
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
        self._nav = Nav(self.manager)

        self._osc_client = NullOSCClient()

        if $remote_on:
            self._osc_client = OSCMultiClient([
                OSCClient(host='127.0.0.1'),
                OSCClient(host='192.168.68.84', port=5005)
            ])

        self._hud_client = HudClient()
        self._remote = Remote(self.manager, self._osc_client, self._hud_client)

        $code_setup

        code_slot_assignments = [
            $code_custom_parameter_mappings
        ]

        code_switch_slot_assignments = [
            $code_switch_parameter_mappings
        ]

        self._helpers = Helpers(self.manager, self._remote, code_slot_assignments, code_switch_slot_assignments, parameter_mappings_raw=$parameter_mappings_raw, encoder_slot_count=$encoder_slot_count, hud_cells=$hud_cells, mode_hud_labels=$mode_hud_labels)

        self._song.add_appointed_device_listener(self.on_device_selected)


        self.log_message(f"main_component finish init.")
        self._previous_values = {}

        self._lisetenr = OSCListener(self.manager, self.button_handler)

        self._song.view.add_selected_parameter_listener(self._on_selected_parameter_changed)

    def button_handler(self, button, send_value):
        value = 127 if send_value > 0.0 else 0

        self._helpers.device_parameter_action(self.selected_device(), button, -1, value, '<OSC Button Press>')

    def remove_all_listeners(self, modes_only=False):
        $code_remove_listeners

    def debug(self):
        return self.manager.debug

    def update_selected_device(self):
        self._helpers.selected_device_changed(self.selected_device())

    def setup_controls(self):
        $code_creation

    def _on_selected_parameter_changed(self):
        if self.manager.debug:
            param = self._song.view.selected_parameter
            if param is not None:
                if param.is_quantized:
                    items = ", items: " +", ".join(param.value_items)
                else:
                    items = ""
                self.log_message(f"Selected parameter changed:  {param.name} (value: {param.value}, min: {param.min}, max: {param.max}, is_quantized: {param.is_quantized}{items})")
            else:
                self.log_message("Selected parameter changed: None")

$code_setup_listeners

    def log_message(self, message):
        self.manager.log_message(message)

    def selected_device(self):
        return self._song.view.selected_track.view.selected_device

    def device_nav_left(self):
        self._nav.device_nav_left()
        self._helpers.selected_device_changed(self.selected_device())

    def device_nav_right(self):
        self._nav.device_nav_right()
        self._helpers.selected_device_changed(self.selected_device())

    def track_nav_inc(self):
        self._nav.track_nav_inc()
        self._helpers.selected_device_changed(self.selected_device())

    def track_nav_dec(self):
        self._nav.track_nav_dec()
        self._helpers.selected_device_changed(self.selected_device())

    def device_nav_first_last(self):
        self._nav.device_nav_first_last()

    def device_nav_first(self):
        self._nav.device_nav_first()
        self._helpers.selected_device_changed(self.selected_device())

    def device_nav_last(self):
        self._nav.device_nav_last()
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

        # HUD: refresh labels for the new mode's bindings (mixer/functions/etc.).
        # Device-bound slots are repopulated by the next selected_device_changed.
        self._helpers.refresh_hud_for_mode(next_mode_name, self.selected_device())

        self.manager.show_message(f'Switched to {next_mode_name}')

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