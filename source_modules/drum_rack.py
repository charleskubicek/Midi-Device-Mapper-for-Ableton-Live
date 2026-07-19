"""Runtime drum-rack editor for the generated surface.

Generated sequencer/velocity listeners call into `DrumRackController`, which
resolves the focused drum rack + the detail clip at call time and edits the
step pattern for the selected pad. Mirrors the `clip_actions.py` pattern: no
Live import at module top level (imported lazily so unit tests run pure), and a
Null* fallback so generated code never branches.

V1 scope (see ai-coding/plans/drum_rack.md):
  - edits bar 1 only, at sixteenth resolution (16 steps).
  - "selected pad" = the pad tapped from the controller if pad wiring is present
    (deferred seam), otherwise Live's own `drum_rack.view.selected_drum_pad`, so
    the step/velocity editing already works against the mouse-selected pad.
  - a step tap toggles the note on/off (needs momentary buttons for a clean edge).

DEFERRED SEAM: pad *audition* + controller-driven pad *selection* wiring depend
on a Live note-forwarding/translation spike and are not wired here. `select_pad`
is implemented so the wiring is a one-liner once the spike resolves.
"""
from collections import namedtuple

# Lazy Live handle: real Live inside Ableton, None under unit test. Note specs
# fall back to a plain namedtuple so the clip-editing math is testable without
# Ableton's Python runtime.
try:
    import Live  # noqa: F401
except Exception:  # pragma: no cover - only importable inside Ableton
    Live = None

NoteSpec = namedtuple("NoteSpec", ["pitch", "start_time", "duration", "velocity", "mute"])

STEP_BEATS = 0.25          # one sixteenth of a 4-beat bar
STEPS_PER_BAR = 16
DEFAULT_VELOCITY = 100
BAR_BEATS = STEP_BEATS * STEPS_PER_BAR

# A drum-rack bank is a 4x4 grid of pads, and so is the controller's pad grid.
PAD_GRID_WIDTH = 4
PAD_GRID_HEIGHT = 4


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def bank_index_from_controller(index, width=PAD_GRID_WIDTH, height=PAD_GRID_HEIGHT):
    """Map a controller pad index to the index Live uses in `visible_drum_pads`.

    The controller numbers its pads top-down (index 0 = top-left, increasing
    left->right then down a row), but Live's drum bank is laid out bottom-up
    (index 0 = the bottom-left pad, note 36). So the two grids are the same
    left-to-right but vertically mirrored: a top-down controller row maps to the
    bottom-up bank row. Columns are unchanged."""
    row, col = divmod(index, width)
    return (height - 1 - row) * width + col


def make_note_spec(pitch, start_time, duration, velocity):
    if Live is not None:  # pragma: no cover - exercised inside Ableton
        return Live.Clip.MidiNoteSpecification(
            pitch=int(pitch), start_time=start_time, duration=duration,
            velocity=int(velocity), mute=False)
    return NoteSpec(int(pitch), start_time, duration, int(velocity), False)


