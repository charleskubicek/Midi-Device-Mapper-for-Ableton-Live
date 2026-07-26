"""`sequencer-start` (ai-coding/plans/sequencer-start-plan.md).

Two orientation decisions exist and they compose rather than duplicate:

  * the controller file's `origin:` maps hardware MIDI numbers -> grid cells.
    A measured fact about the controller.
  * this mapping file's `sequencer-start:` maps grid cells -> step numbers.
    A musical preference about which cell is beat 1.

These tests cover the second. They deliberately use a controller with NO
`origin:` anywhere, so nothing here can pass or fail because of the first.
"""
import unittest
from pathlib import Path

from ableton_control_surface_as_code.gen_error import GenError
from ableton_control_surface_as_code.model_v2 import build_validated_model

# A 4x4 button block (notes 36-51) and two 4x4 knob blocks (CC 16-31, 32-47).
# No `origin:` on any of them: hardware counts top-left, so grid cell (r, c)
# holds the value at index (r-1)*4 + (c-1).
_CONTROLLER = """
light_colors:
    off: 12

control_groups:
    -
        layout: grid
        number: 1
        type: button
        midi_channel: 1
        midi_type: note
        midi_range: C1-DS2
        rows: 4
        columns: 4
    -
        layout: grid
        number: 2
        type: knob
        midi_channel: 1
        midi_type: CC
        midi_range: 16-31
        rows: 4
        columns: 4
        right_of: 1
    -
        layout: grid
        number: 3
        type: knob
        midi_channel: 1
        midi_type: CC
        midi_range: 32-47
        rows: 4
        columns: 4
        right_of: 2
"""

_HEADER = """
controller: controller.nt
ableton_dir: /Applications/Ableton Live 12 Suite.app
remote_on: false
hud: on
show-hud-on: selection
"""

# grid-1, top-left row-major. Cell (1,1)=36 .. cell (4,4)=51.
TOP_LEFT = list(range(36, 52))
# Row-major from the bottom-left: bottom row first, left to right, then upward.
BOTTOM_LEFT = [48, 49, 50, 51, 44, 45, 46, 47, 40, 41, 42, 43, 36, 37, 38, 39]
# Row-major from the top-right: top row first, right to left, then downward.
TOP_RIGHT = [39, 38, 37, 36, 43, 42, 41, 40, 47, 46, 45, 44, 51, 50, 49, 48]
BOTTOM_RIGHT = [51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36]


def _build(mapping_text):
    return build_validated_model(
        _HEADER + mapping_text, Path('.'),
        resolve_controller=lambda root: (_CONTROLLER, 'controller.nt'),
        mapping_source='test mapping')


def _device(mapping_text):
    _root, _controller, modes = _build(mapping_text)
    devices = [m for _name, mappings in modes.mappings
               for m in mappings if hasattr(m, 'step_maps')]
    assert len(devices) == 1, f"expected one device mapping, got {len(devices)}"
    return devices[0]


def _steps(device):
    """step number -> MIDI number, in step order."""
    return [mc.midi_coords.number for mc in sorted(device.step_maps, key=lambda m: m.step)]


def _velocity_steps(device):
    return [mc.midi_coords.number for mc in sorted(device.velocity_maps, key=lambda m: m.step)]


_SEQUENCER_ONLY = """
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            sequencer:
                range: grid-1:1-16
"""


class TestSequencerStartDefault(unittest.TestCase):
    """Absent key must behave exactly as the hardcoded traversal did."""

    def test_absent_key_starts_top_left(self):
        self.assertEqual(TOP_LEFT, _steps(_device(_SEQUENCER_ONLY)))

    def test_explicit_top_left_matches_the_default(self):
        explicit = _device("sequencer-start: top-left\n" + _SEQUENCER_ONLY)
        self.assertEqual(TOP_LEFT, _steps(explicit))


