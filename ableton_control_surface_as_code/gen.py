import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
import shutil
from string import Template
from collections import defaultdict
from typing import Optional, Tuple

from ableton_control_surface_as_code.gen_code import class_function_body_code_block, \
    class_function_code_block, get_python_code_error, device_templates, GeneratedCode, \
    functions_templates, mixer_templates, track_nav_templates, device_nav_templates, \
    transport_templates, dict_variable_decleration_block, GeneratedCodes, \
    parameter_pager_templates, clip_templates
from ableton_control_surface_as_code.model_v2 import read_controller, \
    read_root, ModeGroupWithMidi, read_root_v2, ModeData, AllMappingWithMidiTypes, HudMode, HudTrigger, \
    ModeType, build_validated_model
from ableton_control_surface_as_code.gen_error import GenError, ErrorCode
from ableton_control_surface_as_code.core_model import EncoderType
from ableton_control_surface_as_code.encoder_coords import EncoderRefinements
from ableton_control_surface_as_code.behavior_doc import build_behavior_doc
from ableton_control_surface_as_code.hud_layout import (
    allocate_global_layout, collect_mode_labels, combine_layouts,
)
from ableton_control_surface_as_code.model_composition import is_composition_file, read_composition
from ableton_control_surface_as_code.model_custom_devices import validate_custom_device_mappings
from source_modules.hud_protocol import encode_layout

tab = " " * 4


def tabs(n):
    return tab * n


def setup_template(mode_name, mode_button_midi=None):
    # A composition secondary has modes but no physical mode-button (mode_button_midi
    # is None): emit the FSM state without a button element. self.mode_button stays
    # at its __init__ default (None), so goto_mode's LED feedback is guarded off.
    lines = [
        "self.current_mode = None",
        f"self._first_mode = '{mode_name}'",
    ]
    if mode_button_midi is not None:
        midi_type = 'MIDI_NOTE_TYPE' if mode_button_midi.type.is_note() else 'MIDI_CC_TYPE'
        lines.append(
            f"self.mode_button = ConfigurableButtonElement(True, {midi_type}, "
            f"{mode_button_midi.ableton_channel()}, {mode_button_midi.number})")
    body = ("\n" + tabs(2)).join(lines)
    return f"""
        {body}
    """


def creation_template(mode_name):
    return f"""
        self.current_mode = self._modes['{mode_name}']
        self.goto_mode(self._first_mode)
        """


def add_listeners_template(mode_name):
    return f"""
    def mode_{mode_name}_add_listeners(self):
        self.log_message(f'Adding listeners for mode {mode_name}')
    """


def remove_listeners_template():
    return f"""
        if not modes_only:
            self.mode_button.remove_value_listener(self.mode_button_listener)
    """


def state_dict_template(mode: ModeData, listners_function):
    return f"""
        self._modes['{mode.name}'] = {{
            'name': '{mode.name}',
            'next_mode_name': '{mode.next}',
            'add_listeners_fn': {listners_function},
            'is_shift': {mode.is_shift},
            'color': {mode.color}
        }}
"""


def array_def_template(array_name, array_values):
    end = ",\n" + tabs(3)
    return f"""
        self.{array_name} = [
             {end.join([f"self.{v.controller_variable_name()}" for v in array_values])}
        ]
    """


def all_control_defs(mode_codes):
    res = []

    for mode_code in mode_codes.values():
        for device in mode_code:
            for cf in device.control_defs:
                res.append(cf)

    return res


