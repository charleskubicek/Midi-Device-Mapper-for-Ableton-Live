"""Direct unit tests for ParameterResolver (R9): the resolver is now testable
with plain data + a log sink, no surface/manager/remote fakes required."""
import unittest

from source_modules.param_resolver import ParameterResolver, _build_device_table


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

    def test_bob_encoder_resolves_by_original_name(self):
        raw = {"devices": [{"className": "Amp", "encoders": [{"name": "Bass", "display": "Bass"}], "buttons": []}]}
        r, _ = _resolver(raw)
        dev = FakeDevice("Amp", [FakeParam("On/Off"), FakeParam("Bass")])
        rp = r.resolve_encoder(dev, 1)
        self.assertIsNotNone(rp)
        self.assertEqual(rp.alias, "Bass")
        self.assertIs(rp.param, dev.parameters[1])

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


if __name__ == "__main__":
    unittest.main()
