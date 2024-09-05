import traceback
from dataclasses import dataclass

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ControlSurface import ControlSurface
import Live
import time

from . import parsers
from . import sample_categories
from . import synth_categories


class Functions(ControlSurface):
    def __init__(self, c_instance=None, publish_self=True, *a, **k):
        super().__init__(c_instance=c_instance)
        # self._manager = c_instance

        self.clip_ops = ClipOps(self)
        self.perc_pattern_cycler = PatternCycler(self, Patterns.perc_patterns, self.clip_ops)
        self.midi_pattern_cycler = PatternCycler(self, Patterns.basic_midi_cycles, self.clip_ops)
        self.name_guesser = NameGuesser(self, self.song())
        self.arranger = Arranger(self)
        self.bounce = Bounce(self, self.clip_ops)
        self.record_midi = MidiRecord(self, self.song())

    # def log_message(self, message):
    #     self._manager.log_message(message)

    def selected_device(self):
        return self.song().view.selected_track.view.selected_device

    def press_rack_random_button(self):
        device = self.selected_device()

        if device is not None and device.can_have_chains:
            device.randomize_macros()

    def iterate_perc_pattern(self):
        self.perc_pattern_cycler.next()

    def iterate_midi_pattern(self):
        self.midi_pattern_cycler.next()

    def update_colors(self):
        self.name_guesser.update_track_names()

    def arrange(self):
        self.arranger.copy_all_to_arrangement()

    def selected_audio_to_simpler_in_new_track(self):
        self.bounce.selected_audio_to_simpler_in_new_track()

    def back8(self):
        self.song().jump_by(-8)

    def record_midi_from_track_to_new_track(self):
        self.record_midi.record_midi_from_track_to_new_track(self.song().view.selected_track)

class MidiRecord(ControlSurfaceComponent):

    def __init__(self, ins, song):
        ControlSurfaceComponent.__init__(self)
        self._manager = ins
        self._song = song


    def log_message(self, message):
        self._manager.log_message(message)

    def record_midi_from_track_to_new_track(self, source_track):
        """
        Records the MIDI output from one track into another track in Ableton Live.

        :param song: The current Ableton Live song instance (usually accessed via `self.song()` in a script).
        :param source_track_index: The index of the track from which MIDI will be recorded.
        :param destination_track_index: The index of the track where the MIDI will be recorded.
        """

        if source_track is None:
            raise ValueError("Source track cannot be None")

        song = self._song
        tracks = list(song.tracks)

        source_track_index = tracks.index(source_track)
        destination_track_index = source_track_index + 1

        # Ensure the track indices are valid
        if source_track_index < 0 or source_track_index >= len(song.tracks) or destination_track_index < 0 or destination_track_index >= len(song.tracks):
            raise ValueError("Invalid track index")


        song.create_midi_track(destination_track_index)
        destination_track = song.tracks[destination_track_index]

        # Ensure both tracks are MIDI tracks
        if not source_track.has_midi_input or not destination_track.has_midi_input:
            raise TypeError("Both tracks must be MIDI tracks")

        for i in destination_track.available_input_routing_types:
            self.log_message(f"  i = {i}, {i.display_name}")
            if i.display_name == source_track.name:
                destination_track.current_monitoring_state = 0
                destination_track.input_routing_type = i
                destination_track.arm = 1
                break
        else:
            self._control_surface.show_message("Couldn't configure Routing")

        # Set the destination track to monitor input (ensure it captures the MIDI from the source)

        # Get the first clip slot in the destination track (you could modify this to choose a different slot)
        clip_slot = destination_track.clip_slots[0]

        # Arm the destination track for recording
        destination_track.arm = True

        # Optionally, disarm all other tracks to avoid unintended recording
        for track in song.tracks:
            if track != destination_track:
                track.arm = False

        # Start playback (Live will begin recording the MIDI from the source track into the destination clip)
        source_track.clip_slots[0].fire()
        clip_slot.fire()


        # The duration of recording could be managed via polling or a callback, but for now:
        # Add some delay or mechanism to wait until recording is done, this could be a time delay or event check.


        # # After recording is complete, stop playback
        # song.stop_playing()
        #
        # # Disarm the destination track
        # destination_track.arm = False
        #
        # # Optionally, set the monitoring state back to auto
        # destination_track.current_monitoring_state = Live.Track.Track.monitoring_states.AUTO


