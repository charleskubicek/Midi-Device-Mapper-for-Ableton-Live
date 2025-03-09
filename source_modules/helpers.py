from dataclasses import dataclass
from typing import Any

from .pythonosc.udp_client import SimpleUDPClient
from .pythonosc.osc_message_builder import ArgValue
import logging

class SelectedDeviceParameterPaging:
    def __init__(self, manager, page_size = 16):
        self._manager = manager
        self._page_size = page_size
        self._device_parameter_page = 1

    def paged_parameter_number(self, original_parameter):
        if self._device_parameter_page == 1:
            return 1, original_parameter
        else:
            return self._device_parameter_page, ((self._device_parameter_page - 1) * self._page_size) + original_parameter

    def parameters_numbers_for_selected_page(self, parameters):
        start = (self._device_parameter_page - 1) * self._page_size
        end = self._device_parameter_page * self._page_size
        return list(range(start, min(end, len(parameters))))

    def reset(self):
        self._device_parameter_page = 1

    def validate_and_report_device_page(self, device_parameter_count, page):
        if page < 1:
            self._manager.show_message("Page number must be greater than 0")
            return False
        elif page > self.page_count_of(device_parameter_count):
            self._manager.show_message(f"Page number {page} is greater than the number of pages {self.page_count_of(device_parameter_count)}")
            return False

        return True

    def device_parameter_page_inc(self, device_parameter_count):
        if self.validate_and_report_device_page(device_parameter_count, self._device_parameter_page + 1):
            self._device_parameter_page += 1
            self._manager.show_message(f"Page {self._device_parameter_page}/{self.page_count_of(device_parameter_count)} ({device_parameter_count})")
            return True
        else:
            return False

    def device_parameter_page_dec(self, device_parameter_count):
        if self.validate_and_report_device_page(device_parameter_count, self._device_parameter_page - 1):
            self._device_parameter_page -= 1
            self._manager.show_message(f"Page {self._device_parameter_page}/{self.page_count_of(device_parameter_count)} ({device_parameter_count})")
            return True
        else:
            return False

    def page_count_of(self, device_parameter_count):
        return int(device_parameter_count / self._page_size) + 1

@dataclass
class ParameterGroup:
    on_off:Any
    parameters:list

    def list_of_all_parameters(self):
        return [self.on_off] + self.parameters

class Helpers:
    def __init__(self, manager, remote, custom_mappings={}, page_size=16):
        self._manager = manager
        # self._raw_custom_mappings = custom_mappings
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
        parameters = self._custom_mappings.find_user_defined_parameters_or_defaults(self._last_selected_device)
        parameter_numbers = self._device_parameter_paging.parameters_numbers_for_selected_page(parameters)
        params_to_update = [p for i, p in enumerate(parameters) if i in parameter_numbers]
        params = ParameterGroup(parameters[0], params_to_update)

        self._remote.device_update(self._last_selected_device.name, params,
                                   f"{self._device_parameter_paging._device_parameter_page}/{self._device_parameter_paging.page_count_of(self._last_device_parameter_count)}")

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
            self._last_device_parameter_count = len(self._custom_mappings.find_user_defined_parameters_or_defaults(device))

            parameters = self._custom_mappings.find_user_defined_parameters_or_defaults(device)
            self.log_message(f"Selected device changed to {device.class_name} with {len(parameters)} parameters")
            self._remote.device_update(device.name, ParameterGroup(parameters[0], parameters[0:self.page_size]))
            self._device_parameter_paging.reset()

            if self._custom_mappings.has_user_defined_parameters(device):
                self.show_message(f"{device.class_name}  ({len(parameters)} custom parameters)")

    def device_parameter_action(self, device, raw_parameter_no, midi_no, value, fn_name, toggle=False):
        if device is None:
            return
        else:
            self.selected_device_changed(device)

        page, paged_parameter_no = self._device_parameter_paging.paged_parameter_number(raw_parameter_no)

        self.log_message(
            f"device_parameter_action: {device.name}, {device.class_name}, ({self._custom_mappings.has_user_defined_parameters(device)}), param:{raw_parameter_no}, param_page:{page}, midi:{midi_no}, val:{value}, {fn_name}, {toggle}")

        parameter = self._custom_mappings.find_parameter(device, paged_parameter_no)

        if parameter is None:
            self.log_message(f"Parameter {paged_parameter_no} not found on device {device.name}")
            self.show_message(f"Parameter {paged_parameter_no} not found on device {device.name}, page {page}")
            return

        if self._custom_mappings.has_user_defined_parameters(device):
            self.log_message(f"Found custom mapping for encoder {raw_parameter_no}/page {paged_parameter_no} is {parameter.name}")

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
            # self.log_message(f"Setting to = {float(next_value)}")
            parameter.value = next_value

            self._remote.parameter_updated(parameter, paged_parameter_no, next_value)

        # self.log_message(f"Value is {parameter.value}")

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

