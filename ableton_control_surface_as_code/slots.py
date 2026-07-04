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
    if ":" in raw:
        raise ValueError(
            f"'slots' expects device slot numbers (e.g. '1-16') or slot names, "
            f"not a controller coordinate: {raw!r}. The controller coordinate "
            f"goes under 'range:'; 'slots:' lists which device slots it drives.")
    result: List[str] = []
    for chunk in [c.strip() for c in raw.split(",") if c.strip()]:
        if "-" in chunk and not chunk.startswith("slot"):
            lo_s, hi_s = chunk.split("-", 1)
            try:
                lo, hi = int(lo_s), int(hi_s)
            except ValueError:
                raise ValueError(
                    f"Invalid slot range {chunk!r} in {raw!r}: expected numbers "
                    f"like '1-16' or slot names")
            if lo > hi:
                raise ValueError(f"Invalid slot range {chunk!r}: {lo} > {hi}")
            result.extend(parse_slot_token(str(n)) for n in range(lo, hi + 1))
        else:
            result.append(parse_slot_token(chunk))

    bad = [s for s in result if s in SWITCH_SLOT_NAMES]
    if bad:
        raise ValueError(
            f"{bad} are cycle-type slots and cannot appear under encoders.slots; "
            "place them under a device 'button'/'button-list' mapping instead"
        )
    return result


def parse_button_slot_list(raw: str) -> List[int]:
    """Parse a `button`/`button-list` 'slots:' value into 1-based integer device
    switch-slot indices (e.g. '5-16' -> [5, 6, ..., 16]). Unlike encoder slots,
    button slots are plain integers — there is no 'switchN'/'slotN' naming, so
    a slot number maps directly to a device switch index (switch_idx = n - 1)."""
    if ":" in raw:
        raise ValueError(
            f"'slots' expects device slot numbers (e.g. '1-16'), not a "
            f"controller coordinate: {raw!r}. The controller coordinate goes "
            f"under 'range:'; 'slots:' lists which device switch slots it drives.")
    result: List[int] = []
    for chunk in [c.strip() for c in raw.split(",") if c.strip()]:
        if "-" in chunk:
            lo_s, hi_s = chunk.split("-", 1)
            try:
                lo, hi = int(lo_s), int(hi_s)
            except ValueError:
                raise ValueError(
                    f"Invalid slot range {chunk!r} in {raw!r}: expected numbers "
                    f"like '1-16'")
            if lo > hi:
                raise ValueError(f"Invalid slot range {chunk!r}: {lo} > {hi}")
            if lo < 1:
                raise ValueError(f"Slot index {lo} out of range; must be >= 1")
            result.extend(range(lo, hi + 1))
        else:
            try:
                n = int(chunk)
            except ValueError:
                raise ValueError(f"Unknown slot token: {chunk!r}; expected an integer")
            if n < 1:
                raise ValueError(f"Slot index {n} out of range; must be >= 1")
            result.append(n)
    return result