class ClipOps(ControlSurfaceComponent):

    def __init__(self, ins):
        ControlSurfaceComponent.__init__(self)
        self._manager = ins


    def log_message(self, message):
        self._manager.log_message(message)

    def create_clip_and_notes(self, notes, title, length=4):
        '''
        Create a clip with the given notes and title.

        If its in the arrange view, add the notes to the selected clip.

        :param notes:
        :param title:
        :return:
        '''

        clip = self.get_or_create_selected_clip(length)
        if clip is not None:
            clip.loop_end = length  # a clip from arrangement might be different
            clip.remove_notes_extended(from_time=0, from_pitch=0, time_span=clip.loop_end, pitch_span=128)

            clip.add_new_notes(tuple(notes))
            clip.name = title


    def create_clip_and_copy_it_to_arrangement(self, track, pattern, song_time):
        self.log_message(f"Creating temp clip at {song_time}")
        try:
            for cs in track.clip_slots:
                if not cs.has_clip:
                    cs.create_clip(4)
                    clip = cs.clip

                    clip.add_new_notes(tuple(pattern))
                    clip.name = "C"

                    track.duplicate_clip_to_arrangement(clip, song_time)

                    return
        except Exception as e:
            self.log_message(f"failed to duplcate clip: {e}")

    def get_or_create_selected_clip(self, length, create=True, remove_existing=True):
        vw = self.application().view.focused_document_view
        # self.log("focused_document_view: " + str(vw))

        if vw == 'Arranger':

            tm = self.song().current_song_time
            self.log_message("current_song_time: " + str(tm))

            track = self.song().view.selected_track
            for clip in track.arrangement_clips:
                # self.log(f"is audio clip {clip.is_audio_clip})")
                # self.log(f"is audio clip {clip.is_midi_clip})")
                # self.log(f"start time {clip.start_time})")
                # self.log(f"start marker {clip.start_marker})")
                #
                # self.log(f"end time {clip.end_time})")
                # self.log(f"end marker {clip.loop_end})")
                # self.log(f"end time {str(clip)}")
                # self.log(f"loop end {clip.loop_end})")
                # self.log(f"end time {str(clip)}")

                if clip.is_midi_clip and clip.start_time <= tm < clip.end_time:
                    return clip

            self.create_clip_and_copy_it_to_arrangement(track, Patterns.c_line, tm)

        elif not self.song().view.highlighted_clip_slot.has_clip and create:
            self.song().view.highlighted_clip_slot.create_clip(float(length))
            clip = self.song().view.highlighted_clip_slot.clip

            return clip
        elif self.song().view.highlighted_clip_slot.has_clip:
            clip = self.song().view.highlighted_clip_slot.clip

            if remove_existing:
                clip.remove_notes_extended(from_time=0, from_pitch=0, time_span=clip.loop_end, pitch_span=128)

            return clip

        return None


