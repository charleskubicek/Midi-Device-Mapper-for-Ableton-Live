"""
Build data/blue_hand.json from data/blue_hand.txt and the Ableton parameter output files.

Usage:
    poetry run python scripts/build_blue_hand_json.py <path_to_output_dir>

Where <path_to_output_dir> is the directory containing per-device JSON files
(e.g. /Users/ck/current/live-shortcuts/AbletonShortcuts/parameter_data_gathereer/output).

Each device JSON has a `device_params` array with `name` (str) and `index` (int, 0-based).
The `index` field IS the parameterNumber used at runtime.
"""

import difflib
import json
import re
import sys
from pathlib import Path

# Maps blue_hand.txt display names → (className, output_json_filename)
# Devices with no Live 12 equivalent are omitted (legacy: Flanger, Frequency Shifter,
# Ping Pong Delay, Simple Delay).
DEVICE_MAP = {
    "Amp": ("Amp", "Amp.json"),
    "Auto Filter": ("AutoFilter2", "AutoFilter2.json"),
    "Auto Pan": ("AutoPan2", "AutoPan2.json"),
    "Beat Repeat": ("BeatRepeat", "BeatRepeat.json"),
    "Cabinet": ("Cabinet", "Cabinet.json"),
    "Chorus": ("Chorus2", "Chorus2.json"),
    "Compressor": ("Compressor2", "Compressor2.json"),
    "Corpus": ("Corpus", "Corpus.json"),
    "Dynamic Tube": ("Tube", "Tube.json"),
    "EQ Eight": ("Eq8", "Eq8.json"),
    "EQ Three": ("FilterEQ3", "FilterEQ3.json"),
    "Erosion": ("Erosion", "Erosion.json"),
    "External Audio Effect": ("ProxyAudioEffectDevice", "ProxyAudioEffectDevice.json"),
    "Filter Delay": ("FilterDelay", "FilterDelay.json"),
    "Gate": ("Gate", "Gate.json"),
    "Glue Compressor": ("GlueCompressor", "GlueCompressor.json"),
    "Grain Delay": ("GrainDelay", "GrainDelay.json"),
    "Limiter": ("Limiter", "Limiter.json"),
    "Looper": ("Looper", "Looper.json"),
    "Multiband Dynamics": ("MultibandDynamics", "MultibandDynamics.json"),
    "Overdrive": ("Overdrive", "Overdrive.json"),
    "Phaser": ("PhaserNew", "PhaserNew.json"),
    "Redux": ("Redux2", "Redux2.json"),
    "Resonators": ("Resonator", "Resonator.json"),
    "Reverb": ("Reverb", "Reverb.json"),
    "Saturator": ("Saturator", "Saturator.json"),
    "Utility": ("StereoGain", "StereoGain.json"),
    "Vinyl Distortion": ("Vinyl", "Vinyl.json"),
    "Vocoder": ("Vocoder", "Vocoder.json"),
}

# Manual overrides for cases where fuzzy matching fails due to renamed params.
# Format: {display_name: {position: exact_live12_param_name}}
MANUAL_OVERRIDES = {
    "Vocoder": {4: "Mono/Stereo"},  # blue_hand "Stereo Mode" → Live 12 "Mono/Stereo"
}


def parse_blue_hand(text: str) -> dict[str, dict[int, str]]:
    """Parse blue_hand.txt into {display_name: {position_1_to_8: param_label}}."""
    result = {}
    current_device = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Section header: "DeviceName_"
        if line.endswith("_") and not line[0].isdigit():
            current_device = line[:-1].strip()
            result[current_device] = {}
            continue
        if current_device is None:
            continue
        # Parameter line: "N: Name" or "N-M: -" (skip dashes)
        m = re.match(r'^(\d+):\s*(.+)$', line)
        if not m:
            continue
        pos_str, label = m.group(1), m.group(2).strip()
        if label == '-' or label.startswith('-'):
            continue
        pos = int(pos_str)
        if 1 <= pos <= 8:
            result[current_device][pos] = label
    return result


