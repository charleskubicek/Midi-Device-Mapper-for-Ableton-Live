import unittest
from dataclasses import dataclass, field
from unittest.mock import Mock

from source_modules.helpers import Helpers, ParameterMapping, Remote, SwitchSlotMapping
from source_modules.hud_protocol import EMPTY_SLOT, SlotPayload, BurstSnapshot, PageInfo


@dataclass
class FakeParameter:
    min: float = 0
    max: float = 127
    value: float = 0
    name: str = "p1"
    original_name: str = ""
    is_quantized: bool = False

    def __post_init__(self):
        if not self.original_name:
            self.original_name = self.name


@dataclass
class FakeDevice:
    parameters: list = field(default_factory=list)
    name: str = "Test Device"
    class_name: str = "Test Device"


def _build_named_params(entries, total=50, min=0.0, max=1.0, value=0.0):
    """Build a parameter list whose names match a list of (number, name) JSON
    entries. Defaults to 50 unnamed parameters with names overridden at the
    specified indices — mirrors how Live exposes Parameter.name."""
    params = [FakeParameter(name=f"slot{i}", min=min, max=max, value=value) for i in range(total)]
    for num, nm in entries:
        if num < total:
            params[num].name = nm
            params[num].original_name = nm
    return params


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
            parameters=_build_named_params(
                [(1, "Bass"), (2, "Middle"), (3, "Treble"), (4, "Type"), (5, "Mono")], total=10),
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
            parameters=_build_named_params([(4, "Type"), (5, "Mono")], total=10, max=2, value=0),
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
            parameters=_build_named_params([(4, "Type"), (5, "Mono")], total=10, value=0),
        )
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 1)

    def test_switch_fires_on_any_value(self):
        """LC XL row-3 buttons can be in latching mode where each physical press
        emits exactly one event alternating 127/0. Fire on every event so each
        press advances the cycle once."""
        device = FakeDevice(
            class_name="Amp",
            parameters=_build_named_params([(4, "Type"), (5, "Mono")], total=10, max=2, value=0),
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
        params = _build_named_params([(4, "Type"), (5, "Mono")], total=10, value=0)
        for p in params:
            p.is_quantized = True
        device = FakeDevice(class_name="Amp", parameters=params)
        # switch2 → buttons[1] = "Mono", number=5, no min/max in JSON
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 1)
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 0)
        self.helpers.switch_slot_action(device, 'switch2', 127, 'fn')
        self.assertEqual(device.parameters[5].value, 1)


