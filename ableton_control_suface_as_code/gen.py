import hashlib
from pathlib import Path
from string import Template

from ableton_control_suface_as_code.gen_code import class_function_body_code_block, \
    class_function_code_block, is_valid_python, device_mode_templates, GeneratedModeCode, \
    functions_mode_templates, mixer_mode_templates, track_nav_mode_templates, device_nav_mode_templates, \
    transport_mode_templates
from ableton_control_suface_as_code.core_model import MidiType
from ableton_control_suface_as_code.gen_error import GenError
from ableton_control_suface_as_code.model_controller import ControllerV2
from ableton_control_suface_as_code.model_v2 import read_controller, \
    read_root, ModeGroupWithMidi, read_root_v2, ModeData

mode_template_to_code = {
    'device': device_mode_templates,
    'mixer': mixer_mode_templates,
    'track-nav': track_nav_mode_templates,
    'device-nav': device_nav_mode_templates,
    'functions': functions_mode_templates,
    'transport': transport_mode_templates
}

tab = " " * 4


def tabs(n):
    return tab * n


def mode_setup_template(mode_name):
    return f"""
        self.current_mode = None
        self._first_mode = '{mode_name}'
        self.mode_button = ConfigurableButtonElement(True, MIDI_NOTE_TYPE, 8, 9)    
    """

def mode_creation_template(mode_name):
    return f"""
        self.current_mode = self._modes['{mode_name}']
        self.goto_mode(self._first_mode)
        """

def mode_add_listeners_template(mode_name):
    return f"""
    def mode_{mode_name}_add_listeners(self):
        self.log_message(f'Adding listeners for mode {mode_name}')
    """

def mode_remove_listeners_template():
    return f"""
        if not modes_only:
            self.mode_button.remove_value_listener(self.mode_button_listener)
    """

def mode_state_dict_template(mode:ModeData, listners_function):
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

def generate_mode_code_in_template_vars(modes: ModeGroupWithMidi) -> dict:

    first_mode_name = "mode_1"
    mode_codes = {}

    for name, mode_mappings in modes.mappings.items():
        mode_code = GeneratedModeCode()
        for mapping in mode_mappings:
            code_templates = mode_template_to_code[mapping.type](mapping, name)
            mode_code = mode_code.merge(code_templates)

        mode_codes[name] = mode_code

    array_defs = []
    codes = GeneratedModeCode()

    creation = [creation.variable_initialisation()
                for creation in GeneratedModeCode.merge_all(list(mode_codes.values())).control_defs]

    creation.append(f"self.mode_mode_1_add_listeners()")


    for name, mode_code in mode_codes.items():
        codes.remove_listeners.append(class_function_body_code_block(mode_code.remove_listeners))

        codes.setup_listeners.append(mode_add_listeners_template(name))
        codes.setup_listeners.append(class_function_body_code_block(mode_code.setup_listeners))
        codes.listener_fns.append(class_function_code_block(mode_code.listener_fns))

        for (name, values) in mode_code.array_defs:
            array_defs.append(array_def_template(name, values))

    if modes.has_modes():
        creation.append(mode_creation_template(first_mode_name))
        codes.remove_listeners.append(mode_remove_listeners_template())
        codes.init.append(mode_setup_template(first_mode_name))

        for mode in modes.fsm():
            codes.init.append(mode_state_dict_template(mode, f"self.mode_{mode.name}_add_listeners"))

        codes.init.append(f"{tabs(2)}self.mode_button.add_value_listener(self.mode_button_listener)\n")

    return {
        'code_setup': "\n".join(codes.init),
        'code_creation': class_function_body_code_block(creation+array_defs),
        'code_remove_listeners': "\n".join(codes.remove_listeners),
        'code_setup_listeners': "\n".join(codes.setup_listeners),
        'code_listener_fns': "\n".join(codes.listener_fns)
    }



def write_templates(template_path: Path, target: Path, vars: dict, functions_path: Path):
    root_dir = Path(target, vars['surface_name'])
    root_dir.mkdir(exist_ok=True)

    template_file(root_dir, template_path / 'surface_name', vars, "__init__.py", "__init__.py")
    template_file(root_dir, template_path / 'surface_name', vars, f'modules/class_name_snake.py',
                  f"modules/{vars['class_name_snake']}.py", verify_python=True)
    template_file(root_dir, template_path / 'surface_name', vars, 'surface_name.py', f"{vars['surface_name']}.py")
    template_file(root_dir, template_path, vars, 'deploy.sh', 'deploy.sh')
    template_file(root_dir, template_path, vars, 'tail_logs.sh', 'tail_logs.sh')
    template_file(root_dir, template_path, vars, 'update.py', 'update.py')

    if functions_path is not None:
        functions_target = target / vars['surface_name'] / "modules" / "functions.py"
        functions_target.parent.mkdir(exist_ok=True)
        functions_target.touch()
        functions_target.write_text(functions_path.read_text())


def template_file(root_dir, template_path, vars: dict, source_file_name, target_file_name, verify_python=False):
    target_file = root_dir / target_file_name
    target_file.parent.mkdir(exist_ok=True)
    new_text = Template((template_path / source_file_name).read_text()).substitute(
        vars)

    if verify_python and not is_valid_python(new_text):
        print(f"Code failed validation for file {target_file}")
        # sys.exit(1)

    target_file.write_text(new_text)


def generate_5_digit_number(input_string):
    hex_digest = hashlib.sha256(input_string.encode()).hexdigest()
    five_digits = int(hex_digest[:5], 16)
    return 10000 + (five_digits % 55535)


def print_model(model: ControllerV2):
    from prettytable import PrettyTable

    def padded(f: MidiType):
        if f.is_note():
            return f" {f.value} "
        else:
            return f"  {f.value}  "

    for row in model.control_groups:
        print(f"Row {row.number}")
        table = PrettyTable(header=False)
        table.add_row(['Col '] + [i for i, _ in enumerate(row.midi_coords)])
        table.add_row(['Num '] + [col.number for col in row.midi_coords])
        table.add_row(['Type'] + [padded(col.type) for col in row.midi_coords])
        table.add_row(['Chan'] + [col.channel for col in row.midi_coords])

        print(table)




def generate_modes(mapping_file_path):
    functions_path = root_dir / "functions.py"

    if not functions_path.exists():
        functions_path = None

    mode_mappings = read_root(mapping_file_path.read_text())
    surface_name = mapping_file_path.stem

    vars = {
        'surface_name': surface_name,
        'udp_port': generate_5_digit_number(surface_name) + 1,
        'class_name_snake': 'control_mappings',
        'class_name_camel': 'ControlMappings'
    }

    target_dir = Path('out')

    controller_path = mapping_file_path.parent / mode_mappings.controller
    controller = read_controller(controller_path.read_text())
    print_model(controller)
    mode_with_midi = read_root_v2(mode_mappings, controller)

    code_vars = generate_mode_code_in_template_vars(mode_with_midi)
    mode_vars = vars | code_vars
    write_templates(Path(f'templates'), target_dir, mode_vars, functions_path)

    print("Finished generating code.")


if __name__ == '__main__':
    try:
        root_dir = Path("tests_e2e")
        # generate_modes(root_dir / "ck_test_novation_xl.nt")
        # generate_modes(root_dir / "ck_test_novation_lc.nt")
        generate_modes(root_dir / "ck_test_novation_lc_modes_test.nt")
    # except GenError as e:
    #     print(f"Problem Generating: {e}")
    #     exit(-1)
    except Exception as e:
        raise e
        # print(f"Error: {e}")
        # exit(-1)
        # sys.exit(e.error_code)
