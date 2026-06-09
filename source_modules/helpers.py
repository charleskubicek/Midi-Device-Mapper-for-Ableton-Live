from dataclasses import dataclass
from typing import Any, Optional

from .hud_client import HudClient, NullHudClient
from .hud_protocol import SlotPayload, EMPTY_SLOT, LayoutCell, PageInfo, BurstSnapshot
from .param_resolver import (
    ParameterResolver, RealParameter,
    M4L_CLASSES, _device_table_key, _build_device_table,
    _default_device_banks, _default_bank_names,
)
import logging

logger = logging.getLogger("helpers")


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
    d_idx: Optional[int] = None
    alias: str = ''
    payload: Optional[SlotPayload] = None  # set for LOM-kind entries


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


@dataclass
class SurfaceConfig:
    """Static per-surface configuration baked at codegen time. Groups the
    constructor inputs that used to be a dozen positional/keyword params on
    Helpers.__init__ so the generated template passes one object plus the two
    live collaborators (manager, remote). None means "use the runtime default"."""
    slot_assignments: Any = None
    switch_slot_assignments: Any = None
    parameter_mappings_raw: Any = None
    encoder_slot_count: int = 8
    button_slot_count: int = 8
    hud_cells: Any = None
    mode_hud_labels: Any = None
    device_banks: Any = None
    bank_names: Any = None
    hud_trigger: str = 'controller-nav'


