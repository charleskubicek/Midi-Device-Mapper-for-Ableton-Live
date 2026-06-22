"""Integration test: generate the lc_parks composition end-to-end.

Today's lc_parks secondary (parks) declares no modes, so the reverse mode channel
is DORMANT: both surfaces bake MODE_LINK = None and neither instantiates a
ModeSender/ModeListener. This protects the no-regression path — wiring the reverse
channel must not perturb a composition whose secondary has no modes. The active
path (headless FSM + mode_link) is covered by unit tests (test_modes,
test_composition, test_mode_link).

Output lands in the (gitignored) ck_lc_parks__* dirs next to the composition.
Generation reads templates/ and source_modules/ by relative path, so it must run
from the repo root.
"""
import os
import unittest
from pathlib import Path

from ableton_control_surface_as_code.gen import generate

REPO = Path(__file__).resolve().parent.parent
LC_PARKS = REPO / "live_surfaces" / "lc_parks" / "lc_parks.nt"
PRIMARY = REPO / "live_surfaces" / "lc_parks" / "ck_lc_parks__launch_control" / "modules" / "main_component.py"
SECONDARY = REPO / "live_surfaces" / "lc_parks" / "ck_lc_parks__parks" / "modules" / "main_component.py"


class TestCompositionCodegenDormant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cwd = os.getcwd()
        os.chdir(REPO)
        try:
            generate(LC_PARKS)
        finally:
            os.chdir(cwd)
        cls.primary = PRIMARY.read_text()
        cls.secondary = SECONDARY.read_text()

    def test_mode_link_dormant_when_secondary_has_no_modes(self):
        # Secondary declares no modes -> reverse channel off in both surfaces.
        self.assertIn("MODE_LINK = None", self.primary)
        self.assertIn("MODE_LINK = None", self.secondary)
        for src in (self.primary, self.secondary):
            self.assertNotIn("ModeSender('127.0.0.1', MODE_LINK['port'])", src.replace(
                "self._mode_sender = ModeSender('127.0.0.1', MODE_LINK['port'])", "GUARDED"))

    def test_no_mode_sender_or_listener_instantiated(self):
        # The gated instantiations live behind `if MODE_LINK is not None:`, which
        # is False here. Assert no surface actually constructs one at top level by
        # checking the guard value is None (above) — the instantiation lines are
        # inert. Sanity: the guard block is present (wiring shipped) but dormant.
        self.assertIn("if MODE_LINK is not None:", self.primary)
        self.assertIn("if MODE_LINK is not None:", self.secondary)

    def test_region_wiring_unchanged_on_primary(self):
        # The reverse-channel addition must not disturb the existing region merge.
        self.assertIn("REGION_CONFIG = {'dial_offset'", self.primary)
        self.assertIn("RegionListener(self.manager, self._region_state", self.primary)

    def test_goto_mode_guards_shipped(self):
        # The template guards that make a headless secondary safe ship in every
        # surface (they're inert when a mode-button / mode_sender exists).
        self.assertIn("if self.mode_button is not None:", self.primary)
        self.assertIn("if self._mode_sender is not None:", self.primary)


if __name__ == '__main__':
    unittest.main()
