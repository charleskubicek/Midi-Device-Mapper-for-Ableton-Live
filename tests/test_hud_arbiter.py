import unittest

from source_modules.hud_arbiter import elect_hud_owner, eligible_surfaces, count_hud_surfaces, HudArbiter


class FakeSurface:
    """Stand-in for a generated ControlSurface instance. Identity (`is`)
    matters for election, same as real Live instances in `control_surfaces`."""
    def __init__(self, name, hud_enabled=True):
        self._acsac_surface_name = name
        self._acsac_hud_enabled = hud_enabled


class UnrelatedSurface:
    """Stand-in for a non-generated surface (Push, a factory script): no
    _acsac_* attributes at all."""
    pass


class TestEligibleSurfaces(unittest.TestCase):
    def test_filters_none_slots_and_unrelated_and_hud_off(self):
        a = FakeSurface('ck_alpha')
        off = FakeSurface('ck_off', hud_enabled=False)
        siblings = [None, a, UnrelatedSurface(), off]
        self.assertEqual(eligible_surfaces(siblings), [a])

    def test_empty_or_none_list(self):
        self.assertEqual(eligible_surfaces(None), [])
        self.assertEqual(eligible_surfaces([]), [])


class TestElectHudOwner(unittest.TestCase):
    def test_single_hud_surface_always_owns(self):
        me = FakeSurface('ck_solo')
        self.assertTrue(elect_hud_owner([me], me))

    def test_lowest_name_wins_regardless_of_list_order(self):
        alpha = FakeSurface('ck_alpha')
        beta = FakeSurface('ck_beta')
        # beta listed first -- order must not matter, only the name.
        siblings = [beta, alpha]
        self.assertTrue(elect_hud_owner(siblings, alpha))
        self.assertFalse(elect_hud_owner(siblings, beta))

    def test_none_slots_and_unrelated_surfaces_are_ignored(self):
        alpha = FakeSurface('ck_alpha')
        siblings = [None, UnrelatedSurface(), alpha]
        self.assertTrue(elect_hud_owner(siblings, alpha))

    def test_hud_off_surface_never_owns_even_if_alone(self):
        off = FakeSurface('ck_off', hud_enabled=False)
        self.assertFalse(elect_hud_owner([off], off))

    def test_hud_off_surface_does_not_block_a_real_surface(self):
        off = FakeSurface('ck_aaa_off', hud_enabled=False)  # would sort first by name
        on = FakeSurface('ck_zzz_on')
        siblings = [off, on]
        self.assertTrue(elect_hud_owner(siblings, on))
        self.assertFalse(elect_hud_owner(siblings, off))

    def test_me_not_in_sibling_list_is_not_owner(self):
        alpha = FakeSurface('ck_alpha')
        stranger = FakeSurface('ck_alpha')  # same name, different instance
        self.assertFalse(elect_hud_owner([alpha], stranger))

    def test_no_eligible_surfaces_means_no_owner(self):
        me = FakeSurface('ck_me', hud_enabled=False)
        self.assertFalse(elect_hud_owner([me], me))


class TestCountHudSurfaces(unittest.TestCase):
    def test_counts_only_eligible_and_reports_owner_name(self):
        alpha = FakeSurface('ck_alpha')
        beta = FakeSurface('ck_beta')
        off = FakeSurface('ck_off', hud_enabled=False)
        count, owner_name = count_hud_surfaces([alpha, beta, off, None])
        self.assertEqual(count, 2)
        self.assertEqual(owner_name, 'ck_alpha')

    def test_no_hud_surfaces(self):
        self.assertEqual(count_hud_surfaces([]), (0, None))
        self.assertEqual(count_hud_surfaces(None), (0, None))


class FakeHudClientForArbiter:
    def __init__(self):
        self.enabled_calls = []

    def set_enabled(self, flag):
        self.enabled_calls.append(flag)


class FakeRemote:
    def __init__(self):
        self.resend_layout_calls = 0

    def resend_layout(self):
        self.resend_layout_calls += 1


class FakeHelpers:
    def __init__(self):
        self.update_calls = 0

    def update_remote_parameters(self):
        self.update_calls += 1


class FakeMainComponent:
    def __init__(self):
        self._hud_client = FakeHudClientForArbiter()
        self._remote = FakeRemote()
        self._helpers = FakeHelpers()


class FakeManagerSurface(FakeSurface):
    """Adds the plumbing HudArbiter.reelect touches beyond election itself:
    main_component, show_message, log_message. `reelect()` never imports
    Live, so this can be driven directly, without a running Ableton session --
    this is deliberately the same call `register()`'s observer and
    surface_name.py's recurring `_hud_arbiter_tick` both make, so exercising
    it here proves ownership transfer converges regardless of which of those
    two triggers actually fires at runtime."""
    def __init__(self, name, hud_enabled=True):
        super().__init__(name, hud_enabled)
        self.main_component = FakeMainComponent()
        self.messages = []
        self.logs = []
        self._control_surfaces = None  # set by the test

    def show_message(self, msg):
        self.messages.append(msg)

    def log_message(self, msg):
        self.logs.append(msg)


