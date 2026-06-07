"""Parser for a composition config (e.g. `live_surfaces/lc_parks/lc_parks.nt`).

A composition declares the "primary-drives-the-whole-HUD" pairing: a PRIMARY
surface that owns its MIDI port and drives the entire HUD, and a display-only
SECONDARY surface that owns its own MIDI port but forwards its resolved HUD
region to the primary over UDP. Generating from a composition emits TWO surface
directories:

  - the named compositor surface (this file's stem, e.g. `lc_parks`) — the
    primary, with the secondary's grid placement baked in + a region listener;
  - the secondary forwarding surface — a normal surface whose HudClient is
    redirected at the compositor's `region-port` instead of the HUD.

File shape:

    ableton-dir: /Applications/Ableton Live 12 Suite.app
    primary: ../launch_control/ck_launch_control_16.nt
    secondary:
        mapping: ../parks/ck_parkstool_buttons.nt
        placement: right
    region-port: 5123        # optional; derived from the stem when omitted
"""
from pathlib import Path
from typing import Optional

from nestedtext import nestedtext as nt
from pydantic import BaseModel, Field


class SecondarySpec(BaseModel):
    mapping: str
    placement: str = 'right'   # only 'right' is meaningful today

    class Config:
        extra = 'forbid'


class CompositionRoot(BaseModel):
    ableton_dir: str = Field(alias='ableton-dir')
    primary: str
    secondary: SecondarySpec
    region_port: Optional[int] = Field(default=None, alias='region-port')

    class Config:
        extra = 'forbid'
        populate_by_name = True


def read_composition(text: str) -> CompositionRoot:
    data = nt.loads(text) or {}
    return CompositionRoot.model_validate(data)


def is_composition_file(path: Path) -> bool:
    """A config is a composition if it declares `primary:` and `secondary:`.
    Cheap top-level key sniff so `generate()` can dispatch without fully parsing
    (and without tripping a normal mapping's `extra='forbid'`)."""
    if path.suffix != '.nt':
        return False
    try:
        data = nt.loads(path.read_text()) or {}
    except Exception:
        return False
    return isinstance(data, dict) and 'primary' in data and 'secondary' in data