def fuzzy_match(label: str, params: list) -> dict:
    """Return the best-matching param dict from params for label, or None."""
    names = [p["name"] for p in params]
    names_lower = [n.lower() for n in names]
    label_lower = label.lower()

    # Exact match first (case-insensitive)
    if label_lower in names_lower:
        idx = names_lower.index(label_lower)
        return params[idx]

    # Fuzzy match
    matches = difflib.get_close_matches(label_lower, names_lower, n=1, cutoff=0.6)
    if matches:
        idx = names_lower.index(matches[0])
        return params[idx]

    return None


def load_fixed_slots(out_path: Path) -> dict:
    """Return {class_name: {slot_name: entry}} for all slots marked fixed:true."""
    if not out_path.exists():
        return {}
    fixed = {}
    data = json.loads(out_path.read_text())
    for device in data.get("families", [{}])[0].get("devices", []):
        for slot_name, entry in device.get("slots", {}).items():
            if entry.get("fixed"):
                fixed.setdefault(device["className"], {})[slot_name] = entry
    return fixed


def build(output_dir: Path) -> dict:
    blue_hand_txt = Path(__file__).parent.parent / "data" / "blue_hand.txt"
    out_path = Path(__file__).parent.parent / "data" / "blue_hand.json"
    parsed = parse_blue_hand(blue_hand_txt.read_text())
    fixed_slots = load_fixed_slots(out_path)

    devices_out = []
    skipped_devices = []

    for display_name, positions in parsed.items():
        if display_name not in DEVICE_MAP:
            print(f"  SKIP (no Live 12 mapping): {display_name}")
            skipped_devices.append(display_name)
            continue

        class_name, json_file = DEVICE_MAP[display_name]
        json_path = output_dir / json_file
        if not json_path.exists():
            print(f"  SKIP (file not found): {json_path}")
            skipped_devices.append(display_name)
            continue

        text = json_path.read_text().lstrip(",")
        raw = json.loads(text)
        params = raw["device_params"]

        overrides = MANUAL_OVERRIDES.get(display_name, {})
        fixed = fixed_slots.get(class_name, {})
        slots = {}
        for pos, label in sorted(positions.items()):
            slot_name = f"slot{pos}"
            if slot_name in fixed:
                print(f"  FIXED {display_name} {slot_name}: keeping '{fixed[slot_name]['parameterName']}'")
                slots[slot_name] = fixed[slot_name]
                continue
            is_fuzzy = False
            if pos in overrides:
                override_name = overrides[pos]
                matched = next((p for p in params if p["name"] == override_name), None)
                if matched is None:
                    print(f"  WARN {display_name} slot{pos}: override '{override_name}' not found in params")
                    continue
                print(f"  OVERRIDE {display_name} slot{pos}: '{label}' → '{matched['name']}' (idx {matched['index']})")
            else:
                matched = fuzzy_match(label, params)
                if matched is None:
                    print(f"  WARN {display_name} slot{pos} '{label}': no match found")
                    continue
                if matched["name"].lower() != label.lower():
                    is_fuzzy = True
                    print(f"  FUZZY {display_name} slot{pos}: '{label}' → '{matched['name']}' (idx {matched['index']})")
            entry = {"parameterName": matched["name"], "parameterNumber": matched["index"]}
            if is_fuzzy:
                entry["fuzzy"] = True
            slots[slot_name] = entry

        if slots:
            devices_out.append({
                "className": class_name,
                "deviceName": display_name,
                "slots": slots,
            })

    print(f"\nBuilt {len(devices_out)} devices. Skipped: {skipped_devices}")

    return {
        "families": [{
            "name": "Blue Hand",
            "devices": devices_out,
        }]
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    if not output_dir.is_dir():
        print(f"Error: {output_dir} is not a directory")
        sys.exit(1)

    result = build(output_dir)

    out_path = Path(__file__).parent.parent / "data" / "blue_hand.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Written to {out_path}")
