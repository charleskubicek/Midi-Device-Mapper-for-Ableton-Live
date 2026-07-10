"""JSON-lines stdio sidecar for the Electron mapping editor (ui/).

The editor spawns ``python -m ableton_control_surface_as_code.ui_api`` and sends
one request object per line: ``{"id", "method", "params"}``. Every request gets
exactly one response line: ``{"id", "ok": true, "result": ...}`` or
``{"id", "ok": false, "error": {"kind", "message"}}``.

Invariant: nothing the client sends may kill this process. NestedText parse
errors are pre-caught here because ``read_root``/``read_controller`` respond to
them with ``NestedTextError.terminate()``, which raises SystemExit.
"""
import contextlib
import io
import json
import sys
from pathlib import Path

import nestedtext as nt

from ableton_control_surface_as_code.gen_error import GenError, ErrorCode, ProblemAccumulator
from ableton_control_surface_as_code.model_v2 import read_root, read_controller, read_root_v2


class _ApiError(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def _parse_nt(text):
    try:
        return nt.loads(text)
    except nt.NestedTextError as e:
        raise _ApiError("parse", e.get_message() if hasattr(e, "get_message") else str(e))


def _problem(message, kind="semantic", code=None):
    return {"message": message, "kind": kind, "code": code}


def _load_controller(params):
    path = Path(params["path"])
    try:
        text = path.read_text()
    except OSError as e:
        raise _ApiError("io", f"Cannot read controller file {path}: {e}")
    _parse_nt(text)  # pre-flight: read_controller would terminate() on NT errors
    acc = ProblemAccumulator()
    controller = acc.capture(lambda: read_controller(text, source=str(path), acc=acc))
    if controller is None:
        raise _ApiError("config", "\n".join(acc.problems) or f"Could not parse {path}")
    groups = []
    for g in controller.control_groups:
        coords = g.midi_coords
        groups.append({
            "number": g.number,
            "type": g.type.value,
            "grid_row": g.grid_row,
            "grid_col": g.grid_col,
            "rows": g.rows,
            "columns": g.columns,
            "hud": g.hud,
            "control_count": len(coords),
            "midi_channel": coords[0].channel if coords else None,
            "midi_type": coords[0].type.value if coords else None,
            "midi_numbers": [c.number for c in coords],
        })
    return {
        "light_colors": controller.light_colors,
        "button_behaviour": controller.button_behaviour.value,
        "encoder_mode": controller.encoder_mode.value,
        "groups": groups,
        "problems": [_problem(p) for p in acc.problems],
    }


def _validate(params):
    mapping_text = params["mapping_text"]
    mapping_dir = Path(params["mapping_dir"])

    def problems(items):
        return {"valid": False, "problems": items}

    try:
        parsed = _parse_nt(mapping_text)
    except _ApiError as e:
        return problems([_problem(str(e), kind="parse")])

    # Mirrors build_validated_model (model_v2.py) but keeps the accumulator's
    # individual problems instead of one collapsed GenError, so the UI can
    # attach each problem to the mapping it belongs to.
    acc = ProblemAccumulator()
    try:
        root = read_root(mapping_text, acc=acc)
    except GenError as e:
        return problems([_problem(str(e), kind="config", code=_code_name(e))])

    controller_path = mapping_dir / root.controller
    try:
        controller_text = controller_path.read_text()
    except OSError as e:
        return problems([_problem(f"Cannot read controller file {controller_path}: {e}", kind="io")])
    try:
        _parse_nt(controller_text)
    except _ApiError as e:
        return problems([_problem(str(e), kind="parse")])

    try:
        controller = read_controller(controller_text, source=str(controller_path), acc=acc)
        read_root_v2(root, controller, mapping_dir, acc=acc)
    except GenError as e:
        acc.add(str(e))

    if acc.problems:
        return problems([_problem(p) for p in acc.problems])
    return {"valid": True, "problems": []}


def _code_name(gen_error):
    try:
        return ErrorCode(gen_error.error_code).name
    except ValueError:
        return None


def _field_aliases(model_cls):
    return [f.alias or name for name, f in model_cls.model_fields.items()]


def _schema_info(params):
    from ableton_control_surface_as_code.model_clip import CLIP_ACTIONS
    from ableton_control_surface_as_code.model_transport import TransportMappings
    from ableton_control_surface_as_code.model_track_nav import TrackNavMappings
    from ableton_control_surface_as_code.model_device_nav import DeviceNavMappings
    from ableton_control_surface_as_code.model_functions import RESERVED_BUILTIN_FUNCTIONS
    return {
        "clip_actions": [
            {"key": spec.key, "kind": spec.kind, "label": spec.hud_label,
             "audio_only": spec.audio_only}
            for spec in CLIP_ACTIONS.values()
        ],
        "transport_actions": _field_aliases(TransportMappings),
        "track_nav_actions": _field_aliases(TrackNavMappings),
        "device_nav_actions": _field_aliases(DeviceNavMappings),
        "builtin_functions": sorted(RESERVED_BUILTIN_FUNCTIONS),
    }


def _list_functions(params):
    """Names + non-self arity of the Functions class in <dir>/functions.py.
    Same AST-only inspection the generator uses (never imports the file).
    functions: None means the file doesn't exist (distinct from an empty class)."""
    import ast
    path = Path(params["dir"]) / "functions.py"
    if not path.exists():
        return {"functions": None}
    tree = ast.parse(path.read_text())
    functions = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Functions":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    functions.append({"name": item.name, "params": len(item.args.args) - 1})
    return {"functions": functions}


def _generate(params):
    from ableton_control_surface_as_code import gen
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        gen.generate(Path(params["mapping_path"]))
    return {"output": buffer.getvalue()}


_METHODS = {
    "ping": lambda params: "pong",
    "load_controller": _load_controller,
    "validate": _validate,
    "parse_nt": lambda params: _parse_nt(params["text"]),
    "schema_info": _schema_info,
    "list_functions": _list_functions,
    "generate": _generate,
}


def handle_request(request):
    rid = request.get("id")
    method = request.get("method")
    fn = _METHODS.get(method)
    if fn is None:
        return {"id": rid, "ok": False,
                "error": {"kind": "bad_request", "message": f"Unknown method: {method!r}"}}
    try:
        # The generator prints info tables (device layouts etc.) to stdout;
        # swallow them so the JSON-lines channel stays clean.
        with contextlib.redirect_stdout(io.StringIO()):
            result = fn(request.get("params") or {})
        return {"id": rid, "ok": True, "result": result}
    except _ApiError as e:
        return {"id": rid, "ok": False, "error": {"kind": e.kind, "message": str(e)}}
    except GenError as e:
        return {"id": rid, "ok": False,
                "error": {"kind": "config", "message": str(e), "code": _code_name(e)}}
    except (SystemExit, Exception) as e:  # noqa: BLE001 — the loop must never die
        return {"id": rid, "ok": False,
                "error": {"kind": "internal", "message": f"{type(e).__name__}: {e}"}}


def run(stdin, stdout):
    for line in stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            response = {"id": None, "ok": False,
                        "error": {"kind": "bad_request", "message": f"Invalid JSON: {e}"}}
        else:
            response = handle_request(request)
        stdout.write(json.dumps(response) + "\n")
        stdout.flush()


def main():
    run(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
