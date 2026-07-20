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


class FakeSocket:
    """Captures each `sendto` payload so tests can assert datagram boundaries."""
    def __init__(self):
        self.datagrams = []

    def sendto(self, data, addr):
        self.datagrams.append(data.decode('utf-8'))


class TestHudClientDatagrams(unittest.TestCase):
    def _client(self):
        c = HudClient()
        c._socket = FakeSocket()
        return c

    def test_burst_coalesces_into_single_datagram(self):
        c = self._client()
        c.begin_burst()
        c.send_layout([(0, 0, 'button', 4, 0, 0)])
        c.send_device("EQ Eight")
        c.send_slot('dial', 0, "Freq", 0.5, 0.0, 1.0)
        c.commit(1)
        c.flush_burst()
        self.assertEqual(len(c._socket.datagrams), 1)
        self.assertEqual(
            c._socket.datagrams[0],
            "LAYOUT|1|0|0|button|4|0|0\n"
            "DEVICE|EQ Eight\n"
            "SLOT|dial|0|Freq|0.5|0.0|1.0\n"
            "COMMIT|1\n",
        )

    def test_send_slot_puts_glyph_on_the_wire(self):
        # Guards the emission boundary: send_slot explodes the payload into
        # scalars, so a glyph arg must reach encode_slot (not be dropped).
        c = self._client()
        c.send_slot('button', 2, "Loop Expand", 1.0, 0.0, 1.0, "arrow.left.and.right")
        self.assertEqual(
            c._socket.datagrams,
            ["SLOT|button|2|Loop Expand|1.0|0.0|1.0|arrow.left.and.right\n"],
        )

    def test_send_slot_without_glyph_stays_seven_fields(self):
        c = self._client()
        c.send_slot('button', 2, "Mute", 0.0, 0.0, 1.0)
        self.assertEqual(c._socket.datagrams, ["SLOT|button|2|Mute|0.0|0.0|1.0\n"])

    def test_outside_burst_each_line_is_its_own_datagram(self):
        c = self._client()
        c.send_ping()
        c.send_ping()
        self.assertEqual(c._socket.datagrams, ["PING\n", "PING\n"])

    def test_oversized_burst_degrades_to_per_line_datagrams(self):
        # A burst that would exceed the OS datagram cap must not be dropped: it
        # falls back to one datagram per line (pre-coalescing behavior).
        c = self._client()
        c._max_datagram = 40  # force the fallback with a tiny cap
        c.begin_burst()
        c.send_device("EQ Eight")
        c.send_slot('dial', 0, "Freq", 0.5, 0.0, 1.0)
        c.commit(1)
        c.flush_burst()
        self.assertEqual(len(c._socket.datagrams), 3)
        self.assertEqual(c._socket.datagrams[0], "DEVICE|EQ Eight\n")
        self.assertEqual(c._socket.datagrams[2], "COMMIT|1\n")

    def test_flush_without_buffered_lines_is_noop(self):
        c = self._client()
        c.begin_burst()  # suppressed burst: nothing sent
        c.flush_burst()
        self.assertEqual(c._socket.datagrams, [])

    def test_disabled_client_sends_nothing(self):
        # hud-owner-election-plan: a non-owner surface calls set_enabled(False)
        # and must go fully silent, including HIDE (the flicker trigger).
        c = self._client()
        c.set_enabled(False)
        c.send_ping()
        c.send_hide()
        c.begin_burst()
        c.send_device("EQ Eight")
        c.commit(1)
        c.flush_burst()
        self.assertEqual(c._socket.datagrams, [])

    def test_set_enabled_true_restores_output(self):
        c = self._client()
        c.set_enabled(False)
        c.send_ping()
        c.set_enabled(True)
        c.send_ping()
        self.assertEqual(c._socket.datagrams, ["PING\n"])


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

    def test_null_client_set_enabled_is_noop(self):
        NullHudClient().set_enabled(False)
        NullHudClient().set_enabled(True)


if __name__ == '__main__':
    unittest.main()
