"""Validation tests for the shipped smart-zoning tables + a ground-truth check
that every zoned parameter name is byte-exact against data/devices_12.json.

The ground-truth check is deliberately NOT "slot N == the name I typed in the
test" (circular — a typo would propagate to both). It asserts membership in the
device's real parameter set, so a byte-drift in the shipped JSON fails here.
See grid-po16-synth-surface-plan §10."""
import copy
import json
import unittest
from pathlib import Path

from ableton_control_surface_as_code.model_synth_zones import (
    SynthZoneTables, validate_synth_zone_tables,
)

ZONE_FILE = Path('data/synth_zone_tables.json')
DEVICES_FILE = Path('data/devices_12.json')


def _load():
    return json.loads(ZONE_FILE.read_text())


def _minimal():
    """A tiny-but-valid table (full 32/16 slot cover, one synth) to mutate in
    negative tests without carrying the whole shipped file around."""
    enc = [{'slot': i, 'role': f'e{i}', 'zone': 'osc', 'display': f'E{i}'}
           for i in range(1, 33)]
    btn = [{'slot': i, 'role': f'b{i}', 'zone': 'osc', 'display': f'B{i}'}
           for i in range(1, 17)]
    return {
        'template': {'encoders': enc, 'buttons': btn},
        'synths': {
            'Drift': {'display': 'Drift',
                      'encoders': {'e1': {'name': 'LP Freq'}},
                      'buttons': {'b1': {'name': 'Osc 1 On'}}},
        },
    }


class TestShippedFileValidates(unittest.TestCase):
    def test_shipped_file_validates(self):
        validate_synth_zone_tables(_load())

    def test_shipped_has_four_synths(self):
        raw = _load()
        self.assertEqual(
            set(raw['synths']),
            {'InstrumentVector', 'Drift', 'Operator', 'UltraAnalog'})

    def test_module_orientation(self):
        # ck_grid.nt binds grid-2 (LEFT PO16) -> slots 1-16, grid-3 (RIGHT) ->
        # 17-32. ck wants osc/filter/LFO under the left hand, envelopes/global
        # under the right. Pin that so re-swapping either the .nt or the template
        # in isolation (which would invert the rig) fails loudly.
        raw = _load()
        zone = {e['slot']: e['zone'] for e in raw['template']['encoders']}
        left = {zone[s] for s in range(1, 17)}
        right = {zone[s] for s in range(17, 33)}
        self.assertEqual(left, {'osc', 'filter', 'lfo'})
        self.assertEqual(right, {'env', 'global', 'signature'})

    def test_template_covers_all_slots(self):
        raw = _load()
        self.assertEqual(sorted(e['slot'] for e in raw['template']['encoders']),
                         list(range(1, 33)))
        self.assertEqual(sorted(e['slot'] for e in raw['template']['buttons']),
                         list(range(1, 17)))


class TestZoneColors(unittest.TestCase):
    def test_shipped_colors_cover_every_template_zone(self):
        raw = _load()
        self.assertIn('zone_colors', raw)
        zones = ({e['zone'] for e in raw['template']['encoders']} |
                 {e['zone'] for e in raw['template']['buttons']})
        self.assertEqual(set(raw['zone_colors']), zones)

    def test_shipped_colors_are_6_hex(self):
        import re
        for zone, hexv in _load()['zone_colors'].items():
            self.assertRegex(hexv, r'^[0-9A-Fa-f]{6}$', f"{zone}={hexv!r}")

    def test_missing_zone_color_rejected(self):
        raw = _minimal()  # template uses only 'osc'
        raw['zone_colors'] = {}  # present but missing 'osc'
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_orphan_zone_color_rejected(self):
        raw = _minimal()
        raw['zone_colors'] = {'osc': '112233', 'nosuchzone': '445566'}
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_bad_hex_rejected(self):
        raw = _minimal()
        raw['zone_colors'] = {'osc': 'ZZZ'}
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_zone_colors_optional_when_absent(self):
        # A table with no zone_colors still validates (colours are opt-in).
        SynthZoneTables.model_validate(_minimal())


class TestGroundTruthNames(unittest.TestCase):
    def test_every_zoned_name_exists_in_device(self):
        raw = _load()
        devices = json.loads(DEVICES_FILE.read_text())
        # className -> set of real original param names
        by_class = {}
        for entry in devices.values():
            cn = entry.get('class_name')
            if cn:
                by_class[cn] = {p['name'] for p in entry['parameters']}

        missing = []
        for cn, synth in raw['synths'].items():
            real = by_class.get(cn)
            self.assertIsNotNone(real, f"{cn} not present in devices_12.json")
            for kind in ('encoders', 'buttons'):
                for role, spec in synth[kind].items():
                    if spec['name'] not in real:
                        missing.append((cn, kind, role, spec['name']))
        self.assertEqual(missing, [], f"names not found in devices_12.json: {missing}")


class TestValidatorRejects(unittest.TestCase):
    def test_missing_slot_rejected(self):
        raw = _minimal()
        raw['template']['encoders'].pop()  # drop slot 32
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_duplicate_slot_rejected(self):
        raw = _minimal()
        raw['template']['encoders'][0]['slot'] = 2  # slot 2 twice, 1 missing
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_unknown_role_rejected(self):
        raw = _minimal()
        raw['synths']['Drift']['encoders']['not_a_role'] = {'name': 'LP Reso'}
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_duplicate_param_within_synth_rejected(self):
        raw = _minimal()
        raw['synths']['Drift']['encoders']['e2'] = {'name': 'LP Freq'}  # same as e1
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)

    def test_duplicate_template_role_rejected(self):
        raw = _minimal()
        raw['template']['encoders'][1]['role'] = 'e1'  # e1 twice
        with self.assertRaises(Exception):
            SynthZoneTables.model_validate(raw)


if __name__ == '__main__':
    unittest.main()
