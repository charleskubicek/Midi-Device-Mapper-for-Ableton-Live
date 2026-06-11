"""Generate a per-surface BEHAVIOR.md: one row per button describing, in plain
words, what a single press does. Doubles as living documentation of the
press-once-by-default model (see momentary-vs-toggle-made-explicit-plan):
buttons act once on press unless they carry the `momentary` refinement.

Pure codegen — no runtime cost. Built from the resolved ModeGroupWithMidi so it
reflects exactly what the generated surface will do."""
from typing import List, Tuple

from ableton_control_surface_as_code.encoder_coords import EncoderRefinements


def coord_label(controller, mc) -> str:
    """Reverse-map a resolved MidiCoords back to its `row-N:M` coordinate by
    scanning the controller layout. Falls back to a midi identity string when
    the controller is unavailable or the coord isn't found (e.g. synthetic)."""
    if controller is not None:
        for g in controller.control_groups:
            for i, gmc in enumerate(g.midi_coords):
                if gmc.midi_equals(mc):
                    return f"row-{g.number}:{i + 1}"
    return f"ch{mc.channel}/{mc.type.value}{mc.number}"


def _refinement_names(mc) -> List[str]:
    return [r.name() for r in mc.encoder_refs]


def _press_phrase(kind: str, mc) -> str:
    refs = EncoderRefinements(mc.encoder_refs)
    if kind == 'device_param':
        if refs.has_momentary():
            return "on while held (`momentary`)"
        return "toggles the parameter, once per press"
    if kind == 'switch':
        return "cycles/toggles the slot, once per press"
    if kind == 'mixer':
        return "framework-handled (Ableton mixer button)"
    # method-call buttons: functions / transport / track-nav / device-nav / clip
    if refs.has_momentary():
        return "fires on press *and* release (`momentary`)"
    return "fires once, on press"


def _iter_buttons(mode_with_midi):
    """Yield (mode_name, mapping_type, mc, action_text, kind) for every button.
    `kind` selects the press-behavior phrasing; continuous knobs/sliders are
    skipped (they have no press semantic)."""
    for mode_name, with_midis in mode_with_midi.mappings:
        for wm in with_midis:
            t = wm.type
            if t == 'device':
                for mm in wm.midi_maps:
                    mc = mm.only_midi_coord
                    if mc.encoder_type.is_button():
                        yield (mode_name, t, mc, f"device parameter {mm.parameter}", 'device_param')
                for mb in getattr(wm, 'switch_maps', []):
                    yield (mode_name, t, mb.only_midi_coord, f"slot {mb.slot}", 'switch')
            else:
                for mm in wm.midi_maps:
                    for mc in mm.midi_coords:
                        if mc.encoder_type.is_button():
                            kind = 'mixer' if t == 'mixer' else t
                            yield (mode_name, t, mc, mm.short_info_string(), kind)


def build_behavior_doc(mode_with_midi, controller=None, surface_name: str = "") -> str:
    """Render the BEHAVIOR.md markdown for a surface's buttons."""
    rows: List[Tuple[str, str, str, str, str, str]] = []
    for mode_name, t, mc, action, kind in _iter_buttons(mode_with_midi):
        refs = _refinement_names(mc)
        refs_text = ", ".join(f"`{r}`" for r in refs) if refs else "—"
        rows.append((
            mode_name,
            coord_label(controller, mc),
            t,
            action,
            refs_text,
            _press_phrase(kind, mc),
        ))

    title = f"# Button behavior — {surface_name}" if surface_name else "# Button behavior"
    lines = [
        title,
        "",
        "Generated documentation of what one press of each button does. Buttons "
        "act **once on press** by default; add the `momentary` refinement for "
        "on-while-held (params) / fire-on-both-edges (functions).",
        "",
    ]
    if not rows:
        lines.append("_No buttons mapped on this surface._")
        return "\n".join(lines) + "\n"

    lines.append("| Mode | Coord | Type | Mapping | Refinements | One press… |")
    lines.append("|---|---|---|---|---|---|")
    for mode_name, coord, t, action, refs_text, phrase in rows:
        lines.append(f"| {mode_name} | {coord} | {t} | {action} | {refs_text} | {phrase} |")
    return "\n".join(lines) + "\n"
