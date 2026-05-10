import unittest
from dataclasses import dataclass, field
from unittest.mock import Mock

from source_modules.helpers import Helpers, ParameterMapping, Remote, SwitchSlotMapping
from source_modules.hud_protocol import EMPTY_SLOT, SlotPayload


@dataclass
class FakeParameter:
    min: float = 0
    max: float = 127
    value: float = 0
    name: str = "p1"
    is_quantized: bool = False


@dataclass
class FakeDevice:
    parameters: list = field(default_factory=list)
    name: str = "Test Device"
    class_name: str = "Test Device"


def _amp_mappings():
    return {
        "devices": [
            {
                "className": "Amp",
                "encoders": [
                    {"number": 1, "name": "Bass"},
                    {"number": 2, "name": "Middle"},
                    {"number": 3, "name": "Treble"},
                ],
                "buttons": [
                    {"number": 4, "name": "Type", "min": 0, "max": 2},
                    {"number": 5, "name": "Mono"},
                ],
            }
        ]
    }


class TestEncoderResolution(unittest.TestCase):
    def setUp(self):
        self.manager = Mock()
        self.remote = Mock()
        self.helpers = Helpers(
            self.manager, self.remote,
            slot_assignments=[(1, 'slot1'), (2, 'slot2'), (3, 'slot3')],
            switch_slot_assignments=[(0, 'switch1'), (1, 'switch2')],
            parameter_mappings_raw=_amp_mappings(),
        )

    def test_encoder_resolves_to_json_entry(self):
        device = FakeDevice(
            class_name="Amp",
            parameters=[FakeParameter(name=f"p{i}", min=0.0, max=1.0) for i in range(10)],
        )
        self.helpers.device_parameter_action(device, 1, 22, 64.0, "fn")
        # encoder slot1 → encoders[0] → number=1 → device.parameters[1]
        self.assertAlmostEqual(device.parameters[1].value, 0.5, places=1)
        self.assertEqual(self.remote.parameter_updated.call_args[0][0].alias, 'Bass')

    def test_encoder_identity_fallback_when_class_unknown(self):
        device = FakeDevice(
            class_name="Unknown",
            parameters=[FakeParameter(name=f"p{i}", min=0.0, max=1.0) for i in range(10)],
        )
        self.helpers.device_parameter_action(device, 2, 22, 127.0, "fn")
        self.assertAlmostEqual(device.parameters[2].value, 1.0, places=1)


class TestEncoderFallbackSkipsQuantized(unittest.TestCase):
    """Identity fallback (no JSON entry for class) must skip on/off + quantized params,
    so quantized buttons don't double up on encoders."""

    def setUp(self):
        self.helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1'), (2, 'slot2'), (3, 'slot3')],
            switch_slot_assignments=[],
            parameter_mappings_raw=None,  # no file → fully fallback
        )

    def test_encoders_skip_quantized_in_fallback(self):
        # idx 0 = on/off; 1 = quantized (skip); 2 = continuous; 3 = quantized (skip); 4 = continuous; 5 = continuous
        params = [
            FakeParameter(name="On/Off"),
            FakeParameter(name="q1", is_quantized=True),
            FakeParameter(name="cont1", min=0.0, max=1.0),
            FakeParameter(name="q2", is_quantized=True),
            FakeParameter(name="cont2", min=0.0, max=1.0),
            FakeParameter(name="cont3", min=0.0, max=1.0),
        ]
        device = FakeDevice(class_name="Unknown", parameters=params)
        # encoder 1 → cont1, encoder 2 → cont2, encoder 3 → cont3
        self.helpers.device_parameter_action(device, 1, 0, 127, "fn")
        self.helpers.device_parameter_action(device, 2, 0, 127, "fn")
        self.helpers.device_parameter_action(device, 3, 0, 127, "fn")
        self.assertEqual(params[2].value, 1.0)  # cont1
        self.assertEqual(params[4].value, 1.0)  # cont2
        self.assertEqual(params[5].value, 1.0)  # cont3
        # Quantized params untouched.
        self.assertEqual(params[1].value, 0)
        self.assertEqual(params[3].value, 0)


