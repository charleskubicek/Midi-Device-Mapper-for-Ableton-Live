"""Smart-zoning resolver tier (plan: grid-po16-synth-surface-plan, step D).

A zoned synth resolves page-1 pots/buttons through the fixed zone template
(slot -> role) + the per-synth role->param table, ahead of BOB / factory banks.
With the toggle off, or for a device with no `synths` entry, behavior is
identical to today (regression-pinned in test_param_resolver.py)."""
import unittest

from source_modules.param_resolver import (
    ParameterResolver, _build_device_table, _build_zone_tables,
)
from tests.test_param_resolver import FakeParam, FakeDevice


# Minimal template: 2 encoder slots + 2 button slots, two synths. The real
# shipped template is 32 pots / 16 buttons; the resolver logic is slot-count
# agnostic, so a tiny fixture exercises every branch.
ZONE_TABLES = {
    'template': {
        'encoders': [
            {'slot': 1, 'role': 'amp_attack', 'zone': 'env', 'display': 'Amp attack'},
            {'slot': 2, 'role': 'osc1_timbre', 'zone': 'osc', 'display': 'Osc 1 timbre'},
        ],
        'buttons': [
            {'slot': 1, 'role': 'filter_on', 'zone': 'filter', 'display': 'Filter on'},
            {'slot': 2, 'role': 'unison_on', 'zone': 'global', 'display': 'Unison on'},
        ],
    },
    'synths': {
        'InstrumentVector': {
            'display': 'Wavetable',
            'encoders': {
                'amp_attack': {'name': 'Amp Attack'},
                'osc1_timbre': {'name': 'Osc 1 Pos'},
            },
            # note: no 'unison_on' button -> that role is unmapped for Wavetable
            'buttons': {
                'filter_on': {'name': 'Filter 1 On'},
            },
        },
        'UltraAnalog': {
            'display': 'Analog',
            'encoders': {
                'amp_attack': {'name': 'AEG1 Attack'},
                # no osc1_timbre override with a wrong name -> use a real one
                'osc1_timbre': {'name': 'OSC1 Shape'},
            },
            'buttons': {
                'filter_on': {'name': 'F1 On/Off'},
                'unison_on': {'name': 'Unison On/Off'},
            },
        },
    },
}


def _zoned_resolver(smart_zoning=True, device_banks=None, bank_names=None,
                    banks_per_page=2):
    logs = []
    r = ParameterResolver(
        device_table=_build_device_table(None),
        device_banks=device_banks or {}, bank_names=bank_names or {},
        banks_per_page=banks_per_page, button_switch_count=0,
        button_slot_count=16, log=logs.append,
        smart_zoning=smart_zoning,
        zone_tables=_build_zone_tables(ZONE_TABLES))
    return r, logs


def _wavetable():
    return FakeDevice('InstrumentVector', [
        FakeParam('Amp Attack', value=0.3),
        FakeParam('Osc 1 Pos', value=0.5),
        FakeParam('Filter 1 On', value=1.0, is_quantized=True),
    ])


def _analog():
    return FakeDevice('UltraAnalog', [
        FakeParam('AEG1 Attack'),
        FakeParam('OSC1 Shape'),
        FakeParam('F1 On/Off', is_quantized=True),
        FakeParam('Unison On/Off', is_quantized=True),
    ])


