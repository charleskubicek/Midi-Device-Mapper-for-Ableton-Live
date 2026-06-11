"""HUD wire protocol — pure encode/decode.

The transport (UDP send) lives in `hud_client.py`. Everything in this module
is pure: no sockets, no globals, no logging. That makes it cheap to test and
keeps a single source of truth for the bytes-on-the-wire format.

See `hud_protocol.md` for the spec. Mirrors the Swift `WireProtocol` parser
in /Users/ck/current/ableton_hud.
"""
from dataclasses import dataclass
from typing import List, NamedTuple, Union


# Empty-slot sentinel used by senders for any cell position not bound to a
# real parameter. Receivers render this as a blank slot.
EMPTY_NAME = ''
EMPTY_VALUE = 0
EMPTY_MIN = 0
EMPTY_MAX = 1


class LayoutCell(NamedTuple):
    """One HUD grid cell on the wire. `section` groups cells into
    independently-laid-out blocks: a standalone surface emits everything as
    section 0; the lc_parks compositor tags the secondary controller section 1
    so the HUD renders it as its own sub-grid to the right of the primary.

    A NamedTuple (not a plain tuple) so producers/consumers get named field
    access, but it stays tuple-compatible — it unpacks, indexes, compares equal
    to the matching plain tuple, and `repr()`s into an `eval`-able literal.
    This is the single source of truth for the LAYOUT cell shape; both the
    codegen side (`hud_layout`) and the runtime (`helpers`) import it from here,
    the wire-format owner.
    """
    grid_row: int
    grid_col: int
    kind: str          # 'dial' or 'button'
    count: int
    start: int
    section: int = 0

    @classmethod
    def from_raw(cls, c) -> "LayoutCell":
        """Accept either a LayoutCell or a plain tuple (as baked into generated
        surfaces at the template boundary) and return a LayoutCell."""
        return c if isinstance(c, cls) else cls(*c)


class SlotAddress(NamedTuple):
    """A HUD slot's wire address: which array ('dial'|'button') and the index
    within it. Tuple-compatible, so it interoperates with the `(kind, index)`
    plain tuples used as label-dict keys and baked into generated surfaces."""
    kind: str
    index: int


@dataclass(frozen=True)
class SlotPayload:
    name: str
    value: float
    vmin: float
    vmax: float


EMPTY_SLOT = SlotPayload(EMPTY_NAME, EMPTY_VALUE, EMPTY_MIN, EMPTY_MAX)


@dataclass(frozen=True)
class PageInfo:
    """Encoder/button paging state for a burst. Replaces the old
    "4-tuple or 6-tuple" page_info that forced arity-sniffing at the callee.
    The labels carry the standard-bank page name (e.g. "Amplitude / Filter")
    or "Best of"; empty labels make the wire fall back to the counts-only
    PAGE form (see encode_page_info)."""
    enc_page: int = 1
    enc_total: int = 1
    btn_page: int = 1
    btn_total: int = 1
    enc_label: str = ''
    btn_label: str = ''


@dataclass(frozen=True)
class BurstSnapshot:
    """One device-focus burst as data. Bundles what used to be the 14
    positional params of Remote.device_update / refresh_burst so the burst
    path has one thing to pass around and feedback sinks have room to grow.

    dials/buttons are sequences of (wire_idx, SlotPayload). page=None means
    "don't emit a PAGE line" (mixer/transport bursts that have no paging);
    device bursts always carry a PageInfo."""
    device_name: str
    dials: tuple = ()
    buttons: tuple = ()
    page: 'PageInfo' = None
    suppress_hud: bool = False


# ---- encode -----------------------------------------------------------------

# Single-source protocol: the HUD has exactly one sender (a standalone surface,
# or the `lc_parks` compositor which merges any secondary region itself before
# emitting). No source/group/order on the wire.


def encode_layout(cells: List[LayoutCell]) -> str:
    parts = [str(len(cells))]
    for gr, gc, kind, count, start, section in cells:
        parts += [str(gr), str(gc), kind, str(count), str(start), str(section)]
    return "LAYOUT|" + "|".join(parts)


# `encode_layout` unpacks 6 fields; this assertion guards the LayoutCell shape
# against silently regrowing/shrinking out of sync with the wire format.
assert len(LayoutCell._fields) == 6


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


def encode_event(kind: str, wire_idx: int, text: str) -> str:
    # Show-info feedback: explains a button press on the HUD at the moment it
    # happens (see momentary-vs-toggle-made-explicit-plan, item #7). `kind` is
    # the slot kind ('button'/'dial') or 'info' when not tied to a HUD cell;
    # `wire_idx` is the HUD button-array index (-1 when none). `text` is free
    # form and may itself contain '|', so it is always the final field.
    safe_text = text.replace('\n', ' ')
    return f"EVENT|{kind}|{wire_idx}|{safe_text}"


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
class EventMsg:
    kind: str
    wire_idx: int
    text: str


@dataclass(frozen=True)
class UnknownMsg:
    line: str


Message = Union[LayoutMsg, DeviceMsg, SlotMsg, UpdateMsg, CommitMsg, PingMsg, HideMsg, ModeMsg, PageMsg, EventMsg, UnknownMsg]


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
                cells.append(LayoutCell(
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

    if verb == 'EVENT':
        # EVENT|<kind>|<wire_idx>|<text...> — text is the rest, may contain '|'.
        if len(fields) < 4:
            return UnknownMsg(line)
        try:
            wire_idx = int(fields[2])
        except ValueError:
            return UnknownMsg(line)
        text = '|'.join(fields[3:])
        return EventMsg(fields[1], wire_idx, text)

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