class TestSwitchAction(unittest.TestCase):
    def setUp(self):
        self.helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[],
            switch_slot_assignments=[(0, 'switch1'), (1, 'switch2')],
            parameter_mappings_raw=_amp_mappings(),
        )

    def test_switch_with_range_cycles(self):
        device = FakeDevice(
            class_name="Amp",
            parameters=[FakeParameter(name=f"p{i}", min=0, max=2, value=0) for i in range(10)],
        )
        self.helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.parameters[4].value, 1)
        self.helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.parameters[4].value, 2)
        self.helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.parameters[4].value, 0)

    def test_switch_without_range_pulses(self):
        device = FakeDevice(
            class_name="Amp",
            parameters=[FakeParameter(name=f"p{i}", min=0, max=1, value=0) for i in range(10)],
        )
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 1)

    def test_switch_fires_on_any_value(self):
        """LC XL row-3 buttons can be in latching mode where each physical press
        emits exactly one event alternating 127/0. Fire on every event so each
        press advances the cycle once."""
        device = FakeDevice(
            class_name="Amp",
            parameters=[FakeParameter(name=f"p{i}", min=0, max=2, value=0) for i in range(10)],
        )
        self.helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.parameters[4].value, 1)
        self.helpers.switch_slot_action(device, 'switch1', 0, 'fn')
        self.assertEqual(device.parameters[4].value, 2)
        self.helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.parameters[4].value, 0)

    def test_switch_quantized_without_json_range_cycles_param_range(self):
        """Quantized param with no min/max in JSON should cycle through its own
        min/max — fixes 'binary toggles trigger once then stick' bug."""
        device = FakeDevice(
            class_name="Amp",
            parameters=[FakeParameter(name=f"p{i}", min=0, max=1, value=0, is_quantized=True) for i in range(10)],
        )
        # switch2 → buttons[1] = "Mono", number=5, no min/max in JSON
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 1)
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 0)
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 1)


