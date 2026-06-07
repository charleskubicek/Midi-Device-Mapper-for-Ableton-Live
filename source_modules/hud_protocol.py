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

# Every message carries a `source` id as field[1] (right after the verb) so the
# receiver can attribute interleaved datagrams from multiple surfaces to the
# right per-source state. `LAYOUT` additionally carries the merge `group` and
# display `order` (sent once; the receiver remembers them per source). Defaults
# keep a single-controller surface on the wire as source/group 'main', order 0.
DEFAULT_SOURCE = 'main'
DEFAULT_GROUP = 'main'
DEFAULT_ORDER = 0


def encode_layout(cells: List[LayoutCell], source: str = DEFAULT_SOURCE,
                  group: str = DEFAULT_GROUP, order: int = DEFAULT_ORDER) -> str:
    parts = [source, group, str(order), str(len(cells))]
    for gr, gc, kind, count, start in cells:
        parts += [str(gr), str(gc), kind, str(count), str(start)]
    return "LAYOUT|" + "|".join(parts)


def encode_device(name: str, source: str = DEFAULT_SOURCE) -> str:
    return f"DEVICE|{source}|{name}"


def encode_slot(kind: str, index: int, name: str, value, vmin, vmax,
                source: str = DEFAULT_SOURCE) -> str:
    return f"SLOT|{source}|{kind}|{index}|{name}|{value}|{vmin}|{vmax}"


def encode_slot_payload(kind: str, index: int, payload: SlotPayload,
                        source: str = DEFAULT_SOURCE) -> str:
    return encode_slot(kind, index, payload.name, payload.value, payload.vmin, payload.vmax, source)


def encode_update(kind: str, index: int, name: str, value, vmin, vmax,
                  source: str = DEFAULT_SOURCE) -> str:
    return f"UPDATE|{source}|{kind}|{index}|{name}|{value}|{vmin}|{vmax}"


def encode_commit(count: int, source: str = DEFAULT_SOURCE) -> str:
    return f"COMMIT|{source}|{count}"


def encode_ping(source: str = DEFAULT_SOURCE) -> str:
    return f"PING|{source}"


def encode_hide(source: str = DEFAULT_SOURCE) -> str:
    return f"HIDE|{source}"


def encode_page_info(enc_page: int, enc_total: int, btn_page: int, btn_total: int,
                     enc_label: str = '', btn_label: str = '',
                     source: str = DEFAULT_SOURCE) -> str:
    # Labels carry the standard-bank page name (e.g. "Amplitude / Filter") or
    # "Best of" for page 1 of a known device. Additive: when both labels are
    # empty we emit the short (counts-only) form.
    if not enc_label and not btn_label:
        return f"PAGE|{source}|{enc_page}|{enc_total}|{btn_page}|{btn_total}"
    return f"PAGE|{source}|{enc_page}|{enc_total}|{btn_page}|{btn_total}|{enc_label}|{btn_label}"


def encode_mode(is_shift: bool, source: str = DEFAULT_SOURCE) -> str:
    return f"MODE|{source}|shift" if is_shift else f"MODE|{source}|normal"


# ---- parse ------------------------------------------------------------------

@dataclass(frozen=True)
class LayoutMsg:
    cells: List[LayoutCell]
    source: str = DEFAULT_SOURCE
    group: str = DEFAULT_GROUP
    order: int = DEFAULT_ORDER


@dataclass(frozen=True)
class DeviceMsg:
    name: str
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class SlotMsg:
    kind: str
    index: int
    payload: SlotPayload
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class UpdateMsg:
    kind: str
    index: int
    payload: SlotPayload
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class CommitMsg:
    count: int
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class PingMsg:
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class HideMsg:
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class ModeMsg:
    is_shift: bool
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class PageMsg:
    enc_page: int
    enc_total: int
    btn_page: int
    btn_total: int
    enc_label: str = ''
    btn_label: str = ''
    source: str = DEFAULT_SOURCE


@dataclass(frozen=True)
class UnknownMsg:
    line: str


Message = Union[LayoutMsg, DeviceMsg, SlotMsg, UpdateMsg, CommitMsg, PingMsg, HideMsg, ModeMsg, PageMsg, UnknownMsg]


def _parse_slot_fields(fields):
    # fields: [verb, source, kind, index, name, value, vmin, vmax]
    if len(fields) != 8:
        return None
    kind = fields[2]
    if kind not in ('dial', 'button'):
        return None
    try:
        index = int(fields[3])
        value = float(fields[5])
        vmin = float(fields[6])
        vmax = float(fields[7])
    except ValueError:
        return None
    return kind, index, SlotPayload(fields[4], value, vmin, vmax)


def parse(line: str) -> Message:
    line = line.rstrip('\r\n')
    if not line:
        return UnknownMsg(line)
    fields = line.split('|')
    verb = fields[0]
    # fields[1] is the source id on every message.
    source = fields[1] if len(fields) >= 2 else DEFAULT_SOURCE

    if verb == 'LAYOUT':
        # LAYOUT|<src>|<group>|<order>|<n>|<gr>|<gc>|<kind>|<count>|<start>... × n
        if len(fields) < 5:
            return UnknownMsg(line)
        try:
            group = fields[2]
            order = int(fields[3])
            n = int(fields[4])
        except ValueError:
            return UnknownMsg(line)
        expected = 5 + n * 5
        if len(fields) != expected:
            return UnknownMsg(line)
        cells: List[LayoutCell] = []
        try:
            for i in range(n):
                base = 5 + i * 5
                cells.append((
                    int(fields[base]),
                    int(fields[base + 1]),
                    fields[base + 2],
                    int(fields[base + 3]),
                    int(fields[base + 4]),
                ))
        except ValueError:
            return UnknownMsg(line)
        return LayoutMsg(cells, source=source, group=group, order=order)

    if verb == 'DEVICE':
        if len(fields) < 3:
            return UnknownMsg(line)
        return DeviceMsg(fields[2], source=source)

    if verb in ('SLOT', 'UPDATE'):
        parsed = _parse_slot_fields(fields)
        if parsed is None:
            return UnknownMsg(line)
        kind, index, payload = parsed
        return (SlotMsg(kind, index, payload, source=source) if verb == 'SLOT'
                else UpdateMsg(kind, index, payload, source=source))

    if verb == 'COMMIT':
        if len(fields) != 3:
            return UnknownMsg(line)
        try:
            return CommitMsg(int(fields[2]), source=source)
        except ValueError:
            return UnknownMsg(line)

    if verb == 'PING':
        if len(fields) != 2:
            return UnknownMsg(line)
        return PingMsg(source=source)

    if verb == 'HIDE':
        if len(fields) != 2:
            return UnknownMsg(line)
        return HideMsg(source=source)

    if verb == 'MODE':
        if len(fields) >= 3:
            return ModeMsg(is_shift=(fields[2] == 'shift'), source=source)
        return UnknownMsg(line)

    if verb == 'PAGE':
        if len(fields) not in (6, 8):
            return UnknownMsg(line)
        try:
            counts = (int(fields[2]), int(fields[3]), int(fields[4]), int(fields[5]))
        except ValueError:
            return UnknownMsg(line)
        if len(fields) == 8:
            return PageMsg(*counts, enc_label=fields[6], btn_label=fields[7], source=source)
        return PageMsg(*counts, source=source)

    return UnknownMsg(line)


def parse_all(data: str) -> List[Message]:
    return [parse(line) for line in data.split('\n') if line.strip()]
