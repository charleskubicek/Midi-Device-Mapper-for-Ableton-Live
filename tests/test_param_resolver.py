"""Direct unit tests for ParameterResolver (R9): the resolver is now testable
with plain data + a log sink, no surface/manager/remote fakes required."""
import unittest

from source_modules.param_resolver import (
    ParameterResolver, _build_device_table,
    _device_alive, _same_device, _safe_device_attr,
)


class FakeParam:
    def __init__(self, name, value=0.0, mn=0.0, mx=1.0, original_name=None, is_quantized=False):
        self.name = name
        self.original_name = original_name or name
        self.value = value
        self.min = mn
        self.max = mx
        self.is_quantized = is_quantized


class FakeDevice:
    def __init__(self, class_name, parameters, name=None):
        self.class_name = class_name
        self.name = name or class_name
        self.parameters = parameters


class _DeadDevice:
    """A Live device whose C++ handle was freed (replaced/deleted, e.g.
    Wavetable → Drift). Every attribute access raises — modeling
    Boost.Python.ArgumentError, which is a TypeError subclass, NOT
    AttributeError, so `getattr(dev, 'name', None)` does NOT swallow it.
    __eq__ falls back to object identity (models 'Boost == answers False on a
    dead handle')."""
    def __getattr__(self, name):
        raise TypeError("Boost.Python.ArgumentError: dead device handle")


class _DeadDeviceRaisingEq(_DeadDevice):
    """Variant whose __eq__ itself raises (models 'Boost == throws on a dead
    handle'). The fail-open guards must handle both variants identically."""
    __hash__ = object.__hash__

    def __eq__(self, other):
        raise TypeError("Boost.Python.ArgumentError: dead device handle")


def _resolver(parameter_mappings_raw=None, device_banks=None, bank_names=None,
              banks_per_page=1, button_switch_count=0, button_slot_count=8):
    logs = []
    r = ParameterResolver(
        device_table=_build_device_table(parameter_mappings_raw),
        device_banks=device_banks or {}, bank_names=bank_names or {},
        banks_per_page=banks_per_page, button_switch_count=button_switch_count,
        button_slot_count=button_slot_count, log=logs.append)
    return r, logs


