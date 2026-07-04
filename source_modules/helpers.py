from dataclasses import dataclass
from typing import Any, Optional

from .hud_client import HudClient, NullHudClient
from .hud_protocol import SlotPayload, EMPTY_SLOT, LayoutCell, PageInfo, BurstSnapshot
from .param_resolver import (
    ParameterResolver, RealParameter, ParameterMapping, SwitchSlotMapping,
    M4L_CLASSES, _device_table_key, _build_device_table,
    _default_device_banks, _default_bank_names,
)
from .hud_presenter import HudPresenter
from .doctor import Doctor
from .show_info import ShowInfo
import logging

logger = logging.getLogger("helpers")


def _safe_param_fields(param, alias):
    """Read (name, value, min, max) off a live device parameter, tolerating a
    dead Boost.Python handle. The new Operator rebuilds its parameter list in
    place, so a reference resolved a moment ago can already be freed — any
    attribute access then raises `Boost.Python.ArgumentError`. The resolver now
    hands back live handles (see ParameterResolver._live_param); this is the
    last-line net so one un-readable param degrades to an empty/skipped slot
    instead of aborting the whole burst (which propagates up and crashes the
    mode switch). Returns None when the handle can't be read."""
    try:
        name = param.name if alias is None else alias
        return (name, param.value, param.min, param.max)
    except Exception:
        return None


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
    # Per-mode device encoder / switch assignments ({mode_name: [(idx, slot)]}).
    # The HUD presenter resolves only the active mode's device bindings so a slot
    # device-bound in one mode doesn't show stale device data in another.
    slot_assignments_by_mode: Any = None
    switch_slot_assignments_by_mode: Any = None
    # Base mode whose device page is previewed on the HUD when the parameter-pager
    # is pressed from a mode that doesn't show the device encoders (e.g. paging
    # while holding shift). None when there's no distinct base device mode.
    pager_preview_mode: Any = None
    parameter_mappings_raw: Any = None
    encoder_slot_count: int = 8
    button_slot_count: int = 8
    hud_cells: Any = None
    mode_hud_labels: Any = None
    device_banks: Any = None
    bank_names: Any = None
    hud_trigger: str = 'controller-nav'
    # 'momentary' (default) or 'toggle' — how this controller's buttons report a
    # press (see ButtonBehaviour). Drives the press-once edge guard.
    button_behaviour: str = 'momentary'


