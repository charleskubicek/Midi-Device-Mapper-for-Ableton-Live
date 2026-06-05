import unittest
from pathlib import Path
from string import Template

from ableton_control_surface_as_code.model_v2 import read_root

_MAIN_COMPONENT_TEMPLATE = Path("templates/surface_name/modules/main_component.py")


_BASE = """\
controller: ec4.nt
ableton_dir: /tmp
"""


class TestShiftDismissesHudConfig(unittest.TestCase):
    def test_defaults_false_when_absent(self):
        root = read_root(_BASE)
        self.assertFalse(root.shift_dismisses_hud)

    def test_parsed_true(self):
        doc = _BASE + "shift_dismisses_hud: true\n"
        root = read_root(doc)
        self.assertTrue(root.shift_dismisses_hud)

    def test_parsed_false(self):
        doc = _BASE + "shift_dismisses_hud: false\n"
        root = read_root(doc)
        self.assertFalse(root.shift_dismisses_hud)


class TestShiftDismissesHudRender(unittest.TestCase):
    """The template wires the substitution var into the mode-button press branch."""

    def _render(self, call: str) -> str:
        text = _MAIN_COMPONENT_TEMPLATE.read_text()
        return Template(text).safe_substitute({"shift_dismiss_hud_call": call})

    def _listener_body(self, rendered: str) -> str:
        start = rendered.index("def mode_button_listener")
        end = rendered.index("def on_device_selected", start)
        return rendered[start:end]

    def test_dismiss_fires_after_goto_mode_in_both_branches(self):
        # gen.py renders this string when shift_dismisses_hud is true. The HIDE
        # must come AFTER goto_mode (whose burst clears the dismissed flag) in
        # both the press branch and the shift-release branch.
        body = self._listener_body(self._render("self._hud_client.send_hide()"))
        # two occurrences: one per branch
        self.assertEqual(body.count("self._hud_client.send_hide()"), 2)
        # in each branch the send_hide must appear after a goto_mode call
        first_goto = body.index("self.goto_mode")
        first_hide = body.index("self._hud_client.send_hide()")
        self.assertLess(first_goto, first_hide)

    def test_listener_is_noop_when_disabled(self):
        body = self._listener_body(self._render("pass"))
        self.assertNotIn("send_hide", body)


if __name__ == "__main__":
    unittest.main()