class Bounce(ControlSurfaceComponent):

    def __init__(self, ins, clip_ops):
        ControlSurfaceComponent.__init__(self)
        self._manager = ins
        self._clip_ops = clip_ops

    def log_message(self, message):
        self._manager.log_message(message)

    def selected_audio_to_simpler_in_new_track(self):

        original_track_name = self.song().view.selected_track.name
        clip = self.song().view.highlighted_clip_slot.clip

        if clip is None or clip.is_midi_clip:
            # self._manager.show_message(f"No audio clip selected: {clip}")
            self.log_message(f"No audio clip selected: {clip}")
            return

        song_time = self.song().current_song_time
        new_track = self.audio_to_simpler(clip, original_track_name)

        if self.is_in_arrangement() and song_time is not None:
            self._clip_ops.create_clip_and_copy_it_to_arrangement(new_track, Patterns.c_line, song_time)
        else:
            self._clip_ops.create_clip_and_notes(Patterns.c_line, "C Line")

        self.delete_extra_default_devices(new_track)

    def delete_extra_default_devices(self, new_track):
        total_devices = len(new_track.devices)
        device_deletions = int((total_devices - 1) / 2)

        for i in range(0, device_deletions):
            self.log_message(
                f" deleting device at index: {len(new_track.devices) - 1}: {new_track.devices[len(new_track.devices) - 1].name}")
            new_track.delete_device(len(new_track.devices) - 1)


    def is_in_arrangement(self):
        vw = self.application().view.focused_document_view

        return vw == 'Arranger'

    def audio_to_simpler(self, clip, original_track_name):

        self.log_message("Starting audio to simpler")
        Live.Conversions.create_midi_track_with_simpler(self.song(), clip)
        self.log_message("audio to simpler convert")
        new_track = self.song().view.selected_track

        self.log_message(f"original track naame: {original_track_name}")
        self.log_message(f"     new track naame: {new_track.name}")
        new_track.name = original_track_name + " (Rec)"
        return new_track



class PatternCycler(ControlSurfaceComponent):
    def __init__(self, ins, patterns, clip_ops):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = ins
        self._patterns = patterns
        self._clip_ops = clip_ops

        self.counter = 0
        self.last_press = int(time.time())

    def was_used_within_window(self):
        return int(time.time()) - self.last_press < 4

    def next(self):
        if not self.was_used_within_window():
            self.counter = 0

        name, notes = self._patterns[self.counter]
        self._clip_ops.create_clip_and_notes(notes, name)
        self.counter = (self.counter + 1) % len(self._patterns)

        self.last_press = time.time()


@dataclass
class SimpleNote:
    vel: int
    pitch: int = 60
    duration: float = 0.25


def build_clip(note_spec):
    notes = []
    for pos, note in enumerate(note_spec):
        pos = float(pos) / 2
        if note != 0:
            notes.append(Live.Clip.MidiNoteSpecification(pitch=60, start_time=pos, duration=0.5,
                                                         velocity=127 * (note / float(9))))

    return notes


def to_live_note_spec(n: SimpleNote, start_time):
    return Live.Clip.MidiNoteSpecification(pitch=n.pitch, start_time=start_time, duration=n.duration, velocity=n.vel)


def sixteen_notes_to_spec_notes(notes):
    assert (len(notes) == 16)

    notes = [to_live_note_spec(n, (float(i) / 16) * 4.0) for i, n in enumerate(notes) if n is not None]

    return notes


