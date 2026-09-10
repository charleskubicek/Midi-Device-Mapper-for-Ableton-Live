"""Rack macro shaping (ai-coding/plans/rack-macro-shaping-plan.md).

`macro_at` maps a baked panel-cell slot (1-based) to the 1-based Ableton macro it
should drive, given the panel width and the rack's visible_macro_count — so the
grid mirrors the rack's on-screen 2×N macro panel, left-aligned. None = a cell
outside the rack's shape (dim / dead knob).
"""
import unittest

from source_modules.param_resolver import (
    macro_at, ParameterResolver, _build_device_table,
)


class FakeParam:
    def __init__(self, name):
        self.name = name
        self.original_name = name
        self.value, self.min, self.max, self.is_quantized = 0.0, 0.0, 1.0, False


class FakeRack:
    """A rack: Device On at parameters[0], Macros 1..16 at [1..16]. `visible` is
    visible_macro_count; `mapped` is the 16-long macros_mapped list."""
    def __init__(self, visible, mapped=None, macro_names=None,
                 class_name="AudioEffectGroupDevice"):
        self.visible_macro_count = visible
        self.macros_mapped = mapped if mapped is not None else [True] * 16
        names = macro_names or [f"Macro {i}" for i in range(1, 17)]
        self.parameters = [FakeParam("Device On")] + [FakeParam(n) for n in names]
        self.class_name = class_name
        self.name = class_name


class FakeNonRack:
    """No visible_macro_count -> not a rack."""
    def __init__(self, class_name="Reverb"):
        self.parameters = [FakeParam("Device On")] + [FakeParam(f"p{i}") for i in range(1, 11)]
        self.class_name = class_name
        self.name = class_name


def _resolver(rack_shaping=True, macro_panel_cols=8):
    return ParameterResolver(
        device_table=_build_device_table(None), device_banks={}, bank_names={},
        banks_per_page=2, button_switch_count=0, button_slot_count=8,
        log=lambda m: None, rack_shaping=rack_shaping, macro_panel_cols=macro_panel_cols)


class TestResolverRackTier(unittest.TestCase):
    def test_2x4_rack_left_aligned_shape(self):
        r = _resolver()
        dev = FakeRack(visible=8, macro_names=[
            "Low Decay", "Mid Decay", "High Decay", "Reverb Width",
            "Low Dry/Wet", "Mid Dry/Wet", "High Dry/Wet", "Rack Volume"]
            + [f"Macro {i}" for i in range(9, 17)])
        # Top row: slots 1-4 -> macros 1-4 (params 1-4).
        self.assertIs(r.resolve_encoder(dev, 1).param, dev.parameters[1])
        self.assertEqual(r.resolve_encoder(dev, 1).param.name, "Low Decay")
        # slots 5-8 are right of the 4-wide rack -> dim.
        self.assertIsNone(r.resolve_encoder(dev, 5))
        self.assertIsNone(r.resolve_encoder(dev, 8))
        # Second row: slots 9-12 -> macros 5-8 (params 5-8).
        self.assertIs(r.resolve_encoder(dev, 9).param, dev.parameters[5])
        self.assertEqual(r.resolve_encoder(dev, 9).param.name, "Low Dry/Wet")
        self.assertIsNone(r.resolve_encoder(dev, 13))  # below the rack

    def test_2x8_rack_is_identity(self):
        r = _resolver()
        dev = FakeRack(visible=16)
        for slot in range(1, 17):
            self.assertIs(r.resolve_encoder(dev, slot).param, dev.parameters[slot])

    def test_visible_but_unmapped_macro_dims(self):
        r = _resolver()
        mapped = [True] * 16
        mapped[4] = False  # macro 5 visible (visible=8) but unmapped
        dev = FakeRack(visible=8, mapped=mapped)
        self.assertIsNone(r.resolve_encoder(dev, 9))   # slot 9 -> macro 5 -> dim
        self.assertIsNotNone(r.resolve_encoder(dev, 1))  # macro 1 still resolves

    def test_toggle_off_falls_through_to_fallback(self):
        # rack_shaping off: a rack resolves via the unknown-class fallback exactly
        # as before (positional over continuous params), NOT the shape.
        r = _resolver(rack_shaping=False)
        dev = FakeRack(visible=8)
        # slot 5 would be dim under shaping; under fallback it resolves to a param.
        self.assertIsNotNone(r.resolve_encoder(dev, 5))

    def test_drum_rack_is_excluded_from_shaping(self):
        # A drum rack has visible_macro_count, but this surface repurposes its
        # encoder grid for per-step velocity — shaping its macros onto the HUD
        # would mislabel the knobs. So a drum rack stays on today's behaviour
        # (falls through to fallback), NOT the shape.
        r = _resolver()
        dev = FakeRack(visible=8, class_name="DrumGroupDevice")
        self.assertIsNotNone(r.resolve_encoder(dev, 5))  # would be dim if shaped

    def test_non_rack_unaffected_by_rack_shaping(self):
        r = _resolver(rack_shaping=True)
        dev = FakeNonRack()
        # No visible_macro_count -> rack tier never fires -> fallback resolves.
        self.assertIsNotNone(r.resolve_encoder(dev, 1))


class TestMacroAt(unittest.TestCase):
    def test_2x8_is_identity(self):
        # 16 visible -> rack_cols 8 -> slot == macro across the whole 8×2 panel.
        self.assertEqual([macro_at(s, 8, 16) for s in range(1, 17)],
                         list(range(1, 17)))

    def test_2x8_slot_beyond_visible_is_none(self):
        self.assertIsNone(macro_at(17, 8, 16))

    def test_2x4_left_aligned(self):
        # 8 visible -> rack_cols 4. Top row: slots 1-4 -> macros 1-4, slots 5-8
        # blank (right of the rack). Second row: slots 9-12 -> macros 5-8.
        got = [macro_at(s, 8, 8) for s in range(1, 17)]
        self.assertEqual(got, [1, 2, 3, 4, None, None, None, None,
                               5, 6, 7, 8, None, None, None, None])

    def test_2x2_left_aligned(self):
        # 4 visible -> rack_cols 2. Macros 1-2 top-left, 3-4 directly below.
        got = [macro_at(s, 8, 4) for s in range(1, 17)]
        self.assertEqual(got, [1, 2, None, None, None, None, None, None,
                               3, 4, None, None, None, None, None, None])

    def test_odd_count_uses_ceil_and_drops_the_missing_last_cell(self):
        # 6 visible -> rack_cols 3 (2×3). Bottom row has macros 4,5,6.
        got = [macro_at(s, 8, 6) for s in range(1, 17)]
        self.assertEqual(got[:3], [1, 2, 3])
        self.assertEqual(got[8:11], [4, 5, 6])
        self.assertIsNone(got[3])   # slot 4 is right of a 3-wide rack

    def test_zero_visible_is_all_none(self):
        self.assertTrue(all(macro_at(s, 8, 0) is None for s in range(1, 17)))
