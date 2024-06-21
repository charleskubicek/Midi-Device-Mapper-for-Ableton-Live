from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement

# from _Framework.ButtonElement import OFF_VALUE, ON_VALUE
# import _Framework.ButtonElement as ButtonElementBase


# from _Framework.EncoderElement import *

class CustomOps(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "custopm_ops"

        self.manager = manager
        self.mixer = MixerComponent(124, 24)
        # self.setup_controls()
        # self.setup_listeners()

    def remove_all_listeners(self):
        self.log_message("removing listeners")
        self.encoder_21.remove_value_listener(self.encoder_21_value)
        self.encoder_22.remove_value_listener(self.encoder_22_value)
        self.encoder_23.remove_value_listener(self.encoder_23_value)
        self.encoder_24.remove_value_listener(self.encoder_24_value)

        self.encoder_2_5_sends.remove_value_listener(self.encoder_2_5_sends_listener)

        self.mixer.selected_strip().set_mute_button(None)
        self.mixer.selected_strip().set_solo_button(None)
        self.mixer.selected_strip().set_volume_control(None)
        # self.encoder_25.remove_value_listener(self.encoder_21_value)
        # self.encoder_26.remove_value_listener(self.encoder_21_value)

    def setup_controls(self):

        self.encoder_21 = EncoderElement(MIDI_CC_TYPE, 1, 21, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_22 = EncoderElement(MIDI_CC_TYPE, 1, 22, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_23 = EncoderElement(MIDI_CC_TYPE, 1, 23, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_24 = EncoderElement(MIDI_CC_TYPE, 1, 24, Live.MidiMap.MapMode.relative_binary_offset)

        self.encoder_2_44_volume = EncoderElement(MIDI_CC_TYPE, 1, 44, Live.MidiMap.MapMode.relative_binary_offset)
        self.encoder_2_43_master_volume = EncoderElement(MIDI_CC_TYPE, 1, 43, Live.MidiMap.MapMode.relative_binary_offset)

        self.encoder_2_5_sends = EncoderElement(MIDI_CC_TYPE, 1, 25, Live.MidiMap.MapMode.relative_binary_offset)

        self.controller_LED_on = 127
        self.controller_LED_off = 0
        self.led_on = 120
        self.led_off = 0

        is_momentary=True
        self.button1 = ConfigurableButtonElement(is_momentary, MIDI_CC_TYPE, 1, 60)
        self.button2 = ConfigurableButtonElement(is_momentary, MIDI_CC_TYPE, 1, 61)
        self.button1.set_on_off_values(self.led_on, self.led_off)
        self.button2.set_on_off_values(self.led_on, self.led_off)

        # self.encoder_25 = EncoderElement(MIDI_NOTE_TYPE, 1, 29, Live.MidiMap.MapMode.relative_binary_offset)
        # self.encoder_26 = EncoderElement(MIDI_NOTE_TYPE, 1, 31, Live.MidiMap.MapMode.relative_binary_offset)
        # self.button_36 = ConfigurableButtonElement(MIDI_NOTE_TYPE, 1, 36)
        # self.button_37 = ConfigurableButtonElement(MIDI_NOTE_TYPE, 1, 37)


        self.mixer.selected_strip().set_mute_button(self.button1)
        self.mixer.selected_strip().set_solo_button(self.button2)
        self.mixer.selected_strip().set_volume_control(self.encoder_2_44_volume)

        self.mixer.master_strip().set_volume_control(self.encoder_2_43_master_volume)
        # sends = self._track.mixer_device.sends[0]

        self.setup_listeners()

    def setup_listeners(self):
        self.manager.log_message("Setting up listeners")
        self.encoder_21.add_value_listener(self.encoder_21_value)
        self.encoder_22.add_value_listener(self.encoder_22_value)
        self.encoder_23.add_value_listener(self.encoder_23_value)
        self.encoder_24.add_value_listener(self.encoder_24_value)

        self.encoder_2_5_sends.add_value_listener(self.encoder_2_5_sends_listener)
        # self.button1.add_value_listener(self.button1_value)


    def log_message(self, message):
        self.manager.log_message(message)



    def encoder_2_5_sends_listener(self, value):
        self.log_message(f"encoder_17_value value = {value}")
        self.log_message(f"encoder_17_value max = {self.manager.song().view.selected_track.mixer_device.sends[0].max}")
        self.log_message(f"encoder_17_value min = {self.manager.song().view.selected_track.mixer_device.sends[0].min}")


        self.song().view.selected_track.mixer_device.sends[0].value = float(value) / 128.0

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


controller = {
    'on_led_midi': '77',
    'off_led_midi': '78',
    'control_groups': [
        {'layout': 'row',
         'number': 1,
         'type': 'knobs',
         'midi_channel': 2,
         'midi_type': "CC",
         'range': {'from': 21, 'to': 28}
         },
        {'layout': 'col',
         'number': 1,
         'type': 'buttons',
         'midi_channel': 2,
         'midi_type': "CC",
         'range': {'from': 21, 'to': 28}
         }
    ],
    'toggles':[
        'r2-4'
    ]
}
mode_mappings = {
    'mode_selector': 'r1-1',
    'shift': True,
    'modes': [
        {
            'name': 'device',
            'color': 'red',
            'mappings': []
        }
    ]
}
mappings = [
    {
        'type': 'mixer',
        'track': 'selected',
        'mappings': {
            'volume': "r2-3",
            'pan': "r2-4",
            'sends': [
                {'1': "r2-4"},
                {'2': "r3-4"},
                {'3': "r2-5"},
                {'4': "r3-5"},
            ]
        }
    },
    {
        'type': 'transport',
        'mappings': {
            'play/stop': "r2-3",
            'pan': "r2-4",
        }
    },
    {
        'type': 'function',
        'controller': "r2-3",
        'function': 'functions.volume',
        'value_mapper': {
            'max': 30,
            'min': 12
        }
    },
    {
        'type': 'nav-device',
        'left': "r2-3",
        'right': "r2-4"
    },
    {
        'type': 'nav-track',
        'left': "r2-3",
        'right': "r2-4"
    },
    {
        'type': 'lom',
        'controller': "r2-3",
        'function': 'track.master.device.utility',
        'value_mapper': {
            'max': 30,
            'min': 12
        }
    },
    {
        'type': 'device',
        'lom': 'tracks.selected.device.selected',
        'range_maps': [
            {
                "row": 2,
                "range": {'from': 1, 'to': 9},
                "parameters": {'from': 1, 'to': 9},
            },
            {
                "row": 3,
                "range": {'from': 1, 'to': 9},
                "parameters": {'from': 9, 'to': 17},
            }
        ]
    },
    {
        'type': 'device',
        'lom': 'tracks.master.device.Mono',
        'controller': 'r5-1',
        'parameter': 0,
        'toggle': False
    },
    {
        'type': 'device',
        'lom': 'tracks.master.device.#1',
        'controller': 'r5-1',
        'parameter': 0,
        'toggle': True
    }
]