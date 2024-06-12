from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement


# from _Framework.EncoderElement import *

class CustomOps(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "custopm_ops"

        self.manager = manager
        self.setup_controls()
        self.setup_listeners()

    def remove_all_listeners(self):
        self.encoder_21.remove_value_listener(self.encoder_21_value)
        self.encoder_22.remove_value_listener(self.encoder_22_value)
        self.encoder_23.remove_value_listener(self.encoder_23_value)
        self.encoder_24.remove_value_listener(self.encoder_24_value)
        # self.encoder_25.remove_value_listener(self.encoder_21_value)
        # self.encoder_26.remove_value_listener(self.encoder_21_value)

    def setup_controls(self):
        control_group_rows = [
            {'name': 'row 1',
             'type': 'knobs',
             'midi_channel': 2,
             'midi_type': "CC",
             'range': {'from': 21, 'to': 28}
             }
        ]
        mappings = [
            {}
        ]
        #
        # control_groups = []
        #
        # for control_group_data in control_groups_data:
        #     control_group = []
        #     for index in range(control_group_data['range']['from'], control_group_data['range']['to']):
        #         control_group.append(EncoderElement(MIDI_CC_TYPE, control_group_data['midi_channel'], index, Live.MidiMap.MapMode.relative_binary_offset))
        #     control_groups.append()

        self.encoder_21 = EncoderElement(MIDI_CC_TYPE, 1, 21, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_22 = EncoderElement(MIDI_CC_TYPE, 1, 22, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_23 = EncoderElement(MIDI_CC_TYPE, 1, 23, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_24 = EncoderElement(MIDI_CC_TYPE, 1, 24, Live.MidiMap.MapMode.relative_binary_offset)

        self.encoder_25 = EncoderElement(MIDI_NOTE_TYPE, 1, 29, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_26 = EncoderElement(MIDI_NOTE_TYPE, 1, 31, Live.MidiMap.MapMode.relative_binary_offset)
        # self.button_36 = ConfigurableButtonElement(MIDI_NOTE_TYPE, 1, 36)
        # self.button_37 = ConfigurableButtonElement(MIDI_NOTE_TYPE, 1, 37)

    def setup_listeners(self):
        self.manager.log_message("Setting up listeners")
        self.encoder_21.add_value_listener(self.encoder_21_value)
        self.encoder_22.add_value_listener(self.encoder_22_value)
        self.encoder_23.add_value_listener(self.encoder_23_value)
        self.encoder_24.add_value_listener(self.encoder_24_value)

    def log_message(self, message):
        self.manager.log_message(message)

    def encoder_21_value(self, value):
        selected_device = self.manager.song().view.selected_track.view.selected_device
        if selected_device is None:
            return

        self.log_message(f"encoder_21_value selected_device = {selected_device.name}")
        self.log_message(f"Encoder 21 value: {value} for encoder")
        # self.log_message(f"Encoder 21 actual: {float(value) / 128.0}")
        selected_device = self.manager.song().view.selected_track.view.selected_device
        self.log_message(f"encoder_21_value selected_device = {selected_device.name}")
        paramenter = 1
        if len(selected_device.parameters) < 1:
            self.log_message(f"{paramenter} too long, max is {len(selected_device.parameters)}")
            return

        selected_device.parameters[1].value = value

    def encoder_22_value(self, value):
        selected_device = self.manager.song().view.selected_track.view.selected_device
        if selected_device is None:
            return

        self.log_message(f"encoder_22_value selected_device = {selected_device.name}")
        self.log_message(f"Encoder 22 value: {value} for")
        # self.log_message(f"Encoder 22 actual: {float(value) / 128.0}")
        selected_device = self.manager.song().view.selected_track.view.selected_device
        self.log_message(f"encoder_22_value selected_device = {selected_device.name}")
        paramenter = 1
        if len(selected_device.parameters) < 2:
            self.log_message(f"{paramenter} too long, max is {len(selected_device.parameters)}")
            return

        selected_device.parameters[2].value = value



    def encoder_23_value(self, value):
        selected_device = self.manager.song().view.selected_track.view.selected_device
        if selected_device is None:
            return

        self.log_message(f"encoder_23_value selected_device = {selected_device.name}")
        self.log_message(f"Encoder 23 value: {value} for")
        # self.log_message(f"Encoder 23 actual: {float(value) / 128.0}")
        selected_device = self.manager.song().view.selected_track.view.selected_device
        self.log_message(f"encoder_23_value selected_device = {selected_device.name}")
        paramenter = 1
        if len(selected_device.parameters) < 3:
            self.log_message(f"{paramenter} too long, max is {len(selected_device.parameters)}")
            return

        selected_device.parameters[3].value = value

    def encoder_24_value(self, value):
        selected_device = self.manager.song().view.selected_track.view.selected_device
        if selected_device is None:
            return

        self.log_message(f"encoder_24_value selected_device = {selected_device.name}")
        self.log_message(f"Encoder 24 value: {value} for")
        # self.log_message(f"Encoder 24 actual: {float(value) / 128.0}")
        selected_device = self.manager.song().view.selected_track.view.selected_device
        self.log_message(f"encoder_24_value selected_device = {selected_device.name}")
        paramenter = 1
        if len(selected_device.parameters) < 4:
            self.log_message(f"{paramenter} too long, max is {len(selected_device.parameters)}")
            return


        selected_device.parameters[4].value = value

