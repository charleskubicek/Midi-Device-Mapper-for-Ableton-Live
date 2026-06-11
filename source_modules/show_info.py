"""HUD show-info mode — edge-annotated button feedback.

When enabled (via the `showinfo` update.py command), every button press the
surface receives is explained on the HUD at the moment of the press, by emitting
an `EVENT` wire message the HUD renders + fades. See
momentary-vs-toggle-made-explicit-plan, item #7.

This module owns the *decision* of what text to emit for a given press; the HUD
owns rendering. Kept free of Live coupling so it is unit-testable: it takes a
`send_event(kind, wire_idx, text)` callable (the HudClient method)."""


def describe_edge(value, on_value=127):
    """Plain-words description of a single MIDI edge under the press-once model."""
    if value == 0:
        return "▲0 ignored (press-only)"
    if value == on_value:
        return f"▼{value} → acted"
    return f"▼{value} → acted (on-value≠{on_value})"


class ShowInfo:
    def __init__(self, send_event, log):
        self._send_event = send_event
        self._log = log
        self.enabled = False

    def toggle(self):
        self.enabled = not self.enabled
        self._log(f"[show-info] {'enabled' if self.enabled else 'disabled'}")
        return self.enabled

    def notify(self, fn_name, value, wire_idx=-1, kind='info'):
        """Emit an EVENT explaining this press. No-op unless enabled."""
        if not self.enabled:
            return
        text = f"{fn_name} {describe_edge(value)}"
        self._send_event(kind, wire_idx, text)