class TestSimplerEncoderRegression(unittest.TestCase):
    """Regression for: after adding a `lom_property` entry to Simpler's
    `buttons` list, the encoders themselves got mis-mapped. The HUD label
    said "Fade In" but turning the encoder moved Sustain instead.

    Encoders are independent of buttons, so adding a button-list entry
    must not shift encoder resolution."""

    SIMPLER_ENCODERS = [
        {"number": 3, "name": "S Start", "display": "Start"},
        {"number": 4, "name": "S Length", "display": "Length"},
        {"number": 11, "name": "Transpose"},
        {"number": 12, "name": "Detune"},
        {"number": 21, "name": "Ve Attack"},
        {"number": 22, "name": "Ve Decay"},
        {"number": 23, "name": "Ve Sustain"},   # idx 6
        {"number": 24, "name": "Ve Release"},
        {"number": 36, "name": "Filter Freq"},  # idx 8
        {"number": 37, "name": "Filter Res"},
        {"number": 38, "name": "Filter Morph"},
        {"number": 39, "name": "Filter Drive"},
        {"number": 15, "name": "Volume"},
        {"number": 28, "name": "Fade In"},      # idx 13
        {"number": 30, "name": "Fade Out"},
        {"number": 8, "name": "Spread"},
    ]

    SIMPLER_BUTTONS = [
        {"lom_property": "playback_mode", "type": "enum"},
        {"number": 29, "name": "Trigger Mode"},
    ]

    def _helpers(self, raw_buttons):
        # 16 encoder slots (two rows of 8) — matches ck_launch_control_16.
        return Helpers(
            Mock(), Mock(),
            slot_assignments=[(c, f'slot{c}') for c in range(1, 17)],
            switch_slot_assignments=[(0, 'switch1')],
            parameter_mappings_raw={"devices": [{
                "className": "OriginalSimpler",
                "encoders": self.SIMPLER_ENCODERS,
                "buttons": raw_buttons,
            }]},
            encoder_slot_count=16,
        )

    def _device(self):
        entries = [(e['number'], e['name']) for e in self.SIMPLER_ENCODERS]
        entries.extend([(b['number'], b['name']) for b in self.SIMPLER_BUTTONS if 'number' in b])
        return FakeDevice(
            class_name="OriginalSimpler",
            parameters=_build_named_params(entries, total=50),
        )

    def test_fade_in_encoder_moves_param_28_not_23(self):
        """Turning encoder c_idx=14 must move device.parameters[28] (Fade In),
        not parameters[23] (Sustain)."""
        helpers = self._helpers(self.SIMPLER_BUTTONS)
        device = self._device()
        helpers.device_parameter_action(device, 14, 22, 127.0, "fn")
        self.assertAlmostEqual(device.parameters[28].value, 1.0, places=2,
                               msg="Fade In encoder failed to move param 28")
        self.assertEqual(device.parameters[23].value, 0.0,
                         "Sustain (param 23) must remain untouched when Fade In is turned")

    def test_filter_freq_encoder_moves_param_36(self):
        helpers = self._helpers(self.SIMPLER_BUTTONS)
        device = self._device()
        helpers.device_parameter_action(device, 9, 22, 127.0, "fn")
        self.assertAlmostEqual(device.parameters[36].value, 1.0, places=2,
                               msg="Filter Freq encoder failed to move param 36")

    def test_hud_label_and_encoder_action_agree(self):
        """The HUD label for wire_idx=N must point to the same json entry
        that turning encoder c_idx=N+1 manipulates."""
        helpers = self._helpers(self.SIMPLER_BUTTONS)
        device = self._device()
        helpers.selected_device_changed(device)
        call = helpers._remote.device_update.call_args
        self.assertIsNotNone(call, "device_update must have been invoked")
        real_parameters = call[0][1]
        # wire_idx 13 -> rp_idx 14 -> Fade In (alias)
        fade_in_rp = real_parameters[14]
        self.assertEqual(fade_in_rp.alias, "Fade In",
                         f"HUD slot 14 alias was {fade_in_rp.alias!r}, expected 'Fade In'")
        helpers.device_parameter_action(device, 14, 22, 127.0, "fn")
        self.assertGreater(fade_in_rp.param.value, 0,
                           "Encoder action must move the parameter shown on the HUD")


class _FakePlaybackMode:
    """Mimics a Boost.Python enum: members are int-valued constants and the
    class exposes `.values` as a dict[int, member]."""
    _by_idx = {}

    def __init__(self, name, idx):
        self.name = name
        self._idx = idx

    def __int__(self):
        return self._idx

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, _FakePlaybackMode) and self._idx == other._idx

    def __hash__(self):
        return hash(self._idx)


_FakePlaybackMode.classic = _FakePlaybackMode('classic', 0)
_FakePlaybackMode.one_shot = _FakePlaybackMode('one_shot', 1)
_FakePlaybackMode.slicing = _FakePlaybackMode('slicing', 2)
_FakePlaybackMode.values = {0: _FakePlaybackMode.classic,
                            1: _FakePlaybackMode.one_shot,
                            2: _FakePlaybackMode.slicing}


@dataclass
class FakeSimpler:
    parameters: list = field(default_factory=list)
    name: str = "Simpler"
    class_name: str = "OriginalSimpler"
    playback_mode: object = _FakePlaybackMode.classic
    pad_slicing: bool = False
    crop_calls: int = 0

    def crop(self):
        self.crop_calls += 1