class Helpers:
    def __init__(self, manager, remote, config: 'SurfaceConfig' = None, **legacy):
        # Back-compat: older call sites (and tests) pass the static config as
        # keyword args; bundle them into a SurfaceConfig. The generated template
        # passes a SurfaceConfig directly.
        if config is None:
            config = SurfaceConfig(**legacy)
        self._manager = manager
        self._remote = remote
        # show-hud-on trigger: 'selection' (HUD follows Live's selected device)
        # or 'controller-nav' (HUD only on controller device-nav actions).
        self._hud_trigger = config.hud_trigger
        self._slot_assignments = list(config.slot_assignments or [])
        self._switch_slot_assignments = list(config.switch_slot_assignments or [])
        self._encoder_slot_count = config.encoder_slot_count
        self._button_slot_count = config.button_slot_count
        # Generated surfaces bake hud_cells as plain tuples (see gen.py boundary);
        # re-wrap them as LayoutCells so the rest of the runtime gets named access.
        self._hud_cells = [LayoutCell.from_raw(c) for c in (config.hud_cells or [])]
        device_banks = config.device_banks if config.device_banks is not None else _default_device_banks()
        bank_names = config.bank_names if config.bank_names is not None else _default_bank_names()
        # 16-slot controllers pack two 8-param banks per page; 8-slot pack one.
        banks_per_page = 2 if config.encoder_slot_count >= 16 else 1
        # Number of distinct physical button switches: max switch number from assignments.
        # Used as the per-page stride when paging BOB buttons for known devices.
        button_switch_count = (
            max((int(slot.replace('switch', ''))
                 for _, slot in self._switch_slot_assignments), default=0)
            if self._switch_slot_assignments else 0
        )
        # Pure parameter-resolution + paging math lives in ParameterResolver
        # (no Live coupling). Helpers delegates to it (pass-throughs below); the
        # Live-coupled writes/listeners/messages stay here.
        self._resolver = ParameterResolver(
            device_table=_build_device_table(config.parameter_mappings_raw),
            device_banks=device_banks, bank_names=bank_names,
            banks_per_page=banks_per_page, button_switch_count=button_switch_count,
            button_slot_count=config.button_slot_count, log=self.log_message)
        # mode_hud_labels: {mode_name: {(kind, wire_idx): label}} for non-device
        # mappings. Device cells are populated from live device state and don't
        # appear here. _current_mode_name tracks which overlay is active.
        self._mode_hud_labels = config.mode_hud_labels or {}
        self._current_mode_name = None
        # Local HUD dismiss *intent* for the hud_toggle binding. The Swift side
        # auto-clears its sticky dismissed flag on every device/mode burst, so we
        # mirror that by resetting this to False at each burst emit site (see
        # update_remote_parameters / refresh_hud_for_mode). Otherwise the toggle
        # direction would invert after any device change.
        self._hud_dismissed = False
        self._remote.init_layout(self._hud_cells)
        self._last_selected_device = None
        self._group_selector_listeners = []  # [(param, callback)] for teardown

    def show_message(self, message):
        self._manager.show_message(message)

    def log_message(self, message):
        self._manager.log_message(message)

    # ---- ParameterResolver pass-throughs --------------------------------
    # Resolution + paging math moved to ParameterResolver (R9). These thin
    # delegators preserve the names the generated surfaces, the facade, and the
    # existing tests already call; new code can hit self._resolver directly.

    @property
    def _encoder_page(self):
        return self._resolver.encoder_page

    @_encoder_page.setter
    def _encoder_page(self, value):
        self._resolver.encoder_page = value

    @property
    def _button_page(self):
        return self._resolver.button_page

    @_button_page.setter
    def _button_page(self, value):
        self._resolver.button_page = value

    def has_user_defined_parameters(self, device):
        return self._resolver.has_user_defined_parameters(device)

    def _resolve_param_by_name(self, device, name):
        return self._resolver._resolve_param_by_name(device, name)

    def _standard_banks(self, device):
        return self._resolver._standard_banks(device)

    def _encoder_pages_count(self, device):
        return self._resolver._encoder_pages_count(device)

    def _button_pages_count(self, device):
        return self._resolver._button_pages_count(device)

    def _page_label_for(self, device, page):
        return self._resolver._page_label_for(device, page)

    def _resolve_encoder(self, device, c_idx):
        return self._resolver._resolve_encoder(device, c_idx)

    def _resolve_switch(self, device, switch_idx):
        return self._resolver._resolve_switch(device, switch_idx)

    def _lom_slot_payload(self, info):
        return self._resolver._lom_slot_payload(info)

    def selected_device_changed(self, device, source='selection'):
        if device is None or device == self._last_selected_device:
            return
        self._teardown_group_selector_listeners()
        self._last_selected_device = device
        # Reset the resolver's per-device state: name indices + paging back to 1.
        self._resolver.focus()
        self._attach_group_selector_listeners(device)
        self._log_device_focus(device)
        # show-hud-on gating: in 'controller-nav' mode only an explicit nav
        # action (source='nav') shows the HUD. Mouse / track-select selection
        # changes (source='selection', the 1.5s poll) still remap the encoders
        # and push OSC, but the HUD burst is suppressed. 'selection' mode (the
        # default) never suppresses.
        suppress_hud = (self._hud_trigger == 'controller-nav' and source != 'nav')
        self.update_remote_parameters(suppress_hud=suppress_hud)
        if self.has_user_defined_parameters(device):
            self.show_message(f"{device.class_name}")

    def _log_device_focus(self, device):
        """Single line at focus-change summarising what the runtime will and
        won't do for this device: BOB match? Standard banks? M4L collision?
        Reading this in tail_logs.sh tells you in one glance which branch of
        the resolver every subsequent knob/button event will hit."""
        cn = getattr(device, 'class_name', '?')
        dn = getattr(device, 'name', '?')
        key = _device_table_key(device)
        bob = self._resolver._device_entry(device) is not None
        banks = self._standard_banks(device)
        bank_count = len(banks) if banks else 0
        nparams = len(getattr(device, 'parameters', []) or [])
        is_m4l = cn in M4L_CLASSES
        m4l_note = ''
        if is_m4l and not bob:
            # List the M4L deviceNames present in the JSON for the same class
            # so a missing entry is obvious from the log alone.
            siblings = [k[1] for k in self._resolver.device_table.keys() if k[0] == cn]
            m4l_note = f" m4l_no_match available_deviceNames={siblings}"
        self.log_message(
            f"[focus] class={cn!r} name={dn!r} params={nparams} "
            f"bob={'yes' if bob else 'no'} key={key} "
            f"std_banks={bank_count}{m4l_note}"
        )

    def _attach_group_selector_listeners(self, device):
        for name in self._resolver.group_selector_names(device):
            selector = self._resolve_param_by_name(device, name)
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
        kind = info.get('kind', 'param')
        if kind == 'enum':
            self._cycle_enum_property(info['device'], info['prop'])
            self.update_remote_parameters()
            return
        if kind == 'bool':
            self._toggle_bool_property(info['device'], info['prop'])
            self.update_remote_parameters()
            return
        if kind == 'function':
            self._call_device_function(info['device'], info['fn'])
            return
        p = info['param']
        before = p.value
        is_q = getattr(p, 'is_quantized', False)
        self.log_message(f"[switch] resolved d_idx={info['d_idx']} alias={info.get('alias')} has_range={info['has_range']} json_min={info.get('min')} json_max={info.get('max')} min_max={info.get('min_max')} param.min={p.min} param.max={p.max} param.value={before} is_quantized={is_q}")
        if info.get('min_max'):
            steps = None
            if is_q:
                try:
                    steps = int(round(p.max)) - int(round(p.min)) + 1
                except (TypeError, ValueError):
                    steps = None
            if is_q and steps != 2:
                self.log_message(f"[switch] min_max requested on quantized param {info.get('alias')} with steps={steps} — skipping")
                return
            p.value = p.min
            p.value = p.max
            self.log_message(f"[switch] applied mode=min_max before={before} after={p.value}")
            return
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

    def _cycle_enum_property(self, device, prop):
        try:
            current = getattr(device, prop)
            members = self._resolver._enum_members(current, device, prop)
            if not members:
                self.log_message(f"[enum] no members discovered for {prop} on {device.class_name}")
                return
            idx = self._resolver._enum_index_of(members, current)
            nxt = members[(idx + 1) % len(members)]
            try:
                setattr(device, prop, nxt)
            except (TypeError, Exception):
                try:
                    setattr(device, prop, int(nxt))
                except Exception:
                    raise
            self.log_message(f"[enum] {device.class_name}.{prop}: {current} -> {nxt}")
        except Exception as ex:
            self.log_message(f"[enum] failed to cycle {prop} on {getattr(device,'class_name','?')}: {ex}")

    def _toggle_bool_property(self, device, prop):
        try:
            current = getattr(device, prop)
            setattr(device, prop, not current)
            self.log_message(f"[bool] {device.class_name}.{prop}: {current} -> {not current}")
        except Exception as ex:
            self.log_message(f"[bool] failed to toggle {prop} on {getattr(device,'class_name','?')}: {ex}")

    def _call_device_function(self, device, fn_name):
        try:
            fn = getattr(device, fn_name, None)
            if fn is None or not callable(fn):
                self.log_message(f"[fn] {device.class_name} has no callable {fn_name}")
                return
            fn()
            self.log_message(f"[fn] called {device.class_name}.{fn_name}()")
        except Exception as ex:
            self.log_message(f"[fn] failed to call {fn_name} on {getattr(device,'class_name','?')}: {ex}")

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
            self.log_message(f"[page] inc target={target} ignored: no focused device")
            return
        if target == 'encoder':
            enc_count = self._encoder_pages_count(device)
            btn_count = self._button_pages_count(device)
            changed = False
            if self._encoder_page < enc_count:
                self._encoder_page += 1
                changed = True
            if self._button_page < btn_count:
                self._button_page += 1
                changed = True
            self.log_message(
                f"[page] inc enc enc={self._encoder_page}/{enc_count} "
                f"btn={self._button_page}/{btn_count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )
            if changed:
                self.show_message(f"Enc page {self._encoder_page}/{enc_count}")
                self.update_remote_parameters()
        else:
            count = self._button_pages_count(device)
            changed = self._button_page < count
            if changed:
                self._button_page += 1
                self.show_message(f"Btn page {self._button_page}/{count}")
                self.update_remote_parameters()
            self.log_message(
                f"[page] inc btn btn={self._button_page}/{count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )

    def parameter_page_dec(self, target):
        device = self._last_selected_device
        if device is None:
            self.log_message(f"[page] dec target={target} ignored: no focused device")
            return
        if target == 'encoder':
            enc_count = self._encoder_pages_count(device)
            btn_count = self._button_pages_count(device)
            changed = False
            if self._encoder_page > 1:
                self._encoder_page -= 1
                changed = True
            if self._button_page > 1:
                self._button_page -= 1
                changed = True
            self.log_message(
                f"[page] dec enc enc={self._encoder_page}/{enc_count} "
                f"btn={self._button_page}/{btn_count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )
            if changed:
                self.show_message(f"Enc page {self._encoder_page}/{enc_count}")
                self.update_remote_parameters()
        else:
            count = self._button_pages_count(device)
            changed = self._button_page > 1
            if changed:
                self._button_page -= 1
                self.show_message(f"Btn page {self._button_page}/{count}")
                self.update_remote_parameters()
            self.log_message(
                f"[page] dec btn btn={self._button_page}/{count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )

    def update_remote_parameters(self, suppress_hud=False):
        device = self._last_selected_device
        if device is None:
            return
        on_off = ParameterMapping.on_off().with_real_param(device.parameters[0])
        real_params = [on_off]
        # Append unconditionally — a None placeholder for a failed resolve
        # keeps the wire-index alignment in `_build_dial_payloads`. Squashing
        # Nones here shifts every later encoder one slot left on the HUD.
        missing_c_idxs = []
        for c_idx, _slot in sorted(self._slot_assignments):
            rp = self._resolve_encoder(device, c_idx)
            real_params.append(rp)
            if rp is None:
                missing_c_idxs.append(c_idx)
        if missing_c_idxs:
            # One summary line per burst makes mis-resolved encoders trivial
            # to spot in tail_logs.sh — individual `[bank]`/`[bob]` lines
            # explain *why*, this line tells you *how many* and *which*.
            self.log_message(
                f"[burst] {getattr(device,'class_name','?')} "
                f"enc_page={self._encoder_page} unresolved_c_idxs={missing_c_idxs}"
            )
        switch_entries = []
        for wire_idx, slot in self._switch_slot_assignments:
            # slot_name ("switch1", "switch2", …) drives JSON-table parameter
            # resolution; wire_idx is the HUD button index assigned at codegen.
            logical_idx = int(slot.replace('switch', '')) - 1
            info = self._resolve_switch(device, logical_idx)
            if info is None:
                continue
            kind = info.get('kind', 'param')
            alias = info.get('alias') or ''
            if kind == 'param':
                switch_entries.append(SwitchSlotMapping(wire_idx, info['d_idx'], alias))
            else:
                payload = self._lom_slot_payload(info)
                if payload is not None:
                    switch_entries.append(SwitchSlotMapping(wire_idx, None, alias, payload))
        info_text = f"e{self._encoder_page}/b{self._button_page}"
        mode_labels = self._mode_hud_labels.get(self._current_mode_name)
        enc_total = self._encoder_pages_count(device)
        btn_total = self._button_pages_count(device)
        enc_label = self._page_label_for(device, self._encoder_page)
        btn_label = ''  # button pages don't use named banks
        self._remote.device_update(
            device.name, real_params, info_text, switch_entries, device.parameters,
            hud_layout=self._hud_cells, mode_labels=mode_labels,
            page=PageInfo(enc_page=self._encoder_page, enc_total=enc_total,
                          btn_page=self._button_page, btn_total=btn_total,
                          enc_label=enc_label, btn_label=btn_label),
            suppress_hud=suppress_hud,
        )
        if not suppress_hud:
            # A real burst clears the Swift sticky dismissed flag — re-sync intent.
            self._hud_dismissed = False
        else:
            # Suppressed (controller-nav mode, non-nav selection change). The
            # device_update above kept OSC + feedback sinks flowing but emitted
            # no HUD burst. We must also send HIDE: otherwise the next live
            # `send_update` (turning a knob) would wake the HUD — UPDATE is a
            # show path while the Swift `dismissed` flag is clear — and patch the
            # now-stale slots by index. HIDE sets the sticky flag so UPDATE/PING
            # can't resurrect it; the next device-nav burst clears it and
            # repaints fresh. Mirror the intent locally so hud_toggle re-syncs.
            self._remote.hide()
            self._hud_dismissed = True

    def reemit_combined_burst(self):
        """Compositor hook (lc_parks): the secondary region changed, so re-emit
        a full combined burst for the current device with the parks region
        appended. Bypasses the show-hud-on gate (always suppress_hud=False) and
        the same-device guard in selected_device_changed — otherwise the parks
        region would never reach the HUD under the primary's 'controller-nav'
        trigger or when the focused device is unchanged."""
        if self._last_selected_device is not None:
            self.update_remote_parameters(suppress_hud=False)

    def refresh_hud_for_mode(self, mode_name, device):
        """Called by the surface when goto_mode swaps bindings. Sets the
        active overlay and re-emits a burst so the HUD reflects the new
        labels for non-device cells. Device cells reuse the existing
        device-path data when a device is focused."""
        self._current_mode_name = mode_name
        if device is not None:
            self._last_selected_device = device
        self._emit_current_burst()

    def _emit_current_burst(self):
        """Re-emit the HUD burst for the active mode + focused device. If a
        device is focused, reuse the device path; otherwise emit a label-only
        burst. Either way the burst clears the Swift sticky dismissed flag, so
        intent is re-synced to False."""
        if self._last_selected_device is not None:
            self.update_remote_parameters()
        else:
            # No focused device yet — emit a label-only burst.
            mode_labels = self._mode_hud_labels.get(self._current_mode_name) or {}
            self._remote.device_update(
                '', [], info_text='', switch_entries=[], device_parameters=[],
                hud_layout=self._hud_cells, mode_labels=mode_labels,
            )
            self._hud_dismissed = False

    def toggle_hud(self):
        """Bound to a `functions: hud_toggle` button. Flips the HUD between
        hidden and shown. Hiding sends a sticky HIDE; showing re-emits the
        current burst (which clears the HIDE and repaints the active mode)."""
        self._hud_dismissed = not self._hud_dismissed
        if self._hud_dismissed:
            self._remote.hide()
        else:
            self._emit_current_burst()

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
    def __init__(self, manager, osc_client, hud_client=None, feedback_sinks=None):
        self._manager = manager
        self._osc_client = osc_client
        self._hud_client = hud_client if hud_client is not None else NullHudClient()
        # Generic feedback sinks (e.g. Ec4Client) driven off the same burst as
        # the HUD. The HUD keeps its own bespoke wire protocol; these consume
        # the dense dial/button payloads.
        self._feedback_sinks = list(feedback_sinks) if feedback_sinks else []
        self._in_burst = False  # suppresses UPDATE during device_update burst
        # Controller layout (HUD LAYOUT cells). Stored so every burst can re-emit
        # it: LAYOUT is otherwise a one-shot at surface init, and if the HUD app
        # starts/restarts AFTER the surface, it misses that single LAYOUT and
        # renders an empty grid. Re-emitting at the head of each burst makes the
        # HUD/Ableton startup order irrelevant.
        self._hud_cells = []
        # Optional secondary-region cache (lc_parks compositor). When set, its
        # cached dial/button payloads are appended to the HUD burst so the parks
        # region rides along in the single combined stream.
        self._region_state = None

    def set_region_state(self, region_state):
        self._region_state = region_state

    def init_layout(self, cells):
        # Remember the layout so every burst can re-emit it (restart-resilient),
        # and send it once now for the common case where the HUD is already up.
        self._hud_cells = [LayoutCell.from_raw(c) for c in cells] if cells else []
        if self._hud_cells:
            self._hud_client.send_layout(self._hud_cells)

    def hide(self):
        """Sticky-dismiss the HUD (HIDE). Stays hidden until the next burst."""
        self._hud_client.send_hide()

    #TODO unit tests datatypes sent
    def parameter_updated(self, real_param, parameter_no):
        param = real_param.param
        name = param.name if real_param.alias is None else real_param.alias
        self._osc_client.send_message(f"/selected-device/parameter-update",
                                      [parameter_no, param.value, name, param.min, param.max, real_param.button])
        # Live HUD update — skip on/off (index 0) and skip during the initial burst
        if parameter_no > 0 and not self._in_burst:
            self._hud_client.send_update('dial', parameter_no - 1, name, param.value, param.min, param.max)

    def refresh_burst(self, snapshot: BurstSnapshot):
        """Generic dense burst. `snapshot.dials` / `snapshot.buttons` are
        iterables of (wire_idx, SlotPayload). Caller is responsible for filling
        empty slots with hud_protocol.EMPTY_SLOT — the wire is sender-dense.

        snapshot.page is a PageInfo, or None to emit no PAGE line.

        snapshot.suppress_hud skips the HUD wire (show-hud-on='controller-nav'
        on a non-nav selection change). Feedback sinks (EC4 readouts) still fire
        — they reflect device state regardless of the HUD trigger."""
        self._in_burst = True
        try:
            if not snapshot.suppress_hud:
                # Re-emit LAYOUT at the head of the burst so a HUD that started
                # after the surface (and missed the one-shot init LAYOUT) still
                # gets a grid. The receiver stores it in pendingCells and
                # publishes on COMMIT; DEVICE clears pending slots but not cells.
                if self._hud_cells:
                    self._hud_client.send_layout(self._hud_cells)
                self._hud_client.send_device(snapshot.device_name)
                if snapshot.page is not None:
                    p = snapshot.page
                    self._hud_client.send_page_info(
                        p.enc_page, p.enc_total, p.btn_page, p.btn_total,
                        p.enc_label, p.btn_label)
                # Append the secondary region's cached slots (lc_parks). These
                # carry combined wire indices already; sent after the primary's
                # so any same-index empty placeholder is overridden on the
                # receiver (last-write-wins per index).
                hud_dials = list(snapshot.dials)
                hud_buttons = list(snapshot.buttons)
                if self._region_state is not None:
                    hud_dials += self._region_state.dial_payloads()
                    hud_buttons += self._region_state.button_payloads()

                count = 0
                for idx, p in hud_dials:
                    self._hud_client.send_slot('dial', idx, p.name, p.value, p.vmin, p.vmax)
                    count += 1
                for idx, p in hud_buttons:
                    self._hud_client.send_slot('button', idx, p.name, p.value, p.vmin, p.vmax)
                    count += 1
                self._hud_client.commit(count)
            # Fan the whole snapshot out to generic feedback sinks (EC4 readouts,
            # etc.). on_burst(snapshot) gives sinks room to grow; older sinks
            # implementing only on_device_burst are bridged for one release.
            for sink in self._feedback_sinks:
                try:
                    if hasattr(sink, 'on_burst'):
                        sink.on_burst(snapshot)
                    else:
                        sink.on_device_burst(snapshot.device_name,
                                             list(snapshot.dials), list(snapshot.buttons))
                except Exception as e:
                    # Surface log so a sink mismatch is visible in tail_logs.sh
                    # rather than silently swallowed during a burst.
                    try:
                        self._manager.log_message(
                            f"feedback sink {type(sink).__name__} failed: {e}")
                    except Exception:
                        logger.error(f"feedback sink {type(sink).__name__} failed: {e}")
        finally:
            self._in_burst = False

    def device_update(self, device_name, real_parameters, info_text="", switch_entries=None, device_parameters=None, hud_layout=None, mode_labels=None, page: PageInfo = None, suppress_hud=False):
        self._osc_client.send_message(f"/selected-device/name", [f"{device_name} [{info_text}]"])

        # HUD burst: suppress live UPDATE calls while we build the full snapshot.
        # `parameter_updated` reads `_in_burst`, so we set it before the loop.
        self._in_burst = True
        try:
            for i, pm in enumerate(real_parameters):
                if pm is None:
                    continue
                self.parameter_updated(pm, i)
        finally:
            self._in_burst = False

        dial_payloads = self._build_dial_payloads(real_parameters, hud_layout)
        button_payloads = self._build_button_payloads(switch_entries, device_parameters, hud_layout)
        if mode_labels:
            dial_payloads = _overlay_labels(dial_payloads, mode_labels, 'dial')
            button_payloads = _overlay_labels(button_payloads, mode_labels, 'button')
        self.refresh_burst(BurstSnapshot(
            device_name, dial_payloads, button_payloads,
            page=page if page is not None else PageInfo(),
            suppress_hud=suppress_hud))

        self._osc_client.send_message(f"/selected-device/parameter-update-complete", [min(len(real_parameters), 16)])

    @staticmethod
    def _build_dial_payloads(real_parameters, hud_layout):
        """Dense dial payloads keyed on wire index. real_parameters[0] is
        Device On (skipped); wire idx N corresponds to real_parameters[N+1]."""
        payloads = []
        for cell in map(LayoutCell.from_raw, hud_layout or []):
            if cell.kind != 'dial' or cell.start < 0:
                continue
            count, start = cell.count, cell.start
            for i in range(count):
                wire_idx = start + i
                rp_idx = wire_idx + 1
                if rp_idx < len(real_parameters):
                    pm = real_parameters[rp_idx]
                    if pm is None:
                        payloads.append((wire_idx, EMPTY_SLOT))
                        continue
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
        for cell in map(LayoutCell.from_raw, hud_layout or []):
            if cell.kind != 'button' or cell.start < 0:
                continue
            count, start = cell.count, cell.start
            for i in range(count):
                wire_idx = start + i
                entry = switch_by_idx.get(wire_idx)
                if entry is not None:
                    if entry.payload is not None:
                        payloads.append((wire_idx, entry.payload))
                        continue
                    if entry.d_idx is not None and device_parameters:
                        try:
                            p = device_parameters[entry.d_idx]
                            payloads.append((wire_idx, SlotPayload(entry.alias or p.name, p.value, p.min, p.max)))
                            continue
                        except IndexError:
                            pass
                payloads.append((wire_idx, EMPTY_SLOT))
        return payloads