def generate_code_as_template_vars(modes: ModeGroupWithMidi, controller=None, hud_mode: HudMode = HudMode.On, hud_trigger: HudTrigger = HudTrigger.ControllerNav, feedback=None, outputs=None, hud_cells_override=None) -> dict:
    first_mode_name = modes.first_mode_name()

    # Global wire-index allocation: every physical control on the surface
    # gets a wire slot, regardless of which mode binds it. Modes overlay
    # static labels onto these slots at runtime.
    #
    # The lc_parks compositor passes `hud_cells_override` = the combined grid
    # (primary cells + offset secondary cells) so the LAYOUT it emits, and the
    # slots it builds, span both controllers. Primary mappings still resolve to
    # their original (unchanged) wire indices within that combined grid.
    hud_cells_raw = hud_cells_override if hud_cells_override is not None else allocate_global_layout(controller)

    mode_codes = create_code_model(modes, controller=controller, hud_cells=hud_cells_raw)

    array_defs = []
    codes = GeneratedCode()
    creation = [c.variable_initialisation() for c in all_control_defs(mode_codes)]

    creation.append(f"self.mode_{first_mode_name}_add_listeners()")

    for name, code_model in mode_codes.items():
        merge = GeneratedCodes.merge_all(code_model)
        codes.remove_listeners.append(class_function_body_code_block(merge.remove_listeners))
        codes.setup_listeners.append(add_listeners_template(name))
        codes.setup_listeners.append(class_function_body_code_block(merge.setup_listeners))
        codes.listener_fns.append(class_function_code_block(merge.listener_fns))
        codes.custom_parameter_mappings.append(",\n\t\t\t".join(merge.custom_parameter_mappings))
        codes.switch_parameter_mappings.append(",\n\t\t\t".join(merge.switch_parameter_mappings))

        for (name, values) in merge.array_defs:
            array_defs.append(array_def_template(name, values))

    if modes.has_modes():
        has_mode_button = modes.mode_button is not None
        creation.append(creation_template(first_mode_name))
        mode_btn_midi = modes.mode_button.button if has_mode_button else None
        codes.init.append(setup_template(first_mode_name, mode_button_midi=mode_btn_midi))

        for mode in modes.fsm():
            codes.init.append(state_dict_template(mode, f"self.mode_{mode.name}_add_listeners"))

        # The physical mode-button listener + its teardown only exist when there
        # IS a button. A composition secondary's FSM is driven remotely
        # (mode_link -> goto_mode), so it has neither.
        if has_mode_button:
            codes.remove_listeners.append(remove_listeners_template())
            codes.init.append(f"{tabs(2)}self.mode_button.add_value_listener(self.mode_button_listener)\n")

    device_mappings = [
        m for _, mode_maps in modes.mappings
        for m in mode_maps
        if m.type == 'device'
    ]
    encoder_slot_count = max((m.encoder_slot_count for m in device_mappings), default=8)

    if hud_mode == HudMode.DeviceOnly:
        mode_hud_labels = {mode_name: {} for mode_name, _ in modes.mappings}
    else:
        mode_hud_labels = {
            mode_name: collect_mode_labels(controller, mode_maps, hud_cells_raw)
            for mode_name, mode_maps in modes.mappings
        }

    hud_client_class = 'NullHudClient' if hud_mode == HudMode.Off else 'HudClient'

    # Generic feedback sinks listed under `feedback:` in the mapping file. Each
    # maps to a constructor expression rendered into main_component.py. The HUD
    # keeps its own dedicated client; these are additional output targets driven
    # off the same burst (see Remote._feedback_sinks).
    feedback_sink_ctors = {
        'ec4_text': 'Ec4Client(self.manager)',
    }
    feedback_sinks = ", ".join(
        feedback_sink_ctors[d.type.value] for d in (feedback or [])
    )

    osc_clients = ", ".join(
        f"OSCClient(host='{t.host}', port={t.port})"
        for sink in (outputs or [])
        if sink.type.value == 'osc'
        for t in sink.targets
    )

    return {
        'code_setup': "\n".join(codes.init),
        'code_custom_parameter_mappings': dict_variable_decleration_block(codes.custom_parameter_mappings),
        'code_switch_parameter_mappings': dict_variable_decleration_block(codes.switch_parameter_mappings),
        'code_creation': class_function_body_code_block(creation + array_defs),
        'code_remove_listeners': "\n".join(codes.remove_listeners),
        'code_setup_listeners': "\n".join(codes.setup_listeners),
        'code_listener_fns': "\n".join(codes.listener_fns),
        'encoder_slot_count': encoder_slot_count,
        # Bake LayoutCell / SlotAddress as PLAIN tuples at the template
        # boundary: the generated surface evals this literal without needing the
        # NamedTuple classes in scope. Helpers.__init__ re-wraps cells via
        # LayoutCell.from_raw; label keys stay (kind, wire_idx) tuples, which the
        # runtime looks up with plain tuples anyway (R3 step 5).
        'hud_cells': repr([tuple(c) for c in hud_cells_raw]),
        'mode_hud_labels': repr({
            mode_name: {tuple(k): v for k, v in labels.items()}
            for mode_name, labels in mode_hud_labels.items()
        }),
        'hud_client_class': hud_client_class,
        'hud_trigger': repr(hud_trigger.value),
        # Hardware button mode (momentary vs toggle): drives the runtime
        # press-once guard so the same mapping works on both kinds of hardware.
        'button_behaviour': repr(controller.button_behaviour.value if controller is not None else 'momentary'),
        'feedback_sinks': feedback_sinks,
        'osc_clients': osc_clients,
        '_hud_cells_raw': hud_cells_raw,
    }


