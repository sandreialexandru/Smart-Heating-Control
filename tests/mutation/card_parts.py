"""Split the card into line ranges with about as many mutants each (one job per range).

The mutants are far from even along the card: the drawing of the chart and the
house have many, the styles at the end almost none. ``DENSITY`` holds how many
mutants each tenth of the card had in a full run (2026-11-04: 120 … 74, 4,739 in
all); the ranges follow it, so the jobs take about the same time. When the card
changes a lot, update it from the totals the card jobs print (``All files``).

    python tests/mutation/card_parts.py <card.js> <parts>   → JSON for the matrix
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DENSITY = [120, 333, 503, 473, 912, 919, 479, 598, 328, 74]


def parts(lines: int, count: int, density: list[int] = DENSITY) -> list[dict]:
    """``count`` ranges of the lines 1 … ``lines`` with equal shares of the mutants."""
    size = lines / len(density)
    # Mutants per line, the same within each tenth.
    per_line = [density[min(len(density) - 1, int(i / size))] / size for i in range(lines)]
    total = sum(per_line)
    out, start, acc = [], 1, 0.0
    for line, weight in enumerate(per_line, 1):
        acc += weight
        if acc >= total * (len(out) + 1) / count and len(out) < count - 1:
            out.append({"part": len(out), "range": f"{start}-{line}"})
            start = line + 1
    out.append({"part": len(out), "range": f"{start}-{lines}"})
    return out


if __name__ == "__main__":
    card, count = sys.argv[1], int(sys.argv[2])
    lines = len(Path(card).read_text("utf-8").splitlines())
    print(json.dumps(parts(lines, count)))