class TestLomButtonActions(unittest.TestCase):
    def _make(self, buttons):
        return Helpers(
            Mock(), Mock(),
            slot_assignments=[],
            switch_slot_assignments=[(0, 'switch1')],
            parameter_mappings_raw={"devices": [{
                "className": "OriginalSimpler",
                "encoders": [],
                "buttons": buttons,
            }]},
        )

    def test_enum_button_cycles_through_members(self):
        helpers = self._make([{"lom_property": "playback_mode", "type": "enum"}])
        device = FakeSimpler(parameters=[FakeParameter()])
        helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.playback_mode, _FakePlaybackMode.one_shot)
        helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.playback_mode, _FakePlaybackMode.slicing)
        helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.playback_mode, _FakePlaybackMode.classic)

    def test_bool_button_toggles(self):
        helpers = self._make([{"lom_property": "pad_slicing", "type": "bool"}])
        device = FakeSimpler(parameters=[FakeParameter()])
        helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertTrue(device.pad_slicing)
        helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertFalse(device.pad_slicing)

    def test_function_button_calls(self):
        helpers = self._make([{"lom_function": "crop", "type": "function"}])
        device = FakeSimpler(parameters=[FakeParameter()])
        helpers.switch_slot_action(device, 'switch1', 127, 'fn')
        self.assertEqual(device.crop_calls, 1)

    def test_enum_button_hud_payload(self):
        helpers = self._make([{"lom_property": "playback_mode", "type": "enum", "display": "Mode"}])
        device = FakeSimpler(parameters=[FakeParameter()])
        info = helpers._resolve_switch(device, 0)
        payload = helpers._lom_slot_payload(info)
        self.assertEqual(payload.name, "Mode: classic")
        self.assertEqual(payload.value, 0.0)
        self.assertEqual(payload.vmax, 2.0)


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
                    {"name": "Frequency"},
                    {
                        "controlledBy": "LFO T Mode",
                        "group": [
                            {"name": "p15", "activeWhen": [0]},
                            {"name": "p16", "activeWhen": [1]},
                            {"name": "p17", "activeWhen": [2, 3]},
                            {"name": "p18", "activeWhen": [4]},
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
        params[1] = FakeParameter(name="Frequency", min=0.0, max=1.0)
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
        selector.original_name = "LFO T Mode"
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
        # The group member's `name` field doubles as the original_name lookup
        # AND the alias on the resolved RealParameter.
        remote = self.helpers._remote
        self.helpers.device_parameter_action(device, 2, 22, 64.0, "fn")
        rp = remote.parameter_updated.call_args[0][0]
        self.assertEqual(rp.alias, "p17")
        self.assertEqual(rp.param.original_name, "p17")


class TestPager(unittest.TestCase):
    def setUp(self):
        # Two-bank fake device on an 8-slot controller: 1 BOB page + 1 standard
        # bank page = 2 pages total (banks_per_page=1 when slot_count<16).
        self.helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1'), (2, 'slot2')],
            switch_slot_assignments=[],
            parameter_mappings_raw={
                "devices": [{
                    "className": "Big",
                    "encoders": [{"name": "p1"}],
                    "buttons": [],
                }]
            },
            encoder_slot_count=8,
            device_banks={'Big': (('p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8'),)},
            bank_names={'Big': ('Main',)},
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


class TestFeedbackSinkFanout(unittest.TestCase):
    """Generic feedback sinks (e.g. the EC4 text readouts) ride the same burst
    as the HUD: Remote fans the dial/button payloads out to every sink so an
    additional display stays in lock-step with the HUD without its own path."""

    def setUp(self):
        self.hud = Mock()
        self.sink = Mock()
        self.remote = Remote(manager=Mock(), osc_client=Mock(),
                             hud_client=self.hud, feedback_sinks=[self.sink])

    def test_burst_fans_out_to_sink_with_device_name(self):
        params = [_make_real_param(_make_param("On/Off")),
                  _make_real_param(_make_param("Freq", value=0.5, vmin=0.0, vmax=1.0))]
        self.remote.device_update("EQ Eight", params,
                                  hud_layout=[(0, 0, 'dial', 8, 0)])
        self.sink.on_burst.assert_called_once()
        snapshot = self.sink.on_burst.call_args[0][0]
        self.assertEqual(snapshot.device_name, "EQ Eight")

    def test_sink_receives_dial_payload_for_mapped_slot(self):
        params = [_make_real_param(_make_param("On/Off")),
                  _make_real_param(_make_param("Freq", value=0.5, vmin=0.0, vmax=1.0))]
        self.remote.device_update("Dev", params, hud_layout=[(0, 0, 'dial', 8, 0)])
        dial_payloads = dict(self.sink.on_burst.call_args[0][0].dials)
        self.assertEqual(dial_payloads[0].name, "Freq")

    def test_no_sinks_is_safe(self):
        remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=self.hud)
        remote.device_update("Dev", [_make_real_param(_make_param("On/Off"))])
        # HUD still driven, no error without feedback sinks
        self.hud.commit.assert_called_once()


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

    def test_burst_reemits_layout_at_head_for_restart_resilience(self):
        """A HUD that starts after the surface misses the one-shot init LAYOUT.
        Every burst must re-emit the stored LAYOUT, before DEVICE, so the grid
        survives HUD/Ableton restart order."""
        hud_cells = [(0, 0, 'dial', 8, 0, 0), (2, 0, 'button', 4, 0, 0)]
        self.remote.init_layout(hud_cells)
        self.hud.reset_mock()  # drop the one-time init send

        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        self.remote.device_update("SomeDevice", params, hud_layout=hud_cells)

        self.hud.send_layout.assert_called_once_with(hud_cells)
        # LAYOUT must precede DEVICE in the burst (receiver needs cells first).
        layout_calls = [i for i, c in enumerate(self.hud.method_calls) if c[0] == 'send_layout']
        device_calls = [i for i, c in enumerate(self.hud.method_calls) if c[0] == 'send_device']
        self.assertTrue(layout_calls and device_calls and layout_calls[0] < device_calls[0])

    def test_burst_without_known_layout_does_not_send_layout(self):
        """If no layout was ever registered (init_layout not called), a burst
        must not invent a LAYOUT message."""
        params = [_make_real_param(_make_param(f"p{i}")) for i in range(3)]
        hud_cells = [(0, 0, 'dial', 8, 0, 0), (2, 0, 'button', 4, 0, 0)]
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
        self.remote.refresh_burst(BurstSnapshot(
            "Mixer",
            dials=[(0, SlotPayload("Vol", 0.8, 0, 1)), (1, EMPTY_SLOT)],
            buttons=[(0, SlotPayload("Mute", 1, 0, 1))],
        ))
        self.hud.send_device.assert_called_once_with("Mixer")
        self.hud.commit.assert_called_once_with(3)
        kinds = [c[0][0] for c in self.hud.send_slot.call_args_list]
        self.assertEqual(kinds, ['dial', 'dial', 'button'])

    def test_in_burst_flag_resets_even_on_exception(self):
        self.hud.commit.side_effect = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            self.remote.refresh_burst(BurstSnapshot("Dev", [], []))
        self.assertFalse(self.remote._in_burst)

    def test_no_page_means_no_page_info_emitted(self):
        # refresh_burst with page=None must not emit a PAGE line.
        self.remote.refresh_burst(BurstSnapshot("Dev", [], []))
        self.hud.send_page_info.assert_not_called()

    def test_device_update_forwards_page_labels_to_wire(self):
        params = [_make_real_param(_make_param("On/Off"))]
        self.remote.device_update(
            "Dev", params, hud_layout=[(0, 0, 'dial', 8, 0)],
            page=PageInfo(enc_page=2, enc_total=4, btn_page=1, btn_total=2,
                          enc_label='Best of', btn_label='Toggles'))
        self.hud.send_page_info.assert_called_once_with(2, 4, 1, 2, 'Best of', 'Toggles')


class TestSurfaceConfigEquivalence(unittest.TestCase):
    """SurfaceConfig (the template path) and the legacy keyword path must build
    an identically-configured Helpers."""

    def test_config_object_matches_legacy_kwargs(self):
        from source_modules.helpers import SurfaceConfig
        kwargs = dict(
            slot_assignments=[(1, 'slot1')],
            switch_slot_assignments=[(4, 'switch1')],
            parameter_mappings_raw=None,
            encoder_slot_count=16,
            hud_cells=[(0, 0, 'dial', 8, 0, 0)],
            hud_trigger='selection',
        )
        legacy = Helpers(Mock(), Mock(), **kwargs)
        via_config = Helpers(Mock(), Mock(), SurfaceConfig(**kwargs))
        self.assertEqual(legacy._slot_assignments, via_config._slot_assignments)
        self.assertEqual(legacy._switch_slot_assignments, via_config._switch_slot_assignments)
        self.assertEqual(legacy._resolver._banks_per_page, via_config._resolver._banks_per_page)
        self.assertEqual(legacy._hud_trigger, via_config._hud_trigger)
        self.assertEqual(legacy._hud_cells, via_config._hud_cells)


def _simpler_with_4_switches(buttons):
    """Helper: Helpers instance with 4 physical switches, matching the LC setup."""
    return Helpers(
        Mock(), Mock(),
        slot_assignments=[],
        switch_slot_assignments=[(4, 'switch1'), (5, 'switch2'), (6, 'switch3'), (7, 'switch4')],
        parameter_mappings_raw={"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": buttons,
        }]},
    )