class TestZonedEncoders(unittest.TestCase):
    def test_slot1_resolves_amp_attack_on_page1(self):
        r, _ = _zoned_resolver()
        rp = r.resolve_encoder(_wavetable(), 1)
        self.assertIsNotNone(rp)
        self.assertEqual(rp.param.name, 'Amp Attack')

    def test_slot2_resolves_osc1_timbre(self):
        r, _ = _zoned_resolver()
        rp = r.resolve_encoder(_wavetable(), 2)
        self.assertEqual(rp.param.name, 'Osc 1 Pos')

    def test_same_slot_different_synth_same_role(self):
        # The whole point: slot 1 is "amp attack" on every enrolled synth.
        r, _ = _zoned_resolver()
        self.assertEqual(r.resolve_encoder(_wavetable(), 1).param.name, 'Amp Attack')
        self.assertEqual(r.resolve_encoder(_analog(), 1).param.name, 'AEG1 Attack')

    def test_toggle_off_is_not_zoned(self):
        # smart_zoning off -> no zone tier; unknown class falls back to identity.
        r, _ = _zoned_resolver(smart_zoning=False)
        rp = r.resolve_encoder(_wavetable(), 1)
        # identity fallback skips index 0 and quantized; slot 1 (idx0) is param[1]
        self.assertEqual(rp.param.name, 'Osc 1 Pos')

    def test_unknown_class_not_zoned(self):
        r, _ = _zoned_resolver()
        dev = FakeDevice('SomeVST', [FakeParam('A'), FakeParam('B'), FakeParam('C')])
        rp = r.resolve_encoder(dev, 1)
        # not in synths -> identity fallback (idx0 skipped)
        self.assertEqual(rp.param.name, 'B')

    def test_mapped_name_miss_logs(self):
        # A role mapped to a param the device doesn't have -> None + a log line
        # (byte-drift bug), unlike a template hole which is silent.
        r, logs = _zoned_resolver()
        bad = FakeDevice('InstrumentVector', [FakeParam('Nope')])
        self.assertIsNone(r.resolve_encoder(bad, 1))
        self.assertTrue(any('Amp Attack' in m for m in logs))


class TestZonedButtons(unittest.TestCase):
    def test_button_slot1_resolves(self):
        r, _ = _zoned_resolver()
        info = r.resolve_switch(_wavetable(), 0)  # switch_idx 0 == button slot 1
        self.assertEqual(info['param'].name, 'Filter 1 On')

    def test_unmapped_button_role_is_silent(self):
        # Wavetable has no 'unison_on' -> button slot 2 unmapped: None, no log.
        r, logs = _zoned_resolver()
        self.assertIsNone(r.resolve_switch(_wavetable(), 1))
        self.assertEqual(logs, [])

    def test_analog_fills_unison_button(self):
        r, _ = _zoned_resolver()
        info = r.resolve_switch(_analog(), 1)
        self.assertEqual(info['param'].name, 'Unison On/Off')

    def test_button_slot_outside_template_falls_through(self):
        # The 2-button fixture template owns slots 1-2. A slot beyond it (like
        # shift-mode's grid-1 second bank on slots 17-32) must NOT be swallowed
        # by the zone tier — it falls through to the pre-zoning fallback so those
        # keys keep working on a zoned synth.
        r, _ = _zoned_resolver()
        params = [FakeParam(f'p{i}', is_quantized=True) for i in range(20)]
        dev = FakeDevice('InstrumentVector', params)
        info = r.resolve_switch(dev, 5)  # switch_idx 5 -> slot 6, outside template
        self.assertIsNotNone(info)
        self.assertEqual(info['kind'], 'param')

    def test_multivalue_quantized_button_emits_cycleable_shape(self):
        # B16 Operator == Algorithm (quantized 0-10). The zone tier emits
        # has_range=False; the switch handler then cycles a quantized param over
        # its own min/max (helpers.switch_slot_action `elif is_q`). Pin the shape
        # the handler relies on so a regression here is caught at resolve time.
        tables = _build_zone_tables({
            'template': {
                'encoders': [{'slot': 1, 'role': 'x', 'zone': 'osc'},
                             {'slot': 2, 'role': 'y', 'zone': 'osc'}],
                'buttons': [{'slot': 1, 'role': 'algo', 'zone': 'global'},
                            {'slot': 2, 'role': 'z', 'zone': 'global'}],
            },
            'synths': {'Operator': {'display': 'Operator',
                                    'encoders': {},
                                    'buttons': {'algo': {'name': 'Algorithm'}}}},
        })
        logs = []
        r = ParameterResolver(
            device_table={}, device_banks={}, bank_names={}, banks_per_page=2,
            button_switch_count=0, button_slot_count=16, log=logs.append,
            smart_zoning=True, zone_tables=tables)
        dev = FakeDevice('Operator', [FakeParam('Algorithm', mn=0.0, mx=10.0,
                                                is_quantized=True)])
        info = r.resolve_switch(dev, 0)
        self.assertEqual(info['param'].name, 'Algorithm')
        self.assertFalse(info['has_range'])
        self.assertTrue(info['param'].is_quantized)
        self.assertEqual((info['param'].min, info['param'].max), (0.0, 10.0))


