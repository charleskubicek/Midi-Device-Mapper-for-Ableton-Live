from dataclasses import dataclass, replace, field
from typing import Any, Optional

from .pythonosc.udp_client import SimpleUDPClient
from .pythonosc.osc_message_builder import ArgValue
import logging


class SelectedDeviceParameterPaging:
    def __init__(self, manager, page_size=16):
        self._manager = manager
        self._page_size = page_size
        self._device_parameter_page = 1

    def paged_parameter_number(self, original_parameter):
        if self._device_parameter_page == 1:
            return 1, original_parameter
        else:
            return self._device_parameter_page, ((self._device_parameter_page - 1) * self._page_size) + original_parameter

    def parameters_indexes_for_selected_page(self, parameters_len):
        start = (self._device_parameter_page - 1) * self._page_size
        end = self._device_parameter_page * self._page_size
        return list(range(start, min(end, parameters_len)))

    def reset(self):
        self._device_parameter_page = 1

    def validate_and_report_device_page(self, device_parameter_count, page):
        if page < 1:
            self._manager.show_message("Page number must be greater than 0")
            return False
        elif page > self.page_count_of(device_parameter_count):
            self._manager.show_message(
                f"Page number {page} is greater than the number of pages {self.page_count_of(device_parameter_count)}")
            return False

        return True

    def device_parameter_page_inc(self, device_parameter_count):
        if self.validate_and_report_device_page(device_parameter_count, self._device_parameter_page + 1):
            self._device_parameter_page += 1
            self._manager.show_message(
                f"Page {self._device_parameter_page}/{self.page_count_of(device_parameter_count)} ({device_parameter_count})")
            return True
        else:
            return False

    def device_parameter_page_dec(self, device_parameter_count):
        if self.validate_and_report_device_page(device_parameter_count, self._device_parameter_page - 1):
            self._device_parameter_page -= 1
            self._manager.show_message(
                f"Page {self._device_parameter_page}/{self.page_count_of(device_parameter_count)} ({device_parameter_count})")
            return True
        else:
            return False

    def page_count_of(self, device_parameter_count):
        return int(device_parameter_count / self._page_size) + 1


@dataclass
class ParameterNumberGroup:
    on_off: [int, str] = field(default=(0, "On/Off"))
    parameters: list[(int, Optional[str])] = field(default_factory=list)

    def filter_parameter_indexes(self, parameter_indexes):
        return replace(self, parameters=[(p, a) for i, (p, a) in enumerate(self.parameters) if i in parameter_indexes])

    @classmethod
    def from_raw_device_parameters(cls, device_parameter_count):
        return cls((0, "On/Off"), list([(i, None) for i in range(1, device_parameter_count)]))


    @classmethod
    def from_user_defined_parameters(cls, custom_mappings):
        return ParameterNumberGroup((0, "On/Off"), [(p, a) for i, (p, a) in custom_mappings])

    def list_of_all_parameters(self):
        return [self.on_off] + self.parameters

    def parameters_and_aliasses_from_device_params(self, device_parameters, include_on_off=True):
        real_params = [(device_parameters[p[0]], p[1]) for p in self.parameters]
        if include_on_off:
            return [(device_parameters[0], "On/Off")] + real_params
        else:
            return real_params

    def parameter_from_device_params(self, device_parameters, param_no, include_on_off=True):
        return self.parameters_and_aliasses_from_device_params(device_parameters, include_on_off)[param_no]



