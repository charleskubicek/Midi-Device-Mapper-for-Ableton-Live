from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent
from Launchpad.ConfigurableButtonElement import ConfigurableButtonElement
from .helpers import Helpers, Remote, SurfaceConfig
from .osc_client import OSCClient, OSCMultiClient, NullOSCClient
from .hud_client import HudClient, NullHudClient
from .ec4_client import Ec4Client, NullEc4Client
from .clip_actions import ClipActions
from .listener import OSCListener
from .region_state import RegionState
from .region_listener import RegionListener
from .mode_link import ModeSender, ModeListener
from .nav import Nav
# from _Framework.EncoderElement import *

functions_loaded_error = None

try:
    from .functions import Functions
except Exception as e:
    functions_loaded_error = e

class MainComponent(ControlSurfaceComponent):
    def __init__(self, manager):
        super().__init__(manager)
        self.class_identifier = "main_component"

        self.manager = manager

        self.mixer = MixerComponent(124, 24)
        # self.setup_controls()
        # self.setup_listeners()

        if functions_loaded_error is not None:
            self.log_message(f"Error loading functions: {functions_loaded_error}")
        else:
            self.functions = Functions(self)

        self._modes = {}
        # Default None so goto_mode's guards hold on surfaces with no physical
        # mode-button and on non-composition surfaces. The mode setup and the
        # MODE_LINK block below overwrite these when present.
        self.mode_button = None
        self._mode_sender = None
        self._song = self.manager.song()
        self._nav = Nav(self.manager)
        self.clip_actions = ClipActions(self.manager)

        self._osc_client = NullOSCClient()
        _osc_targets = [$osc_clients]
        if _osc_targets:
            self._osc_client = OSCMultiClient(_osc_targets)

        # HUD_TARGET is data, not code: None for a standalone surface (HUD on
        # 127.0.0.1:5006), or (host, port) for the parks forwarder which retargets
        # its HUD client at the compositor's region port.
        HUD_TARGET = $hud_target
        _hud_host, _hud_port = HUD_TARGET if HUD_TARGET is not None else ('127.0.0.1', 5006)
        self._hud_client = $hud_client_class(_hud_host, _hud_port)
        self._feedback_sinks = [$feedback_sinks]
        self._remote = Remote(self.manager, self._osc_client, self._hud_client, self._feedback_sinks)

        $code_setup

        code_slot_assignments = [
            $code_custom_parameter_mappings
        ]

        code_switch_slot_assignments = [
            $code_switch_parameter_mappings
        ]

        # Per-mode device bindings so the HUD resolves only the active mode's
        # device slots (a slot device-bound in one mode otherwise shows stale
        # device data in a mode where it is mixer/empty-bound).
        code_slot_assignments_by_mode = $code_slot_assignments_by_mode
        code_switch_slot_assignments_by_mode = $code_switch_slot_assignments_by_mode

        self._helpers = Helpers(self.manager, self._remote, SurfaceConfig(
            slot_assignments=code_slot_assignments,
            switch_slot_assignments=code_switch_slot_assignments,
            slot_assignments_by_mode=code_slot_assignments_by_mode,
            switch_slot_assignments_by_mode=code_switch_slot_assignments_by_mode,
            pager_preview_mode=$code_pager_preview_mode,
            parameter_mappings_raw=$parameter_mappings_raw,
            encoder_slot_count=$encoder_slot_count,
            hud_cells=$hud_cells,
            mode_hud_labels=$mode_hud_labels,
            hud_trigger=$hud_trigger,
            button_behaviour=$button_behaviour))

        self._song.add_appointed_device_listener(self.on_device_selected)
        # A device *replace* (e.g. Wavetable → Drift) doesn't reliably fire the
        # appointed-device listener, so also observe the selected track and its
        # device chain. The devices-list observer fires on any add/remove/replace
        # and re-bursts against the live device; it is re-attached whenever the
        # selected track changes.
        self._devices_listener_track = None
        self._song.view.add_selected_track_listener(self.on_selected_track_changed)
        self._attach_track_devices_listener()


        self.log_message(f"main_component finish init.")
        self._previous_values = {}

        self._lisetenr = OSCListener(self.manager, self.button_handler, port=$osc_listen_port, name="$surface_name")

        # Compositor only: receive the secondary surface's forwarded HUD region
        # and merge it into this surface's single combined HUD stream. The wiring
        # is real (always present, syntax-checked) and gated on REGION_CONFIG —
        # data, not a code string built in gen.py. None for standalone surfaces.
        REGION_CONFIG = $region_config
        if REGION_CONFIG is not None:
            self._region_state = RegionState(self._hud_client,
                dial_offset=REGION_CONFIG['dial_offset'],
                button_offset=REGION_CONFIG['button_offset'],
                on_commit=self._helpers.reemit_combined_burst)
            self._remote.set_region_state(self._region_state)
            self._region_listener = RegionListener(self.manager, self._region_state,
                port=REGION_CONFIG['port'], name="$surface_name-region")

        # Reverse mode channel (lc_parks only): the primary sends the active mode
        # name to the secondary so holding shift on the primary switches the
        # secondary's mappings too. Data, not code; None on standalone surfaces.
        # role='sender' -> primary (this surface owns a shift mode-button);
        # role='listener' -> secondary (headless FSM driven remotely).
        MODE_LINK = $mode_link
        if MODE_LINK is not None:
            if MODE_LINK['role'] == 'sender':
                self._mode_sender = ModeSender('127.0.0.1', MODE_LINK['port'])
            else:
                self._mode_listener = ModeListener(self.manager, self,
                    port=MODE_LINK['port'], name="$surface_name-mode")

        self._song.view.add_selected_parameter_listener(self._on_selected_parameter_changed)

        # Dismiss the HUD when the user navigates away from the device (browser,
        # Session/Arrangement switch, leaving the device chain). We over-index on
        # hiding: only a fresh device burst re-shows the HUD. Callbacks are
        # directional so they can't race our own show burst.
        self._app_view = Live.Application.get_application().view
        self._register_app_view_listeners()

    def _register_app_view_listeners(self):
        try:
            self._app_view.add_focused_document_view_listener(self._on_doc_view_changed)
        except Exception as e:
            self.log_message(f"HUD dismiss: failed to add focused_document_view listener: {e}")
        try:
            self._app_view.add_is_view_visible_listener('Browser', self._on_browser_visibility_changed)
        except Exception as e:
            self.log_message(f"HUD dismiss: failed to add Browser visibility listener: {e}")
        try:
            self._app_view.add_is_view_visible_listener('Detail/DeviceChain', self._on_detail_changed)
        except Exception as e:
            self.log_message(f"HUD dismiss: failed to add Detail/DeviceChain visibility listener: {e}")

    def _attach_track_devices_listener(self):
        """Observe the selected track's device chain so a device *replace*
        (Wavetable → Drift) — which doesn't reliably fire the appointed-device
        listener — still re-bursts. Idempotent: detaches the previous track's
        observer first, so repeated calls (e.g. on every track change) don't
        stack listeners."""
        self._teardown_track_devices_listener()
        try:
            track = self._song.view.selected_track
        except Exception:
            track = None
        if track is None:
            return
        try:
            track.add_devices_listener(self._on_track_devices_changed)
            self._devices_listener_track = track
        except Exception as e:
            self.log_message(f"HUD: failed to add devices listener: {e}")

    def _teardown_track_devices_listener(self):
        track = getattr(self, '_devices_listener_track', None)
        if track is None:
            return
        try:
            track.remove_devices_listener(self._on_track_devices_changed)
        except Exception:
            pass
        self._devices_listener_track = None

    def _on_track_devices_changed(self):
        # Device chain changed (add/remove/replace). Re-resolve the focused
        # device and funnel through selected_device_changed; its fail-open guard
        # treats a now-dead previous handle as changed and re-bursts for the live
        # device.
        self.fine(f"[listener] _on_track_devices_changed dev={getattr(self.selected_device(),'name',None)!r}")
        self._helpers.selected_device_changed(self.selected_device())

    def remove_app_view_listeners(self):
        self._teardown_track_devices_listener()
        try:
            self._song.view.remove_selected_track_listener(self.on_selected_track_changed)
        except Exception:
            pass
        try:
            self._app_view.remove_focused_document_view_listener(self._on_doc_view_changed)
        except Exception:
            pass
        try:
            self._app_view.remove_is_view_visible_listener('Browser', self._on_browser_visibility_changed)
        except Exception:
            pass
        try:
            self._app_view.remove_is_view_visible_listener('Detail/DeviceChain', self._on_detail_changed)
        except Exception:
            pass

    def _on_doc_view_changed(self):
        # Session <-> Arrangement switch. Device selection never changes this, so
        # an unconditional hide can't race our show burst. Note: Live emits this
        # redundantly (several times per change); HIDE is idempotent so that's fine.
        self.fine("[appview] _on_doc_view_changed -> hud_view_left")
        self._helpers.hud_view_left()

    def _on_browser_visibility_changed(self):
        # Hide only when the browser becomes visible (the user opened it). Fires
        # on show/hide toggle only — clicking into an already-open browser is not
        # observable in the Live API, so that case won't dismiss.
        try:
            visible = self._app_view.is_view_visible('Browser')
            self.fine(f"[appview] _on_browser_visibility_changed visible={visible}")
            if visible:
                self._helpers.hud_view_left()
        except Exception as e:
            self.log_message(f"HUD dismiss: Browser visibility check failed: {e}")

    def _on_detail_changed(self):
        # Hide only when the device chain becomes hidden. Selecting a device makes
        # it visible, so this won't fire a hide on selection.
        try:
            visible = self._app_view.is_view_visible('Detail/DeviceChain')
            self.fine(f"[appview] _on_detail_changed device_chain_visible={visible}")
            if not visible:
                self._helpers.hud_view_left()
        except Exception as e:
            self.log_message(f"HUD dismiss: Detail/DeviceChain visibility check failed: {e}")

    def button_handler(self, button, send_value):
        value = 127 if send_value > 0.0 else 0

        self._helpers.device_parameter_action(self.selected_device(), button, -1, value, '<OSC Button Press>')

    def remove_all_listeners(self, modes_only=False):
        $code_remove_listeners

    def debug(self):
        return self.manager.debug

    def update_selected_device(self):
        self._helpers.selected_device_changed(self.selected_device())

    def setup_controls(self):
        $code_creation

    def _on_selected_parameter_changed(self):
        if self.manager.debug:
            param = self._song.view.selected_parameter
            if param is not None:
                if param.is_quantized:
                    items = ", items: " +", ".join(param.value_items)
                else:
                    items = ""
                self.log_message(f"Selected parameter changed:  {param.name} (value: {param.value}, min: {param.min}, max: {param.max}, is_quantized: {param.is_quantized}{items})")
            else:
                self.log_message("Selected parameter changed: None")

