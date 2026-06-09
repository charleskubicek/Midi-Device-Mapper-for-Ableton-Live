#!/usr/bin/env python3
"""Architectural quality snapshot.

Run via ./build.sh (after the test suite). Computes drift-indicator metrics over
the generator package and the runtime modules, appends a summary line to
.quality/history.jsonl, writes full per-run detail to .quality/runs/, and
renders .quality/dashboard.md comparing this run against the previous one.

Metrics (all trend-tracked; thresholds are flags, not failures):
  - long_param_functions   functions with > 4 parameters (self/cls excluded)
  - god_classes            classes with >= 15 methods or >= 300 lines
  - wide_tuples            Tuple[...] annotations / returned tuple literals with > 2 elements
  - cc_*                   cyclomatic complexity (max / mean / count over 10)
  - long_functions         functions longer than 60 lines
  - duplicate_function_groups  structurally identical function bodies (normalized AST)
  - duplicate_files        byte-equivalent tracked .py files (whitespace-normalized)
  - deferred_imports       imports inside function bodies (cycle pressure)
  - unreferenced_defs      module-level defs with no textual reference anywhere else
  - config_drift_issues    mapping-type registries out of sync (builders/templates/union)
  - config_vocabulary      size of the mapping-file root vocabulary + mapping types
  - concern_spread         how many modules mention each cross-cutting concern (hud/wire/region/osc)
"""
import ast
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUALITY_DIR = ROOT / ".quality"
RUNS_DIR = QUALITY_DIR / "runs"
HISTORY = QUALITY_DIR / "history.jsonl"
DASHBOARD = QUALITY_DIR / "dashboard.md"

# Production code under review. templates/ is excluded (string.Template $vars are
# not parseable Python); vendored pythonosc is excluded.
CORE_DIRS = ["ableton_control_surface_as_code", "source_modules"]
EXCLUDE_DIR_NAMES = {"pythonosc", "__pycache__"}

PARAM_THRESHOLD = 4
GOD_METHODS = 15
GOD_LOC = 300
TUPLE_ARITY = 2          # tuples wider than this should be dataclasses
CC_THRESHOLD = 10
FN_LENGTH_THRESHOLD = 60
MODULE_LOC_THRESHOLD = 400
DUP_MIN_NODES = 25       # minimum AST size for duplicate-function comparison
CONCERNS = ["hud", "wire", "region", "osc"]

# Metrics where an increase means drift (drives the cleanup verdict).
BAD_IF_UP = [
    "long_param_functions", "max_params", "god_classes", "wide_tuples",
    "cc_max", "cc_functions_over_threshold", "long_functions",
    "duplicate_function_groups", "duplicate_files", "deferred_imports",
    "unreferenced_defs", "config_drift_issues", "modules_over_loc_threshold",
]


def _core_files():
    files = []
    for d in CORE_DIRS:
        for p in sorted((ROOT / d).rglob("*.py")):
            if EXCLUDE_DIR_NAMES & set(p.parts):
                continue
            files.append(p)
    return files


def _rel(p):
    return str(p.relative_to(ROOT))


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return ""


def _tracked_py_files():
    out = _git("ls-files", "*.py")
    files = []
    for line in out.splitlines():
        if "/modules/" in line:  # generated copies of source_modules inside surfaces
            continue
        if EXCLUDE_DIR_NAMES & set(Path(line).parts):
            continue
        p = ROOT / line
        if p.exists():
            files.append(p)
    return files


# ---- AST helpers -------------------------------------------------------------

def _iter_functions(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _param_count(fn):
    a = fn.args
    names = [x.arg for x in getattr(a, "posonlyargs", []) + a.args + a.kwonlyargs]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    return len(names) + (1 if a.vararg else 0) + (1 if a.kwarg else 0)


def _complexity(fn):
    score = 1
    for node in ast.walk(fn):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor,
                             ast.ExceptHandler, ast.IfExp, ast.Assert)):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
    return score


def _fn_length(fn):
    return (fn.end_lineno or fn.lineno) - fn.lineno + 1


class _Normalizer(ast.NodeTransformer):
    """Strip identifiers so structurally identical bodies hash equal."""

    def visit_Name(self, node):
        return ast.copy_location(ast.Name(id="x", ctx=ast.Load()), node)

    def visit_arg(self, node):
        node.arg = "x"
        node.annotation = None
        return node

    def _visit_fn(self, node):
        self.generic_visit(node)
        node.name = "f"
        node.decorator_list = []
        node.returns = None
        return node

    visit_FunctionDef = _visit_fn
    visit_AsyncFunctionDef = _visit_fn


