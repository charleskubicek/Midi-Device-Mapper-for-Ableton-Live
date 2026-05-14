import socket
import logging

from . import hud_protocol

logger = logging.getLogger("hud-client")


class HudClient:
    def __init__(self, host='127.0.0.1', port=5006):
        self._host = host
        self._port = port
        self._socket = None
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"HudClient created: {host}:{port}")
        except Exception as e:
            logger.error(f"HudClient: failed to create socket: {e}")

    def _send(self, line: str):
        if self._socket is None:
            return
        try:
            self._socket.sendto((line + '\n').encode('utf-8'), (self._host, self._port))
        except Exception as e:
            logger.error(f"HudClient._send: {e}")

    def send_layout(self, cells):
        self._send(hud_protocol.encode_layout(cells))

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

    def send_mode(self, is_shift: bool):
        self._send(hud_protocol.encode_mode(is_shift))

    def send_page_info(self, enc_page: int, enc_total: int, btn_page: int, btn_total: int,
                       enc_label: str = '', btn_label: str = ''):
        self._send(hud_protocol.encode_page_info(
            enc_page, enc_total, btn_page, btn_total, enc_label, btn_label))


class NullHudClient:
    def send_layout(self, cells): pass
    def send_device(self, name: str): pass
    def send_slot(self, kind: str, index: int, name: str, value, vmin, vmax): pass
    def send_update(self, kind: str, index: int, name: str, value, vmin, vmax): pass
    def commit(self, count: int): pass
    def send_ping(self): pass
    def send_mode(self, is_shift: bool): pass
    def send_page_info(self, enc_page, enc_total, btn_page, btn_total, enc_label='', btn_label=''): pass