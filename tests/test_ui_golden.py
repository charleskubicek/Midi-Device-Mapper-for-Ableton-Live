"""Golden contract for the Electron editor's TypeScript NestedText serializer.

ui/test/golden/*.nt are byte-exact outputs of serializer.ts (kept current by
`cd ui && npx vitest run`, regenerated with UPDATE_GOLDEN=1). This side asserts
the generator actually accepts them — parse, semantic validation, clash
detection — against the controller.nt + functions.py snapshots in the same
directory. If the serializer ever emits NT the generator rejects, this fails.
"""
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ableton_control_surface_as_code.ui_api import handle_request

GOLDEN_DIR = Path(__file__).parent.parent / "ui" / "test" / "golden"
NON_MAPPING_FILES = {"controller.nt"}


class TestGoldenMappingFiles(unittest.TestCase):
    def test_golden_dir_exists_and_has_mappings(self):
        mapping_files = [p for p in GOLDEN_DIR.glob("*.nt") if p.name not in NON_MAPPING_FILES]
        self.assertGreaterEqual(len(mapping_files), 2, f"no golden mapping files in {GOLDEN_DIR}")

    def test_all_golden_files_validate(self):
        for path in sorted(GOLDEN_DIR.glob("*.nt")):
            if path.name in NON_MAPPING_FILES:
                continue
            with self.subTest(file=path.name):
                resp = handle_request({
                    "id": 1,
                    "method": "validate",
                    "params": {"mapping_text": path.read_text(),
                               "mapping_dir": str(GOLDEN_DIR)},
                })
                self.assertTrue(resp["ok"], resp)
                result = resp["result"]
                self.assertTrue(
                    result["valid"],
                    f"{path.name} rejected:\n" +
                    "\n".join(p["message"] for p in result["problems"]))


class TestGoldenGeneratesEndToEnd(unittest.TestCase):
    """The full 8-type document the UI serializes must generate an actual
    surface directory, not just validate."""

    def test_full_golden_generates_a_surface(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name in ("full.nt", "controller.nt", "functions.py"):
                shutil.copy(GOLDEN_DIR / name, tmp / name)
            text = (tmp / "full.nt").read_text()
            (tmp / "full.nt").write_text(
                text.replace("ableton_dir: /Applications/Ableton Live 12 Suite.app",
                             f"ableton_dir: {tmp}"))
            resp = handle_request({
                "id": 1, "method": "generate",
                "params": {"mapping_path": str(tmp / "full.nt")},
            })
            self.assertTrue(resp["ok"], resp)
            self.assertIn("Finished generating", resp["result"]["output"])
            self.assertTrue((tmp / "full" / "full.py").exists())
            self.assertTrue((tmp / "full" / "modules" / "main_component.py").exists())


if __name__ == "__main__":
    unittest.main()
