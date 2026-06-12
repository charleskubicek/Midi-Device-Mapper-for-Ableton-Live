import unittest

from source_modules.doctor import classify_button, Doctor


class TestClassifyButton(unittest.TestCase):
    def test_momentary_quick_down_up(self):
        kind, on_value = classify_button([(127, 0.0), (0, 0.05)])
        self.assertEqual(kind, 'momentary')
        self.assertEqual(on_value, 127)

    def test_toggle_separate_presses(self):
        kind, on_value = classify_button([(127, 0.0), (0, 1.0)])
        self.assertEqual(kind, 'toggle')

    def test_trigger_never_zero(self):
        kind, _ = classify_button([(127, 0.0), (127, 1.0)])
        self.assertEqual(kind, 'trigger')

    def test_custom_on_value_reported(self):
        kind, on_value = classify_button([(100, 0.0), (0, 0.05)])
        self.assertEqual(kind, 'momentary')
        self.assertEqual(on_value, 100)

    def test_no_events(self):
        self.assertEqual(classify_button([]), ('no-events', None))


class TestDoctorReport(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.t = [0.0]

    def _doctor(self, assumed='momentary'):
        return Doctor(log=self.logs.append, clock=lambda: self.t[0],
                      assumed_behaviour=assumed)

    def test_disabled_ignores_events(self):
        doc = self._doctor()
        doc.observe('btn', 127)
        self.assertEqual(doc._events, {})

    def test_momentary_hardware_matches_momentary_surface(self):
        doc = self._doctor(assumed='momentary')
        doc.toggle()
        self.t[0] = 0.0; doc.observe('btn_a', 127)
        self.t[0] = 0.05; doc.observe('btn_a', 0)
        doc.report()
        report = "\n".join(self.logs)
        self.assertIn('btn_a: momentary', report)
        self.assertIn('match', report)
        self.assertNotIn('MISMATCH', report)

    def test_toggle_hardware_mismatches_momentary_surface_with_fix(self):
        doc = self._doctor(assumed='momentary')
        doc.toggle()
        self.t[0] = 0.0; doc.observe('btn_b', 127)
        self.t[0] = 2.0; doc.observe('btn_b', 0)
        doc.report()
        report = "\n".join(self.logs)
        self.assertIn('btn_b: toggle', report)
        self.assertIn('MISMATCH', report)
        self.assertIn('button-behaviour: toggle', report)

    def test_toggle_hardware_matches_toggle_surface(self):
        doc = self._doctor(assumed='toggle')
        doc.toggle()
        self.t[0] = 0.0; doc.observe('btn_c', 127)
        self.t[0] = 2.0; doc.observe('btn_c', 0)
        doc.report()
        report = "\n".join(self.logs)
        self.assertNotIn('MISMATCH', report)

    def test_short_label_strips_generated_prefix(self):
        doc = self._doctor()
        doc.toggle()
        self.t[0] = 0.0
        doc.observe('button_ch9_36_note__mode_shift_mode_switch1_listener', 127)
        self.t[0] = 0.05
        doc.observe('button_ch9_36_note__mode_shift_mode_switch1_listener', 0)
        doc.report()
        report = "\n".join(self.logs)
        self.assertIn('mode_shift_mode_switch1', report)


if __name__ == "__main__":
    unittest.main()