def create_code_model(modes, controller=None, hud_cells=None):
    return {mode_name: build_mode_code(maps, mode_name, controller=controller, hud_cells=hud_cells)
            for mode_name, maps in modes.mappings}


template_to_code = {
    'mixer': mixer_templates,
    'track-nav': track_nav_templates,
    'device-nav': device_nav_templates,
    'functions': functions_templates,
    'transport': transport_templates,
    'parameter-pager': parameter_pager_templates,
    'clip': clip_templates,
}

def warn_deprecated_toggle(mode_with_midi: ModeGroupWithMidi, mapping_source: str = "") -> None:
    """`toggle` is now the default (buttons act once on press), so any surviving
    `toggle` keyword is redundant. Emit a one-line stderr deprecation warning per
    affected mode so configs can be cleaned up. `momentary` (which wins on
    conflict) is the keyword that actually changes behaviour now."""
    seen = set()
    for mode_name, withMidis in mode_with_midi.mappings:
        for withMidi in withMidis:
            for midi_map in withMidi.midi_maps:
                for mc in midi_map.midi_coords:
                    if EncoderRefinements(mc.encoder_refs).has_toggle():
                        key = (mode_name, mc.source_info)
                        if key in seen:
                            continue
                        seen.add(key)
                        src = f"{mapping_source}: " if mapping_source else ""
                        print(
                            f"WARNING: 'toggle' is now the default and can be removed "
                            f"({src}mode '{mode_name}', {mc.source_info})",
                            file=sys.stderr)


def build_mode_code(mode_mappings, name, controller=None, hud_cells=None) -> list[GeneratedCode]:
    res = []
    for mapping in mode_mappings:
        if mapping.type == 'device':
            res.extend(device_templates(mapping, name, controller=controller, hud_cells=hud_cells))
        else:
            res.extend(template_to_code[mapping.type](mapping, name))

    return res


def write_templates(template_path: Path, target: Path, vars: dict):
    root_dir = Path(target, vars['surface_name'])
    root_dir.mkdir(exist_ok=True)

    template_file(root_dir, template_path / 'surface_name', vars, "__init__.py", "__init__.py")
    template_file(root_dir, template_path / 'surface_name', vars, f'modules/main_component.py',
                  f"modules/main_component.py", verify_python=True)
    # template_file(root_dir, template_path / 'surface_name', vars, "modules/helpers.py", "modules/helpers.py")
    # template_file(root_dir, template_path / 'surface_name', vars, "modules/nav.py", "modules/nav.py")
    template_file(root_dir, template_path / 'surface_name', vars, 'surface_name.py', f"{vars['surface_name']}.py")
    template_file(root_dir, template_path, vars, 'deploy.sh', 'deploy.sh')
    template_file(root_dir, template_path, vars, 'tail_logs.sh', 'tail_logs.sh')
    template_file(root_dir, template_path, vars, 'update.py', 'update.py')


def template_file(root_dir, template_path, vars: dict, source_file_name, target_file_name, verify_python=False):
    target_file = root_dir / target_file_name
    target_file.parent.mkdir(exist_ok=True)
    new_text = Template((template_path / source_file_name).read_text()).substitute(
        vars)

    if verify_python:
        err = get_python_code_error(new_text)
        if err is not None:
            error_text = f"Code failed validation for file {target_file}: error {err}"
            print("\033[31m" + error_text + ".\033[0m")

    target_file.write_text(new_text)


def generate_5_digit_number(input_string):
    hex_digest = hashlib.sha256(input_string.encode()).hexdigest()
    five_digits = int(hex_digest[:5], 16)
    return 10000 + (five_digits % 55535)


