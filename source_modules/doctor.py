"""Button doctor — hardware-mode diagnostic.

Runs inside the generated surface. When enabled (via the `doctor` update.py
command), every button listener feeds its raw MIDI value here. The user presses
each button twice; `report()` then classifies each button's hardware behavior
against what the surface assumes (hardware-momentary):

- `127,0` within ~200ms          → hardware **momentary** (assumed; OK)
- `127` then `0` on separate presses → hardware **toggle**  (⚠ press-only mappings fire every other press)
- `127` only, never `0`          → hardware **trigger**
- on-value ≠ 127                 → ⚠ the press guard `value_is_max(value, 127)` will never fire

See momentary-vs-toggle-made-explicit-plan, item #9. The classification is pure
logic (no Live coupling) so it is unit-tested directly."""

MOMENTARY_WINDOW_S = 0.2


def classify_button(events, window_s=MOMENTARY_WINDOW_S):
    """Classify a single button from its observed `(value, timestamp)` events.

    Returns `(kind, warnings)` where kind is one of
    'momentary' | 'toggle' | 'trigger' | 'no-events', and warnings is a list of
    human-readable strings for mismatches against the momentary assumption."""
    if not events:
        return 'no-events', []

    values = [v for v, _ in events]
    nonzero = [v for v in values if v != 0]
    has_zero = any(v == 0 for v in values)
    warnings = []

    on_value = nonzero[0] if nonzero else None
    if on_value is not None and on_value != 127:
        warnings.append(
            f"on-value={on_value} (≠127): the press guard value_is_max(value, 127) "
            f"will never fire — this button is dead under press-only mappings")

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

    if kind == 'toggle':
        warnings.append(
            "hardware TOGGLE: press-only mappings will fire every other press "
            "(set the button to Momentary/Trigger in the controller editor)")
    elif kind == 'trigger':
        warnings.append(
            "hardware TRIGGER (never sends 0): fine for press-only mappings, "
            "but `momentary` (hold) mappings can never release")

    return kind, warnings


class Doctor:
    """Accumulates per-button events while enabled; emits a classification
    report to the Live log on demand."""

    def __init__(self, log, clock=None):
        import time
        self._log = log
        self._clock = clock or time.time
        self.enabled = False
        self._events = {}

    def toggle(self):
        self.enabled = not self.enabled
        self._events = {}
        self._log(f"[doctor] {'ENABLED — press each button twice, then run `doctor` again to report' if self.enabled else 'disabled'}")
        return self.enabled

    def observe(self, fn_name, value):
        if not self.enabled:
            return
        self._events.setdefault(fn_name, []).append((value, self._clock()))
        self._log(f"[doctor] {fn_name} value={value}")

    def report(self):
        if not self._events:
            self._log("[doctor] no button events observed")
            return
        self._log("[doctor] === button classification ===")
        for fn_name in sorted(self._events):
            kind, warnings = classify_button(self._events[fn_name])
            self._log(f"[doctor] {fn_name}: {kind}")
            for w in warnings:
                self._log(f"[doctor]   ⚠ {w}")
