"""Mutation testing of the integration: do the tests notice a small mistake?

Every mutant is one small change in the code (``<`` becomes ``<=``, ``+``
becomes ``-``, ``and`` becomes ``or``, a number becomes that number + 1,
``True`` becomes ``False``...). For each one the tests run: when a test fails
the mutant is *killed* (good: the tests saw the mistake); when every test
passes it *survived* (a mistake no test notices: a test is missing).

    python tests/mutation/mutate.py --list                 count the mutants
    python tests/mutation/mutate.py --files engine.py      one module, all its mutants
    python tests/mutation/mutate.py --shard 3 --shards 20  every 20th mutant from the 4th
    python tests/mutation/mutate.py --limit 10             only the first 10 (a quick try)

The modules without Home Assistant are tested first with their own tests
(standard library only, fast), then, if the mutant survived, with the Home
Assistant tests too. The other modules are tested with the whole suite
(pytest, stopped at the first failure). The results are written as JSON
(``--out``); ``report.py`` turns them into a report.

A line ending with ``# pragma: no mutate`` is left as it is. The code is
changed in place and always restored, also after an error.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "custom_components" / "advanced_climate"
# Constants only: a changed constant is a changed setting, not a mistake in the logic.
SKIP_FILES = {"const.py"}
# The modules the standard-library tests load (tests/pure.py).
PURE = {
    "alerts.py",
    "device_echo.py",
    "engine.py",
    "learning.py",
    "mold.py",
    "outdoor.py",
    "presence.py",
    "schedule.py",
    "sun.py",
    "trend.py",
    "window.py",
}
# Calls whose arguments are only text for people (logs, messages): not mutated.
QUIET_CALLS = {"debug", "info", "warning", "error", "exception", "critical"}

COMPARE = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}
ARITHMETIC = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
    ast.FloorDiv: ast.Div,
}
SYMBOL = {
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.And: "and",
    ast.Or: "or",
}


class Mutator(ast.NodeTransformer):
    """Walks a module; counts the places it can change and changes the ``target`` one."""

    def __init__(self, lines: list[str], target: int | None = None) -> None:
        self.lines = lines
        self.target = target
        self.count = 0
        self.found: list[dict] = []
        self.done: dict | None = None

    # -- places that are not mutated ---------------------------------------
    def _quiet(self, node: ast.AST) -> bool:
        line = getattr(node, "lineno", None)
        return line is not None and self.lines[line - 1].rstrip().endswith("# pragma: no mutate")

    def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.AST:
        return node  # f-strings: text

    def visit_Call(self, node: ast.Call) -> ast.AST:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in QUIET_CALLS:
            return node  # a log line
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._function(node)

    def _function(self, node):  # noqa: ANN001, ANN202
        # The docstring and the annotations are left alone; the defaults and the body are not.
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            body = body[1:]
        node.args.defaults = [self.visit(d) for d in node.args.defaults]
        node.args.kw_defaults = [self.visit(d) if d else d for d in node.args.kw_defaults]
        new_body = [self.visit(statement) for statement in body]
        node.body = node.body[: len(node.body) - len(body)] + new_body
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
        if node.value is not None:
            node.value = self.visit(node.value)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        return node

    # -- one place ----------------------------------------------------------
    def _place(self, node: ast.AST, what: str, apply) -> ast.AST:  # noqa: ANN001
        if self._quiet(node):
            return node
        index = self.count
        self.count += 1
        line = getattr(node, "lineno", 0)
        info = {"index": index, "line": line, "change": what}
        if self.target is None:
            self.found.append(info)
            return node
        if index == self.target:
            self.done = info
            return apply()
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            new = COMPARE.get(type(op))
            if new is None:
                continue

            def apply(i=i, new=new):  # noqa: ANN001, ANN202
                node.ops[i] = new()
                return node

            node = self._place(node, f"{SYMBOL[type(op)]} → {SYMBOL[new]}", apply)
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        new = ARITHMETIC.get(type(node.op))
        if new is None:
            return node
        old = type(node.op)

        def apply():  # noqa: ANN202
            node.op = new()
            return node

        return self._place(node, f"{SYMBOL[old]} → {SYMBOL[new]}", apply)

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        self.generic_visit(node)
        new = ARITHMETIC.get(type(node.op))
        if new is None:
            return node
        old = type(node.op)

        def apply():  # noqa: ANN202
            node.op = new()
            return node

        return self._place(node, f"{SYMBOL[old]}= → {SYMBOL[new]}=", apply)

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        old = type(node.op)
        new = ast.Or if old is ast.And else ast.And

        def apply():  # noqa: ANN202
            node.op = new()
            return node

        return self._place(node, f"{SYMBOL[old]} → {SYMBOL[new]}", apply)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            return self._place(node, "not x → x", lambda: node.operand)
        if isinstance(node.op, ast.USub) and not isinstance(node.operand, ast.Constant):
            return self._place(node, "-x → x", lambda: node.operand)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        value = node.value
        if isinstance(value, bool):
            return self._place(
                node,
                f"{value} → {not value}",
                lambda: ast.copy_location(ast.Constant(not value), node),
            )
        if isinstance(value, (int, float)):
            new = value + 1
            return self._place(
                node, f"{value!r} → {new!r}", lambda: ast.copy_location(ast.Constant(new), node)
            )
        return node


def _docstring_free(tree: ast.Module) -> list[ast.stmt]:
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        return body[1:]
    return body


def mutants_of(path: Path) -> list[dict]:
    """Every place of a module that can be changed."""
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    mutator = Mutator(source.splitlines())
    for statement in _docstring_free(tree):
        mutator.visit(statement)
    for info in mutator.found:
        info["file"] = path.name
        info["code"] = source.splitlines()[info["line"] - 1].strip() if info["line"] else ""
    return mutator.found


def mutated_source(path: Path, index: int) -> str:
    """The module with the place ``index`` changed (written back as Python)."""
    source = path.read_text("utf-8")
    tree = ast.parse(source)
    mutator = Mutator(source.splitlines(), index)
    tree.body = tree.body[: len(tree.body) - len(_docstring_free(tree))] + [
        mutator.visit(statement) for statement in _docstring_free(tree)
    ]
    if mutator.done is None:
        raise ValueError(f"{path.name}: no place {index}")
    return ast.unparse(ast.fix_missing_locations(tree))


def same_source(path: Path) -> str:
    """The module written back unchanged (as the mutants are): checks the round trip."""
    return ast.unparse(ast.parse(path.read_text("utf-8")))


# ---------------------------------------------------------------------------
# Running the tests
# ---------------------------------------------------------------------------
def has_pytest() -> bool:
    try:
        import pytest_homeassistant_custom_component  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def pure_tests_for(module: str) -> list[str]:
    """The standard-library test modules that use ``module`` (all of them if none says so)."""
    name = module.removesuffix(".py")
    tests = []
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        text = test.read_text("utf-8")
        if f"{name}." in text or f" {name}," in text or f"import {name}" in text:
            tests.append(f"tests.{test.stem}")
    return tests or ["discover"]


def run(command: list[str], timeout: float) -> tuple[str, float]:
    """``passed``, ``failed`` or ``timeout``, and the seconds it took."""
    start = time.monotonic()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        result = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return "timeout", time.monotonic() - start
    return ("passed" if result.returncode == 0 else "failed"), time.monotonic() - start


def commands(module: str, ha: bool) -> list[list[str]]:
    """The test runs for a mutant of ``module``, fastest first."""
    python = sys.executable
    out: list[list[str]] = []
    if module in PURE:
        tests = pure_tests_for(module)
        if tests == ["discover"]:
            out.append([python, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-f"])
        else:
            out.append([python, "-m", "unittest", "-f", *tests])
    if ha:
        out.append(
            [python, "-m", "pytest", "tests", "-x", "-q", "-p", "no:cacheprovider", "--no-cov"]
        )
    elif module not in PURE:
        out.append([python, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-f"])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--files", nargs="*", help="modules to mutate (default: all but const.py)")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="at most this many mutants")
    parser.add_argument("--max-minutes", type=float, default=0, help="stop after this time")
    parser.add_argument("--list", action="store_true", help="only count the mutants")
    parser.add_argument("--out", default="mutation-results.json")
    args = parser.parse_args()

    files = args.files or sorted(p.name for p in PACKAGE.glob("*.py") if p.name not in SKIP_FILES)
    every = [m for name in files for m in mutants_of(PACKAGE / name)]
    if args.list:
        per_file: dict[str, int] = {}
        for m in every:
            per_file[m["file"]] = per_file.get(m["file"], 0) + 1
        for name, count in sorted(per_file.items(), key=lambda x: -x[1]):
            print(f"{count:6} {name}")
        print(f"{len(every):6} in total")
        return 0
    chosen = every[args.shard :: args.shards]
    if args.limit:
        chosen = chosen[: args.limit]

    ha = has_pytest()
    backup = {name: (PACKAGE / name).read_text("utf-8") for name in {m["file"] for m in chosen}}
    results: list[dict] = []
    deadline = time.monotonic() + args.max_minutes * 60 if args.max_minutes else None
    try:
        # The round trip first: the modules written back unchanged must pass every test.
        for name in backup:
            (PACKAGE / name).write_text(same_source(PACKAGE / name), "utf-8")
        baseline = {}
        for name in sorted(backup):
            for command in commands(name, ha):
                key = " ".join(command)
                if key not in baseline:
                    status, seconds = run(command, 3600)
                    if status != "passed":
                        print(f"The tests fail without any change: {key}", file=sys.stderr)
                        return 2
                    baseline[key] = seconds
        for name, text in backup.items():
            (PACKAGE / name).write_text(text, "utf-8")

        print(f"{len(chosen)} mutants (of {len(every)}), Home Assistant tests: {ha}", flush=True)
        for number, mutant in enumerate(chosen, 1):
            if deadline is not None and time.monotonic() > deadline:
                results.extend({**m, "status": "not_run"} for m in chosen[number - 1 :])
                break
            path = PACKAGE / mutant["file"]
            path.write_text(mutated_source(path, mutant["index"]), "utf-8")
            status = "survived"
            seconds = 0.0
            for command in commands(mutant["file"], ha):
                limit = 3 * baseline[" ".join(command)] + 30
                outcome, took = run(command, limit)
                seconds += took
                if outcome != "passed":
                    status = "killed" if outcome == "failed" else "timeout"
                    break
            path.write_text(backup[mutant["file"]], "utf-8")
            results.append({**mutant, "status": status, "seconds": round(seconds, 1)})
            print(
                f"[{number}/{len(chosen)}] {status:8} {mutant['file']}:{mutant['line']} "
                f"{mutant['change']}",
                flush=True,
            )
    finally:
        for name, text in backup.items():
            (PACKAGE / name).write_text(text, "utf-8")
        shutil.rmtree(PACKAGE / "__pycache__", ignore_errors=True)
        Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
