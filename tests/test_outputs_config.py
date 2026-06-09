import unittest
from unittest.mock import MagicMock

from ableton_control_surface_as_code.gen import generate_code_as_template_vars
from ableton_control_surface_as_code.model_v2 import (
    OutputSinkDef,
    OutputSinkType,
    OSCTarget,
    read_root,
)


_BASE = """\
controller: ec4.nt
ableton_dir: /tmp
"""


class TestOutputsConfig(unittest.TestCase):

    def test_no_outputs_section_defaults_empty(self):
        root = read_root(_BASE)
        self.assertEqual(root.outputs, [])

    def test_osc_sink_parsed(self):
        doc = _BASE + """\
outputs:
    -
        type: osc
        targets:
            -
                host: 127.0.0.1
            -
                host: 192.168.1.10
                port: 9000
"""
        root = read_root(doc)
        self.assertEqual(len(root.outputs), 1)
        sink = root.outputs[0]
        self.assertIsInstance(sink, OutputSinkDef)
        self.assertEqual(sink.type, OutputSinkType.OSC)
        self.assertEqual(len(sink.targets), 2)
        self.assertEqual(sink.targets[0].host, '127.0.0.1')
        self.assertEqual(sink.targets[0].port, 5005)
        self.assertEqual(sink.targets[1].host, '192.168.1.10')
        self.assertEqual(sink.targets[1].port, 9000)

    def test_remote_on_true_synthesises_legacy_osc_sink(self):
        doc = _BASE + "remote_on: true\n"
        root = read_root(doc)
        self.assertEqual(len(root.outputs), 1)
        sink = root.outputs[0]
        self.assertEqual(sink.type, OutputSinkType.OSC)
        hosts = [t.host for t in sink.targets]
        self.assertEqual(hosts, ['127.0.0.1'])

    def test_remote_on_false_no_outputs(self):
        doc = _BASE + "remote_on: false\n"
        root = read_root(doc)
        self.assertEqual(root.outputs, [])

    def test_explicit_outputs_takes_precedence_over_remote_on(self):
        doc = _BASE + """\
remote_on: true
outputs:
    -
        type: osc
        targets:
            -
                host: 10.0.0.1
"""
        root = read_root(doc)
        # explicit outputs wins; back-compat synthesis skipped
        self.assertEqual(len(root.outputs), 1)
        self.assertEqual(root.outputs[0].targets[0].host, '10.0.0.1')

    def test_unknown_output_type_rejected(self):
        doc = _BASE + """\
outputs:
    -
        type: not_real
"""
        with self.assertRaises(Exception):
            read_root(doc)


class TestOscClientsCodegen(unittest.TestCase):

    def _make_mock_modes(self):
        """Minimal ModeGroupWithMidi stub sufficient for generate_code_as_template_vars."""
        modes = MagicMock()
        modes.first_mode_name.return_value = 'default'
        modes.mappings = [('default', [])]
        modes.has_modes.return_value = False
        modes.fsm.return_value = []
        modes.mode_button = None
        return modes

    def test_empty_outputs_produces_empty_osc_clients(self):
        modes = self._make_mock_modes()
        result = generate_code_as_template_vars(modes, outputs=[])
        self.assertEqual(result['osc_clients'], '')

    def test_none_outputs_produces_empty_osc_clients(self):
        modes = self._make_mock_modes()
        result = generate_code_as_template_vars(modes, outputs=None)
        self.assertEqual(result['osc_clients'], '')

    def test_osc_outputs_rendered_as_constructor_expressions(self):
        modes = self._make_mock_modes()
        sink = OutputSinkDef(
            type=OutputSinkType.OSC,
            targets=[
                OSCTarget(host='127.0.0.1', port=5005),
                OSCTarget(host='192.168.68.84', port=5005),
            ],
        )
        result = generate_code_as_template_vars(modes, outputs=[sink])
        self.assertIn("OSCClient(host='127.0.0.1', port=5005)", result['osc_clients'])
        self.assertIn("OSCClient(host='192.168.68.84', port=5005)", result['osc_clients'])


if __name__ == '__main__':
    unittest.main()