class TestZoneColors(unittest.TestCase):
    _TABLES = {
        'template': {
            'encoders': [{'slot': 1, 'role': 'a', 'zone': 'osc'},
                         {'slot': 2, 'role': 'b', 'zone': 'filter'}],
            'buttons': [{'slot': 1, 'role': 'c', 'zone': 'filter'},
                        {'slot': 2, 'role': 'd', 'zone': 'character'}],
        },
        'zone_colors': {'osc': 'E0A33E', 'filter': '33B5A6', 'character': '5B8BC4'},
        'synths': {'InstrumentVector': {'display': 'Wavetable',
                                        'encoders': {'a': {'name': 'Osc 1 Pos'}},
                                        'buttons': {}}},
    }

    def _r(self, smart_zoning=True):
        return ParameterResolver(
            device_table={}, device_banks={}, bank_names={}, banks_per_page=2,
            button_switch_count=0, button_slot_count=16, log=lambda *_: None,
            smart_zoning=smart_zoning, zone_tables=_build_zone_tables(self._TABLES))

    def test_zone_for_slot(self):
        r = self._r()
        self.assertEqual(r.zone_for_slot('dial', 1), 'osc')
        self.assertEqual(r.zone_for_slot('dial', 2), 'filter')
        self.assertEqual(r.zone_for_slot('button', 2), 'character')

    def test_color_for_slot(self):
        r = self._r()
        self.assertEqual(r.color_for_slot('dial', 1), 'E0A33E')
        self.assertEqual(r.color_for_slot('button', 1), '33B5A6')
        self.assertEqual(r.color_for_slot('button', 2), '5B8BC4')

    def test_slot_outside_template_has_no_color(self):
        self.assertIsNone(self._r().color_for_slot('dial', 99))

    def test_no_zone_tables_no_color(self):
        r = ParameterResolver(device_table={}, device_banks={}, bank_names={},
                              banks_per_page=2, button_switch_count=0,
                              button_slot_count=16, log=lambda *_: None)
        self.assertIsNone(r.color_for_slot('dial', 1))
        self.assertIsNone(r.zone_for_slot('dial', 1))


class TestZonedPaging(unittest.TestCase):
    def test_zone_is_page1_banks_from_page2(self):
        banks = {'InstrumentVector': (('Bk A p0', 'Bk A p1'),)}
        names = {'InstrumentVector': ['Bank A']}
        r, _ = _zoned_resolver(device_banks=banks, bank_names=names)
        dev = FakeDevice('InstrumentVector', [
            FakeParam('Amp Attack'), FakeParam('Osc 1 Pos'),
            FakeParam('Bk A p0'), FakeParam('Bk A p1'),
        ])
        # page 1 -> zone
        self.assertEqual(r.resolve_encoder(dev, 1).param.name, 'Amp Attack')
        self.assertEqual(r.page_label_for(dev, 1), 'Zoned')
        # standard banks start at page 2
        self.assertEqual(r._first_standard_page(dev), 2)
        r.encoder_page = 2
        self.assertEqual(r.resolve_encoder(dev, 1).param.name, 'Bk A p0')

    def test_encoder_pages_count_includes_zone_lead(self):
        banks = {'InstrumentVector': (('a', 'b'), ('c', 'd'))}
        r, _ = _zoned_resolver(device_banks=banks)
        dev = _wavetable()
        # 1 zone page + ceil(2 banks / 2 per page)=1 => 2 pages
        self.assertEqual(r.encoder_pages_count(dev), 2)

    def test_zoned_button_pages_is_one(self):
        r, _ = _zoned_resolver()
        self.assertEqual(r.button_pages_count(_wavetable()), 1)


if __name__ == '__main__':
    unittest.main()
