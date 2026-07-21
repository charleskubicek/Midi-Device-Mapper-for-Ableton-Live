"""HUD burst assembly + HUD show/hide intent, extracted from Helpers.

`HudPresenter` turns the focused device (resolved via `ParameterResolver`) into
a HUD/feedback burst on `Remote`, and owns the local mirror of the Swift sticky
"dismissed" flag plus the active mode-label overlay. It does no Live writes and
holds no manager/song — Helpers passes it the focused device on each call.

Show/hide intent is owned by the `HudVisibility` table: the presenter
fires events (`DeviceFocus`, `ModeChange`, `ClipViewChanged`, `ViewLeft`,
`RegionCommit`) and acts on the returned `Decision`; the `dismissed` flag only
changes inside `HudVisibility.apply`. The hud_toggle button is HUD-arbitrated
(see `toggle`) and does not fire a table event.
"""
from .param_resolver import ParameterMapping, SwitchSlotMapping, _device_alive
from .hud_protocol import PageInfo, IDLE_DISMISS_SECONDS
from .hud_visibility import (
    HudVisibility, Decision, DeviceFocus, ModeChange, ViewLeft, RegionCommit,
    ClipViewChanged,
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
        # Gated protocol-trace sink; no-op by default so unit tests and
        # pre-flag surfaces stay silent.
        self._fine = fine or (lambda msg: None)
        # Single owner of show/hide intent. Its `dismissed` flag mirrors
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
        # The focused device may have been deleted/replaced (e.g. Wavetable →
        # Drift): its Boost handle is dead and every attribute read below
        # (`device.name`, `device.parameters`) would raise ArgumentError and
        # abort the burst — which propagates up and, historically, left the HUD
        # permanently dead. Drop the now-stale HUD and bail; the devices-listener
        # funnel re-bursts against the live device.
        if not _device_alive(device):
            self._fine("[burst] emit_burst skipped: dead/removed device handle")
            self._remote.hide()
            return
        # Single source of truth: if this burst is for a device the funnel never
        # reset (a bypassed selection path), drop the stale name index + paging
        # here so the burst can't inherit the previous device's page/index.
        self._resolver.ensure_focused(device)
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
        # Zone colour tints apply only to a zoned device, but then to EVERY
        # template slot — an unmapped/dim slot still shows its zone hue (colour
        # is a template property, not tied to what resolved).
        zoned = self._resolver.is_zoned(device)
        on_off = ParameterMapping.on_off().with_real_param(device.parameters[0])
        real_params = [on_off]
        # dial_zone_colors is kept parallel to real_params (index 0 = Device On
        # = no tint), so `_build_zone_color_entries` can index it exactly like
        # the dial payloads.
        dial_zone_colors = [None]
        # Append unconditionally — a None placeholder for a failed resolve
        # keeps the wire-index alignment in `_build_dial_payloads`. Squashing
        # Nones here shifts every later encoder one slot left on the HUD.
        missing_c_idxs = []
        for c_idx, _slot in sorted(self._active_slot_assignments(burst_mode)):
            rp = self._resolver.resolve_encoder(device, c_idx)
            real_params.append(rp)
            dial_zone_colors.append(
                self._resolver.color_for_slot('dial', c_idx) if zoned else None)
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
        button_zone_colors = {}
        for wire_idx, slot in self._active_switch_slot_assignments(burst_mode):
            # slot is a 1-based device switch-slot int; it drives JSON-table
            # parameter resolution. wire_idx is the HUD button index assigned
            # at codegen.
            # Tint by zone before resolving — an unmapped button still shows its
            # zone hue (dim), so the colour must not depend on info being non-None.
            if zoned:
                c = self._resolver.color_for_slot('button', slot)
                if c:
                    button_zone_colors[wire_idx] = c
            logical_idx = slot - 1
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
            dial_zone_colors=dial_zone_colors,
            button_zone_colors=button_zone_colors,
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
        # No idle-sync here: no DeviceFocus rule reads `dismissed` (summon
        # selection is unconditionally EMIT_SILENT_AND_HIDE, nav is always
        # EMIT_BURST), so the mirror-drift guard is a no-op on this path. It
        # still matters for ModeChange (see refresh_for_mode).
        decision = self._visibility.decide(DeviceFocus(source))
        self.emit_burst(device, suppress_hud=(decision is Decision.EMIT_SILENT_AND_HIDE))

    def on_device_focus_lost(self, source):
        """Focus moved to a device-less track (track-nav onto an empty / return /
        master / fresh track — `view.selected_device` is None). Route the
        focus-loss through the visibility table and hide only when it decides
        EMIT_SILENT_AND_HIDE. No burst, no resolver: there is nothing to resolve.

        - summon / controller-nav: DeviceFocus('selection') -> EMIT_SILENT_AND_HIDE
          -> HIDE goes out, mirror syncs, a summoned HUD stops freezing on the
          previous device (hud-hide-on-empty-track).
        - selection (incl. the forced lc_parks compositor): -> EMIT_BURST, but
          with nothing to burst it is a deliberate no-op — a HIDE here would race
          the parks-driven combined COMMIT.
        - source='nav' landing on nothing: -> EMIT_BURST -> also a no-op (a nav
          that lands on nothing shows nothing)."""
        self._fine(f"[focus] on_device_focus_lost source={source}")
        if self._visibility.decide(DeviceFocus(source)) is Decision.EMIT_SILENT_AND_HIDE:
            self._fine("[focus] -> remote.hide() (focus lost, nothing to burst)")
            self._remote.hide()

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
            # Honour the clip-view gate: while a clip is open RegionCommit
            # classifies to EMIT_SILENT_AND_HIDE, so the combined burst is
            # suppressed (OSC/sinks still flow, HUD wire skipped + HIDE) rather
            # than re-showing over the clip editor.
            decision = self._visibility.decide(RegionCommit())
            self.emit_burst(device, suppress_hud=(decision is Decision.EMIT_SILENT_AND_HIDE))

    def refresh_for_mode(self, mode_name, device):
        """Called by the surface when goto_mode swaps bindings. Sets the active
        overlay and re-emits a burst so the HUD reflects the new labels for
        non-device cells. The visibility table decides whether this repaints the
        HUD or only feeds the sinks silently — under `summon` a mode press must
        not summon a hidden HUD, so the ModeChange decision is routed into
        suppress_hud exactly like on_device_focus (a `selection`/`controller-nav`
        surface still classifies ModeChange to EMIT_BURST and shows)."""
        self._current_mode_name = mode_name
        # Same mirror-drift guard as on_device_focus: after an idle hide, a mode
        # press must not re-summon a hidden HUD under `summon`.
        self._sync_idle_dismiss()
        decision = self._visibility.decide(ModeChange())
        self.emit_current_burst(
            device, suppress_hud=(decision is Decision.EMIT_SILENT_AND_HIDE))

    def clip_view_changed(self, visible):
        """Detail/Clip flipped visibility. Opening hides the HUD and gates later
        selection/mode/region bursts; closing clears the gate without re-showing.
        Routes through the table so the dismiss mirror stays in sync with the
        Swift sticky flag. (The browser and other non-device views are handled by
        the Swift input monitor now, not by per-view listeners.)"""
        if self._visibility.decide(ClipViewChanged(visible)) is Decision.HIDE:
            self._fine("[clipview] -> remote.hide()")
            self._remote.hide()

    def emit_current_burst(self, device, suppress_hud=False):
        """Re-emit the HUD burst for the active mode + focused device. If a
        device is focused, reuse the device path; otherwise emit a label-only
        burst. When not suppressed the burst clears the Swift sticky dismissed
        flag; when suppressed it sends HIDE + sets the flag, mirroring
        emit_burst's own suppress branch."""
        if device is not None:
            self.emit_burst(device, suppress_hud=suppress_hud)
        else:
            # No focused device yet — emit a label-only burst.
            mode_labels = self._mode_hud_labels.get(self._current_mode_name) or {}
            self._remote.device_update(
                '', [], info_text='', switch_entries=[], device_parameters=[],
                hud_layout=self._hud_cells, mode_labels=mode_labels,
                suppress_hud=suppress_hud,
            )
            if suppress_hud:
                self._remote.hide()
                self._visibility.apply(Decision.EMIT_SILENT_AND_HIDE)
            else:
                self._visibility.apply(Decision.EMIT_BURST)

    def toggle(self, device):
        """Bound to a `functions: hud_toggle` button. A true toggle, arbitrated
        by the HUD: Python cannot track the HUD's visibility (it hides
        autonomously via the Swift idle timer and the input monitor), so a
        Python-side flip mis-fires. Instead we send a TOGGLE marker + a fresh
        burst; the HUD hides if it was visible, or shows the fresh data if it
        wasn't (see DeviceState arbitration). One press, every time, for every
        trigger. Our local `dismissed` mirror is best-effort after this — the
        HUD is the source of truth."""
        self._remote.send_toggle()
        self.emit_current_burst(device)

    def _sync_idle_dismiss(self):
        """Mirror-drift fix: the Swift idle timer sticky-dismisses the overlay on
        its own (no back-channel), so our `dismissed` mirror can wrongly read
        `shown` after an idle hide. If nothing has been sent for longer than the
        shared idle window, the Swift timer has fired — sync the mirror to
        dismissed so a following ModeChange under summon stays silent instead of
        re-summoning a HUD the idle timer already hid (refresh_for_mode). Keyed
        on real send activity (burst/UPDATE/PING) so knob traffic that keeps the
        Swift timer alive also keeps this mirror shown."""
        if self._visibility.dismissed:
            return
        idle = self._remote.seconds_since_last_hud_send()
        # Contract is float | None (None = nothing sent yet). Guard on the type,
        # not just `is not None`, so anything unmeasurable simply skips the sync.
        if isinstance(idle, (int, float)) and idle > IDLE_DISMISS_SECONDS:
            self._fine(f"[idle-sync] idle {idle:.1f}s > {IDLE_DISMISS_SECONDS}s -> sync dismissed")
            self._visibility.apply(Decision.HIDE)
