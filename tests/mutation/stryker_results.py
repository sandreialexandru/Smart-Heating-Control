"""Turn the JSON report of Stryker (the card) into the results of mutate.py.

    python tests/mutation/stryker_results.py reports/card-mutation.json --out results/card-0.json

Then report.py puts the card and the Python modules in one report. Mutants
Stryker could not run (they break the code before any test) are "invalid";
those outside the lines of the job (Stryker lists them as "Ignored") are left
out, since the job of those lines tests them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

STATUS = {
    "Killed": "killed",
    "Timeout": "timeout",
    "Survived": "survived",
    "NoCoverage": "survived",
    "CompileError": "invalid",
    "RuntimeError": "invalid",
    "Pending": "not_run",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.report).read_text("utf-8"))
    results = []
    for path, item in data.get("files", {}).items():
        lines = item.get("source", "").splitlines()
        name = Path(path).name
        for index, mutant in enumerate(item.get("mutants", [])):
            if mutant.get("status") == "Ignored":
                continue  # outside the lines of this job: another job tests it
            line = mutant["location"]["start"]["line"]
            replacement = " ".join(str(mutant.get("replacement", "")).split())
            if len(replacement) > 60:
                replacement = replacement[:57] + "..."
            results.append(
                {
                    "file": name,
                    "index": index,
                    "line": line,
                    "change": f"{mutant['mutatorName']}: {replacement}",
                    "code": lines[line - 1].strip()[:120] if 0 < line <= len(lines) else "",
                    "status": STATUS.get(mutant.get("status", ""), "invalid"),
                }
            )
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(results)} mutants of the card")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
