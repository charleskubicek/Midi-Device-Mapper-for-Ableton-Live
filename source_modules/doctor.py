"""Button doctor — hardware-mode diagnostic.

Runs inside the generated surface. When enabled (the `doctor` update.py command),
every button listener feeds its raw MIDI value here. The user presses each
button twice; `report()` then classifies each button's hardware behavior and —
crucially — says whether it matches what this surface is configured to assume
(`button-behaviour` in the controller .nt), with a concrete fix when it doesn't.

Classification (per button, from its observed edges):
- on→0 within ~200ms          → **momentary** (down + release per press)
- alternating on/0, far apart  → **toggle** (one event per press)
- on only, never 0             → **trigger**
- on-value ≠ 127               → flagged (a 127-only guard would never fire)

See momentary-vs-toggle-made-explicit-plan, item #9. Classification is pure
logic (no Live coupling) and unit-tested.
"""

MOMENTARY_WINDOW_S = 0.2


def classify_button(events, window_s=MOMENTARY_WINDOW_S):
    """Classify a single button from its `(value, timestamp)` events.

    Returns `(kind, on_value)` where kind is
    'momentary' | 'toggle' | 'trigger' | 'no-events' and on_value is the first
    non-zero value seen (the hardware "on" level), or None."""
    if not events:
        return 'no-events', None

    values = [v for v, _ in events]
    nonzero = [v for v in values if v != 0]
    on_value = nonzero[0] if nonzero else None
    has_zero = any(v == 0 for v in values)

    quick_release = any(
        v0 != 0 and v1 == 0 and (t1 - t0) <= window_s
        for (v0, t0), (v1, t1) in zip(events, events[1:])
    )

    if not has_zero:
        kind = 'trigger'
    elif quick_release:
        kind = 'momentary'
    else:
        kind = 'toggle'
    return kind, on_value


def _short_label(fn_name):
    """Trim the generated listener name to something readable in the log."""
    name = fn_name
    for suffix in ('_listener',):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    # keep the meaningful tail (e.g. ...switch1, ...fn_back8, ...device_nav_left)
    parts = name.split('__')
    return parts[-1] if len(parts) > 1 else name


class Doctor:
    def __init__(self, log, clock=None, assumed_behaviour='momentary'):
        import time
        self._log = log
        self._clock = clock or time.time
        self._assumed = assumed_behaviour
        self.enabled = False
        self._events = {}

    def toggle(self):
        self.enabled = not self.enabled
        self._events = {}
        if self.enabled:
            self._log("[doctor] ENABLED — press each button TWICE, then run "
                      "`doctor` again to see the report")
        else:
            self._log("[doctor] disabled")
        return self.enabled

    def observe(self, fn_name, value):
        if not self.enabled:
            return
        self._events.setdefault(fn_name, []).append((value, self._clock()))

    def report(self):
        if not self._events:
            self._log("[doctor] no button presses observed — enable, press each "
                      "button twice, then run `doctor` again")
            return

        self._log(f"[doctor] ===== button report (surface assumes "
                  f"button-behaviour: {self._assumed}) =====")
        mismatches = 0
        # 'trigger' is compatible with a momentary assumption (press-only acts on
        # the down); only momentary↔toggle is a real misfire.
        for fn_name in sorted(self._events):
            events = self._events[fn_name]
            kind, on_value = classify_button(events)
            seq = ' '.join(str(v) for v, _ in events)
            label = _short_label(fn_name)
            self._log(f"[doctor] {label}: {kind}  (saw: {seq})")

            if on_value is not None and on_value != 127:
                self._log(f"[doctor]   ⚠ on-value is {on_value}, not 127 — set this "
                          f"button's 'on' value to 127 in the controller editor")

            effective = 'momentary' if kind in ('momentary', 'trigger') else kind
            if kind != 'no-events' and effective != self._assumed:
                mismatches += 1
                self._log(f"[doctor]   ✗ MISMATCH: hardware is {kind} but surface "
                          f"assumes {self._assumed} → press-once buttons fire every "
                          f"OTHER press")
                self._log(f"[doctor]     fix: set `button-behaviour: {effective}` in "
                          f"the controller .nt, regenerate, redeploy")

        if mismatches == 0:
            self._log("[doctor] ✓ all buttons match the surface's assumed "
                      "button-behaviour")
        else:
            self._log(f"[doctor] {mismatches} button(s) mismatched — see fixes above")
