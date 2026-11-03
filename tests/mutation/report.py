"""Merge the results of mutate.py (one JSON file per shard) into a report.

    python tests/mutation/report.py results/*.json --markdown report.md --json all.json

The score of a module is the share of its mutants the tests noticed (killed,
or so slow they timed out). Every survivor is listed with its line: each one
is a change no test notices, so either a test is missing, or the change does
not matter there (an "equivalent" mutant, e.g. ``>`` → ``>=`` where the two
values can never be equal).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--markdown", default="mutation-report.md")
    parser.add_argument("--json", default="mutation-all.json")
    args = parser.parse_args()

    results: list[dict] = []
    for name in args.files:
        results.extend(json.loads(Path(name).read_text("utf-8")))
    results.sort(key=lambda r: (r["file"], r["line"], r["index"]))
    Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")

    per_file: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in results:
        per_file[r["file"]][r["status"]] += 1
    total: dict[str, int] = defaultdict(int)
    for counts in per_file.values():
        for status, count in counts.items():
            total[status] += count

    def score(counts: dict[str, int]) -> str:
        tested = counts["killed"] + counts["timeout"] + counts["survived"]
        if not tested:
            return "–"
        return f"{100 * (counts['killed'] + counts['timeout']) / tested:.1f} %"

    lines = [
        "# Mutation testing",
        "",
        f"**{score(total)}** of the mutants noticed by the tests: "
        f"{total['killed']} killed, {total['timeout']} timed out, "
        f"**{total['survived']} survived**"
        + (f", {total['not_run']} not run (time)" if total["not_run"] else "")
        + (f", {total['invalid']} invalid (the change breaks the code)" if total["invalid"] else "")
        + ".",
        "",
        "| Module | Mutants | Killed | Timeout | Survived | Not run / invalid | Score |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    order = sorted(per_file.items(), key=lambda item: -item[1]["survived"])
    for name, counts in order:
        mutants = sum(counts.values())
        lines.append(
            f"| `{name}` | {mutants} | {counts['killed']} | {counts['timeout']} | "
            f"{counts['survived']} | {counts['not_run'] + counts['invalid']} | {score(counts)} |"
        )
    lines += ["", "## Survivors", ""]
    for name, _counts in order:
        survivors = [r for r in results if r["file"] == name and r["status"] == "survived"]
        if not survivors:
            continue
        lines += [
            f"### `{name}` ({len(survivors)})",
            "",
            "| Line | Change | Code |",
            "|---:|---|---|",
        ]
        for r in survivors:
            code = r.get("code", "").replace("|", "\\|")
            lines.append(f"| {r['line']} | `{r['change']}` | `{code}` |")
        lines.append("")
    Path(args.markdown).write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines[: 8 + len(order)]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
