import hashlib
import sys
from pathlib import Path
import shutil
from string import Template
from collections import defaultdict
from typing import Tuple

from ableton_control_surface_as_code.gen_code import class_function_body_code_block, \
    class_function_code_block, get_python_code_error, device_templates, GeneratedCode, \
    functions_templates, mixer_templates, track_nav_templates, device_nav_templates, \
    transport_templates, dict_variable_decleration_block, GeneratedCodes, code_for_parameter_paging, \
    device_class_names_to_friendly_names
from ableton_control_surface_as_code.model_v2 import read_controller, \
    read_root, ModeGroupWithMidi, read_root_v2, ModeData, AllMappingWithMidiTypes

tab = " " * 4


def tabs(n):
    return tab * n


def setup_template(mode_name):
    return f"""
        self.current_mode = None
        self._first_mode = '{mode_name}'
        self.mode_button = ConfigurableButtonElement(True, MIDI_NOTE_TYPE, 8, 9)    
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

def generate_code_as_template_vars(modes: ModeGroupWithMidi) -> dict:
    first_mode_name = modes.first_mode_name()

    mode_codes = create_code_model(modes)

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

        for (name, values) in merge.array_defs:
            array_defs.append(array_def_template(name, values))

    if modes.has_modes():
        creation.append(creation_template(first_mode_name))
        codes.remove_listeners.append(remove_listeners_template())
        codes.init.append(setup_template(first_mode_name))

        for mode in modes.fsm():
            codes.init.append(state_dict_template(mode, f"self.mode_{mode.name}_add_listeners"))

        codes.init.append(f"{tabs(2)}self.mode_button.add_value_listener(self.mode_button_listener)\n")

    return {
        'code_setup': "\n".join(codes.init),
        'code_custom_parameter_mappings': dict_variable_decleration_block(codes.custom_parameter_mappings),
        'code_creation': class_function_body_code_block(creation + array_defs),
        'code_remove_listeners': "\n".join(codes.remove_listeners),
        'code_setup_listeners': "\n".join(codes.setup_listeners),
        'code_listener_fns': "\n".join(codes.listener_fns),
        'device_friendly_names_to_class_names': str(device_class_names_to_friendly_names)
    }


def create_code_model(modes):
    exports = find_device_parameter_paging_mode_exports(modes.mappings)

    mode_codes = {mode_name: build_mode_code(maps, mode_name)
                  for mode_name, maps in modes.mappings}

    validate_exports(exports, mode_codes)

    for export_mode, export_code in exports.items():
        mode_codes[export_mode].extend(export_code)

    return mode_codes


template_to_code = {
    'device': device_templates,
    'mixer': mixer_templates,
    'track-nav': track_nav_templates,
    'device-nav': device_nav_templates,
    'functions': functions_templates,
    'transport': transport_templates
}

def find_device_parameter_paging_mode_exports(mode_mappings:list[Tuple[str, AllMappingWithMidiTypes]]):
    '''
    Given a list of mode mappings, find the device parameter paging mappings that export to another mode,
    generate the GenerateCode for the parameter paging and return a dictionary of the mode to the generated code,
    or an empty dictionary if no exports are found.

    :param mode_mappings:
    :return:
    '''
    for mode, mode_mapping in mode_mappings:
        for mapping in mode_mapping:
            if mapping.type == 'device' and mapping.has_paging_export:
                #TODO: only parameter_page_nav can export to another mode

                export_target = mapping.parameter_page_nav.export_to_mode
                gen_code = code_for_parameter_paging(mapping.parameter_page_nav, export_target)

                return {export_target: gen_code}

    return {}

def build_mode_code(mode_mappings, name) -> list[GeneratedCode]:
    res = []
    for mapping in mode_mappings:
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


def generate(mapping_file_path):
    functions_path = mapping_file_path.parent / "functions.py"

    if not functions_path.exists():
        functions_path = None

    mappings = read_root(mapping_file_path.read_text())
    surface_name = mapping_file_path.stem

    if mapping_file_path == Path.cwd():
        target_dir = Path('out')
    else:
        target_dir = mapping_file_path.parent

    controller_path = mapping_file_path.parent / mappings.controller
    controller = read_controller(controller_path.read_text())
    mode_with_midi = read_root_v2(mappings, controller, mapping_file_path.parent)

    vars = {
        'surface_name': surface_name,
        'udp_port': generate_5_digit_number(surface_name) + 1,
        'class_name_snake': 'control_mappings',
        'class_name_camel': 'ControlMappings',
        'ableton_dir': validate_path(mappings.ableton_dir)
    }

    code_vars = generate_code_as_template_vars(mode_with_midi)
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

    print("Finished generating code.")


if __name__ == '__main__':
    # try:

    script_file = Path(sys.argv[1])
    generate(script_file)

    # # except GenError as e:
    # #     print(f"Problem Generating: {e}")
    # #     exit(-1)
    # except Exception as e:
    #     raise e
    #     # print(f"Error: {e}")
    #     # exit(-1)
    #     # sys.exit(e.error_code)