def _simpler_device(param_names):
    """FakeSimpler with named parameters matching the given list."""
    params = [FakeParameter(name=n, original_name=n, is_quantized=True, min=0, max=2, value=0)
              for n in param_names]
    return FakeSimpler(parameters=params)


class TestButtonPaging(unittest.TestCase):
    """Button paging for known-class devices (BOB table)."""

    BUTTONS_8 = [{"name": f"btn{i}", "type": "param"} for i in range(8)]

    def _make_device(self):
        params = [FakeParameter(name=f"btn{i}", original_name=f"btn{i}",
                                is_quantized=True, min=0, max=1, value=0)
                  for i in range(8)]
        return FakeDevice(class_name="OriginalSimpler", parameters=params)

    def test_button_pages_count_known_class(self):
        helpers = _simpler_with_4_switches(self.BUTTONS_8)
        device = self._make_device()
        # 8 buttons, 4 switches per page → 2 pages
        self.assertEqual(helpers._button_pages_count(device), 2)

    def test_button_pages_count_one_page_when_few_buttons(self):
        helpers = _simpler_with_4_switches([{"name": "btn0", "type": "param"}])
        device = FakeDevice(
            class_name="OriginalSimpler",
            parameters=[FakeParameter(name="btn0", original_name="btn0")],
        )
        self.assertEqual(helpers._button_pages_count(device), 1)

    def test_page1_shows_first_4_buttons(self):
        helpers = _simpler_with_4_switches(self.BUTTONS_8)
        device = self._make_device()
        helpers.selected_device_changed(device)
        # switch_idx 0..3 on page 1 → buttons 0..3
        for switch_idx in range(4):
            info = helpers._resolve_switch(device, switch_idx)
            self.assertIsNotNone(info, f"page 1 switch {switch_idx} should resolve")
            self.assertEqual(info['alias'], f"btn{switch_idx}")

    def test_page2_shows_next_4_buttons(self):
        helpers = _simpler_with_4_switches(self.BUTTONS_8)
        device = self._make_device()
        helpers.selected_device_changed(device)
        helpers._button_page = 2
        # switch_idx 0..3 on page 2 → buttons 4..7
        for switch_idx in range(4):
            info = helpers._resolve_switch(device, switch_idx)
            self.assertIsNotNone(info, f"page 2 switch {switch_idx} should resolve")
            self.assertEqual(info['alias'], f"btn{switch_idx + 4}")

    def test_encoder_pager_also_advances_button_page(self):
        helpers = _simpler_with_4_switches(self.BUTTONS_8)
        device = self._make_device()
        helpers.selected_device_changed(device)
        # Add some encoder pages so pager has something to advance
        helpers._encoder_page = 1
        # Directly call inc with target='encoder'
        helpers._last_selected_device = device
        helpers.parameter_page_inc('encoder')
        self.assertEqual(helpers._button_page, 2,
                         "Button page should advance in sync with encoder page")

    def test_encoder_pager_dec_also_decrements_button_page(self):
        helpers = _simpler_with_4_switches(self.BUTTONS_8)
        device = self._make_device()
        helpers.selected_device_changed(device)
        helpers._button_page = 2
        helpers._encoder_page = 2
        helpers._last_selected_device = device
        helpers.parameter_page_dec('encoder')
        self.assertEqual(helpers._button_page, 1)

    def test_button_page_capped_at_max(self):
        helpers = _simpler_with_4_switches(self.BUTTONS_8)
        device = self._make_device()
        helpers.selected_device_changed(device)
        helpers._button_page = 2
        helpers._encoder_page = 2
        helpers._last_selected_device = device
        # Only 2 button pages — inc should not go to page 3
        helpers.parameter_page_inc('encoder')
        self.assertEqual(helpers._button_page, 2)


