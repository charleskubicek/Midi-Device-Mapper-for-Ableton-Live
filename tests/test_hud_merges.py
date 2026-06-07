import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ableton_control_surface_as_code.model_merges import (
    read_merges,
    resolve_group_order,
    find_merges_file,
)

SAMPLE = """
merges:
  -
    name: lc_parks
    members:
      -
        source: main
        order: 0
      -
        source: parks_btns
        order: 1
"""


class TestReadMerges(unittest.TestCase):
    def test_parses_members(self):
        merges = read_merges(SAMPLE)
        self.assertEqual(len(merges.merges), 1)
        self.assertEqual(merges.merges[0].name, "lc_parks")
        self.assertEqual([m.source for m in merges.merges[0].members], ["main", "parks_btns"])

    def test_order_coerced_to_int(self):
        merges = read_merges(SAMPLE)
        self.assertEqual(merges.merges[0].members[1].order, 1)
        self.assertIsInstance(merges.merges[0].members[1].order, int)

    def test_resolve_member_returns_group_and_order(self):
        merges = read_merges(SAMPLE)
        self.assertEqual(merges.resolve("main"), ("lc_parks", 0))
        self.assertEqual(merges.resolve("parks_btns"), ("lc_parks", 1))

    def test_resolve_unknown_source_is_standalone(self):
        merges = read_merges(SAMPLE)
        self.assertEqual(merges.resolve("ec4"), ("ec4", 0))

    def test_empty_file_is_all_standalone(self):
        merges = read_merges("merges:\n")
        self.assertEqual(merges.resolve("anything"), ("anything", 0))

    def test_inline_comment_in_source_raises(self):
        # NestedText absorbs trailing '#' into the value — fail loudly.
        bad = (
            "merges:\n"
            "    -\n"
            "        name: g\n"
            "        members:\n"
            "            -\n"
            "                source: main   # a comment\n"
            "                order: 0\n"
        )
        with self.assertRaises(Exception):
            read_merges(bad)


class TestResolveGroupOrder(unittest.TestCase):
    def _make_tree(self, root: Path):
        # live_surfaces/_Global/merged_controllers.nt + live_surfaces/lc/map.nt
        global_dir = root / "live_surfaces" / "_Global"
        global_dir.mkdir(parents=True)
        (global_dir / "merged_controllers.nt").write_text(SAMPLE)
        mapping_dir = root / "live_surfaces" / "lc"
        mapping_dir.mkdir(parents=True)
        return mapping_dir

    def test_finds_global_file_walking_up(self):
        with TemporaryDirectory() as d:
            mapping_dir = self._make_tree(Path(d))
            found = find_merges_file(mapping_dir)
            self.assertIsNotNone(found)
            self.assertTrue(str(found).endswith("_Global/merged_controllers.nt"))

    def test_resolves_member_from_tree(self):
        with TemporaryDirectory() as d:
            mapping_dir = self._make_tree(Path(d))
            self.assertEqual(resolve_group_order(mapping_dir, "main"), ("lc_parks", 0))
            self.assertEqual(resolve_group_order(mapping_dir, "parks_btns"), ("lc_parks", 1))

    def test_standalone_when_no_global_file(self):
        with TemporaryDirectory() as d:
            mapping_dir = Path(d) / "live_surfaces" / "lc"
            mapping_dir.mkdir(parents=True)
            self.assertEqual(resolve_group_order(mapping_dir, "lc"), ("lc", 0))


if __name__ == '__main__':
    unittest.main()
