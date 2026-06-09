"""Slot-name parsing — a leaf module with no internal dependencies.

Lives apart from `model_device` so that `core_model` can resolve slot lists
without depending on a leaf model module (which would create an import cycle).
Both `core_model` and `model_device` import from here.
"""
from typing import List


SWITCH_SLOT_NAMES = [f"switch{i}" for i in range(1, 9)]


def is_switch_slot(name: str) -> bool:
    return name in SWITCH_SLOT_NAMES


def parse_slot_token(token: str) -> str:
    token = token.strip()
    if token.startswith("slot") and token[4:].isdigit():
        return token
    if token in SWITCH_SLOT_NAMES:
        return token
    if token.isdigit():
        n = int(token)
        if n < 1:
            raise ValueError(f"Slot index {n} out of range; must be >= 1")
        return f"slot{n}"
    raise ValueError(f"Unknown slot token: {token!r}")


def parse_continuous_slot_list(raw: str) -> List[str]:
    result: List[str] = []
    for chunk in [c.strip() for c in raw.split(",") if c.strip()]:
        if "-" in chunk and not chunk.startswith("slot"):
            lo_s, hi_s = chunk.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo > hi:
                raise ValueError(f"Invalid slot range {chunk!r}: {lo} > {hi}")
            result.extend(parse_slot_token(str(n)) for n in range(lo, hi + 1))
        else:
            result.append(parse_slot_token(chunk))

    bad = [s for s in result if s in SWITCH_SLOT_NAMES]
    if bad:
        raise ValueError(
            f"{bad} are cycle-type slots and cannot appear under encoders.slots; "
            "place them under mode-buttons instead"
        )
    return result
