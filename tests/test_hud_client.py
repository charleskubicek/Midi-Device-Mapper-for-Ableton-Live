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


class TestHudClientStampsSource(unittest.TestCase):
    def test_every_message_carries_source(self):
        c = CapturingHudClient(source='parks_btns', group='lc_parks', order=1)
        c.send_layout([(0, 0, 'button', 4, 0)])
        c.send_device("EQ Eight")
        c.send_slot('dial', 0, "Freq", 0.5, 0.0, 1.0)
        c.send_update('dial', 0, "Freq", 0.6, 0.0, 1.0)
        c.commit(1)
        c.send_ping()
        c.send_hide()
        c.send_mode(True)
        c.send_page_info(1, 2, 1, 1)

        # Field[1] is the source on every line.
        for line in c.sent:
            self.assertEqual(line.split('|')[1], 'parks_btns', msg=line)

    def test_layout_carries_group_and_order(self):
        c = CapturingHudClient(source='parks_btns', group='lc_parks', order=1)
        c.send_layout([(0, 0, 'button', 4, 0)])
        self.assertEqual(c.sent[0], "LAYOUT|parks_btns|lc_parks|1|1|0|0|button|4|0")

    def test_defaults_are_main(self):
        c = CapturingHudClient()
        c.send_ping()
        self.assertEqual(c.sent[0], "PING|main")

    def test_null_client_accepts_identity_kwargs(self):
        # The template always constructs with source/group/order; NullHudClient
        # must accept them without error.
        NullHudClient(source='x', group='y', order=2)


if __name__ == '__main__':
    unittest.main()