class TestGroupedEncoder(unittest.TestCase):
    """A grouped encoder occupies one encoder slot but maps to one of N
    parameters depending on the value of a selector parameter named by
    `controlledBy`. Each group member's `activeWhen` lists the selector
    values for which that member is active."""

    def _mappings(self):
        return {
            "devices": [{
                "className": "AutoFilter2",
                "encoders": [
                    {"number": 1, "name": "Frequency"},
                    {
                        "controlledBy": "LFO T Mode",
                        "group": [
                            {"number": 15, "activeWhen": [0]},
                            {"number": 16, "activeWhen": [1]},
                            {"number": 17, "activeWhen": [2, 3]},
                            {"number": 18, "activeWhen": [4]},
                        ],
                    },
                ],
                "buttons": [],
            }]
        }

    def _make_device(self, selector_value):
        # parameters[0] = on/off, [1] = Frequency, [14] = "LFO T Mode" selector,
        # [15..18] = the four group members.
        params = [FakeParameter(name=f"p{i}", min=0.0, max=1.0) for i in range(20)]
        params[14] = FakeParameter(name="LFO T Mode", value=selector_value, min=0, max=4, is_quantized=True)
        return FakeDevice(class_name="AutoFilter2", parameters=params)

    def setUp(self):
        self.helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1'), (2, 'slot2')],
            switch_slot_assignments=[],
            parameter_mappings_raw=self._mappings(),
        )

    def test_grouped_encoder_routes_to_member_for_selector_value_0(self):
        device = self._make_device(selector_value=0)
        self.helpers.device_parameter_action(device, 2, 22, 127.0, "fn")
        self.assertEqual(device.parameters[15].value, 1.0)
        self.assertEqual(device.parameters[16].value, 0.0)
        self.assertEqual(device.parameters[17].value, 0.0)
        self.assertEqual(device.parameters[18].value, 0.0)

    def test_grouped_encoder_routes_to_member_for_selector_value_1(self):
        device = self._make_device(selector_value=1)
        self.helpers.device_parameter_action(device, 2, 22, 127.0, "fn")
        self.assertEqual(device.parameters[16].value, 1.0)
        self.assertEqual(device.parameters[15].value, 0.0)

    def test_grouped_encoder_routes_to_member_with_multi_value_activeWhen(self):
        device = self._make_device(selector_value=3)
        self.helpers.device_parameter_action(device, 2, 22, 127.0, "fn")
        # value 3 is in activeWhen=[2,3] of the third member (param 17)
        self.assertEqual(device.parameters[17].value, 1.0)
        self.assertEqual(device.parameters[16].value, 0.0)

    def test_selector_value_change_triggers_hud_refresh(self):
        """When the selector parameter changes value (e.g. user touches the
        device UI in Live), the HUD must re-burst so the active member's
        name and value appear without the user touching the encoder."""
        # Use a real-ish param with listener support via Mock
        selector = Mock()
        selector.name = "LFO T Mode"
        selector.value = 0
        selector.min = 0
        selector.max = 4
        selector.is_quantized = True
        params = [FakeParameter(name=f"p{i}", min=0.0, max=1.0) for i in range(20)]
        params[14] = selector
        device = FakeDevice(class_name="AutoFilter2", parameters=params)
        self.helpers.selected_device_changed(device)
        selector.add_value_listener.assert_called_once()
        cb = selector.add_value_listener.call_args[0][0]
        self.helpers._remote.reset_mock()
        cb()  # simulate Live firing the listener
        self.helpers._remote.device_update.assert_called()

    def test_grouped_encoder_uses_active_member_name_in_remote_update(self):
        device = self._make_device(selector_value=2)
        device.parameters[17].name = "LFO Rate"
        remote = self.helpers._remote
        self.helpers.device_parameter_action(device, 2, 22, 64.0, "fn")
        rp = remote.parameter_updated.call_args[0][0]
        # No alias from JSON → fall through to live param name
        self.assertEqual(rp.alias, None)
        self.assertEqual(rp.param.name, "LFO Rate")


class TestPager(unittest.TestCase):
    def setUp(self):
        self.helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1'), (2, 'slot2')],
            switch_slot_assignments=[],
            parameter_mappings_raw={
                "devices": [{
                    "className": "Big",
                    "encoders": [{"number": i, "name": f"n{i}"} for i in range(1, 17)],
                    "buttons": [],
                }]
            },
            encoder_slot_count=8,
        )

    def test_encoder_page_inc_dec_within_bounds(self):
        device = FakeDevice(
            class_name="Big",
            parameters=[FakeParameter(name=f"p{i}") for i in range(20)],
        )
        self.helpers.selected_device_changed(device)
        self.assertEqual(self.helpers._encoder_page, 1)
        self.helpers.parameter_page_inc('encoder')
        self.assertEqual(self.helpers._encoder_page, 2)
        self.helpers.parameter_page_inc('encoder')  # at max (2 pages of 8)
        self.assertEqual(self.helpers._encoder_page, 2)
        self.helpers.parameter_page_dec('encoder')
        self.assertEqual(self.helpers._encoder_page, 1)
        self.helpers.parameter_page_dec('encoder')  # at min
        self.assertEqual(self.helpers._encoder_page, 1)


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
    def setUp(self):
        self.osc = Mock()
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=self.osc, hud_client=self.hud)

    def _burst(self, params):
        self.remote.device_update("TestDevice", params)

    def test_send_update_not_called_during_burst(self):
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(4)]
        self._burst(params)
        self.hud.send_update.assert_not_called()

    def test_send_update_called_after_burst(self):
        rp = _make_real_param(_make_param("Freq", value=0.7), alias="Frequency")
        self.remote.parameter_updated(rp, parameter_no=1)
        self.hud.send_update.assert_called_once_with('dial', 0, "Frequency", 0.7, 0.0, 1.0)

    def test_send_update_not_called_for_index_0(self):
        rp = _make_real_param(_make_param("On/Off"))
        self.remote.parameter_updated(rp, parameter_no=0)
        self.hud.send_update.assert_not_called()

    def test_burst_sends_commit(self):
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        self._burst(params)
        self.hud.commit.assert_called_once()

    def test_burst_sends_device_name(self):
        params = [_make_real_param(_make_param())]
        self.remote.device_update("EQ Eight", params)
        self.hud.send_device.assert_called_once_with("EQ Eight")