class Patterns(object):
    c_line = [Live.Clip.MidiNoteSpecification(pitch=60, start_time=0, duration=4, velocity=127)]
    g_line = [Live.Clip.MidiNoteSpecification(pitch=55, start_time=0, duration=4, velocity=127)]
    notes_c_kicks = [
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=0, duration=1, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=1, duration=1, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=2, duration=1, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=3, duration=1, velocity=127)
    ]

    notes_off_beat = [
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=0.5, duration=0.5, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=1.5, duration=0.5, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=2.5, duration=0.5, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=3.5, duration=0.5, velocity=127)
    ]

    # https://commons.wikimedia.org/wiki/Category:MIDI_files_of_rhythms_and_percussion_music
    # half beats
    randoms = [
        (build_clip([9, 0, 7, 0, 9, 8]), '6/8', 3),
        (build_clip([8, 0, 9, 0, 8, 0, 0, 9]), '6/8', 4),
        (build_clip([8, 0, 9, 0, 9, 0, 0, 9, 0, 9, 0, 0]), '6/8', 6),
        (build_clip([9, 0, 9, 0, 9, 0, 8, 9, 0, 9, 0, 9]), '6/8', 6),
        (build_clip([9, 0, 9, 0, 9, 0, 8, 0, 0, 9, 0, 0]), '6/8', 6),
        (build_clip([9, 0, 9, 0, 9, 7, 0, 8, 0, 9, 0, 0, 0, 0, 9, 0]), '6/8', 8)
    ]

    # midi_drum_loops = [
    #     (build_loop([[0,0,9,0],[0,0,9,3],[0,0,0,0],[0,9,3,0]]))
    # ]

    notes_c_16s = [
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=0, duration=0.25, velocity=75),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=0.25, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=0.5, duration=0.25, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=0.75, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=1, duration=0.25, velocity=75),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=1.25, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=1.5, duration=0.25, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=1.75, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=2, duration=0.25, velocity=75),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=2.25, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=2.5, duration=0.25, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=2.75, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=3, duration=0.25, velocity=75),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=3.25, duration=0.25, velocity=100),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=3.5, duration=0.25, velocity=127),
        Live.Clip.MidiNoteSpecification(pitch=60, start_time=3.75, duration=0.25, velocity=100)
    ]

    pattern_1 = [
        None,
        None,
        None,
        SimpleNote(100),
        #
        SimpleNote(75),
        SimpleNote(75),
        SimpleNote(127),
        None,
        #
        None,
        None,
        None,
        SimpleNote(100),
        #
        SimpleNote(75),
        SimpleNote(75),
        SimpleNote(127),
        None,
        #
    ]

    pattern_2 = [
        None,
        None,
        SimpleNote(127),
        None,
        #
        None,
        None,
        SimpleNote(127),
        None,
        #
        None,
        SimpleNote(127),
        None,
        SimpleNote(100),
        #
        None,
        None,
        None,
        None
        #
    ]

    pattern_3 = [
        None,
        None,
        SimpleNote(127),
        None,
        #
        None,
        SimpleNote(127),
        None,
        None,
        #
        SimpleNote(127),
        None,
        None,
        SimpleNote(60),
        #
        None,
        None,
        SimpleNote(100),
        None
        #
    ]

    pattern_4 = [
        None,
        None,
        None,
        None,
        #
        SimpleNote(110),
        None,
        SimpleNote(127),
        None,
        #
        None,
        None,
        None,
        SimpleNote(127),
        #
        None,
        None,
        SimpleNote(100),
        None
        #
    ]

    basic_midi_cycles = [
        ('C Line', c_line),
        ('C Beats', notes_c_kicks),
        ('C Offbeat', notes_off_beat),
        ('C 16s', notes_c_16s),
        ('G Line', g_line),
    ]

    perc_patterns = [
        ('Pat 1', sixteen_notes_to_spec_notes(pattern_1)),
        ('Pat 2', sixteen_notes_to_spec_notes(pattern_2)),
        ('Pat 3', sixteen_notes_to_spec_notes(pattern_3)),
        ('Pat 4', sixteen_notes_to_spec_notes(pattern_4))
    ]