class TestButtonPagingUnknownClass(unittest.TestCase):
    """Button paging for unknown-class devices (quantized fallback) is unchanged."""

    def test_unknown_class_still_uses_button_slot_count(self):
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[],
            switch_slot_assignments=[(0, 'switch1'), (1, 'switch2')],
            button_slot_count=2,
        )
        params = [FakeParameter(name="q0", is_quantized=True, min=0, max=1),
                  FakeParameter(name="q1", is_quantized=True, min=0, max=1),
                  FakeParameter(name="q2", is_quantized=True, min=0, max=1),
                  FakeParameter(name="q3", is_quantized=True, min=0, max=1)]
        device = FakeDevice(class_name="Unknown", parameters=params)
        self.assertEqual(helpers._button_pages_count(device), 2)


class TestSimplerParamButtonDebugLogging(unittest.TestCase):
    """When a param button name isn't found, a log message is emitted."""

    def test_missing_param_button_logs_name(self):
        manager = Mock()
        helpers = _simpler_with_4_switches([
            {"lom_property": "playback_mode", "type": "enum"},
            {"name": "NonExistentParam", "type": "param"},
        ])
        helpers._manager = manager
        device = FakeSimpler(parameters=[FakeParameter(name="p0", original_name="p0")])
        helpers.selected_device_changed(device)
        # switch1 (enum) resolves fine; switch2 (bad param name) should log
        info1 = helpers._resolve_switch(device, 0)
        self.assertIsNotNone(info1, "lom_property button should still resolve")
        info2 = helpers._resolve_switch(device, 1)
        self.assertIsNone(info2, "bad param should not resolve")
        manager.log_message.assert_called()
        log_msg = manager.log_message.call_args[0][0]
        self.assertIn("NonExistentParam", log_msg)


