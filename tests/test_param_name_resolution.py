"""Tests for name-based device parameter resolution.

Replaces the legacy index-based (`number`) addressing — see
`parameter-update-requirements.md`. Encoders and buttons are addressed by
`Parameter.original_name` and resolved through a two-tier page model:

  page 1: Best-of (BOB), authored in custom_device_mappings.json.
  page 2+: standard banks bundled from Ableton's _Generic/Devices.py, paired
           two-banks-per-page on 16-encoder controllers.

A name that doesn't resolve produces an EMPTY slot — never a wrong-index
silent fallback.
"""

import unittest
from dataclasses import dataclass, field
from unittest.mock import Mock

from source_modules.helpers import Helpers, SurfaceConfig


@dataclass
class FakeParameter:
    original_name: str = ""
    name: str = ""  # user-rename (unstable; resolver must ignore)
    min: float = 0.0
    max: float = 1.0
    value: float = 0.0
    is_quantized: bool = False

    def __post_init__(self):
        if not self.name:
            self.name = self.original_name


@dataclass
class FakeDevice:
    parameters: list = field(default_factory=list)
    name: str = "Test"
    class_name: str = "Test"


def _params(original_names, total=50):
    """Build a parameter list, filling unspecified slots with `slotN` names.

    `original_names` is a dict {index: original_name} OR a list of names
    starting at index 0.
    """
    if isinstance(original_names, list):
        original_names = {i: n for i, n in enumerate(original_names)}
    out = []
    for i in range(total):
        nm = original_names.get(i, f"slot{i}")
        out.append(FakeParameter(original_name=nm))
    return out


SIM_BANK1 = ('Ve Attack', 'Ve Decay', 'Ve Sustain', 'Ve Release',
             'S Start', 'S Loop Length', 'S Length', 'S Loop Fade')
SIM_BANK2 = ('Fe Attack', 'Fe Decay', 'Fe Sustain', 'Fe Release',
             'Filter Freq', 'Filter Res', 'Filt < Vel', 'Fe < Env')
SIM_BANK3 = ('L Attack', 'L Rate', 'L R < Key', 'L Wave',
             'Vol < LFO', 'Filt < LFO', 'Pitch < LFO', 'Pan < LFO')
SIM_BANK4 = ('Pe Attack', 'Pe Decay', 'Pe Sustain', 'Pe Release',
             'Glide Time', 'Spread', 'Pan', 'Volume')
SIM_BANKS = (SIM_BANK1, SIM_BANK2, SIM_BANK3, SIM_BANK4)
SIM_BANK_NAMES = ('Amplitude', 'Filter', 'LFO', 'Pitch Modifiers')


def _device_banks():
    return {'OriginalSimpler': SIM_BANKS}


def _bank_names():
    return {'OriginalSimpler': SIM_BANK_NAMES}


def _all_simpler_names():
    """Every name a fully-loaded Simpler param list needs."""
    names = ['Device On']
    for bank in SIM_BANKS:
        names.extend(bank)
    # BOB references some additional names too.
    names.extend(['Fade In', 'Fade Out', 'Transpose', 'Detune', 'Filter Morph', 'Filter Drive'])
    return names


def _simpler_device(missing=()):
    """Build a Simpler-shaped device where every standard-bank parameter is
    present at some index (order doesn't matter — resolution is by name)."""
    names = [n for n in _all_simpler_names() if n not in missing]
    return FakeDevice(class_name='OriginalSimpler', parameters=_params(names))


def _helpers(parameter_mappings_raw=None, slot_count=16, button_slot_count=8,
             slot_assignments=None, switch_slot_assignments=None):
    return Helpers(
               Mock(),
               Mock(),
               SurfaceConfig(
                   slot_assignments=slot_assignments or [(c, f'slot{c}') for c in range(1, slot_count + 1)],
                   switch_slot_assignments=switch_slot_assignments or [],
                   parameter_mappings_raw=parameter_mappings_raw,
                   encoder_slot_count=slot_count,
                   button_slot_count=button_slot_count,
                   device_banks=_device_banks(),
                   bank_names=_bank_names(),
               ),
           )


