


class Helpers:
    def __init__(self, manager):
        self._manager = manager

    def log_message(self, message):
        self._manager.log_message(message)

    def device_parameter_action(self, device, parameter_no, value, fn_name, toggle=False):
        if device is None:
            return

        if len(device.parameters) < parameter_no:
            self.log_message(f"{parameter_no} too large, max is {len(device.parameters)}")
            return

        min = device.parameters[parameter_no].min
        max = device.parameters[parameter_no].max

        will_fire = not toggle or (toggle and value == 127)

        if toggle:
            current_value = device.parameters[parameter_no].value
            next_value = max if current_value == min else min
        else:
            next_value = self.normalise(value, min, max)

        if self._manager.debug:
            self.log_message(f"{fn_name}: selected_device:{device.name}, trigger value:{value}, next value:{next_value}")
            self.log_message(f"Device param min:{min}, max: {max}, will_fire:{will_fire}, current value is {device.parameters[parameter_no].value}")

        if will_fire:
            self.log_message(f"Setting to = {float(next_value)}")
            device.parameters[parameter_no].value = next_value

        self.log_message(f"Value is {device.parameters[parameter_no].value}")

    def value_is_max(self, value, max):
        return value == max

    def normalise(self, midi_value, min_value, max_value):
        """
        Maps a MIDI value (0-127) to the given range [min_value, max_value].

        :param midi_value: int, The input MIDI value (0-127)
        :param min_value: int, The minimum value of the target range
        :param max_value: int, The maximum value of the target range
        :return: int, The mapped value within the range [min_value, max_value]
        """
        if min_value == max_value:
            return min_value

        normalized_value = midi_value / 127.0
        mapped_value = min_value + normalized_value * (max_value - min_value)

        # mapped_value = round(mapped_value)
        return max(min_value, min(mapped_value, max_value))

    def find_device(self, song, track_name, device_name):
        track = self.find_track(song, track_name)
        if track is not None:
            return self.find_device_on_track(track, device_name)

    def find_track(self, song, track_name):
        if track_name == "selected":
            return song.view.selected_track
        elif track_name == "master":
            return song.master_track
        elif track_name.isnumeric():
            return song.tracks[int(track_name)-1]


        for track in self._manager.song().tracks:
            if track is not None and track.name == track_name:
                return track

        return None

    def find_device_on_track(self,  track, device_name):
        if device_name.isnumeric():
            return track.devices[int(device_name)-1]

        for device in track.devices:
            if device is not None and device.name == device_name:
                return device

        return None