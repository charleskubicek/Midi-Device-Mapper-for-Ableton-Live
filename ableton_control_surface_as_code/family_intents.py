"""
Loader for the device-family-intents JSON.

The JSON groups Ableton devices into families. Each device declares slots
(slot1..slot8, switch1, switch2) that map a canonical role (e.g. "Dry/Wet")
to a parameter number on that device.

Slots are used to drive runtime dispatch: when an encoder is mapped to a
slot, the listener looks up the currently selected device's class_name and
finds the parameter number for that slot on that class.

"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONTINUOUS_SLOT_NAMES = [f"slot{i}" for i in range(1, 9)]
MODE_SLOT_NAMES = [f"switch{i}" for i in range(1, 9)]
ALL_SLOT_NAMES = CONTINUOUS_SLOT_NAMES + MODE_SLOT_NAMES

# Switch action vocabulary. `cycle` is the original audio-family behavior
# (step through cycleMin..cycleMax). The rest cover the midi-family cases:
# pulse (0->1), inc, dec, random (single param), group_random (many params).
SWITCH_ACTIONS = {"cycle", "pulse", "inc", "dec", "random", "group_random"}


@dataclass(frozen=True)
class SlotEntry:
    parameter_number: int
    parameter_name: str
    cycle_min: Optional[int] = None
    cycle_max: Optional[int] = None
    action: str = "cycle"
    parameter_names: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_cycle(self) -> bool:
        return self.cycle_min is not None and self.cycle_max is not None


_DEFAULT_PATH = Path(__file__).parent.parent / "data" / "device_family_intents.json"


def load_family_intents(path: Path = _DEFAULT_PATH) -> Dict[str, Dict[str, SlotEntry]]:
    """
    Load the family-intents JSON and flatten into a lookup of:
        slot_name -> { class_name -> SlotEntry }
    Only entries with the slot defined for that class appear in the inner dict.
    """
    raw = json.loads(path.read_text())
    table: Dict[str, Dict[str, SlotEntry]] = {name: {} for name in ALL_SLOT_NAMES}

    for family in raw.get("families", []):
        for device in family.get("devices", []):
            class_name = device["className"]
            for slot_name, slot in device.get("slots", {}).items():
                if slot_name not in ALL_SLOT_NAMES:
                    continue
                action = slot.get("action", "cycle")
                if action not in SWITCH_ACTIONS:
                    raise ValueError(
                        f"Unknown action {action!r} for {class_name}.{slot_name}; "
                        f"expected one of {sorted(SWITCH_ACTIONS)}"
                    )
                # parameterNumber is required for cycle (legacy audio families)
                # but optional for midi actions that look up by parameterName at runtime.
                param_no = int(slot["parameterNumber"]) if "parameterNumber" in slot else -1
                # parameterName remains the canonical lookup key. group_random uses
                # parameterNames (a list) instead.
                param_name = str(slot.get("parameterName", ""))
                param_names = tuple(slot.get("parameterNames", []))
                table[slot_name][class_name] = SlotEntry(
                    parameter_number=param_no,
                    parameter_name=param_name,
                    cycle_min=int(slot["cycleMin"]) if "cycleMin" in slot else None,
                    cycle_max=int(slot["cycleMax"]) if "cycleMax" in slot else None,
                    action=action,
                    parameter_names=param_names,
                )

    return table


def is_continuous_slot(name: str) -> bool:
    return name in CONTINUOUS_SLOT_NAMES


def is_mode_slot(name: str) -> bool:
    return name in MODE_SLOT_NAMES


def parse_slot_token(token: str) -> str:
    """
    Accept canonical slot names (slot1..slot8, switch1, switch2) or bare integers
    (1..8, expanded to slot1..slot8). Returns the canonical name.
    Raises ValueError on anything else.
    """
    token = token.strip()
    if token in ALL_SLOT_NAMES:
        return token
    if token.isdigit():
        n = int(token)
        if 1 <= n <= 8:
            return f"slot{n}"
        raise ValueError(f"Slot index {n} out of range; only 1-8 are valid")
    raise ValueError(f"Unknown slot token: {token!r}")


def parse_continuous_slot_list(raw: str) -> List[str]:
    """
    Parse a slot list from the user's mapping NT under `encoders.slots`.
    Accepts:
        - `1-8`           range expansion to slot1..slot8
        - `1,3,5`         individual indices
        - `slot1,slot3`   explicit canonical names
        - mixes: `1,slot3,5-7`
    Rejects switch1 / switch2 (those belong in mode-buttons).
    """
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

    bad = [s for s in result if s in MODE_SLOT_NAMES]
    if bad:
        raise ValueError(
            f"{bad} are cycle-type slots and cannot appear under encoders.slots; "
            "place them under mode-buttons instead"
        )
    return result