class TestHudArbiterReelect(unittest.TestCase):
    def test_becoming_owner_pushes_fresh_burst(self):
        me = FakeManagerSurface('ck_alpha')
        me._control_surfaces = [me]
        arbiter = HudArbiter(me)
        arbiter.reelect()
        self.assertTrue(arbiter._is_owner)
        self.assertEqual(me.main_component._hud_client.enabled_calls, [True])
        self.assertEqual(me.main_component._remote.resend_layout_calls, 1)
        self.assertEqual(me.main_component._helpers.update_calls, 1)

    def test_non_owner_is_disabled_and_gets_no_burst(self):
        alpha = FakeManagerSurface('ck_alpha')
        beta = FakeManagerSurface('ck_beta')
        siblings = [alpha, beta]
        beta._control_surfaces = siblings
        arb_beta = HudArbiter(beta)
        arb_beta.reelect()
        self.assertFalse(arb_beta._is_owner)
        self.assertEqual(beta.main_component._hud_client.enabled_calls, [False])
        self.assertEqual(beta.main_component._remote.resend_layout_calls, 0)

    def test_control_surfaces_accessed_as_a_method_not_a_property(self):
        # Regression: `ControlSurface._control_surfaces` is a plain instance
        # method on the real base class, not a property (confirmed by a
        # RemoteScriptError in the field: 'method' object is not iterable,
        # from treating the bound method itself as the sibling list). Model
        # that exact shape here so this can't silently regress.
        me = FakeManagerSurface('ck_alpha')
        siblings = [me]
        me._control_surfaces = lambda: siblings
        arbiter = HudArbiter(me)
        arbiter.reelect()
        self.assertTrue(arbiter._is_owner)
        self.assertEqual(me.main_component._hud_client.enabled_calls, [True])

    def test_relinquishing_ownership_disables_client(self):
        # The scenario at the heart of the fix: a previous owner must give up
        # ownership -- and go silent on the HUD -- purely as a result of
        # reelect() being called again with an updated sibling list. This is
        # exactly what both the control_surfaces observer AND the recurring
        # _hud_arbiter_tick reduce to, so this proves ownership transfer works
        # independent of which trigger actually fires in a real Live session.
        alpha = FakeManagerSurface('ck_alpha')
        arb = HudArbiter(alpha)
        alpha._control_surfaces = [alpha]
        arb.reelect()
        self.assertTrue(arb._is_owner)

        aaa = FakeManagerSurface('ck_aaa')  # sorts before 'ck_alpha'
        alpha._control_surfaces = [alpha, aaa]
        arb.reelect()
        self.assertFalse(arb._is_owner)
        self.assertEqual(alpha.main_component._hud_client.enabled_calls, [True, False])
        # Only enabled once (on first becoming owner) -- no repeat burst push
        # for a relinquish.
        self.assertEqual(alpha.main_component._remote.resend_layout_calls, 1)

    def test_multi_surface_notice_shown_once_then_gated_on_repeat(self):
        # reelect() runs on a ~1.5s recurring tick, so a plain "if count > 1:
        # show_message(...)" would spam the message pane every tick.
        alpha = FakeManagerSurface('ck_alpha')
        beta = FakeManagerSurface('ck_beta')
        siblings = [alpha, beta]
        alpha._control_surfaces = siblings
        arb = HudArbiter(alpha)

        arb.reelect()
        arb.reelect()  # simulates the next recurring tick, nothing changed

        self.assertEqual(len(alpha.messages), 1)
        self.assertIn('2 HUD surfaces loaded', alpha.messages[0])
        self.assertIn('ck_alpha owns the HUD', alpha.messages[0])

    def test_notice_reappears_after_a_change_and_back(self):
        alpha = FakeManagerSurface('ck_alpha')
        beta = FakeManagerSurface('ck_beta')
        arb = HudArbiter(alpha)

        alpha._control_surfaces = [alpha]
        arb.reelect()  # solo: no notice
        self.assertEqual(alpha.messages, [])

        alpha._control_surfaces = [alpha, beta]
        arb.reelect()  # two now: notice fires
        self.assertEqual(len(alpha.messages), 1)

        alpha._control_surfaces = [alpha]
        arb.reelect()  # back to solo: no new message, gate resets
        self.assertEqual(len(alpha.messages), 1)

        alpha._control_surfaces = [alpha, beta]
        arb.reelect()  # two again: this is a fresh occurrence, notice fires
        self.assertEqual(len(alpha.messages), 2)

    def test_solo_hud_surface_gets_no_notice(self):
        alpha = FakeManagerSurface('ck_alpha')
        alpha._control_surfaces = [alpha]
        arb = HudArbiter(alpha)
        arb.reelect()
        self.assertEqual(alpha.messages, [])


if __name__ == '__main__':
    unittest.main()
