"""Reverse mode channel for the `lc_parks` compositor (primary -> secondary).

The secondary controller is on its own MIDI port and can never see the primary's
shift button, so it cannot switch its own mappings on its own. This module is the
one-way link that lets the PRIMARY drive the SECONDARY's mode FSM: when the user
holds shift on the primary, the primary's `goto_mode` forwards the active mode
NAME over UDP; the secondary receives it and calls its own `goto_mode`, swapping
its listeners and re-forwarding its HUD region so the combined HUD repaints.

`ModeSender` is the primary side (a tiny UDP line sender, modelled on HudClient).
`ModeListener` is the secondary side (a non-blocking poll loop, modelled on
RegionListener). Both are inert/absent on standalone surfaces.
"""
import errno
import socket
import traceback

from . import hud_protocol


class ModeSender:
    """Primary side: send the active mode name to the secondary's mode port."""

    def __init__(self, host='127.0.0.1', port=0):
        self._host = host
        self._port = port
        self._socket = None
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception:
            self._socket = None

    def send_mode(self, name: str):
        if self._socket is None:
            return
        try:
            line = hud_protocol.encode_set_mode(name) + '\n'
            self._socket.sendto(line.encode('utf-8'), (self._host, self._port))
        except Exception:
            pass


class ModeListener:
    """Secondary side: receive forwarded mode names and drive `target.goto_mode`.

    Mirrors `region_listener.RegionListener`'s non-blocking tick loop (driven by
    `manager.schedule_message`). `target` is the surface's main_component.
    """

    def __init__(self, manager, target, port, name="mode"):
        self._manager = manager
        self._target = target
        self._name = name
        self._socket = None
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self._socket.bind(('127.0.0.1', port))
            self.log_message(f"{name}: mode listener on port {port}")
            self._manager.schedule_message(1, self.tick)
        except Exception:
            self.log_message(f"{name}: mode listener socket error on port {port}: {traceback.format_exc()}")

    def log_message(self, msg):
        self._manager.log_message(msg)

    def _handle(self, text):
        for msg in hud_protocol.parse_all(text):
            if isinstance(msg, hud_protocol.SetModeMsg):
                self._target.goto_mode(msg.name)

    def tick(self):
        try:
            while True:
                data, _addr = self._socket.recvfrom(4096)
                self._handle(data.decode('utf-8', errors='replace'))
        except socket.error as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.ECONNRESET):
                pass
            else:
                self.log_message(f"{self._name}: mode socket error: {traceback.format_exc()}")
        except Exception:
            self.log_message(f"{self._name}: mode listener error: {traceback.format_exc()}")
        self._manager.schedule_message(1, self.tick)
