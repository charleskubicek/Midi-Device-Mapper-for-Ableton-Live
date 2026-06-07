"""Secondary-region cache + relay for the `lc_parks` compositor.

The parks surface forwards its already-resolved HUD region (DEVICE / SLOT /
COMMIT / UPDATE / HIDE) to lc_parks over UDP instead of to the HUD. lc_parks is
the single HUD sender; it merges the parks region into its own combined grid.

`RegionState` is the pure, socket-free core (so it's cheap to unit-test):
- caches the secondary's slots, remapped from the secondary's own wire indices
  into the combined wire space via the baked dial/button offsets,
- relays live `UPDATE`s straight to the real HUD (remapped),
- on a full secondary burst (`COMMIT`) or `HIDE`, calls `on_commit` so the
  primary re-emits the full combined burst (its own region + this cache).

`RegionListener` (region_listener.py) wraps this with the UDP socket.
"""
from typing import Callable, Dict, List, Optional, Tuple

from . import hud_protocol
from .hud_protocol import (
    DeviceMsg, SlotMsg, CommitMsg, UpdateMsg, HideMsg, SlotPayload,
)


class RegionState:
    def __init__(self, hud_client, dial_offset: int, button_offset: int,
                 on_commit: Optional[Callable[[], None]] = None):
        self._hud = hud_client
        self._dial_offset = dial_offset
        self._button_offset = button_offset
        self._on_commit = on_commit
        # Published cache (combined wire index -> payload), read by the primary
        # burst path. Pending buffers are swapped in on COMMIT.
        self._dials: Dict[int, SlotPayload] = {}
        self._buttons: Dict[int, SlotPayload] = {}
        self._pending_dials: Dict[int, SlotPayload] = {}
        self._pending_buttons: Dict[int, SlotPayload] = {}

    def _offset(self, kind: str) -> int:
        return self._dial_offset if kind == 'dial' else self._button_offset

    def handle(self, msg) -> None:
        if isinstance(msg, DeviceMsg):
            self._pending_dials = {}
            self._pending_buttons = {}
        elif isinstance(msg, SlotMsg):
            idx = msg.index + self._offset(msg.kind)
            if msg.kind == 'dial':
                self._pending_dials[idx] = msg.payload
            else:
                self._pending_buttons[idx] = msg.payload
        elif isinstance(msg, CommitMsg):
            self._dials = dict(self._pending_dials)
            self._buttons = dict(self._pending_buttons)
            self._fire_commit()
        elif isinstance(msg, UpdateMsg):
            idx = msg.index + self._offset(msg.kind)
            target = self._dials if msg.kind == 'dial' else self._buttons
            target[idx] = msg.payload
            p = msg.payload
            self._hud.send_update(msg.kind, idx, p.name, p.value, p.vmin, p.vmax)
        elif isinstance(msg, HideMsg):
            # Drop the secondary region but do NOT re-burst: a parks HIDE means
            # "navigated away", and a COMMIT here would re-show the HUD (DEVICE/
            # COMMIT clear the receiver's sticky dismiss), defeating auto-dismiss.
            # lc_parks's own app-view HIDE owns hiding the panel; the next
            # legitimate primary burst repaints without the parks region.
            self._dials = {}
            self._buttons = {}
        # LayoutMsg / PingMsg / ModeMsg / PageMsg from the secondary are ignored:
        # lc_parks bakes the secondary's placement at codegen and owns paging.

    def handle_data(self, data: str) -> None:
        for msg in hud_protocol.parse_all(data):
            self.handle(msg)

    def _fire_commit(self) -> None:
        if self._on_commit is not None:
            self._on_commit()

    def dial_payloads(self) -> List[Tuple[int, SlotPayload]]:
        return sorted(self._dials.items())

    def button_payloads(self) -> List[Tuple[int, SlotPayload]]:
        return sorted(self._buttons.items())
