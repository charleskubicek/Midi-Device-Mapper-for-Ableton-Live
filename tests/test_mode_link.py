import unittest

from source_modules.mode_link import ModeListener


class FakeManager:
    def __init__(self):
        self.logs = []
        self.scheduled = []

    def log_message(self, msg):
        self.logs.append(msg)

    def schedule_message(self, delay, fn):
        # Record but don't recurse — tests drive _handle directly.
        self.scheduled.append((delay, fn))


class CapturingSurface:
    def __init__(self):
        self.modes = []

    def goto_mode(self, name):
        self.modes.append(name)


class TestModeListener(unittest.TestCase):
    def setUp(self):
        self.manager = FakeManager()
        self.surface = CapturingSurface()
        # port 0 lets the OS pick a free port; we drive _handle directly so no
        # real datagram is needed.
        self.listener = ModeListener(self.manager, self.surface, port=0, name="t-mode")

    def test_setmode_drives_goto_mode(self):
        self.listener._handle("SETMODE|shift_mode\n")
        self.assertEqual(self.surface.modes, ["shift_mode"])

    def test_ignores_non_setmode_lines(self):
        self.listener._handle("PING\nMODE|shift\nDEVICE|EQ\n")
        self.assertEqual(self.surface.modes, [])

    def test_multiple_lines_in_one_datagram(self):
        self.listener._handle("SETMODE|main_mode\nSETMODE|shift_mode\n")
        self.assertEqual(self.surface.modes, ["main_mode", "shift_mode"])


if __name__ == '__main__':
    unittest.main()