"""
class CustomMappings:
    def __init__(self, manager, custom_mappings: dict[str, [(int, int)]]):
        self._manager = manager
        self._custom_mappings: dict[str, [(int, int)]] = custom_mappings

    def log_message(self, message):
        self._manager.log_message(message)

    def show_message(self, message):
        self._manager.show_message(message)

    def has_user_defined_parameters(self, device):
        return device.class_name in self._custom_mappings

    def find_user_defined_parameters_or_defaults(self, device):
        if not self.has_user_defined_parameters(device) or len(self._custom_mappings[device.class_name]) == 0:
            return device.parameters
        else:
            return [device.parameters[p_no] for m, p_no in self._custom_mappings[device.class_name]]

    def find_parameter(self, device, parameter_no):
        if not self.has_user_defined_parameters(device):
            return device.parameters[parameter_no]
        else:
            params = self.find_user_defined_parameters_or_defaults(device)
            if parameter_no < len(params):
                return params[parameter_no]
            else:
                return None


class Remote:
    def __init__(self, osc_client):
        self._osc_client = osc_client

    def parameter_updated(self, param, parameter_no, next_value):
        self._osc_client.send_message(f"/selected-device/parameter-update",
                                      [parameter_no, str(next_value), param.name, param.min, param.max])

    def device_update(self, device_name, parameters:ParameterGroup, info_text=""):
        self._osc_client.send_message(f"/selected-device/name", [f"{device_name} [{info_text}]"])

        all_parameters = parameters.list_of_all_parameters()[0:17]
        for i, param in enumerate(all_parameters):
            self._osc_client.send_message(f"/selected-device/parameter-update",
                                          [i, str(param.value), param.name, param.min, param.max])

        self._osc_client.send_message(f"/selected-device/parameter-update-complete", [min(len(all_parameters), 16)])


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


device_parameter_names = {
    'OriginalSimpler': [
        {'no': '00', 'name': 'Device On', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '01', 'name': 'Snap', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '02', 'name': 'Sample Selector', 'value': 0.0, 'min': 0.0, 'max': 127.0},
        {'no': '03', 'name': 'S Start', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '04', 'name': 'S Length', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '05', 'name': 'S Loop On', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '06', 'name': 'S Loop Length', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '07', 'name': 'S Loop Fade', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '08', 'name': 'Spread', 'value': 0.0, 'min': 0.0, 'max': 100.0},
        {'no': '09', 'name': 'Glide Mode', 'value': 0.0, 'min': 0.0, 'max': 2.0},
        {'no': '10', 'name': 'Glide Time', 'value': 0.5397940278053284, 'min': 0.0, 'max': 1.0},
        {'no': '11', 'name': 'Transpose', 'value': 0.0, 'min': -48.0, 'max': 48.0},
        {'no': '12', 'name': 'Detune', 'value': 0.0, 'min': -50.0, 'max': 50.0},
        {'no': '13', 'name': 'Pitch < LFO', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '14', 'name': 'Pe On', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '15', 'name': 'Pe < Env', 'value': 0.0, 'min': -48.0, 'max': 48.0},
        {'no': '16', 'name': 'Pe Attack', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '17', 'name': 'Pe Init', 'value': 0.0, 'min': -1.0, 'max': 1.0},
        {'no': '18', 'name': 'Pe A Slope', 'value': 0.0, 'min': -1.0, 'max': 1.0},
        {'no': '19', 'name': 'Pe Decay', 'value': 0.581428050994873, 'min': 0.0, 'max': 1.0},
        {'no': '20', 'name': 'Pe Peak', 'value': 1.0, 'min': -1.0, 'max': 1.0},
        {'no': '21', 'name': 'Pe D Slope', 'value': 1.0, 'min': -1.0, 'max': 1.0},
        {'no': '22', 'name': 'Pe Sustain', 'value': 0.0, 'min': -1.0, 'max': 1.0},
        {'no': '23', 'name': 'Pe Release', 'value': 0.35557058453559875, 'min': 0.0, 'max': 1.0},
        {'no': '24', 'name': 'Pe End', 'value': 0.0, 'min': -1.0, 'max': 1.0},
        {'no': '25', 'name': 'Pe R Slope', 'value': 1.0, 'min': -1.0, 'max': 1.0},
        {'no': '26', 'name': 'Pe Mode', 'value': 0.0, 'min': 0.0, 'max': 4.0},
        {'no': '27', 'name': 'Pe Loop', 'value': 0.5397940278053284, 'min': 0.0, 'max': 1.0},
        {'no': '28', 'name': 'Pe Retrig', 'value': 3.0, 'min': 0.0, 'max': 14.0},
        {'no': '29', 'name': 'Pe R < Vel', 'value': 0.0, 'min': -100.0, 'max': 100.0},
        {'no': '30', 'name': 'Volume', 'value': -12.0, 'min': -36.0, 'max': 36.0},
        {'no': '31', 'name': 'Vol < Vel', 'value': 0.3499999940395355, 'min': 0.0, 'max': 1.0},
        {'no': '32', 'name': 'Vol < LFO', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '33', 'name': 'Pan', 'value': 0.0, 'min': -1.0, 'max': 1.0},
        {'no': '34', 'name': 'Pan < Rnd', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '35', 'name': 'Pan < LFO', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '36', 'name': 'Ve Attack', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '37', 'name': 'Ve Decay', 'value': 0.581428050994873, 'min': 0.0, 'max': 1.0},
        {'no': '38', 'name': 'Ve Sustain', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '39', 'name': 'Ve Release', 'value': 0.35557058453559875, 'min': 0.0, 'max': 1.0},
        {'no': '40', 'name': 'Ve Mode', 'value': 0.0, 'min': 0.0, 'max': 4.0},
        {'no': '41', 'name': 'Ve Loop', 'value': 0.5397940278053284, 'min': 0.0, 'max': 1.0},
        {'no': '42', 'name': 'Ve Retrig', 'value': 3.0, 'min': 0.0, 'max': 14.0},
        {'no': '43', 'name': 'Fade In', 'value': 0.03684031590819359, 'min': 0.0, 'max': 1.0},
        {'no': '44', 'name': 'Trigger Mode', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '45', 'name': 'Fade Out', 'value': 0.03684031590819359, 'min': 0.0, 'max': 1.0},
        {'no': '46', 'name': 'F On', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '47', 'name': 'Filter Type', 'value': 0.0, 'min': 0.0, 'max': 4.0},
        {'no': '48', 'name': 'Filter Circuit - LP/HP', 'value': 0.0, 'min': 0.0, 'max': 4.0},
        {'no': '49', 'name': 'Filter Circuit - BP/NO/Morph', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '50', 'name': 'Filter Slope', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '51', 'name': 'Filter Freq', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '52', 'name': 'Filter Res', 'value': 0.0, 'min': 0.0, 'max': 1.25},
        {'no': '53', 'name': 'Filter Morph', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '54', 'name': 'Filter Drive', 'value': 0.0, 'min': 0.0, 'max': 24.0},
        {'no': '55', 'name': 'Fe On', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '56', 'name': 'Fe < Env', 'value': 0.0, 'min': -72.0, 'max': 72.0},
        {'no': '57', 'name': 'Fe Attack', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '58', 'name': 'Fe Init', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '59', 'name': 'Fe A Slope', 'value': 0.0, 'min': -1.0, 'max': 1.0},
        {'no': '60', 'name': 'Fe Decay', 'value': 0.581428050994873, 'min': 0.0, 'max': 1.0},
        {'no': '61', 'name': 'Fe Peak', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '62', 'name': 'Fe D Slope', 'value': 1.0, 'min': -1.0, 'max': 1.0},
        {'no': '63', 'name': 'Fe Sustain', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '64', 'name': 'Fe Release', 'value': 0.35557058453559875, 'min': 0.0, 'max': 1.0},
        {'no': '65', 'name': 'Fe End', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '66', 'name': 'Fe R Slope', 'value': 1.0, 'min': -1.0, 'max': 1.0},
        {'no': '67', 'name': 'Fe Mode', 'value': 0.0, 'min': 0.0, 'max': 4.0},
        {'no': '68', 'name': 'Fe Loop', 'value': 0.5397940278053284, 'min': 0.0, 'max': 1.0},
        {'no': '69', 'name': 'Fe Retrig', 'value': 3.0, 'min': 0.0, 'max': 14.0},
        {'no': '70', 'name': 'Fe R < Vel', 'value': 0.0, 'min': -100.0, 'max': 100.0},
        {'no': '71', 'name': 'Filt < Key', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '72', 'name': 'Filt < Vel', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '73', 'name': 'Filt < LFO', 'value': 0.0, 'min': 0.0, 'max': 24.0},
        {'no': '74', 'name': 'L On', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '75', 'name': 'L Wave', 'value': 0.0, 'min': 0.0, 'max': 5.0},
        {'no': '76', 'name': 'L Sync', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '77', 'name': 'L Rate', 'value': 0.5751884579658508, 'min': 0.0, 'max': 1.0},
        {'no': '78', 'name': 'L Sync Rate', 'value': 4.0, 'min': 0.0, 'max': 21.0},
        {'no': '79', 'name': 'L R < Key', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '80', 'name': 'L Attack', 'value': 0.0, 'min': 0.0, 'max': 1.0},
        {'no': '81', 'name': 'L Retrig', 'value': 1.0, 'min': 0.0, 'max': 1.0},
        {'no': '82', 'name': 'L Offset', 'value': 0.0, 'min': 0.0, 'max': 360.0}
    ]
}
