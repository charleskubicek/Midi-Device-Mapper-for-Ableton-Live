from dataclasses import dataclass

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ControlSurface import ControlSurface
import Live
import time


class Functions(ControlSurface):
    def __init__(self, c_instance=None, publish_self=True, *a, **k):
        super().__init__(c_instance=c_instance)

        self.perc_pattern_cycler = PatternCycler(self, Patterns.perc_patterns)
        self.midi_pattern_cycler = PatternCycler(self, Patterns.basic_midi_cycles)

    def selected_device(self):
        return self.song().view.selected_track.view.selected_device

    def iterate_perc_pattern(self):
        self.perc_pattern_cycler.next()

    def iterate_midi_pattern(self):
        self.perc_pattern_cycler.next()




class PatternCycler(ControlSurfaceComponent):
    def __init__(self, ins, patterns):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = ins
        self._patterns = patterns

        self.counter = 0
        self.last_press = int(time.time())

    def was_used_within_window(self):
        return int(time.time()) - self.last_press < 4

    def next(self):
        if not self.was_used_within_window():
            self.counter = 0

        name, notes = self._patterns[self.counter]
        self._control_surface.create_clip_and_notes(notes, name)
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