class TestM4LDeviceDisambiguation(unittest.TestCase):
    """All Max-for-Live plugins share class_name='MxDeviceMidiEffect' (or
    -AudioEffect). The custom-mapping table must match on device.name so an
    entry for 'SQ Sequencer' is not applied to every M4L plugin loaded."""

    def _mappings(self):
        return {"devices": [
            {
                "className": "MxDeviceMidiEffect",
                "deviceName": "SQ Sequencer",
                "encoders": [{"name": "PStep1"}],
                "buttons": [{"name": "FollowRoot", "type": "param"}],
            },
            {
                "className": "MxDeviceMidiEffect",
                "deviceName": "Other M4L",
                "encoders": [{"name": "Aux1"}],
                "buttons": [],
            },
        ]}

    def test_matching_m4l_device_resolves_to_its_own_entry(self):
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1')],
            switch_slot_assignments=[(0, 'switch1')],
            parameter_mappings_raw=self._mappings(),
        )
        device = FakeDevice(
            class_name="MxDeviceMidiEffect", name="Other M4L",
            parameters=[
                FakeParameter(name="Device On"),
                FakeParameter(name="Aux1", min=0, max=1, value=0),
            ],
        )
        # encoder 1 should resolve to "Aux1" via the "Other M4L" entry,
        # not to "PStep1" from the SQ Sequencer entry.
        rp = helpers._resolve_encoder(device, 1)
        self.assertIsNotNone(rp)
        self.assertIs(rp.param, device.parameters[1])

    def test_unmatched_m4l_device_falls_back_to_unknown_class(self):
        """An M4L device with no JSON entry must not pick up another M4L
        device's mapping. It should be treated as unknown."""
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1')],
            switch_slot_assignments=[(0, 'switch1')],
            parameter_mappings_raw=self._mappings(),
        )
        device = FakeDevice(
            class_name="MxDeviceMidiEffect", name="Yet Another M4L",
            parameters=[
                FakeParameter(name="Device On"),
                FakeParameter(name="Random", min=0, max=1, value=0),
            ],
        )
        self.assertFalse(helpers.has_user_defined_parameters(device))
        # _resolve_switch on unknown class falls back to quantized chunking,
        # which finds nothing here — and crucially does not try "FollowRoot".
        info = helpers._resolve_switch(device, 0)
        self.assertIsNone(info)

    def test_standard_banks_skipped_for_m4l_classes(self):
        """Even if a class_name collision existed in DEVICE_BANKS, no M4L
        plugin should ever receive standard-bank pages."""
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[],
            switch_slot_assignments=[],
            parameter_mappings_raw=None,
            device_banks={"MxDeviceMidiEffect": (("X", "Y", "Z", "W", "V", "U", "T", "S"),)},
            bank_names={},
        )
        device = FakeDevice(class_name="MxDeviceMidiEffect", name="Anything")
        self.assertEqual(helpers._standard_banks(device), ())


