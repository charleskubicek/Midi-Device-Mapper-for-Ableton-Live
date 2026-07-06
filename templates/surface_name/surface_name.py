import errno
from pathlib import Path

import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
# from _Framework.EncoderElement import *

import importlib
import socket
import traceback

from . import modules
from .modules import main_component
from .modules import helpers
from .modules.listener import OSCListener
from .modules import hud_arbiter

try:
    from .modules import functions
except ImportError:
    pass

class $surface_name(ControlSurface):
    def __init__(self, c_instance):
        super($surface_name, self).__init__(c_instance)

        # HUD-owner election markers. Sibling surfaces read these off
        # `self._control_surfaces` (Ableton's shared
        # cross-script registry) to decide who owns the shared HUD sink at
        # 127.0.0.1:5006 -- set immediately after super().__init__ (which is
        # where ControlSurface publishes `self` into that registry) so the
        # window where we're registered but unmarked is as small as possible.
        self._acsac_hud_enabled = $hud_mode_on
        self._acsac_surface_name = "$surface_name"

        self.ops = None
        self.log_message("$surface_name custom script loaded")


        with self.component_guard():

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self.log_message("$surface_name: starting listen on port $udp_port")
            self._socket.bind(('0.0.0.0', $udp_port))

            self.init_modules()

            # Elect a single HUD owner among all co-loaded HUD-enabled
            # surfaces. Re-runs on every control_surfaces change so ownership
            # self-heals as surfaces load/unload.
            self._hud_arbiter = hud_arbiter.HudArbiter(self)
            self._hud_arbiter.register()

            self.schedule_message(1, self.tick)
            self.show_message("Connected to $surface_name")
            self.debug = False
            # Gated HUD protocol-trace flag.
            # Off by default; toggled by the `hudtrace` command. Read by
            # Helpers.fine to emit `[hudtrace]` lines for the HUD<->surface path.
            self.fine = False

            self.schedule_message(5, self.update_main_component_with_selected_device)
            # Re-election runs on a recurring tick, not just the
            # control_surfaces observer registered above: that observer's
            # method name is Live-API-guessed and unverifiable outside a real
            # Ableton session, and it fails silently (logged + swallowed) if
            # wrong. The observer gives near-instant ownership transfer when
            # it works; this loop is the guarantee that ownership still
            # converges (within ~1.5s) even if it doesn't -- correctness must
            # not depend on an assumption we can't test.
            self.schedule_message(10, self._hud_arbiter_tick)

    def _hud_arbiter_tick(self):
        self._hud_arbiter.reelect()
        fifteen_ticks = 15
        self.schedule_message(fifteen_ticks, self._hud_arbiter_tick)

    def update_main_component_with_selected_device(self):
        self.main_component.update_selected_device()
        one_and_a_half_seconds = 15
        self.schedule_message(one_and_a_half_seconds, self.update_main_component_with_selected_device)

    def functions_file_exsits(self):
        return (Path(__file__).resolve().parent / 'functions.py').exists()

    def init_modules(self):

        self.main_component = main_component.MainComponent(self)
        self.main_component.setup_controls()

    def dump_selected_device_parameter_names(self):
        device = self.song().view.selected_track.view.selected_device
        if not device:
            self.log_message("No device selected")
            return

        self.log_message("Dumping parameters for device; name:" + device.name+", class_name: " + device.class_name)

        params_formated = "\n            - ".join([p.original_name for p in device.parameters])

        res = f"""\n
    -
        device-name: {device.name}
        parameters:
            - {params_formated}
"""
        self.log_message(res)


    def dump_selected_device_parameter_info(self):
        device = self.song().view.selected_track.view.selected_device
        if not device:
            self.log_message("No device selected")
            return


        self.log_message("Dumping parameters for device; name:" + device.name+", class_name: " + device.class_name)
        parameters = []

        for i, p in enumerate(device.parameters):
            i = str(i).zfill(2)
            msg = {
                'no': i,
                'original_name': p.original_name,
                'display_name': p.name,
                'value': p.value,
                'min': p.min,
                'max': p.max
            }
            parameters.append(msg)

        result_obj = { "class_name" : device.class_name,"name": device.name,  "parameters": parameters }
        self.log_message('\n' + str(result_obj).replace('\n', ' '))

        string_params = [f"""{{"no": {i}, "name": "{p.original_name}", "min": {p.min}, "max": {p.max}}}""" for i, p in enumerate(device.parameters)]
        joined = ",\n        ".join(string_params)

        res = f"""    {{
        "id": "{device.class_name}",
        "name": "{device.name}",
        "parameters": [
        {joined}        
        ]}}"""

        self.log_message(res)

    def dump_selected_device_parameter_info_split_into_encoders_and_buttons(self):
        device = self.song().view.selected_track.view.selected_device
        if not device:
            self.log_message("No device selected")
            return


        self.log_message("Dumping parameters for device; name:" + device.name+", class_name: " + device.class_name)
        encoders = []
        buttons = []

        for i, p in enumerate(device.parameters):
            msg = {
                'no': i,
                'name': p.original_name,
            }

            if p.is_quantized:
                buttons.append(msg)
            else:
                encoders.append(msg)

        result_obj = { "class_name" : device.class_name,"name": device.name,  "encoders": encoders }
        self.log_message('\n' + str(result_obj).replace('\n', ' '))

        string_enc_params = [f"""{{"name": "{p['name']}"}}""" for i, p in enumerate(encoders)]
        joined_encoders = ",\n          ".join(string_enc_params)

        string_button_params = [f"""{{"name": "{p['name']}"}}""" for i, p in enumerate(buttons)]
        joined_buttons = ",\n          ".join(string_button_params)

        res = f"""    
    {{
        "className": "{device.class_name}",
        "deviceName": "{device.name}",
        "encoders": [
          {joined_encoders}
        ],
        "buttons": [
          {joined_buttons}
        ]
    }}"""

        self.log_message(res)

    def dump_selected_device_lom(self):
        """Diagnostic dump of non-parameter LOM attributes on the selected
        device: properties, methods, and (especially) any enum-typed values
        with whatever introspection hooks they expose. Use this to figure
        out how to enumerate things like SimplerDevice.playback_mode."""
        device = self.song().view.selected_track.view.selected_device
        if not device:
            self.log_message("No device selected")
            return

        self.log_message(f"=== LOM dump for {device.class_name} ({device.name}) ===")
        self.log_message(f"device python type: {type(device)!r}")
        self.log_message(f"device mro: {[c.__name__ for c in type(device).__mro__]}")

        skip = {'parameters', 'canonical_parent'}
        props = []
        methods = []
        enums = []

        for attr in sorted(dir(device)):
            if attr.startswith('_') or attr in skip:
                continue
            try:
                val = getattr(device, attr)
            except Exception as ex:
                self.log_message(f"  [skip] {attr}: getattr raised {ex!r}")
                continue
            if callable(val):
                methods.append(attr)
                continue
            tname = type(val).__name__
            tmod = getattr(type(val), '__module__', '?')
            line = f"  {attr}: type={tmod}.{tname}  value={val!r}"
            props.append(line)
            # Heuristic: anything that isn't a plain primitive may be enum-like.
            if not isinstance(val, (int, float, bool, str, bytes, list, tuple, dict, type(None))):
                enums.append((attr, val))

        self.log_message("-- properties --")
        for line in props:
            self.log_message(line)

        self.log_message("-- methods --")
        self.log_message("  " + ", ".join(methods))

        self.log_message("-- enum-like introspection --")
        for attr, val in enums:
            cls = type(val)
            self.log_message(f"  {attr}: cls={cls.__module__}.{cls.__name__}")
            self.log_message(f"    repr(val)={val!r}  int_cast={self._safe_int(val)}")
            self.log_message(f"    dir(cls)={[d for d in dir(cls) if not d.startswith('_')]}")
            values = getattr(cls, 'values', None)
            self.log_message(f"    cls.values={values!r}  type={type(values).__name__}")
            try:
                it = list(cls)
                self.log_message(f"    list(cls)={it!r}")
            except Exception as ex:
                self.log_message(f"    list(cls) raised: {ex!r}")
            try:
                names = getattr(cls, 'names', None)
                self.log_message(f"    cls.names={names!r}")
            except Exception as ex:
                self.log_message(f"    cls.names raised: {ex!r}")

        self.log_message("=== end LOM dump ===")

    @staticmethod
    def _safe_int(v):
        try:
            return int(v)
        except Exception:
            return None

    def tick(self):
        # self.log_message(f"Ticking..")
        try:
            data, addr = self._socket.recvfrom(1024)
            cmd_str = data.decode('utf-8', errors='ignore').strip()
            parts = cmd_str.split('|')
            cmd = parts[0]
            response = None

            if cmd == 'PING':
                response = b'PONG'

            elif cmd == 'HELLO':
                self.main_component._remote.resend_layout()
                self.main_component._helpers.update_remote_parameters()

            elif cmd == 'GET_DEVICE':
                device = self.song().view.selected_track.view.selected_device
                if device:
                    n = len(device.parameters)
                    response = f'DEVICE|{device.class_name}|{device.name}|{n}'.encode('utf-8')
                else:
                    response = b'DEVICE|||0'

            elif cmd == 'GET_PARAMS':
                device = self.song().view.selected_track.view.selected_device
                if device and len(parts) >= 3:
                    start, count = int(parts[1]), int(parts[2])
                    chunk = device.parameters[start:start + count]
                    entries = ';'.join(f'{start + i},{p.original_name},{p.min},{p.max},{1 if p.is_quantized else 0}' for i, p in enumerate(chunk))
                    response = f'PARAMS|{entries}'.encode('utf-8')
                else:
                    response = b'PARAMS|'

            elif cmd == 'GET_PARAM_VALUES':
                device = self.song().view.selected_track.view.selected_device
                if device and len(parts) >= 3:
                    start, count = int(parts[1]), int(parts[2])
                    chunk = device.parameters[start:start + count]
                    values = ','.join(str(p.value) for p in chunk)
                    response = f'PARAM_VALUES|{values}'.encode('utf-8')
                else:
                    response = b'PARAM_VALUES|'

            elif cmd == 'reload':
                try:
                    self.log_message('Reloading modules')
                    try:
                        self.main_component.remove_all_listeners()
                    except Exception as e:
                        self.log_message(f'Error removing listeners: {e}')
                        self.log_message(traceback.format_exc())

                    importlib.reload(modules.helpers)
                    importlib.reload(modules.hud_arbiter)
                    importlib.reload(modules.main_component)

                    if self.functions_file_exsits():
                        importlib.reload(modules.functions)

                    self.log_message('Re-initialising modules')
                    self.init_modules()
                    response = b'reload complete'
                    self.show_message("Reload complete")
                except Exception as e:
                    self.log_message(f'Error reloading module: {e}')
                    self.show_message("Reload Failed, check logs")
                    self.log_message(traceback.format_exc())
                    response = b'reload failed, check logs'

            elif cmd == 'debug':
                self.debug = not self.debug
                self.log_message(f"Debug set to {self.debug}")
                response = b'Debug set to ' + str(self.debug).encode('utf-8')

            elif cmd == 'hudtrace':
                # Toggle gated HUD protocol tracing. `[hudtrace]`-tagged lines
                # then trace the nav/listener/mode/visibility path; capture with
                # ./bin/tail_logs.sh. The Swift HUD has its own HUD_FINE switch.
                self.fine = not self.fine
                self.log_message(f"HUD trace set to {self.fine}")
                response = b'HUD trace set to ' + str(self.fine).encode('utf-8')

            elif cmd == 'dump':
                self.dump_selected_device_parameter_info()
                response = b'Dumped to logs'


            elif cmd == 'dump2':
                self.dump_selected_device_parameter_info_split_into_encoders_and_buttons()
                response = b'Dumped to logs'

            elif cmd == 'dumpnames':
                self.dump_selected_device_parameter_names()
                response = b'Dumped to logs'

            elif cmd == 'lom':
                self.dump_selected_device_lom()
                response = b'LOM dump written to logs'

            elif cmd == 'doctor':
                # Button doctor: first call enables (press each button twice),
                # second call reports the hardware classification to the logs.
                enabled = self.main_component._helpers.doctor_toggle()
                response = (b'doctor enabled - press each button twice, then run `doctor` again'
                            if enabled else b'doctor report written to logs')

            elif cmd == 'showinfo':
                # HUD show-info: each button press is explained on the HUD via an
                # EVENT message until toggled off.
                enabled = self.main_component._helpers.show_info_toggle()
                response = (b'show-info enabled - press a button to see it explained on the HUD'
                            if enabled else b'show-info disabled')

            if response is not None:
                self._socket.sendto(response, addr)

        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                #--------------------------------------------------------------------------------
                # This benign error seems to occur on startup on Windows
                #--------------------------------------------------------------------------------
                self.log_message(f"$surface_name: Non-fatal socket error: {traceback.format_exc}")
            elif e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                #--------------------------------------------------------------------------------
                # Another benign networking error, throw when no data is received
                # on a call to recvfrom() on a non-blocking socket
                #--------------------------------------------------------------------------------
                pass
            else:
                #--------------------------------------------------------------------------------
                # Something more serious has happened
                #--------------------------------------------------------------------------------
                self.log_message(f"$surface_name: Socket error: {traceback.format_exc()}")
        except Exception as e:
            self.log_message(f"$surface_name: Exception in message processing: {traceback.format_exc()}")
        finally:
            self.schedule_message(1, self.tick)

    def disconnect(self):
        self.show_message("Disconnecting...")
        try:
            self._hud_arbiter.unregister()
        except Exception as e:
            self.log_message(f"Error unregistering HUD arbiter: {e}")
        try:
            self.main_component.remove_app_view_listeners()
        except Exception as e:
            self.log_message(f"Error removing app view listeners: {e}")
        self._socket.close()
        super().disconnect()
        # def _setup_session(self):
    #     self._session = SessionComponent(num_tracks=8, num_scenes=1)
    #     self._session.set_enabled(True)
    # 
    # def _setup_mixer(self):
    #     self._mixer = MixerComponent(num_tracks=8)
    #     self._mixer.set_enabled(True)