class DrumRackController:
    def __init__(self, manager, hud_client=None):
        self._manager = manager
        self._hud_client = hud_client
        # Pad tapped from the controller (0-based index into the visible bank).
        # None => fall back to Live's mouse-selected drum pad.
        self._selected_pad_index = None

    # -- device / clip resolution -------------------------------------------

    def is_active(self):
        """True when the focused device is a drum rack — the condition under which
        drum roles take precedence over a shared control's device macro/switch
        role. Generated dispatching listeners branch on this."""
        return self._drum_rack() is not None

    def _drum_rack(self):
        try:
            device = self._manager.song().view.selected_track.view.selected_device
        except Exception:
            return None
        if device is None:
            return None
        # A drum rack is the only device that can host pads; when the focused
        # device is anything else the whole controller is inert.
        if not getattr(device, "can_have_drum_pads", False):
            return None
        return device

    def _detail_clip(self):
        try:
            clip = self._manager.song().view.detail_clip
        except Exception:
            return None
        if clip is None:
            return None
        try:
            if not clip.is_midi_clip:
                return None
        except Exception:
            return None
        return clip

    def _clip_for_edit(self):
        """The MIDI clip to edit — in order of preference:
          1. the MIDI detail clip, if one is focused;
          2. in Arrangement view, one looping clip that fills the arrangement
             loop (created on first edit — see _arrangement_clip_for_edit);
          3. otherwise a fresh 1-bar clip in the highlighted session slot."""
        clip = self._detail_clip()
        if clip is not None:
            return clip
        if self._in_arrangement():
            return self._arrangement_clip_for_edit()
        try:
            slot = self._manager.song().view.highlighted_clip_slot
        except Exception:
            return None
        if slot is None:
            return None
        try:
            if not slot.has_clip:
                slot.create_clip(BAR_BEATS)
            return slot.clip
        except Exception:
            return None

    def _in_arrangement(self):
        """True when the Arrangement (not Session) is the focused document view.
        Drives sequencing into a real arrangement clip instead of a session slot."""
        try:
            return self._manager.application().view.focused_document_view == "Arranger"
        except Exception:
            return False

    def _arrangement_clip_for_edit(self):
        """The arrangement clip to sequence into, created on first edit.

        Mirrors the manual Ableton gesture "make a 1-bar clip, turn on loop, drag
        the right edge to fill the arrangement loop": a SINGLE looping MIDI clip
        placed at the arrangement loop start, spanning the whole loop, whose
        content loops every bar. Because it is one clip (not tiled copies), every
        step edit updates every repetition — there is nothing to keep in sync.

        Idempotent: an existing clip anchored at the loop start is reused, so
        repeated taps never spawn a second clip."""
        try:
            song = self._manager.song()
            track = song.view.selected_track
            loop_start = song.loop_start
            span = max(song.loop_length, BAR_BEATS)
        except Exception:
            return None
        if track is None:
            return None
        existing = self._existing_arrangement_clip(track, loop_start)
        if existing is not None:
            return existing
        try:
            clip = track.create_midi_clip(loop_start, span)
        except Exception:
            return None  # non-MIDI/frozen/recording track etc.
        if clip is None:
            return None
        try:
            clip.looping = True
            clip.loop_start = 0.0
            clip.loop_end = BAR_BEATS
        except Exception:
            pass
        try:
            song.view.detail_clip = clip
        except Exception:
            pass
        return clip

    def _existing_arrangement_clip(self, track, loop_start):
        """A MIDI arrangement clip already anchored at loop_start, or None.
        Guards against creating a fresh clip on every step tap."""
        clips = getattr(track, "arrangement_clips", None)
        if not clips:
            return None
        for clip in clips:
            try:
                if abs(clip.start_time - loop_start) < 1e-6 and clip.is_midi_clip:
                    return clip
            except Exception:
                continue
        return None

    # -- pad selection -------------------------------------------------------

    def _visible_pads(self, drum_rack):
        """The DrumPad objects of the rack's currently-visible 4x4 bank.

        Live API: `RackDevice.visible_drum_pads` (16 pads for the current bank,
        respecting `view.drum_pads_scroll_position`). NOT `view.drum_pads` — that
        attribute doesn't exist and returned None, which is why pad selection
        silently no-op'd. Returns [] if unavailable."""
        pads = getattr(drum_rack, "visible_drum_pads", None)
        if pads is None:
            return []
        try:
            return list(pads)
        except Exception:
            return []

    def _bank_pad(self, pads, controller_index):
        """The DrumPad for a controller pad index, accounting for the top-down /
        bottom-up orientation flip. None if out of range."""
        bank_index = bank_index_from_controller(controller_index)
        if 0 <= bank_index < len(pads):
            return pads[bank_index]
        return None

    def _selected_pad_note(self, drum_rack):
        # Prefer the controller-selected pad (re-resolved from the live visible
        # bank so scrolling is respected); fall back to Live's mouse-selected pad.
        if self._selected_pad_index is not None:
            pads = self._visible_pads(drum_rack)
            pad = self._bank_pad(pads, self._selected_pad_index)
            if pad is not None:
                note = getattr(pad, "note", None)
                if note is not None:
                    return note
        view = getattr(drum_rack, "view", None)
        pad = getattr(view, "selected_drum_pad", None) if view is not None else None
        if pad is None:
            return None
        return getattr(pad, "note", None)

    def select_pad(self, index):
        """Controller pad tap: make pad `index` (0-based into the visible bank)
        the pad the sequencer/velocity controls edit, and mirror the selection
        into Live's UI. Audition of the pad's sound is the deferred spike seam."""
        self._selected_pad_index = index
        drum_rack = self._drum_rack()
        pads = self._visible_pads(drum_rack) if drum_rack is not None else []
        note = None
        pad = self._bank_pad(pads, index)
        if pad is not None:
            note = getattr(pad, "note", None)
            try:
                drum_rack.view.selected_drum_pad = pad
            except Exception as e:
                self._log(f"[drum] select_pad: could not set selected_drum_pad: {e}")
        self._log(f"[drum] select_pad index={index} active={drum_rack is not None} "
                  f"visible_pads={len(pads)} note={note}")
        self._emit_hud()

    def _log(self, message):
        try:
            self._manager.log_message(message)
        except Exception:
            pass

    # -- step editing --------------------------------------------------------

    def step_event(self, step, value):
        # A step tap toggles the note. Act on the release edge (value == 0) so a
        # single press-and-let-go is one toggle on momentary buttons.
        if value == 0:
            self.toggle_step(step)
        self._emit_hud()

    def toggle_step(self, step):
        drum_rack = self._drum_rack()
        if drum_rack is None:
            return
        pitch = self._selected_pad_note(drum_rack)
        self._log(f"[drum] toggle_step step={step} sel_index={self._selected_pad_index} pitch={pitch}")
        if pitch is None:
            return
        clip = self._clip_for_edit()
        if clip is None:
            return
        start, span = step * STEP_BEATS, STEP_BEATS
        if self._notes_in_window(clip, pitch, start, span):
            clip.remove_notes_extended(pitch, 1, start, span)
        else:
            clip.add_new_notes([make_note_spec(pitch, start, span, DEFAULT_VELOCITY)])

    # -- velocity editing ----------------------------------------------------

    def set_velocity(self, step, value):
        drum_rack = self._drum_rack()
        if drum_rack is None:
            return
        pitch = self._selected_pad_note(drum_rack)
        if pitch is None:
            return
        clip = self._clip_for_edit()
        if clip is None:
            return
        start, span = step * STEP_BEATS, STEP_BEATS
        notes = self._notes_in_window(clip, pitch, start, span)
        if not notes:
            return  # empty step: turning the encoder does nothing
        new_velocity = clamp(int(value), 1, 127)
        for note in notes:
            try:
                note.velocity = new_velocity
            except Exception:
                pass
        try:
            clip.apply_note_modifications(notes)
        except Exception:
            pass

    # -- helpers -------------------------------------------------------------

    def _notes_in_window(self, clip, pitch, start, span):
        try:
            result = clip.get_notes_extended(pitch, 1, start, span)
        except Exception:
            return []
        notes = list(result) if result is not None else []
        # get_notes_extended already filters by time_span, but guard against a
        # note that only touches the window from a previous step.
        return [n for n in notes if start <= getattr(n, "start_time", start) < start + span]

    def pattern(self):
        """16-char pattern for the selected pad: 'X' filled, '.' empty."""
        drum_rack = self._drum_rack()
        if drum_rack is None:
            return "." * STEPS_PER_BAR
        pitch = self._selected_pad_note(drum_rack)
        clip = self._detail_clip()
        if pitch is None or clip is None:
            return "." * STEPS_PER_BAR
        try:
            result = clip.get_notes_extended(pitch, 1, 0.0, BAR_BEATS)
        except Exception:
            return "." * STEPS_PER_BAR
        notes = list(result) if result is not None else []
        cells = ["."] * STEPS_PER_BAR
        for n in notes:
            idx = int(getattr(n, "start_time", 0.0) / STEP_BEATS)
            if 0 <= idx < STEPS_PER_BAR:
                cells[idx] = "X"
        return "".join(cells)

    def _pad_name(self):
        drum_rack = self._drum_rack()
        if drum_rack is None:
            return ""
        view = getattr(drum_rack, "view", None)
        pad = getattr(view, "selected_drum_pad", None) if view is not None else None
        if pad is None:
            return ""
        return getattr(pad, "name", "") or ""

    def _emit_hud(self):
        if self._hud_client is None:
            return
        try:
            self._hud_client.send_drum(self._pad_name(), self.pattern())
        except Exception:
            pass


class NullDrumRackController:
    """No-op fallback so generated code never needs to branch."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, _name):
        return lambda *a, **k: None
