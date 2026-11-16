"""Split the card modules into groups with about as many mutants each (one job per group).

The card is in modules (custom_components/advanced_climate/www/shc). Each job
mutates a group of whole modules; the groups are made so that their sizes are
about equal. The size of a module is its number of lines, except the CSS
(core/style.js) and the texts (core/i18n.js): strings are not mutated, so they
count for little.

    python tests/mutation/card_parts.py <folder of the modules> <parts>   → JSON for the matrix
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Modules that are mostly strings (not mutated): a tenth of their lines.
LIGHT = {"style.js", "i18n.js"}


def weight(path: Path) -> float:
    lines = len([line for line in path.read_text("utf-8").splitlines() if line.strip()])
    return lines / 10 if path.name in LIGHT else lines


def parts(folder: Path, count: int, root: Path) -> list[dict]:
    """``count`` groups of the modules in ``folder`` (paths relative to ``root``), largest first."""
    files = sorted(folder.rglob("*.js"), key=lambda p: (-weight(p), str(p)))
    groups: list[tuple[float, list[str]]] = [
        (0.0, []) for _ in range(max(1, min(count, len(files))))
    ]
    for f in files:
        i = min(range(len(groups)), key=lambda k: groups[k][0])
        size, names = groups[i]
        groups[i] = (size + weight(f), [*names, f.relative_to(root).as_posix()])
    base = folder.relative_to(root)
    return [
        {
            "part": i,
            "mutate": ",".join(sorted(names)),
            "label": ", ".join(Path(n).relative_to(base).as_posix() for n in sorted(names)),
        }
        for i, (_, names) in enumerate(groups)
    ]


if __name__ == "__main__":
    folder, count = Path(sys.argv[1]).resolve(), int(sys.argv[2])
    print(json.dumps(parts(folder, count, Path.cwd().resolve())))
