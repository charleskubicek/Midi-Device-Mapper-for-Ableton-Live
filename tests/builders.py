from ableton_control_suface_as_code.core_model import MixerWithMidi, MixerMidiMapping, MidiCoords, EncoderType, \
    EncoderCoords, TrackInfo, MidiType, Direction
from ableton_control_suface_as_code.model_controller import ControllerV2, ControllerRawV2, ControlGroupPartV2
from ableton_control_suface_as_code.model_device import DeviceWithMidi, DeviceMidiMapping
from ableton_control_suface_as_code.model_functions import FunctionsWithMidi, FunctionsMidiMapping
from ableton_control_suface_as_code.model_track_nav import TrackNavWithMidi, TrackNavMidiMapping


def midi_coords_ch2_cc_50_knob(encoder_override=EncoderType.knob):
    return MidiCoords(channel=2, type='CC', number=50, encoder_type=encoder_override)


def encoder_coords_1_2():
    return EncoderCoords(row=1, col=2, row_range_end=2)


def build_track_nav_with_midi_button(midi_coords=midi_coords_ch2_cc_50_knob(EncoderType.button)):
    return TrackNavWithMidi(midi_maps=[TrackNavMidiMapping(
        midi_coords=[midi_coords],
        direction=Direction.inc
    )])

def build_1_group_controller(midi_range='21-28'):
    return ControllerV2.build_from(ControllerRawV2(
        light_colors={},
        control_groups=[ControlGroupPartV2(
            layout='row',
            number=1,
            type=EncoderType.knob,
            midi_channel=2,
            midi_type=MidiType.CC,
            midi_range=midi_range
        )]))


def build_device_midi_mapping(midi_channel=2, midi_number=10, midi_type="CC", parameter=1,
                              encoder_type=EncoderType.knob):
    return DeviceMidiMapping(
        midi_coords=[MidiCoords(channel=midi_channel, type=midi_type, number=midi_number, encoder_type=encoder_type)],
        parameter=parameter)


def build_midi_device_mapping(midi_coords=midi_coords_ch2_cc_50_knob(), param=1):
    return DeviceWithMidi(
        track=TrackInfo.selected(),
        device="selected",
        midi_range_maps=[DeviceMidiMapping(
            midi_coords=midi_coords,
            parameter=param
        )])


def build_mixer_with_midi(
        api_fn="pan",
        midi_coord=midi_coords_ch2_cc_50_knob(),
        encoder_coords=encoder_coords_1_2()
) -> MixerWithMidi:
    return MixerWithMidi(
        midi_maps=[MixerMidiMapping(
            midi_coords=[midi_coord],
            controller_type=EncoderType.knob,
            api_function=api_fn,
            encoder_coords=encoder_coords,
            track_info=TrackInfo.selected()
        )])


def build_mixer_with_multiple_mappings(chan=2, nos=[], type="CC", api_fn="pan", enocder_type=EncoderType.knob,
                                       track_info=TrackInfo.selected()):

    col = 2
    return MixerWithMidi(
        midi_maps=[MixerMidiMapping(
            midi_coords=[MidiCoords(channel=chan, type=type, number=no, encoder_type=EncoderType.knob) for no in nos],
            api_function=api_fn,
            track_info=track_info,
            encoder_coords=EncoderCoords(row=1, col=col, row_range_end=(col + 1 + len(nos) - 1)),

        )])


def build_functions_with_midi(channel=1, number=51, type="CC", function="toggle") -> FunctionsWithMidi:
    return FunctionsWithMidi(midi_maps=[
        FunctionsMidiMapping(
            midi_coords=[MidiCoords(channel=channel, type=type, number=number, encoder_type=EncoderType.button)],
            function=function
        )
    ])
