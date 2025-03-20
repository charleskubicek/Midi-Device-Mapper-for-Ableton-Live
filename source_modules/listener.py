"""
OSC listener class for receiving OSC messages.
"""

import errno
import socket
import traceback

from .pythonosc.osc_message import OscMessage


class OSCListener:
    """
    A listener for OSC messages that sets up a UDP socket and processes received messages.
    """
    def __init__(self, manager, button_handler, port=5015):
        """
        Initialize the OSC listener.
        
        Args:
            manager: The manager object that provides scheduling and logging functionality
            button_handler: The handler for button events
        """
        self._manager = manager
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self._socket.bind(('0.0.0.0', port))
            self.log_message(f"ck_launch_control_16: listening on port {port}")

            self._manager.schedule_message(1, self.tick)
        except socket.error as e:
            self.log_message(f"ck_launch_control_16: Socket error: {traceback.format_exc()}")
            self._manager.show_message(f"ck_launch_control_16: Socket error: {traceback.format_exc()}")
        self.button_handler = button_handler
        # self.show_message("Connected to ck_launch_control_16")
    
    def log_message(self, msg):
        """
        Log a message using the manager.
        
        Args:
            msg: The message to log
        """
        self._manager.log_message(msg)
    
    def tick(self):
        """
        Process any received OSC messages.
        This method is called periodically by the manager.
        """
        # self.log_message(f"Ticking..")
        try:
            while True:
                data, addr = self._socket.recvfrom(1024)
                self.log_message(f"data = {data}")
                response = None

                message = OscMessage(data)
                self.log_message(f"message.address: {message.address}")
                self.log_message(f"message.params: {message.params}")

                if message.address == '/button/down':
                    if len(message.params) > 1:
                        self.button_handler(message.params[0], message.params[1])

                if response is not None:
                    self._socket.sendto(response, addr)
                    print(f"Sent response to {addr}")
                
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                #--------------------------------------------------------------------------------
                # This benign error seems to occur on startup on Windows
                #--------------------------------------------------------------------------------
                self.log_message(f"ck_launch_control_16: Non-fatal socket error: {traceback.format_exc}")
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
                self.log_message(f"ck_launch_control_16: Socket error: {traceback.format_exc()}")
        
        self._manager.schedule_message(1, self.tick)