class NameGuesser(ControlSurfaceComponent):

    def __init__(self, ins, song):
        ControlSurfaceComponent.__init__(self)
        self._manager = ins
        self._song = song
        self.default_track_colour_index = 69  # dark grey

    def log_message(self, message):
        self._manager.log_message(message)

    def update_track_names(self):

        not_updating = []

        for track in self._song.tracks:
            self.log_message(track.name)
            self.log_message(track.is_grouped)
            self.log_message(track.group_track)

        for track in self._song.tracks:
            try:
                self.log_message(f"------------------------------------------------")
                self.log_message(f"[{track.name}]")

                if self.is_track_grouping_other_tracks(track):
                    self.set_grouping_track_colour_from_others(track)

                if track.name.endswith('.') \
                        or self.is_track_grouping_other_tracks(track) \
                        or self.track_has_already_been_updated(track):
                    self.log_message(f"[{track.name}] Skipping")
                    continue

                if track.name.startswith('[bip]'):
                    track.name = f"# {track.name[len('[bip] '):]} [bip]"
                    continue

                guess = parsers.guess_cat_from_track_name(track.name)
                self.log_message(f"[{track.name}] track name guess is {str(guess)}")

                if guess is None:
                    guess = self.guess_track_type_from_devices(track.name, track.devices)
                    if guess is not None:
                        track.name = parsers.update_with_track_number(guess.name, track.name)

                if guess is not None:
                    self.log_message(f"[{track.name}] is {str(guess)}, setting colour {guess.colour}")

                    track.color_index = guess.colour

                    for ac in track.arrangement_clips:
                        ac.color_index = guess.colour

                    for cs in track.clip_slots:
                        if cs.clip is not None:
                            cs.clip.color_index = guess.colour

                    self.log_message(f"[{track.name}] \U00002705")
                else:
                    self.log_message(f"[{track.name}] \U0000274C")
                    not_updating.append(track.name)
            except Exception as e:
                self.log_message(f'[{track.name}] error while guessing type: ' + str(e) + str(traceback.format_exc()))


    def guess_track_type_from_devices(self, track_name, devices):  # -> Union[None, str]:

        for d in devices:
            #    self.log('csslog: device ' + str(d)+ ' name is  '+ str(d.name)+' type is '+ str(d.type) +" class is " + str(d.class_name))

            if str(d.type) == 'midi_effect':
                guess = self.guess_from_midi_effect(d)
                if guess is not None:
                    return guess

            if str(d.type) == 'instrument':

                for name, fn in [
                    ('instrument name', parsers.guess_cat_from_instrument_name),
                    ('sample name', sample_categories.lookup_sample_category),
                    ('synth category', synth_categories.lookup_synth_category)
                ]:
                    guess = fn(d.name)
                    self.log_message(f"[{track_name}] {name} guess for {d.name} was: {guess}")
                    if guess is not None:
                        return guess

            else:
                return None

    def update_selected_track_colour_index(self, knob_value):

        # self.log_message(f"update_selected_track_colour_index: {knob_value}")
        new_colour_index = int(knob_value / 10)
        # self.log_message(f"new_colour_index: {new_colour_index}")
        new_colour = self.colours[new_colour_index]
        # self.log_message(f"new_colour: {new_colour}")
        self.song().view.selected_track.color_index = new_colour

        for track in self.song().view.selected_track.arrangement_clips:
            track.color_index = new_colour

        for cs in self.song().view.selected_track.clip_slots:
            if cs.clip is not None:
                cs.clip.color_index = new_colour

    def is_track_grouping_other_tracks(self, the_track):
        for track in self.song().tracks:
            if track.group_track is not None and track.group_track.name == the_track.name:
                return True

        return False

    def set_grouping_track_colour_from_others(self, the_group_track):
        track_colors = [t.color_index for t in self.song().tracks if
                        t.group_track is not None and t.group_track.name == the_group_track.name]
        track_colours_set = set(track_colors)

        if len(track_colours_set) == 1:
            the_group_track.color_index = track_colours_set.pop()

    def track_has_already_been_updated(self, the_track):
        return the_track.color_index != self.default_track_colour_index