def validate_path(string):
    if not Path(string).exists():
        raise ValueError(f"File {string} does not exist")
    else:
        return string


def print_hud_layout(hud_cells_raw):
    layout_line = encode_layout(hud_cells_raw)
    print("HUD wire messages:")
    print(f"  {layout_line}")
    print()
    print("  HUD cells breakdown:")
    for gr, gc, kind, count, start, section in hud_cells_raw:
        mapped = f"slots {start}..{start + count - 1}" if start >= 0 else "unmapped"
        print(f"    sec={section} grid({gr},{gc})  {kind:<8}  count={count}  {mapped}")


def print_ascii_layout(controller):
    symbol = {
        EncoderType.knob: '(o)',
        EncoderType.button: '[■]',
        EncoderType.slider: '[-]',
    }

    # Group control groups by grid_row
    by_row = {}
    for g in controller.control_groups:
        by_row.setdefault(g.grid_row, []).append(g)

    for grid_row in sorted(by_row):
        cols = sorted(by_row[grid_row], key=lambda g: g.grid_col)
        parts = []
        for g in cols:
            s = symbol.get(g.type, '[?]')
            row_label = f"row-{g.number}"
            controls = ' '.join([s] * len(g.midi_coords))
            parts.append(f"{row_label}: {controls}")
        print('  |  '.join(parts))


def generate(input_path):
    """Generate one or more surfaces from a config file. A composition config
    (declares `primary:`/`secondary:`) emits the lc_parks compositor + the
    secondary forwarder; any other config is a normal single surface."""
    if is_composition_file(input_path):
        generate_composition(input_path)
    else:
        target_dir = Path('out') if input_path == Path.cwd() else input_path.parent
        _generate_surface(input_path, input_path.stem, target_dir)


@dataclass
class CompositionOverrides:
    """The handful of values the lc_parks compositor injects into an otherwise
    normal surface. Everything here is DATA the template consumes as a constant
    (see REGION_CONFIG / HUD_TARGET in main_component.py) — never a code string.
    All-None is a standalone surface."""
    hud_target: Optional[Tuple[str, int]] = None     # forwarder's HUD client (host, port)
    region_config: Optional[dict] = None             # compositor's {dial_offset, button_offset, port}
    hud_cells: Optional[list] = None                 # combined layout override
    hud_trigger: Optional['HudTrigger'] = None       # force show-hud-on (compositor: Selection)
    mode_link: Optional[dict] = None                 # reverse mode channel {role: sender|listener, port}