class Helpers:
    def __init__(self, manager, remote, config: 'SurfaceConfig' = None, **legacy):
        # Back-compat: older call sites (and tests) pass the static config as
        # keyword args; bundle them into a SurfaceConfig. The generated template
        # passes a SurfaceConfig directly.
        if config is None:
            config = SurfaceConfig(**legacy)
        self._manager = manager
        self._remote = remote
        # Generated surfaces bake hud_cells as plain tuples (see gen.py boundary);
        # re-wrap them as LayoutCells so the rest of the runtime gets named access.
        hud_cells = [LayoutCell.from_raw(c) for c in (config.hud_cells or [])]
        slot_assignments = list(config.slot_assignments or [])
        switch_slot_assignments = list(config.switch_slot_assignments or [])
        device_banks = config.device_banks if config.device_banks is not None else _default_device_banks()
        bank_names = config.bank_names if config.bank_names is not None else _default_bank_names()
        # 16-slot controllers pack two 8-param banks per page; 8-slot pack one.
        banks_per_page = 2 if config.encoder_slot_count >= 16 else 1
        # Number of distinct physical button switches: max switch slot number from
        # assignments. Used as the per-page stride when paging BOB buttons for
        # known devices.
        button_switch_count = (
            max((slot for _, slot in switch_slot_assignments), default=0)
            if switch_slot_assignments else 0
        )
        # Pure parameter-resolution + paging math lives in ParameterResolver
        # (no Live coupling); HUD burst assembly + show/hide intent live in
        # HudPresenter (no Live writes). The Live-coupled writes/listeners/
        # messages stay here on the facade.
        self._resolver = ParameterResolver(
            device_table=_build_device_table(config.parameter_mappings_raw),
            device_banks=device_banks, bank_names=bank_names,
            banks_per_page=banks_per_page, button_switch_count=button_switch_count,
            button_slot_count=config.button_slot_count, log=self.log_message)
        self._presenter = HudPresenter(
            remote=remote, resolver=self._resolver,
            slot_assignments=slot_assignments,
            switch_slot_assignments=switch_slot_assignments,
            slot_assignments_by_mode=config.slot_assignments_by_mode,
            switch_slot_assignments_by_mode=config.switch_slot_assignments_by_mode,
            hud_cells=hud_cells,
            mode_hud_labels=config.mode_hud_labels or {},
            log=self.log_message, hud_trigger=config.hud_trigger,
            fine=self.fine)
        self._remote.init_layout(hud_cells)
        self._last_selected_device = None
        self._group_selector_listeners = []  # [(param, callback)] for teardown
        self._button_behaviour = config.button_behaviour
        self._pager_preview_mode = config.pager_preview_mode
        # Button diagnostics, both off until their update.py command enables them.
        self._doctor = Doctor(log=self.log_message, assumed_behaviour=config.button_behaviour)
        self._show_info = ShowInfo(
            send_event=lambda kind, idx, text: self._remote._hud_client.send_event(kind, idx, text),
            log=self.log_message)

    def should_act_on_edge(self, value):
        """Whether this raw MIDI button edge is a distinct *press* that should act
        once. Parameterised on the controller's hardware button mode so a
        press-once button works on both:

        - 'toggle' hardware sends one alternating on/off event per press, so
          *every* edge is its own press → always act.
        - 'momentary' hardware sends on-then-0 per press, so only the non-zero
          down is a press; the 0 release is suppressed.

        Continuous knobs/sliders never call this (they are not press-once)."""
        if self._button_behaviour == 'toggle':
            return True
        return value != 0

    def button_event(self, fn_name, value, wire_idx=-1):
        """Single chokepoint every generated *button* listener calls (continuous
        knobs/sliders do not). Fans out to the diagnostics that care about raw
        button edges: the hardware doctor and HUD show-info."""
        self._doctor.observe(fn_name, value)
        self._show_info.notify(fn_name, value, wire_idx)

    def doctor_toggle(self):
        """Toggle doctor mode; when turning off, emit the classification report."""
        was_enabled = self._doctor.enabled
        self._doctor.toggle()
        if was_enabled:
            self._doctor.report()
        return self._doctor.enabled

    def show_info_toggle(self):
        """Toggle HUD show-info mode (edge-annotated button feedback)."""
        return self._show_info.toggle()

    def show_message(self, message):
        self._manager.show_message(message)

    def log_message(self, message):
        self._manager.log_message(message)

    def fine(self, message):
        """Gated protocol-trace channel (hud-protocol-instrumentation-plan).
        Silent unless the surface's `manager.fine` flag is on; every line is
        `[hudtrace]`-tagged so a captured trace is greppable in tail_logs.sh.
        Threaded into HudPresenter/HudVisibility the same way `log_message` is."""
        if getattr(self._manager, 'fine', False):
            self._manager.log_message(f"[hudtrace] {message}")

    def selected_device_changed(self, device, source='selection'):
        # THE funnel: both device_nav_* and on_device_selected pass through here,
        # and the same-device guard below is where Bug 1's nav-then-listener race
        # is decided. Trace device + source + whether the guard short-circuited so
        # a captured HIDE can be attributed to its cause.
        dev_name = getattr(device, 'name', None)
        if device is None or device == self._last_selected_device:
            self.fine(
                f"[funnel] selected_device_changed device={dev_name!r} source={source} "
                f"guard=short-circuit ({'none' if device is None else 'same-device'})"
            )
            return
        self.fine(
            f"[funnel] selected_device_changed device={dev_name!r} source={source} "
            f"guard=pass prev={getattr(self._last_selected_device, 'name', None)!r}"
        )
        self._teardown_group_selector_listeners()
        self._last_selected_device = device
        # Reset the resolver's per-device state (name indices + paging) before
        # re-attaching group-selector listeners, which resolve against the fresh
        # index. ensure_focused records the device so the burst-side guard in
        # emit_burst is a no-op on this same-device path.
        self._resolver.ensure_focused(device)
        self._attach_group_selector_listeners(device)
        self._log_device_focus(device)
        # show-hud-on gating now lives in the HudVisibility table (R10): in
        # 'controller-nav' mode only an explicit nav action shows the HUD; a
        # selection-poll change still remaps encoders + pushes OSC but the HUD
        # burst is suppressed (and HIDE sent). 'selection' mode never suppresses.
        self._presenter.on_device_focus(device, source)
        if self._resolver.has_user_defined_parameters(device):
            self.show_message(f"{device.class_name}")

    def _log_device_focus(self, device):
        """Single line at focus-change summarising what the runtime will and
        won't do for this device: BOB match? Standard banks? M4L collision?
        Reading this in tail_logs.sh tells you in one glance which branch of
        the resolver every subsequent knob/button event will hit."""
        cn = getattr(device, 'class_name', '?')
        dn = getattr(device, 'name', '?')
        key = _device_table_key(device)
        bob = self._resolver.device_entry(device) is not None
        banks = self._resolver.standard_banks(device)
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
            selector = self._resolver.resolve_param_by_name(device, name)
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
        rp = self._resolver.resolve_encoder(device, raw_parameter_no)
        if rp is None:
            self.log_message(f"{fn_name}: encoder {raw_parameter_no} not resolvable on {device.class_name}")
            return
        parameter = rp.param
        # For a latching button (toggle=True) act once per *press*; the edge
        # guard handles momentary vs toggle hardware. Continuous knobs
        # (toggle=False) always apply.
        will_fire = not toggle or self.should_act_on_edge(value)
        if toggle:
            next_value = parameter.max if parameter.value == parameter.min else parameter.min
        else:
            next_value = self.normalise(value, parameter.min, parameter.max)
        if will_fire:
            parameter.value = next_value
            self._remote.parameter_updated(rp, raw_parameter_no)

    def switch_slot_action(self, device, slot, value, fn_name):
        """`slot` is a 1-based device switch-slot index (int)."""
        self.log_message(f"[switch] enter fn={fn_name} slot={slot} value={value} device={getattr(device,'class_name','None')}")
        if device is None:
            return
        self.selected_device_changed(device)
        switch_idx = slot - 1
        info = self._resolver.resolve_switch(device, switch_idx)
        if info is None:
            self.log_message(f"[switch] {slot} not resolvable on {device.class_name}")
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
            members = self._resolver.enum_members(current, device, prop)
            if not members:
                self.log_message(f"[enum] no members discovered for {prop} on {device.class_name}")
                return
            idx = self._resolver.enum_index_of(members, current)
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
            enc_count = self._resolver.encoder_pages_count(device)
            btn_count = self._resolver.button_pages_count(device)
            changed = False
            if self._resolver.encoder_page < enc_count:
                self._resolver.encoder_page += 1
                changed = True
            if self._resolver.button_page < btn_count:
                self._resolver.button_page += 1
                changed = True
            self.log_message(
                f"[page] inc enc enc={self._resolver.encoder_page}/{enc_count} "
                f"btn={self._resolver.button_page}/{btn_count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )
            if changed:
                self.show_message(f"Enc page {self._resolver.encoder_page}/{enc_count}")
                self.update_remote_parameters(preview_mode_name=self._pager_preview_mode)
        else:
            count = self._resolver.button_pages_count(device)
            changed = self._resolver.button_page < count
            if changed:
                self._resolver.button_page += 1
                self.show_message(f"Btn page {self._resolver.button_page}/{count}")
                self.update_remote_parameters(preview_mode_name=self._pager_preview_mode)
            self.log_message(
                f"[page] inc btn btn={self._resolver.button_page}/{count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )

    def parameter_page_dec(self, target):
        device = self._last_selected_device
        if device is None:
            self.log_message(f"[page] dec target={target} ignored: no focused device")
            return
        if target == 'encoder':
            enc_count = self._resolver.encoder_pages_count(device)
            btn_count = self._resolver.button_pages_count(device)
            changed = False
            if self._resolver.encoder_page > 1:
                self._resolver.encoder_page -= 1
                changed = True
            if self._resolver.button_page > 1:
                self._resolver.button_page -= 1
                changed = True
            self.log_message(
                f"[page] dec enc enc={self._resolver.encoder_page}/{enc_count} "
                f"btn={self._resolver.button_page}/{btn_count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )
            if changed:
                self.show_message(f"Enc page {self._resolver.encoder_page}/{enc_count}")
                self.update_remote_parameters(preview_mode_name=self._pager_preview_mode)
        else:
            count = self._resolver.button_pages_count(device)
            changed = self._resolver.button_page > 1
            if changed:
                self._resolver.button_page -= 1
                self.show_message(f"Btn page {self._resolver.button_page}/{count}")
                self.update_remote_parameters(preview_mode_name=self._pager_preview_mode)
            self.log_message(
                f"[page] dec btn btn={self._resolver.button_page}/{count} changed={changed} "
                f"class={getattr(device,'class_name','?')}"
            )

    def update_remote_parameters(self, suppress_hud=False, preview_mode_name=None):
        # Burst assembly lives in HudPresenter; Helpers owns the focused device.
        # preview_mode_name (parameter-pager only) previews a base mode's device
        # page while staying in the current mode; the presenter no-ops it when it
        # equals the active mode.
        self._presenter.emit_burst(self._last_selected_device, suppress_hud=suppress_hud,
                                   preview_mode_name=preview_mode_name)

    def reemit_combined_burst(self):
        """Compositor hook (lc_parks): re-emit a full combined burst for the
        current device with the parks region appended. See
        HudPresenter.reemit_combined_burst."""
        self._presenter.reemit_combined_burst(self._last_selected_device)

    def refresh_hud_for_mode(self, mode_name, device):
        """Called by the surface when goto_mode swaps bindings. Sets the active
        overlay and re-emits a burst so the HUD reflects the new labels."""
        # A bare assignment is safe for the reported index/paging staleness:
        # refresh_for_mode -> emit_current_burst -> emit_burst runs the resolver's
        # ensure_focused guard, which resets a stale index/page for a changed
        # device. (Residual: on a mode+device change together this skips
        # group-selector listener re-attach until the next real selection —
        # tracked as a follow-up, not part of the reported bug.)
        if device is not None:
            self._last_selected_device = device
        self._presenter.refresh_for_mode(mode_name, self._last_selected_device)

    def toggle_hud(self):
        """Bound to a `functions: hud_toggle` button. Flips the HUD between
        hidden and shown."""
        self._presenter.toggle(self._last_selected_device)

    def hud_view_left(self):
        """The generated surface's app-view listeners (doc-view switch, browser
        opened, detail hidden) forward here. Routes through the HudVisibility
        table so the dismiss mirror stays in sync with the Swift sticky flag."""
        self._presenter.view_left()

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
        fields = _safe_param_fields(param, real_param.alias)
        if fields is None:
            # Dead Live handle — skip this slot loudly rather than abort the burst.
            try:
                self._manager.log_message(
                    f"[deadparam] skipped parameter_no={parameter_no}: unreadable Live handle")
            except Exception:
                logger.error(f"[deadparam] skipped parameter_no={parameter_no}")
            return
        name, value, pmin, pmax = fields
        self._osc_client.send_message(f"/selected-device/parameter-update",
                                      [parameter_no, value, name, pmin, pmax, real_param.button])
        # Live HUD update — skip on/off (index 0) and skip during the initial burst
        if parameter_no > 0 and not self._in_burst:
            self._hud_client.send_update('dial', parameter_no - 1, name, value, pmin, pmax)

    def refresh_burst(self, snapshot: BurstSnapshot):
        """Generic dense burst. `snapshot.dials` / `snapshot.buttons` are
        iterables of (wire_idx, SlotPayload). Caller is responsible for filling
        empty slots with hud_protocol.EMPTY_SLOT — the wire is sender-dense.

        snapshot.page is a PageInfo, or None to emit no PAGE line.

        snapshot.suppress_hud skips the HUD wire (show-hud-on='controller-nav'
        on a non-nav selection change). Feedback sinks (EC4 readouts) still fire
        — they reflect device state regardless of the HUD trigger."""
        self._in_burst = True
        # Buffer the whole burst into one datagram so it lands atomically: a
        # dropped datagram loses the entire burst (HUD stays on the last good
        # device) rather than dropping a lone DEVICE frame and publishing the new
        # device's slots under the previous device's name. See
        # hud-burst-datagram-atomicity-plan.
        self._hud_client.begin_burst()
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
            self._hud_client.flush_burst()
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
                    fields = _safe_param_fields(pm.param, pm.alias)
                    if fields is None:
                        payloads.append((wire_idx, EMPTY_SLOT))
                        continue
                    name, value, vmin, vmax = fields
                    payloads.append((wire_idx, SlotPayload(name, value, vmin, vmax)))
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
                        except IndexError:
                            p = None
                        if p is not None:
                            fields = _safe_param_fields(p, entry.alias or None)
                            if fields is not None:
                                name, value, vmin, vmax = fields
                                payloads.append((wire_idx, SlotPayload(name, value, vmin, vmax)))
                                continue
                payloads.append((wire_idx, EMPTY_SLOT))
        return payloads
