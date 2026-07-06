import logging

logger = logging.getLogger("hud-arbiter")


# --- pure election logic (no Live import; fully unit-testable) -------------

def _is_hud_enabled(surface):
    return getattr(surface, '_acsac_hud_enabled', False)


def eligible_surfaces(surfaces):
    """Filter a sibling list (e.g. `self._control_surfaces`, which may contain
    `None` slots, non-generated surfaces (Push, factory scripts), and
    generated-but-HUD-off surfaces) down to the ones eligible to own the HUD."""
    return [s for s in (surfaces or []) if s is not None and _is_hud_enabled(s)]


def elect_hud_owner(surfaces, me):
    """True iff `me` is the elected HUD owner among `surfaces`.

    Owner = the eligible surface with the smallest `_acsac_surface_name` (a
    stable, codegen-baked key) -- not list position, so ownership doesn't
    depend on load order and is reproducible across sessions. A surface that
    isn't itself HUD-enabled never owns, even if it's the only one in the list
    (it has nothing to show)."""
    if not _is_hud_enabled(me):
        return False
    candidates = eligible_surfaces(surfaces)
    if not candidates:
        return False
    owner = min(candidates, key=lambda s: (getattr(s, '_acsac_surface_name', ''), id(s)))
    return owner is me


def count_hud_surfaces(surfaces):
    """(count, owner_name) among eligible siblings -- for the operator-facing
    message pane notice. (0, None) when no HUD-enabled surface is loaded."""
    candidates = eligible_surfaces(surfaces)
    if not candidates:
        return 0, None
    owner = min(candidates, key=lambda s: (getattr(s, '_acsac_surface_name', ''), id(s)))
    return len(candidates), getattr(owner, '_acsac_surface_name', None)


# --- Live wiring -------------------------------------------------------------

class HudArbiter:
    """Elects a single HUD owner among all currently-loaded generated
    surfaces, so independently-generated surfaces co-loaded in Live don't
    fight over the shared 127.0.0.1:5006 HUD sink.
    Only the elected owner's HudClient stays enabled; the rest go silent on
    the HUD (see HudClient.set_enabled) -- this kills both the cross-surface
    HIDE flicker and burst interleaving by construction, since the HUD only
    ever hears from one sender.

    Built on two facts about the Ableton Remote Script host:
    - `ControlSurface.__init__` publishes `self` into a registry shared across
      every loaded script, retrieved by calling `self._control_surfaces()` --
      a plain instance method on the base class, NOT a property, confirmed by
      a RemoteScriptError in the field ('method' object is not iterable) after
      an initial guess got this wrong -- so a surface can read a sibling's
      Python attributes directly (Ableton's own AutoArmComponent uses this
      same mechanism to coordinate across surfaces).
    - `Live.Application.control_surfaces` is observable, so re-election can be
      driven by every load/unload rather than a single startup check.
    """

    def __init__(self, manager):
        self.manager = manager
        self._app = None
        self._is_owner = False
        # Last (count, owner_name) we posted a message-pane notice for, so the
        # recurring reelect() tick doesn't re-post the same notice every 1.5s.
        self._last_notice = None

    def register(self):
        """Start observing `control_surfaces` and run an initial election.
        Safe to call once, after `manager.main_component` exists."""
        import Live
        try:
            self._app = Live.Application.get_application()
            self._app.add_control_surfaces_listener(self.reelect)
        except Exception as e:
            self.manager.log_message(f"HudArbiter: failed to register control_surfaces listener: {e}")
        self.reelect()

    def unregister(self):
        if self._app is not None:
            try:
                self._app.remove_control_surfaces_listener(self.reelect)
            except Exception:
                pass
            self._app = None

    def _sibling_surfaces(self):
        """Accessor for the shared registry. `_control_surfaces` is a plain
        method on the real ControlSurface base class -- call it. Tests stand
        in a plain list/None for simplicity, so tolerate that shape too."""
        accessor = getattr(self.manager, '_control_surfaces', None)
        return accessor() if callable(accessor) else accessor

    def reelect(self):
        """Recompute ownership and gate this surface's HudClient accordingly.
        Idempotent; called both from the best-effort control_surfaces
        observer (near-instant transfer when it fires) and from a recurring
        ~1.5s tick (surface_name.py's `_hud_arbiter_tick`) that guarantees
        convergence even if the observer never fires -- see the call site for
        why that guarantee matters."""
        siblings = self._sibling_surfaces()
        was_owner = self._is_owner
        self._is_owner = elect_hud_owner(siblings, self.manager)

        hud_client = getattr(self.manager.main_component, '_hud_client', None)
        if hud_client is not None:
            hud_client.set_enabled(self._is_owner)

        if self._is_owner and not was_owner:
            # Just became owner (first election, or the previous owner
            # unloaded): push a fresh full burst so the HUD reflects this
            # surface instead of staying on whatever the old owner last sent.
            try:
                main = self.manager.main_component
                main._remote.resend_layout()
                main._helpers.update_remote_parameters()
            except Exception as e:
                self.manager.log_message(f"HudArbiter: refresh burst on election failed: {e}")

        count, owner_name = count_hud_surfaces(siblings)
        if self._is_owner and count > 1:
            # Gate on change: reelect() runs on a ~1.5s recurring tick, so an
            # unconditional show_message here would spam the message pane
            # with the same notice roughly once per tick.
            notice = (count, owner_name)
            if notice != self._last_notice:
                msg = f"HUD: {count} HUD surfaces loaded; {owner_name} owns the HUD"
                self.manager.show_message(msg)
                self.manager.log_message(msg)
                self._last_notice = notice
        else:
            self._last_notice = None
