"""Tests for the UI sidecar API (ableton_control_surface_as_code.ui_api).

The Electron mapping editor spawns `python -m ableton_control_surface_as_code.ui_api`
and speaks JSON-lines over stdio. These tests drive both the request handler
directly and the stdio loop with in-memory streams. The hard requirement
throughout: no input — malformed JSON, NestedText syntax errors, missing files —
may ever kill the process (NestedTextError.terminate() raises SystemExit).
"""
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ableton_control_surface_as_code.ui_api import handle_request, run


CONTROLLER = """\
light_colors:
    off: 12
    red_low: 13
control_groups:
  -
    layout: grid
    number: 1
    type: knob
    midi_channel: 1
    midi_type: CC
    midi_range: 32-47
    rows: 4
    columns: 4
  -
    layout: grid
    number: 2
    type: button
    midi_channel: 1
    midi_type: note
    midi_range: C2-DS3
    rows: 4
    columns: 4
    right_of: 1
"""

MAPPING_OK = """\
controller: controller.nt
ableton_dir: /tmp
hud: off
show-hud-on: selection
mappings:
    -
        type: mixer
        track: selected
        mappings:
            volume: grid-1:1
"""


def req(method, _id=1, **params):
    return {"id": _id, "method": method, "params": params}


class UiApiDirBase(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "controller.nt").write_text(CONTROLLER)

    def tearDown(self):
        self._tmp.cleanup()


class TestPing(unittest.TestCase):
    def test_ping(self):
        resp = handle_request(req("ping"))
        self.assertEqual(resp["id"], 1)
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["result"], "pong")

    def test_unknown_method(self):
        resp = handle_request(req("frobnicate"))
        self.assertFalse(resp["ok"])
        self.assertIn("frobnicate", resp["error"]["message"])

    def test_missing_method(self):
        resp = handle_request({"id": 7})
        self.assertEqual(resp["id"], 7)
        self.assertFalse(resp["ok"])


class TestLoadController(UiApiDirBase):
    def test_loads_groups_with_positions(self):
        resp = handle_request(req("load_controller", path=str(self.dir / "controller.nt")))
        self.assertTrue(resp["ok"], resp)
        r = resp["result"]
        self.assertEqual(r["light_colors"], {"off": 12, "red_low": 13})
        self.assertEqual(r["button_behaviour"], "momentary")
        self.assertEqual(r["problems"], [])
        groups = {g["number"]: g for g in r["groups"]}
        self.assertEqual(set(groups), {1, 2})
        knobs = groups[1]
        self.assertEqual(knobs["type"], "knob")
        self.assertEqual((knobs["grid_row"], knobs["grid_col"]), (0, 0))
        self.assertEqual((knobs["rows"], knobs["columns"]), (4, 4))
        self.assertEqual(knobs["control_count"], 16)
        self.assertEqual(knobs["midi_channel"], 1)
        self.assertEqual(knobs["midi_type"], "CC")
        self.assertEqual(knobs["midi_numbers"][:3], [32, 33, 34])
        buttons = groups[2]
        self.assertEqual(buttons["type"], "button")
        self.assertEqual((buttons["grid_row"], buttons["grid_col"]), (0, 1))
        self.assertEqual(buttons["midi_type"], "note")

    def test_missing_file_is_error_not_crash(self):
        resp = handle_request(req("load_controller", path=str(self.dir / "nope.nt")))
        self.assertFalse(resp["ok"])
        self.assertIn("nope.nt", resp["error"]["message"])

    def test_nt_syntax_error_does_not_exit(self):
        (self.dir / "bad.nt").write_text("light_colors:\n  broken\n    indent: x\n")
        resp = handle_request(req("load_controller", path=str(self.dir / "bad.nt")))
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["kind"], "parse")


