import errno

import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
# from _Framework.EncoderElement import *

import importlib
import socket
import traceback

from . import modules
from .modules import %class_name_snake

class $surface_name(ControlSurface):
    def __init__(self, c_instance):
        super($surface_name, self).__init__(c_instance)
        self.ops = None
        self.log_message("$surface_name custom script loaded")
        with self.component_guard():

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self._socket.bind(('0.0.0.0', 11111))

            self.init_modules()

            self.schedule_message(1, self.tick)
            self.log_message("listening")


    def init_modules(self):

        self.%class_name_cammel = %class_name_snake.%class_name_cammel(self)
        self.%class_name_cammel.setup_controls()

    def tick(self):
        # self.log_message(f"Ticking..")
        try:
            data, addr = self._socket.recvfrom(1024)
            self.log_message(f"data = {data}")
            self.log_message(f"data is reload {data == b'reload'}")
            if data == b'reload':
                try:
                    self.log_message('Reloading modules')
                    self.ops.remove_all_listeners()
                    importlib.reload(modules.%class_name_snake)

                    self.log_message('Re-initialising modules')
                    self.init_modules()
                except Exception as e:
                    self.log_message(f'Error reloading module: {e}')
                    self.log_message(traceback.format_exc())
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                #--------------------------------------------------------------------------------
                # This benign error seems to occur on startup on Windows
                #--------------------------------------------------------------------------------
                self.logger.warning("$surface_name: Non-fatal socket error: %s" % (traceback.format_exc()))
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
                self.logger.error("$surface_name: Socket error: %s" % (traceback.format_exc()))

        self.schedule_message(1, self.tick)

    # def _setup_session(self):
    #     self._session = SessionComponent(num_tracks=8, num_scenes=1)
    #     self._session.set_enabled(True)
    # 
    # def _setup_mixer(self):
    #     self._mixer = MixerComponent(num_tracks=8)
    #     self._mixer.set_enabled(True)
