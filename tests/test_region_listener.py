import unittest

from source_modules.region_state import RegionState
from source_modules.hud_protocol import (
    DeviceMsg, SlotMsg, CommitMsg, UpdateMsg, HideMsg, LayoutMsg, PingMsg, SlotPayload,
)


class CapturingHud:
    def __init__(self):
        self.updates = []
        self.pings = 0

    def send_update(self, kind, index, name, value, vmin, vmax):
        self.updates.append((kind, index, name, value, vmin, vmax))

    def send_ping(self):
        self.pings += 1


class TestRegionStateCaching(unittest.TestCase):
    def setUp(self):
        self.hud = CapturingHud()
        self.commits = []
        self.state = RegionState(
            self.hud, dial_offset=16, button_offset=4,
            on_commit=lambda: self.commits.append(True),
        )

    def test_burst_caches_with_offset_indices(self):
        self.state.handle(DeviceMsg("EQ Eight"))
        self.state.handle(SlotMsg('button', 0, SlotPayload("Hi", 1.0, 0.0, 1.0)))
        self.state.handle(SlotMsg('button', 1, SlotPayload("Lo", 0.0, 0.0, 1.0)))
        self.state.handle(CommitMsg(2))

        # button 0/1 from parks → combined 4/5 (button_offset=4)
        self.assertEqual(
            self.state.button_payloads(),
            [(4, SlotPayload("Hi", 1.0, 0.0, 1.0)), (5, SlotPayload("Lo", 0.0, 0.0, 1.0))],
        )
        # COMMIT triggers a combined re-burst on the primary
        self.assertEqual(len(self.commits), 1)

    def test_dial_offset_applied(self):
        self.state.handle(DeviceMsg("Dev"))
        self.state.handle(SlotMsg('dial', 2, SlotPayload("Cut", 0.5, 0.0, 1.0)))
        self.state.handle(CommitMsg(1))
        self.assertEqual(self.state.dial_payloads(), [(18, SlotPayload("Cut", 0.5, 0.0, 1.0))])

    def test_layout_from_secondary_is_ignored(self):
        # lc_parks bakes placement at codegen; it does not consume the
        # secondary's LAYOUT.
        self.state.handle(LayoutMsg([(0, 0, 'button', 8, 0)]))
        self.assertEqual(self.state.button_payloads(), [])

    def test_update_relays_remapped_to_hud_and_updates_cache(self):
        self.state.handle(DeviceMsg("Dev"))
        self.state.handle(SlotMsg('button', 0, SlotPayload("Hi", 0.0, 0.0, 1.0)))
        self.state.handle(CommitMsg(1))

        # live press on parks button 0 → UPDATE
        self.state.handle(UpdateMsg('button', 0, SlotPayload("Hi", 1.0, 0.0, 1.0)))

        # relayed to the real HUD with the combined index (0 + 4)
        self.assertEqual(self.hud.updates, [('button', 4, "Hi", 1.0, 0.0, 1.0)])
        # cache reflects the new value for the next combined burst
        self.assertEqual(self.state.button_payloads(), [(4, SlotPayload("Hi", 1.0, 0.0, 1.0))])

    def test_second_burst_replaces_first(self):
        self.state.handle(DeviceMsg("A"))
        self.state.handle(SlotMsg('dial', 0, SlotPayload("X", 0.1, 0.0, 1.0)))
        self.state.handle(CommitMsg(1))

        self.state.handle(DeviceMsg("B"))
        self.state.handle(SlotMsg('dial', 1, SlotPayload("Y", 0.2, 0.0, 1.0)))
        self.state.handle(CommitMsg(1))

        self.assertEqual(self.state.dial_payloads(), [(17, SlotPayload("Y", 0.2, 0.0, 1.0))])

    def test_ping_relayed_to_hud_keepalive(self):
        # A parks button/switch press emits PING (keepalive). The compositor
        # must relay it to the real HUD so its dismiss timer re-arms — otherwise
        # the HUD closes while the user is working the secondary controller.
        self.state.handle(PingMsg())
        self.assertEqual(self.hud.pings, 1)
        # PING is keepalive only — it must not trigger a combined re-burst.
        self.assertEqual(len(self.commits), 0)

    def test_hide_clears_region_without_reburst(self):
        # A parks HIDE (navigated away) must NOT trigger a combined re-burst —
        # a COMMIT would re-show the HUD and defeat auto-dismiss. It only drops
        # the cached region; lc_parks's own app-view HIDE hides the panel.
        self.state.handle(DeviceMsg("A"))
        self.state.handle(SlotMsg('dial', 0, SlotPayload("X", 0.1, 0.0, 1.0)))
        self.state.handle(CommitMsg(1))
        self.commits.clear()

        self.state.handle(HideMsg())
        self.assertEqual(self.state.dial_payloads(), [])
        self.assertEqual(len(self.commits), 0)


if __name__ == '__main__':
    unittest.main()