class TestResolveParamByName(unittest.TestCase):
    """The single-lookup primitive: original_name -> Parameter."""

    def test_returns_param_when_original_name_matches(self):
        helpers = _helpers()
        device = _simpler_device()
        p = helpers._resolver.resolve_param_by_name(device, 'Filter Freq')
        self.assertIsNotNone(p)
        self.assertEqual(p.original_name, 'Filter Freq')

    def test_returns_none_when_name_missing(self):
        helpers = _helpers()
        device = _simpler_device(missing=('Filter Freq',))
        self.assertIsNone(helpers._resolver.resolve_param_by_name(device, 'Filter Freq'))

    def test_ignores_user_renamed_name_field(self):
        """User can rename a param; resolver must match original_name only."""
        helpers = _helpers()
        device = _simpler_device()
        # Pretend the user renamed "Filter Freq" to "Brightness" via a macro.
        target = next(p for p in device.parameters if p.original_name == 'Filter Freq')
        target.name = 'Brightness'
        self.assertIs(helpers._resolver.resolve_param_by_name(device, 'Filter Freq'), target)
        self.assertIsNone(helpers._resolver.resolve_param_by_name(device, 'Brightness'))


class TestBobPageEncoderResolution(unittest.TestCase):
    """Page 1 reads from the authored BOB JSON (custom_device_mappings.json)."""

    BOB_ENCODERS = [
        {"name": "S Start", "display": "Start"},
        {"name": "Filter Freq"},
        {"name": "Ve Attack"},
        {"name": "Volume"},
    ]

    def _h(self, slot_count=16):
        return _helpers(
            parameter_mappings_raw={"devices": [{
                "className": "OriginalSimpler",
                "encoders": self.BOB_ENCODERS,
                "buttons": [],
            }]},
            slot_count=slot_count,
        )

    def test_encoder_resolves_through_bob_name(self):
        helpers = self._h()
        device = _simpler_device()
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        ve_attack = next(p for p in device.parameters if p.original_name == 'S Start')
        self.assertAlmostEqual(ve_attack.value, 1.0, places=2)

    def test_missing_bob_name_does_not_drive_any_param(self):
        """If the authored BOB references a name not present on the device,
        the encoder is dead — must NOT fall through to an index-based slot."""
        helpers = _helpers(parameter_mappings_raw={"devices": [{
            "className": "OriginalSimpler",
            "encoders": [{"name": "Filter Freq"}],
            "buttons": [],
        }]})
        device = _simpler_device(missing=('Filter Freq',))
        before = [p.value for p in device.parameters]
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        after = [p.value for p in device.parameters]
        self.assertEqual(before, after, "No parameter should have moved")

    def test_bob_display_overrides_alias(self):
        helpers = self._h()
        device = _simpler_device()
        helpers.device_parameter_action(device, 1, 22, 64.0, "fn")
        rp = helpers._remote.parameter_updated.call_args[0][0]
        self.assertEqual(rp.alias, 'Start')