class TestHudLayoutSeparation(unittest.TestCase):
    """
    LAYOUT describes the physical controller — it never changes between devices.
    It must NOT be re-sent inside device_update; that would reset the HUD on
    every device selection and wipe any button state before SLOT|button can arrive.

    SLOT|button messages are the per-device concern and must always be emitted
    for every switch position defined in hud_cells, even when _resolve_switch
    cannot find a matching parameter (the layout is independent of resolution).
    """

    def setUp(self):
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=self.hud)

    def test_device_update_does_not_call_send_layout(self):
        """LAYOUT is a one-time controller description; device_update must not re-send it."""
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        hud_cells = [(0, 0, 'dial', 8, 0), (2, 0, 'button', 4, 0)]
        self.remote.device_update("SomeDevice", params, hud_layout=hud_cells)
        self.hud.send_layout.assert_not_called()

    def test_device_update_always_sends_button_slots_for_all_hud_button_cells(self):
        """Every button cell in hud_cells must produce SLOT|button messages,
        regardless of whether a device parameter could be resolved."""
        real_params = [_make_real_param(_make_param("On/Off"))]
        # switch_entries is empty — simulates a device with no resolvable params
        self.remote.device_update(
            "SomeRack", real_params,
            switch_entries=[],
            device_parameters=[],
            hud_layout=[(2, 0, 'button', 4, 0)],
        )
        button_calls = [c for c in self.hud.send_slot.call_args_list if c[0][0] == 'button']
        self.assertEqual(len(button_calls), 4,
            "Expected one SLOT|button per button cell slot even when no params resolved")


class TestDenseSymmetricEmission(unittest.TestCase):
    """Dials and buttons must follow the same emission rule: one SLOT per cell
    position, whether or not a parameter resolves. Empty slots use the
    EMPTY_SLOT sentinel."""

    def setUp(self):
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=self.hud)

    def test_dial_cells_emit_dense_with_empty_sentinel_for_unfilled(self):
        # Two real params (skipping on/off) but a dial cell of count=8 starting at 0
        params = [_make_real_param(_make_param("On/Off"))]
        params.append(_make_real_param(_make_param("Freq", value=0.5, vmin=0.0, vmax=1.0)))
        params.append(_make_real_param(_make_param("Q", value=0.7, vmin=0.0, vmax=1.0)))
        self.remote.device_update(
            "Dev", params,
            hud_layout=[(0, 0, 'dial', 8, 0)],
        )
        dial_calls = [c for c in self.hud.send_slot.call_args_list if c[0][0] == 'dial']
        self.assertEqual(len(dial_calls), 8, "Expected 8 SLOT|dial — one per cell position")
        # First two carry real names, rest are empty
        self.assertEqual(dial_calls[0][0][2], "Freq")
        self.assertEqual(dial_calls[1][0][2], "Q")
        for idx in range(2, 8):
            self.assertEqual(dial_calls[idx][0][2], EMPTY_SLOT.name)
            self.assertEqual(dial_calls[idx][0][3], EMPTY_SLOT.value)
            self.assertEqual(dial_calls[idx][0][4], EMPTY_SLOT.vmin)
            self.assertEqual(dial_calls[idx][0][5], EMPTY_SLOT.vmax)

    def test_unmapped_cell_with_negative_start_emits_no_slots(self):
        # start=-1 cells aren't in the wire-index space; they're placeholders
        params = [_make_real_param(_make_param("On/Off"))]
        self.remote.device_update(
            "Dev", params,
            hud_layout=[(2, 0, 'button', 4, -1)],
        )
        self.assertEqual([c for c in self.hud.send_slot.call_args_list], [])

    def test_commit_count_matches_emitted_slots(self):
        params = [_make_real_param(_make_param("On/Off"))]
        self.remote.device_update(
            "Dev", params,
            hud_layout=[(0, 0, 'dial', 8, 0), (2, 0, 'button', 4, 0)],
        )
        # 8 dials + 4 buttons = 12
        self.hud.commit.assert_called_once_with(12)


