import unittest

from source_modules.show_info import ShowInfo, describe_edge


class TestDescribeEdge(unittest.TestCase):
    def test_press_acted(self):
        self.assertIn("acted", describe_edge(127))

    def test_release_ignored(self):
        self.assertIn("ignored", describe_edge(0))

    def test_custom_on_value_noted(self):
        self.assertIn("on-value≠127", describe_edge(100))


class TestShowInfo(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.logs = []
        self.si = ShowInfo(send_event=lambda k, i, t: self.events.append((k, i, t)),
                           log=self.logs.append)

    def test_disabled_emits_nothing(self):
        self.si.notify('btn', 127)
        self.assertEqual(self.events, [])

    def test_enabled_emits_event(self):
        self.si.toggle()
        self.si.notify('btn', 127, wire_idx=4, kind='button')
        self.assertEqual(len(self.events), 1)
        kind, idx, text = self.events[0]
        self.assertEqual(kind, 'button')
        self.assertEqual(idx, 4)
        self.assertIn('btn', text)
        self.assertIn('acted', text)

    def test_toggle_off_stops_emitting(self):
        self.si.toggle()
        self.si.toggle()
        self.si.notify('btn', 127)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
