"""UDP receiver for the secondary surface's forwarded HUD region.

Binds a loopback port that the parks (secondary) surface points its HudClient at.
Incoming datagrams are fed to a `RegionState`, which caches/relays them into the
lc_parks compositor's single HUD stream. Mirrors `OSCListener`'s non-blocking
tick loop (driven by `manager.schedule_message`).
"""
import errno
import socket
import traceback


class RegionListener:
    def __init__(self, manager, region_state, port, name="region"):
        self._manager = manager
        self._region_state = region_state
        self._name = name
        self._socket = None
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(0)
            self._socket.bind(('127.0.0.1', port))
            self.log_message(f"{name}: HUD region listener on port {port}")
            self._manager.schedule_message(1, self.tick)
        except Exception:
            self.log_message(f"{name}: region listener socket error on port {port}: {traceback.format_exc()}")

    def log_message(self, msg):
        self._manager.log_message(msg)

    def tick(self):
        try:
            while True:
                # 64K: the secondary now coalesces each region burst into one
                # datagram; a read shorter than the datagram truncates it (UDP),
                # which would drop the burst's trailing COMMIT.
                data, _addr = self._socket.recvfrom(65536)
                text = data.decode('utf-8', errors='replace')
                self._region_state.handle_data(text)
        except socket.error as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.ECONNRESET):
                pass
            else:
                self.log_message(f"{self._name}: region socket error: {traceback.format_exc()}")
        except Exception:
            self.log_message(f"{self._name}: region listener error: {traceback.format_exc()}")
        self._manager.schedule_message(1, self.tick)
