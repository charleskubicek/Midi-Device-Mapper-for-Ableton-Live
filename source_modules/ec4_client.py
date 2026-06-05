"""Faderfox EC4 text-readout feedback sink.

The EC4 has 16 encoders, each with a 4-character OLED readout. This sink writes
the currently-mapped parameter names to those readouts on every device-focus /
mode burst, mirroring what the HUD shows — but rendered on the controller itself.

Transport is MIDI SysEx out the surface's port (`manager._send_midi`), not UDP.
`HudClient` is the sibling sink over UDP; both are driven from `Remote` off the
same dial payloads, so the EC4 readouts stay in lock-step with the HUD.

Protocol validated byte-for-byte against Ableton's stock driver
`MIDI Remote Scripts/Faderfox_Universal_2/` (consts.py, faderfox_display_element.py)
and the Faderfox EC4 SysEx manual. The "set encoder display" message:

    F0 00 00 00            sysex start + 3-byte inventor id
    4E 2C 1B               device-id 0xCB  (APP_FUNC | 0xC0 | 11, EC4 = 11)
    4E 22 10               display type 0 = control names
    4A 2<ah> 1<al>         start char address (0..63), here 0
    4D 2<vh> 1<vl>  x N    one triple per char
    F7

16 cells x 4 chars = 64 char addresses; cell N starts at address N*4. We always
send the full 64-char buffer in one message (one handshake), exactly like the
stock driver. Unset cells are '-' (0x2D) — the EC4 only honours a live overwrite
for encoders whose configured name is '----', so dashes are the blank state.

NOTE: the EC4 setup/group must have all 16 encoder names set to '----' or the
readouts won't update (hardware-side overwrite rule).
"""
import logging
import re

logger = logging.getLogger("ec4-client")

# ---- SysEx framing (see module docstring) -----------------------------------
SYSEX_START = (0xF0, 0x00, 0x00, 0x00)
FADERFOX_EC4_DEVICE_ID = (0x4E, 0x2C, 0x1B)   # device-id byte 0xCB (EC4 = 11)
SET_TEXT_MSG_HEADER = (0x4E, 0x22, 0x10)      # APP_FUNC_DISP_CTRL (control names)
BASE_ADDRESS = (0x4A, 0x20, 0x10)             # start char address 0
SYSEX_END = (0xF7,)

NUM_CELLS = 16
CHARS_PER_CELL = 4
BLANK_CELL = "-" * CHARS_PER_CELL


# OLED character table (OLEDM204), copied verbatim from Ableton's stock
# Faderfox_Universal_2/consts.py. Maps an input character to the display's
# character code. For the common set (A-Z a-z 0-9 space . / -) the code equals
# the ASCII value, but routing through this table also gives a safe fallback
# (0x1F) for anything the display can't render.
CHARS = {char: idx for idx, char in enumerate("".join([
    '                ',
    '                ',
    ' !"# %&\'()*+,-./',
    '0123456789:;<=>?',
    ' ABCDEFGHIJKLMNO',
    'PQRSTUVWXYZÄÖ Ü§',
    ' abcdefghijklmno',
    'pqrstuvwxyzäö üà',
    '  ²³            ',
    '          ()    ',
    '@               ',
    '                ',
    '    _           ',
    '                ',
    '                ',
    '          [\\]<|>'
]))}
CHARS[' '] = 0x20


def translate_string(string):
    """Map a string to EC4 display character codes (returned as a str of
    chr(code)). Unknown chars become 0x1F; runs of whitespace collapse to one
    space. Matches Faderfox_Universal_2/consts.py:translate_string."""
    if not string:
        return ''
    translated = ''.join([chr(CHARS[char] if char in CHARS else 0x1F) for char in string])
    return re.sub(r'\s+', ' ', translated)


def _fit_cell(name):
    """Translate a label and fit it to exactly CHARS_PER_CELL display codes,
    truncating long names and padding short ones with '-'."""
    t = translate_string(name or '')[:CHARS_PER_CELL]
    return t.ljust(CHARS_PER_CELL, '-')


def _data_triple(code):
    return [0x4D, 0x20 | (code >> 4), 0x10 | (code & 0x0F)]


class Ec4Client:
    def __init__(self, manager):
        self._manager = manager

    def on_device_burst(self, device_name, dial_payloads, button_payloads=None):
        """Render the 16 dial labels to the EC4 readouts. `dial_payloads` is an
        iterable of (wire_idx, SlotPayload); wire_idx is the dense dial index,
        which equals the EC4 cell number for a row-major 4x4 knob grid.
        `button_payloads` is accepted for sink-interface symmetry but unused —
        the EC4's readouts belong to the encoders, not the buttons."""
        cells = [BLANK_CELL] * NUM_CELLS
        for wire_idx, payload in dial_payloads:
            if wire_idx < 0 or wire_idx >= NUM_CELLS:
                continue
            name = getattr(payload, 'name', '') or ''
            cells[wire_idx] = _fit_cell(name)
        self._send_cells(cells)

    def on_hide(self):
        self._send_cells([BLANK_CELL] * NUM_CELLS)

    def _send_cells(self, cells):
        text = "".join(cells)
        data = [b for ch in text for b in _data_triple(ord(ch))]
        payload = (list(SYSEX_START) + list(FADERFOX_EC4_DEVICE_ID)
                   + list(SET_TEXT_MSG_HEADER) + list(BASE_ADDRESS)
                   + data + list(SYSEX_END))
        try:
            self._manager._send_midi(tuple(payload))
        except Exception as e:
            # Route through the surface log so failures (e.g. a bad send path on
            # first bringup) land in tail_logs.sh, not just python logging.
            try:
                self._manager.log_message(f"Ec4Client._send_cells failed: {e}")
            except Exception:
                logger.error(f"Ec4Client._send_cells: {e}")


class NullEc4Client:
    def on_device_burst(self, device_name, dial_payloads, button_payloads=None): pass
    def on_hide(self): pass
