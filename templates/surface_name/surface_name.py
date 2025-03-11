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

try:
    from .modules import functions
except ImportError:
    pass

class $surface_name(ControlSurface):
    def __init__(self, c_instance):
        super($surface_name, self).__init__(c_instance)
        self.ops = None
        self.log_message("$surface_name custom script loaded")
        with self.component_guard():

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self._socket.bind(('0.0.0.0', $udp_port))
            self.log_message("$surface_name: listening on port $udp_port")

            self.init_modules()

            self.schedule_message(1, self.tick)
            self.show_message("Connected to $surface_name")
            self.debug = False

            self.schedule_message(5, self.update_main_component_with_selected_device)

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
        self.log_message("Dumping parameters for device; name:" + device.name+", class_name: " + device.class_name)
        parameters = []

        for i, p in enumerate(device.parameters):
            i = str(i).zfill(2)
            msg = {
                'no': i,
                'name': p.name,
                'value': p.value,
                'min': p.min,
                'max': p.max
            }
            # self.log_message(str(msg)+", ")
            parameters.append(msg)

        result_obj = { "class_name" : device.class_name,"name": device.name,  "parameters": parameters }
        self.log_message('\n' + str(result_obj).replace('\n', ' '))

    def tick(self):
        # self.log_message(f"Ticking..")
        try:
            data, addr = self._socket.recvfrom(1024)
            self.log_message(f"data = {data}")
            self.log_message(f"data is reload {data == b'reload'}")
            response = None
            if data == b'reload':
                try:
                    self.log_message('Reloading modules')
                    try:
                        self.main_component.remove_all_listeners()
                    except Exception as e:
                        self.log_message(f'Error removing listeners: {e}')
                        self.log_message(traceback.format_exc())

                    importlib.reload(modules.helpers)
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
            elif data == b'debug':
                self.debug = not self.debug
                self.log_message(f"Debug set to {self.debug}")
                response = b'Debug set to ' + str(self.debug).encode('utf-8')

            elif data == b'dump':
                self.dump_selected_device_parameter_names()
                response = b'Dumped to logs'

            if response is not None:
                self._socket.sendto(response, addr)
                print(f"Sent response to {addr}")

        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                #--------------------------------------------------------------------------------
                # This benign error seems to occur on startup on Windows
                #--------------------------------------------------------------------------------
                self.logger.warning(f"$surface_name: Non-fatal socket error: {traceback.format_exc}")
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
                self.logger.error(f"$surface_name: Socket error: {traceback.format_exc()}")

        self.schedule_message(1, self.tick)

    def disconnect(self):
        self.show_message("Disconnecting...")
        self._socket.close()
        super().disconnect()
        # def _setup_session(self):
    #     self._session = SessionComponent(num_tracks=8, num_scenes=1)
    #     self._session.set_enabled(True)
    # 
    # def _setup_mixer(self):
    #     self._mixer = MixerComponent(num_tracks=8)
    #     self._mixer.set_enabled(True)
