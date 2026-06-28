"""HUD burst assembly + HUD show/hide intent, extracted from Helpers (R9).

`HudPresenter` turns the focused device (resolved via `ParameterResolver`) into
a HUD/feedback burst on `Remote`, and owns the local mirror of the Swift sticky
"dismissed" flag plus the active mode-label overlay. It does no Live writes and
holds no manager/song — Helpers passes it the focused device on each call.

Show/hide intent is owned by the `HudVisibility` table (R10): the presenter
fires events (`DeviceFocus`, `ModeChange`, `UserToggle`, `ViewLeft`,
`RegionCommit`) and acts on the returned `Decision`; the `dismissed` flag only
changes inside `HudVisibility.apply`.
"""
from .param_resolver import ParameterMapping, SwitchSlotMapping
from .hud_protocol import PageInfo
from .hud_visibility import (
    HudVisibility, Decision, DeviceFocus, ModeChange, UserToggle, ViewLeft, RegionCommit,
)


class HudPresenter:
    def __init__(self, remote, resolver, slot_assignments, switch_slot_assignments,
                 hud_cells, mode_hud_labels, log, hud_trigger='controller-nav',
                 slot_assignments_by_mode=None, switch_slot_assignments_by_mode=None,
                 fine=None):
        self._remote = remote
        self._resolver = resolver
        # Flat global assignments (union across modes) — the fallback used by
        # modeless surfaces and before the first goto_mode. The *_by_mode dicts
        # carry the per-mode device bindings so a burst resolves only the
        # encoders/switches that are device-bound in the *active* mode; anything
        # else falls through to EMPTY and the mode's static labels overlay it.
        self._slot_assignments = slot_assignments
        self._switch_slot_assignments = switch_slot_assignments
        self._slot_assignments_by_mode = slot_assignments_by_mode or {}
        self._switch_slot_assignments_by_mode = switch_slot_assignments_by_mode or {}
        self._hud_cells = hud_cells
        # mode_hud_labels: {mode_name: {(kind, wire_idx): label}} for non-device
        # mappings. Device cells are populated from live device state and don't
        # appear here. _current_mode_name tracks which overlay is active.
        self._mode_hud_labels = mode_hud_labels or {}
        self._current_mode_name = None
        self._log = log
        # Gated protocol-trace sink (hud-protocol-instrumentation-plan); no-op by
        # default so unit tests and pre-flag surfaces stay silent.
        self._fine = fine or (lambda msg: None)
        # Single owner of show/hide intent (R10). Its `dismissed` flag mirrors
        # the Swift sticky-dismiss flag; a real burst clears it. Shares the trace
        # sink so the decide() line interleaves with the presenter's own lines.
        self._visibility = HudVisibility(hud_trigger, fine=self._fine)

    @property
    def hud_dismissed(self):
        return self._visibility.dismissed

    @hud_dismissed.setter
    def hud_dismissed(self, value):
        self._visibility.dismissed = value

    def _active_slot_assignments(self, mode_name=None):
        """Device encoder assignments for the given mode (defaults to the active
        mode), falling back to the flat global list when the mode isn't keyed
        (modeless / pre-goto_mode)."""
        mn = self._current_mode_name if mode_name is None else mode_name
        if mn in self._slot_assignments_by_mode:
            return self._slot_assignments_by_mode[mn]
        return self._slot_assignments

    def _active_switch_slot_assignments(self, mode_name=None):
        """Device switch assignments for the given mode, same fallback rule."""
        mn = self._current_mode_name if mode_name is None else mode_name
        if mn in self._switch_slot_assignments_by_mode:
            return self._switch_slot_assignments_by_mode[mn]
        return self._switch_slot_assignments

    def emit_burst(self, device, suppress_hud=False, preview_mode_name=None):
        if device is None:
            return
        # Page-preview (parameter-pager pressed from a shift mode): resolve this
        # one burst against the *base* mode's device bindings so the user sees the
        # new page's params, while staying in shift (current mode + visibility
        # untouched). One-shot — the next normal burst overwrites it. No-op when
        # the preview target is already the active mode.
        burst_mode = (preview_mode_name
                      if (preview_mode_name is not None
                          and preview_mode_name != self._current_mode_name)
                      else self._current_mode_name)
        self._fine(
            f"[burst] emit_burst device={getattr(device, 'name', None)!r} "
            f"suppress_hud={suppress_hud} mode={self._current_mode_name!r} "
            f"burst_mode={burst_mode!r}"
        )
        on_off = ParameterMapping.on_off().with_real_param(device.parameters[0])
        real_params = [on_off]
        # Append unconditionally — a None placeholder for a failed resolve
        # keeps the wire-index alignment in `_build_dial_payloads`. Squashing
        # Nones here shifts every later encoder one slot left on the HUD.
        missing_c_idxs = []
        for c_idx, _slot in sorted(self._active_slot_assignments(burst_mode)):
            rp = self._resolver.resolve_encoder(device, c_idx)
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
        for wire_idx, slot in self._active_switch_slot_assignments(burst_mode):
            # slot_name ("switch1", "switch2", …) drives JSON-table parameter
            # resolution; wire_idx is the HUD button index assigned at codegen.
            logical_idx = int(slot.replace('switch', '')) - 1
            info = self._resolver.resolve_switch(device, logical_idx)
            if info is None:
                continue
            kind = info.get('kind', 'param')
            alias = info.get('alias') or ''
            if kind == 'param':
                switch_entries.append(SwitchSlotMapping(wire_idx, info['d_idx'], alias))
            else:
                payload = self._resolver.lom_slot_payload(info)
                if payload is not None:
                    switch_entries.append(SwitchSlotMapping(wire_idx, None, alias, payload))
        info_text = f"e{self._resolver.encoder_page}/b{self._resolver.button_page}"
        mode_labels = self._mode_hud_labels.get(burst_mode)
        enc_total = self._resolver.encoder_pages_count(device)
        btn_total = self._resolver.button_pages_count(device)
        enc_label = self._resolver.page_label_for(device, self._resolver.encoder_page)
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
            self._visibility.apply(Decision.EMIT_BURST)
        else:
            # Suppressed (controller-nav mode, non-nav selection change). The
            # device_update above kept OSC + feedback sinks flowing but emitted
            # no HUD burst. We must also send HIDE: otherwise the next live
            # `send_update` (turning a knob) would wake the HUD — UPDATE is a
            # show path while the Swift `dismissed` flag is clear — and patch the
            # now-stale slots by index. HIDE sets the sticky flag so UPDATE/PING
            # can't resurrect it; the next device-nav burst clears it and
            # repaints fresh. Mirror the intent locally so hud_toggle re-syncs.
            self._fine("[burst] -> remote.hide() (suppressed selection)")
            self._remote.hide()
            self._visibility.apply(Decision.EMIT_SILENT_AND_HIDE)

    def on_device_focus(self, device, source):
        """A device became focused (source 'nav' | 'selection'). The single
        visibility table decides whether this shows the HUD or only feeds the
        OSC/feedback sinks while staying hidden (controller-nav on a non-nav
        selection). Replaces the inline suppress rule that lived in Helpers."""
        self._fine(f"[focus] on_device_focus device={getattr(device, 'name', None)!r} source={source}")
        decision = self._visibility.decide(DeviceFocus(source))
        self.emit_burst(device, suppress_hud=(decision is Decision.EMIT_SILENT_AND_HIDE))

    def view_left(self):
        """App-view listeners (doc-view switch, browser opened, detail hidden)
        forward here instead of calling send_hide() directly, so the local
        dismiss mirror stays in sync with the Swift sticky flag."""
        if self._visibility.decide(ViewLeft()) is Decision.HIDE:
            self._fine("[viewleft] -> remote.hide()")
            self._remote.hide()

    def reemit_combined_burst(self, device):
        """Compositor hook (lc_parks): the secondary region changed, so re-emit
        a full combined burst for the current device with the parks region
        appended. A RegionCommit is a real burst — it bypasses the show-hud-on
        gate and the same-device guard in selected_device_changed, otherwise
        the parks region would never reach the HUD under the primary's
        'controller-nav' trigger or when the focused device is unchanged."""
        if device is not None:
            self._visibility.decide(RegionCommit())
            self.emit_burst(device, suppress_hud=False)

    def refresh_for_mode(self, mode_name, device):
        """Called by the surface when goto_mode swaps bindings. Sets the
        active overlay and re-emits a burst so the HUD reflects the new
        labels for non-device cells. Device cells reuse the existing
        device-path data when a device is focused. A mode change always shows
        the HUD, even after a view-left dismiss (ModeChange -> EMIT_BURST)."""
        self._current_mode_name = mode_name
        self._visibility.decide(ModeChange())
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
            self._visibility.apply(Decision.EMIT_BURST)

    def toggle(self, device):
        """Bound to a `functions: hud_toggle` button. Flips the HUD between
        hidden and shown via the visibility table: hiding sends a sticky HIDE;
        showing re-emits the current burst (clears the HIDE, repaints)."""
        if self._visibility.decide(UserToggle()) is Decision.HIDE:
            self._remote.hide()
        else:
            self.emit_current_burst(device)