class TestEncoderResolveGapPreservesHudAlignment(unittest.TestCase):
    """If `_resolve_encoder` returns None for one encoder, subsequent encoders
    must NOT shift left on the HUD wire. Each c_idx maps to a fixed wire
    position; a failed resolve renders EMPTY_SLOT in that position."""

    def test_missing_encoder_leaves_empty_slot_not_shifted_neighbour(self):
        # Reverb-shape mock: standard banks define names, but the first
        # parameter's original_name does NOT match the bank, simulating a
        # bank-data mismatch. Encoder 13 (slot 12, bank 1 slot 4) should
        # still appear at wire_idx 12, not shifted to wire_idx 11.
        params = [FakeParameter(name="Device On", original_name="Device On")]
        # 16 params, names match bank slots 1..15 but slot 0 does NOT match
        bank_names_in_order = [
            "WRONG_NAME", "B", "C", "D", "E", "F", "G", "H",
            "I", "J", "K", "L", "HiShelf Gain", "N", "O", "P",
        ]
        for i, nm in enumerate(bank_names_in_order):
            real_name = nm if nm != "WRONG_NAME" else "ActualParamName"
            params.append(FakeParameter(name=real_name, original_name=real_name, min=0, max=1))
        device = FakeDevice(class_name="Reverb", name="Reverb", parameters=params)

        banks = {"Reverb": (tuple(bank_names_in_order[:8]), tuple(bank_names_in_order[8:]))}
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(c, f'slot{c}') for c in range(1, 17)],
            switch_slot_assignments=[],
            parameter_mappings_raw=None,
            encoder_slot_count=16,
            hud_cells=[(0, 0, 'dial', 16, 0)],
            device_banks=banks, bank_names={},
        )
        # encoder 1 fails to resolve (bank says "In Filter Freq" — i.e. WRONG_NAME);
        # encoder 13 resolves to "HiShelf Gain"
        self.assertIsNone(helpers._resolve_encoder(device, 1))
        self.assertIsNotNone(helpers._resolve_encoder(device, 13))

        # Now drive the full burst and verify wire_idx 12 carries HiShelf Gain.
        # source='nav' so the burst actually fires (default show-hud-on is
        # controller-nav, which suppresses non-nav selection changes).
        hud = Mock()
        helpers._remote = Remote(manager=Mock(), osc_client=Mock(), hud_client=hud)
        helpers.selected_device_changed(device, source='nav')
        dial_calls = [c for c in hud.send_slot.call_args_list if c[0][0] == 'dial']
        self.assertEqual(len(dial_calls), 16)
        # wire_idx 0 (encoder 1) is empty due to failed resolve
        self.assertEqual(dial_calls[0][0][2], EMPTY_SLOT.name)
        # wire_idx 12 (encoder 13) still shows HiShelf Gain — no left shift
        self.assertEqual(dial_calls[12][0][2], "HiShelf Gain")


