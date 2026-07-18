import socket
import logging

from . import hud_protocol

logger = logging.getLogger("hud-client")


class HudClient:
    # Single-source protocol. `host`/`port` default to the HUD app on
    # 127.0.0.1:5006, but the parks forwarder points its client at the
    # `lc_parks` compositor's region port instead, which relays/merges into the
    # one HUD stream.
    def __init__(self, host='127.0.0.1', port=5006):
        self._host = host
        self._port = port
        self._socket = None
        # When a list, `_send` buffers lines instead of emitting them, so a whole
        # burst can be flushed as ONE datagram (burst-atomic on the wire — a lost
        # datagram then loses the whole burst rather than mixing devices). See
        # hud_protocol.md "Burst semantics".
        self._burst_buffer = None
        # A single UDP datagram is OS-capped (macOS net.inet.udp.maxdgram default
        # 9216); over it, `sendto` raises EMSGSIZE and the whole burst is lost.
        # Above this threshold `flush_burst` degrades to per-line datagrams — the
        # pre-coalescing behavior — so an oversized burst is never *dropped*, only
        # non-atomic. Real bursts are a few KB, so this never trips in practice.
        self._max_datagram = 8192
        # Owner gate for co-loaded surfaces: a surface that lost HUD-owner
        # election calls set_enabled(False) so it
        # goes fully silent on the wire -- including HIDE, which is what was
        # tearing down the elected owner's HUD burst before this existed.
        self._enabled = True
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"HudClient created: {host}:{port}")
        except Exception as e:
            logger.error(f"HudClient: failed to create socket: {e}")

    def _send(self, line: str):
        if self._burst_buffer is not None:
            self._burst_buffer.append(line)
            return
        self._sendto(line + '\n')

    def _sendto(self, payload: str):
        if self._socket is None or not self._enabled:
            return
        try:
            self._socket.sendto(payload.encode('utf-8'), (self._host, self._port))
        except Exception as e:
            logger.error(f"HudClient._sendto: {e}")

    def set_enabled(self, flag: bool):
        """Gate all outgoing datagrams. Used by HudArbiter: only the elected
        HUD owner stays enabled; a non-owner surface goes silent -- including
        HIDE -- rather than fighting the owner over the shared HUD sink.
        Gated in `_sendto` (not `_send`), so burst buffering is untouched:
        a disabled client still buffers/coalesces normally, it just discards
        the assembled datagram(s) at the last step."""
        self._enabled = flag

    def begin_burst(self):
        """Start buffering lines. Everything sent until `flush_burst` is held so
        the burst goes out as a single datagram. Idempotent; a second call just
        drops any half-buffered lines (a burst is always assembled start-to-end
        on Live's single thread, so this can't split a live burst)."""
        self._burst_buffer = []

    def flush_burst(self):
        """Emit the buffered burst as one datagram and return to pass-through.
        No-op when nothing was buffered (e.g. a suppressed burst)."""
        lines, self._burst_buffer = self._burst_buffer, None
        if not lines:
            return
        payload = ''.join(line + '\n' for line in lines)
        if len(payload.encode('utf-8')) <= self._max_datagram:
            self._sendto(payload)
        else:
            # Oversized burst: send per line so it's delivered (non-atomic) rather
            # than rejected wholesale by the OS datagram cap.
            for line in lines:
                self._sendto(line + '\n')

    def send_layout(self, cells):
        self._send(hud_protocol.encode_layout(cells))

    def send_dividers(self, cols):
        self._send(hud_protocol.encode_dividers(cols))

    def send_device(self, name: str):
        self._send(hud_protocol.encode_device(name))

    def send_slot(self, kind: str, index: int, name: str, value, vmin, vmax):
        self._send(hud_protocol.encode_slot(kind, index, name, value, vmin, vmax))

    def send_update(self, kind: str, index: int, name: str, value, vmin, vmax):
        self._send(hud_protocol.encode_update(kind, index, name, value, vmin, vmax))

    def commit(self, count: int):
        self._send(hud_protocol.encode_commit(count))

    def send_ping(self):
        self._send(hud_protocol.encode_ping())

    def send_hide(self):
        self._send(hud_protocol.encode_hide())

    def send_mode(self, is_shift: bool):
        self._send(hud_protocol.encode_mode(is_shift))

    def send_page_info(self, enc_page: int, enc_total: int, btn_page: int, btn_total: int,
                       enc_label: str = '', btn_label: str = ''):
        self._send(hud_protocol.encode_page_info(
            enc_page, enc_total, btn_page, btn_total, enc_label, btn_label))

    def send_event(self, kind: str, wire_idx: int, text: str):
        self._send(hud_protocol.encode_event(kind, wire_idx, text))

    def send_zones(self, entries):
        self._send(hud_protocol.encode_zones(entries))

    def send_drum(self, pad_name: str, pattern: str):
        self._send(hud_protocol.encode_drum(pad_name, pattern))


class NullHudClient:
    def __init__(self, host='127.0.0.1', port=5006): pass
    def set_enabled(self, flag: bool): pass
    def begin_burst(self): pass
    def flush_burst(self): pass
    def send_layout(self, cells): pass
    def send_dividers(self, cols): pass
    def send_device(self, name: str): pass
    def send_slot(self, kind: str, index: int, name: str, value, vmin, vmax): pass
    def send_update(self, kind: str, index: int, name: str, value, vmin, vmax): pass
    def commit(self, count: int): pass
    def send_ping(self): pass
    def send_hide(self): pass
    def send_mode(self, is_shift: bool): pass
    def send_page_info(self, enc_page, enc_total, btn_page, btn_total, enc_label='', btn_label=''): pass
    def send_event(self, kind, wire_idx, text): pass
    def send_zones(self, entries): pass
    def send_drum(self, pad_name, pattern): pass