class TestSequencerStartCorners(unittest.TestCase):

    def test_bottom_left_puts_beat_one_on_the_bottom_row(self):
        steps = _steps(_device("sequencer-start: bottom-left\n" + _SEQUENCER_ONLY))
        self.assertEqual(BOTTOM_LEFT, steps)
        self.assertEqual(48, steps[0])   # grid cell (4,1)
        self.assertEqual(51, steps[3])   # (4,4) — the bottom row runs left to right
        self.assertEqual(36, steps[12])  # (1,1) — last four steps are the top row

    def test_top_right(self):
        self.assertEqual(TOP_RIGHT, _steps(_device("sequencer-start: top-right\n" + _SEQUENCER_ONLY)))

    def test_bottom_right(self):
        self.assertEqual(BOTTOM_RIGHT, _steps(_device("sequencer-start: bottom-right\n" + _SEQUENCER_ONLY)))


class TestSequencerStartGovernsVelocitiesToo(unittest.TestCase):
    """The reported bug: the sequencer and the velocity row disagreed about
    which cell was beat 1. One key drives both, so they cannot drift apart."""

    _BOTH = """
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            sequencer:
                range: grid-1:1-16
            velocities:
                range: grid-2:1-16
"""

    def test_default_agrees_across_blocks(self):
        device = _device(self._BOTH)
        self.assertEqual(TOP_LEFT, _steps(device))
        self.assertEqual(list(range(16, 32)), _velocity_steps(device))

    def test_bottom_left_moves_both_the_same_way(self):
        device = _device("sequencer-start: bottom-left\n" + self._BOTH)
        self.assertEqual(BOTTOM_LEFT, _steps(device))
        # Same permutation over grid-2's CC 16-31.
        self.assertEqual([28, 29, 30, 31, 24, 25, 26, 27, 20, 21, 22, 23, 16, 17, 18, 19],
                         _velocity_steps(device))

    def test_step_n_is_the_same_grid_cell_in_both_roles(self):
        device = _device("sequencer-start: bottom-left\n" + self._BOTH)
        steps, velocities = _steps(device), _velocity_steps(device)
        # grid-1 cell index of each step == grid-2 cell index of each step.
        self.assertEqual([n - 36 for n in steps], [n - 16 for n in velocities])


class TestSequencerStartDoesNotTouchPads(unittest.TestCase):
    """A pad index selects which drum, not which step — that ordering is Live's
    drum rack layout, not ours."""

    _PADS = """
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            pads:
                range: grid-1:1-16
"""

    def test_pads_ignore_the_key(self):
        device = _device("sequencer-start: bottom-left\n" + self._PADS)
        pads = [m.midi_coords.number for m in sorted(device.pad_maps, key=lambda m: m.index)]
        self.assertEqual(TOP_LEFT, pads)


class TestSequencerStartNeedsAGridShape(unittest.TestCase):
    """A non-default corner is only meaningful over a range with an unambiguous
    2D shape. Guessing one would silently scramble the steps."""

    _HALF_BLOCK = """
sequencer-start: bottom-left
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            sequencer:
                range: grid-1:1-8
"""

    _TWO_BLOCKS = """
sequencer-start: bottom-left
mappings:
    -
        type: device
        track: selected
        device: selected
        mappings:
            velocities:
                range: grid-2:1-8,grid-3:1-8
"""

    def test_partial_block_is_an_error_naming_the_key(self):
        with self.assertRaises(GenError) as ctx:
            _device(self._HALF_BLOCK)
        self.assertIn('sequencer-start', str(ctx.exception))

    def test_range_spanning_two_blocks_is_an_error(self):
        with self.assertRaises(GenError) as ctx:
            _device(self._TWO_BLOCKS)
        self.assertIn('sequencer-start', str(ctx.exception))

    def test_top_left_stays_legal_on_those_ranges(self):
        # The identity permutation needs no shape, so the default must not start
        # rejecting configs that work today.
        device = _device(self._HALF_BLOCK.replace('sequencer-start: bottom-left\n', ''))
        self.assertEqual(list(range(36, 44)), _steps(device))


if __name__ == '__main__':
    unittest.main()
