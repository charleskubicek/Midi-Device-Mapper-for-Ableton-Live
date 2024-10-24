import hashlib
import sys
from pathlib import Path
import shutil
from string import Template

from ableton_control_surface_as_code.gen_code import class_function_body_code_block, \
    class_function_code_block, get_python_code_error, device_templates, GeneratedCode, \
    functions_templates, mixer_templates, track_nav_templates, device_nav_templates, \
    transport_templates
from ableton_control_surface_as_code.model_v2 import read_controller, \
    read_root, ModeGroupWithMidi, read_root_v2, ModeData

template_to_code = {
    'device': device_templates,
    'mixer': mixer_templates,
    'track-nav': track_nav_templates,
    'device-nav': device_nav_templates,
    'functions': functions_templates,
    'transport': transport_templates
}

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

def state_dict_template(mode:ModeData, listners_function):
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

def generate_code_as_template_vars(modes: ModeGroupWithMidi) -> dict:

    first_mode_name = "mode_1"

    mode_codes = {name: build_mode_code(maps, name)
                  for name, maps in modes.mappings.items()}

    array_defs = []
    codes = GeneratedCode()

    creation = [creation.variable_initialisation()
                for creation in GeneratedCode.merge_all(list(mode_codes.values())).control_defs]

    creation.append(f"self.mode_mode_1_add_listeners()")

    for name, code_model in mode_codes.items():
        codes.remove_listeners.append(class_function_body_code_block(code_model.remove_listeners))
        codes.setup_listeners.append(add_listeners_template(name))
        codes.setup_listeners.append(class_function_body_code_block(code_model.setup_listeners))
        codes.listener_fns.append(class_function_code_block(code_model.listener_fns))

        for (name, values) in code_model.array_defs:
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
        'code_creation': class_function_body_code_block(creation+array_defs),
        'code_remove_listeners': "\n".join(codes.remove_listeners),
        'code_setup_listeners': "\n".join(codes.setup_listeners),
        'code_listener_fns': "\n".join(codes.listener_fns)
    }


def build_mode_code(mode_mappings, name):
    codes = [template_to_code[mapping.type](mapping, name)
             for mapping in mode_mappings]

    return GeneratedCode.merge_all(codes)


def write_templates(template_path: Path, target: Path, vars: dict, functions_path: Path):
    root_dir = Path(target, vars['surface_name'])
    root_dir.mkdir(exist_ok=True)

    template_file(root_dir, template_path / 'surface_name', vars, "__init__.py", "__init__.py")
    template_file(root_dir, template_path / 'surface_name', vars, f'modules/main_component.py',
                  f"modules/main_component.py", verify_python=True)
    template_file(root_dir, template_path / 'surface_name', vars, "modules/helpers.py", "modules/helpers.py")
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
        shutil.copy(file, target_dir / vars['surface_name'] / "modules" /  file.name)


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

