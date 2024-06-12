import errno

import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.EncoderElement import EncoderElement
# from _Framework.EncoderElement import *

import importlib
import socket
import traceback

from . import ableton_control_suface_as_code
from .ableton_control_suface_as_code import custom_ops

class ck_custom(ControlSurface):
    def __init__(self, c_instance):
        super(ck_custom, self).__init__(c_instance)
        self.ops = None
        self.log_message("custom script loaded")
        with self.component_guard():
            # self._setup_session()
            # self._setup_mixer()
            #
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self._socket.bind(('0.0.0.0', 11111))

            self.init_modules()

            self.schedule_message(1, self.tick)
            self.log_message("listening")


    def init_modules(self):

        self.ops = custom_ops.CustomOps(self)
        self.ops.setup_controls()

    def tick(self):
        # self.log_message(f"Ticking..")
        try:
            data, addr = self._socket.recvfrom(1024)
            self.log_message(f"data = {data}")
            self.log_message(f"data is reload {data == b'reload'}")
            if data == b'reload':
                try:
                    self.ops.remove_all_listeners()
                    importlib.reload(ableton_control_suface_as_code.custom_ops)
                    self.log_message('Reloading module')

                    self.init_modules()
                except Exception as e:
                    self.log_message(f'Error reloading module: {e}')
                    self.log_message(traceback.format_exc())
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                #--------------------------------------------------------------------------------
                # This benign error seems to occur on startup on Windows
                #--------------------------------------------------------------------------------
                self.logger.warning("AbletonOSC: Non-fatal socket error: %s" % (traceback.format_exc()))
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
                self.logger.error("AbletonOSC: Socket error: %s" % (traceback.format_exc()))

        self.schedule_message(1, self.tick)

    # def _setup_session(self):
    #     self._session = SessionComponent(num_tracks=8, num_scenes=1)
    #     self._session.set_enabled(True)
    # 
    # def _setup_mixer(self):
    #     self._mixer = MixerComponent(num_tracks=8)
    #     self._mixer.set_enabled(True)