def _normalized_hash(fn):
    node = copy.deepcopy(fn)
    # Drop the docstring before hashing.
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        node.body = node.body[1:] or [ast.Pass()]
    node = _Normalizer().visit(node)
    return hashlib.md5(ast.dump(node).encode()).hexdigest()


def _is_wide_tuple_annotation(node):
    if not isinstance(node, ast.Subscript):
        return False
    base = node.value
    name = base.id if isinstance(base, ast.Name) else (
        base.attr if isinstance(base, ast.Attribute) else None)
    if name not in ("Tuple", "tuple"):
        return False
    sl = node.slice
    if isinstance(sl, ast.Index):  # py3.8 compat node
        sl = sl.value
    return isinstance(sl, ast.Tuple) and len(sl.elts) > TUPLE_ARITY


# ---- metric collectors ---------------------------------------------------------

def collect(files):
    details = {
        "long_param_functions": [],
        "god_classes": [],
        "wide_tuples": [],
        "complex_functions": [],
        "long_functions": [],
        "duplicate_function_groups": [],
        "deferred_imports": [],
        "big_modules": [],
    }
    loc_total = 0
    cc_values = []
    dup_index = {}

    for path in files:
        rel = _rel(path)
        try:
            text = path.read_text()
            tree = ast.parse(text)
        except SyntaxError as e:
            details.setdefault("parse_errors", []).append(f"{rel}: {e}")
            continue
        loc = len(text.splitlines())
        loc_total += loc
        if loc > MODULE_LOC_THRESHOLD:
            details["big_modules"].append({"where": rel, "loc": loc})

        # wide tuple annotations / aliases anywhere in the module
        for node in ast.walk(tree):
            if _is_wide_tuple_annotation(node):
                details["wide_tuples"].append(
                    {"where": f"{rel}:{node.lineno}", "kind": "annotation"})

        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            methods = [n for n in cls.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            cls_loc = (cls.end_lineno or cls.lineno) - cls.lineno + 1
            if len(methods) >= GOD_METHODS or cls_loc >= GOD_LOC:
                details["god_classes"].append({
                    "where": f"{rel}:{cls.lineno}", "name": cls.name,
                    "methods": len(methods), "loc": cls_loc})

        for fn in _iter_functions(tree):
            where = f"{rel}:{fn.lineno}"
            n_params = _param_count(fn)
            if n_params > PARAM_THRESHOLD:
                details["long_param_functions"].append(
                    {"where": where, "name": fn.name, "params": n_params})
            cc = _complexity(fn)
            cc_values.append(cc)
            if cc > CC_THRESHOLD:
                details["complex_functions"].append(
                    {"where": where, "name": fn.name, "cc": cc})
            length = _fn_length(fn)
            if length > FN_LENGTH_THRESHOLD:
                details["long_functions"].append(
                    {"where": where, "name": fn.name, "lines": length})
            # returned wide tuple literals
            for node in ast.walk(fn):
                if (isinstance(node, ast.Return)
                        and isinstance(node.value, ast.Tuple)
                        and len(node.value.elts) > TUPLE_ARITY):
                    details["wide_tuples"].append(
                        {"where": f"{rel}:{node.lineno}", "kind": "return",
                         "fn": fn.name})
                    break
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    details["deferred_imports"].append(
                        {"where": f"{rel}:{node.lineno}", "fn": fn.name})
            if sum(1 for _ in ast.walk(fn)) >= DUP_MIN_NODES:
                dup_index.setdefault(_normalized_hash(fn), []).append(
                    {"where": where, "name": fn.name})

    for entries in dup_index.values():
        if len(entries) > 1:
            details["duplicate_function_groups"].append(entries)

    return details, loc_total, cc_values


def duplicate_files(tracked):
    by_hash = {}
    for p in tracked:
        try:
            norm = "\n".join(l.strip() for l in p.read_text().splitlines() if l.strip())
        except Exception:
            continue
        if len(norm) < 200:  # ignore trivial files (__init__ etc.)
            continue
        by_hash.setdefault(hashlib.md5(norm.encode()).hexdigest(), []).append(_rel(p))
    return [grp for grp in by_hash.values() if len(grp) > 1]


def unreferenced_defs(core_files, tracked):
    """Module-level defs never mentioned outside their own definition. Textual
    search so references from template strings / generated code still count."""
    corpus = "\n".join(p.read_text() for p in tracked)
    findings = []
    for path in core_files:
        rel = _rel(path)
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith("__") or name == "main":
                continue
            refs = len(re.findall(r"\b%s\b" % re.escape(name), corpus))
            if refs <= 1:  # the def itself
                findings.append({"where": f"{rel}:{node.lineno}", "name": name})
    return findings


def config_language_check():
    """Conceptual-integrity checks on the config language: every mapping type
    must be registered consistently in the union, the builder registry, and the
    codegen template registry; vocabulary size is tracked as a growth signal."""
    issues = []
    vocab = {}
    sys.path.insert(0, str(ROOT))
    try:
        from ableton_control_surface_as_code.model_v2 import (  # noqa: PLC0415
            KNOWN_MAPPING_TYPES, _MAPPING_BUILDERS, RootV2ModesOrModeless)
        from ableton_control_surface_as_code.gen import template_to_code  # noqa: PLC0415
        known = set(KNOWN_MAPPING_TYPES)
        builders = set(_MAPPING_BUILDERS)
        # 'device' is special-cased in build_mode_code rather than registered.
        templates = set(template_to_code) | {"device"}
        for label, got in (("_MAPPING_BUILDERS", builders),
                           ("template_to_code", templates)):
            for t in sorted(known - got):
                issues.append(f"mapping type '{t}' missing from {label}")
            for t in sorted(got - known):
                issues.append(f"{label} registers unknown mapping type '{t}'")
        vocab = {
            "mapping_types": len(known),
            "root_keys": len(RootV2ModesOrModeless.model_fields),
        }
    except Exception as e:  # import failure is itself a drift signal
        issues.append(f"config introspection failed: {e}")
    return issues, vocab


def concern_spread(files):
    """Number of modules mentioning each cross-cutting concern. A concern that
    creeps across more modules over time is coupling in progress."""
    spread = {}
    for concern in CONCERNS:
        pat = re.compile(r"\b%s" % concern, re.IGNORECASE)
        hits = [_rel(p) for p in files if pat.search(p.read_text())]
        spread[concern] = {"modules": len(hits), "files": hits}
    return spread


# ---- run / persist / render -----------------------------------------------------

def read_test_results():
    out_file = QUALITY_DIR / "last_test_output.txt"
    passed = failed = errors = 0
    if out_file.exists():
        text = out_file.read_text()
        m = re.search(r"(\d+) passed", text)
        passed = int(m.group(1)) if m else 0
        m = re.search(r"(\d+) failed", text)
        failed = int(m.group(1)) if m else 0
        m = re.search(r"(\d+) error", text)
        errors = int(m.group(1)) if m else 0
    return {"passed": passed, "failed": failed, "errors": errors}


def build_snapshot(test_exit):
    core = _core_files()
    tracked = _tracked_py_files()
    details, loc_total, cc_values = collect(core)
    dup_files = duplicate_files(tracked)
    dead = unreferenced_defs(core, tracked)
    cfg_issues, vocab = config_language_check()
    spread = concern_spread(core)

    tests = read_test_results()
    tests["exit"] = test_exit

    metrics = {
        "loc_total": loc_total,
        "modules_over_loc_threshold": len(details["big_modules"]),
        "long_param_functions": len(details["long_param_functions"]),
        "max_params": max([d["params"] for d in details["long_param_functions"]] or [0]),
        "god_classes": len(details["god_classes"]),
        "wide_tuples": len(details["wide_tuples"]),
        "cc_max": max(cc_values or [0]),
        "cc_mean": round(sum(cc_values) / len(cc_values), 2) if cc_values else 0,
        "cc_functions_over_threshold": len(details["complex_functions"]),
        "long_functions": len(details["long_functions"]),
        "duplicate_function_groups": len(details["duplicate_function_groups"]),
        "duplicate_files": len(dup_files),
        "deferred_imports": len(details["deferred_imports"]),
        "unreferenced_defs": len(dead),
        "config_drift_issues": len(cfg_issues),
        "config_mapping_types": vocab.get("mapping_types", 0),
        "config_root_keys": vocab.get("root_keys", 0),
    }
    for concern, info in spread.items():
        metrics["spread_%s" % concern] = info["modules"]

    details["duplicate_files"] = dup_files
    details["unreferenced_defs"] = dead
    details["config_drift_issues"] = cfg_issues
    details["concern_spread"] = spread

    return {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "sha": _git("rev-parse", "--short", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(_git("status", "--porcelain")),
        "tests": tests,
        "metrics": metrics,
    }, details


def load_history():
    if not HISTORY.exists():
        return []
    entries = []
    for line in HISTORY.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def verdict_for(snapshot, previous):
    if previous is None:
        return "baseline", []
    worsened = []
    prev_m = previous.get("metrics", {})
    for key in BAD_IF_UP:
        cur = snapshot["metrics"].get(key, 0)
        prev = prev_m.get(key)
        if prev is not None and cur > prev:
            worsened.append("%s %s→%s" % (key, prev, cur))
    if snapshot["tests"]["failed"] > 0:
        return "broken: failing tests", worsened
    if len(worsened) >= 3:
        return "cleanup recommended", worsened
    if worsened:
        return "watch", worsened
    return "ok", worsened


def _fmt_delta(cur, prev):
    if prev is None:
        return "—"
    d = cur - prev
    if isinstance(d, float):
        d = round(d, 2)
    if d == 0:
        return "·"
    return ("+%s" % d) if d > 0 else str(d)


def render_dashboard(snapshot, details, history):
    previous = history[-1] if history else None
    verdict, worsened = verdict_for(snapshot, previous)
    m = snapshot["metrics"]
    prev_m = previous["metrics"] if previous else {}

    def trend(key, n=10):
        vals = [h["metrics"].get(key) for h in history[-(n - 1):]] + [m.get(key)]
        return " → ".join(str(v) for v in vals if v is not None)

    rows = [
        ("Tests passed", "tests_passed"), ("LOC (core)", "loc_total"),
        ("Modules > %d LOC" % MODULE_LOC_THRESHOLD, "modules_over_loc_threshold"),
        ("Functions > %d params" % PARAM_THRESHOLD, "long_param_functions"),
        ("Max params", "max_params"),
        ("God classes (≥%d methods or ≥%d LOC)" % (GOD_METHODS, GOD_LOC), "god_classes"),
        ("Wide tuples (> %d elements)" % TUPLE_ARITY, "wide_tuples"),
        ("Cyclomatic complexity (max)", "cc_max"),
        ("Cyclomatic complexity (mean)", "cc_mean"),
        ("Functions CC > %d" % CC_THRESHOLD, "cc_functions_over_threshold"),
        ("Functions > %d lines" % FN_LENGTH_THRESHOLD, "long_functions"),
        ("Duplicate function groups", "duplicate_function_groups"),
        ("Duplicate files", "duplicate_files"),
        ("Deferred (in-function) imports", "deferred_imports"),
        ("Unreferenced top-level defs", "unreferenced_defs"),
        ("Config-language drift issues", "config_drift_issues"),
        ("Config mapping types", "config_mapping_types"),
        ("Config root keys", "config_root_keys"),
    ] + [("Concern spread: %s (modules)" % c, "spread_%s" % c) for c in CONCERNS]

    lines = []
    lines.append("# Quality Dashboard")
    lines.append("")
    lines.append("`%s` on `%s`%s — %s" % (
        snapshot["sha"], snapshot["branch"],
        " (dirty)" if snapshot["dirty"] else "", snapshot["ts"]))
    lines.append("")
    lines.append("**Verdict: %s**" % verdict)
    if worsened:
        lines.append("")
        lines.append("Worsened since last run: " + "; ".join(worsened))
    lines.append("")
    lines.append("Tests: %(passed)s passed, %(failed)s failed, %(errors)s errors"
                 % snapshot["tests"])
    lines.append("")
    lines.append("| Metric | Current | Prev | Δ | Trend (oldest → newest) |")
    lines.append("|---|---:|---:|---:|---|")
    for label, key in rows:
        if key == "tests_passed":
            cur = snapshot["tests"]["passed"]
            prev = previous["tests"]["passed"] if previous else None
            tr = " → ".join(str(h["tests"]["passed"]) for h in history[-9:]) or ""
            tr = (tr + " → " if tr else "") + str(cur)
        else:
            cur = m.get(key, 0)
            prev = prev_m.get(key)
            tr = trend(key)
        lines.append("| %s | %s | %s | %s | %s |"
                     % (label, cur, "—" if prev is None else prev,
                        _fmt_delta(cur, prev), tr))

    def section(title, items, fmt, limit=12):
        lines.append("")
        lines.append("## %s (%d)" % (title, len(items)))
        if not items:
            lines.append("- none")
            return
        for it in items[:limit]:
            lines.append("- " + fmt(it))
        if len(items) > limit:
            lines.append("- … and %d more (see .quality/runs/)" % (len(items) - limit))

    section("Functions with > %d params" % PARAM_THRESHOLD,
            sorted(details["long_param_functions"], key=lambda d: -d["params"]),
            lambda d: "`%s` %s — %d params" % (d["where"], d["name"], d["params"]))
    section("God classes",
            sorted(details["god_classes"], key=lambda d: -d["loc"]),
            lambda d: "`%s` %s — %d methods, %d LOC"
                      % (d["where"], d["name"], d["methods"], d["loc"]))
    section("Most complex functions (CC > %d)" % CC_THRESHOLD,
            sorted(details["complex_functions"], key=lambda d: -d["cc"]),
            lambda d: "`%s` %s — CC %d" % (d["where"], d["name"], d["cc"]))
    section("Wide tuples", details["wide_tuples"],
            lambda d: "`%s` (%s%s)" % (d["where"], d["kind"],
                                       ", in %s" % d["fn"] if d.get("fn") else ""))
    section("Duplicate function groups", details["duplicate_function_groups"],
            lambda grp: "; ".join("`%s` %s" % (e["where"], e["name"]) for e in grp))
    section("Duplicate files", details["duplicate_files"],
            lambda grp: " == ".join("`%s`" % f for f in grp))
    section("Deferred imports", details["deferred_imports"],
            lambda d: "`%s` (in %s)" % (d["where"], d["fn"]))
    section("Unreferenced top-level defs", details["unreferenced_defs"],
            lambda d: "`%s` %s" % (d["where"], d["name"]))
    section("Config-language drift", details["config_drift_issues"], lambda s: s)
    section("Big modules (> %d LOC)" % MODULE_LOC_THRESHOLD,
            sorted(details["big_modules"], key=lambda d: -d["loc"]),
            lambda d: "`%s` — %d LOC" % (d["where"], d["loc"]))

    lines.append("")
    lines.append("## Concern spread detail")
    for concern in CONCERNS:
        info = details["concern_spread"][concern]
        lines.append("- **%s**: %d modules — %s"
                     % (concern, info["modules"],
                        ", ".join("`%s`" % f for f in info["files"])))
    lines.append("")
    return "\n".join(lines), verdict


def main():
    test_exit = 0
    args = sys.argv[1:]
    if "--test-exit" in args:
        test_exit = int(args[args.index("--test-exit") + 1])

    QUALITY_DIR.mkdir(exist_ok=True)
    RUNS_DIR.mkdir(exist_ok=True)

    history = load_history()
    snapshot, details = build_snapshot(test_exit)
    dashboard, verdict = render_dashboard(snapshot, details, history)
    snapshot["verdict"] = verdict

    run_name = "%s_%s.json" % (snapshot["ts"].replace(":", "-"),
                               snapshot["sha"] or "nosha")
    (RUNS_DIR / run_name).write_text(
        json.dumps({"snapshot": snapshot, "details": details}, indent=2))
    with HISTORY.open("a") as f:
        f.write(json.dumps(snapshot) + "\n")
    DASHBOARD.write_text(dashboard)

    previous = history[-1] if history else None
    print("Quality snapshot: %s (%s)" % (snapshot["sha"] or "no-sha", verdict))
    m = snapshot["metrics"]
    prev_m = previous["metrics"] if previous else {}
    for key in ["loc_total", "long_param_functions", "god_classes", "wide_tuples",
                "cc_functions_over_threshold", "duplicate_function_groups",
                "deferred_imports", "unreferenced_defs", "config_drift_issues",
                "spread_hud"]:
        print("  %-28s %6s  (Δ %s)" % (key, m.get(key),
                                       _fmt_delta(m.get(key, 0), prev_m.get(key))))
    print("Dashboard: %s" % _rel(DASHBOARD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
