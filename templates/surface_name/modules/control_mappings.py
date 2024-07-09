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


class ControlMappings(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "control_mappings"

        self.manager = manager

        self.mixer = MixerComponent(124, 24)
        # self.setup_controls()
        # self.setup_listeners()

        if functions_loaded_error is not None:
            self.log_message(f"Error loading functions: {functions_loaded_error}")
        else:
            self.functions = Functions(self)

        self._song = self.manager.song()

    def remove_all_listeners(self):
        self.encoder_ch3_no21_CC__p1.remove_value_listener(self.encoder_ch3_no21_CC__p1_value)
        self.encoder_ch3_no22_CC__p2.remove_value_listener(self.encoder_ch3_no22_CC__p2_value)
        self.encoder_ch3_no23_CC__p3.remove_value_listener(self.encoder_ch3_no23_CC__p3_value)
        self.encoder_ch3_no24_CC__p4.remove_value_listener(self.encoder_ch3_no24_CC__p4_value)
        self.encoder_ch3_no25_CC__p5.remove_value_listener(self.encoder_ch3_no25_CC__p5_value)
        self.encoder_ch3_no26_CC__p6.remove_value_listener(self.encoder_ch3_no26_CC__p6_value)
        self.encoder_ch3_no27_CC__p7.remove_value_listener(self.encoder_ch3_no27_CC__p7_value)
        self.encoder_ch3_no28_CC__p8.remove_value_listener(self.encoder_ch3_no28_CC__p8_value)
        self.encoder_ch3_no29_CC__p9.remove_value_listener(self.encoder_ch3_no29_CC__p9_value)
        self.encoder_ch3_no42_CC__p10.remove_value_listener(self.encoder_ch3_no42_CC__p10_value)
        self.encoder_ch3_no43_CC__p11.remove_value_listener(self.encoder_ch3_no43_CC__p11_value)
        self.encoder_ch3_no44_CC__p12.remove_value_listener(self.encoder_ch3_no44_CC__p12_value)
        self.encoder_ch3_no45_CC__p13.remove_value_listener(self.encoder_ch3_no45_CC__p13_value)
        self.encoder_ch3_no46_CC__p14.remove_value_listener(self.encoder_ch3_no46_CC__p14_value)
        self.encoder_ch3_no47_CC__p15.remove_value_listener(self.encoder_ch3_no47_CC__p15_value)
        self.encoder_ch3_no48_CC__p16.remove_value_listener(self.encoder_ch3_no48_CC__p16_value)
        self.button_function_press_rack_random_button_ch9_43_note.remove_value_listener(
            self.button_function_press_rack_random_button_ch9_43_note_value)

    def setup_controls(self):
        self.encoder_ch3_no21_CC__p1 = EncoderElement(MIDI_CC_TYPE, 2, 21, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no22_CC__p2 = EncoderElement(MIDI_CC_TYPE, 2, 22, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no23_CC__p3 = EncoderElement(MIDI_CC_TYPE, 2, 23, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no24_CC__p4 = EncoderElement(MIDI_CC_TYPE, 2, 24, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no25_CC__p5 = EncoderElement(MIDI_CC_TYPE, 2, 25, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no26_CC__p6 = EncoderElement(MIDI_CC_TYPE, 2, 26, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no27_CC__p7 = EncoderElement(MIDI_CC_TYPE, 2, 27, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no28_CC__p8 = EncoderElement(MIDI_CC_TYPE, 2, 28, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no29_CC__p9 = EncoderElement(MIDI_CC_TYPE, 2, 29, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no42_CC__p10 = EncoderElement(MIDI_CC_TYPE, 2, 42, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no43_CC__p11 = EncoderElement(MIDI_CC_TYPE, 2, 43, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no44_CC__p12 = EncoderElement(MIDI_CC_TYPE, 2, 44, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no45_CC__p13 = EncoderElement(MIDI_CC_TYPE, 2, 45, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no46_CC__p14 = EncoderElement(MIDI_CC_TYPE, 2, 46, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no47_CC__p15 = EncoderElement(MIDI_CC_TYPE, 2, 47, Live.MidiMap.MapMode.absolute)
        self.encoder_ch3_no48_CC__p16 = EncoderElement(MIDI_CC_TYPE, 2, 48, Live.MidiMap.MapMode.absolute)
        self.button_function_press_rack_random_button_ch9_43_note = ConfigurableButtonElement(True, MIDI_NOTE_TYPE, 8,
                                                                                              43)

        self.setup_listeners()

    def setup_listeners(self):
        self.log_message("Setting up listeners")
        self.encoder_ch3_no21_CC__p1.add_value_listener(self.encoder_ch3_no21_CC__p1_value)
        self.encoder_ch3_no22_CC__p2.add_value_listener(self.encoder_ch3_no22_CC__p2_value)
        self.encoder_ch3_no23_CC__p3.add_value_listener(self.encoder_ch3_no23_CC__p3_value)
        self.encoder_ch3_no24_CC__p4.add_value_listener(self.encoder_ch3_no24_CC__p4_value)
        self.encoder_ch3_no25_CC__p5.add_value_listener(self.encoder_ch3_no25_CC__p5_value)
        self.encoder_ch3_no26_CC__p6.add_value_listener(self.encoder_ch3_no26_CC__p6_value)
        self.encoder_ch3_no27_CC__p7.add_value_listener(self.encoder_ch3_no27_CC__p7_value)
        self.encoder_ch3_no28_CC__p8.add_value_listener(self.encoder_ch3_no28_CC__p8_value)
        self.encoder_ch3_no29_CC__p9.add_value_listener(self.encoder_ch3_no29_CC__p9_value)
        self.encoder_ch3_no42_CC__p10.add_value_listener(self.encoder_ch3_no42_CC__p10_value)
        self.encoder_ch3_no43_CC__p11.add_value_listener(self.encoder_ch3_no43_CC__p11_value)
        self.encoder_ch3_no44_CC__p12.add_value_listener(self.encoder_ch3_no44_CC__p12_value)
        self.encoder_ch3_no45_CC__p13.add_value_listener(self.encoder_ch3_no45_CC__p13_value)
        self.encoder_ch3_no46_CC__p14.add_value_listener(self.encoder_ch3_no46_CC__p14_value)
        self.encoder_ch3_no47_CC__p15.add_value_listener(self.encoder_ch3_no47_CC__p15_value)
        self.encoder_ch3_no48_CC__p16.add_value_listener(self.encoder_ch3_no48_CC__p16_value)
        self.button_function_press_rack_random_button_ch9_43_note.add_value_listener(
            self.button_function_press_rack_random_button_ch9_43_note_value)

        self.mode_button.add_value_listener(self.mode_listener)

    def mode_listener(self, value):
        last_mode = self.mode()
        self.mode = self.mode.next_mode()
        if self.mode == 1:
            self.encoder_ch3_no48_CC__p16.remove_value_listener(self.encoder_m1_ch3_no48_CC__p16_value)
            self.encoder_ch3_no48_CC__p16.remove_value_listener(self.encoder_m1_ch3_no48_CC__p16_value)

            self.encoder_ch3_no48_CC__p16.remove_value_listener(self.encoder_m2_ch3_no48_CC__p16_value)

            self.mixer.master_strip().set_volume_control(None)

            self.setup_mode_x_listeners()

        def setup_mode_x_listeners(self):

    def setup_controls(self):
        self.ch3_21_CC = EncoderElement(MIDI_CC_TYPE, 2, 21, Live.MidiMap.MapMode.absolute)
        self.ch3_22_CC = EncoderElement(MIDI_CC_TYPE, 2, 22, Live.MidiMap.MapMode.absolute)
        self.ch3_23_CC = EncoderElement(MIDI_CC_TYPE, 2, 23, Live.MidiMap.MapMode.absolute)

    def setup_listeners_for_mode_1(self):
        self.log_message("Setting up listeners")


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
            self.log_message(
                f"Device param min:{device.parameters[parameter_no].min}, max: {device.parameters[parameter_no].max}")

        device.parameters[parameter_no].value = value

    def encoder_ch3_no21_CC__p1_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 1, value, "encoder_ch3_no21_CC__p1_value")

    def encoder_ch3_no22_CC__p2_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 2, value, "encoder_ch3_no22_CC__p2_value")

    def encoder_ch3_no23_CC__p3_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 3, value, "encoder_ch3_no23_CC__p3_value")

    def encoder_ch3_no24_CC__p4_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 4, value, "encoder_ch3_no24_CC__p4_value")

    def encoder_ch3_no25_CC__p5_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 5, value, "encoder_ch3_no25_CC__p5_value")

    def encoder_ch3_no26_CC__p6_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 6, value, "encoder_ch3_no26_CC__p6_value")

    def encoder_ch3_no27_CC__p7_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 7, value, "encoder_ch3_no27_CC__p7_value")

    def encoder_ch3_no28_CC__p8_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 8, value, "encoder_ch3_no28_CC__p8_value")

    def encoder_ch3_no29_CC__p9_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 9, value, "encoder_ch3_no29_CC__p9_value")

    def encoder_ch3_no42_CC__p10_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 10, value, "encoder_ch3_no42_CC__p10_value")

    def encoder_ch3_no43_CC__p11_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 11, value, "encoder_ch3_no43_CC__p11_value")

    def encoder_ch3_no44_CC__p12_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 12, value, "encoder_ch3_no44_CC__p12_value")

    def encoder_ch3_no45_CC__p13_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 13, value, "encoder_ch3_no45_CC__p13_value")

    def encoder_ch3_no46_CC__p14_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 14, value, "encoder_ch3_no46_CC__p14_value")

    def encoder_ch3_no47_CC__p15_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 15, value, "encoder_ch3_no47_CC__p15_value")

    def encoder_ch3_no48_CC__p16_value(self, value):
        device = self.manager.song().view.selected_track.view.selected_device
        self.device_parameter_action(device, 16, value, "encoder_ch3_no48_CC__p16_value")

        # function_press_rack_random_button_ch9_43_note

    def button_function_press_rack_random_button_ch9_43_note_value(self, value):
        if self.manager.debug:
            self.log_message(
                f"button_function_press_rack_random_button_ch9_43_note_value (function_press_rack_random_button_ch9_43_note) callee = self.functions.press_rack_random_button(), value is {value}")

        self.functions.press_rack_random_button()
