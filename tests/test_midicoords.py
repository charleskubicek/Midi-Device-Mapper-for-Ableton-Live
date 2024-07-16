import unittest
from ableton_control_surface_as_code.core_model import MidiCoords, EncoderType, MidiType, EncoderMode


class TestMidiCoords(unittest.TestCase):

    def setUp(self):
        self.midi_coords = MidiCoords(channel=1, number=21, type=MidiType.CC, encoder_type=EncoderType.knob, encoder_mode=EncoderMode.Absolute, source_info="tests")

    def test_ableton_channel(self):
        self.assertEqual(self.midi_coords.ableton_channel(), 0)

    def test_create_button_element(self):
        self.midi_coords.encoder_type = EncoderType.button
        self.assertEqual(self.midi_coords.create_button_element(), "ConfigurableButtonElement(True, MIDI_CC_TYPE, 0, 21)")

    def test_create_encoder_element(self):
        self.assertEqual(self.midi_coords.create_encoder_element(), "EncoderElement(MIDI_CC_TYPE, 0, 21, Live.MidiMap.MapMode.absolute)")

    def test_create_controller_element(self):
        self.assertEqual(self.midi_coords.create_controller_element(), "EncoderElement(MIDI_CC_TYPE, 0, 21, Live.MidiMap.MapMode.absolute)")

    def test_controller_variable_name(self):
        self.assertEqual(self.midi_coords.controller_variable_name(), "knob_ch1_21_CC")

    def test_controller_listener_fn_name(self):
        self.assertEqual(self.midi_coords.controller_listener_fn_name("mode1"), "knob_ch1_21_CC_mode1value")

    def test_info_string(self):
        self.assertEqual(self.midi_coords.info_string(), "ch1_21_CC")