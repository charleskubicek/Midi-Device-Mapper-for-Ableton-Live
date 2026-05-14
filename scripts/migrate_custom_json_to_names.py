"""One-shot migration: strip the legacy `number` field from
`data/custom_device_mappings.json`.

After the index→name resolution rewrite, `number` is no longer authoritative
(and is rejected by the schema with `extra='forbid'`). Every authored entry
in this codebase already carries a `name`, so this migration is purely a
field strip.

Run once:
    poetry run python scripts/migrate_custom_json_to_names.py [--in PATH] [--out PATH]
"""
import argparse
import json
import sys
from pathlib import Path


def strip_numbers(node):
    if isinstance(node, dict):
        node.pop('number', None)
        for v in node.values():
            strip_numbers(v)
    elif isinstance(node, list):
        for v in node:
            strip_numbers(v)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--in', dest='in_path',
                        default='data/custom_device_mappings.json')
    parser.add_argument('--out', dest='out_path', default=None,
                        help='default: overwrite the input file')
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path) if args.out_path else in_path

    raw = json.loads(in_path.read_text())
    strip_numbers(raw)

    # Round-trip through the validator to catch any entries that lacked a name.
    from ableton_control_surface_as_code.model_custom_devices import validate_custom_device_mappings
    try:
        validate_custom_device_mappings(raw)
    except Exception as ex:
        print(f"Migration produced an invalid file: {ex}", file=sys.stderr)
        sys.exit(2)

    out_path.write_text(json.dumps(raw, indent=2) + '\n')
    print(f"Migrated {in_path} -> {out_path}")


if __name__ == '__main__':
    main()