class Helpers:
    def __init__(self, manager, remote, custom_mappings={}, page_size=16):
        self._manager = manager
        self._custom_mappings = CustomMappings(manager, custom_mappings)
        self._device_parameter_paging = SelectedDeviceParameterPaging(manager, page_size)
        self._last_device_message_about = None
        self._last_selected_device = None
        self._last_device_parameter_count = -1
        self._send_upd = True
        self.page_size = page_size

        self._remote = remote

    def show_message(self, message):
        self._manager.show_message(message)

    def log_message(self, message):
        self._manager.log_message(message)

    def device_parameter_page_inc(self):
        if self._device_parameter_paging.device_parameter_page_inc(self._last_device_parameter_count):
            self.update_remote_parameters()

    def device_parameter_page_dec(self):
        if self._device_parameter_paging.device_parameter_page_dec(self._last_device_parameter_count):
            self.update_remote_parameters()

    def update_remote_parameters(self):
        real_params = Helpers.get_actual_parameters_from_device(
            self._manager,
            self._custom_mappings,
            self._device_parameter_paging,
            self._last_selected_device)

        info = f"{self._device_parameter_paging._device_parameter_page}/{self._device_parameter_paging.page_count_of(self._last_device_parameter_count)}"
        self._remote.device_update(self._last_selected_device.name, real_params, info)

    @staticmethod
    def get_actual_parameters_from_device(manager, custom_mappings, paging, device):
        p_group = custom_mappings.user_defined_parameters_or_defaults(device)
        parameter_indexes = paging.parameters_indexes_for_selected_page(len(p_group.parameters))
        filtered = p_group.filter_parameter_indexes(parameter_indexes)
        real_params = filtered.parameters_and_aliasses_from_device_params(device.parameters)

        # manager.log_message(f"update_remote_parameters: p_group      : {str(p_group.parameters)}")
        # manager.log_message(f"update_remote_parameters: param numbers: {(str(parameter_indexes))}")
        # manager.log_message(f"update_remote_parameters: filtered     : {str(filtered.parameters)}")
        # manager.log_message(f"update_remote_parameters: real_params: : {[r.name[0:5] for r in real_params]}")

        return real_params

    def selected_device_changed(self, device):
        if device is None:
            # self.log_message("Selected device is None")
            return
        if device == self._last_selected_device:
            # self.log_message("Selected device is the same as last time")
            return
        else:
            self._last_selected_device = device
            self._last_device_message_about = None
            self._last_device_parameter_count = len(self._custom_mappings.user_defined_parameters_or_defaults(device).parameters)

            self._device_parameter_paging.reset()
            self.update_remote_parameters()

            if self._custom_mappings.has_user_defined_parameters(device.class_name):
                self.show_message(f"{device.class_name}")

    def device_parameter_action(self, device, raw_parameter_no, midi_no, value, fn_name, toggle=False):
        if device is None:
            return
        else:
            self.selected_device_changed(device)

        page, paged_parameter_no = self._device_parameter_paging.paged_parameter_number(raw_parameter_no)
        parameter, alias = self._custom_mappings.find_parameter(device, paged_parameter_no)

        self.log_message(
            f"device_parameter_action: {device.name}, {device.class_name}, ({self._custom_mappings.has_user_defined_parameters(device.class_name)}), raw_parameter_no:{raw_parameter_no}, param_page:{page}, param_name:{parameter.name} midi:{midi_no}, val:{value}, {fn_name}, {toggle}")

        if parameter is None:
            self.log_message(f"Parameter {paged_parameter_no} not found on device {device.name}")
            self.show_message(f"Parameter {paged_parameter_no} not found on device {device.name}, page {page}")
            return

        min = parameter.min
        max = parameter.max

        will_fire = not toggle or (toggle and value == 127)

        if toggle:
            current_value = parameter.value
            next_value = max if current_value == min else min
        else:
            next_value = self.normalise(value, min, max)

        if self._manager.debug:
            self.log_message \
                (f"{fn_name}: selected_device:{device.name}, trigger value:{value}, next value:{next_value}")
            self.log_message \
                (f"Device param min:{min}, max: {max}, will_fire:{will_fire}, current value is {device.parameters[paged_parameter_no].value}")

        if will_fire:
            parameter.value = next_value
            self._remote.parameter_updated(parameter, alias, raw_parameter_no, next_value)

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
        if self._manager.debug:
            self.log_message(f"Looking for device {device_name} on track {track_name}")

        track = self.find_track(song, track_name)
        if track is not None:
            return self.find_device_on_track(track, device_name)
        else:
            self.log_message(f"Track {track_name} not found")
            return None

    def find_track(self, song, track_name):
        if self._manager.debug:
            self.log_message(f"Looking for track {track_name}")

        if track_name == "selected":
            return song.view.selected_track
        elif track_name == "master":
            return song.master_track
        elif track_name.isnumeric():
            return song.tracks[int(track_name) - 1]

        if self._manager.debug:
            self.log_message(f"Track {track_name} must be one of: selected, manager or number")
            from pprint import pprint;
            pprint(vars(song))

        for track in self._manager.song().tracks:
            if track is not None and track.name == track_name:
                return track

        if self._manager.debug:
            self.log_message(f"Track {track_name} not found")

        return None

    def find_device_on_track(self, track, device_name):
        if self._manager.debug:
            self.log_message(f"find_device_on_track Looking for device {device_name} on track {track.name}")

        if device_name == "selected":
            return track.view.selected_device
        elif device_name.isnumeric():
            return track.devices[int(device_name) - 1]

        for device in track.devices:
            if device is not None and device.name == device_name:
                return device

        if self._manager.debug:
            self.log_message(f"Device {device_name} not found")

        return None


