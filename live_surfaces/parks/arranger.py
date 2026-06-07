from _Framework.ControlSurface import ControlSurface
from _Framework.ControlSurface import logger

from _Framework.ControlSurfaceComponent import ControlSurfaceComponent


class Arranger(ControlSurfaceComponent):
    def __init__(self, ins):
        ControlSurfaceComponent.__init__(self)
        self._control_surface = ins

    def copy_clip_to_arrangement_and_extend(self, clip, track, start: int, beats_to_build: int):

        # self._control_surface.log_message(f"arrange   clip_slot.clip len = {clip.length}")

        clip_loop_start = clip.loop_start
        original_clip_loop_end = clip.loop_end

        # self._control_surface.log_message(f"quick_arrange clip_loop_start = {clip_loop_start}")
        # self._control_surface.log_message(f"quick_arrange original_clip_loop_end = {original_clip_loop_end}")

        ## can't change length of clip in arrangement view, we have to
        ## extend it first, copy it, then shorten it to the original size

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

    def copy_all_to_arrangement(self):
        for track in self.song().tracks:
            self._control_surface.log_message(f"arrange   track = {track.name}")
            clip_slot = track.clip_slots[0]

            if clip_slot.clip is not None:
                beats_per_new_clip = 8 * 4

                self.copy_clip_to_arrangement_and_extend(clip_slot.clip, track, 0, beats_per_new_clip)

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
