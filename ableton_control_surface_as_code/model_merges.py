"""Parser for `live_surfaces/_Global/merged_controllers.nt`.

A merge topology declares which surfaces (by `hud_source` id) compose into one
HUD overlay, and in what left→right order. The topology is consumed at codegen
time: `resolve_group_order` stamps each generated surface with the `group` and
`order` it should advertise on the wire, so the HUD stays config-free and
composes purely from what each surface announces.

A surface whose source is not a member of any merge is "standalone" — it gets
`group == its own source`, `order == 0`, and renders as a lone region.

File shape:

    merges:
      - name: lc_parks
        members:
          - source: main
            order: 0
          - source: parks_btns
            order: 1
"""
from pathlib import Path
from typing import List, Optional, Tuple

from nestedtext import nestedtext as nt
from pydantic import BaseModel, Field, field_validator

GLOBAL_DIR_NAME = "_Global"
MERGES_FILENAME = "merged_controllers.nt"


class MergeMember(BaseModel):
    source: str
    order: int = 0

    class Config:
        extra = 'forbid'

    @field_validator('source')
    @classmethod
    def _no_whitespace(cls, v: str) -> str:
        # NestedText has no inline `#` comments — a trailing comment would be
        # silently absorbed into the value. Catch that (and stray spaces) loudly.
        if v != v.strip() or any(c.isspace() for c in v):
            raise ValueError(
                f"merge member source {v!r} contains whitespace — NestedText does not "
                f"support inline '#' comments; put comments on their own line"
            )
        return v


class Merge(BaseModel):
    name: str
    members: List[MergeMember]

    class Config:
        extra = 'forbid'


class MergesRoot(BaseModel):
    merges: List[Merge] = Field(default_factory=list)

    class Config:
        extra = 'forbid'

    def resolve(self, source: str) -> Tuple[str, int]:
        """Return (group, order) for a source id. Standalone sources (not a
        member of any merge) map to (source, 0)."""
        for merge in self.merges:
            for member in merge.members:
                if member.source == source:
                    return merge.name, member.order
        return source, 0


def read_merges(text: str) -> MergesRoot:
    """Parse merge-topology text. `nestedtext` coerces all scalars to strings,
    so `order` arrives as a string and Pydantic coerces it back to int."""
    data = nt.loads(text) or {}
    # `merges:` with no items parses to the empty string — normalize to a list.
    if not data.get('merges'):
        data = {**data, 'merges': []}
    return MergesRoot.model_validate(data)


def find_merges_file(mapping_dir: Path) -> Optional[Path]:
    """Walk up from a mapping's directory looking for a sibling
    `live_surfaces/_Global/merged_controllers.nt`. Returns None if no `_Global`
    folder is found on the way to the filesystem root."""
    for parent in [mapping_dir, *mapping_dir.parents]:
        candidate = parent / GLOBAL_DIR_NAME / MERGES_FILENAME
        if candidate.exists():
            return candidate
    return None


def resolve_group_order(mapping_dir: Path, source: str) -> Tuple[str, int]:
    """Resolve (group, order) for a source by locating and parsing the merge
    topology near `mapping_dir`. Falls back to standalone (source, 0) when no
    topology file exists."""
    merges_file = find_merges_file(mapping_dir)
    if merges_file is None:
        return source, 0
    return read_merges(merges_file.read_text()).resolve(source)
