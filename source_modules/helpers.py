from dataclasses import dataclass, replace, field, Field
from typing import Any, Optional

from .pythonosc.udp_client import SimpleUDPClient
from .pythonosc.osc_message_builder import ArgValue
import logging


@dataclass
class RealParameter:
    param:Any
    alias:Optional[str] = None
    button:Optional[str] = None

@dataclass
class ParameterMapping:
    #(2, (5, 'Mono'), 'toggle')
    mapped_parameter:int
    alias:Optional[str] = None
    button:Optional[str] = None

    @classmethod
    def from_tuple(cls, tuple):
        return cls(tuple[0], tuple[1], tuple[2])

    @classmethod
    def on_off(cls, param=0):
        return cls(param, "On/Off", None)

    def with_real_param(self, real_param):
        return RealParameter(real_param, self.alias, self.button)

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

    #TODO Test
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
    # on_off: ParameterMapping = field(default_factory=lambda : ParameterMapping.on_off())
    # parameters: list[(int, Optional[str], Optional[str])] = field(default_factory=list)
    parameters: [(int, ParameterMapping)] = field(default_factory=list)

    def filter_parameter_indexes(self, parameter_indexes):
        return replace(self, parameters=[(i, p) for i, p in self.parameters if i-1 in parameter_indexes])

    @classmethod
    def from_raw_device_parameters(cls, device_parameter_count):
        return cls(parameters=[(i, ParameterMapping(i)) for i in range(1, device_parameter_count)])


    @classmethod
    def from_user_defined_parameters(cls, custom_mappings):
        return cls(parameters=[(i, m) for (i, m) in custom_mappings])

    def parameters_and_aliasses_from_device_params(self, device_parameters) -> [RealParameter]:
        #validate_parameters_are_in_device_parameters()

        for i, p in self.parameters:
            if p.mapped_parameter >= len(device_parameters):
                print(f"Warning: Parameter {p.mapped_parameter} is out of range for device parameters {len(device_parameters)}")
                print(f"Device parameters are: {[d.name for d in device_parameters]}")
                return []

        return [p.with_real_param(device_parameters[p.mapped_parameter]) for i, p in self.parameters]


    def parameter_from_device_params(self, device_parameters, param_no):
        if len([(i, p) for i, p in self.parameters if i == param_no]) == 0:
            print(f"Didn't find {param_no} in {self.parameters}")
            return None

        p, m = [(p, device_parameters[p.mapped_parameter]) for i, p in self.parameters if i == param_no][0]

        return RealParameter(m, alias=p.alias, button=p.button)

def parse_custom_mappings(custom_mappings_raw):
    res = {}
    for device, mappings in custom_mappings_raw.items():
        pm = [(m['c_idx'], ParameterMapping(m['d_idx'], m['alias'], m.get('button', None)))
         for m in mappings]

        res[device] = pm

    return res



class Helpers:
    def __init__(self, manager, remote, custom_mappings_raw, page_size=16):
        self._manager = manager
        self._custom_mappings = CustomMappings(manager, parse_custom_mappings(custom_mappings_raw))
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

        on_off = ParameterMapping.on_off().with_real_param(self._last_selected_device.parameters[0])
        all_params = [on_off] + real_params

        info = f"{self._device_parameter_paging._device_parameter_page}/{self._device_parameter_paging.page_count_of(self._last_device_parameter_count)}"
        self._remote.device_update(self._last_selected_device.name, all_params, info)

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

            if self._custom_mappings.has_user_defined_parameters(device):
                self.show_message(f"{device.class_name}")

    def device_parameter_action(self, device, raw_parameter_no, midi_no, value, fn_name, toggle=False):
        if device is None:
            return
        else:
            self.selected_device_changed(device)

        self.log_message(
            f"device_parameter_action raw data: name: {device.name}, class: {device.class_name}, Has custom params:{self._custom_mappings.has_user_defined_parameters(device)}, raw_parameter_no:{raw_parameter_no}, midi:{midi_no}, val:{value}, {fn_name}, {toggle}")

        page, paged_parameter_no = self._device_parameter_paging.paged_parameter_number(raw_parameter_no)
        self.log_message(f"device_parameter_action raw data: page:{page}, paged_param_no:{paged_parameter_no}")

        custom_mapping = self._custom_mappings.find_parameter(device, paged_parameter_no)
        if custom_mapping is None:
            self.log_message(f"Parameter {paged_parameter_no} not found on device {device.name}")
            self.show_message(f"Parameter {paged_parameter_no} not found on device {device.name}, page {page}")
            return

        parameter = custom_mapping.param
        button = custom_mapping.button

        self.log_message(
            f"device_parameter_action: {device.name}, {device.class_name}, ({self._custom_mappings.has_user_defined_parameters(device)}), raw_parameter_no:{raw_parameter_no}, param_page:{page}, param_name:{parameter.name} midi:{midi_no}, val:{value}, button:{button}, {fn_name}, {toggle}")

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
                (f"Device param {parameter} min:{min}, max: {max}, will_fire:{will_fire}, current value is {device.parameters[paged_parameter_no].value}")

        if will_fire:
            parameter.value = next_value
            self._remote.parameter_updated(custom_mapping, raw_parameter_no)

    def value_is_max(self, value, max):
        return value == max

    def device_param_cycle(self, device, param_no, cycle_min, cycle_max, fn_name):
        """
        Cycle a discrete-valued parameter through [cycle_min, cycle_max] inclusive.
        Wraps from cycle_max back to cycle_min.
        """
        if device is None:
            return
        if param_no >= len(device.parameters):
            self.log_message(f"{fn_name}: param {param_no} out of range for {device.class_name}")
            return
        parameter = device.parameters[param_no]
        steps = cycle_max - cycle_min + 1
        if steps < 2:
            return
        try:
            current_step = int(round(parameter.value))
        except (TypeError, ValueError):
            current_step = cycle_min
        next_step = cycle_min + ((current_step - cycle_min + 1) % steps)
        if self._manager.debug:
            self.log_message(
                f"{fn_name}: {device.class_name} param {param_no} cycle {cycle_min}..{cycle_max}: {current_step} -> {next_step}"
            )
        parameter.value = next_step

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


