import unittest
from dataclasses import dataclass, field
# from typing import List
from unittest.mock import Mock, MagicMock, call

from source_modules.helpers import Helpers, ParameterMapping, Remote
from source_modules.hud_client import NullHudClient


@dataclass
class FakeParameter:
    min: float = 0
    max: float = 127
    value: float = 0
    name: str = "p1"


@dataclass
class FakeDevice:
    parameters: list[FakeParameter] = field(default_factory=list)
    name = "Test Device"
    class_name = "Test Device"


class FakeManager:
    def debug(self):
        return True

    def log_message(self, msg):
        print(msg)


class TestHelpersWithCustom(unittest.TestCase):

    def setUp(self):
        self.manager = Mock()
        self.manager.debug = True
        self.manager.log_message.side_effect = lambda x:print(x)
        self.remote_mock = Mock()
        self.mappings = {
            'SQ Sequencer': [
                {'c_idx': 39, 'd_idx': 108, 'alias': 'ScramblePitch'},
                {'c_idx': 40, 'd_idx': 112, 'alias': 'RandPitch'},
                {'c_idx': 41, 'd_idx': 219, 'alias': 'ScrambleVel'}]
        }

        self.helpers = Helpers(self.manager, self.remote_mock, self.mappings)

    def test_device_parameter_action(self):
        device = Mock()
        device.name = "SQ Sequencer"
        device.class_name = "SQ Sequencer"
        device.parameters = [Mock(min=0.0, max=1.0, value=0.1, name=f"param {i}") for i in range(220)]

        parameter_no = 40
        value = 64.0
        midi_no = 23
        fn_name = "test_fn"
        toggle = False

        self.helpers.device_parameter_action(device, parameter_no, midi_no, value, fn_name, toggle)

        self.assertAlmostEqual(device.parameters[112].value, 0.5, places=1)
        result = self.remote_mock.parameter_updated.call_args[0]

        self.assertAlmostEqual(result[0].param.value, 0.5, places=1)
        self.assertEqual(result[0].param, device.parameters[112])
        self.assertEqual(result[0].alias, 'RandPitch')
        self.assertEqual(result[1], 40)



class TestHelpers(unittest.TestCase):

    def setUp(self):
        self.manager = Mock()
        self.manager.debug = True
        self.manager.log_message.side_effect = lambda x:print(x)
        self.remote_mock = Mock()
        self.mappings = {
            # 3 values for the first 3 encoders on the midi device, Each maps to
            # controller on the ableton device and an alias is applied to each.
            # "Simpler": [(0, ParameterMapping(2, 'a', None)), (1, ParameterMapping(5, 'b', 'toggle')), (2, ParameterMapping(4, 'c', None))]
            'Simpler': [
                {'c_idx': 1, 'd_idx': 2, 'alias': 'a'},
                {'c_idx': 2, 'd_idx': 5, 'alias': 'b', 'button': 'toggle'},
                {'c_idx': 3, 'd_idx': 4, 'alias': 'c'}]

        }

        self.helpers = Helpers(self.manager, self.remote_mock, self.mappings)

    def test_device_parameter_action(self):
        device = Mock()
        device.name = "Simpler"
        device.class_name = "Simpler"
        device.parameters = [Mock(min=0.0, max=1.0, value=0.1, name=f"param {i}") for i in range(150)]

        parameter_no = 3 # mapped to parameter 4
        value = 64.0
        midi_no = 23
        fn_name = "test_fn"
        toggle = False

        self.helpers.device_parameter_action(device, parameter_no, midi_no, value, fn_name, toggle)

        self.assertAlmostEqual(device.parameters[4].value, 0.5, places=1)
        result = self.remote_mock.parameter_updated.call_args[0]

        self.assertEqual(result[0].param, device.parameters[4])
        self.assertEqual(result[0].alias, 'c')
        self.assertEqual(result[1], 3)
        self.assertAlmostEqual(result[0].param.value, 0.5, places=1)

    def test_sets_correct_parameter_between_0_and_1(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0, value=0.0)])
        self.helpers.device_parameter_action(device, 1, 22, 64.0, "test")

        self.assertEqual(device.parameters[0].value, 0)
        self.assertAlmostEqual(device.parameters[1].value, 0.5, places=2)

    def test_sets_toggle_correctly_for_toggle_button_when_on(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0, value=0.0)])

        self.helpers.device_parameter_action(device, 1, 22, 127, "test", toggle=True)
        self.assertEqual(device.parameters[1].value, 1.0)
        self.helpers.device_parameter_action(device, 1, 22, 0, "test", toggle=True)
        self.assertEqual(device.parameters[1].value, 1.0)

    def test_sets_toggle_correctly_for_toggle_button_when_off(self):
        device = FakeDevice([FakeParameter(), FakeParameter(min=0.0, max=1.0, value=0.0)])

        self.helpers.device_parameter_action(device, 1, 22, 127, "test", toggle=False)
        self.assertEqual(1.0, device.parameters[1].value)
        self.helpers.device_parameter_action(device, 1, 22, 0, "test", toggle=False)
        self.assertEqual(0, device.parameters[1].value)

    def test_normalise_within_range(self):
        self.assertAlmostEqual(self.helpers.normalise(65, 0.0, 1.0), 0.5, places=1)
        self.assertAlmostEqual(self.helpers.normalise(0, 0.0, 1.0), 0.0)
        self.assertAlmostEqual(self.helpers.normalise(127, 0.0, 1.0), 1.0)

    def test_normalise_below_min(self):
        self.assertAlmostEqual(self.helpers.normalise(-1, 0.0, 1.0), 0.0)

    def test_normalise_above_max(self):
        self.assertAlmostEqual(self.helpers.normalise(128, 0.0, 1.0), 1.0)

    def test_normalise_with_different_range(self):
        self.assertAlmostEqual(int(self.helpers.normalise(64, 0.0, 10.0)), 5)
        self.assertAlmostEqual(int(self.helpers.normalise(0, -10.0, 10.0)), -10)
        self.assertAlmostEqual(int(self.helpers.normalise(64, -10.0, 10.0)), 0)
        self.assertAlmostEqual(int(self.helpers.normalise(127, -10.0, 10.0)), 10)