$code_setup_listeners

    def log_message(self, message):
        self.manager.log_message(message)

    def fine(self, message):
        # Gated protocol-trace channel:
        # silent unless `manager.fine` is on (toggle with `update.py hudtrace`).
        # Delegates to Helpers.fine so all `[hudtrace]` lines share one gate/tag.
        self._helpers.fine(message)

    def selected_device(self):
        return self._song.view.selected_track.view.selected_device

    # device-nav handlers pass source='nav' so the HUD shows even under
    # show-hud-on='controller-nav'. track-nav keeps the default 'selection'
    # source (silent in controller-nav mode, per the show-hud-on contract).
    # Each nav method logs the focused device name before and after the _nav
    # call, so a [hudtrace] capture shows whether Live's appointed-device
    # listener fired synchronously inside scroll_view: if it did,
    # on_device_selected's line lands *between* these two (single-threaded
    # log order = execution order), which matters because that ordering
    # decides whether selected_device_changed's same-device guard sees the
    # nav call or the listener call first.
    def device_nav_left(self):
        self.fine(f"[nav] device_nav_left enter dev={getattr(self.selected_device(),'name',None)!r}")
        self._nav.device_nav_left()
        self.fine(f"[nav] device_nav_left post-scroll dev={getattr(self.selected_device(),'name',None)!r} source=nav")
        self._helpers.selected_device_changed(self.selected_device(), source='nav')

    def device_nav_right(self):
        self.fine(f"[nav] device_nav_right enter dev={getattr(self.selected_device(),'name',None)!r}")
        self._nav.device_nav_right()
        self.fine(f"[nav] device_nav_right post-scroll dev={getattr(self.selected_device(),'name',None)!r} source=nav")
        self._helpers.selected_device_changed(self.selected_device(), source='nav')

    def track_nav_inc(self):
        self.fine(f"[nav] track_nav_inc enter dev={getattr(self.selected_device(),'name',None)!r}")
        self._nav.track_nav_inc()
        self.fine(f"[nav] track_nav_inc post-scroll dev={getattr(self.selected_device(),'name',None)!r} source=selection")
        self._helpers.selected_device_changed(self.selected_device())

    def track_nav_dec(self):
        self.fine(f"[nav] track_nav_dec enter dev={getattr(self.selected_device(),'name',None)!r}")
        self._nav.track_nav_dec()
        self.fine(f"[nav] track_nav_dec post-scroll dev={getattr(self.selected_device(),'name',None)!r} source=selection")
        self._helpers.selected_device_changed(self.selected_device())

    def device_nav_first_last(self):
        self._nav.device_nav_first_last()

    def device_nav_first(self):
        self.fine(f"[nav] device_nav_first enter dev={getattr(self.selected_device(),'name',None)!r}")
        self._nav.device_nav_first()
        self.fine(f"[nav] device_nav_first post-scroll dev={getattr(self.selected_device(),'name',None)!r} source=nav")
        self._helpers.selected_device_changed(self.selected_device(), source='nav')

    def device_nav_last(self):
        self.fine(f"[nav] device_nav_last enter dev={getattr(self.selected_device(),'name',None)!r}")
        self._nav.device_nav_last()
        self.fine(f"[nav] device_nav_last post-scroll dev={getattr(self.selected_device(),'name',None)!r} source=nav")
        self._helpers.selected_device_changed(self.selected_device(), source='nav')

    $code_listener_fns

    def goto_mode(self, next_mode_name):
        self.log_message(f'switching to {next_mode_name}')
        next_mode = self._modes[next_mode_name]
        self.log_message(f'next mode: {next_mode}')
        self.remove_all_listeners(modes_only=True)
        self._modes[next_mode_name]['add_listeners_fn']()

        # The secondary of an lc_parks composition has modes but no physical
        # mode-button (its FSM is driven remotely via mode_link), so guard the
        # LED feedback.
        if self.mode_button is not None:
            if next_mode['color'] is not None:
                self.mode_button.send_value(next_mode['color'])
            else:
                self.mode_button.send_value(0)

        self.current_mode = next_mode

        # HUD: refresh labels for the new mode's bindings (mixer/functions/etc.).
        # Device-bound slots are repopulated by the next selected_device_changed.
        # Trace the order of refresh_hud_for_mode -> send_mode -> mode_sender:
        # a stray MODE/HIDE interleave here is order-dependent, so a [hudtrace]
        # capture needs to see these three sends in the order they actually fire.
        self.fine(f"[mode] goto_mode {next_mode_name!r} is_shift={next_mode['is_shift']} -> refresh_hud_for_mode")
        self._helpers.refresh_hud_for_mode(next_mode_name, self.selected_device())

        self.fine(f"[mode] goto_mode {next_mode_name!r} -> send_mode({next_mode['is_shift']})")
        self._hud_client.send_mode(next_mode['is_shift'])

        # Compositor primary only: forward the active mode name to the secondary
        # so holding shift on the primary also switches the secondary's mappings.
        if self._mode_sender is not None:
            self._mode_sender.send_mode(next_mode['name'])

        self.manager.show_message(f'Switched to {next_mode_name}')

    def device_parameter_action(self, device, parameter_no, midi_no, value, fn_name, toggle=False):
        self._helpers.device_parameter_action(device, parameter_no, midi_no, value, fn_name, toggle)

    def find_device(self, track_name, device_name):
        return self._helpers.find_device(self._song, track_name, device_name)


    def mode_button_listener(self, value):
        self.log_message(f'mode_button_listener: {value}, current mode is {self.current_mode}')

        if value == 127:# and self._modes[current_mode['next_mode_name']]['is_shift'] is not True:
            self.fine(f"[mode] mode_button_listener value=127 branch=press cur={self.current_mode['name']!r}")
            self.goto_mode(self.current_mode['next_mode_name'])
        elif value == 0 and self.current_mode['is_shift']:
            # Shift release: goto_mode (which sends send_mode(next.is_shift)) is
            # immediately followed by an explicit send_mode(False), so the HUD
            # briefly sees the wrong MODE value between the two sends. Trace
            # both in order so a [hudtrace] capture can confirm the interleave.
            self.fine(f"[mode] mode_button_listener value=0 branch=shift-release cur={self.current_mode['name']!r}")
            self.goto_mode(self.current_mode['next_mode_name'])
            self.fine("[mode] mode_button_listener shift-release -> send_mode(False)")
            self._hud_client.send_mode(False)

    def on_device_selected(self):
        # Live's appointed_device listener. If this line lands between a nav
        # method's enter/post-scroll lines, scroll_view fired it synchronously,
        # racing selected_device_changed's same-device guard. source defaults
        # to 'selection'.
        self.fine(f"[listener] on_device_selected dev={getattr(self.selected_device(),'name',None)!r}")
        self._helpers.selected_device_changed(self.selected_device())

    def on_selected_track_changed(self):
        ### This is called when the selected track changes
        self.fine(f"[listener] on_selected_track_changed dev={getattr(self.selected_device(),'name',None)!r}")
        # Follow the new track's device chain (see _attach_track_devices_listener).
        self._attach_track_devices_listener()
        self._helpers.selected_device_changed(self.selected_device())