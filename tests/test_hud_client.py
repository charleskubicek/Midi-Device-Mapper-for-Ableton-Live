import unittest

from source_modules.hud_client import HudClient, NullHudClient


class CapturingHudClient(HudClient):
    """HudClient with the socket replaced by a capture list, so we can assert
    the exact lines it would put on the wire."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sent = []
        self._socket = None  # ensure no real datagrams

    def _send(self, line: str):
        self.sent.append(line)


class TestHudClientWire(unittest.TestCase):
    def test_single_source_lines(self):
        c = CapturingHudClient()
        c.send_layout([(0, 0, 'button', 4, 0, 0)])
        c.send_device("EQ Eight")
        c.send_slot('dial', 0, "Freq", 0.5, 0.0, 1.0)
        c.send_update('dial', 0, "Freq", 0.6, 0.0, 1.0)
        c.commit(1)
        c.send_ping()
        c.send_hide()
        c.send_mode(True)
        c.send_page_info(1, 2, 1, 1)

        self.assertEqual(c.sent[0], "LAYOUT|1|0|0|button|4|0|0")
        self.assertEqual(c.sent[1], "DEVICE|EQ Eight")
        self.assertEqual(c.sent[2], "SLOT|dial|0|Freq|0.5|0.0|1.0")
        self.assertEqual(c.sent[3], "UPDATE|dial|0|Freq|0.6|0.0|1.0")
        self.assertEqual(c.sent[4], "COMMIT|1")
        self.assertEqual(c.sent[5], "PING")
        self.assertEqual(c.sent[6], "HIDE")

    def test_host_port_are_configurable(self):
        # The parks forwarder points its client at the lc_parks region port.
        c = CapturingHudClient(host='127.0.0.1', port=5023)
        self.assertEqual(c._port, 5023)

    def test_null_client_accepts_host_port(self):
        NullHudClient(host='127.0.0.1', port=5023)


if __name__ == '__main__':
    unittest.main()
