import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from string import Template

import ast

from ableton_control_suface_as_code.code import encoder_template, class_function_body_code_block, \
    class_function_code_block, is_valid_python
from ableton_control_suface_as_code.model import Controller, DeviceWithMidi, Mappings, build_mode_model


def gen(template_path: Path, target: Path, devices_with_midi: [DeviceWithMidi], vars: dict):
    root_dir = Path(target, vars['surface_name'])
    root_dir.mkdir(exist_ok=True)

    for devices_with_midi in devices_with_midi:
        if devices_with_midi.device.type == 'device':
            encoder_code = encoder_template(devices_with_midi)
            vars['encoder_code_creation'] = class_function_body_code_block(encoder_code.creation)
            vars['encoder_code_remove_listeners'] = class_function_body_code_block(encoder_code.remove_listeners)
            vars['encoder_code_setup_listeners'] = class_function_body_code_block(encoder_code.setup_listeners)
            vars['encoder_code_listener_fns'] = class_function_code_block(encoder_code.listener_fns)
        elif devices_with_midi.device.type == 'mixer':
            pass

    template_file(root_dir, template_path / 'surface_name', vars, "__init__.py", "__init__.py")
    template_file(root_dir, template_path / 'surface_name', vars, f'modules/class_name_snake.py',f"modules/{vars['class_name_snake']}.py", verify_python=True)
    template_file(root_dir, template_path / 'surface_name', vars, 'surface_name.py', f"{vars['surface_name']}.py")
    template_file(root_dir, template_path, vars, 'deploy.sh', 'deploy.sh')
    template_file(root_dir, template_path, vars, 'tail_logs.sh', 'tail_logs.sh')
    template_file(root_dir, template_path, vars, 'update.py', 'update.py')


def template_file(root_dir, template_path, vars: dict, source_file_name, target_file_name, verify_python=False):
    target_file = root_dir / target_file_name
    target_file.parent.mkdir(exist_ok=True)
    new_text = Template((template_path / source_file_name).read_text()).substitute(
        vars)

    if verify_python and not is_valid_python(new_text):
        print(f"Code failed validation for file {target_file}")
        sys.exit(1)

    target_file.write_text(new_text)

def generate_5_digit_number(input_string):
    hex_digest = hashlib.sha256(input_string.encode()).hexdigest()
    five_digits = int(hex_digest[:5], 16)
    return 10000 + (five_digits % 55535)

if __name__ == '__main__':
    mapping_file_name = "tests_e2e/ck_test_novation_xl.json"
    mapping_file_path = Path(mapping_file_name)

    mapping = Mappings.model_validate_json(mapping_file_path.read_text())

    controller = Controller.model_validate_json((mapping_file_path.parent / mapping.controller).read_text())
    surface_name = mapping_file_path.stem


    vars = {
        'surface_name': surface_name,
        'udp_port': generate_5_digit_number(surface_name)+1,
        'class_name_snake': 'control_mappings',
        'class_name_camel': 'ControlMappings'
    }

    target_dir = Path('out')
    devices_with_midi = build_mode_model(mapping.mappings, controller)

    gen(Path(f'templates'), target_dir, devices_with_midi, vars)
