import unittest
from pathlib import Path

from ableton_control_surface_as_code.model_composition import (
    read_composition, is_composition_file, CompositionRoot,
)
from ableton_control_surface_as_code.gen import validate_composition_modes
from ableton_control_surface_as_code.model_v2 import RootV2, ModeDef, ModeButton, ModeType
from ableton_control_surface_as_code.gen_error import GenError

REPO = Path(__file__).resolve().parent.parent
LC_PARKS = REPO / "live_surfaces" / "lc_parks" / "lc_parks.nt"


def _root(mode_names, mode_button=None):
    """Build a minimal RootV2 with the given declared mode names (empty list =
    a modeless mapping, i.e. the synthesized single fake-wrapper mode)."""
    if mode_names:
        modes = [ModeDef(name=n, mappings=[]) for n in mode_names]
    else:
        modes = [ModeDef.empty_with_one_mode([])]
    return RootV2(controller='c.nt', mode_button=mode_button, modes=modes, ableton_dir='/x')


_SHIFT_BTN = ModeButton(button='row-3:1', type=ModeType.Shift)


class TestValidateCompositionModes(unittest.TestCase):
    def test_matching_shift_modes_ok(self):
        primary = _root(['main_mode', 'shift_mode'], mode_button=_SHIFT_BTN)
        secondary = _root(['main_mode', 'shift_mode'])
        validate_composition_modes(primary, secondary)  # no raise

    def test_secondary_modeless_is_ok(self):
        primary = _root(['main_mode', 'shift_mode'], mode_button=_SHIFT_BTN)
        validate_composition_modes(primary, _root([]))  # no raise

    def test_primary_without_shift_rejected(self):
        primary = _root(['main_mode', 'shift_mode'])  # no mode-button
        secondary = _root(['main_mode', 'shift_mode'])
        with self.assertRaises(GenError) as ctx:
            validate_composition_modes(primary, secondary)
        self.assertIn('type: shift', str(ctx.exception))

    def test_secondary_with_own_mode_button_rejected(self):
        primary = _root(['main_mode', 'shift_mode'], mode_button=_SHIFT_BTN)
        secondary = _root(['main_mode', 'shift_mode'], mode_button=_SHIFT_BTN)
        with self.assertRaises(GenError) as ctx:
            validate_composition_modes(primary, secondary)
        self.assertIn('must not declare its own', str(ctx.exception))

    def test_mismatched_mode_names_rejected(self):
        primary = _root(['main_mode', 'shift_mode'], mode_button=_SHIFT_BTN)
        secondary = _root(['main_mode', 'other_mode'])
        with self.assertRaises(GenError) as ctx:
            validate_composition_modes(primary, secondary)
        self.assertIn('match the primary modes', str(ctx.exception))


class TestReadComposition(unittest.TestCase):
    def test_parses_primary_and_secondary(self):
        comp = read_composition(LC_PARKS.read_text())
        self.assertIsInstance(comp, CompositionRoot)
        self.assertEqual(comp.primary, "../launch_control/ck_launch_control_16.nt")
        self.assertEqual(comp.secondary.mapping, "../parks/ck_parkstool_buttons.nt")
        self.assertEqual(comp.secondary.placement, "right")
        self.assertIsNone(comp.region_port)

    def test_region_port_optional_override(self):
        comp = read_composition(
            "ableton-dir: /x\nprimary: a.nt\nsecondary:\n    mapping: b.nt\nregion-port: 5123\n"
        )
        self.assertEqual(comp.region_port, 5123)

    def test_rejects_unknown_key(self):
        with self.assertRaises(Exception):
            read_composition("ableton-dir: /x\nprimary: a.nt\nsecondary:\n    mapping: b.nt\nbogus: 1\n")


class TestIsCompositionFile(unittest.TestCase):
    def test_detects_composition(self):
        self.assertTrue(is_composition_file(LC_PARKS))

    def test_normal_mapping_is_not_composition(self):
        normal = REPO / "live_surfaces" / "parks" / "ck_parkstool_buttons.nt"
        self.assertFalse(is_composition_file(normal))


if __name__ == '__main__':
    unittest.main()
