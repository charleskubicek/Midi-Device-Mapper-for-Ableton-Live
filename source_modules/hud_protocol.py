"""HUD wire protocol — pure encode/decode.

The transport (UDP send) lives in `hud_client.py`. Everything in this module
is pure: no sockets, no globals, no logging. That makes it cheap to test and
keeps a single source of truth for the bytes-on-the-wire format.

See `hud_protocol.md` for the spec. Mirrors the Swift `WireProtocol` parser
in /Users/ck/current/ableton_hud.
"""
from dataclasses import dataclass
from typing import List, Tuple, Union


# Empty-slot sentinel used by senders for any cell position not bound to a
# real parameter. Receivers render this as a blank slot.
EMPTY_NAME = ''
EMPTY_VALUE = 0
EMPTY_MIN = 0
EMPTY_MAX = 1


# (grid_row, grid_col, kind, count, start_index)
LayoutCell = Tuple[int, int, str, int, int]


@dataclass(frozen=True)
class SlotPayload:
    name: str
    value: float
    vmin: float
    vmax: float


EMPTY_SLOT = SlotPayload(EMPTY_NAME, EMPTY_VALUE, EMPTY_MIN, EMPTY_MAX)


# ---- encode -----------------------------------------------------------------

# Single-source protocol: the HUD has exactly one sender (a standalone surface,
# or the `lc_parks` compositor which merges any secondary region itself before
# emitting). No source/group/order on the wire.


def encode_layout(cells: List[LayoutCell]) -> str:
    parts = [str(len(cells))]
    for gr, gc, kind, count, start, section in cells:
        parts += [str(gr), str(gc), kind, str(count), str(start), str(section)]
    return "LAYOUT|" + "|".join(parts)


def encode_device(name: str) -> str:
    return f"DEVICE|{name}"


def encode_slot(kind: str, index: int, name: str, value, vmin, vmax) -> str:
    return f"SLOT|{kind}|{index}|{name}|{value}|{vmin}|{vmax}"


def encode_slot_payload(kind: str, index: int, payload: SlotPayload) -> str:
    return encode_slot(kind, index, payload.name, payload.value, payload.vmin, payload.vmax)


def encode_update(kind: str, index: int, name: str, value, vmin, vmax) -> str:
    return f"UPDATE|{kind}|{index}|{name}|{value}|{vmin}|{vmax}"


def encode_commit(count: int) -> str:
    return f"COMMIT|{count}"


def encode_ping() -> str:
    return "PING"


def encode_hide() -> str:
    return "HIDE"


def encode_page_info(enc_page: int, enc_total: int, btn_page: int, btn_total: int,
                     enc_label: str = '', btn_label: str = '') -> str:
    # Labels carry the standard-bank page name (e.g. "Amplitude / Filter") or
    # "Best of" for page 1 of a known device. Additive: when both labels are
    # empty we emit the short (counts-only) form.
    if not enc_label and not btn_label:
        return f"PAGE|{enc_page}|{enc_total}|{btn_page}|{btn_total}"
    return f"PAGE|{enc_page}|{enc_total}|{btn_page}|{btn_total}|{enc_label}|{btn_label}"


def encode_mode(is_shift: bool) -> str:
    return "MODE|shift" if is_shift else "MODE|normal"


# ---- parse ------------------------------------------------------------------

@dataclass(frozen=True)
class LayoutMsg:
    cells: List[LayoutCell]


@dataclass(frozen=True)
class DeviceMsg:
    name: str


@dataclass(frozen=True)
class SlotMsg:
    kind: str
    index: int
    payload: SlotPayload


@dataclass(frozen=True)
class UpdateMsg:
    kind: str
    index: int
    payload: SlotPayload


@dataclass(frozen=True)
class CommitMsg:
    count: int


@dataclass(frozen=True)
class PingMsg:
    pass


@dataclass(frozen=True)
class HideMsg:
    pass


@dataclass(frozen=True)
class ModeMsg:
    is_shift: bool


@dataclass(frozen=True)
class PageMsg:
    enc_page: int
    enc_total: int
    btn_page: int
    btn_total: int
    enc_label: str = ''
    btn_label: str = ''


@dataclass(frozen=True)
class UnknownMsg:
    line: str


Message = Union[LayoutMsg, DeviceMsg, SlotMsg, UpdateMsg, CommitMsg, PingMsg, HideMsg, ModeMsg, PageMsg, UnknownMsg]


def _parse_slot_fields(fields):
    # fields: [verb, kind, index, name, value, vmin, vmax]
    if len(fields) != 7:
        return None
    kind = fields[1]
    if kind not in ('dial', 'button'):
        return None
    try:
        index = int(fields[2])
        value = float(fields[4])
        vmin = float(fields[5])
        vmax = float(fields[6])
    except ValueError:
        return None
    return kind, index, SlotPayload(fields[3], value, vmin, vmax)


def parse(line: str) -> Message:
    line = line.rstrip('\r\n')
    if not line:
        return UnknownMsg(line)
    fields = line.split('|')
    verb = fields[0]

    if verb == 'LAYOUT':
        # LAYOUT|<n>|<gr>|<gc>|<kind>|<count>|<start>|<section>... × n
        if len(fields) < 2:
            return UnknownMsg(line)
        try:
            n = int(fields[1])
        except ValueError:
            return UnknownMsg(line)
        expected = 2 + n * 6
        if len(fields) != expected:
            return UnknownMsg(line)
        cells: List[LayoutCell] = []
        try:
            for i in range(n):
                base = 2 + i * 6
                cells.append((
                    int(fields[base]),
                    int(fields[base + 1]),
                    fields[base + 2],
                    int(fields[base + 3]),
                    int(fields[base + 4]),
                    int(fields[base + 5]),
                ))
        except ValueError:
            return UnknownMsg(line)
        return LayoutMsg(cells)

    if verb == 'DEVICE':
        if len(fields) < 2:
            return UnknownMsg(line)
        return DeviceMsg(fields[1])

    if verb in ('SLOT', 'UPDATE'):
        parsed = _parse_slot_fields(fields)
        if parsed is None:
            return UnknownMsg(line)
        kind, index, payload = parsed
        return (SlotMsg(kind, index, payload) if verb == 'SLOT'
                else UpdateMsg(kind, index, payload))

    if verb == 'COMMIT':
        if len(fields) != 2:
            return UnknownMsg(line)
        try:
            return CommitMsg(int(fields[1]))
        except ValueError:
            return UnknownMsg(line)

    if verb == 'PING':
        if len(fields) != 1:
            return UnknownMsg(line)
        return PingMsg()

    if verb == 'HIDE':
        if len(fields) != 1:
            return UnknownMsg(line)
        return HideMsg()

    if verb == 'MODE':
        if len(fields) == 2:
            return ModeMsg(is_shift=(fields[1] == 'shift'))
        return UnknownMsg(line)

    if verb == 'PAGE':
        if len(fields) not in (5, 7):
            return UnknownMsg(line)
        try:
            counts = (int(fields[1]), int(fields[2]), int(fields[3]), int(fields[4]))
        except ValueError:
            return UnknownMsg(line)
        if len(fields) == 7:
            return PageMsg(*counts, enc_label=fields[5], btn_label=fields[6])
        return PageMsg(*counts)

    return UnknownMsg(line)


def parse_all(data: str) -> List[Message]:
    return [parse(line) for line in data.split('\n') if line.strip()]