def _generate_surface(mapping_file_path, surface_name, target_dir, overrides=None):
    """Build and write a single surface directory named `surface_name` under
    `target_dir`, from the mapping at `mapping_file_path`. Returns
    (controller, code_vars). `overrides` (CompositionOverrides) carries the
    compositor's combined layout + region config and the forwarder's HUD target,
    all as data the template gates on."""
    overrides = overrides if overrides is not None else CompositionOverrides()
    def _resolve_controller(root):
        controller_path = mapping_file_path.parent / root.controller
        return controller_path.read_text(), controller_path.name

    mappings, controller, mode_with_midi = build_validated_model(
        mapping_file_path.read_text(),
        mapping_file_path.parent,
        resolve_controller=_resolve_controller,
        mapping_source=mapping_file_path.name)

    warn_deprecated_toggle(mode_with_midi, mapping_file_path.name)

    parameter_mappings_raw = None
    if mappings.parameter_mappings_file is not None:
        pm_path = (mapping_file_path.parent / mappings.parameter_mappings_file).resolve()
        if not pm_path.exists():
            raise ValueError(f"parameter_mappings_file not found: {pm_path}")
        parameter_mappings_raw = json.loads(pm_path.read_text())
        validate_custom_device_mappings(parameter_mappings_raw)

    vars = {
        'surface_name': surface_name,
        'udp_port': generate_5_digit_number(surface_name) + 1,
        # OSC button-input listener port — unique per surface so multiple
        # surfaces can run at once (was a hardcoded 5015 that collided).
        'osc_listen_port': generate_5_digit_number(surface_name) + 2,
        'class_name_snake': 'control_mappings',
        'class_name_camel': 'ControlMappings',
        'ableton_dir': validate_path(mappings.ableton_dir),
        'parameter_mappings_raw': repr(parameter_mappings_raw),
        # HUD client target as data. None -> the HUD on 127.0.0.1:5006; the parks
        # forwarder sets (host, port) to reach the compositor's region port.
        'hud_target': repr(overrides.hud_target),
        # Compositor region config as data (lc_parks only). None for normal surfaces.
        'region_config': repr(overrides.region_config),
        # Reverse mode channel config as data (lc_parks only). None otherwise.
        'mode_link': repr(overrides.mode_link),
    }

    hud_trigger = overrides.hud_trigger if overrides.hud_trigger is not None else mappings.show_hud_on
    code_vars = generate_code_as_template_vars(mode_with_midi, controller=controller, hud_mode=mappings.hud, hud_trigger=hud_trigger, feedback=mappings.feedback, outputs=mappings.outputs, hud_cells_override=overrides.hud_cells)
    mode_vars = vars | code_vars
    write_templates(Path(f'templates'), target_dir, mode_vars)

    # Living documentation of the press-once-by-default model: one row per
    # button describing what a single press does.
    behavior_md = build_behavior_doc(mode_with_midi, controller=controller, surface_name=surface_name)
    (target_dir / surface_name / "BEHAVIOR.md").write_text(behavior_md)

    # # copy all .py files into the modules folder
    for file in mapping_file_path.parent.glob('*.py'):
        shutil.copy(file, target_dir / vars['surface_name'] / "modules" / file.name)

    # copy all files and folders in the source_modules folder to target_dir
    for file in Path('source_modules').glob('*'):
        if file.is_file():
            shutil.copy(file, target_dir / vars['surface_name'] / "modules")
        else:
            shutil.copytree(file, target_dir / vars['surface_name'] / "modules" / file.name, dirs_exist_ok=True)

    # Bundle the Ableton stock-device parameter banks alongside helpers so
    # name-based resolution works in the generated surface (no `data` package
    # is on sys.path inside Live).
    banks_src = Path('data/live_device_banks.py')
    if banks_src.exists():
        shutil.copy(banks_src, target_dir / vars['surface_name'] / "modules" / banks_src.name)

    print(f"Finished generating {surface_name}.")
    print()
    print_hud_layout(code_vars['_hud_cells_raw'])
    print()
    print_ascii_layout(controller)
    return controller, code_vars


def _declared_mode_names(root):
    """Mode names the user actually declared (the synthesized single-mode
    wrapper for a modeless mapping doesn't count)."""
    return [m.name for m in root.modes if not m.is_fake_wrapper_mode]


def validate_composition_modes(primary_root, secondary_root):
    """When the secondary declares its own modes, the primary's shift drives them
    over the reverse mode channel (mode_link). Guard the config so the two FSMs
    map 1:1: the primary must own a `type: shift` mode-button, the secondary must
    NOT declare its own mode-button (it is driven purely from the primary), and
    their declared mode names must match exactly (same names, same order)."""
    secondary_modes = _declared_mode_names(secondary_root)
    if not secondary_modes:
        return  # secondary has no modes — the primary's shift only affects the primary.

    primary_modes = _declared_mode_names(primary_root)
    problems = []

    if primary_root.mode_button is None or primary_root.mode_button.type != ModeType.Shift:
        problems.append(
            "the secondary declares modes, so the primary must declare a "
            "`type: shift` mode-button to drive them.")

    if secondary_root.mode_button is not None:
        problems.append(
            "the secondary must not declare its own `mode-button:` — its shift is "
            "driven by the primary. Remove the secondary's mode-button.")

    if primary_modes != secondary_modes:
        problems.append(
            f"secondary modes {secondary_modes} must match the primary modes "
            f"{primary_modes} exactly (identical names, same order) so the "
            f"primary's forwarded shift maps 1:1.")

    if problems:
        raise GenError(
            "Invalid lc_parks composition:\n" + "\n".join(f"  - {p}" for p in problems),
            ErrorCode.SEMANTIC_VALIDATION)


