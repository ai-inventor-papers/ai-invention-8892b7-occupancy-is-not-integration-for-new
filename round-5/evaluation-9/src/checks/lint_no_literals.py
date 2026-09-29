#!/usr/bin/env python3
"""Lint: no data number typed into plot code.

Plot modules necessarily contain layout floats (axes positions in figure fractions, limits), which are 2-3
decimal fractions and coincide with plotted values by chance. The rule is therefore:
  (a) no number inside a STRING literal (captions, labels, annotations) of src/plots/*.py may equal a plotted
      value at its display precision (this is where typed numbers drift from the record), and
  (b) no FLOAT literal with >= 4 significant digits may equal a plotted value (layout never needs that
      precision; a data value usually has it).
Trivial cosmetics (0.5, 1.96, 0.05, style.py tick positions) are exempt.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
from src import style  # noqa: E402

TRIVIAL = {0.0, 0.5, 1.0, 1.96, 0.05, 0.1, 0.2, 0.3, 0.25, 0.4, 0.6, 0.7, 0.8, 0.9, 1.1, 1.2, 1.4, 1.6, 1.8,
           2.0, 2.2, 0.15, 0.02, 0.01} | set(style.LOG_TICKS) | set(style.OR_TICKS)
NUM_IN_STR = re.compile(r"(?<![\w.])-?\d+\.\d+(?![\w.])")


def plotted_values() -> set[str]:
    out = set()
    for pv in list((WS / "figures").glob("*/plotted_values.json")) + [WS / "tables" / "caveats_values.json"]:
        if not pv.exists():
            continue
        for r in json.loads(pv.read_text()):
            v = r.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                for nd in (2, 3):
                    s = f"{v:.{nd}f}"
                    if float(s) not in TRIVIAL and abs(float(s)) >= 0.01 and not float(s).is_integer():
                        out.add(s)
    return out


def main() -> int:
    targets = plotted_values()
    hits = []
    for py in sorted((WS / "src" / "plots").glob("*.py")):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                sig = len(re.sub(r"[^0-9]", "", f"{node.value}").lstrip("0"))
                if sig >= 4 and (f"{node.value:.3f}" in targets or f"{node.value:.2f}" in targets):
                    hits.append((py.name, node.lineno, node.value))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for m in NUM_IN_STR.findall(node.value):
                    if m.lstrip("-") in targets or m in targets:
                        hits.append((py.name, node.lineno, m))
    res = {"n_targets": len(targets), "n_hits": len(hits), "hits": hits}
    (WS / "results" / "lint_no_literals.json").write_text(json.dumps(res, indent=1))
    print(res)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