class TestModeOverlay(unittest.TestCase):
    """Mode-aware burst: non-device cells in the active mode get static
    labels overlaid onto the EMPTY device-path payloads."""

    def setUp(self):
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=self.hud)

    def test_mode_labels_replace_empty_slots(self):
        params = [_make_real_param(_make_param("On/Off"))]
        self.remote.device_update(
            "Dev", params,
            hud_layout=[(0, 0, 'dial', 8, 0)],
            mode_labels={('dial', 4): 'volume', ('dial', 5): 'pan'},
        )
        dial_calls = [c for c in self.hud.send_slot.call_args_list if c[0][0] == 'dial']
        names = [c[0][2] for c in dial_calls]
        # idx 0..3 empty, idx 4 = 'volume', idx 5 = 'pan', idx 6..7 empty
        self.assertEqual(names, ['', '', '', '', 'volume', 'pan', '', ''])

    def test_mode_labels_do_not_clobber_real_device_data(self):
        params = [
            _make_real_param(_make_param("On/Off")),
            _make_real_param(_make_param("Freq", value=0.5, vmin=0.0, vmax=1.0)),
        ]
        self.remote.device_update(
            "Dev", params,
            hud_layout=[(0, 0, 'dial', 8, 0)],
            mode_labels={('dial', 0): 'should_not_appear'},
        )
        dial_calls = [c for c in self.hud.send_slot.call_args_list if c[0][0] == 'dial']
        # idx 0 should keep the real device label, not the mode label
        self.assertEqual(dial_calls[0][0][2], 'Freq')

    def test_mode_labels_carry_placeholder_range(self):
        self.remote.device_update(
            "Dev", [_make_real_param(_make_param("On/Off"))],
            hud_layout=[(0, 0, 'dial', 8, 0)],
            mode_labels={('dial', 0): 'volume'},
        )
        first = next(c for c in self.hud.send_slot.call_args_list if c[0][0] == 'dial')
        # name, value, vmin, vmax — labeled but with placeholder range 0..1, value 0
        self.assertEqual(first[0][2:], ('volume', 0, 0, 1))


class TestRefreshBurst(unittest.TestCase):
    """The generic burst entrypoint: takes precomputed dense payloads."""

    def setUp(self):
        self.hud = Mock()
        self.remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=self.hud)

    def test_refresh_burst_emits_device_then_slots_then_commit(self):
        self.remote.refresh_burst(
            "Mixer",
            dial_payloads=[(0, SlotPayload("Vol", 0.8, 0, 1)), (1, EMPTY_SLOT)],
            button_payloads=[(0, SlotPayload("Mute", 1, 0, 1))],
        )
        self.hud.send_device.assert_called_once_with("Mixer")
        self.hud.commit.assert_called_once_with(3)
        kinds = [c[0][0] for c in self.hud.send_slot.call_args_list]
        self.assertEqual(kinds, ['dial', 'dial', 'button'])

    def test_in_burst_flag_resets_even_on_exception(self):
        self.hud.commit.side_effect = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            self.remote.refresh_burst("Dev", [], [])
        self.assertFalse(self.remote._in_burst)


if __name__ == '__main__':
    unittest.main()