class Arranger(ControlSurfaceComponent):
    def __init__(self, ins):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = ins
        self._manager = ins


    def log_message(self, message):
        self._manager.log_message(message)

    def find_next_emmpty_clip_slot(self, track):
        for cs in track.clip_slots:
            if cs.has_clip:
                continue
            return cs

    def copy_all_to_arrangement(self):
        clip_lengths = set({})
        for track in self.song().tracks:
            self.log_message(f"arrange   track = {track.name}")
            clip_slot = track.clip_slots[0]

            if clip_slot.clip is not None:
                clip_lengths.add(clip_slot.clip.length)

        target_len = 1
        for l in clip_lengths:
            target_len = target_len * l

        self.log_message("target_len = " + str(target_len))

        while target_len < 16:
            target_len = target_len * 2

        self.log_message("target_len after stretch = " + str(target_len))

        for track in self.song().tracks:
            self._control_surface.log_message(f"arrange   track = {track.name}")
            clip_slot = track.clip_slots[0]

            if clip_slot.clip is not None:
                temp_clip_slot = self.find_next_emmpty_clip_slot(track)
                clip_slot.duplicate_clip_to(temp_clip_slot)
                temp_clip_slot.clip.name = track.name

                duplicates = int(target_len / clip_slot.clip.length)
                self.log_message(f"copy_all_to_arrangement duplicates = {duplicates}, clip len: {clip_slot.clip.length}")
                self.copy_clip_to_arrangement_consolidate(temp_clip_slot.clip, track, 0, duplicates)

                temp_clip_slot.delete_clip()

        self.song().loop_start = 0
        self.song().loop_length = target_len

    def copy_clip_to_arrangement_consolidate(self, clip, track, start: int, duplicates: int):

        clip_loop_start = clip.loop_start
        original_clip_loop_end = clip.loop_end
        clip_len = clip.length

        self.log_message(f"clip_loop: looped, start, end, len, end_marker = {clip.name}  ({clip.looping}, {clip_loop_start}, {original_clip_loop_end}, {clip_len}, {clip.end_marker})")

        if clip.is_midi_clip:
            if clip.looping:
                for i in range(0, duplicates-1):
                    self.log_message(f"  dplicating i = {i}")
                    clip.duplicate_region(clip.loop_start, clip.loop_end, clip_len + (clip_len * i))

                self.log_message(f"clip.length * duplicates ={clip.length} * {duplicates} = {int(clip.length * duplicates)}")
                clip.loop_end = int(clip.length * duplicates)
                clip.end_marker = int(clip.length * duplicates)

                self.log_message(f"clip.loop_end = {clip.loop_end}")
                self.log_message(f"clip.length = {clip.length}")

            track.duplicate_clip_to_arrangement(clip, start)
        else:
            # for i in range(start, start + beats_to_build, int(clip.length)):
            if clip.looping:
                for i in range(0, duplicates):
                    j = start + (i * int(clip.length))
                    track.duplicate_clip_to_arrangement(clip, j)
            else:
                track.duplicate_clip_to_arrangement(clip, 0)



    def copy_clip_to_arrangement_and_extend(self, clip, track, start: int, beats_to_build: int):

        clip_loop_start = clip.loop_start
        original_clip_loop_end = clip.loop_end

        if clip.is_midi_clip:
            while int(clip.length) < beats_to_build:
                clip.duplicate_loop()

            clip.loop_end = beats_to_build
            clip.crop()

            track.duplicate_clip_to_arrangement(clip, start)
            clip.loop_end = original_clip_loop_end
            clip.crop()
        else:
            for i in range(start, start + beats_to_build, int(clip.length)):
                track.duplicate_clip_to_arrangement(clip, i)

    def quick_numbered_points_arrange(self):
        points = sorted(self.song().cue_points, key=lambda p: p.time)

        self.log_locator_mark_info(points)

        for i in range(0, len(points) - 1):
            loc = points[i]
            name = loc.name
            start_loc_in_beats = loc.time
            end_loc_in_beats = points[i + 1].time

            self._control_surface.log_message(f"arrange locator {name}, time {loc.time}")

            for track in self.song().tracks:
                self._control_surface.log_message(f"arrange   track = {track.name}")
                clip_slot = track.clip_slots[int(name) - 1]

                if clip_slot.clip is not None:
                    beats_per_new_clip = 8 * 4

                    self._control_surface.log_message(
                        f"arrange   clip_slot for loc/track {name}/{track.name} is {clip_slot.clip.name} writing from bars {int(start_loc_in_beats) / 4} to {int(end_loc_in_beats) / 4}")
                    for b in range(int(start_loc_in_beats), int(end_loc_in_beats), beats_per_new_clip):
                        self.copy_clip_to_arrangement_and_extend(clip_slot.clip, track, b, beats_per_new_clip)

    def log_locator_mark_info(self, points):
        for i in range(0, len(points) - 1):
            loc = points[i]
            name = loc.name
            start_loc_in_beats = loc.time
            end_loc_in_beats = points[i + 1].time
            end_loc = points[i + 1].name
            beats_to_build = end_loc_in_beats - start_loc_in_beats

            self._control_surface.log_message(
                f"{name} -> {end_loc} : {start_loc_in_beats} -> {end_loc_in_beats} ({beats_to_build})")
