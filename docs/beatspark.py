"""
beatspark Control Surface - bridges Ableton Live to the beatspark app via OSC.
"""

import Live
import re
from _Framework.ControlSurface import ControlSurface
from .osc_handler import OSCHandler

# Monotonically-increasing script version, echoed in every pong so the app can
# detect a STALE LOADED script: the app hash-syncs this file on every run, but
# Ableton only loads control surfaces at startup, so a user who skips the
# relaunch keeps the old code in memory (pongs still flow, newer `get` handlers
# silently never answer -> lesson softlocks). Bump this on EVERY change to the
# remote script; the app compares it against the bundled file's value and shows
# the "relaunch Ableton" banner on mismatch. Old scripts send a bare pong,
# which the app reads as version 0.
SCRIPT_VERSION = 1


class beatspark(ControlSurface):
    """
    Main control surface class. Ableton instantiates this when the
    beatspark remote script is selected in Preferences.
    """

    def __init__(self, c_instance):
        super(beatspark, self).__init__(c_instance)
        with self.component_guard():
            self._osc = OSCHandler(
                send_host='127.0.0.1',
                send_port=9001,     # Sends TO beatspark app
                listen_port=9000,   # Listens FROM beatspark app
            )
            self._last_track_count = len(self.song().tracks)
            self._clip_watchers = []  # List of (track_index, clip_index) to monitor
            self._MAX_CLIP_WATCHERS = 32
            self._last_clip_state = {}  # (track, clip) -> has_clip boolean
            self._device_param_watchers = {}  # {(track_idx, param_name): teardown_fn}
            # Authoring-time "watch every param on this track" (for the
            # builder's Capture flow). One entry per active track, each
            # entry is a list of teardown callables.
            self._track_watchers = {}  # {track_idx: [teardown_fn, ...]}
            # Passive send-automation sampling. ARRANGEMENT automation is NOT
            # readable via the LOM (no envelope value_at_time), so to verify
            # "send X = N dB at bar B" we watch the live param value while the
            # user plays and sample it as current_song_time crosses the target
            # beat. One watch at a time; replaced each step. None = inactive.
            self._send_automation_watch = None  # {ti, send, at, eps, last} or None
            self._setup_listeners()
            self.log_message('beatspark: initialized')

    def _setup_listeners(self):
        """Register listeners on the Live song object."""
        song = self.song()

        # Tempo listener (guard against double-registration)
        if not song.tempo_has_listener(self._on_tempo_changed):
            song.add_tempo_listener(self._on_tempo_changed)

        # Playing status listener
        if not song.is_playing_has_listener(self._on_playing_changed):
            song.add_is_playing_listener(self._on_playing_changed)

        # Selected track listener
        if not song.view.selected_track_has_listener(self._on_selected_track_changed):
            song.view.add_selected_track_listener(self._on_selected_track_changed)

        # Detail clip listener (fires when clip detail view opens/changes)
        if not song.view.detail_clip_has_listener(self._on_detail_clip_changed):
            song.view.add_detail_clip_listener(self._on_detail_clip_changed)

        # Focused document view listener (Arranger vs Session)
        try:
            app_view = self.application().view
            if not app_view.focused_document_view_has_listener(self._on_focused_document_view_changed):
                app_view.add_focused_document_view_listener(self._on_focused_document_view_changed)
        except Exception as e:
            self.log_message('beatspark: focused_document_view listener error: %s' % str(e))

        # Arrangement loop listeners — the loop on/off switch and the brace
        # position (start + length). Push the loop state on every change so the
        # lesson RECORDER captures it as ground truth, not just on request.
        try:
            for has_l, add_l in (
                (song.loop_has_listener, song.add_loop_listener),
                (song.loop_start_has_listener, song.add_loop_start_listener),
                (song.loop_length_has_listener, song.add_loop_length_listener),
            ):
                if not has_l(self._on_arrangement_loop_changed):
                    add_l(self._on_arrangement_loop_changed)
        except Exception as e:
            self.log_message('beatspark: arrangement-loop listener error: %s' % str(e))

        # Arrangement Record (global record button) — push on change so a "arm
        # Arrangement Record" lesson step can be captured (reuses wait_record).
        try:
            if not song.record_mode_has_listener(self._on_record_mode_changed):
                song.add_record_mode_listener(self._on_record_mode_changed)
        except Exception as e:
            self.log_message('beatspark: record-mode listener error: %s' % str(e))

        # Register OSC message handlers
        self._osc.register_handler('/beatspark/ping', self._handle_ping)
        self._osc.register_handler('/beatspark/get', self._handle_get)
        self._osc.register_handler('/beatspark/set/tempo', self._handle_set_tempo)
        self._osc.register_handler('/beatspark/set/device-param', self._handle_set_device_param)
        self._osc.register_handler('/beatspark/nudge/device-param', self._handle_nudge_device_param)
        self._osc.register_handler('/beatspark/watch/clip', self._handle_watch_clip)
        self._osc.register_handler('/beatspark/watch/device-param', self._handle_watch_device_param)
        self._osc.register_handler('/beatspark/watch/track-params', self._handle_watch_track_params)
        self._osc.register_handler('/beatspark/unwatch/track-params', self._handle_unwatch_track_params)
        self._osc.register_handler('/beatspark/watch/send-automation', self._handle_watch_send_automation)

        # Seed the rename-poll cache so update_display doesn't re-send every track
        # name on its first tick (only real renames during a session should fire).
        try:
            self._last_track_names = [str(t.name) for t in song.tracks]
        except Exception:
            self._last_track_names = None

        # Seed the device-poll cache so update_display only pushes device changes
        # that happen DURING the session (a device added/removed/replaced doesn't
        # change the track count and has no cheap listener we manage). A tuple of
        # device names per track is the signature.
        try:
            self._last_device_sigs = [tuple(str(d.name) for d in t.devices) for t in song.tracks]
        except Exception:
            self._last_device_sigs = None

        # Send initial state
        self._send_full_state()
        self._send_arrangement_view_state()

    def _send_full_state(self):
        """Send all current state to the beatspark app."""
        song = self.song()
        self._osc.send('/beatspark/tempo', song.tempo)
        self._osc.send('/beatspark/playing', 1 if song.is_playing else 0)
        self._send_track_info()

    def _send_track_info(self):
        """Send track names and count."""
        song = self.song()
        tracks = song.tracks
        self._osc.send('/beatspark/track/count', len(tracks))
        for i, track in enumerate(tracks):
            self._osc.send('/beatspark/track/name', i, track.name)

    def _send_selected_track_index(self):
        """Send the index AND NAME of the currently selected track. index = position
        in song.tracks, or -1 for a return/master track (which aren't in that list).
        The name lets a lesson verify a return-track selection (e.g. the 'B Delay'
        return) that has no regular-track index — wait_track_select's targetName."""
        song = self.song()
        selected = song.view.selected_track
        name = ''
        try:
            name = str(selected.name)
        except Exception:
            pass
        tracks = list(song.tracks)
        try:
            index = tracks.index(selected)
        except ValueError:
            index = -1  # return or master track
        self._osc.send('/beatspark/selected-track', index, name)

    # --- Listeners (called by Ableton when state changes) ---

    def _on_tempo_changed(self):
        self._osc.send('/beatspark/tempo', self.song().tempo)

    def _on_arrangement_loop_changed(self):
        self._send_arrangement_loop_state()

    def _on_record_mode_changed(self):
        self._send_record_mode()

    def _on_playing_changed(self):
        self._osc.send('/beatspark/playing', 1 if self.song().is_playing else 0)

    def _on_selected_track_changed(self):
        self._send_selected_track_index()

    def _on_focused_document_view_changed(self):
        self._send_arrangement_view_state()

    def _probe_arrangement_view(self):
        """Temporary debug: probe what song.view exposes for arrangement scroll/zoom."""
        song = self.song()
        candidates = [
            'arrangement_position', 'current_song_time', 'zooming_level',
            'session_visible_tracks', 'highlighted_clip_slot',
        ]
        for attr in candidates:
            try:
                val = getattr(song.view, attr)
                self.log_message('beatspark: probe song.view.%s = %s' % (attr, str(val)))
            except Exception as e:
                self.log_message('beatspark: probe song.view.%s -> ERROR: %s' % (attr, str(e)))
        try:
            self.log_message('beatspark: probe song.current_song_time = %s' % str(song.current_song_time))
        except Exception as e:
            self.log_message('beatspark: probe song.current_song_time -> ERROR: %s' % str(e))

    def _send_arrangement_loop_state(self):
        """Send arrangement loop enabled state, start position, and length in beats."""
        try:
            song = self.song()
            loop_on = 1 if song.loop else 0
            loop_start = song.loop_start
            loop_length = song.loop_length
            self.log_message('beatspark: arrangement-loop on=%d start=%.3f length=%.3f' % (loop_on, loop_start, loop_length))
            self._osc.send('/beatspark/arrangement-loop', loop_on, loop_start, loop_length)
        except Exception as e:
            self.log_message('beatspark: arrangement-loop error: %s' % str(e))
            self._osc.send('/beatspark/arrangement-loop', 0, 0.0, 0.0, 0.0)

    def _send_arrangement_length(self):
        """Send the arrangement's last_event_time (beats) + the time signature, so the
        app can derive the length in bars. Drives wait_arrangement_length (e.g. verify
        a Duplicate-Time made the arrangement 16 bars). last_event_time = beat of the
        last event (clip end, automation breakpoint, cue/loop end) in the Arrangement."""
        try:
            song = self.song()
            self._osc.send('/beatspark/arrangement-length', float(song.last_event_time),
                           int(song.signature_numerator), int(song.signature_denominator))
        except Exception as e:
            self.log_message('beatspark: arrangement-length error: %s' % str(e))
            self._osc.send('/beatspark/arrangement-length', 0.0, 4, 4)

    def _send_arrangement_view_state(self):
        try:
            view = self.application().view.focused_document_view
            is_arrangement = 1 if view == 'Arranger' else 0
            self._osc.send('/beatspark/arrangement-view', is_arrangement)
            self.log_message('beatspark: focused_document_view=%s is_arrangement=%d' % (view, is_arrangement))
        except Exception as e:
            self.log_message('beatspark: arrangement view state error: %s' % str(e))

    def _on_detail_clip_changed(self):
        self._send_detail_clip_info()
        # Also push drum pad layout and loop bounds for the newly opened clip
        song = self.song()
        clip = song.view.detail_clip
        if clip is not None:
            tracks = list(song.tracks)
            # Check session clip slots first
            for ti, track in enumerate(tracks):
                for ci, slot in enumerate(track.clip_slots):
                    if slot.has_clip and slot.clip == clip:
                        self._send_drum_pads(ti)
                        self._send_clip_loop_bounds(ti, ci)
                        self._send_clip_scale(ti, ci)
                        return
            # Fallback: arrangement clips - find track via canonical_parent
            try:
                parent = clip.canonical_parent
                for ti, track in enumerate(tracks):
                    if track == parent:
                        self._send_drum_pads(ti)
                        # Auto-push loop-bounds + scale for the arrangement clip
                        # too (clip=-1 -> detail_clip), mirroring the session-clip
                        # path above. Without this _midiLoopBounds stays empty
                        # until the per-step requestLoopBounds reply lands, so the
                        # Loop Brace markers (scroll/zoom-aware X) can't resolve
                        # for the first ticks of an arrangement MIDI step.
                        self._send_clip_loop_bounds(ti, -1)
                        self._send_clip_scale(ti, -1)
                        return
                grandparent = parent.canonical_parent if hasattr(parent, 'canonical_parent') else None
                if grandparent:
                    for ti, track in enumerate(tracks):
                        if track == grandparent:
                            self._send_drum_pads(ti)
                            self._send_clip_loop_bounds(ti, -1)
                            self._send_clip_scale(ti, -1)
                            return
            except Exception as e:
                self.log_message('beatspark: detail_clip_changed arrangement fallback error: %s' % str(e))

    def _send_detail_clip_info(self):
        """Send track/clip index of the currently open detail clip, or -1 if none."""
        song = self.song()
        # Check if the clip detail view is actually visible
        try:
            detail_visible = self.application().view.is_view_visible('Detail')
            clip_visible = self.application().view.is_view_visible('Detail/Clip')
            self.log_message('beatspark: detail_visible=%s clip_visible=%s' % (detail_visible, clip_visible))
            if not clip_visible:
                self._osc.send('/beatspark/detail-clip', -1, -1)
                return
        except Exception as e:
            self.log_message('beatspark: is_view_visible error: %s' % str(e))
        clip = song.view.detail_clip
        if clip is None:
            self._osc.send('/beatspark/detail-clip', -1, -1)
            return
        tracks = list(song.tracks)
        for ti, track in enumerate(tracks):
            for ci, slot in enumerate(track.clip_slots):
                if slot.has_clip and slot.clip == clip:
                    self._osc.send('/beatspark/detail-clip', ti, ci)
                    return
        # Fallback: arrangement clips aren't in clip_slots - find by checking canonical_parent chain
        try:
            parent = clip.canonical_parent
            self.log_message('beatspark: detail-clip fallback: clip.canonical_parent=%s type=%s' % (str(parent), type(parent).__name__))
            # Try direct parent (arrangement clips: Clip - Track)
            for ti, track in enumerate(tracks):
                if track == parent:
                    self.log_message('beatspark: detail-clip found arrangement clip on track %d (direct parent)' % ti)
                    self._osc.send('/beatspark/detail-clip', ti, -1)
                    return
            # Try grandparent (Clip - ClipSlot - Track)
            grandparent = parent.canonical_parent if hasattr(parent, 'canonical_parent') else None
            if grandparent:
                self.log_message('beatspark: detail-clip fallback: grandparent=%s type=%s' % (str(grandparent), type(grandparent).__name__))
                for ti, track in enumerate(tracks):
                    if track == grandparent:
                        self.log_message('beatspark: detail-clip found arrangement clip on track %d (grandparent)' % ti)
                        self._osc.send('/beatspark/detail-clip', ti, -1)
                        return
        except Exception as e:
            self.log_message('beatspark: arrangement clip fallback error: %s' % str(e))
        self._osc.send('/beatspark/detail-clip', -1, -1)

    # --- OSC Message Handlers (called when beatspark app sends us messages) ---

    def _handle_ping(self, args):
        # Echo the script version so the app can detect a stale loaded script
        # (see SCRIPT_VERSION at the top of this file).
        self._osc.send('/beatspark/pong', SCRIPT_VERSION)
        self.log_message('beatspark: ping -> pong (v%d)' % SCRIPT_VERSION)

    def _handle_get(self, args):
        if not args:
            return

        param = args[0]
        if param == 'tempo':
            self._osc.send('/beatspark/tempo', self.song().tempo)
        elif param == 'tracks':
            self._send_track_info()
        elif param == 'clips':
            if len(args) > 1:
                self._send_clip_info(int(args[1]))
        elif param == 'selected-track':
            self._send_selected_track_index()
        elif param == 'time-signature':
            song = self.song()
            self._osc.send(
                '/beatspark/time-signature',
                song.signature_numerator,
                song.signature_denominator,
            )
        elif param == 'track-count':
            self._osc.send('/beatspark/track/count', len(self.song().tracks))
        elif param == 'track-kinds':
            self._send_track_kinds()
        elif param == 'has-clip':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                tracks = self.song().tracks
                if ti < len(tracks):
                    slots = tracks[ti].clip_slots
                    if ci < len(slots):
                        self._osc.send('/beatspark/clip/has-clip', ti, ci,
                                       1 if slots[ci].has_clip else 0)
        elif param == 'devices':
            if len(args) > 1:
                ti = int(args[1])
                self._send_device_info(ti)
        elif param == 'grid-quantization':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                self._send_grid_quantization(ti, ci)
        elif param == 'note-count':
            self.log_message('beatspark: got note-count request, args=%s' % str(args))
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                from_pitch = int(args[3]) if len(args) > 3 else 0
                pitch_span = int(args[4]) if len(args) > 4 else 128
                from_time = float(args[5]) if len(args) > 5 else -1.0
                time_span = float(args[6]) if len(args) > 6 else -1.0
                self._send_note_count(ti, ci, from_pitch, pitch_span, from_time, time_span)
            else:
                self.log_message('beatspark: note-count request missing args, got %d args' % len(args))
        elif param == 'note-duration-total':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                self._send_note_duration_total(ti, ci)
        elif param == 'selected-note-count':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                self._send_selected_note_count(ti, ci)
        elif param == 'all-notes':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                self._send_all_notes(ti, ci)
        elif param == 'notes-at-positions':
            # args: [param, ti, ci, tolerance, pitch1, time1, pitch2, time2, ...]
            if len(args) >= 6:
                ti, ci = int(args[1]), int(args[2])
                tol = float(args[3])
                specs = []
                i = 4
                while i + 1 < len(args):
                    specs.append((int(args[i]), float(args[i + 1])))
                    i += 2
                self._send_notes_at_positions(ti, ci, tol, specs)
        elif param == 'clip-playing':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                self._send_clip_playing(ti, ci)
        elif param == 'detail-clip':
            self._send_detail_clip_info()
        elif param == 'device-view-visible':
            try:
                song = self.song()
                visible = False
                # Try direct check first
                try:
                    visible = self.application().view.is_view_visible('Detail/DeviceChain')
                except Exception:
                    pass
                # Fallback: detail panel open but clip view NOT shown = device chain must be shown
                if not visible:
                    try:
                        detail_visible = self.application().view.is_view_visible('Detail')
                        clip_visible = self.application().view.is_view_visible('Detail/Clip')
                        visible = detail_visible and not clip_visible
                    except Exception:
                        pass
                self.log_message('beatspark: device-view-visible=%s' % visible)
                self._osc.send('/beatspark/device-view-visible', 1 if visible else 0)
            except Exception as e:
                self.log_message('beatspark: device-view-visible error: %s' % str(e))
                self._osc.send('/beatspark/device-view-visible', 0)
        elif param == 'drum-pads':
            if len(args) > 1:
                self._send_drum_pads(int(args[1]))
        elif param == 'drum-pad-samples':
            if len(args) > 1:
                self._send_drum_pad_samples(int(args[1]))
        elif param == 'loop-bounds':
            if len(args) > 2:
                self._send_clip_loop_bounds(int(args[1]), int(args[2]))
        elif param == 'clip-scale':
            self.log_message('beatspark: clip-scale dispatch reached, args=' + str(list(args)))
            if len(args) > 2:
                self._send_clip_scale(int(args[1]), int(args[2]))
        elif param == 'simpler-sample':
            if len(args) > 1:
                self._send_simpler_sample(int(args[1]))
        elif param == 'device-params':
            if len(args) > 1:
                # args: [param, trackIdx, trackKind?]
                self._send_device_params(int(args[1]), args[2] if len(args) > 2 else '')
        elif param == 'aux-tracks':
            self._send_aux_tracks()
        elif param == 'device-catalog':
            self._send_device_catalog()
        elif param == 'wavetable-modmatrix':
            if len(args) > 1:
                self._probe_wavetable_modmatrix(int(args[1]))
        elif param == 'mod-value':
            # args: [param, trackIdx, sourceIdx, targetSpec]
            if len(args) > 3:
                self._send_mod_value(int(args[1]), int(args[2]), args[3])
        elif param == 'browser-category':
            if len(args) > 1:
                category = args[1]
                self._send_browser_category_state(category)
        elif param == 'browser-visible':
            try:
                song = self.song()
                visible = self.application().view.is_view_visible('Browser')
                self._osc.send('/beatspark/browser/visible', 1 if visible else 0)
            except Exception as e:
                self.log_message('beatspark: browser visible error: %s' % str(e))
                self._osc.send('/beatspark/browser/visible', 0)
        elif param == 'groove-amount':
            try:
                amount = self.song().groove_amount
                self._osc.send('/beatspark/groove-amount', amount)
                self.log_message('beatspark: groove-amount=%.3f' % amount)
            except Exception as e:
                self.log_message('beatspark: groove-amount error: %s' % str(e))
                self._osc.send('/beatspark/groove-amount', 0.0)
        elif param == 'arrangement-clips':
            if len(args) > 1:
                self._send_arrangement_clips(int(args[1]))
        elif param == 'clip-start-time':
            if len(args) > 2:
                ti, ci = int(args[1]), int(args[2])
                self._send_clip_start_time(ti, ci)
        elif param == 'arrangement-loop':
            self._send_arrangement_loop_state()
        elif param == 'arrangement-length':
            self._send_arrangement_length()
        elif param == 'arrangement-view':
            self._send_arrangement_view_state()
        elif param == 'probe-arrangement':
            self._probe_arrangement_view()
        elif param == 'song-file-path':
            self._send_song_file_path()
        elif param == 'song-modified':
            self._send_song_modified()
        elif param == 'back-to-arranger':
            self._send_back_to_arranger()
        elif param == 'record-mode':
            self._send_record_mode()
        elif param == 'track-arm':
            if len(args) > 1:
                self._send_track_arm(int(args[1]))
        elif param == 'track-mute':
            if len(args) > 1:
                self._send_track_mute(int(args[1]))
        elif param == 'track-solo':
            if len(args) > 1:
                self._send_track_solo(int(args[1]))
        elif param == 'clip-pitch-range':
            if len(args) > 2:
                self._send_clip_pitch_range(int(args[1]), int(args[2]))
        elif param == 'draw-mode':
            # Song.View.draw_mode: 0 = breakpoint editing, 1 = drawing (pencil)
            self._osc.send('/beatspark/draw-mode', int(self.song().view.draw_mode))
        elif param == 'scale-mode':
            # Song.scale_mode: bool - true when Fold to Scale is on
            self._osc.send('/beatspark/scale-mode', int(self.song().scale_mode))
        elif param == 'clip-view-probe':
            # Diagnostic: introspect Live's clip.view to find what viewport-
            # related properties exist on this Live version. Logs everything
            # to log_message and sends a summary string back via OSC.
            self._probe_clip_view()
        elif param == 'any-clip-triggered':
            self._send_any_clip_triggered()
        elif param == 'version':
            self._send_live_version()

    def _send_live_version(self):
        """Send the running Live version as a dotted string, e.g. '12.1.5'.
        Edition (Intro/Standard/Suite) is NOT exposed by the LOM - the Electron
        side derives that from the app bundle path."""
        try:
            app = self.application()
            try:
                version = '%d.%d.%d' % (int(app.get_major_version()),
                                        int(app.get_minor_version()),
                                        int(app.get_bugfix_version()))
            except Exception:
                version = str(app.get_version_string())
            self._osc.send('/beatspark/version', version)
            self.log_message('beatspark: version -> %s' % version)
        except Exception as e:
            self.log_message('beatspark: version error: %s' % str(e))
            self._osc.send('/beatspark/version', '')  # answered-but-unknown

    def _handle_set_tempo(self, args):
        if args:
            self.song().tempo = float(args[0])

    def _handle_set_device_param(self, args):
        """Set a LOM DeviceParameter to an explicit value. Args:
        [track_index, param_name, value, occurrence?]. Used by the authoring-side
        highlight resolver to restore a param after nudging it. The optional
        1-based occurrence picks WHICH device when several share the param name.
        No reply."""
        if len(args) < 3:
            return
        try:
            ti = int(args[0])
            param_name = args[1]
            value = float(args[2])
            try:
                occurrence = int(args[3]) if len(args) >= 4 else 1
            except Exception:
                occurrence = 1
            track_kind = args[4] if len(args) >= 5 else ''   # '' / 'return' / 'master'
            track = self._resolve_track(ti, track_kind)
            if track is None:
                return
            param = self._find_device_param(track.devices, param_name, occurrence=max(1, occurrence))
            if param is not None and getattr(param, 'is_enabled', True):
                param.value = max(float(param.min), min(float(param.max), value))
        except Exception as e:
            self.log_message('beatspark: set/device-param error: %s' % str(e))

    def _handle_nudge_device_param(self, args):
        """Authoring helper: momentarily move a param to a different value so the
        app can diff the macOS Accessibility tree and learn which on-screen
        control (AXDescription) maps to this LOM param. Args:
        [track_index, param_name, occurrence?]. Replies /beatspark/device-param/nudged
        with [ti, param_name, original, nudged, ok(1|0), reason]. The optional
        1-based occurrence picks WHICH device when several share the param name, so
        the diff learns the correct on-screen control. The app reads the a11y tree,
        then restores the value via /beatspark/set/device-param."""
        ti = -1
        param_name = ''
        try:
            if len(args) < 2:
                return
            ti = int(args[0])
            param_name = args[1]
            try:
                occurrence = int(args[2]) if len(args) >= 3 else 1
            except Exception:
                occurrence = 1
            track_kind = args[3] if len(args) >= 4 else ''   # '' / 'return' / 'master'
            track = self._resolve_track(ti, track_kind)
            if track is None:
                self._osc.send('/beatspark/device-param/nudged', ti, param_name, 0.0, 0.0, 0, 'bad-track')
                return
            param = self._find_device_param(track.devices, param_name, occurrence=max(1, occurrence))
            if param is None:
                self._osc.send('/beatspark/device-param/nudged', ti, param_name, 0.0, 0.0, 0, 'not-found')
                return
            if not getattr(param, 'is_enabled', True):
                self._osc.send('/beatspark/device-param/nudged', ti, param_name, 0.0, 0.0, 0, 'not-writable')
                return
            original = float(param.value)
            pmin = float(param.min)
            pmax = float(param.max)
            if pmax <= pmin:
                self._osc.send('/beatspark/device-param/nudged', ti, param_name, original, original, 0, 'no-range')
                return
            # Trust is_quantized — accessing param.value_items on a CONTINUOUS
            # param raises "Only quantized parameters have value items" (hasattr
            # is True for all params, so it can't guard the access).
            is_quant = bool(getattr(param, 'is_quantized', False))
            if is_quant:
                # Step to a clearly different discrete value (opposite end).
                nudged = pmin if original > (pmin + pmax) / 2.0 else pmax
            else:
                # ~20% of range — big enough to change the on-screen value display,
                # small-ish to stay gentle. Restored within a few hundred ms.
                delta = (pmax - pmin) * 0.2
                nudged = original + delta
                if nudged > pmax:
                    nudged = original - delta
                if nudged < pmin:
                    nudged = pmin
            try:
                param.value = nudged
            except Exception as se:
                # Isolate setter failures (read-only / range / device-state) from
                # everything else so the reason names the real cause.
                self.log_message('beatspark: nudge set-failed "%s": %s: %s' % (param_name, type(se).__name__, str(se)))
                self._osc.send('/beatspark/device-param/nudged', ti, param_name, original, original, 0,
                               ('set-failed %s: %s' % (type(se).__name__, str(se)))[:110])
                return
            self._osc.send('/beatspark/device-param/nudged', ti, param_name, original, float(param.value), 1, '')
        except Exception as e:
            err = '%s: %s' % (type(e).__name__, str(e))
            self.log_message('beatspark: nudge/device-param error: %s' % err)
            try:
                self._osc.send('/beatspark/device-param/nudged', ti, param_name, 0.0, 0.0, 0, ('error ' + err)[:110])
            except Exception:
                pass

    def _handle_watch_clip(self, args):
        """Start watching a clip slot for creation. Args: [track_index, clip_index]"""
        if len(args) >= 2:
            key = (int(args[0]), int(args[1]))
            if key not in self._clip_watchers:
                if len(self._clip_watchers) >= self._MAX_CLIP_WATCHERS:
                    self._clip_watchers.pop(0)
                self._clip_watchers.append(key)
                self.log_message('beatspark: watching clip slot %d/%d' % key)

    def _handle_watch_send_automation(self, args):
        """Watch a track's SEND value during playback so update_display can sample
        it as the playhead crosses a target beat. Args:
          [track_index, send_spec, at_beats, eps]
        send_spec is the send INDEX (int, 0=Return A, 1=Return B, …) OR a
        return-track NAME substring (str, e.g. "B-Delay"). Empty args clears the
        watch. ARRANGEMENT automation has no LOM envelope read, so observing the
        live param value at the crossing is the only way to verify it."""
        try:
            if not args:
                self._send_automation_watch = None
                return
            song = self.song()
            tracks = song.tracks
            ti = int(args[0])
            if ti < 0 or ti >= len(tracks):
                return
            mx = tracks[ti].mixer_device
            spec = args[1] if len(args) >= 2 else 0
            # send_spec may arrive as an int index or a return-name substring.
            try:
                send_idx = int(spec)
            except (ValueError, TypeError):
                send_idx = -1
                want = str(spec).lower()
                for i, rt in enumerate(song.return_tracks):
                    if want in str(rt.name).lower():
                        send_idx = i
                        break
            if send_idx < 0 or send_idx >= len(mx.sends):
                self.log_message('beatspark: send-automation watch - bad send "%s" on track %d' % (str(spec), ti))
                self._send_automation_watch = None
                return
            at_beats = float(args[2]) if len(args) >= 3 else 0.0
            eps = float(args[3]) if len(args) >= 4 else 0.1
            self._send_automation_watch = {
                'ti': ti, 'send': send_idx, 'at': at_beats, 'eps': eps,
                'last': float(song.current_song_time),
            }
            self.log_message('beatspark: watching send %d automation on track %d at beat %.3f (eps %.3f)'
                             % (send_idx, ti, at_beats, eps))
        except Exception as e:
            self.log_message('beatspark: send-automation watch error: %s' % str(e))
            self._send_automation_watch = None

    def _resolve_track(self, track_index, track_kind=''):
        """Resolve a (track_index, track_kind) reference to a Track object so
        wait_device_param can target RETURN + MASTER tracks (which aren't in
        song.tracks). track_kind: '' / 'track' -> song.tracks[track_index];
        'return' -> song.return_tracks[track_index]; 'master' -> song.master_track
        (index ignored). Returns None on out-of-range / error."""
        song = self.song()
        k = (str(track_kind) if track_kind is not None else '').lower()
        try:
            if k == 'master':
                return song.master_track
            if k in ('return', 'return_track', 'returntrack'):
                rts = song.return_tracks
                return rts[track_index] if 0 <= track_index < len(rts) else None
            tracks = song.tracks
            return tracks[track_index] if 0 <= track_index < len(tracks) else None
        except Exception:
            return None

    def _chain_index_of(self, track, device):
        """Top-level chain index (0-based) of `device` in track.devices, or of the
        rack that contains it (nested device -> its rack's panel). -1 if not found
        (e.g. a mixer param). Lets the app AUTO-SCOPE a device-param highlight to the
        device's panel without the author hardcoding `#N.1#` — reorder-safe."""
        if device is None:
            return -1
        def _contains(d, target):
            if d == target:
                return True
            try:
                for ch in (getattr(d, 'chains', None) or []):
                    for nd in (getattr(ch, 'devices', None) or []):
                        if _contains(nd, target):
                            return True
            except Exception:
                pass
            return False
        try:
            for i, d in enumerate(track.devices):
                if _contains(d, device):
                    return i
        except Exception:
            pass
        return -1

    def _find_device_param(self, devices, param_name, depth=0, max_depth=10, occurrence=1, _state=None):
        """Recursively search devices (and rack chains) for a DeviceParameter by name.

        occurrence (1-based) disambiguates when SEVERAL devices on the track
        expose the same param name (e.g. Chorus-Ensemble + Reverb both have
        'Dry/Wet'): devices are visited in chain order, recursing into racks, so
        occurrence N selects the Nth such device left-to-right. Defaults to 1
        (the first match — the historical behaviour). `_state` threads the match
        counter across the recursion; callers pass only occurrence."""
        if depth > max_depth:
            self.log_message('beatspark: _find_device_param max depth (%d) exceeded' % max_depth)
            return None
        if _state is None:
            _state = {'n': 0}
        for dev in devices:
            try:
                for p in dev.parameters:
                    if p.name == param_name:
                        _state['n'] += 1
                        if _state['n'] >= occurrence:
                            return p
                        break  # one matching param per device — move to the next
            except Exception:
                pass
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            found = self._find_device_param(chain.devices, param_name, depth + 1, max_depth, occurrence, _state)
                            if found is not None:
                                return found
            except Exception:
                pass
        return None

    def _log_device_params(self, devices, depth=0):
        """Recursively log all device parameter names - for discovery."""
        for dev in devices:
            try:
                names = [p.name for p in dev.parameters]
                self.log_message('beatspark: device "%s" params: %s' % (dev.name, ', '.join(names)))
            except Exception:
                pass
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            self._log_device_params(chain.devices, depth + 1)
            except Exception:
                pass

    def _collect_device_params(self, devices, device_path):
        """Walk devices and return a flat list of param dicts for lesson authoring.

        device_path is a slash-joined breadcrumb of parent device names so the
        author can disambiguate identical param names across a rack's chains.
        Each entry: {device, deviceClass, path, name, value, valueName, min, max,
        display, displayMin, displayMax, items: [str]}.

        min/max are Live's *internal* values (often normalized 0..1 for newer
        devices), which are useless to a lesson author. displayMin/displayMax are
        str_for_value() at those endpoints (e.g. "0.0 ms" / "250 ms") so the
        picker can show real units + range. Only emitted for non-quantized
        (continuous) params; quantized params carry their value_items instead.

        Defensive str() everywhere — Live exposes `name`, `class_name`, and
        value_items as Live-flavored strings (Live.Base.Live...) that
        json.dumps refuses to serialize. Coerce on the way in.
        """
        out = []
        for dev in devices:
            dev_name = str(getattr(dev, 'name', '?'))
            dev_class = str(getattr(dev, 'class_name', '?'))
            dev_class_display = str(getattr(dev, 'class_display_name', dev_class))
            path = (device_path + '/' + dev_name) if device_path else dev_name
            try:
                params = list(dev.parameters)
            except Exception:
                params = []
            for p in params:
                out.append(self._param_to_dict(p, dev_name, dev_class, dev_class_display, path))
            # Tier-2 observable ATTRIBUTES (Wavetable's wavetable category/index,
            # Simpler's playback_mode, ...) are NOT in .parameters — emit them in
            # the same param-dict shape so the recorder's snapshot diff, the
            # generator's wait_device_param derivation, and the editor's picker
            # all see them with zero downstream changes.
            try:
                for e in self._observable_device_attrs(dev):
                    pmax = float(len(e['items']) - 1) if e['items'] else (1.0 if e['kind'] == 'bool' else 0.0)
                    out.append({
                        'device': dev_name, 'deviceClass': dev_class, 'classDisplay': dev_class_display,
                        'path': path, 'name': e['attr'], 'value': e['value'],
                        'valueName': e['valueName'], 'min': 0.0, 'max': pmax,
                        'display': e['valueName'] or str(e['value']),
                        'displayMin': '', 'displayMax': '', 'items': e['items'],
                        'attr': True,
                    })
            except Exception:
                pass
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            chain_path = path + '/' + str(getattr(chain, 'name', '?'))
                            out.extend(self._collect_device_params(chain.devices, chain_path))
            except Exception:
                pass
        return out

    def _param_to_dict(self, p, dev_name, dev_class, dev_class_display, path):
        """One DeviceParameter → the authoring dict (units/range/enum). Shared by the
        device walk and the mixer collection so mixer params look identical to the picker."""
        try:
            val = float(p.value)
        except Exception:
            val = 0.0
        try:
            raw_items = list(p.value_items) if hasattr(p, 'value_items') else []
            items = [str(it) for it in raw_items]
        except Exception:
            items = []
        value_name = ''
        try:
            if items and 0 <= int(val) < len(items):
                value_name = items[int(val)]
        except Exception:
            pass
        try:
            pmin = float(p.min) if hasattr(p, 'min') else 0.0
        except Exception:
            pmin = 0.0
        try:
            pmax = float(p.max) if hasattr(p, 'max') else 1.0
        except Exception:
            pmax = 1.0
        display = ''
        display_min = ''
        display_max = ''
        try:
            if hasattr(p, 'str_for_value'):
                display = str(p.str_for_value(p.value))
                if not items:
                    display_min = str(p.str_for_value(pmin))
                    display_max = str(p.str_for_value(pmax))
        except Exception:
            pass
        return {
            'device': dev_name, 'deviceClass': dev_class, 'classDisplay': dev_class_display,
            'path': path, 'name': str(getattr(p, 'name', '?')), 'value': val,
            'valueName': value_name, 'min': pmin, 'max': pmax, 'display': display,
            'displayMin': display_min, 'displayMax': display_max, 'items': items,
        }

    def _mixer_params(self, track):
        """The track's MIXER DeviceParameters (volume, pan, sends). They live on
        track.mixer_device, NOT track.devices, so wait_device_param + the picker miss
        them without this. Names are e.g. 'Track Volume', 'Track Panning', 'Send A'."""
        out = []
        try:
            mx = track.mixer_device
            for getter in ('volume', 'panning'):
                try:
                    p = getattr(mx, getter, None)
                    if p is not None:
                        out.append(p)
                except Exception:
                    pass
            try:
                for s in mx.sends:
                    out.append(s)
            except Exception:
                pass
        except Exception:
            pass
        return out

    def _collect_mixer_params(self, track):
        return [self._param_to_dict(p, 'Mixer', 'MixerDevice', 'Mixer', 'Mixer')
                for p in self._mixer_params(track)]

    # OSC UDP payload limit on macOS (net.inet.udp.maxdgram) defaults to
    # 9216 bytes. We stay well under that to leave room for OSC framing
    # overhead (address string + type tags + padding). Bigger chunks = fewer
    # packets, but anything above ~6KB risks EMSGSIZE on some systems.
    _DEVICE_PARAMS_CHUNK_BYTES = 4096

    def _send_device_params(self, track_index, track_kind=''):
        """Dump every LOM DeviceParameter on the track for lesson authoring.
        track_kind ('' / 'return' / 'master') addresses return + master tracks.

        Chunks the JSON across multiple OSC messages to avoid the macOS UDP
        9216-byte maxdgram limit. Operator alone produces ~15KB.

        Wire protocol:
          /beatspark/device-params-chunk <trackIdx> <chunkIdx> <totalChunks> <fragment>
          /beatspark/device-params-done  <trackIdx> <totalChunks>

        Error path (always emits something so the Electron 5s timer doesn't fire):
          /beatspark/device-params-chunk <trackIdx> 0 1 <"{\\"error\\":\\"...\\",\\"params\\":[]}">
          /beatspark/device-params-done  <trackIdx> 1
        """
        self.log_message('beatspark: device-params received track=%d kind=%s' % (track_index, str(track_kind)))
        try:
            track = self._resolve_track(track_index, track_kind)
            if track is None:
                err = '{"error":"invalid-track","params":[]}'
                self._osc.send('/beatspark/device-params-chunk', track_index, 0, 1, err)
                self._osc.send('/beatspark/device-params-done', track_index, 1)
                self.log_message('beatspark: device-params invalid track index')
                return
            params = self._collect_device_params(track.devices, '') + self._collect_mixer_params(track)
            payload = {'trackIndex': int(track_index), 'trackName': str(track.name), 'params': params}
            try:
                import json
                blob = json.dumps(payload)
            except Exception as e:
                self.log_message('beatspark: device-params json error: %s' % str(e))
                blob = '{"error":"json-encode-failed","params":[]}'
            self._chunk_and_send_device_params(track_index, blob, len(params))
        except Exception as e:
            err_msg = str(e).replace('"', "'")
            self.log_message('beatspark: device-params error: %s' % err_msg)
            err = '{"error":"%s","params":[]}' % err_msg
            self._osc.send('/beatspark/device-params-chunk', track_index, 0, 1, err)
            self._osc.send('/beatspark/device-params-done', track_index, 1)

    def _chunk_and_send_device_params(self, track_index, blob, param_count):
        """Send a JSON blob in N chunks + a `done` sentinel."""
        chunk_size = self._DEVICE_PARAMS_CHUNK_BYTES
        total_bytes = len(blob)
        total_chunks = max(1, (total_bytes + chunk_size - 1) // chunk_size)
        for i in range(total_chunks):
            fragment = blob[i * chunk_size : (i + 1) * chunk_size]
            self._osc.send('/beatspark/device-params-chunk', track_index, i, total_chunks, fragment)
        self._osc.send('/beatspark/device-params-done', track_index, total_chunks)
        self.log_message('beatspark: device-params track=%d count=%d bytes=%d chunks=%d' % (
            track_index, param_count, total_bytes, total_chunks))

    def _find_modmatrix_device(self, devices):
        """Recursively find the first device exposing Wavetable's modulation-
        matrix FUNCTIONS (get_modulation_value + visible_modulation_target_names).
        Duck-typed rather than class-name matched so it survives Live renames and
        also catches a Wavetable nested inside an Instrument/Drum rack."""
        for dev in devices:
            try:
                if (hasattr(dev, 'get_modulation_value') and
                        hasattr(dev, 'visible_modulation_target_names')):
                    return dev
            except Exception:
                pass
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            found = self._find_modmatrix_device(chain.devices)
                            if found is not None:
                                return found
            except Exception:
                pass
        return None

    def _probe_wavetable_modmatrix(self, track_index):
        """Diagnostic dump of a Wavetable mod matrix. Wavetable's routings are NOT
        in device.parameters and the a11y tree is a dead end (see LOM reference),
        but the matrix IS readable via get_modulation_value(target_idx, source_idx).

        Targets come with names (visible_modulation_target_names /
        get_modulation_target_parameter_name); SOURCES are bare indices with no name
        property — this probe exists to learn the source index->name mapping
        empirically: set a known routing in the UI (e.g. LFO 1 -> Osc 1 Pos = 100%),
        run this, and read which (target, source) cell is nonzero.

        Result is logged to Log.txt (reliable) and sent chunked over OSC:
          /beatspark/wavetable-modmatrix-chunk <chunkIdx> <total> <fragment>
          /beatspark/wavetable-modmatrix-done  <total>
        """
        import json
        self.log_message('beatspark: wavetable-modmatrix probe track=%d' % track_index)
        try:
            tracks = self.song().tracks
            if track_index < 0 or track_index >= len(tracks):
                blob = json.dumps({'error': 'invalid-track'})
                self._chunk_and_send_blob(blob,
                    '/beatspark/wavetable-modmatrix-chunk',
                    '/beatspark/wavetable-modmatrix-done')
                return
            dev = self._find_modmatrix_device(tracks[track_index].devices)
            if dev is None:
                self.log_message('beatspark: wavetable-modmatrix no Wavetable on track')
                blob = json.dumps({'error': 'no-modmatrix-device', 'trackIndex': int(track_index)})
                self._chunk_and_send_blob(blob,
                    '/beatspark/wavetable-modmatrix-chunk',
                    '/beatspark/wavetable-modmatrix-done')
                return

            # Target names (matrix rows). visible_modulation_target_names is the
            # authoritative visible list; cross-check each via the per-index fn.
            try:
                targets = [str(n) for n in dev.visible_modulation_target_names]
            except Exception:
                targets = []
            target_count = len(targets)

            # Probe source count WITHOUT breaking on the first miss: a single index
            # may raise for one target but be valid for another, so test every
            # target before declaring an index invalid. Records the valid set so a
            # gap (UI shows 15 columns; API may expose fewer/renumbered) is visible.
            valid_sources = []
            if target_count > 0:
                for s in range(32):
                    ok = False
                    for t in range(target_count):
                        try:
                            dev.get_modulation_value(t, s)
                            ok = True
                            break
                        except Exception:
                            pass
                    if ok:
                        valid_sources.append(s)
                    elif valid_sources and s > valid_sources[-1] + 2:
                        break  # two consecutive misses past the last hit → done
            source_count = (valid_sources[-1] + 1) if valid_sources else 0

            # Full grid + nonzero convenience list.
            matrix = []
            nonzero = []
            for t in range(target_count):
                try:
                    name = str(dev.get_modulation_target_parameter_name(t))
                except Exception:
                    name = targets[t] if t < len(targets) else ('target_%d' % t)
                row = []
                for s in range(source_count):
                    try:
                        v = float(dev.get_modulation_value(t, s))
                    except Exception:
                        v = 0.0
                    row.append(round(v, 4))
                    if abs(v) > 1e-6:
                        nonzero.append([t, s, round(v, 4)])
                matrix.append({'index': t, 'name': name, 'values': row})

            self.log_message(
                'beatspark: wavetable-modmatrix dev=%s targets=%d sources=%d valid=%s nonzero=%s' % (
                    getattr(dev, 'name', '?'), target_count, source_count,
                    str(valid_sources), str(nonzero)))
            for m in matrix:
                self.log_message('beatspark: modmatrix t%d %s = %s' % (
                    m['index'], m['name'], str(m['values'])))

            payload = {
                'trackIndex': int(track_index),
                'deviceName': str(getattr(dev, 'name', '')),
                'targetCount': target_count,
                'sourceCount': source_count,
                'validSources': valid_sources,
                'targets': targets,
                'matrix': matrix,
                'nonzero': nonzero,
            }
            self._chunk_and_send_blob(json.dumps(payload),
                '/beatspark/wavetable-modmatrix-chunk',
                '/beatspark/wavetable-modmatrix-done')
        except Exception as e:
            err = str(e).replace('"', "'")
            self.log_message('beatspark: wavetable-modmatrix error: %s' % err)
            self._chunk_and_send_blob(json.dumps({'error': err}),
                '/beatspark/wavetable-modmatrix-chunk',
                '/beatspark/wavetable-modmatrix-done')

    def _resolve_mod_target_index(self, dev, target_spec):
        """Resolve a modulation TARGET to its matrix index. `target_spec` may be an
        int-like string (used directly as the index) or a name matched (exact, then
        case-insensitive substring) against BOTH the UI labels
        (visible_modulation_target_names, e.g. "Pitch") AND the LOM parameter names
        (get_modulation_target_parameter_name, e.g. "Transpose"). These differ for
        several targets (Amp/Volume, Pitch/Transpose, Osc 1 Warp/Osc 1 Effect 1), so
        authoring with the on-screen label must work too. Returns (index, name) or
        (-1, ''); name is the LOM name (canonical for logging)."""
        try:
            ui_names = [str(n) for n in dev.visible_modulation_target_names]
        except Exception:
            ui_names = []
        n = len(ui_names)
        lom_names = []
        for i in range(n):
            try:
                lom_names.append(str(dev.get_modulation_target_parameter_name(i)))
            except Exception:
                lom_names.append(ui_names[i])
        # Int index form.
        try:
            idx = int(str(target_spec))
            if 0 <= idx < n:
                return idx, lom_names[idx]
        except (ValueError, TypeError):
            pass
        spec = str(target_spec).strip().lower()
        # Exact match against either name list.
        for i in range(n):
            if lom_names[i].strip().lower() == spec or ui_names[i].strip().lower() == spec:
                return i, lom_names[i]
        # Substring match against either name list.
        for i in range(n):
            if spec in lom_names[i].strip().lower() or spec in ui_names[i].strip().lower():
                return i, lom_names[i]
        return -1, ''

    def _send_mod_value(self, track_index, source_index, target_spec):
        """Focused read of one Wavetable mod-matrix cell for wait_mod_routing.
        Wire: /beatspark/wavetable/mod-value <trackIdx> <targetIdx> <sourceIdx>
              <value> <targetName>  (targetIdx = -1 when the device/target is missing)."""
        try:
            tracks = self.song().tracks
            if track_index < 0 or track_index >= len(tracks):
                self._osc.send('/beatspark/wavetable/mod-value', track_index, -1, source_index, 0.0, '')
                return
            dev = self._find_modmatrix_device(tracks[track_index].devices)
            if dev is None:
                self._osc.send('/beatspark/wavetable/mod-value', track_index, -1, source_index, 0.0, '')
                return
            tgt_idx, tgt_name = self._resolve_mod_target_index(dev, target_spec)
            if tgt_idx < 0:
                self._osc.send('/beatspark/wavetable/mod-value', track_index, -1, source_index, 0.0, '')
                return
            try:
                value = float(dev.get_modulation_value(tgt_idx, int(source_index)))
            except Exception:
                value = 0.0
            self._osc.send('/beatspark/wavetable/mod-value', track_index, tgt_idx,
                           int(source_index), value, tgt_name)
        except Exception as e:
            self.log_message('beatspark: mod-value error: %s' % str(e))
            self._osc.send('/beatspark/wavetable/mod-value', track_index, -1, source_index, 0.0, '')

    def _chunk_and_send_blob(self, blob, chunk_addr, done_addr):
        """Generic chunked JSON sender: <chunk_addr> <chunkIdx> <total> <fragment>
        then <done_addr> <total>. Used by the offline device-catalog dump."""
        chunk_size = self._DEVICE_PARAMS_CHUNK_BYTES
        total_chunks = max(1, (len(blob) + chunk_size - 1) // chunk_size)
        for i in range(total_chunks):
            fragment = blob[i * chunk_size:(i + 1) * chunk_size]
            self._osc.send(chunk_addr, i, total_chunks, fragment)
        self._osc.send(done_addr, total_chunks)
        return total_chunks

    def _live_version_string(self):
        try:
            return str(self.application().get_version_string())
        except Exception:
            return ''

    def _send_device_catalog(self):
        """Dump every device + parameter across ALL tracks (regular + return +
        master) for the offline catalog generator (roadmap P2). Reuses
        _collect_device_params; adds the Live version. Chunked on dedicated
        addresses so it never collides with per-track device-params.

        Wire: /beatspark/device-catalog-chunk <chunkIdx> <total> <fragment>
              /beatspark/device-catalog-done  <total>
        """
        self.log_message('beatspark: device-catalog requested')
        try:
            song = self.song()
            tracks = list(song.tracks)
            try:
                tracks += list(song.return_tracks)
            except Exception:
                pass
            try:
                if song.master_track is not None:
                    tracks.append(song.master_track)
            except Exception:
                pass
            params = []
            attrs = []
            for track in tracks:
                try:
                    params.extend(self._collect_device_params(track.devices, ''))
                    params.extend(self._collect_mixer_params(track))
                except Exception:
                    pass
                try:
                    attrs.extend(self._collect_device_attrs(track.devices))
                except Exception:
                    pass
            payload = {'liveVersion': self._live_version_string(), 'params': params, 'attrs': attrs}
            import json
            try:
                blob = json.dumps(payload)
            except Exception as e:
                self.log_message('beatspark: device-catalog json error: %s' % str(e))
                blob = '{"error":"json-encode-failed","params":[]}'
            total = self._chunk_and_send_blob(blob, '/beatspark/device-catalog-chunk', '/beatspark/device-catalog-done')
            self.log_message('beatspark: device-catalog count=%d attrs=%d bytes=%d chunks=%d' % (
                len(params), len(attrs), len(blob), total))
        except Exception as e:
            err_msg = str(e).replace('"', "'")
            self.log_message('beatspark: device-catalog error: %s' % err_msg)
            err = '{"error":"%s","params":[]}' % err_msg
            self._osc.send('/beatspark/device-catalog-chunk', 0, 1, err)
            self._osc.send('/beatspark/device-catalog-done', 1)

    # Attributes we never want in the discovered Tier-2 set: structural LOM
    # collections / navigation, read-only status, rack/macro internals, and
    # routing objects (handled separately / curated). Verified against a full
    # 12.4 dump — these are the names that showed up as noise.
    _ATTR_DENYLIST = set([
        # structural / navigation
        'parameters', 'chains', 'return_chains', 'drum_pads', 'visible_drum_pads',
        'view', 'canonical_parent', 'sample', 'sample_slices',
        # read-only status (on every device)
        'is_active', 'latency_in_ms', 'latency_in_samples', 'name',
        'is_using_compare_preset_b', 'has_drum_pads',
        # rack / macro internals
        'has_macro_mappings', 'is_showing_chains', 'macros_mapped',
        'visible_macro_count', 'variation_count',
        # routing: the current-value type/channel attrs are NOW verifiable via their
        # .display_name (see _routing_display_name) — e.g. a Gate/Compressor sidechain
        # source. Only the backing collections / raw IO lists stay hidden.
        'audio_inputs', 'audio_outputs', 'midi_inputs', 'midi_outputs',
        'available_input_routing_channels', 'available_input_routing_types',
        'available_output_routing_channels', 'available_output_routing_types',
        # device-specific read-only status
        'can_warp_as', 'can_warp_double', 'can_warp_half',
        'playing_position', 'playing_position_enabled',
    ])

    def _routing_display_name(self, raw):
        """Extract the display string from a routing value. Live's Python API returns
        a RoutingType/RoutingChannel OBJECT with `.display_name` (the M4L 'dictionary'
        is the Max view); also tolerate a dict. Returns None for plain scalars — so
        callers can use it to detect a routing attr (input/output_routing_type/channel)."""
        try:
            dn = getattr(raw, 'display_name', None)
            if dn is not None:
                return str(dn)
        except Exception:
            pass
        try:
            if isinstance(raw, dict) and 'display_name' in raw:
                return str(raw['display_name'])
        except Exception:
            pass
        return None

    def _routing_options(self, dev, attr):
        """Available routing display names for a routing attr (input_routing_type ->
        available_input_routing_types). For the picker's dropdown; [] if not routing."""
        try:
            av = getattr(dev, 'available_' + attr + 's', None)
            if av is None:
                return []
            return [self._routing_display_name(o) or str(o) for o in list(av)]
        except Exception:
            return []

    def _resolve_attr_list(self, dev, attr):
        """Return the enum-name list for an attr via Live's `<attr>_list` /
        `<attr>s` / `available_<attr>s` conventions (shared by the attr GET
        path and _attach_device_attr_listener). Empty list when not an enum."""
        candidates = [attr + '_list', attr + 's', 'available_' + attr + 's']
        if attr.endswith('_index'):
            candidates.append(attr.replace('_index', '_list'))
            # Wavetable: oscillator_1_wavetable_index → oscillator_1_wavetables
            candidates.append(attr.replace('_index', 's'))
        if attr.endswith('y'):
            # oscillator_1_wavetable_category → ..._categories
            candidates.append(attr[:-1] + 'ies')
        # Some backing lists drop a positional qualifier — Wavetable's category
        # list is shared across both oscillators (oscillator_1_wavetable_category
        # → oscillator_wavetable_categories). Try each candidate with the first
        # `_<digit>` segment removed too.
        for c in list(candidates):
            collapsed = re.sub(r'_\d+', '', c, count=1)
            if collapsed != c:
                candidates.append(collapsed)
        for la in candidates:
            try:
                raw = getattr(dev, la, None)
                if raw is not None:
                    return [str(x) for x in list(raw)]
            except Exception:
                continue
        return []

    def _observable_device_attrs(self, dev):
        """Tier-2 discovery for ONE device: every observable attribute that is
        NOT a DeviceParameter (`add_<attr>_listener` + underlying attr = the
        authoritative "real control" test). Yields
        {attr, value, valueName, items, kind} with kind ∈ enum | bool | number;
        text/complex attrs are skipped. Shared by the catalog dump, the
        device-params snapshot, and the watch-all listener attach — Wavetable's
        wavetable category/index selectors live here, not in .parameters.
        """
        out = []
        try:
            names = set(dir(dev))
            found = sorted(
                a[4:-9] for a in names
                if a.startswith('add_') and a.endswith('_listener') and a[4:-9] in names
            )
        except Exception:
            return out
        for attr in found:
            if attr in self._ATTR_DENYLIST:
                continue
            # `<x>_list` are the backing enum arrays for `<x>`, not controls.
            if attr.endswith('_list'):
                continue
            try:
                raw = getattr(dev, attr)
            except Exception:
                continue
            # Routing attrs (sidechain source etc.): object/dict with .display_name.
            # Surface as a text/enum control valued by the display string so the
            # picker offers it and wait_device_param can verify it.
            _routeDisp = self._routing_display_name(raw)
            if _routeDisp is not None:
                _opts = self._routing_options(dev, attr)
                out.append({'attr': attr, 'value': 0.0, 'valueName': _routeDisp,
                            'items': _opts, 'kind': 'enum' if _opts else 'text'})
                continue
            items = self._resolve_attr_list(dev, attr)
            value = 0.0
            value_name = ''
            if items:
                kind = 'enum'
                try:
                    value = float(raw)
                    idx = int(value)
                    if 0 <= idx < len(items):
                        value_name = items[idx]
                except Exception:
                    pass
            elif isinstance(raw, bool) or attr.endswith('_on') or attr.endswith('_enabled'):
                kind = 'bool'
                try:
                    value = 1.0 if bool(raw) else 0.0
                except Exception:
                    pass
            elif isinstance(raw, (int, float)):
                kind = 'number'
                try:
                    value = float(raw)
                except Exception:
                    pass
            else:
                # Backing list / name / complex object — not a verifiable control.
                continue
            out.append({'attr': attr, 'value': value, 'valueName': value_name,
                        'items': items, 'kind': kind})
        return out

    def _collect_device_attrs(self, devices):
        """Structured Tier-2 discovery: every observable attribute that is NOT a
        DeviceParameter, across devices (recursing into rack chains). The
        `add_<attr>_listener` + underlying-attr signal (same as _log_device_attrs)
        is the authoritative "this is a real control" test — so the union of this
        across all loaded devices IS the complete Tier-2 set, no guessing.

        Each entry: {classDisplay, deviceClass, attr, value, valueName, items, kind}
        kind ∈ enum | bool | number | text (text = complex/dict-valued → a11y-preferred).
        """
        out = []
        for dev in devices:
            try:
                dev_class = str(getattr(dev, 'class_name', '?'))
                dev_class_display = str(getattr(dev, 'class_display_name', dev_class))
                for e in self._observable_device_attrs(dev):
                    out.append({
                        'classDisplay': dev_class_display,
                        'deviceClass': dev_class,
                        'attr': e['attr'],
                        'value': e['value'],
                        'valueName': e['valueName'],
                        'items': e['items'],
                        'kind': e['kind'],
                    })
            except Exception:
                pass
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            out.extend(self._collect_device_attrs(chain.devices))
            except Exception:
                pass
        return out

    def _log_device_attrs(self, devices, depth=0):
        """Recursively log every listenable attribute on each device.

        A "listenable" attr is one with a matching `add_<X>_listener` method —
        that's the universal signal that Live exposes the value as observable.
        This is broader than the old mod/source/target-only filter and is
        intended for lesson-author discovery: when wait_device_param can't
        find a name, the author tails Live's Log.txt and sees the real names.
        """
        for dev in devices:
            try:
                cls = getattr(dev, 'class_name', '?')
                names = set(dir(dev))
                listenable = sorted(
                    a for a in names
                    if a.startswith('add_') and a.endswith('_listener')
                    and a[4:-9] in names  # the underlying attr also exists
                )
                attrs = [a[4:-9] for a in listenable]
                self.log_message('beatspark: device "%s" (class=%s) listenable attrs: %s' % (dev.name, cls, ', '.join(attrs)))
            except Exception as e:
                self.log_message('beatspark: device-attr dump error: %s' % str(e))
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            self._log_device_attrs(chain.devices, depth + 1)
            except Exception:
                pass

    def _attr_path_exists(self, obj, dotted):
        """True if a (possibly dotted) attribute path resolves on obj.
        e.g. _attr_path_exists(simpler, "sample.warping") walks simpler.sample
        and checks for `warping`. A single name behaves like hasattr."""
        cur = obj
        parts = dotted.split('.')
        for p in parts[:-1]:
            cur = getattr(cur, p, None)
            if cur is None:
                return False
        return hasattr(cur, parts[-1])

    def _find_device_with_attr(self, devices, attr_name, occurrence=1, _state=None):
        """Recursively find the device (including nested in racks) that exposes the
        given attribute name. Used for Drift-style modulation source/target attrs
        like 'modulation_source_shape_index' that aren't in .parameters. Also accepts
        a dotted path into a child object (e.g. 'sample.warping' on Simpler/Sampler).

        occurrence (1-based) selects the Nth device exposing the attr, in chain
        order — the attribute mirror of _find_device_param's disambiguation."""
        if _state is None:
            _state = {'n': 0}
        for dev in devices:
            try:
                if self._attr_path_exists(dev, attr_name):
                    _state['n'] += 1
                    if _state['n'] >= occurrence:
                        return dev
            except Exception:
                pass
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            found = self._find_device_with_attr(chain.devices, attr_name, occurrence, _state)
                            if found is not None:
                                return found
            except Exception:
                pass
        return None

    def _handle_watch_device_param(self, args):
        """Watch a device control's value. Args: [track_index, param_name].
        Registers a value listener and sends /beatspark/device-param/value on
        change. Also sends the current value immediately.

        Three param forms are accepted, in this order:
         1. DeviceParameter name in `.parameters` (e.g. "Osc 1 On", "Volume")
         2. Device attribute (e.g. "slicing_style", "playback_mode",
            "modulation_source_shape_index"). If a parallel "<attr>_list"
            exists, it's used to map int values to enum names so lesson
            authors can write `target: "Beat"` instead of `target: 1`.
         3. Not found → log + dump candidate params + attrs for the author.

        This makes `wait_device_param` the universal verifier across every
        Live device — no new step types per knob, toggle, or dropdown.
        """
        if len(args) < 2:
            return
        ti = int(args[0])
        param_name = args[1]
        # Optional 3rd arg: 1-based device occurrence — which device to target when
        # several on the track expose this same param (Chorus + Reverb both have
        # 'Dry/Wet'). Absent/old callers → 1 (first match, historical behaviour).
        try:
            occurrence = int(args[2]) if len(args) >= 3 else 1
        except Exception:
            occurrence = 1
        if occurrence < 1:
            occurrence = 1
        # Optional 4th arg: track_kind ('' / 'return' / 'master') so wait_device_param
        # can target a return/master track's device. Absent -> regular song.tracks[ti].
        track_kind = args[3] if len(args) >= 4 else ''
        track = self._resolve_track(ti, track_kind)
        if track is None:
            self.log_message('beatspark: watch/device-param: invalid track %d (kind=%s)' % (ti, str(track_kind)))
            return

        # Key includes occurrence so the watcher dict can hold distinct devices.
        # But only ONE device per (track, param) should report at a time: tear down
        # EVERY prior watcher for this (track, param) — any occurrence — before
        # attaching the new one. Otherwise a still-attached watcher on another
        # device with the same param name (Chorus's 'Dry/Wet' from an earlier step)
        # keeps firing and could false-satisfy the current step.
        for k in [k for k in list(self._device_param_watchers.keys())
                  if isinstance(k, tuple) and len(k) >= 2 and k[0] == ti and k[1] == param_name]:
            try:
                self._device_param_watchers[k]()
            except Exception:
                pass
            del self._device_param_watchers[k]

        # Path 1: DeviceParameter (most common — explicit param objects)
        param = self._find_device_param(track.devices, param_name, occurrence=occurrence)
        # Path 1b: the track MIXER's params (Track Volume / Track Panning / Send A…)
        # — they're on track.mixer_device, not track.devices.
        if param is None:
            for mp in self._mixer_params(track):
                try:
                    if mp.name == param_name:
                        param = mp
                        break
                except Exception:
                    pass
        if param is not None:
            # Chain index of the owning device (from the param's canonical_parent) so
            # the app can auto-scope the highlight to that panel. -1 for mixer params.
            chain_index = self._chain_index_of(track, getattr(param, 'canonical_parent', None))
            self._attach_device_param_listener(ti, param_name, param, occurrence, chain_index)
            return

        # Path 2: device attribute (e.g. slicing_style, playback_mode).
        # We try this for ANY name that isn't a DeviceParameter — not just
        # "_index" attrs. Lets the author write `param: "slicing_style"`
        # and target the enum value by name via the parallel `<attr>_list`.
        device = self._find_device_with_attr(track.devices, param_name, occurrence=occurrence)
        if device is not None:
            chain_index = self._chain_index_of(track, device)
            self._attach_device_attr_listener(ti, param_name, device, occurrence, chain_index)
            return

        # Path 3: not found anywhere — emit diagnostic dumps so the author
        # can find the right name.
        self.log_message('beatspark: watch/device-param: "%s" not found on track %d. Dumping available params + attrs:' % (param_name, ti))
        self._log_device_params(track.devices)
        self._log_device_attrs(track.devices)

    def _attach_device_param_listener(self, ti, param_name, param, occurrence=1, chain_index=-1):
        """Path 1 helper — DeviceParameter with `.add_value_listener`. chain_index =
        the owning device's top-level chain index (echoed so the app auto-scopes the
        highlight); -1 = unknown/mixer."""
        def _on_change():
            try:
                val = float(param.value)
                value_name = ''
                try:
                    items = list(param.value_items) if hasattr(param, 'value_items') else []
                    if items and 0 <= int(val) < len(items):
                        value_name = items[int(val)]
                except Exception:
                    pass
                pmin = float(param.min) if hasattr(param, 'min') else 0.0
                pmax = float(param.max) if hasattr(param, 'max') else 1.0
                display = ''
                try:
                    if hasattr(param, 'str_for_value'):
                        display = str(param.str_for_value(param.value))
                except Exception:
                    pass
                self._osc.send('/beatspark/device-param/value', ti, param_name, val, value_name, pmin, pmax, display, int(chain_index))
            except Exception as e:
                self.log_message('beatspark: device-param listener error: %s' % str(e))

        try:
            param.add_value_listener(_on_change)
            def _teardown():
                try:
                    param.remove_value_listener(_on_change)
                except Exception:
                    pass
            self._device_param_watchers[(ti, param_name, occurrence)] = _teardown
            self.log_message('beatspark: watching track %d param "%s" (current=%.4f)' % (ti, param_name, float(param.value)))
            _on_change()  # Send current value immediately
        except Exception as e:
            self.log_message('beatspark: watch/device-param registration failed: %s' % str(e))

    def _attach_device_attr_listener(self, ti, attr_name, device, occurrence=1, chain_index=-1):
        """Path 2 helper — direct device attribute with `add_<attr>_listener`.

        Looks for `<attr>_list` to resolve the int value to an enum name.
        Convention in Live: `slicing_style` has `slicing_style_list`,
        `modulation_source_shape_index` has `modulation_source_shape_list`
        (note the `_index` → `_list` rewrite for that historical shape).

        `attr_name` may be a dotted path into a child object (e.g.
        `sample.warping` on Simpler/Sampler). We listen on the leaf attr of the
        resolved child (the *bearer*), but echo the full dotted name back over
        OSC so the lesson's `param` still matches. `warping` is a bool → val
        0.0/1.0, which `wait_device_param`'s on/off check reads directly.
        """
        # Resolve a dotted path to the object that actually bears the leaf attr.
        bearer = device
        leaf = attr_name
        if '.' in attr_name:
            parts = attr_name.split('.')
            for p in parts[:-1]:
                bearer = getattr(bearer, p, None)
                if bearer is None:
                    self.log_message('beatspark: device-attr path "%s": missing "%s"' % (attr_name, p))
                    return
            leaf = parts[-1]

        def _on_attr_change():
            try:
                raw_val = getattr(bearer, leaf)
                # Routing attrs (input/output_routing_type/channel) are objects with
                # a .display_name (the dropdown's text, e.g. "Dubstep Drums" /
                # "Kick Amber"). Verify against that string — send it as value_name so
                # wait_device_param's valueName match fires on `target: "Dubstep Drums"`.
                disp = self._routing_display_name(raw_val)
                if disp is not None:
                    self._osc.send('/beatspark/device-param/value', ti, attr_name, 0.0, disp, 0.0, 0.0, '', int(chain_index))
                    return
                # Most enum attrs return int; non-enum attrs (e.g. floats)
                # are also fine via float() cast.
                try:
                    val = float(raw_val)
                except (TypeError, ValueError):
                    val = 0.0
                # Resolve the enum-name list on every fire, not once at attach:
                # Wavetable's oscillator_N_wavetables list CHANGES when the
                # category changes, so a cached list would mislabel values.
                items = self._resolve_attr_list(bearer, leaf)
                value_name = ''
                try:
                    idx = int(val)
                    if items and 0 <= idx < len(items):
                        value_name = items[idx]
                except Exception:
                    pass
                pmax = float(len(items) - 1) if items else 0.0
                self._osc.send('/beatspark/device-param/value', ti, attr_name, val, value_name, 0.0, pmax, '', int(chain_index))
            except Exception as e:
                self.log_message('beatspark: device-attr listener error: %s' % str(e))

        listener_name = 'add_' + leaf + '_listener'
        remove_name = 'remove_' + leaf + '_listener'
        try:
            getattr(bearer, listener_name)(_on_attr_change)
            def _teardown():
                try:
                    getattr(bearer, remove_name)(_on_attr_change)
                except Exception:
                    pass
            self._device_param_watchers[(ti, attr_name, occurrence)] = _teardown
            self.log_message('beatspark: watching track %d device-attr "%s" (occurrence %d)' % (ti, attr_name, occurrence))
            _on_attr_change()
        except Exception as e:
            self.log_message('beatspark: device-attr listener registration failed (%s): %s' % (listener_name, str(e)))

    def _handle_watch_track_params(self, args):
        """Watch *every* DeviceParameter on a track for change. Args: [track_index].

        Used by the builder's Capture flow: the author demonstrates a tweak
        in Ableton, and beatspark needs to discover which param changed
        without the author knowing the LOM name in advance.

        Each param change emits:
          /beatspark/track-param-changed <ti> <devicePath> <paramName> <value> <valueName> <display>

        Idempotent: re-watching the same track tears down the prior watcher
        set first. Pair with `/beatspark/unwatch/track-params <ti>` to stop.
        """
        if len(args) < 1:
            return
        ti = int(args[0])
        tracks = self.song().tracks
        if ti < 0 or ti >= len(tracks):
            self.log_message('beatspark: watch/track-params: invalid track %d' % ti)
            return
        # Tear down any prior watchers for this track
        self._teardown_track_watchers(ti)
        track = tracks[ti]
        teardowns = []
        try:
            self._attach_track_param_listeners(ti, track.devices, '', teardowns)
            # Also watch the MIXER params (volume/pan/sends) so the Capture flow +
            # recorder see "turned the track down / panned it / raised a send".
            for p in self._mixer_params(track):
                self._register_param_change_listener(ti, 'Mixer', 'MixerDevice', p, teardowns)
            # Mute/solo aren't DeviceParameters — push them on change too, so the
            # recorder captures "muted the bass" / "soloed the kick".
            try:
                def _mute_cb():
                    try: self._send_track_mute(ti)
                    except Exception: pass
                def _solo_cb():
                    try: self._send_track_solo(ti)
                    except Exception: pass
                track.add_mute_listener(_mute_cb)
                track.add_solo_listener(_solo_cb)
                teardowns.append(lambda: track.remove_mute_listener(_mute_cb))
                teardowns.append(lambda: track.remove_solo_listener(_solo_cb))
            except Exception:
                pass
        except Exception as e:
            self.log_message('beatspark: watch/track-params attach error: %s' % str(e))
        self._track_watchers[ti] = teardowns
        self.log_message('beatspark: watching track %d params (n=%d)' % (ti, len(teardowns)))

    def _handle_unwatch_track_params(self, args):
        """Stop watching every param on a track. Args: [track_index]."""
        if len(args) < 1:
            return
        ti = int(args[0])
        self._teardown_track_watchers(ti)
        self.log_message('beatspark: unwatched track %d params' % ti)

    def _teardown_track_watchers(self, ti):
        teardowns = self._track_watchers.pop(ti, None)
        if not teardowns:
            return
        for fn in teardowns:
            try:
                fn()
            except Exception:
                pass

    def _attach_track_param_listeners(self, ti, devices, device_path, teardowns):
        """Recurse into devices (and rack chains), attaching a value listener
        to every DeviceParameter. Each callback sends one OSC message naming
        the device path, param, new value, valueName (enum), and display string.
        teardowns is mutated — each registration appends its remover."""
        for dev in devices:
            dev_name = str(getattr(dev, 'name', '?'))
            dev_class = str(getattr(dev, 'class_name', '?'))
            dev_class_display = str(getattr(dev, 'class_display_name', dev_class))
            path = (device_path + '/' + dev_name) if device_path else dev_name
            try:
                params = list(dev.parameters)
            except Exception:
                params = []
            for p in params:
                # Bind param + path + device class in a closure so each callback
                # knows which param/device fired (class keys the a11y map).
                self._register_param_change_listener(ti, path, dev_class_display, p, teardowns)
            # Tier-2 attrs (wavetable category/index, playback_mode, ...) have
            # their own add_<attr>_listener — watch them too so the builder's
            # Capture flow and the recorder see selector changes live.
            try:
                for e in self._observable_device_attrs(dev):
                    self._register_attr_change_listener(ti, path, dev_class_display, dev, e['attr'], teardowns)
            except Exception:
                pass
            # Recurse into nested rack chains.
            try:
                if hasattr(dev, 'chains'):
                    for chain in dev.chains:
                        if hasattr(chain, 'devices'):
                            chain_name = str(getattr(chain, 'name', '?'))
                            self._attach_track_param_listeners(
                                ti, chain.devices, path + '/' + chain_name, teardowns)
            except Exception:
                pass

    def _register_param_change_listener(self, ti, device_path, class_display, p, teardowns):
        param_name = str(getattr(p, 'name', '?'))

        def _on_change():
            try:
                val = float(p.value)
                value_name = ''
                try:
                    items = list(p.value_items) if hasattr(p, 'value_items') else []
                    if items and 0 <= int(val) < len(items):
                        value_name = str(items[int(val)])
                except Exception:
                    pass
                display = ''
                try:
                    if hasattr(p, 'str_for_value'):
                        display = str(p.str_for_value(p.value))
                except Exception:
                    pass
                self._osc.send('/beatspark/track-param-changed',
                               ti, device_path, param_name, val, value_name, display, class_display)
            except Exception as e:
                self.log_message('beatspark: track-param listener error: %s' % str(e))

        try:
            p.add_value_listener(_on_change)
        except Exception:
            return

        def _teardown():
            try:
                p.remove_value_listener(_on_change)
            except Exception:
                pass
        teardowns.append(_teardown)

    def _register_attr_change_listener(self, ti, device_path, class_display, dev, attr, teardowns):
        """Watch-all companion for Tier-2 device ATTRIBUTES (not DeviceParameters).
        Sends the same /beatspark/track-param-changed wire shape with the attr
        name as the param name. The enum-name list is re-resolved on every fire
        — Wavetable's oscillator_N_wavetables list changes when the category
        changes, so a cached list would mislabel values."""
        def _on_change():
            try:
                raw_val = getattr(dev, attr)
                try:
                    val = float(raw_val)
                except (TypeError, ValueError):
                    val = 0.0
                items = self._resolve_attr_list(dev, attr)
                value_name = ''
                try:
                    idx = int(val)
                    if items and 0 <= idx < len(items):
                        value_name = items[idx]
                except Exception:
                    pass
                self._osc.send('/beatspark/track-param-changed',
                               ti, device_path, attr, val, value_name, value_name, class_display)
            except Exception as e:
                self.log_message('beatspark: track-attr listener error: %s' % str(e))

        try:
            getattr(dev, 'add_' + attr + '_listener')(_on_change)
        except Exception:
            return

        def _teardown():
            try:
                getattr(dev, 'remove_' + attr + '_listener')(_on_change)
            except Exception:
                pass
        teardowns.append(_teardown)

    def _send_song_file_path(self):
        """Send the current song's file_path (absolute path, or empty for unsaved)."""
        try:
            path = self.song().file_path or ''
        except Exception as e:
            self.log_message('beatspark: song-file-path error: %s' % str(e))
            path = ''
        self._osc.send('/beatspark/song/file-path', path)

    def _send_song_modified(self):
        """Send 1 if the song has unsaved changes, 0 if clean, -1 if LOM can't tell.
        Used by main.js save-progress to detect "saved over same path" where the
        path stays the same but the dirty flag transitions true -> false."""
        flag = -1
        try:
            # Live 11+ exposes is_modified; older versions may not.
            if hasattr(self.song(), 'is_modified'):
                flag = 1 if self.song().is_modified else 0
        except Exception as e:
            self.log_message('beatspark: song-modified error: %s' % str(e))
        self._osc.send('/beatspark/song/modified', flag)

    def _probe_clip_view(self):
        """Diagnostic: dump every readable attribute of song.view.detail_clip.view,
        focused on names that could plausibly describe the visible bar/pitch
        viewport (vs the loop region we already know about). Logs the full
        dump to Live's log file and sends a compact summary via OSC."""
        try:
            song = self.song()
            clip = song.view.detail_clip
            if clip is None:
                self.log_message('beatspark: clip-view-probe - no detail_clip open')
                self._osc.send('/beatspark/clip-view-probe', 'no-clip')
                return
            cv = clip.view
            self.log_message('beatspark: clip-view-probe - clip type=%s' % type(clip).__name__)
            # Names worth checking explicitly + prefix matches for anything else.
            interesting_prefixes = ('show_', 'visible', 'scroll', 'editing', 'pitch', 'bar', 'time', 'loop', 'view')
            attrs = []
            try:
                attrs = sorted([a for a in dir(cv) if not a.startswith('_')])
            except Exception:
                pass
            self.log_message('beatspark: clip-view-probe - %d public attrs on clip.view' % len(attrs))
            summary_parts = []
            for name in attrs:
                lname = name.lower()
                if not any(lname.startswith(p) or p in lname for p in interesting_prefixes):
                    continue
                try:
                    val = getattr(cv, name)
                    if callable(val):
                        # method - note its existence but don't call
                        self.log_message('beatspark: clip-view-probe   %s = <callable>' % name)
                        summary_parts.append('%s=callable' % name)
                    else:
                        s = str(val)
                        if len(s) > 80:
                            s = s[:80] + '...'
                        self.log_message('beatspark: clip-view-probe   %s = %s' % (name, s))
                        summary_parts.append('%s=%s' % (name, s))
                except Exception as e:
                    self.log_message('beatspark: clip-view-probe   %s -> ERROR: %s' % (name, str(e)))
            # Also probe the detail clip object itself for visible-range fields.
            for name in ('view', 'is_arrangement_clip', 'looping', 'loop_start', 'loop_end',
                         'start_time', 'end_time', 'start_marker', 'end_marker'):
                try:
                    val = getattr(clip, name)
                    if not callable(val):
                        s = str(val)[:60]
                        self.log_message('beatspark: clip-view-probe   clip.%s = %s' % (name, s))
                except Exception:
                    pass
            self._osc.send('/beatspark/clip-view-probe', ' | '.join(summary_parts) or 'empty')
        except Exception as e:
            self.log_message('beatspark: clip-view-probe error: %s' % str(e))
            self._osc.send('/beatspark/clip-view-probe', 'error:' + str(e))

    def _send_clip_pitch_range(self, track_index, clip_index):
        """Send min/max MIDI pitch present in a clip's note list. Used by
        the cross-platform note-block detector as an octave anchor: the
        top-most detected colored block corresponds to the max pitch."""
        try:
            # clip_index == -1 → the currently-open detail clip (arrangement view,
            # where session slots are empty). The 0 <= clip_index guard in the else
            # avoids slots[-1] silently grabbing the LAST session slot.
            clip = None
            if clip_index == -1:
                clip = self.song().view.detail_clip
            else:
                tracks = self.song().tracks
                if 0 <= track_index < len(tracks):
                    slots = tracks[track_index].clip_slots
                    if 0 <= clip_index < len(slots) and slots[clip_index].has_clip:
                        clip = slots[clip_index].clip
            if clip is not None:
                notes = []
                try:
                    notes = clip.get_notes_extended(0, 128, 0, clip.length)
                except Exception:
                    try:
                        notes = clip.get_notes(0, 0, clip.length, 128)
                    except Exception:
                        notes = []
                if notes:
                    # get_notes_extended → list of MidiNote objects with .pitch
                    # get_notes (legacy) → list of (pitch, time, dur, vel, mute) tuples
                    pitches = set()
                    for n in notes:
                        try:
                            p = n.pitch
                        except AttributeError:
                            p = n[0]
                        pitches.add(int(p))
                    if pitches:
                        sorted_pitches = sorted(pitches)
                        # Send full sorted unique pitch list as trailing args.
                        # Lets the cross-platform block detector unambiguously
                        # map detected blocks (sorted by Y) → pitches (sorted
                        # descending), removing the previous topmost-block-is-
                        # max-pitch heuristic.
                        self._osc.send('/beatspark/clip/pitch-range',
                                       track_index, clip_index,
                                       sorted_pitches[0], sorted_pitches[-1], len(sorted_pitches),
                                       *sorted_pitches)
                        self.log_message('beatspark: pitch-range track=%d clip=%d pitches=%s' %
                                         (track_index, clip_index, sorted_pitches))
                        return
        except Exception as e:
            self.log_message('beatspark: pitch-range error: %s' % str(e))
        # Sentinel: -1 / -1 / 0 means no notes / unknown (no trailing pitch list).
        self._osc.send('/beatspark/clip/pitch-range', track_index, clip_index, -1, -1, 0)

    def _send_record_mode(self):
        """Send Song.record_mode as 1/0. True when arrangement record is armed
        (the round Arrangement Record button glows red)."""
        flag = -1
        try:
            flag = 1 if self.song().record_mode else 0
        except Exception as e:
            self.log_message('beatspark: record-mode error: %s' % str(e))
        self._osc.send('/beatspark/song/record-mode', flag)
        self.log_message('beatspark: record-mode=%d' % flag)

    def _send_track_arm(self, track_index):
        """Send a TRACK's record-arm state as 1/0 (the round arm button on the
        track that record-enables it). This is per-track arm, distinct from the
        global Arrangement Record (record_mode). -1 when the track is out of range
        or can't be armed (return/master/group tracks have no arm)."""
        flag = -1
        try:
            tracks = self.song().tracks
            if 0 <= track_index < len(tracks):
                t = tracks[track_index]
                if getattr(t, 'can_be_armed', False):
                    flag = 1 if t.arm else 0
        except Exception as e:
            self.log_message('beatspark: track-arm error: %s' % str(e))
        self._osc.send('/beatspark/track/arm', int(track_index), flag)
        self.log_message('beatspark: track-arm t%d=%d' % (track_index, flag))

    def _send_track_mute(self, track_index):
        """Send a track's MUTE state as 1/0 (-1 if out of range)."""
        flag = -1
        try:
            tracks = self.song().tracks
            if 0 <= track_index < len(tracks):
                flag = 1 if tracks[track_index].mute else 0
        except Exception as e:
            self.log_message('beatspark: track-mute error: %s' % str(e))
        self._osc.send('/beatspark/track/mute', int(track_index), flag)

    def _send_track_solo(self, track_index):
        """Send a track's SOLO state as 1/0 (-1 if out of range)."""
        flag = -1
        try:
            tracks = self.song().tracks
            if 0 <= track_index < len(tracks):
                flag = 1 if tracks[track_index].solo else 0
        except Exception as e:
            self.log_message('beatspark: track-solo error: %s' % str(e))
        self._osc.send('/beatspark/track/solo', int(track_index), flag)

    def _send_back_to_arranger(self):
        """Send Song.back_to_arranger as 1/0. True when session clips override
        arrangement playback; flips to false when the user clicks the orange
        "Back to Arrangement" button in the arrangement view."""
        flag = -1
        try:
            if hasattr(self.song(), 'back_to_arranger'):
                flag = 1 if self.song().back_to_arranger else 0
        except Exception as e:
            self.log_message('beatspark: back-to-arranger error: %s' % str(e))
        self._osc.send('/beatspark/song/back-to-arranger', flag)
        self.log_message('beatspark: back-to-arranger=%d' % flag)

    def _send_browser_category_state(self, category):
        """Check if a browser category is currently selected."""
        try:
            app = self.application()
            browser = app.browser
            # Map category names to browser filter properties
            category_map = {
                'Drums': 'drums',
                'Instruments': 'instruments',
                'Sounds': 'sounds',
                'Audio Effects': 'audio_effects',
                'MIDI Effects': 'midi_effects',
                'Max for Live': 'max_for_live',
                'Plug-Ins': 'plugins',
                'Clips': 'clips',
                'Samples': 'samples',
                'Packs': 'packs',
                'User Library': 'user_library',
                'Current Project': 'current_project',
            }
            is_selected = 0
            attr_name = category_map.get(category)

            # Primary check: use the browser attribute's is_selected property
            if attr_name and hasattr(browser, attr_name):
                try:
                    filter_item = getattr(browser, attr_name)
                    if filter_item.is_selected:
                        is_selected = 1
                except Exception as e:
                    self.log_message('beatspark: is_selected check failed: %s' % str(e))

            # Fallback ONLY for categories with no LOM filter attribute:
            # check if the browser's selected item name matches. For MAPPED
            # categories this fallback is a false-positive machine - in Live
            # 12.2's browser the sidebar labels are themselves items (a browse
            # cursor merely SITTING on "Instruments" made the app advance a
            # "select the Instruments category" step the user never did), so
            # for those the is_selected attribute above is the only signal.
            if is_selected == 0 and not (attr_name and hasattr(browser, attr_name)):
                try:
                    sel = browser.selected_item
                    if sel and sel.name == category:
                        is_selected = 1
                except Exception:
                    pass

            self.log_message('beatspark: browser category "%s" is_selected=%d' % (category, is_selected))
            self._osc.send('/beatspark/browser/category', category, is_selected)
        except Exception as e:
            self.log_message('beatspark: browser category check error: %s' % str(e))
            self._osc.send('/beatspark/browser/category', category, 0)

    def _send_any_clip_triggered(self):
        """Send whether ANY clip slot across ALL tracks is playing or triggered."""
        any_active = 0
        try:
            tracks = self.song().tracks
            for ti, track in enumerate(tracks):
                try:
                    for ci, slot in enumerate(track.clip_slots):
                        try:
                            if slot.has_clip:
                                if slot.clip.is_playing or slot.clip.is_triggered:
                                    any_active = 1
                                    break
                        except Exception:
                            pass
                    if any_active:
                        break
                except Exception:
                    pass
        except Exception as e:
            self.log_message('beatspark: any-clip-triggered error: %s' % str(e))
        self.log_message('beatspark: any-clip-triggered=%d' % any_active)
        self._osc.send('/beatspark/any-clip-triggered', any_active)

    def _send_clip_playing(self, track_index, clip_index):
        """Send whether a specific clip slot is currently playing."""
        try:
            tracks = self.song().tracks
            if track_index < len(tracks):
                slots = tracks[track_index].clip_slots
                if clip_index < len(slots):
                    slot = slots[clip_index]
                    slot_playing = slot.is_playing if hasattr(slot, 'is_playing') else False
                    clip_playing = False
                    clip_triggered = False
                    if slot.has_clip:
                        clip_playing = slot.clip.is_playing
                        clip_triggered = slot.clip.is_triggered
                    self.log_message('beatspark: clip-playing check track=%d clip=%d slot.is_playing=%s clip.is_playing=%s clip.is_triggered=%s' % (track_index, clip_index, slot_playing, clip_playing, clip_triggered))
                    is_playing = 1 if (clip_playing or clip_triggered) else 0
                    self._osc.send('/beatspark/clip/playing', track_index, clip_index, is_playing)
                    return
        except Exception as e:
            self.log_message('beatspark: clip playing error: %s' % str(e))
        self._osc.send('/beatspark/clip/playing', track_index, clip_index, 0)

    def _send_grid_quantization(self, track_index, clip_index):
        """Send the current grid quantization for a clip's view."""
        try:
            clip = None
            if clip_index == -1:
                # Use the currently open detail clip (arrangement clips)
                clip = self.song().view.detail_clip
            else:
                tracks = self.song().tracks
                if track_index < len(tracks):
                    slots = tracks[track_index].clip_slots
                    if clip_index < len(slots) and slots[clip_index].has_clip:
                        clip = slots[clip_index].clip
            if clip is not None:
                gq = str(clip.view.grid_quantization)
                is_triplet = 1 if clip.view.grid_is_triplet else 0
                self.log_message('beatspark: grid quantization=%s triplet=%d' % (gq, is_triplet))
                self._osc.send('/beatspark/clip/grid-quantization', track_index, clip_index, gq, is_triplet)
                return
        except Exception as e:
            self.log_message('beatspark: grid quantization error: %s' % str(e))
        self._osc.send('/beatspark/clip/grid-quantization', track_index, clip_index, 'unknown', 0)

    def _send_note_count(self, track_index, clip_index, from_pitch=0, pitch_span=128, from_time=-1.0, time_span=-1.0):
        """Send the number of MIDI notes in a clip, optionally filtered by pitch and time range."""
        try:
            clip = None
            tracks = self.song().tracks
            if clip_index == -1:
                # Use the currently open detail clip (arrangement clips)
                clip = self.song().view.detail_clip
            elif track_index < len(tracks):
                slots = tracks[track_index].clip_slots
                if clip_index < len(slots) and slots[clip_index].has_clip:
                    clip = slots[clip_index].clip
            if clip is not None:
                length = clip.length if clip.length > 0 else 4.0
                # Clamp the pitch window to MIDI's 0..127. Live's get_notes_extended
                # / get_notes RAISE when from_pitch + pitch_span > 128, and the
                # except-path below silently returns count=0 - so a drum step that
                # omits pitchSpan (engine defaults it to 128) with a non-zero
                # fromPitch (e.g. G1=43 -> 43+128=171) NEVER passes no matter how
                # many notes the user draws. Clamp so the query stays in range.
                from_pitch = max(0, min(127, from_pitch))
                if pitch_span < 1:
                    pitch_span = 1
                if from_pitch + pitch_span > 128:
                    pitch_span = 128 - from_pitch
                # Use full clip range if no time filter specified
                ft = from_time if from_time >= 0 else 0.0
                ts = time_span if time_span > 0 else length
                count = 0
                max_vel = 127
                total_dur = 0.0
                try:
                    notes = clip.get_notes_extended(from_pitch, pitch_span, ft, ts)
                    count = len(notes)
                    if count > 0:
                        # MidiNote objects (newer) expose .velocity/.duration;
                        # legacy tuples are (pitch, time, duration, velocity, muted).
                        try:
                            max_vel = max(n.velocity for n in notes)
                            total_dur = sum(n.duration for n in notes)
                        except AttributeError:
                            max_vel = max(n[3] for n in notes)
                            total_dur = sum(n[2] for n in notes)
                except Exception:
                    try:
                        notes = clip.get_notes(ft, from_pitch, ts, pitch_span)
                        count = len(notes)
                        if count > 0:
                            max_vel = max(n[3] for n in notes)
                            total_dur = sum(n[2] for n in notes)
                    except Exception:
                        count = 0
                self.log_message('beatspark: note-count=%d maxVel=%d dur=%.2f track=%d clip=%d pitch=%d-%d time=%.1f+%.1f clipLen=%.1f' % (count, max_vel, total_dur, track_index, clip_index, from_pitch, from_pitch + pitch_span, ft, ts, length))
                self._osc.send('/beatspark/clip/note-count', track_index, clip_index, count, max_vel, total_dur)
                return
        except Exception as e:
            self.log_message('beatspark: note count error: %s' % str(e))
        self._osc.send('/beatspark/clip/note-count', track_index, clip_index, 0)

    def _send_all_notes(self, track_index, clip_index):
        """Dump every note (pitch/start/duration) in a clip for the lesson
        builder's draw-and-capture flow. Chunked JSON (device-catalog pattern).
        Wire: /beatspark/clip/all-notes-chunk <idx> <total> <fragment>
              /beatspark/clip/all-notes-done  <total>   (payload carries t/c)
        """
        notes_out = []
        # clipStart/isArr identify WHICH clip this is when clip_index == -1 (the
        # detail clip): two arrangement clips on one track share clipIndex -1, so
        # the recorder/generator key on the arrangement start_time (beats) to keep
        # them distinct (kicks-clip @0 vs hats-clip @16) instead of conflating them.
        diag = {'hadClip': False, 'clipName': '', 'clipLen': 0.0, 'isMidi': False,
                'clipStart': None, 'isArr': False}
        try:
            clip = None
            tracks = self.song().tracks
            if clip_index == -1:
                clip = self.song().view.detail_clip
            elif track_index < len(tracks):
                slots = tracks[track_index].clip_slots
                if clip_index < len(slots) and slots[clip_index].has_clip:
                    clip = slots[clip_index].clip
            if clip is not None:
                diag['hadClip'] = True
                try: diag['clipName'] = str(getattr(clip, 'name', ''))
                except Exception: pass
                try: diag['clipLen'] = float(getattr(clip, 'length', 0.0))
                except Exception: pass
                diag['isMidi'] = bool(getattr(clip, 'is_midi_clip', True))
                try: diag['isArr'] = bool(getattr(clip, 'is_arrangement_clip', False))
                except Exception: pass
                # Arrangement position (beats) — the clip's identity on the timeline.
                if diag['isArr']:
                    try: diag['clipStart'] = float(getattr(clip, 'start_time', 0.0))
                    except Exception: pass
                if diag['isMidi']:
                    length = clip.length if clip.length > 0 else 4.0
                    try:
                        raw = clip.get_notes_extended(0, 128, 0.0, length)
                    except Exception:
                        raw = clip.get_notes(0.0, 0, length, 128)
                    for n in raw:
                        # Newer Live (get_notes_extended): MidiNote objects with
                        # .pitch/.start_time/.duration. Older Live (get_notes):
                        # (pitch, time, duration, velocity, muted) tuples. Index
                        # access on a MidiNote raises — handle both.
                        try:
                            try:
                                p, t, d = n.pitch, n.start_time, n.duration
                            except AttributeError:
                                p, t, d = n[0], n[1], n[2]
                            notes_out.append({'p': int(p), 't': float(t), 'd': float(d)})
                        except Exception:
                            pass
        except Exception as e:
            self.log_message('beatspark: all-notes error: %s' % str(e))
        import json
        payload = {'trackIndex': track_index, 'clipIndex': clip_index, 'notes': notes_out,
                   'hadClip': diag['hadClip'], 'clipName': diag['clipName'], 'clipLen': diag['clipLen'], 'isMidi': diag['isMidi'],
                   'clipStart': diag['clipStart'], 'isArr': diag['isArr']}
        try:
            blob = json.dumps(payload)
        except Exception:
            blob = '{"trackIndex":%d,"clipIndex":%d,"notes":[],"error":"json"}' % (track_index, clip_index)
        total = self._chunk_and_send_blob(blob, '/beatspark/clip/all-notes-chunk', '/beatspark/clip/all-notes-done')
        self.log_message('beatspark: all-notes track=%d clip=%d count=%d hadClip=%s name="%s" len=%.2f midi=%s chunks=%d' % (
            track_index, clip_index, len(notes_out), diag['hadClip'], diag['clipName'], diag['clipLen'], diag['isMidi'], total))

    def _send_arrangement_clips(self, track_index):
        """Dump every clip on a track's ARRANGEMENT timeline (position + sample) so
        a lesson can verify "drag this audio clip onto the track at bar N". Reads
        the LOM track.arrangement_clips list directly — no detail-clip dependency.
        Wire: /beatspark/arrangement-clips-chunk <idx> <total> <fragment>
              /beatspark/arrangement-clips-done  <total>   (payload carries trackIndex)
        """
        clips_out = []
        try:
            tracks = self.song().tracks
            if 0 <= track_index < len(tracks):
                track = tracks[track_index]
                arr_clips = list(getattr(track, 'arrangement_clips', []) or [])
                for clip in arr_clips:
                    try:
                        is_audio = bool(getattr(clip, 'is_audio_clip', False))
                        entry = {
                            'name': str(getattr(clip, 'name', '')),
                            'start': float(getattr(clip, 'start_time', 0.0)),
                            'end': float(getattr(clip, 'end_time', 0.0)),
                            'length': float(getattr(clip, 'length', 0.0)),
                            'isAudio': is_audio,
                        }
                        # file_path is only meaningful on audio clips; store just the
                        # basename so a lesson can match the sample name ("Kick 606").
                        # Also capture the audio-clip property tweaks a lesson might
                        # teach (gain / transpose / warp) so they can be verified.
                        if is_audio:
                            fp = getattr(clip, 'file_path', '') or ''
                            entry['file'] = fp.split('/')[-1] if fp else ''
                            try:
                                entry['gainDb'] = str(getattr(clip, 'gain_display_string', '') or '')
                            except Exception:
                                pass
                            try:
                                entry['transpose'] = int(getattr(clip, 'pitch_coarse', 0) or 0)
                            except Exception:
                                pass
                            try:
                                entry['warpMode'] = int(getattr(clip, 'warp_mode', -1))
                                entry['warping'] = bool(getattr(clip, 'warping', False))
                            except Exception:
                                pass
                        clips_out.append(entry)
                    except Exception:
                        pass
        except Exception as e:
            self.log_message('beatspark: arrangement-clips error: %s' % str(e))
        import json
        payload = {'trackIndex': track_index, 'clips': clips_out}
        try:
            blob = json.dumps(payload)
        except Exception:
            blob = '{"trackIndex":%d,"clips":[],"error":"json"}' % track_index
        total = self._chunk_and_send_blob(blob, '/beatspark/arrangement-clips-chunk', '/beatspark/arrangement-clips-done')
        self.log_message('beatspark: arrangement-clips track=%d count=%d chunks=%d' % (
            track_index, len(clips_out), total))

    def _send_notes_at_positions(self, track_index, clip_index, tolerance, specs):
        """For each (pitch, time) spec, count notes matching within ??tolerance beats.
        Reply: /beatspark/clip/notes-at-positions <track> <clip> <count1> <count2> ...
        Used to verify position-accurate MIDI note placement when a single
        pitch+time window is too coarse (e.g. duplicated phrases).
        clip_index == -1 means 'the currently-open detail clip' - used in
        arrangement view where clips aren't addressable by slot index."""
        counts = [0] * len(specs)
        try:
            clip = None
            if clip_index == -1:
                try:
                    clip = self.song().view.detail_clip
                except Exception:
                    clip = None
            else:
                tracks = self.song().tracks
                if track_index < len(tracks):
                    slots = tracks[track_index].clip_slots
                    if clip_index < len(slots) and slots[clip_index].has_clip:
                        clip = slots[clip_index].clip
            if clip is not None:
                length = clip.length if clip.length > 0 else 4.0
                notes_iter = []
                try:
                    notes_iter = clip.get_notes_extended(0, 128, 0.0, length)
                except Exception:
                    try:
                        notes_iter = clip.get_notes(0.0, 0, length, 128)
                    except Exception:
                        notes_iter = []
                for n in notes_iter:
                    # Newer Live: MidiNote object with .pitch and .start_time.
                    # Older Live: tuple (pitch, time, duration, velocity, muted).
                    try:
                        np_ = n.pitch
                        nt_ = n.start_time
                    except AttributeError:
                        np_, nt_ = int(n[0]), float(n[1])
                    for i, (tp, tt) in enumerate(specs):
                        if np_ == tp and abs(nt_ - tt) <= tolerance:
                            counts[i] += 1
        except Exception as e:
            self.log_message('beatspark: notes-at-positions error: %s' % str(e))
        self._osc.send('/beatspark/clip/notes-at-positions', track_index, clip_index, *counts)

    def _send_selected_note_count(self, track_index, clip_index):
        """Send the count of currently-selected notes in a clip. Used to verify
        the user deselected all notes (e.g. by clicking empty space)."""
        count = 0
        try:
            # clip_index == -1 → the currently-open detail clip (arrangement view).
            clip = None
            if clip_index == -1:
                clip = self.song().view.detail_clip
            else:
                tracks = self.song().tracks
                if 0 <= track_index < len(tracks):
                    slots = tracks[track_index].clip_slots
                    if 0 <= clip_index < len(slots) and slots[clip_index].has_clip:
                        clip = slots[clip_index].clip
            if clip is not None:
                try:
                    notes = clip.get_selected_notes_extended()
                    count = len(notes)
                except Exception:
                    try:
                        notes = clip.get_selected_notes()
                        count = len(notes)
                    except Exception:
                        count = 0
        except Exception as e:
            self.log_message('beatspark: selected-note-count error: %s' % str(e))
        self._osc.send('/beatspark/clip/selected-note-count', track_index, clip_index, count)

    def _send_note_duration_total(self, track_index, clip_index):
        """Send the total duration of all MIDI notes in a clip."""
        try:
            # clip_index == -1 → the currently-open detail clip (arrangement view).
            clip = None
            if clip_index == -1:
                clip = self.song().view.detail_clip
            else:
                tracks = self.song().tracks
                if 0 <= track_index < len(tracks):
                    slots = tracks[track_index].clip_slots
                    if 0 <= clip_index < len(slots) and slots[clip_index].has_clip:
                        clip = slots[clip_index].clip
            if clip is not None:
                length = clip.length if clip.length > 0 else 4.0
                total = 0.0
                try:
                    notes = clip.get_notes_extended(0, 128, 0.0, length)
                    for note in notes:
                        total += note.duration
                except Exception:
                    try:
                        notes = clip.get_notes(0.0, 0, length, 128)
                        for note in notes:
                            total += note[2]  # (pitch, time, duration, velocity, muted)
                    except Exception:
                        total = 0.0
                self.log_message('beatspark: note-duration-total=%.4f track=%d clip=%d' % (total, track_index, clip_index))
                self._osc.send('/beatspark/clip/note-duration-total', track_index, clip_index, total)
                return
        except Exception as e:
            self.log_message('beatspark: note duration total error: %s' % str(e))
        self._osc.send('/beatspark/clip/note-duration-total', track_index, clip_index, 0.0)

    def _send_aux_tracks(self):
        """Send return + master track NAMES so the editor's Track dropdown can offer
        them for wait_device_param (they aren't in the regular track/name burst).
        Wire: /beatspark/aux-tracks <returnCount> <ret0> <ret1> ... <masterName>."""
        song = self.song()
        try:
            rts = list(song.return_tracks)
        except Exception:
            rts = []
        out = [len(rts)]
        for rt in rts:
            try:
                out.append(str(rt.name))
            except Exception:
                out.append('Return')
        try:
            out.append(str(song.master_track.name))
        except Exception:
            out.append('Main')
        self._osc.send('/beatspark/aux-tracks', *out)

    def _send_device_info(self, track_index):
        """Send device names for a given track."""
        song = self.song()
        tracks = song.tracks
        if track_index < 0 or track_index >= len(tracks):
            return
        track = tracks[track_index]
        devices = track.devices
        self._osc.send('/beatspark/device/count', track_index, len(devices))
        for i, device in enumerate(devices):
            self._osc.send('/beatspark/device/name', track_index, i, device.name)

    def _send_clip_info(self, track_index):
        """Send the clip-slot list for a track so the editor can offer a clip
        dropdown: per slot we send (has_clip flag, name) — has_clip distinguishes
        an empty slot ('' name, flag 0) from a freshly-drawn unnamed clip ('' name,
        flag 1). Capped at 16 slots. Also fires the per-occupied clip/name
        messages for any other consumers."""
        song = self.song()
        tracks = song.tracks
        if track_index < 0 or track_index >= len(tracks):
            self._osc.send('/beatspark/track/clips', track_index, 0)
            return
        clip_slots = tracks[track_index].clip_slots
        cap = min(len(clip_slots), 16)
        payload = [track_index, cap]
        for i in range(cap):
            slot = clip_slots[i]
            if slot.has_clip:
                payload.append(1)
                payload.append(slot.clip.name)
                self._osc.send('/beatspark/clip/name', track_index, i, slot.clip.name)
            else:
                payload.append(0)
                payload.append('')
        self._osc.send('/beatspark/track/clips', *payload)

    def _find_drum_rack(self, track_or_device, depth=0, max_depth=10):
        """Recursively search for a Drum Rack device."""
        if depth > max_depth:
            self.log_message('beatspark: _find_drum_rack max depth (%d) exceeded' % max_depth)
            return None
        devices = track_or_device.devices if hasattr(track_or_device, 'devices') else []
        for device in devices:
            try:
                if device.has_drum_pads:
                    self.log_message('beatspark: found drum rack "%s" at depth %d' % (device.name, depth))
                    return device
            except Exception:
                pass
            # Search inside racks (Instrument Rack, Audio Effect Rack, etc.)
            try:
                if hasattr(device, 'chains'):
                    self.log_message('beatspark: searching %d chains in "%s" (class=%s) at depth %d' % (len(device.chains), device.name, device.class_name, depth))
                    for chain in device.chains:
                        result = self._find_drum_rack(chain, depth + 1, max_depth)
                        if result:
                            return result
            except Exception as e:
                self.log_message('beatspark: chain search error in "%s": %s' % (device.name, str(e)))
        return None

    def _send_drum_pad_samples(self, track_index):
        """Send each ASSIGNED drum-pad's loaded sample (note + pad name + sample file
        basename) so the recorder/generator can capture "dragged Kick 606 onto a pad".
        Walks the drum rack's pad chains for a Simpler/Sampler with a sample. Chunked
        JSON (mirrors arrangement-clips) so it can't blow the OSC packet size."""
        pads_out = []
        try:
            tracks = self.song().tracks
            if 0 <= track_index < len(tracks):
                rack = self._find_drum_rack(tracks[track_index])
                if rack is not None:
                    for pad in rack.drum_pads:
                        try:
                            if not pad.chains:
                                continue
                            sample = ''
                            for chain in pad.chains:
                                for dev in chain.devices:
                                    try:
                                        smp = getattr(dev, 'sample', None)
                                        fp = getattr(smp, 'file_path', '') if smp is not None else ''
                                        if fp:
                                            sample = fp.split('/')[-1]
                                            break
                                    except Exception:
                                        pass
                                if sample:
                                    break
                            pads_out.append({'note': int(pad.note), 'name': str(pad.name), 'sample': sample})
                        except Exception:
                            pass
        except Exception as e:
            self.log_message('beatspark: drum-pad-samples error: %s' % str(e))
        import json
        try:
            blob = json.dumps({'trackIndex': track_index, 'pads': pads_out})
        except Exception:
            blob = '{"trackIndex":%d,"pads":[]}' % track_index
        self._chunk_and_send_blob(blob, '/beatspark/drum-pad-samples-chunk', '/beatspark/drum-pad-samples-done')

    def _send_drum_pads(self, track_index):
        """Send drum pad layout (note + name, sorted ascending) for the drum rack on a track."""
        try:
            tracks = self.song().tracks
            if track_index < 0 or track_index >= len(tracks):
                return
            track = tracks[track_index]
            self.log_message('beatspark: drum-pads searching track %d "%s", %d devices' % (track_index, track.name, len(track.devices)))
            for i, dev in enumerate(track.devices):
                has_dp = False
                try:
                    has_dp = dev.has_drum_pads
                except Exception:
                    pass
                self.log_message('beatspark: drum-pads device %d: "%s" class=%s has_drum_pads=%s can_have_chains=%s' % (
                    i, dev.name, dev.class_name, has_dp, hasattr(dev, 'chains')))
            drum_rack = self._find_drum_rack(track)
            if drum_rack is None:
                self._osc.send('/beatspark/drum-pads', track_index, 0)
                return
            # Collect only assigned pads (those with at least one chain)
            pads = []
            for pad in drum_rack.drum_pads:
                if pad.chains:
                    pads.append((pad.note, pad.name))
            pads.sort(key=lambda x: x[0])  # ascending by MIDI note = bottom-to-top in editor
            # Format: trackIndex, count, note0, name0, note1, name1, ...
            osc_args = [track_index, len(pads)]
            for note, name in pads:
                osc_args.extend([note, name])
            self._osc.send('/beatspark/drum-pads', *osc_args)
            self.log_message('beatspark: drum-pads track=%d count=%d pads=%s' % (
                track_index, len(pads), str([(n, nm) for n, nm in pads])))
        except Exception as e:
            self.log_message('beatspark: drum-pads error: %s' % str(e))
            self._osc.send('/beatspark/drum-pads', track_index, 0)

    def _send_clip_loop_bounds(self, track_index, clip_index):
        """Send clip loop_start and loop_end in beats (quarter notes from clip start)."""
        try:
            clip = None
            if clip_index == -1:
                # Use the currently open detail clip (arrangement clips)
                clip = self.song().view.detail_clip
            else:
                tracks = self.song().tracks
                if track_index < 0 or track_index >= len(tracks):
                    return
                slots = tracks[track_index].clip_slots
                if clip_index >= 0 and clip_index < len(slots) and slots[clip_index].has_clip:
                    clip = slots[clip_index].clip
            if clip is None:
                self._osc.send('/beatspark/clip/loop-bounds', track_index, clip_index, 0.0, 0.0, 0.0)
                return
            loop_start = clip.loop_start
            loop_end = clip.loop_end
            clip_length = clip.length
            self._osc.send('/beatspark/clip/loop-bounds', track_index, clip_index, loop_start, loop_end, clip.length)
            self.log_message('beatspark: loop-bounds track=%d clip=%d start=%.3f end=%.3f' % (
                track_index, clip_index, loop_start, loop_end, clip.length))
        except Exception as e:
            self.log_message('beatspark: loop-bounds error: %s' % str(e))
            self._osc.send('/beatspark/clip/loop-bounds', track_index, clip_index, 0.0, 0.0, 0.0)

    def _send_clip_start_time(self, track_index, clip_index):
        """Send a clip's arrangement start_time (in beats from song 0).
        For session clips this is usually 0; it's meaningful for arrangement clips.
        Returns -1.0 when the clip can't be resolved."""
        try:
            clip = None
            if clip_index == -1:
                clip = self.song().view.detail_clip
            else:
                tracks = self.song().tracks
                if 0 <= track_index < len(tracks):
                    slots = tracks[track_index].clip_slots
                    if 0 <= clip_index < len(slots) and slots[clip_index].has_clip:
                        clip = slots[clip_index].clip
            if clip is None:
                self._osc.send('/beatspark/clip/start-time', track_index, clip_index, -1.0)
                return
            start_time = float(clip.start_time) if hasattr(clip, 'start_time') else -1.0
            self.log_message('beatspark: clip-start-time track=%d clip=%d start=%.3f' % (
                track_index, clip_index, start_time))
            self._osc.send('/beatspark/clip/start-time', track_index, clip_index, start_time)
        except Exception as e:
            self.log_message('beatspark: clip-start-time error: %s' % str(e))
            self._osc.send('/beatspark/clip/start-time', track_index, clip_index, -1.0)

    # NOTE: the canonical _send_arrangement_clips is the RICH, chunked version
    # defined ABOVE (each clip carries isAudio / name / file / length / gain /
    # transpose / warp). A second, positions-only definition used to live here and
    # — because Python keeps the LAST definition of a method — silently SHADOWED
    # the rich one, so every `get arrangement-clips` returned start/end only. That
    # made wait_arrangement_sample's audio + name match fail (isAudio=undefined,
    # name=""). The duplicate is removed; wait_arrangement_clip still gets its
    # positions from the rich clips' `start`.

    # Hardcoded scale-name - semitone-offset mapping. Used when Live exposes
    # scale_name but not a parseable scale_intervals (older versions, edge cases).
    _SCALE_NAME_INTERVALS = {
        'Major':            [0, 2, 4, 5, 7, 9, 11],
        'Minor':            [0, 2, 3, 5, 7, 8, 10],
        'Dorian':           [0, 2, 3, 5, 7, 9, 10],
        'Mixolydian':       [0, 2, 4, 5, 7, 9, 10],
        'Lydian':           [0, 2, 4, 6, 7, 9, 11],
        'Phrygian':         [0, 1, 3, 5, 7, 8, 10],
        'Locrian':          [0, 1, 3, 5, 6, 8, 10],
        'Harmonic Minor':   [0, 2, 3, 5, 7, 8, 11],
        'Melodic Minor':    [0, 2, 3, 5, 7, 9, 11],
        'Whole Tone':       [0, 2, 4, 6, 8, 10],
        'Arabic':           [0, 1, 3, 5, 6, 8, 10],
        'Akebono':          [0, 2, 5, 7, 9],
        'Kumoi':            [0, 2, 5, 7, 9],
        'Pelog':            [0, 1, 3, 4, 7, 8],
        'Hirajoshi':        [0, 2, 3, 5, 7, 8, 10],
        'Iwato':            [0, 1, 5, 6, 10],
        'In-Sen':           [0, 1, 5, 7, 10],
        'Yo':               [0, 2, 5, 7, 9],
        'Gong':             [0, 2, 3, 5, 7, 8, 10],
        'Hungarian Minor':  [0, 2, 3, 6, 7, 8, 11],
        'Hungarian Major':  [0, 2, 4, 6, 7, 9, 11],
        'Neapolitan Minor': [0, 1, 3, 5, 7, 8, 11],
        'Neapolitan Major': [0, 1, 3, 5, 7, 9, 11],
        'Enigmatic':        [0, 1, 3, 6, 7, 9, 11],
        'Augmented':        [0, 3, 4, 7, 8, 11],
        'Prometheus':       [0, 2, 4, 6, 9, 10],
        'Pentatonic':       [0, 2, 4, 7, 9],
        'Minor Pentatonic': [0, 3, 5, 7, 10],
        'Major Pentatonic': [0, 2, 4, 7, 9],
        'Major Blues':      [0, 2, 3, 4, 7, 9],
        'Minor Blues':      [0, 3, 5, 6, 7, 10],
        'Blues':            [0, 3, 5, 6, 7, 10],
        'Chromatic':        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    }

    def _normalize_intervals(self, raw):
        """Convert Live's scale_intervals to a list of semitone offsets from root.

        Live can return either:
          - a 12-element bool/int mask (True/False or 1/0 per semitone), or
          - a list of offsets ([0, 2, 4, 5, 7, 9, 11]).
        Detect the mask form and convert; otherwise pass through.
        """
        if not raw:
            return []
        try:
            seq = list(raw)
        except Exception:
            return []
        if not seq:
            return []
        # Mask form: 12 entries that are all 0/1/True/False
        if len(seq) == 12 and all(v in (0, 1, True, False) for v in seq):
            return [i for i, v in enumerate(seq) if v]
        return [int(v) for v in seq]

    def _send_clip_scale(self, track_index, clip_index):
        """Send the focused clip's scale info.

        Per the LOM, scale lives on Song (not Clip): Song.root_note,
        Song.scale_name, Song.scale_intervals. In Live 12 the toolbar Scale
        section mirrors the focused clip, so reading Song.* gives the
        currently-focused clip's scale. beatspark only queries scale for the
        clip the user is editing (= the focused clip), so this is correct.
        """
        self.log_message('beatspark: _send_clip_scale ENTRY track=' + str(track_index) + ' clip=' + str(clip_index))
        root_note = -1
        scale_name = 'unknown'
        intervals = []
        try:
            song = self.song()
            try:
                root_note = int(song.root_note)
            except (AttributeError, TypeError, ValueError) as e:
                self.log_message('beatspark: song.root_note miss: ' + type(e).__name__)
            try:
                scale_name = str(song.scale_name)
            except (AttributeError, TypeError) as e:
                self.log_message('beatspark: song.scale_name miss: ' + type(e).__name__)
            try:
                intervals = self._normalize_intervals(song.scale_intervals)
            except (AttributeError, TypeError) as e:
                self.log_message('beatspark: song.scale_intervals miss: ' + type(e).__name__)
            # Last-resort: derive intervals from scale name via hardcoded table.
            if not intervals and scale_name in self._SCALE_NAME_INTERVALS:
                intervals = list(self._SCALE_NAME_INTERVALS[scale_name])
        except Exception as e:
            self.log_message('beatspark: clip-scale song read error: ' + str(e))
        osc_args = [track_index, clip_index, root_note, scale_name] + intervals
        self._osc.send('/beatspark/clip/scale', *osc_args)
        self.log_message('beatspark: clip-scale track=' + str(track_index) + ' clip=' + str(clip_index) +
                         ' root=' + str(root_note) + ' scale=' + str(scale_name) +
                         ' intervals=' + str(intervals))

    def _send_track_kinds(self):
        """Send counts of audio / midi / return tracks so the app can verify a
        create_*_track (a kind's count went up) or delete_track (total went down)
        step. song.tracks holds regular tracks (classified by has_midi_input);
        return tracks live in song.return_tracks."""
        audio = 0
        midi = 0
        ret = 0
        grp = 0
        # Per-track kind code IN ORDER (song.tracks index): 0=audio 1=midi 2=group.
        # Lets the app verify a create_*_track step landed at a SPECIFIC index even
        # when the project already has tracks at/after that index (the counts alone
        # can't tell which index a new track occupies). Appended after the counts so
        # an older app that only reads the 4 counts is unaffected.
        codes = []
        # Per-track PARENT-GROUP index IN ORDER (song.tracks index): the index of
        # the group track this track is a DIRECT member of, or -1 for top-level
        # tracks (and the group tracks themselves, unless nested). Appended AFTER
        # the kind codes; the app splits the trailing args in half using the
        # track count (audio+midi+group). Lets wait_group_track verify the group
        # actually CONTAINS the expected number of tracks (a bare count-increase
        # passed on any group, regardless of what was grouped).
        parents = []
        try:
            song = self.song()
            tracks = list(song.tracks)
            for t in tracks:
                try:
                    # A group track (is_foldable) is neither pure audio nor midi —
                    # count it as `group` so "group your drums" is verifiable AND so
                    # creating a group doesn't falsely trip wait_create_audio_track.
                    if getattr(t, 'is_foldable', False):
                        grp += 1
                        codes.append(2)
                    elif t.has_midi_input:
                        midi += 1
                        codes.append(1)
                    else:
                        audio += 1
                        codes.append(0)
                except Exception:
                    audio += 1
                    codes.append(0)
                p = -1
                try:
                    gt = getattr(t, 'group_track', None)
                    if gt is not None:
                        for gi, t2 in enumerate(tracks):
                            if t2 == gt:
                                p = gi
                                break
                except Exception:
                    p = -1
                parents.append(p)
            ret = len(song.return_tracks)
        except Exception as e:
            self.log_message('beatspark: track-kinds error: ' + str(e))
        self._osc.send('/beatspark/track-kinds', audio, midi, ret, grp, *(codes + parents))

    def _send_simpler_sample(self, track_index):
        """Send the file_path + playback_mode of the first Simpler/Sampler
        on a track. Used by wait_sample_loaded + wait_simpler_playback_mode.

        - file_path: "" when no sample is loaded
        - playback_mode: 0=Classic, 1=One Shot, 2=Slicing, or -1 when missing

        Other Simpler attributes (slicing_style, slicing_beat_division, etc.)
        are NOT broadcast here — they're reached via the generic
        wait_device_param attribute path. Adding bespoke OSC fields per
        attribute doesn't scale.
        """
        file_path = ''
        playback_mode = -1
        try:
            tracks = self.song().tracks
            if 0 <= track_index < len(tracks):
                track = tracks[track_index]
                for device in track.devices:
                    # LOM class_name is 'OriginalSimpler' for Simpler and
                    # 'MultiSampler' for Sampler - the human-facing names
                    # ('Simpler'/'Sampler') only appear in class_display_name.
                    # Match both so this works regardless of Live version.
                    cn = getattr(device, 'class_name', '')
                    cdn = getattr(device, 'class_display_name', '')
                    if (cn not in ('OriginalSimpler', 'MultiSampler', 'Simpler', 'Sampler')
                            and cdn not in ('Simpler', 'Sampler')):
                        continue
                    try:
                        sample = device.sample
                    except AttributeError:
                        continue
                    try:
                        playback_mode = int(device.playback_mode)
                    except (AttributeError, TypeError, ValueError):
                        pass
                    if sample is not None:
                        try:
                            fp = sample.file_path
                            if fp:
                                file_path = str(fp)
                        except AttributeError:
                            pass
                    break
        except Exception as e:
            self.log_message('beatspark: simpler-sample error: ' + str(e))
        self._osc.send('/beatspark/simpler/sample', track_index, file_path, playback_mode)
        self.log_message('beatspark: simpler-sample track=' + str(track_index) +
                         ' playback_mode=' + str(playback_mode) +
                         ' file_path="' + file_path + '"')

    # --- Cleanup ---

    def disconnect(self):
        """Called when the control surface is removed."""
        try:
            song = self.song()
            if song.tempo_has_listener(self._on_tempo_changed):
                song.remove_tempo_listener(self._on_tempo_changed)
            if song.is_playing_has_listener(self._on_playing_changed):
                song.remove_is_playing_listener(self._on_playing_changed)
            if song.view.selected_track_has_listener(self._on_selected_track_changed):
                song.view.remove_selected_track_listener(self._on_selected_track_changed)
            if song.view.detail_clip_has_listener(self._on_detail_clip_changed):
                song.view.remove_detail_clip_listener(self._on_detail_clip_changed)
            try:
                app_view = self.application().view
                if app_view.focused_document_view_has_listener(self._on_focused_document_view_changed):
                    app_view.remove_focused_document_view_listener(self._on_focused_document_view_changed)
            except Exception:
                pass
            try:
                for has_l, rm_l in (
                    (song.loop_has_listener, song.remove_loop_listener),
                    (song.loop_start_has_listener, song.remove_loop_start_listener),
                    (song.loop_length_has_listener, song.remove_loop_length_listener),
                ):
                    if has_l(self._on_arrangement_loop_changed):
                        rm_l(self._on_arrangement_loop_changed)
            except Exception:
                pass
            try:
                if song.record_mode_has_listener(self._on_record_mode_changed):
                    song.remove_record_mode_listener(self._on_record_mode_changed)
            except Exception:
                pass
        except Exception:
            pass
        self._osc.shutdown()
        self.log_message('beatspark: disconnected')
        super(beatspark, self).disconnect()

    def update_display(self):
        """Called periodically by Ableton (~10Hz). Process incoming OSC and poll state."""
        super(beatspark, self).update_display()
        self._osc.process()

        # Poll track count changes
        song = self.song()
        current_count = len(song.tracks)
        if current_count != self._last_track_count:
            self._last_track_count = current_count
            self._osc.send('/beatspark/track/count', current_count)
            self._send_track_info()
            # Push the kind breakdown too (incl. group count) so create/delete/group
            # are captured during recording, not just on a wait-step request.
            self._send_track_kinds()

        # Poll track NAME changes — a rename doesn't change the count, so it isn't
        # caught above and has no cheap per-track listener we manage. Reading the names
        # each ~10Hz tick is cheap; send only the ones that actually changed. Seeded in
        # _setup_listeners so we don't re-send every name on the first tick.
        try:
            names = [str(t.name) for t in song.tracks]
            prev = getattr(self, '_last_track_names', None)
            if names != prev:
                for i, nm in enumerate(names):
                    if prev is None or i >= len(prev) or prev[i] != nm:
                        self._osc.send('/beatspark/track/name', i, nm)
                self._last_track_names = names
        except Exception:
            pass

        # Poll per-track DEVICE changes — adding/removing/replacing a top-level
        # device (e.g. dropping a Drum Rack onto a track) doesn't change the track
        # count and has no listener we manage, so without this it's only captured
        # when the user happens to select the track or open a clip. Reading device
        # names each ~10Hz tick is cheap; push only the tracks that actually
        # changed via _send_device_info (count + per-device names), which the lesson
        # recorder assembles into a deduped 'track-devices' event. Seeded in
        # _setup_listeners so we don't re-send every track's chain on the first tick.
        try:
            sigs = [tuple(str(d.name) for d in t.devices) for t in song.tracks]
            prev = getattr(self, '_last_device_sigs', None)
            if sigs != prev:
                for i, sig in enumerate(sigs):
                    if prev is None or i >= len(prev) or prev[i] != sig:
                        self._send_device_info(i)
                self._last_device_sigs = sigs
        except Exception:
            pass

        # Poll watched clip slots for creation, remove watchers after they fire
        fired = []
        for key in self._clip_watchers:
            ti, ci = key
            tracks = song.tracks
            if ti < len(tracks):
                slots = tracks[ti].clip_slots
                if ci < len(slots):
                    has_clip = slots[ci].has_clip
                    prev = self._last_clip_state.get(key, False)
                    if has_clip and not prev:
                        clip_name = slots[ci].clip.name if has_clip else ''
                        self._osc.send('/beatspark/clip/created', ti, ci, clip_name)
                        fired.append(key)
                    self._last_clip_state[key] = has_clip
        for key in fired:
            self._clip_watchers.remove(key)
            self._last_clip_state.pop(key, None)
        if fired:
            self.log_message('beatspark: removed %d satisfied clip watcher(s)' % len(fired))

        # Passive send-automation sampling. ARRANGEMENT automation isn't readable
        # via the LOM (no envelope value_at_time), so to verify "send X = N dB at
        # bar B" we watch the live SEND value while the user plays and sample it as
        # current_song_time crosses the target beat. Non-intrusive — we never move
        # the playhead. Re-samples on each pass (the engine advances on a value
        # match); a backward jump (loop/seek) resets the baseline so it can't
        # register a false forward crossing.
        w = self._send_automation_watch
        if w is not None and song.is_playing:
            try:
                now = float(song.current_song_time)
                crossed = (w['last'] <= w['at'] <= now)
                near = abs(now - w['at']) <= w['eps']
                if crossed or near:
                    s = song.tracks[w['ti']].mixer_device.sends[w['send']]
                    val = float(s.value)
                    disp = str(s.str_for_value(s.value)) if hasattr(s, 'str_for_value') else str(val)
                    self._osc.send('/beatspark/send-automation/sample', w['ti'], w['send'], w['at'], val, disp)
                w['last'] = now
            except Exception:
                pass