def generate_composition(comp_path):
    comp = read_composition(comp_path.read_text())
    comp_dir = comp_path.parent
    comp_stem = comp_path.stem  # e.g. lc_parks

    primary_path = (comp_dir / comp.primary).resolve()
    secondary_path = (comp_dir / comp.secondary.mapping).resolve()

    # Both surfaces are emitted INTO the composition folder under unique,
    # composition-namespaced names (no dashes — Ableton won't load those). This
    # makes each surface unambiguously "part of lc_parks": the secondary here is
    # always the forwarder, never confusable with a standalone build of the same
    # mapping. Role = the referenced mapping's parent dir (launch_control/parks).
    primary_name = f"ck_{comp_stem}__{primary_path.parent.name}"      # ck_lc_parks__launch_control
    secondary_name = f"ck_{comp_stem}__{secondary_path.parent.name}"  # ck_lc_parks__parks

    # Region port: single source of truth for both surfaces. Derived from the
    # composition stem (offset +3 to dodge each surface's udp/osc ports) unless
    # set explicitly.
    region_port = comp.region_port if comp.region_port is not None else generate_5_digit_number(comp_stem) + 3
    # Reverse mode channel port (primary -> secondary). Same stem-derived base as
    # region_port but a different offset so the two channels can't collide.
    mode_port = generate_5_digit_number(comp_stem) + 4
    assert mode_port != region_port, "mode_port must differ from region_port"

    primary_root = read_root(primary_path.read_text(), source=primary_path.name)
    secondary_root = read_root(secondary_path.read_text(), source=secondary_path.name)
    validate_composition_modes(primary_root, secondary_root)

    # Combined layout: primary cells + secondary cells offset to the right.
    primary_ctrl = read_controller((primary_path.parent / primary_root.controller).read_text())
    secondary_ctrl = read_controller((secondary_path.parent / secondary_root.controller).read_text())
    primary_cells = allocate_global_layout(primary_ctrl)
    secondary_cells = allocate_global_layout(secondary_ctrl)
    combined_cells, dial_offset, button_offset = combine_layouts(primary_cells, secondary_cells)

    # 1. Compositor surface (the named lc_parks): primary mapping + combined
    #    layout + region listener. Output lands in the composition folder.
    # Force the compositor to show-hud-on='selection'. The primary mapping is
    # often 'controller-nav' (launch_control is), which SUPPRESSES the burst on
    # a plain selection AND sends HIDE. That HIDE races the parks-triggered
    # combined COMMIT (two independent selection polls in two processes), so the
    # values flash then vanish. Showing on selection removes the HIDE-on-select
    # entirely; device-nav (source='nav') still shows as before.
    # The primary forwards its mode to the secondary ONLY when it actually has a
    # shift mode-button to forward; mode_link is None otherwise (single-mode
    # primary), so the secondary just stays in its first mode.
    primary_drives_modes = primary_root.mode_button is not None and bool(_declared_mode_names(secondary_root))
    primary_mode_link = {'role': 'sender', 'port': mode_port} if primary_drives_modes else None
    secondary_mode_link = {'role': 'listener', 'port': mode_port} if primary_drives_modes else None

    _generate_surface(primary_path, primary_name, comp_dir, CompositionOverrides(
        region_config={'dial_offset': dial_offset, 'button_offset': button_offset,
                       'port': region_port},
        hud_cells=combined_cells,
        hud_trigger=HudTrigger.Selection,
        mode_link=primary_mode_link))

    # 2. Secondary forwarder: a normal surface whose HudClient is redirected at
    #    the compositor's region port instead of the HUD. Emitted into the
    #    composition folder under the namespaced name (NOT next to its own
    #    mapping), so it can't be confused with a standalone build.
    _generate_surface(secondary_path, secondary_name, comp_dir, CompositionOverrides(
        hud_target=('127.0.0.1', region_port),
        mode_link=secondary_mode_link))

    print(f"Composition {comp_stem}: {primary_name} (compositor) + {secondary_name} "
          f"(forwarder) share region port {region_port}.")


if __name__ == '__main__':
    script_file = Path(sys.argv[1])
    try:
        generate(script_file)
    except GenError as e:
        # Config problems are user errors, not bugs — print the readable
        # message and exit non-zero, without a Python traceback.
        print(f"\nCould not generate from {script_file}:\n{e}", file=sys.stderr)
        sys.exit(1)
    #     # exit(-1)
    #     # sys.exit(e.error_code)
