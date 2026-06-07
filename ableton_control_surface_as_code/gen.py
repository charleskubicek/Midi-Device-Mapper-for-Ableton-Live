import hashlib
import json
import sys
from pathlib import Path
import shutil
from string import Template
from collections import defaultdict
from typing import Tuple

from ableton_control_surface_as_code.gen_code import class_function_body_code_block, \
    class_function_code_block, get_python_code_error, device_templates, GeneratedCode, \
    functions_templates, mixer_templates, track_nav_templates, device_nav_templates, \
    transport_templates, dict_variable_decleration_block, GeneratedCodes, \
    parameter_pager_templates, clip_templates
from ableton_control_surface_as_code.model_v2 import read_controller, \
    read_root, ModeGroupWithMidi, read_root_v2, ModeData, AllMappingWithMidiTypes, HudMode, HudTrigger

tab = " " * 4


def tabs(n):
    return tab * n


def setup_template(mode_name, mode_button_midi=None):
    if mode_button_midi is not None:
        midi_type = 'MIDI_NOTE_TYPE' if mode_button_midi.type.is_note() else 'MIDI_CC_TYPE'
        btn_line = f"self.mode_button = ConfigurableButtonElement(True, {midi_type}, {mode_button_midi.ableton_channel()}, {mode_button_midi.number})"
    else:
        btn_line = "self.mode_button = ConfigurableButtonElement(True, MIDI_NOTE_TYPE, 8, 9)"
    return f"""
        self.current_mode = None
        self._first_mode = '{mode_name}'
        {btn_line}
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


def validate_exports(export_targets, mode_codes):
    for et in export_targets:
        if et not in mode_codes:
            raise ValueError(f"Export target {et} not found in mode codes")

    for export_target_mode, export_codes in export_targets.items():
        for cm_mode, code_mode in mode_codes.items():
            if export_target_mode == cm_mode:
                commmon = GeneratedCodes.common_midi_coords_in_control_defs(export_codes, code_mode)
                if len(commmon) > 0:
                    raise ValueError(f"export to {export_target_mode} from {cm_mode} has overlapping midi coords: {[(ys.info_string(), ys.source_info) for ys in commmon]}")

def generate_code_as_template_vars(modes: ModeGroupWithMidi, controller=None, hud_mode: HudMode = HudMode.On, hud_trigger: HudTrigger = HudTrigger.ControllerNav, feedback=None, hud_cells_override=None) -> dict:
    first_mode_name = modes.first_mode_name()

    # Global wire-index allocation: every physical control on the surface
    # gets a wire slot, regardless of which mode binds it. Modes overlay
    # static labels onto these slots at runtime.
    #
    # The lc_parks compositor passes `hud_cells_override` = the combined grid
    # (primary cells + offset secondary cells) so the LAYOUT it emits, and the
    # slots it builds, span both controllers. Primary mappings still resolve to
    # their original (unchanged) wire indices within that combined grid.
    from ableton_control_surface_as_code.hud_layout import (
        allocate_global_layout, collect_mode_labels,
    )
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
        creation.append(creation_template(first_mode_name))
        codes.remove_listeners.append(remove_listeners_template())
        mode_btn_midi = modes.mode_button.button if modes.mode_button else None
        codes.init.append(setup_template(first_mode_name, mode_button_midi=mode_btn_midi))

        for mode in modes.fsm():
            codes.init.append(state_dict_template(mode, f"self.mode_{mode.name}_add_listeners"))

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

    return {
        'code_setup': "\n".join(codes.init),
        'code_custom_parameter_mappings': dict_variable_decleration_block(codes.custom_parameter_mappings),
        'code_switch_parameter_mappings': dict_variable_decleration_block(codes.switch_parameter_mappings),
        'code_creation': class_function_body_code_block(creation + array_defs),
        'code_remove_listeners': "\n".join(codes.remove_listeners),
        'code_setup_listeners': "\n".join(codes.setup_listeners),
        'code_listener_fns': "\n".join(codes.listener_fns),
        'encoder_slot_count': encoder_slot_count,
        'hud_cells': repr(hud_cells_raw),
        'mode_hud_labels': repr(mode_hud_labels),
        'hud_client_class': hud_client_class,
        'hud_trigger': repr(hud_trigger.value),
        'feedback_sinks': feedback_sinks,
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

def build_mode_code(mode_mappings, name, controller=None, hud_cells=None) -> list[GeneratedCode]:
    res = []
    for mapping in mode_mappings:
        if mapping.type == 'device':
            res.extend(device_templates(mapping, name, controller=controller, hud_cells=hud_cells))
        else:
            res.extend(template_to_code[mapping.type](mapping, name))

    return res


def write_templates(template_path: Path, target: Path, vars: dict, functions_path: Path):
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
    from source_modules.hud_protocol import encode_layout
    layout_line = encode_layout(hud_cells_raw)
    print("HUD wire messages:")
    print(f"  {layout_line}")
    print()
    print("  HUD cells breakdown:")
    for gr, gc, kind, count, start in hud_cells_raw:
        mapped = f"slots {start}..{start + count - 1}" if start >= 0 else "unmapped"
        print(f"    grid({gr},{gc})  {kind:<8}  count={count}  {mapped}")


def print_ascii_layout(controller):
    from ableton_control_surface_as_code.core_model import EncoderType

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
    from ableton_control_surface_as_code.model_composition import is_composition_file
    if is_composition_file(input_path):
        generate_composition(input_path)
    else:
        target_dir = Path('out') if input_path == Path.cwd() else input_path.parent
        _generate_surface(input_path, input_path.stem, target_dir)


def _generate_surface(mapping_file_path, surface_name, target_dir,
                      hud_client_args='', region_setup='pass', hud_cells_override=None,
                      hud_trigger_override=None):
    """Build and write a single surface directory named `surface_name` under
    `target_dir`, from the mapping at `mapping_file_path`. Returns
    (controller, code_vars). Overrides let the compositor inject the combined
    layout + region wiring, and let the forwarder retarget its HUD client."""
    functions_path = mapping_file_path.parent / "functions.py"
    if not functions_path.exists():
        functions_path = None

    mappings = read_root(mapping_file_path.read_text())

    controller_path = mapping_file_path.parent / mappings.controller
    controller = read_controller(controller_path.read_text())
    mode_with_midi = read_root_v2(mappings, controller, mapping_file_path.parent)

    parameter_mappings_raw = None
    if mappings.parameter_mappings_file is not None:
        pm_path = (mapping_file_path.parent / mappings.parameter_mappings_file).resolve()
        if not pm_path.exists():
            raise ValueError(f"parameter_mappings_file not found: {pm_path}")
        parameter_mappings_raw = json.loads(pm_path.read_text())
        from ableton_control_surface_as_code.model_custom_devices import validate_custom_device_mappings
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
        'remote_on': mappings.remote_on,
        'parameter_mappings_raw': repr(parameter_mappings_raw),
        # Constructor args for the HUD client. Empty for a standalone surface
        # (defaults to the HUD on 127.0.0.1:5006). The parks forwarder overrides
        # this to target the lc_parks compositor's region port.
        'hud_client_args': hud_client_args,
        # Compositor region wiring (lc_parks only). 'pass' for normal surfaces.
        'region_setup': region_setup,
    }

    hud_trigger = hud_trigger_override if hud_trigger_override is not None else mappings.show_hud_on
    code_vars = generate_code_as_template_vars(mode_with_midi, controller=controller, hud_mode=mappings.hud, hud_trigger=hud_trigger, feedback=mappings.feedback, hud_cells_override=hud_cells_override)
    mode_vars = vars | code_vars
    write_templates(Path(f'templates'), target_dir, mode_vars, functions_path)

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


def _region_setup_code(dial_offset, button_offset, region_port, surface_name):
    """Render the compositor's region wiring for main_component.py. Lines after
    the first must carry their own 8-space indentation (the template substitutes
    `$region_setup` at that indent)."""
    indent = " " * 8
    lines = [
        f"self._region_state = RegionState(self._hud_client, dial_offset={dial_offset}, button_offset={button_offset}, on_commit=self._helpers.reemit_combined_burst)",
        f"self._remote.set_region_state(self._region_state)",
        f'self._region_listener = RegionListener(self.manager, self._region_state, port={region_port}, name="{surface_name}-region")',
    ]
    return ("\n" + indent).join(lines)


def generate_composition(comp_path):
    from ableton_control_surface_as_code.model_composition import read_composition
    from ableton_control_surface_as_code.hud_layout import allocate_global_layout, combine_layouts

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

    # Combined layout: primary cells + secondary cells offset to the right.
    primary_ctrl = read_controller((primary_path.parent / read_root(primary_path.read_text(), source=primary_path.name).controller).read_text())
    secondary_ctrl = read_controller((secondary_path.parent / read_root(secondary_path.read_text(), source=secondary_path.name).controller).read_text())
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
    from ableton_control_surface_as_code.model_v2 import HudTrigger
    region_setup = _region_setup_code(dial_offset, button_offset, region_port, primary_name)
    _generate_surface(primary_path, primary_name, comp_dir,
                      region_setup=region_setup, hud_cells_override=combined_cells,
                      hud_trigger_override=HudTrigger.Selection)

    # 2. Secondary forwarder: a normal surface whose HudClient is redirected at
    #    the compositor's region port instead of the HUD. Emitted into the
    #    composition folder under the namespaced name (NOT next to its own
    #    mapping), so it can't be confused with a standalone build.
    forwarder_args = f"host='127.0.0.1', port={region_port}"
    _generate_surface(secondary_path, secondary_name, comp_dir,
                      hud_client_args=forwarder_args)

    print(f"Composition {comp_stem}: {primary_name} (compositor) + {secondary_name} "
          f"(forwarder) share region port {region_port}.")


if __name__ == '__main__':
    # try:

    script_file = Path(sys.argv[1])
    generate(script_file)

    # script_file = Path(sys.argv[2])
    # generate(script_file)

    # # except GenError as e:
    # #     print(f"Problem Generating: {e}")
    # #     exit(-1)
    # except Exception as e:
    #     raise e
    #     # print(f"Error: {e}")
    #     # exit(-1)
    #     # sys.exit(e.error_code)