def _make_param(name="Freq", value=0.5, vmin=0.0, vmax=1.0):
    p = Mock()
    p.name = name
    p.value = value
    p.min = vmin
    p.max = vmax
    return p


def _make_real_param(param, alias=None, button=None):
    rp = Mock()
    rp.param = param
    rp.alias = alias
    rp.button = button
    return rp


class TestRemoteBurstSuppression(unittest.TestCase):
    """Remote must not emit UPDATE during a device_update burst."""

    def setUp(self):
        self.osc = Mock()
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=self.osc, hud_client=self.hud)

    def _burst(self, params):
        """Run a minimal device_update with the given RealParam list (index 0 = on/off)."""
        self.remote.device_update("TestDevice", params)

    def test_send_update_not_called_during_burst(self):
        """send_update must be silent while device_update is building the snapshot."""
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(4)]
        self._burst(params)
        self.hud.send_update.assert_not_called()

    def test_send_update_called_after_burst(self):
        """send_update IS sent when parameter_updated is called outside a burst."""
        rp = _make_real_param(_make_param("Freq", value=0.7), alias="Frequency")
        self.remote.parameter_updated(rp, parameter_no=1)
        self.hud.send_update.assert_called_once_with('dial', 0, "Frequency", 0.7, 0.0, 1.0)

    def test_send_update_not_called_for_index_0(self):
        """on/off at parameter_no=0 never triggers send_update."""
        rp = _make_real_param(_make_param("On/Off"))
        self.remote.parameter_updated(rp, parameter_no=0)
        self.hud.send_update.assert_not_called()

    def test_send_update_uses_alias_over_param_name(self):
        """Alias takes priority over raw parameter name in send_update."""
        rp = _make_real_param(_make_param("RawName"), alias="NiceName")
        self.remote.parameter_updated(rp, parameter_no=2)
        args = self.hud.send_update.call_args[0]
        self.assertEqual(args[2], "NiceName")

    def test_send_update_uses_param_name_when_no_alias(self):
        rp = _make_real_param(_make_param("RawName"), alias=None)
        self.remote.parameter_updated(rp, parameter_no=3)
        args = self.hud.send_update.call_args[0]
        self.assertEqual(args[2], "RawName")

    def test_burst_flag_cleared_after_device_update(self):
        """After device_update completes, send_update works again."""
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        self._burst(params)
        self.hud.send_update.reset_mock()

        rp = _make_real_param(_make_param("Res", value=0.3))
        self.remote.parameter_updated(rp, parameter_no=1)
        self.hud.send_update.assert_called_once()

    def test_burst_sends_commit(self):
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        self._burst(params)
        self.hud.commit.assert_called_once()

    def test_burst_sends_device_name(self):
        params = [_make_real_param(_make_param())]
        self.remote.device_update("EQ Eight", params)
        self.hud.send_device.assert_called_once_with("EQ Eight")

    def test_dial_index_mapping(self):
        """parameter_no 1..N maps to dial slot 0..N-1."""
        rp = _make_real_param(_make_param("Size", value=0.9))
        self.remote.parameter_updated(rp, parameter_no=5)
        args = self.hud.send_update.call_args[0]
        self.assertEqual(args[1], 4)  # dial index = parameter_no - 1


if __name__ == '__main__':
    unittest.main()