"""
CustomMappings

This class is responsible for managing custom mappings for devices. It is used to find user defined parameters or defaults
for a given device. It also provides a method to find a parameter for a given device, parameter number and midi number.

The custom_mappings maps encoder indexes to device parameter indexes

"""


class CustomMappings:
    def __init__(self, manager, custom_mappings: dict[str, [(int, (int, str))]]):
        self._manager = manager
        self._custom_mappings: dict[str, [(int, (int, str))]] = custom_mappings

    def log_message(self, message):
        self._manager.log_message(message)

    def show_message(self, message):
        self._manager.show_message(message)

    def has_user_defined_parameters(self, device_class_name):
        return device_class_name in self._custom_mappings

    def user_defined_parameters_or_defaults(self, device) -> ParameterNumberGroup:
        '''
        Returns the user defined parameters for a device if they exist, otherwise returns the default parameters

        Will NOT send the on/off parameter, use ParameterGroup to send the on/off parameter
        :param device:
        :return:
        '''
        if not self.has_user_defined_parameters(device.class_name) or len(
                self._custom_mappings[device.class_name]) == 0:
            return ParameterNumberGroup.from_raw_device_parameters(len(device.parameters))
        else:
            return ParameterNumberGroup.from_user_defined_parameters(self._custom_mappings[device.class_name])

    def find_parameter(self, device, parameter_no):
        '''

        :param device:
        :param parameter_no:
        :return parameter, alias tuple:
        '''
        if not self.has_user_defined_parameters(device.class_name):
            return device.parameters[parameter_no], None
        else:
            param_group = self.user_defined_parameters_or_defaults(device)
            return param_group.parameter_from_device_params(device.parameters, parameter_no, include_on_off=True)


class Remote:
    def __init__(self, manager, osc_client):
        self._manager = manager
        self._osc_client = osc_client

    def parameter_updated(self, param, alias, parameter_no, next_value):
        name = param.name if alias is None else alias
        self._osc_client.send_message(f"/selected-device/parameter-update",
                                      [parameter_no, str(next_value), name, param.min, param.max])

    def device_update(self, device_name, real_parameters, info_text=""):
        self._osc_client.send_message(f"/selected-device/name", [f"{device_name} [{info_text}]"])

        for i, (param, alias) in enumerate(real_parameters):
            self.parameter_updated(param, alias, i, param.value)

        self._osc_client.send_message(f"/selected-device/parameter-update-complete", [min(len(real_parameters), 16)])


class NullOSCClient:
    def send_message(self, address: str, value: ArgValue) -> None:
        pass


class OSCClient:

    def __init__(self, host='127.0.0.1', port=5005):
        self.client = SimpleUDPClient(host, port)
        self.logger = logging.getLogger("osc-client")

        self.logger.info(f"OSCClient created with host {host} and port {port}")

    def send_message(self, address: str, value: ArgValue) -> None:
        try:
            self.client.send_message(address, value)
        except Exception as e:
            self.logger.error(f"Error sending OSC message {address} {value} {e}")


class OSCMultiClient:

    def __init__(self, clients: list[OSCClient]):
        self.clients = clients

    def send_message(self, address: str, value: ArgValue) -> None:
        for client in self.clients:
            client.send_message(address, value)
