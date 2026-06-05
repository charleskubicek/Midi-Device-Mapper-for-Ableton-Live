"""Runtime helpers for editing the currently-detailed clip.

Generated clip listeners call into `ClipActions`, which resolves
`song().view.detail_clip` at call time and applies the change, guarding for a
valid clip and (where relevant) audio-only properties.

Bounded properties (gain, pitch) are driven by absolute encoders: the raw
0..127 MIDI value maps linearly onto the property's range. Unbounded
properties (loop / markers, in beats) are nudged by inc/dec buttons a fixed
step per press.
"""


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def absolute_to_range(value, lo, hi, cast=None):
    """Map an absolute 0..127 encoder value onto [lo, hi]."""
    new = lo + (value / 127.0) * (hi - lo)
    if cast == "int":
        new = int(round(new))
    return clamp(new, lo, hi)


class ClipActions:
    def __init__(self, manager):
        # `manager` is the ControlSurface; manager.song() gives the live Song.
        self._manager = manager

    # -- clip resolution -----------------------------------------------------

    def _clip(self, audio_only=False):
        clip = self._manager.song().view.detail_clip
        if clip is None:
            return None
        try:
            if not clip.is_audio_clip and not clip.is_midi_clip:
                return None
        except RuntimeError:
            # liveobj no longer valid
            return None
        if audio_only and not clip.is_audio_clip:
            return None
        return clip

    def _set_absolute(self, prop, value, lo, hi, cast, audio_only):
        clip = self._clip(audio_only=audio_only)
        if clip is None:
            return
        setattr(clip, prop, absolute_to_range(value, lo, hi, cast))

    def _nudge(self, prop, delta, audio_only=False):
        clip = self._clip(audio_only=audio_only)
        if clip is None:
            return
        setattr(clip, prop, getattr(clip, prop) + delta)

    # -- absolute encoders ---------------------------------------------------

    def set_gain(self, value):
        self._set_absolute("gain", value, 0.0, 1.0, None, audio_only=True)

    def set_pitch_coarse(self, value):
        self._set_absolute("pitch_coarse", value, -48, 48, "int", audio_only=True)

    def set_pitch_fine(self, value):
        self._set_absolute("pitch_fine", value, -50, 50, "int", audio_only=True)

    # -- nudge encoders (turn a knob to step beats) --------------------------

    def nudge_loop_start(self, delta):
        self._nudge("loop_start", delta)

    def nudge_loop_end(self, delta):
        self._nudge("loop_end", delta)

    def nudge_start_marker(self, delta):
        self._nudge("start_marker", delta)

    def nudge_end_marker(self, delta):
        self._nudge("end_marker", delta)

    def nudge_move_loop(self, delta):
        self._move_loop(delta)

    # -- inc/dec buttons (1 beat per press) ----------------------------------

    def loop_start_inc(self):
        self._nudge("loop_start", 1.0)

    def loop_start_dec(self):
        self._nudge("loop_start", -1.0)

    def loop_end_inc(self):
        self._nudge("loop_end", 1.0)

    def loop_end_dec(self):
        self._nudge("loop_end", -1.0)

    def start_marker_inc(self):
        self._nudge("start_marker", 1.0)

    def start_marker_dec(self):
        self._nudge("start_marker", -1.0)

    def end_marker_inc(self):
        self._nudge("end_marker", 1.0)

    def end_marker_dec(self):
        self._nudge("end_marker", -1.0)

    # -- toggles / methods / composites --------------------------------------

    def toggle_looping(self):
        clip = self._clip()
        if clip is not None:
            clip.looping = not clip.looping

    def toggle_warping(self):
        clip = self._clip(audio_only=True)
        if clip is not None:
            clip.warping = not clip.warping

    def duplicate_loop(self):
        clip = self._clip()
        if clip is not None:
            clip.duplicate_loop()

    def sync_loop_and_markers(self):
        clip = self._clip()
        if clip is not None:
            clip.start_marker = clip.loop_start
            clip.end_marker = clip.loop_end

    def _move_loop(self, delta_beats):
        clip = self._clip()
        if clip is None:
            return
        new_start = clip.loop_start + delta_beats
        new_end = clip.loop_end + delta_beats
        # Live enforces loop_start < loop_end; set the leading edge first so an
        # intermediate state never inverts the loop.
        if delta_beats > 0:
            clip.loop_end = new_end
            clip.loop_start = new_start
        else:
            clip.loop_start = new_start
            clip.loop_end = new_end

    def move_loop_forward(self):
        self._move_loop(1.0)

    def move_loop_backward(self):
        self._move_loop(-1.0)


class NullClipActions:
    """No-op fallback so generated code never needs to branch."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, _name):
        return lambda *a, **k: None
