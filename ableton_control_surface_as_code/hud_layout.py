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
# LayoutCell / SlotAddress live in the wire-format owner so codegen and runtime
# share one definition. Re-exported here for callers that import from
# hud_layout.
from source_modules.hud_protocol import LayoutCell, SlotAddress


# SF Symbol vocabulary for built-in button types (Phase 2b). Operation-type is
# encoded in the glyph family, direction in the .left/.right suffix, so the
# different "left/right" ops stay visually distinct. Names verified for the
# HUD's macOS 14 deployment target; a missing name degrades to text on the HUD
# (existence-gated render), so this table is safe to extend.
_TRACK_NAV_GLYPH = {'inc': 'chevron.right', 'dec': 'chevron.left'}
_DEVICE_NAV_GLYPH = {
    'left': 'arrowtriangle.left.fill',
    'right': 'arrowtriangle.right.fill',
    'first': 'arrow.left.to.line',
    'last': 'arrow.right.to.line',
    'first-last': 'arrow.left.and.right',
}
_TRANSPORT_GLYPH = {
    'play_stop_raw': 'playpause.fill',
    'record_session_raw': 'record.circle',
    'record_arrangement_raw': 'record.circle.fill',
    'loop_raw': 'repeat',
    'midi_arrange_overdub_raw': 'pencil.and.outline',
    'metronome_raw': 'metronome',
}
_PAGER_GLYPH = {'inc': 'chevron.down', 'dec': 'chevron.up'}


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
        if getattr(g, 'hud', True) is False:
            continue
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
        # A grid-layout group (`columns` set) is rendered as one cell per grid
        # row, so the HUD — which stacks cells by grid_row and lays each cell
        # out as a horizontal strip — tiles it into a `rows × columns` block
        # instead of one long strip. Wire indices stay global (start + offset),
        # so slot addressing via find_wire_index is unchanged.
        cols = getattr(g, 'columns', None)
        if cols and cols < count:
            for r in range((count + cols - 1) // cols):
                row_count = min(cols, count - r * cols)
                cells.append(LayoutCell(g.grid_row + r, g.grid_col, kind,
                                        row_count, start + r * cols, 0))
        else:
            cells.append(LayoutCell(g.grid_row, g.grid_col, kind, count, start, 0))
    return cells


def dial_count(cells: List[LayoutCell]) -> int:
    """Total dial slots across all dial cells (= the dial wire-index space)."""
    return sum(c.count for c in map(LayoutCell.from_raw, cells) if c.kind == 'dial')


def button_count(cells: List[LayoutCell]) -> int:
    """Total button slots across all button cells (= the button wire-index space)."""
    return sum(c.count for c in map(LayoutCell.from_raw, cells) if c.kind == 'button')


def offset_layout(cells: List[LayoutCell], dial_offset: int,
                  button_offset: int, section: int) -> List[LayoutCell]:
    """Return a copy of `cells` with each cell's wire `start` bumped by
    `dial_offset` / `button_offset` per kind and tagged with `section`.

    The cells keep their OWN grid_row/grid_col — placement beside the primary is
    the HUD's job (it renders each section as its own sub-grid). Only the wire
    start is bumped, because the dial/button slot arrays remain flat and shared
    across sections, so the secondary must not collide with the primary's range."""
    out: List[LayoutCell] = []
    for gr, gc, kind, count, start, _section in cells:
        bump = dial_offset if kind == 'dial' else button_offset
        out.append(LayoutCell(gr, gc, kind, count, start + bump, section))
    return out


def combine_layouts(primary: List[LayoutCell], secondary: List[LayoutCell]):
    """Concatenate two per-controller layouts into one cell list: the primary is
    section 0, the secondary section 1. The secondary keeps its own grid (the HUD
    lays each section out independently and places section 1 to the right of
    section 0), but its wire indices are bumped past the primary's dial/button
    counts so the shared flat slot arrays don't collide.

    Returns (combined_cells, dial_offset, button_offset). The offsets are what
    the RegionListener adds to incoming secondary slot indices to remap them
    into the shared wire space."""
    primary = [LayoutCell.from_raw(c) for c in primary]
    dial_offset = dial_count(primary)
    button_offset = button_count(primary)
    shifted = offset_layout(secondary, dial_offset, button_offset, section=1)
    return primary + shifted, dial_offset, button_offset


def _kind_for(group_type) -> str:
    if group_type == EncoderType.knob:
        return 'dial'
    if group_type == EncoderType.button:
        return 'button'
    # sliders aren't HUD-rendered today; tolerate by returning None
    return None


def find_wire_index(controller, coord: MidiCoords, cells: List[LayoutCell]):
    """Resolve a MidiCoords back to a SlotAddress(kind, wire_idx) using the
    controller's physical layout and the global allocation. Returns None if the
    coord doesn't correspond to a HUD-rendered control (e.g. a slider)."""
    if controller is None or coord is None:
        return None
    for group in controller.control_groups:
        if getattr(group, 'hud', True) is False:
            continue
        for i, gc in enumerate(group.midi_coords):
            if gc.midi_equals(coord):
                kind = _kind_for(group.type)
                if kind is None:
                    return None
                cell = _cell_for(cells, group.grid_row, group.grid_col, kind)
                if cell is None:
                    return None
                return SlotAddress(kind, cell.start + i)
    return None


def _cell_for(cells, gr, gc, kind):
    for cell in cells:
        if cell.grid_row == gr and cell.grid_col == gc and cell.kind == kind:
            return cell
    return None


def collect_mode_labels(controller, mode_mappings, cells) -> Dict[SlotAddress, Tuple[str, str]]:
    """For one mode's mappings, return {SlotAddress(kind, wire_idx): (name, glyph)}
    entries for every non-device mapping that occupies a HUD-rendered control.
    `glyph` is an optional SF Symbol name ("" = none). Device mappings are
    skipped — they're populated from live device data at runtime."""
    labels: Dict[SlotAddress, Tuple[str, str]] = {}
    for mapping in mode_mappings:
        for coord, name, glyph in _label_pairs_for_mapping(mapping):
            wire = find_wire_index(controller, coord, cells)
            if wire is None:
                continue
            labels[wire] = (name, glyph)
    return labels


def _label_pairs_for_mapping(mapping) -> List[Tuple[MidiCoords, str, str]]:
    """Return [(coord, name, glyph)] for every slot the mapping owns. `glyph` is
    an SF Symbol name or "" when the slot is text-only. Empty for device
    mappings — those are handled by the device path at runtime."""
    t = getattr(mapping, 'type', None)

    if t == 'device':
        # Device parameter cells are filled from live device data by the runtime
        # burst, so they carry no static label. The one exception is the fixed
        # on/off toggle — it's a constant function of the button, not a device
        # parameter, so give it a static label the burst won't overwrite.
        return [(mm.only_midi_coord, "dev on/off", "")
                for mm in mapping.midi_maps if getattr(mm, 'is_on_off', False)]

    if t == 'mixer':
        out = []
        for mm in mapping.midi_maps:
            label = mm.api_function
            if label == 'sends':
                # Sends span multiple coords; number them.
                for i, c in enumerate(mm.midi_coords, start=1):
                    out.append((c, f"send {i}", ""))
            else:
                # volume / pan / mute / solo / arm — single coord
                for c in mm.midi_coords:
                    out.append((c, label, ""))
        return out

    if t == 'functions':
        # The one type that carries a caller-chosen glyph today, via
        # `@hud_name(name, glyph)`.
        return [(mm.only_midi_coord, mm.hud_name or mm.function_name, mm.hud_glyph or "")
                for mm in mapping.midi_maps]

    if t == 'track-nav':
        return [(mm.only_midi_coord, f"track {mm.direction.value}",
                 _TRACK_NAV_GLYPH.get(mm.direction.value, "")) for mm in mapping.midi_maps]

    if t == 'device-nav':
        return [(mm.only_midi_coord, f"device {mm.action.value}",
                 _DEVICE_NAV_GLYPH.get(mm.action.value, "")) for mm in mapping.midi_maps]

    if t == 'transport':
        return [(mm.only_midi_coord, mm.api_call,
                 _TRANSPORT_GLYPH.get(mm.api_call, "")) for mm in mapping.midi_maps]

    if t == 'parameter-pager':
        return [(mm.only_midi_coord, f"page {mm.direction}",
                 _PAGER_GLYPH.get(mm.direction, "")) for mm in mapping.midi_maps]

    if t == 'clip':
        return [(mm.only_midi_coord, f"clip: {mm.spec.hud_label}", "") for mm in mapping.midi_maps]

    return []
