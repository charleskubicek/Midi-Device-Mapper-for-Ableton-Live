from pathlib import Path

import nested_text as nt
from ableton_control_suface_as_code.model_v1 import MappingsV1

try:
    xl_nt = 'tests_e2e/ck_test_novation_xl.nt'
    content = Path(xl_nt).read_text()
    data = nt.loads(content, top='dict')

    def normalize_key(key, parent_keys):
        return '_'.join(key.lower().split())

    obj = nt.load(xl_nt, normalize_key=normalize_key)
    model = MappingsV1.model_validate(obj)

    print(model)

except nt.NestedTextError as e:

    e.terminate()
