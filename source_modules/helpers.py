from dataclasses import dataclass
from typing import Any, Optional

from .pythonosc.udp_client import SimpleUDPClient
from .pythonosc.osc_message_builder import ArgValue
from .hud_client import HudClient, NullHudClient
from .hud_protocol import SlotPayload, EMPTY_SLOT
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

@dataclass
class SwitchSlotMapping:
    switch_idx: int
    d_idx: int
    alias: str


def _overlay_labels(payloads, labels, kind):
    """Replace EMPTY slots with labeled placeholders when the active mode
    binds that wire index to a non-device mapping. Real device data stays
    untouched."""
    if not labels:
        return payloads
    out = []
    for wire_idx, p in payloads:
        if p == EMPTY_SLOT:
            label = labels.get((kind, wire_idx))
            if label is not None:
                out.append((wire_idx, SlotPayload(label, 0, 0, 1)))
                continue
        out.append((wire_idx, p))
    return out


def _build_device_table(raw):
    table = {}
    if not raw:
        return table
    for d in raw.get('devices', []):
        table[d['className']] = {
            'encoders': d.get('encoders', []) or [],
            'buttons': d.get('buttons', []) or [],
        }
    return table


class Helpers:
    def __init__(self, manager, remote,
                 slot_assignments=None, switch_slot_assignments=None,
                 parameter_mappings_raw=None,
                 encoder_slot_count=8, button_slot_count=8,
                 hud_cells=None, mode_hud_labels=None):
        self._manager = manager
        self._remote = remote
        self._slot_assignments = list(slot_assignments or [])
        self._switch_slot_assignments = list(switch_slot_assignments or [])
        self._device_table = _build_device_table(parameter_mappings_raw)
        self._encoder_slot_count = encoder_slot_count
        self._button_slot_count = button_slot_count
        self._hud_cells = hud_cells or []
        # mode_hud_labels: {mode_name: {(kind, wire_idx): label}} for non-device
        # mappings. Device cells are populated from live device state and don't
        # appear here. _current_mode_name tracks which overlay is active.
        self._mode_hud_labels = mode_hud_labels or {}
        self._current_mode_name = None
        self._remote.init_layout(self._hud_cells)
        self._encoder_page = 1
        self._button_page = 1
        self._last_selected_device = None
        self._group_selector_listeners = []  # [(param, callback)] for teardown

    def show_message(self, message):
        self._manager.show_message(message)

    def log_message(self, message):
        self._manager.log_message(message)

    def has_user_defined_parameters(self, device):
        return device is not None and device.class_name in self._device_table

    def _encoder_json_index(self, c_idx):
        return (self._encoder_page - 1) * self._encoder_slot_count + (c_idx - 1)

    def _button_json_index(self, switch_idx):
        return (self._button_page - 1) * self._button_slot_count + switch_idx

    def _encoder_pages_count(self, device):
        n = len(self._device_table.get(getattr(device, 'class_name', None), {}).get('encoders', []))
        if n == 0:
            return 1
        return max(1, (n + self._encoder_slot_count - 1) // self._encoder_slot_count)

    def _button_pages_count(self, device):
        n = len(self._device_table.get(getattr(device, 'class_name', None), {}).get('buttons', []))
        if n == 0:
            return 1
        return max(1, (n + self._button_slot_count - 1) // self._button_slot_count)

    def _resolve_encoder(self, device, c_idx):
        if device is None:
            return None
        idx = self._encoder_json_index(c_idx)
        entry = self._device_table.get(device.class_name)
        if entry and idx < len(entry['encoders']):
            e = entry['encoders'][idx]
            if 'controlledBy' in e and 'group' in e:
                e = self._resolve_group_member(device, e)
                if e is None:
                    return None
            d_idx = int(e['number'])
            if d_idx >= len(device.parameters):
                return None
            return RealParameter(device.parameters[d_idx], e.get('display') or e.get('name'), e.get('button'))
        # Identity fallback: skip on/off (idx 0) and quantized params so
        # buttons (which switch slots already cover) don't double up on encoders.
        non_quantized = [(i, p) for i, p in enumerate(device.parameters)
                         if i > 0 and not getattr(p, 'is_quantized', False)]
        if idx >= len(non_quantized):
            return None
        d_idx, p = non_quantized[idx]
        return RealParameter(p, None, None)

    def _resolve_group_member(self, device, entry):
        selector_name = entry['controlledBy']
        selector = next((p for p in device.parameters if p.name == selector_name), None)
        if selector is None:
            return None
        try:
            sel_value = int(round(selector.value))
        except (TypeError, ValueError):
            return None
        for member in entry['group']:
            if sel_value in member.get('activeWhen', []):
                return member
        return None

    def _resolve_switch(self, device, switch_idx):
        if device is None:
            return None
        idx = self._button_json_index(switch_idx)
        entry = self._device_table.get(device.class_name)
        if entry and idx < len(entry['buttons']):
            b = entry['buttons'][idx]
            d_idx = int(b['number'])
            if d_idx >= len(device.parameters):
                return None
            has_range = 'min' in b and 'max' in b
            return {
                'param': device.parameters[d_idx],
                'alias': b.get('display') or b.get('name'),
                'd_idx': d_idx,
                'has_range': has_range,
                'min': int(b['min']) if has_range else None,
                'max': int(b['max']) if has_range else None,
            }
        quantized = [(i, p) for i, p in enumerate(device.parameters) if i > 0 and getattr(p, 'is_quantized', False)]
        if idx >= len(quantized):
            return None
        d_idx, p = quantized[idx]
        return {
            'param': p, 'alias': p.name, 'd_idx': d_idx,
            'has_range': True, 'min': int(p.min), 'max': int(p.max),
        }

    def selected_device_changed(self, device):
        if device is None or device == self._last_selected_device:
            return
        self._teardown_group_selector_listeners()
        self._last_selected_device = device
        self._encoder_page = 1
        self._button_page = 1
        self._attach_group_selector_listeners(device)
        self.update_remote_parameters()
        if self.has_user_defined_parameters(device):
            self.show_message(f"{device.class_name}")

    def _attach_group_selector_listeners(self, device):
        entry = self._device_table.get(getattr(device, 'class_name', None))
        if not entry:
            return
        seen = set()
        for e in entry['encoders']:
            name = e.get('controlledBy') if isinstance(e, dict) else None
            if not name or name in seen:
                continue
            seen.add(name)
            selector = next((p for p in device.parameters if p.name == name), None)
            if selector is None or not hasattr(selector, 'add_value_listener'):
                continue
            cb = self._on_group_selector_changed
            try:
                selector.add_value_listener(cb)
                self._group_selector_listeners.append((selector, cb))
            except Exception as ex:
                self.log_message(f"[group] failed to attach listener on {name}: {ex}")

    def _teardown_group_selector_listeners(self):
        for selector, cb in self._group_selector_listeners:
            try:
                selector.remove_value_listener(cb)
            except Exception:
                pass
        self._group_selector_listeners = []

    def _on_group_selector_changed(self):
        if self._last_selected_device is not None:
            self.update_remote_parameters()

    def device_parameter_action(self, device, raw_parameter_no, midi_no, value, fn_name, toggle=False):
        if device is None:
            return
        self.selected_device_changed(device)
        rp = self._resolve_encoder(device, raw_parameter_no)
        if rp is None:
            self.log_message(f"{fn_name}: encoder {raw_parameter_no} not resolvable on {device.class_name}")
            return
        parameter = rp.param
        will_fire = not toggle or (toggle and value == 127)
        if toggle:
            next_value = parameter.max if parameter.value == parameter.min else parameter.min
        else:
            next_value = self.normalise(value, parameter.min, parameter.max)
        if will_fire:
            parameter.value = next_value
            self._remote.parameter_updated(rp, raw_parameter_no)

    def switch_slot_action(self, device, slot_name, value, fn_name):
        self.log_message(f"[switch] enter fn={fn_name} slot={slot_name} value={value} device={getattr(device,'class_name','None')}")
        if device is None:
            return
        self.selected_device_changed(device)
        switch_idx = int(slot_name.replace('switch', '')) - 1
        info = self._resolve_switch(device, switch_idx)
        if info is None:
            self.log_message(f"[switch] {slot_name} not resolvable on {device.class_name}")
            return
        p = info['param']
        before = p.value
        is_q = getattr(p, 'is_quantized', False)
        self.log_message(f"[switch] resolved d_idx={info['d_idx']} alias={info.get('alias')} has_range={info['has_range']} json_min={info.get('min')} json_max={info.get('max')} param.min={p.min} param.max={p.max} param.value={before} is_quantized={is_q}")
        if info['has_range']:
            self._cycle(p, info['min'], info['max'])
            mode = "cycle(json)"
        elif is_q:
            try:
                self._cycle(p, int(p.min), int(p.max))
                mode = "cycle(param)"
            except (TypeError, ValueError):
                self._pulse(p)
                mode = "pulse(fallback)"
        else:
            self._pulse(p)
            mode = "pulse"
        self.log_message(f"[switch] applied mode={mode} before={before} after={p.value}")

    def _cycle(self, parameter, cmin, cmax):
        steps = cmax - cmin + 1
        if steps < 2:
            return
        try:
            current = int(round(parameter.value))
        except (TypeError, ValueError):
            current = cmin
        parameter.value = cmin + ((current - cmin + 1) % steps)

    def _pulse(self, parameter):
        parameter.value = parameter.max

    def parameter_page_inc(self, target):
        device = self._last_selected_device
        if device is None:
            return
        if target == 'encoder':
            count = self._encoder_pages_count(device)
            if self._encoder_page < count:
                self._encoder_page += 1
                self.show_message(f"Enc page {self._encoder_page}/{count}")
                self.update_remote_parameters()
        else:
            count = self._button_pages_count(device)
            if self._button_page < count:
                self._button_page += 1
                self.show_message(f"Btn page {self._button_page}/{count}")
                self.update_remote_parameters()

    def parameter_page_dec(self, target):
        device = self._last_selected_device
        if device is None:
            return
        if target == 'encoder':
            if self._encoder_page > 1:
                self._encoder_page -= 1
                count = self._encoder_pages_count(device)
                self.show_message(f"Enc page {self._encoder_page}/{count}")
                self.update_remote_parameters()
        else:
            if self._button_page > 1:
                self._button_page -= 1
                count = self._button_pages_count(device)
                self.show_message(f"Btn page {self._button_page}/{count}")
                self.update_remote_parameters()

    def update_remote_parameters(self):
        device = self._last_selected_device
        if device is None:
            return
        on_off = ParameterMapping.on_off().with_real_param(device.parameters[0])
        real_params = [on_off]
        for c_idx, _slot in sorted(self._slot_assignments):
            rp = self._resolve_encoder(device, c_idx)
            if rp is not None:
                real_params.append(rp)
        switch_entries = []
        for wire_idx, slot in self._switch_slot_assignments:
            # slot_name ("switch1", "switch2", …) drives JSON-table parameter
            # resolution; wire_idx is the HUD button index assigned at codegen.
            logical_idx = int(slot.replace('switch', '')) - 1
            info = self._resolve_switch(device, logical_idx)
            if info is not None:
                switch_entries.append(SwitchSlotMapping(wire_idx, info['d_idx'], info.get('alias') or ''))
        info_text = f"e{self._encoder_page}/b{self._button_page}"
        mode_labels = self._mode_hud_labels.get(self._current_mode_name)
        enc_total = self._encoder_pages_count(device)
        btn_total = self._button_pages_count(device)
        self._remote.device_update(
            device.name, real_params, info_text, switch_entries, device.parameters,
            hud_layout=self._hud_cells, mode_labels=mode_labels,
            enc_page=self._encoder_page, enc_total=enc_total,
            btn_page=self._button_page, btn_total=btn_total,
        )

    def refresh_hud_for_mode(self, mode_name, device):
        """Called by the surface when goto_mode swaps bindings. Sets the
        active overlay and re-emits a burst so the HUD reflects the new
        labels for non-device cells. Device cells reuse the existing
        device-path data when a device is focused."""
        self._current_mode_name = mode_name
        if device is not None:
            self._last_selected_device = device
        if self._last_selected_device is not None:
            self.update_remote_parameters()
        else:
# No focused device yet — emit a label-only burst.
            mode_labels = self._mode_hud_labels.get(mode_name) or {}
            self._remote.device_update(
                '', [], info_text='', switch_entries=[], device_parameters=[],
                hud_layout=self._hud_cells, mode_labels=mode_labels,
                enc_page=1, enc_total=1, btn_page=1, btn_total=1,
            )

    def value_is_max(self, value, max):
        return value == max

    def normalise(self, midi_value, min_value, max_value):
        if min_value == max_value:
            return min_value
        normalized_value = midi_value / 127.0
        mapped_value = min_value + normalized_value * (max_value - min_value)
        return max(min_value, min(mapped_value, max_value))

    def find_device(self, song, track_name, device_name):
        track = self.find_track(song, track_name)
        if track is not None:
            return self.find_device_on_track(track, device_name)
        return None

    def find_track(self, song, track_name):
        if track_name == "selected":
            return song.view.selected_track
        elif track_name == "master":
            return song.master_track
        elif track_name.isnumeric():
            return song.tracks[int(track_name) - 1]
        for track in self._manager.song().tracks:
            if track is not None and track.name == track_name:
                return track
        return None

    def find_device_on_track(self, track, device_name):
        if device_name == "selected":
            return track.view.selected_device
        elif device_name.isnumeric():
            return track.devices[int(device_name) - 1]
        for device in track.devices:
            if device is not None and device.name == device_name:
                return device
        return None


class Remote:
    def __init__(self, manager, osc_client, hud_client=None):
        self._manager = manager
        self._osc_client = osc_client
        self._hud_client = hud_client if hud_client is not None else NullHudClient()
        self._in_burst = False  # suppresses UPDATE during device_update burst

    def init_layout(self, cells):
        if cells:
            self._hud_client.send_layout(cells)

    #TODO unit tests datatypes sent
    def parameter_updated(self, real_param, parameter_no):
        param = real_param.param
        name = param.name if real_param.alias is None else real_param.alias
        self._osc_client.send_message(f"/selected-device/parameter-update",
                                      [parameter_no, param.value, name, param.min, param.max, real_param.button])
        # Live HUD update — skip on/off (index 0) and skip during the initial burst
        if parameter_no > 0 and not self._in_burst:
            self._hud_client.send_update('dial', parameter_no - 1, name, param.value, param.min, param.max)

    def refresh_burst(self, device_name, dial_payloads=(), button_payloads=(), page_info=None):
        """Generic dense burst. dial_payloads / button_payloads are iterables
        of (wire_idx, SlotPayload). Caller is responsible for filling empty
        slots with hud_protocol.EMPTY_SLOT — the wire is sender-dense."""
        self._in_burst = True
        try:
            self._hud_client.send_device(device_name)
            if page_info is not None:
                enc_page, enc_total, btn_page, btn_total = page_info
                self._hud_client.send_page_info(enc_page, enc_total, btn_page, btn_total)
            count = 0
            for idx, p in dial_payloads:
                self._hud_client.send_slot('dial', idx, p.name, p.value, p.vmin, p.vmax)
                count += 1
            for idx, p in button_payloads:
                self._hud_client.send_slot('button', idx, p.name, p.value, p.vmin, p.vmax)
                count += 1
            self._hud_client.commit(count)
        finally:
            self._in_burst = False

    def device_update(self, device_name, real_parameters, info_text="", switch_entries=None, device_parameters=None, hud_layout=None, mode_labels=None, enc_page=1, enc_total=1, btn_page=1, btn_total=1):
        self._osc_client.send_message(f"/selected-device/name", [f"{device_name} [{info_text}]"])

        # HUD burst: suppress live UPDATE calls while we build the full snapshot.
        # `parameter_updated` reads `_in_burst`, so we set it before the loop.
        self._in_burst = True
        try:
            for i, pm in enumerate(real_parameters):
                self.parameter_updated(pm, i)
        finally:
            self._in_burst = False

        dial_payloads = self._build_dial_payloads(real_parameters, hud_layout)
        button_payloads = self._build_button_payloads(switch_entries, device_parameters, hud_layout)
        if mode_labels:
            dial_payloads = _overlay_labels(dial_payloads, mode_labels, 'dial')
            button_payloads = _overlay_labels(button_payloads, mode_labels, 'button')
        self.refresh_burst(device_name, dial_payloads, button_payloads,
                           page_info=(enc_page, enc_total, btn_page, btn_total))

        self._osc_client.send_message(f"/selected-device/parameter-update-complete", [min(len(real_parameters), 16)])

    @staticmethod
    def _build_dial_payloads(real_parameters, hud_layout):
        """Dense dial payloads keyed on wire index. real_parameters[0] is
        Device On (skipped); wire idx N corresponds to real_parameters[N+1]."""
        payloads = []
        for cell in (hud_layout or []):
            _gr, _gc, kind, count, start = cell
            if kind != 'dial' or start < 0:
                continue
            for i in range(count):
                wire_idx = start + i
                rp_idx = wire_idx + 1
                if rp_idx < len(real_parameters):
                    pm = real_parameters[rp_idx]
                    p = pm.param
                    name = p.name if pm.alias is None else pm.alias
                    payloads.append((wire_idx, SlotPayload(name, p.value, p.min, p.max)))
                else:
                    payloads.append((wire_idx, EMPTY_SLOT))
        return payloads

    @staticmethod
    def _build_button_payloads(switch_entries, device_parameters, hud_layout):
        switch_by_idx = {e.switch_idx: e for e in (switch_entries or [])}
        payloads = []
        for cell in (hud_layout or []):
            _gr, _gc, kind, count, start = cell
            if kind != 'button' or start < 0:
                continue
            for i in range(count):
                wire_idx = start + i
                entry = switch_by_idx.get(wire_idx)
                if entry is not None and device_parameters:
                    try:
                        p = device_parameters[entry.d_idx]
                        payloads.append((wire_idx, SlotPayload(entry.alias or p.name, p.value, p.min, p.max)))
                        continue
                    except IndexError:
                        pass
                payloads.append((wire_idx, EMPTY_SLOT))
        return payloads


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
