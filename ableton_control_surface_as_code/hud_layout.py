"""Codegen-time helpers for HUD layout: assign global wire indices to every
physical control on the surface, and walk per-mode mappings to produce
(kind, wire_idx) → label dicts for non-device mappings.

Device mappings are intentionally excluded from the labels dict — the device
path populates those slots at runtime from the focused device's parameters.
The mode-aware burst overlays these static labels on top of the device
payloads (see `Helpers.refresh_hud_for_mode`).
"""
from typing import Dict, List, Tuple

from ableton_control_surface_as_code.core_model import EncoderType, MidiCoords


# (grid_row, grid_col, kind, count, start_index)
LayoutCell = Tuple[int, int, str, int, int]


def allocate_global_layout(controller) -> List[LayoutCell]:
    """Walk every ControlGroup on the controller and assign sequential wire
    start indices per kind. Dial cells share one index space; button cells
    share another."""
    if controller is None:
        return []
    # Stable order: by grid_row then grid_col, dials first within a row.
    groups = sorted(
        controller.control_groups,
        key=lambda g: (g.grid_row, g.grid_col),
    )
    cells: List[LayoutCell] = []
    dial_next = 0
    button_next = 0
    for g in groups:
        kind = _kind_for(g.type)
        if kind is None:
            continue
        count = len(g.midi_coords)
        if kind == 'dial':
            start = dial_next
            dial_next += count
        else:
            start = button_next
            button_next += count
        cells.append((g.grid_row, g.grid_col, kind, count, start))
    return cells


def _kind_for(group_type) -> str:
    if group_type == EncoderType.knob:
        return 'dial'
    if group_type == EncoderType.button:
        return 'button'
    # sliders aren't HUD-rendered today; tolerate by returning None
    return None


def find_wire_index(controller, coord: MidiCoords, cells: List[LayoutCell]):
    """Resolve a MidiCoords back to (kind, wire_idx) using the controller's
    physical layout and the global allocation. Returns None if the coord
    doesn't correspond to a HUD-rendered control (e.g. a slider)."""
    if controller is None or coord is None:
        return None
    for group in controller.control_groups:
        for i, gc in enumerate(group.midi_coords):
            if gc.midi_equals(coord):
                kind = _kind_for(group.type)
                if kind is None:
                    return None
                cell = _cell_for(cells, group.grid_row, group.grid_col, kind)
                if cell is None:
                    return None
                _gr, _gc, _k, _count, start = cell
                return kind, start + i
    return None


def _cell_for(cells, gr, gc, kind):
    for cell in cells:
        if cell[0] == gr and cell[1] == gc and cell[2] == kind:
            return cell
    return None


def collect_mode_labels(controller, mode_mappings, cells) -> Dict[Tuple[str, int], str]:
    """For one mode's mappings, return {(kind, wire_idx): label} entries for
    every non-device mapping that occupies a HUD-rendered control.
    Device mappings are skipped — they're populated from live device data
    at runtime, not from static labels."""
    labels: Dict[Tuple[str, int], str] = {}
    for mapping in mode_mappings:
        for coord, label in _label_pairs_for_mapping(mapping):
            wire = find_wire_index(controller, coord, cells)
            if wire is None:
                continue
            labels[wire] = label
    return labels


def _label_pairs_for_mapping(mapping) -> List[Tuple[MidiCoords, str]]:
    """Return [(coord, label)] for every slot the mapping owns. Empty for
    device mappings — those are handled by the device path at runtime."""
    t = getattr(mapping, 'type', None)

    if t == 'device':
        return []

    if t == 'mixer':
        out = []
        for mm in mapping.midi_maps:
            label = mm.api_function
            if label == 'sends':
                # Sends span multiple coords; number them.
                for i, c in enumerate(mm.midi_coords, start=1):
                    out.append((c, f"send {i}"))
            else:
                # volume / pan / mute / solo / arm — single coord
                for c in mm.midi_coords:
                    out.append((c, label))
        return out

    if t == 'functions':
        return [(mm.only_midi_coord, mm.function_name) for mm in mapping.midi_maps]

    if t == 'track-nav':
        return [(mm.only_midi_coord, f"track {mm.direction.value}") for mm in mapping.midi_maps]

    if t == 'device-nav':
        return [(mm.only_midi_coord, f"device {mm.action.value}") for mm in mapping.midi_maps]

    if t == 'transport':
        return [(mm.only_midi_coord, mm.api_call) for mm in mapping.midi_maps]

    if t == 'parameter-pager':
        return [(mm.only_midi_coord, f"page {mm.direction}") for mm in mapping.midi_maps]

    return []