class TestBankResolverFallsBackToDisplayName(unittest.TestCase):
    """Standard-bank lookup uses `_resolve_bank_param`, which falls back to
    `Parameter.name` when `original_name` doesn't match. The bank data was
    scraped from Live's display-name table (`_Generic/Devices.py`); a
    handful of built-in params (e.g. Reverb's filter cluster) expose a
    different `original_name`, so the strict-only lookup blanks them.

    The strict resolver `_resolve_param_by_name` stays original_name-only
    so user-renamed Rack macros don't hijack BOB/switch lookups."""

    def test_bank_resolves_via_display_name_when_original_name_differs(self):
        params = [
            FakeParameter(name="Device On", original_name="Device On"),
            # Display name matches the bank entry; original_name does not.
            FakeParameter(name="In Filter Freq", original_name="HpLpFreq",
                          min=0, max=1, value=0),
        ]
        device = FakeDevice(class_name="Reverb", name="Reverb", parameters=params)
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1')],
            switch_slot_assignments=[],
            parameter_mappings_raw=None,
            encoder_slot_count=16,
            device_banks={"Reverb": (("In Filter Freq", "x", "x", "x", "x", "x", "x", "x"),)},
            bank_names={},
        )
        rp = helpers._resolve_encoder(device, 1)
        self.assertIsNotNone(rp, "bank resolver should fall back to Parameter.name")
        self.assertIs(rp.param, params[1])

    def test_strict_resolver_still_ignores_display_name_collisions(self):
        # Rack: original_name='Macro 1' on the authored param, but another
        # param happens to have display name='Macro 1'. Strict lookup of
        # 'Macro 1' must return the original_name match, not the rename.
        authored = FakeParameter(name="Brightness", original_name="Macro 1",
                                 min=0, max=1, value=0)
        collider = FakeParameter(name="Macro 1", original_name="something_else",
                                 min=0, max=1, value=0)
        params = [FakeParameter(name="Device On", original_name="Device On"),
                  authored, collider]
        device = FakeDevice(class_name="Rack", name="Rack", parameters=params)
        helpers = Helpers(Mock(), Mock(), parameter_mappings_raw=None)
        self.assertIs(helpers._resolve_param_by_name(device, "Macro 1"), authored)


class TestBankResolveLogsAvailableNames(unittest.TestCase):
    """When a standard-bank name doesn't match any original_name, log the
    available names so the bank data can be diagnosed."""

    def test_logs_available_names_on_miss(self):
        manager = Mock()
        params = [FakeParameter(name="Device On", original_name="Device On"),
                  FakeParameter(name="Real", original_name="Real")]
        device = FakeDevice(class_name="Reverb", name="Reverb", parameters=params)
        helpers = Helpers(
            manager, Mock(),
            slot_assignments=[(1, 'slot1')],
            switch_slot_assignments=[],
            parameter_mappings_raw=None,
            encoder_slot_count=16,
            device_banks={"Reverb": (("Not Real", "x", "x", "x", "x", "x", "x", "x"),)},
            bank_names={},
        )
        rp = helpers._resolve_encoder(device, 1)
        self.assertIsNone(rp)
        manager.log_message.assert_called()
        log_msg = manager.log_message.call_args[0][0]
        self.assertIn("Not Real", log_msg)
        self.assertIn("Real", log_msg)


class TestRackBobButtonsOnlyKeepsMacrosOnPageOne(unittest.TestCase):
    """A Rack BOB entry with only buttons (no encoders) must NOT push Macro
    banks onto page 2 — encoders should still resolve to Macros on page 1."""

    def test_buttons_only_bob_does_not_shift_encoders(self):
        mappings = {"devices": [{
            "className": "AudioEffectGroupDevice",
            "deviceName": "MyRack",
            "encoders": [],
            "buttons": [{"name": "Macro 5", "min_max": True}],
        }]}
        params = [FakeParameter(name="Device On", original_name="Device On")]
        for i in range(1, 9):
            params.append(FakeParameter(name=f"Macro {i}", original_name=f"Macro {i}",
                                        min=0, max=127, value=0))
        device = FakeDevice(class_name="AudioEffectGroupDevice", name="MyRack",
                            parameters=params)
        helpers = Helpers(
            Mock(), Mock(),
            slot_assignments=[(1, 'slot1')],
            switch_slot_assignments=[(0, 'switch1')],
            parameter_mappings_raw=mappings,
            device_banks={"AudioEffectGroupDevice": (
                ("Macro 1", "Macro 2", "Macro 3", "Macro 4",
                 "Macro 5", "Macro 6", "Macro 7", "Macro 8"),)},
            bank_names={},
        )
        rp = helpers._resolve_encoder(device, 1)
        self.assertIsNotNone(rp, "encoder 1 should resolve to Macro 1 on page 1")
        self.assertIs(rp.param, params[1])
        self.assertEqual(helpers._encoder_pages_count(device), 1)


if __name__ == '__main__':
    unittest.main()
