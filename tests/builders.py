from typing import List

from ableton_control_suface_as_code.model_v1 import MixerMappingsV1, MixerV1
from ableton_control_suface_as_code.core_model import MixerMidiMapping, ControlTypeEnum, MidiTypeEnum, MixerWithMidi
from ableton_control_suface_as_code.model_v1 import MixerV1, MixerMidiMapping

class MixerMidiMappingBuilder:
    def __init__(self):
        self._midi_channel = 1
        self._midi_number = 1
        self._midi_type = MidiTypeEnum.midi
        self._controller_type = ControlTypeEnum.button
        self._api_function = "volume"
        self._selected_track = True
        self._tracks = None
        self._encoder_coords = "r1-1"

    def midi_channel(self, midi_channel):
        self._midi_channel = midi_channel
        return self

    def midi_number(self, midi_number):
        self._midi_number = midi_number
        return self

    def midi_type(self, midi_type):
        self._midi_type = midi_type
        return self

    def midi_info(self, chan, no, midi_type):
        self._midi_channel = chan
        self._midi_number = no
        self._midi_type = MidiTypeEnum[midi_type]
        return self

    def controller_type(self, controller_type):
        self._controller_type = controller_type
        return self

    def api_function(self, api_function):
        self._api_function = api_function
        return self

    def selected_track(self, selected_track):
        self._selected_track = selected_track
        return self

    def tracks(self, tracks):
        self._tracks = tracks
        return self

    def encoder_coords(self, encoder_coords):
        self._encoder_coords = encoder_coords
        return self


    def build(self):
        return MixerMidiMapping(
            midi_channel=self._midi_channel,
            midi_number=self._midi_number,
            midi_type=self._midi_type,
            controller_type=self._controller_type,
            api_function=self._api_function,
            selected_track=self._selected_track,
            tracks=self._tracks,
            encoder_coords=self._encoder_coords
        )

#     @property
#     def api_function_val(self):
#         return self._api_function
#
#
# class MixerMappingsBuilder:
#     def __init__(self):
#         self._volume = None
#         self._pan = None
#         self._mute = None
#         self._solo = None
#         self._arm = None
#         self._sends = None
#
#     def volume(self, volume):
#         self._volume = volume
#         return self
#
#     def pan(self, pan):
#         self._pan = pan
#         return self
#
#     def mute(self, mute):
#         self._mute = mute
#         return self
#
#     def solo(self, solo):
#         self._solo = solo
#         return self
#
#     def arm(self, arm):
#         self._arm = arm
#         return self
#
#     def sends(self, sends:List[str]):
#         self._sends = sends
#         return self
#
#     def build(self):
#         return MixerMappings(
#             volume=self._volume,
#             pan=self._pan,
#             mute=self._mute,
#             solo=self._solo,
#             arm=self._arm,
#             sends=self._sends
#         )
#
# class MixerBuilder:
#     def __init__(self):
#         self._type = 'mixer'
#         self._track = None
#         self._mappings_builder = MixerMappingsBuilder()
#
#     def track(self, track):
#         self._track = track
#         return self
#
#     def mappings(self, mappings:MixerMappingsBuilder):
#         self._mappings_builder = mappings
#         return self
#
#     def mappings2(self, mappings:{}):
#
#
#     def build(self):
#         return Mixer(
#             type=self._type,
#             track=self._track,
#             mappings=self._mappings_builder.build()
#         )
#
# class MixerWithMidiBuilder:
#     def __init__(self):
#         self._type = 'mixer'
#         self._mixer_builder = MixerBuilder().build()
#         self._midi_map_builders = []
#
#     def type(self, type):
#         self._type = type
#         return self
#
#     def mixer_builder(self, mixer_builder):
#         self._mixer_builder = mixer_builder
#         return self
#
#     def midi_maps(self, midi_mapping_builders):
#         self._midi_map_builders = midi_mapping_builders
#         return self
#
#     def build(self) -> MixerWithMidi:
#         return MixerWithMidi(
#             type=self._type,
#             mixer=self._mixer_builder.build(),
#             midi_maps=[x.build() for x in self._midi_map_builders]
#         )