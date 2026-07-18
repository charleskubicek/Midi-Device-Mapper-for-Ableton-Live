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
  - a plain step tap toggles the note; hold step A + tap a later step B makes one
    note A..B (long-note gesture, needs momentary buttons).

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


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


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
        # Steps currently held down (for the long-note gesture). Maps step ->
        # {'consumed': bool}; a consumed step's release does not toggle (its note
        # was already created as the anchor or the length-defining tap).
        self._pressed = {}

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
        """The MIDI clip to edit — the detail clip, or a fresh 1-bar clip in the
        highlighted session slot when there is no MIDI detail clip."""
        clip = self._detail_clip()
        if clip is not None:
            return clip
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

    def _selected_pad_note(self, drum_rack):
        # Prefer the controller-selected pad (re-resolved from the live visible
        # bank so scrolling is respected); fall back to Live's mouse-selected pad.
        if self._selected_pad_index is not None:
            pads = self._visible_pads(drum_rack)
            if 0 <= self._selected_pad_index < len(pads):
                note = getattr(pads[self._selected_pad_index], "note", None)
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
        if 0 <= index < len(pads):
            pad = pads[index]
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
        if value == 0:
            self._on_step_release(step)
        else:
            self._on_step_press(step)
        self._emit_hud()

    def _on_step_press(self, step):
        anchor = self._anchor_for(step)
        if anchor is not None:
            # Held step A + tap later step B -> one note A..B. Neither the anchor
            # nor this length-defining tap toggle on release.
            self._create_long_note(anchor, step)
            if anchor in self._pressed:
                self._pressed[anchor]["consumed"] = True
            self._pressed[step] = {"consumed": True}
        else:
            self._pressed[step] = {"consumed": False}

    def _anchor_for(self, step):
        held = [s for s in self._pressed if s < step]
        return min(held) if held else None

    def _on_step_release(self, step):
        info = self._pressed.pop(step, None)
        if info is None:
            return
        if not info["consumed"]:
            self.toggle_step(step)

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

    def _create_long_note(self, anchor, b):
        drum_rack = self._drum_rack()
        if drum_rack is None:
            return
        pitch = self._selected_pad_note(drum_rack)
        if pitch is None:
            return
        clip = self._clip_for_edit()
        if clip is None:
            return
        start = anchor * STEP_BEATS
        duration = (b - anchor + 1) * STEP_BEATS
        # Replace any note already at the anchor step.
        clip.remove_notes_extended(pitch, 1, start, STEP_BEATS)
        clip.add_new_notes([make_note_spec(pitch, start, duration, DEFAULT_VELOCITY)])

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
