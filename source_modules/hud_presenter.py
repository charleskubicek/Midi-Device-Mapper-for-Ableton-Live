"""HUD burst assembly + HUD show/hide intent, extracted from Helpers (R9).

`HudPresenter` turns the focused device (resolved via `ParameterResolver`) into
a HUD/feedback burst on `Remote`, and owns the local mirror of the Swift sticky
"dismissed" flag plus the active mode-label overlay. It does no Live writes and
holds no manager/song — Helpers passes it the focused device on each call.

R10 will replace the inline suppress/HIDE branching in `emit_burst` with the
table-driven HudVisibility decision object; the seams here are kept aligned with
that work (emit_burst's suppress_hud arg is the one show/hide knob).
"""
from .param_resolver import ParameterMapping, SwitchSlotMapping
from .hud_protocol import PageInfo


class HudPresenter:
    def __init__(self, remote, resolver, slot_assignments, switch_slot_assignments,
                 hud_cells, mode_hud_labels, log):
        self._remote = remote
        self._resolver = resolver
        self._slot_assignments = slot_assignments
        self._switch_slot_assignments = switch_slot_assignments
        self._hud_cells = hud_cells
        # mode_hud_labels: {mode_name: {(kind, wire_idx): label}} for non-device
        # mappings. Device cells are populated from live device state and don't
        # appear here. _current_mode_name tracks which overlay is active.
        self._mode_hud_labels = mode_hud_labels or {}
        self._current_mode_name = None
        self._log = log
        # Local HUD dismiss *intent* for the hud_toggle binding. The Swift side
        # auto-clears its sticky dismissed flag on every device/mode burst, so we
        # mirror that by resetting this to False at each burst emit site.
        # Otherwise the toggle direction would invert after any device change.
        self._hud_dismissed = False

    @property
    def hud_dismissed(self):
        return self._hud_dismissed

    @hud_dismissed.setter
    def hud_dismissed(self, value):
        self._hud_dismissed = value

    def emit_burst(self, device, suppress_hud=False):
        if device is None:
            return
        on_off = ParameterMapping.on_off().with_real_param(device.parameters[0])
        real_params = [on_off]
        # Append unconditionally — a None placeholder for a failed resolve
        # keeps the wire-index alignment in `_build_dial_payloads`. Squashing
        # Nones here shifts every later encoder one slot left on the HUD.
        missing_c_idxs = []
        for c_idx, _slot in sorted(self._slot_assignments):
            rp = self._resolver._resolve_encoder(device, c_idx)
            real_params.append(rp)
            if rp is None:
                missing_c_idxs.append(c_idx)
        if missing_c_idxs:
            # One summary line per burst makes mis-resolved encoders trivial
            # to spot in tail_logs.sh — individual `[bank]`/`[bob]` lines
            # explain *why*, this line tells you *how many* and *which*.
            self._log(
                f"[burst] {getattr(device,'class_name','?')} "
                f"enc_page={self._resolver.encoder_page} unresolved_c_idxs={missing_c_idxs}"
            )
        switch_entries = []
        for wire_idx, slot in self._switch_slot_assignments:
            # slot_name ("switch1", "switch2", …) drives JSON-table parameter
            # resolution; wire_idx is the HUD button index assigned at codegen.
            logical_idx = int(slot.replace('switch', '')) - 1
            info = self._resolver._resolve_switch(device, logical_idx)
            if info is None:
                continue
            kind = info.get('kind', 'param')
            alias = info.get('alias') or ''
            if kind == 'param':
                switch_entries.append(SwitchSlotMapping(wire_idx, info['d_idx'], alias))
            else:
                payload = self._resolver._lom_slot_payload(info)
                if payload is not None:
                    switch_entries.append(SwitchSlotMapping(wire_idx, None, alias, payload))
        info_text = f"e{self._resolver.encoder_page}/b{self._resolver.button_page}"
        mode_labels = self._mode_hud_labels.get(self._current_mode_name)
        enc_total = self._resolver._encoder_pages_count(device)
        btn_total = self._resolver._button_pages_count(device)
        enc_label = self._resolver._page_label_for(device, self._resolver.encoder_page)
        btn_label = ''  # button pages don't use named banks
        self._remote.device_update(
            device.name, real_params, info_text, switch_entries, device.parameters,
            hud_layout=self._hud_cells, mode_labels=mode_labels,
            page=PageInfo(enc_page=self._resolver.encoder_page, enc_total=enc_total,
                          btn_page=self._resolver.button_page, btn_total=btn_total,
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

    def reemit_combined_burst(self, device):
        """Compositor hook (lc_parks): the secondary region changed, so re-emit
        a full combined burst for the current device with the parks region
        appended. Bypasses the show-hud-on gate (always suppress_hud=False) and
        the same-device guard in selected_device_changed — otherwise the parks
        region would never reach the HUD under the primary's 'controller-nav'
        trigger or when the focused device is unchanged."""
        if device is not None:
            self.emit_burst(device, suppress_hud=False)

    def refresh_for_mode(self, mode_name, device):
        """Called by the surface when goto_mode swaps bindings. Sets the
        active overlay and re-emits a burst so the HUD reflects the new
        labels for non-device cells. Device cells reuse the existing
        device-path data when a device is focused."""
        self._current_mode_name = mode_name
        self.emit_current_burst(device)

    def emit_current_burst(self, device):
        """Re-emit the HUD burst for the active mode + focused device. If a
        device is focused, reuse the device path; otherwise emit a label-only
        burst. Either way the burst clears the Swift sticky dismissed flag, so
        intent is re-synced to False."""
        if device is not None:
            self.emit_burst(device)
        else:
            # No focused device yet — emit a label-only burst.
            mode_labels = self._mode_hud_labels.get(self._current_mode_name) or {}
            self._remote.device_update(
                '', [], info_text='', switch_entries=[], device_parameters=[],
                hud_layout=self._hud_cells, mode_labels=mode_labels,
            )
            self._hud_dismissed = False

    def toggle(self, device):
        """Bound to a `functions: hud_toggle` button. Flips the HUD between
        hidden and shown. Hiding sends a sticky HIDE; showing re-emits the
        current burst (which clears the HIDE and repaints the active mode)."""
        self._hud_dismissed = not self._hud_dismissed
        if self._hud_dismissed:
            self._remote.hide()
        else:
            self.emit_current_burst(device)
