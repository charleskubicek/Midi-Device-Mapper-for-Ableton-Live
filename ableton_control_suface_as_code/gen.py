import hashlib
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from string import Template

import ast
from typing import Union

from ableton_control_suface_as_code.code import device_templates, class_function_body_code_block, \
    class_function_code_block, is_valid_python, mixer_templates, GeneratedCode
from ableton_control_suface_as_code.model_v1 import ControllerV1, MappingsV1, build_mode_model_v1
from ableton_control_suface_as_code.core_model import DeviceWithMidi, MixerWithMidi
from ableton_control_suface_as_code.model_v2 import build_mode_model_v2, MappingsV2, ControllerV2, read_controller, \
    read_mapping

template_to_code = {
    'device': device_templates,
    'mixer': mixer_templates
}

# @dataclass
# class TemplateVars:
#     surface_name: str

def generate_code_in_template_vars(devices_with_midi: [Union[DeviceWithMidi, MixerWithMidi]]) -> dict:
    code = GeneratedCode([], [], [], [], [])
    for device_with_midi in devices_with_midi:
        code_templates = template_to_code[device_with_midi.type]
        code = code.merge(code_templates(device_with_midi))

    return {
        'code_setup': class_function_body_code_block(code.setup),
        'code_creation': class_function_body_code_block(code.creation),
        'code_remove_listeners': class_function_body_code_block(code.remove_listeners),
        'code_setup_listeners': class_function_body_code_block(code.setup_listeners),
        'code_listener_fns': class_function_code_block(code.listener_fns)
    }

def write_templates(template_path: Path, target: Path, vars: dict):
    root_dir = Path(target, vars['surface_name'])
    root_dir.mkdir(exist_ok=True)

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
        # sys.exit(1)

    target_file.write_text(new_text)

def generate_5_digit_number(input_string):
    hex_digest = hashlib.sha256(input_string.encode()).hexdigest()
    five_digits = int(hex_digest[:5], 16)
    return 10000 + (five_digits % 55535)

if __name__ == '__main__':
    mapping_file_name = "tests_e2e/ck_test_novation_xl.json"
    mapping_file_path = Path(mapping_file_name)

    controller = read_controller(Path('tests_e2e/controller_xl.nt').read_text())
    mapping = read_mapping(Path('tests_e2e/ck_test_novation_xl.nt').read_text())
    # mapping = MappingsV2.model_validate_json(mapping_file_path.read_text())
    #
    # controller = ControllerV2.model_validate_json((mapping_file_path.parent / mapping.controller).read_text())
    surface_name = mapping_file_path.stem
    #
    vars = {
        'surface_name': surface_name,
        'udp_port': generate_5_digit_number(surface_name)+1,
        'class_name_snake': 'control_mappings',
        'class_name_camel': 'ControlMappings'
    }

    target_dir = Path('out')
    # devices_with_midi = build_mode_model_v1(mapping.mappings, controller)
    devices_with_midi = build_mode_model_v2(mapping.mappings, controller)

    vars = vars | generate_code_in_template_vars(devices_with_midi)
    write_templates(Path(f'templates'), target_dir, vars)

    print("Finished generating code.")