class TestStandardBankPages(unittest.TestCase):
    """Pages 2+ pull from bundled Ableton banks, paired 2-banks-per-page."""

    def test_page_1_slot_1_is_bank1_slot_0(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        helpers.selected_device_changed(device)
        self.assertEqual(helpers._resolver.encoder_page, 1)
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        ve_attack = next(p for p in device.parameters if p.original_name == 'Ve Attack')
        self.assertAlmostEqual(ve_attack.value, 1.0, places=2)

    def test_page_1_slot_9_is_bank2_slot_0(self):
        """On a 16-encoder controller, slot 9 is the first slot of the second
        bank paired onto page 1."""
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        helpers.selected_device_changed(device)
        helpers.device_parameter_action(device, 9, 22, 127.0, "fn")
        fe_attack = next(p for p in device.parameters if p.original_name == 'Fe Attack')
        self.assertAlmostEqual(fe_attack.value, 1.0, places=2)

    def test_page_2_uses_banks_3_and_4(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        helpers.selected_device_changed(device)
        helpers.parameter_page_inc('encoder')
        self.assertEqual(helpers._resolver.encoder_page, 2)
        # slot 1 -> L Attack (bank3 slot 0)
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        # slot 9 -> Pe Attack (bank4 slot 0)
        helpers.device_parameter_action(device, 9, 22, 127.0, "fn")
        l_attack = next(p for p in device.parameters if p.original_name == 'L Attack')
        pe_attack = next(p for p in device.parameters if p.original_name == 'Pe Attack')
        self.assertAlmostEqual(l_attack.value, 1.0, places=2)
        self.assertAlmostEqual(pe_attack.value, 1.0, places=2)

    def test_standard_bank_missing_name_does_not_resolve(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device(missing=('Ve Attack',))
        helpers.selected_device_changed(device)
        before = [p.value for p in device.parameters]
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        self.assertEqual([p.value for p in device.parameters], before)


class TestBankOnlyDevice(unittest.TestCase):
    """When a device has standard banks but no BOB authored in
    custom_device_mappings.json, page 1 shows the first standard bank
    (no empty 'placeholder' BOB page)."""

    def test_page_1_resolves_to_bank0_when_no_bob(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        helpers.selected_device_changed(device)
        self.assertEqual(helpers._resolver.encoder_page, 1)
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        ve_attack = next(p for p in device.parameters if p.original_name == 'Ve Attack')
        self.assertAlmostEqual(ve_attack.value, 1.0, places=2)

    def test_page_1_slot_9_is_bank1_when_no_bob(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        helpers.selected_device_changed(device)
        helpers.device_parameter_action(device, 9, 22, 127.0, "fn")
        fe_attack = next(p for p in device.parameters if p.original_name == 'Fe Attack')
        self.assertAlmostEqual(fe_attack.value, 1.0, places=2)

    def test_page_count_when_no_bob_omits_bob_page(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        # 4 banks paired 2-per-page → 2 pages, no extra BOB page.
        self.assertEqual(helpers._resolver.encoder_pages_count(device), 2)

    def test_page_1_label_pairs_first_two_bank_names_when_no_bob(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        self.assertEqual(helpers._resolver.page_label_for(device, 1), 'Amplitude / Filter')
        self.assertEqual(helpers._resolver.page_label_for(device, 2), 'LFO / Pitch Modifiers')


class TestPageCount(unittest.TestCase):
    """Pages = 1 (BOB) + ceil(len(banks) / 2)."""

    def test_known_device_page_count(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        # SIM has 4 banks, 2 banks per page, no BOB -> ceil(4/2) = 2
        self.assertEqual(helpers._resolver.encoder_pages_count(device), 2)

    def test_unknown_device_falls_back_to_chunked_pages(self):
        helpers = _helpers(parameter_mappings_raw=None, slot_count=16)
        # 33 params -> skip on/off -> 32 -> 4 banks of 8 -> 2 paired pages -> 1 BOB? no, no BOB → just 2
        device = FakeDevice(class_name='WhoKnows',
                            parameters=_params({i: f'p{i}' for i in range(33)}, total=33))
        # We bundle banks of 8 from device.parameters[1:], pair onto 16-slot pages.
        # 32 params / 8 = 4 banks -> ceil(4/2) = 2 pages. No BOB defined → 2 total.
        self.assertEqual(helpers._resolver.encoder_pages_count(device), 2)

    def test_button_pages_capped_at_one_for_known_class(self):
        """Buttons live on the BOB page only — standard-bank pages don't surface
        buttons (requirements answer #5)."""
        helpers = _helpers(parameter_mappings_raw={"devices": [{
            "className": "OriginalSimpler",
            "encoders": [],
            "buttons": [{"name": "Trigger Mode"}],
        }]})
        device = _simpler_device(missing=())
        # Add Trigger Mode at some slot
        device.parameters.append(FakeParameter(original_name='Trigger Mode'))
        self.assertEqual(helpers._resolver.button_pages_count(device), 1)


class TestNamedSwitchResolution(unittest.TestCase):
    """Param-kind buttons resolve by name; LOM kinds untouched."""

    def test_button_param_resolves_by_name(self):
        helpers = _helpers(
            parameter_mappings_raw={"devices": [{
                "className": "OriginalSimpler",
                "encoders": [],
                "buttons": [{"name": "Trigger Mode"}],
            }]},
            switch_slot_assignments=[(0, 1)],
        )
        device = _simpler_device()
        device.parameters.append(FakeParameter(original_name='Trigger Mode',
                                               min=0, max=2, is_quantized=True))
        helpers.switch_slot_action(device, 1, 127, 'fn')
        target = next(p for p in device.parameters if p.original_name == 'Trigger Mode')
        self.assertEqual(target.value, 1)

    def test_button_with_missing_name_does_nothing(self):
        helpers = _helpers(
            parameter_mappings_raw={"devices": [{
                "className": "OriginalSimpler",
                "encoders": [],
                "buttons": [{"name": "Nonexistent"}],
            }]},
            switch_slot_assignments=[(0, 1)],
        )
        device = _simpler_device()
        before = [p.value for p in device.parameters]
        helpers.switch_slot_action(device, 1, 127, 'fn')
        self.assertEqual([p.value for p in device.parameters], before)


class TestGroupSelectorUsesOriginalName(unittest.TestCase):
    """`Parameter.name` is unstable (user macros) — selectors must read
    `original_name`."""

    def test_selector_lookup_by_original_name(self):
        helpers = _helpers(
            parameter_mappings_raw={"devices": [{
                "className": "OriginalSimpler",
                "encoders": [{
                    "controlledBy": "LFO T Mode",
                    "group": [
                        {"name": "L Rate", "activeWhen": [0]},
                        {"name": "L Attack", "activeWhen": [1]},
                    ],
                }],
                "buttons": [],
            }]},
            slot_count=16,
        )
        device = _simpler_device()
        # Selector param: original_name="LFO T Mode" but user renamed it.
        selector = FakeParameter(original_name='LFO T Mode', value=1,
                                 min=0, max=2, is_quantized=True)
        selector.name = 'My Mode'  # user rename — must be ignored
        device.parameters.append(selector)
        helpers.device_parameter_action(device, 1, 22, 127.0, "fn")
        l_attack = next(p for p in device.parameters if p.original_name == 'L Attack')
        self.assertAlmostEqual(l_attack.value, 1.0, places=2)


class TestBankHudLabels(unittest.TestCase):
    """HUD page-info burst carries a label string per page."""

    def test_bob_page_label_is_best_of(self):
        helpers = _helpers(parameter_mappings_raw={"devices": [{
            "className": "OriginalSimpler",
            "encoders": [{"name": "Filter Freq"}],
            "buttons": [],
        }]})
        device = _simpler_device()
        helpers.selected_device_changed(device)
        self.assertEqual(helpers._resolver.page_label_for(device, 1), 'Best of')

    def test_standard_page_label_pairs_bank_names(self):
        helpers = _helpers(parameter_mappings_raw=None)
        device = _simpler_device()
        # No BOB -> page 1 = bank 0 + bank 1
        self.assertEqual(helpers._resolver.page_label_for(device, 1), 'Amplitude / Filter')
        self.assertEqual(helpers._resolver.page_label_for(device, 2), 'LFO / Pitch Modifiers')


class TestLiveDeviceBanksSnapshot(unittest.TestCase):
    """The bundled snapshot module must export the expected mappings."""

    def test_snapshot_module_exposes_simpler_banks(self):
        from data import live_device_banks
        self.assertIn('OriginalSimpler', live_device_banks.DEVICE_BANKS)
        banks = live_device_banks.DEVICE_BANKS['OriginalSimpler']
        # 4 banks of 8 names each.
        self.assertEqual(len(banks), 4)
        for bank in banks:
            self.assertEqual(len(bank), 8)
        self.assertIn('Filter Freq', banks[1])

    def test_snapshot_exposes_bank_names(self):
        from data import live_device_banks
        names = live_device_banks.BANK_NAMES['OriginalSimpler']
        self.assertEqual(names, ('Amplitude', 'Filter', 'LFO', 'Pitch Modifiers'))


if __name__ == '__main__':
    unittest.main()
