import unittest
from pathlib import Path

from ableton_control_surface_as_code.model_composition import (
    read_composition, is_composition_file, CompositionRoot,
)

REPO = Path(__file__).resolve().parent.parent
LC_PARKS = REPO / "live_surfaces" / "lc_parks" / "lc_parks.nt"


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