class CustomMappings:
    """
        CustomMappings

        Manages slot-derived parameter mappings keyed on the device's `class_name`.
        For each known device class (Compressor2, Eq8, ...) it carries the list of
        (encoder_index, ParameterMapping) entries derived from the user's `slots:` list
        and the family-intents JSON.

        Devices not in the slot table (notably Macro Racks — AudioEffectGroupDevice,
        InstrumentGroupDevice, MidiEffectGroupDevice, DrumGroupDevice) fall through to
        a direct identity mapping: encoder N drives device.parameters[N], so encoder 1
        drives Macro 1, encoder 2 drives Macro 2, etc. This is intentional — racks
        have no canonical slot meanings, so the macros themselves are the contract.
    """
    def __init__(self, manager,
                 custom_mappings: dict[str, [(int, ParameterMapping)]]):
        self._manager = manager

        self._custom_mappings: dict[str, [(int, ParameterMapping)]] = custom_mappings

    def log_message(self, message):
        self._manager.log_message(message)

    def show_message(self, message):
        self._manager.show_message(message)

    def has_user_defined_parameters(self, device):
        return self.device_lookup_key(device) in self._custom_mappings

    def device_lookup_key(self, device):
        return device.class_name

    def user_defined_parameters_for(self, device) -> [(int, ParameterMapping)]:
        return self._custom_mappings[self.device_lookup_key(device)]

    def user_defined_parameters_or_defaults(self, device) -> ParameterNumberGroup:
        '''
        Returns the user defined parameters for a device if they exist, otherwise returns the default parameters

        Will NOT send the on/off parameter, use ParameterGroup to send the on/off parameter
        :param device:
        :return:
        '''
        if not self.has_user_defined_parameters(device) or len(
                self.user_defined_parameters_for(device)) == 0:
            self.log_message(f"no mapping found for {device.name}/{device.class_name}, look up key: {self.device_lookup_key(device)}")
            return ParameterNumberGroup.from_raw_device_parameters(len(device.parameters))
        else:
            self.log_message(f"Creating ParameterNumberGroup from user defined parameters for {device.name}/{device.class_name}, look up key: {self.device_lookup_key(device)}. Parameter count on device is {len(device.parameters)}. User parameter count is: {len(self.user_defined_parameters_for(device))}")
            return ParameterNumberGroup.from_user_defined_parameters(self.user_defined_parameters_for(device))

    def find_parameter(self, device, parameter_no):
        '''

        :param device:
        :param parameter_no:
        :return parameter, alias tuple: or None if not found for the parameter number because the device has less parameters.
        '''
        if not self.has_user_defined_parameters(device):
            if parameter_no >= len(device.parameters):
                self.log_message("CustomMappings.find_parameter returning None as parameter_no >= len(device.parameters)")
                return None
            else:
                return RealParameter(device.parameters[parameter_no], None, None) #TODO RealParameter here?
        else:
            param_group = self.user_defined_parameters_or_defaults(device)
            self.log_message(f"CustomMappings.find_parameter param_group is {[(p[0], p[1].mapped_parameter) for p in param_group.parameters]}")
            return param_group.parameter_from_device_params(device.parameters, parameter_no)


class Remote:
    def __init__(self, manager, osc_client):
        self._manager = manager
        self._osc_client = osc_client

    #TODO unit tests datatypes sent
    def parameter_updated(self, real_param, parameter_no):
        param = real_param.param
        name = param.name if real_param.alias is None else real_param.alias
        self._osc_client.send_message(f"/selected-device/parameter-update",
                                      [parameter_no, param.value, name, param.min, param.max, real_param.button])

    def device_update(self, device_name, real_parameters, info_text=""):
        self._osc_client.send_message(f"/selected-device/name", [f"{device_name} [{info_text}]"])

        for i, pm in enumerate(real_parameters):
            self.parameter_updated(pm, i)

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
