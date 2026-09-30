#!/usr/bin/env python3
"""M2 record drift: compare every number quoted in the hypothesis/record (results/record_expectations.csv) with
the value in its source file. Status: MATCH (source rounds to the quoted value), ROUNDING_DIFF (within one unit of
the last quoted digit), DRIFT (larger difference), NOT_FOUND (no source contains it)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
from src.registry import Registry  # noqa: E402

TRANSFORMS = {"": lambda x: x, "pct": lambda x: 100.0 * x, "neg": lambda x: -x}


def parse(q: str) -> tuple[float, int]:
    s = q.replace(",", "").replace("+", "").replace("%", "").strip()
    dec = len(s.split(".")[1]) if "." in s else 0
    return float(s), dec


def status_of(src: float, quoted: float, prec: int) -> str:
    if abs(round(src, prec) - quoted) < 1e-9:
        return "MATCH"
    if abs(src - quoted) <= 10.0 ** (-prec) + 1e-12:
        return "ROUNDING_DIFF"
    return "DRIFT"


def main() -> int:
    reg = Registry()
    rows = list(csv.DictReader((WS / "results" / "record_expectations.csv").open()))
    out = []
    for r in rows:
        quoted, dec = parse(r["quoted"])
        prec = int(r["precision"]) if r.get("precision") else dec
        src_val, path, st = None, "", "NOT_FOUND"
        if r["source_key"]:
            v = reg.try_get(r["source_key"])
            if v is not None:
                src_val = TRANSFORMS[r["transform"]](float(v))
                m = reg.meta(r["source_key"])
                path = f"{m['artifact_id']}:{m['path']}"
                st = status_of(src_val, quoted, prec)
        out.append({"key": r["key"], "quoted": r["quoted"], "source_value": src_val, "status": st,
                    "source_key": r["source_key"], "transform": r["transform"], "source": path, "note": r["note"]})
    with (WS / "results" / "drift_report.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    counts = {s: sum(o["status"] == s for o in out) for s in ("MATCH", "ROUNDING_DIFF", "DRIFT", "NOT_FOUND")}
    summary = {"n": len(out), "counts": counts,
               "drift_and_not_found": [o for o in out if o["status"] in ("DRIFT", "NOT_FOUND")],
               "rounding_diff": [o for o in out if o["status"] == "ROUNDING_DIFF"]}
    (WS / "results" / "drift_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(counts))
    for o in summary["drift_and_not_found"] + summary["rounding_diff"]:
        print(o["status"], o["key"], o["quoted"], o["source_value"], o["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
