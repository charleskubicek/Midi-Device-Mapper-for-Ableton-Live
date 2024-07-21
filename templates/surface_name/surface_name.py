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
from .modules import $class_name_snake


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

    def functions_file_exsits(self):
        return (Path(__file__).resolve().parent / 'functions.py').exists()

    def init_modules(self):

        self.$class_name_snake = $class_name_snake.$class_name_camel(self)
        self.$class_name_snake.setup_controls()

    def dump_selected_device_parameter_names(self):
        device = self.song().view.selected_track.view.selected_device
        print("Dumping parameters for device: " + device.name)
        for i, p in enumerate(device.parameters):
            i = str(i).zfill(2)
            self.log_message(f" - {i}, {p.name}:{p.value}")

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
                        self.$class_name_snake.remove_all_listeners()
                    except Exception as e:
                        self.log_message(f'Error removing listeners: {e}')
                        self.log_message(traceback.format_exc())

                    importlib.reload(modules.helpers)
                    importlib.reload(modules.$class_name_snake)

                    if self.functions_file_exsits():
                        importlib.reload(modules.functions.py)

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