class TestValidate(UiApiDirBase):
    def _validate(self, mapping_text):
        resp = handle_request(req("validate", mapping_text=mapping_text,
                                  mapping_dir=str(self.dir)))
        self.assertTrue(resp["ok"], resp)
        return resp["result"]

    def test_valid_mapping(self):
        r = self._validate(MAPPING_OK)
        self.assertTrue(r["valid"])
        self.assertEqual(r["problems"], [])

    def test_coord_out_of_range(self):
        r = self._validate(MAPPING_OK.replace("grid-1:1", "grid-1:99"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("99" in p["message"] for p in r["problems"]))

    def test_multiple_problems_reported_individually(self):
        # Problems in two separate mapping blocks must come back as two
        # entries, not one collapsed "Found 2 config problem(s)" message.
        bad = MAPPING_OK + (
            "    -\n"
            "        type: mixer\n"
            "        track: selected\n"
            "        mappings:\n"
            "            pan: grid-1:98\n"
        )
        bad = bad.replace("volume: grid-1:1", "volume: grid-1:99")
        r = self._validate(bad)
        self.assertFalse(r["valid"])
        self.assertGreaterEqual(len(r["problems"]), 2)
        self.assertFalse(any("config problem(s)" in p["message"] for p in r["problems"]))

    def test_clash_detected(self):
        bad = MAPPING_OK.replace(
            "            volume: grid-1:1",
            "            volume: grid-1:1\n            pan: grid-1:1")
        r = self._validate(bad)
        self.assertFalse(r["valid"])
        self.assertTrue(any("clash" in p["message"].lower() for p in r["problems"]))

    def test_missing_hud_keys(self):
        r = self._validate(MAPPING_OK.replace("hud: off\n", "").replace("show-hud-on: selection\n", ""))
        self.assertFalse(r["valid"])
        self.assertTrue(any("hud" in p["message"] for p in r["problems"]))

    def test_nt_syntax_error_in_mapping_survives(self):
        r = self._validate("controller controller.nt\n:::\n")
        self.assertFalse(r["valid"])
        self.assertEqual(r["problems"][0]["kind"], "parse")

    def test_missing_controller_file(self):
        r = self._validate(MAPPING_OK.replace("controller.nt", "ghost.nt"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("ghost.nt" in p["message"] for p in r["problems"]))

    def test_controller_nt_syntax_error_survives(self):
        (self.dir / "controller.nt").write_text("control_groups:\n  broken\n    x: y\n")
        r = self._validate(MAPPING_OK)
        self.assertFalse(r["valid"])
        self.assertEqual(r["problems"][0]["kind"], "parse")

    def test_unknown_mapping_type(self):
        r = self._validate(MAPPING_OK.replace("type: mixer", "type: mixxer"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("mixxer" in p["message"] for p in r["problems"]))


class TestSchemaInfo(unittest.TestCase):
    def test_exports_clip_actions_and_action_lists(self):
        resp = handle_request(req("schema_info"))
        self.assertTrue(resp["ok"])
        r = resp["result"]
        clip = {a["key"]: a for a in r["clip_actions"]}
        self.assertEqual(len(clip), 22)
        self.assertEqual(clip["gain"]["kind"], "encoder")
        self.assertEqual(clip["loop-start"]["kind"], "nudge")
        self.assertEqual(clip["looping"]["kind"], "button")
        self.assertTrue(all(a["label"] for a in r["clip_actions"]))
        self.assertIn("play-stop", r["transport_actions"])
        self.assertEqual(r["track_nav_actions"], ["left", "right"])
        self.assertIn("first-last", r["device_nav_actions"])
        self.assertEqual(r["builtin_functions"], ["hud_toggle"])


class TestParseNt(unittest.TestCase):
    def test_parses_to_json(self):
        resp = handle_request(req("parse_nt", text="a: 1\nb:\n    c: x\n"))
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["result"], {"a": "1", "b": {"c": "x"}})

    def test_parse_error_survives(self):
        resp = handle_request(req("parse_nt", text=": :\n  ::bad"))
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["kind"], "parse")


class TestListFunctions(UiApiDirBase):
    def test_lists_functions_class_methods(self):
        (self.dir / "functions.py").write_text(
            "class Functions:\n"
            "    def __init__(self):\n"
            "        pass\n"
            "    def toggle_thing(self):\n"
            "        pass\n"
            "    def with_value(self, value):\n"
            "        pass\n")
        resp = handle_request(req("list_functions", dir=str(self.dir)))
        self.assertTrue(resp["ok"], resp)
        fns = {f["name"]: f["params"] for f in resp["result"]["functions"]}
        self.assertEqual(fns, {"toggle_thing": 0, "with_value": 1})

    def test_no_functions_py(self):
        resp = handle_request(req("list_functions", dir=str(self.dir)))
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["result"], {"functions": None})


