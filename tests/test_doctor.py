import unittest

from source_modules.doctor import classify_button, Doctor


class TestClassifyButton(unittest.TestCase):
    def test_momentary_quick_down_up(self):
        # 127 then 0 within the window = hardware momentary
        kind, warnings = classify_button([(127, 0.0), (0, 0.05)])
        self.assertEqual(kind, 'momentary')
        self.assertEqual(warnings, [])

    def test_toggle_separate_presses(self):
        # 127 on one press, 0 on a later press (gap > window) = hardware toggle
        kind, warnings = classify_button([(127, 0.0), (0, 1.0)])
        self.assertEqual(kind, 'toggle')
        self.assertTrue(any('every other press' in w for w in warnings))

    def test_trigger_never_zero(self):
        kind, warnings = classify_button([(127, 0.0), (127, 1.0)])
        self.assertEqual(kind, 'trigger')
        self.assertTrue(any('TRIGGER' in w for w in warnings))

    def test_custom_on_value_flagged(self):
        kind, warnings = classify_button([(100, 0.0), (0, 0.05)])
        self.assertEqual(kind, 'momentary')
        self.assertTrue(any('≠127' in w for w in warnings))

    def test_no_events(self):
        self.assertEqual(classify_button([]), ('no-events', []))


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.t = [0.0]
        self.doc = Doctor(log=self.logs.append, clock=lambda: self.t[0])

    def test_disabled_doctor_ignores_events(self):
        self.doc.observe('btn', 127)
        self.assertEqual(self.doc._events, {})

    def test_enabled_accumulates_and_reports(self):
        self.doc.toggle()  # enable
        self.t[0] = 0.0
        self.doc.observe('btn_a', 127)
        self.t[0] = 0.05
        self.doc.observe('btn_a', 0)
        self.doc.report()
        report = "\n".join(self.logs)
        self.assertIn('btn_a: momentary', report)

    def test_toggle_then_report_classifies_toggle_hardware(self):
        self.doc.toggle()  # enable
        self.t[0] = 0.0
        self.doc.observe('btn_b', 127)
        self.t[0] = 2.0
        self.doc.observe('btn_b', 0)
        self.doc.report()
        report = "\n".join(self.logs)
        self.assertIn('btn_b: toggle', report)


if __name__ == "__main__":
    unittest.main()