class TestResolverDirect(unittest.TestCase):
    def test_focus_resets_pages_and_indices(self):
        r, _ = _resolver()
        r.encoder_page = 3
        r.button_page = 2
        r._name_index = {'x': (0, None)}
        r.focus()
        self.assertEqual((r.encoder_page, r.button_page), (1, 1))
        self.assertIsNone(r._name_index)

    def test_ensure_focused_resets_on_device_change(self):
        # A burst for a device the funnel never reset must drop stale paging +
        # index rather than inherit the previous device's page (stale-index bug).
        r, _ = _resolver()
        dev_a, dev_b = FakeDevice("A", []), FakeDevice("B", [])
        r.ensure_focused(dev_a)
        r.encoder_page = 4
        r.button_page = 3
        r._name_index = {'stale': 0}
        r.ensure_focused(dev_b)  # different device
        self.assertEqual((r.encoder_page, r.button_page), (1, 1))
        self.assertIsNone(r._name_index)

    def test_ensure_focused_is_noop_on_same_device(self):
        # Idempotent on the same device so live paging (pager, group-selector
        # refresh) survives repeated bursts.
        r, _ = _resolver()
        dev = FakeDevice("A", [])
        r.ensure_focused(dev)
        r.encoder_page = 4
        r.ensure_focused(dev)  # same device
        self.assertEqual(r.encoder_page, 4)

    def test_ensure_focused_resets_when_previous_device_is_dead(self):
        # Fail-open: if the previously-focused device was replaced (dead Boost
        # handle), the identity compare must treat the new device as changed and
        # reset — never inherit the dead device's paging. Without fail-open the
        # compare would raise (or wrongly compare), leaving stale state.
        r, _ = _resolver()
        r._focused_device = _DeadDevice()
        r.encoder_page = 4
        r.button_page = 3
        r._name_index = {'stale': 0}
        r.ensure_focused(FakeDevice("Drift", []))  # live replacement
        self.assertEqual((r.encoder_page, r.button_page), (1, 1))
        self.assertIsNone(r._name_index)

    def test_ensure_focused_resets_when_previous_device_raises_on_eq(self):
        # Same as above but the dead handle raises on __eq__ (the other plausible
        # Boost behavior). The fail-open guard must handle both identically.
        r, _ = _resolver()
        r._focused_device = _DeadDeviceRaisingEq()
        r.encoder_page = 4
        new = FakeDevice("Drift", [])
        r.ensure_focused(new)
        self.assertEqual(r.encoder_page, 1)
        self.assertIs(r._focused_device, new)

    def test_bob_encoder_resolves_by_original_name(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Bass", "display": "Bass"}], "buttons": []}]}
        r, _ = _resolver(raw)
        dev = FakeDevice("Amp", [FakeParam("On/Off"), FakeParam("Bass")])
        rp = r.resolve_encoder(dev, 1)
        self.assertIsNotNone(rp)
        self.assertEqual(rp.alias, "Bass")
        self.assertIs(rp.param, dev.parameters[1])

    def test_resolve_refetches_live_param_after_handle_swap(self):
        """The new Operator rebuilds its parameter objects in place; the cache
        must hand back the *live* handle, not the stale one captured at index
        build time (a stale handle raises Boost.Python.ArgumentError on access)."""
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Bass", "display": "Bass"}], "buttons": []}]}
        r, _ = _resolver(raw)
        p0, p1 = FakeParam("On/Off"), FakeParam("Bass", value=0.1)
        dev = FakeDevice("Amp", [p0, p1])
        self.assertIs(r.resolve_encoder(dev, 1).param, p1)  # builds the index
        p1_live = FakeParam("Bass", value=0.9)
        dev.parameters = [p0, p1_live]  # Live swapped the handle in place
        self.assertIs(r.resolve_encoder(dev, 1).param, p1_live)

    def test_resolve_rebuilds_index_when_list_reordered(self):
        """If the live list reordered/resized so the cached index no longer
        points at the named param, the resolver rebuilds the index and finds it
        at its new position rather than returning the wrong (or dead) param."""
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Bass", "display": "Bass"}], "buttons": []}]}
        r, _ = _resolver(raw)
        p0, p1 = FakeParam("On/Off"), FakeParam("Bass", value=0.3)
        dev = FakeDevice("Amp", [p0, p1])
        self.assertIs(r.resolve_encoder(dev, 1).param, p1)  # index: Bass -> 1
        bass_moved = FakeParam("Bass", value=0.7)
        dev.parameters = [p0, FakeParam("Inserted"), bass_moved]  # Bass now at 2
        self.assertIs(r.resolve_encoder(dev, 1).param, bass_moved)

    def test_unknown_class_fallback_skips_onoff_and_quantized(self):
        r, _ = _resolver()
        dev = FakeDevice("Mystery", [
            FakeParam("On/Off"), FakeParam("q", is_quantized=True),
            FakeParam("cont1"), FakeParam("cont2"),
        ])
        # encoder 1 -> first continuous (skipping on/off + quantized)
        self.assertIs(r.resolve_encoder(dev, 1).param, dev.parameters[2])
        self.assertIs(r.resolve_encoder(dev, 2).param, dev.parameters[3])

    def test_page_label_best_of_for_bob_encoders(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Bass"}], "buttons": []}]}
        r, _ = _resolver(raw)
        dev = FakeDevice("Amp", [FakeParam("On/Off"), FakeParam("Bass")])
        self.assertEqual(r.page_label_for(dev, 1), "Best of")

    def test_unresolved_bob_name_logs_available(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Missing"}], "buttons": []}]}
        r, logs = _resolver(raw)
        dev = FakeDevice("Amp", [FakeParam("On/Off"), FakeParam("Bass")])
        self.assertIsNone(r.resolve_encoder(dev, 1))
        self.assertTrue(any("[bob]" in m and "Missing" in m for m in logs))


class TestDeviceLivenessPrimitives(unittest.TestCase):
    """The shared dead-handle guards used by the burst path and the
    focus/selection guards. Boost.Python.ArgumentError is a TypeError subclass,
    so the whole point is that a plain getattr-default does NOT shield callers —
    these primitives do."""

    def test_getattr_default_does_not_swallow_dead_handle(self):
        # Anti-vacuous guard: if this ever stops raising, the _DeadDevice double
        # is wrong and every dead-handle test below is meaningless.
        with self.assertRaises(TypeError):
            getattr(_DeadDevice(), 'name', None)

    def test_device_alive_true_for_live_false_for_dead_and_none(self):
        self.assertTrue(_device_alive(FakeDevice("Live", [])))
        self.assertFalse(_device_alive(_DeadDevice()))
        self.assertFalse(_device_alive(_DeadDeviceRaisingEq()))
        self.assertFalse(_device_alive(None))

    def test_safe_device_attr_returns_default_on_dead_handle(self):
        self.assertEqual(_safe_device_attr(_DeadDevice(), 'name', '?'), '?')
        self.assertEqual(_safe_device_attr(FakeDevice("X", []), 'name'), "X")

    def test_same_device_fail_open_when_prev_dead(self):
        new = FakeDevice("Drift", [])
        # Dead / raising-eq / None prev must never count as "same" — proceed.
        self.assertFalse(_same_device(new, _DeadDevice()))
        self.assertFalse(_same_device(new, _DeadDeviceRaisingEq()))
        self.assertFalse(_same_device(new, None))

    def test_same_device_true_only_for_live_equal(self):
        dev = FakeDevice("X", [])
        self.assertTrue(_same_device(dev, dev))
        self.assertFalse(_same_device(dev, FakeDevice("Y", [])))
        self.assertFalse(_same_device(None, dev))


if __name__ == "__main__":
    unittest.main()
