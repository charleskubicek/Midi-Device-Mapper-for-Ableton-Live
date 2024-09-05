import traceback
from dataclasses import dataclass

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ControlSurface import ControlSurface
import Live
import time


class Functions(ControlSurface):
    def __init__(self, c_instance=None, publish_self=True, *a, **k):
        super().__init__(c_instance=c_instance)
        # self._manager = c_instance
        self.track_nav = TrackNav(self, self.song())

    # def log_message(self, message):
    #     self._manager.log_message(message)

    def encoder_track_nav(self, value, previous_value):
        self.track_nav.update_value(value, previous_value)

    def selected_device(self):
        return self.song().view.selected_track.view.selected_device


class TrackNav(ControlSurfaceComponent):

    def __init__(self, ins, song):
        ControlSurfaceComponent.__init__(self)
        self._manager = ins
        self._song = song

    def log_message(self, message):
        self._manager.log_message(message)

    def update_value(self, value, previous_value):
        self.log_message(f"New value is {value}, previous value was {previous_value}")

        if value % 2 == 0:
            if value > previous_value:
                self.track_nav_inc()
            elif value < previous_value:
                self.track_nav_dec()

    def track_nav_inc(self):
        all_tracks = len(self._song.tracks)
        selected_track = self._song.view.selected_track  # Get the currently selected track

        self.log_message(f"Selected track name is {selected_track.name}")

        if selected_track.name == "Master":
            self.log_message("Can't increment from Master")

        next_index = list(self._song.tracks).index(selected_track) + 1  # Get the index of the selected track

        if next_index < all_tracks:
            self._song.view.selected_track = self._song.tracks[next_index]

    def track_nav_dec(self):
        selected_track = self._song.view.selected_track  # Get the currently selected track

        if selected_track.name == "Master":
            next_index = len(list(self._song.tracks)) - 1
        else:
            next_index = list(self._song.tracks).index(selected_track) - 1  # Get the index of the selected track

        if next_index >= 0:
            self._song.view.selected_track = self._song.tracks[next_index]

