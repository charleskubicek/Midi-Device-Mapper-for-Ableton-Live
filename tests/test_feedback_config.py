import unittest

from ableton_control_surface_as_code.model_v2 import read_root, FeedbackSinkDef


_BASE = """\
controller: ec4.nt
ableton_dir: /tmp
hud: on
show-hud-on: selection
"""


class TestFeedbackConfig(unittest.TestCase):
    def test_no_feedback_section_defaults_empty(self):
        root = read_root(_BASE)
        self.assertEqual(root.feedback, [])

    def test_ec4_text_sink_parsed(self):
        doc = _BASE + """\
feedback:
    -
        type: ec4_text
"""
        root = read_root(doc)
        self.assertEqual(len(root.feedback), 1)
        self.assertIsInstance(root.feedback[0], FeedbackSinkDef)
        self.assertEqual(root.feedback[0].type, "ec4_text")

    def test_unknown_sink_type_rejected(self):
        doc = _BASE + """\
feedback:
    -
        type: not_a_real_sink
"""
        with self.assertRaises(Exception):
            read_root(doc)


if __name__ == "__main__":
    unittest.main()