class TestGenerate(UiApiDirBase):
    def test_generates_a_surface_directory(self):
        (self.dir / "my_surface.nt").write_text(
            MAPPING_OK.replace("ableton_dir: /tmp", f"ableton_dir: {self.dir}"))
        resp = handle_request(req("generate", mapping_path=str(self.dir / "my_surface.nt")))
        self.assertTrue(resp["ok"], resp)
        self.assertIn("Finished generating", resp["result"]["output"])
        self.assertTrue((self.dir / "my_surface" / "my_surface.py").exists())
        self.assertTrue((self.dir / "my_surface" / "deploy.sh").exists())

    def test_generate_error_is_structured(self):
        (self.dir / "bad.nt").write_text(
            MAPPING_OK.replace("grid-1:1", "grid-1:99").replace(
                "ableton_dir: /tmp", f"ableton_dir: {self.dir}"))
        resp = handle_request(req("generate", mapping_path=str(self.dir / "bad.nt")))
        self.assertFalse(resp["ok"])
        self.assertIn("99", resp["error"]["message"])


class TestStdioLoop(unittest.TestCase):
    def _run(self, lines):
        out = io.StringIO()
        run(io.StringIO(lines), out)
        return [json.loads(l) for l in out.getvalue().splitlines() if l.strip()]

    def test_request_response(self):
        responses = self._run(json.dumps(req("ping", _id=42)) + "\n")
        self.assertEqual(responses, [{"id": 42, "ok": True, "result": "pong"}])

    def test_malformed_json_does_not_kill_loop(self):
        lines = "this is not json\n" + json.dumps(req("ping", _id=2)) + "\n"
        responses = self._run(lines)
        self.assertEqual(len(responses), 2)
        self.assertFalse(responses[0]["ok"])
        self.assertTrue(responses[1]["ok"])

    def test_handler_prints_never_pollute_the_json_stream(self):
        # Device mappings make the generator print info tables to stdout; every
        # line the loop emits must still be valid JSON.
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "controller.nt").write_text(CONTROLLER)
            device_mapping = MAPPING_OK.replace(
                "        type: mixer\n"
                "        track: selected\n"
                "        mappings:\n"
                "            volume: grid-1:1\n",
                "        type: device\n"
                "        track: selected\n"
                "        device: selected\n"
                "        mappings:\n"
                "            encoders:\n"
                "                range: grid-1:1-8\n"
                "                slots: 1-8\n")
            out = io.StringIO()
            run(io.StringIO(json.dumps(req("validate", mapping_text=device_mapping,
                                           mapping_dir=tmp)) + "\n"), out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        parsed = json.loads(lines[0])  # raises if a table line leaked
        self.assertTrue(parsed["ok"])

    def test_handler_crash_does_not_kill_loop(self):
        lines = (json.dumps(req("load_controller", _id=1, path=123))  # wrong type
                 + "\n" + json.dumps(req("ping", _id=2)) + "\n")
        responses = self._run(lines)
        self.assertEqual(len(responses), 2)
        self.assertFalse(responses[0]["ok"])
        self.assertTrue(responses[1]["ok"])


if __name__ == "__main__":
    unittest.main()
