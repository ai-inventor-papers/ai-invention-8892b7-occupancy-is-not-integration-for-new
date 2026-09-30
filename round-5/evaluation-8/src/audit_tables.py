#!/usr/bin/env python3
"""Reusable table-assertion checker. Re-reads every sourced cell of a paper table
from its source file and asserts that the displayed value matches under the
frozen match rule. A table with any failing cell must not be emitted.

CLI
  python audit_tables.py check-dir tables/ --out results/table_assertions.json
      checks every tables/<T>.cells.json (cells: display, src 'relpath::key', kind, check)
  python audit_tables.py check-rows k1_rows.csv --value-col value --source-col source [--kind-col kind]
      checks a rows CSV whose source column holds 'relpath::key' (run-root-relative) for each value
      (this is how the K1/K2/K3 post-confirmation rows produced in parallel can be checked later).

Key syntax: JSON path 'a/b/0/c'; CSV 'csv:col=v;col2=v2|target'; 'recompute:<fn>' resolves through
checks.RECOMPUTE (row-level recomputation). Paths are relative to the run root.
Exit code 0 = all tables pass, 1 = at least one failing cell.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import math
import re
import sys
from pathlib import Path

RUN_ROOT = Path(os.environ.get("AII_RUN_ROOT", str(Path(__file__).resolve().parents[4])))  # run root: this folder is <run>/3_invention_loop/iter_5/gen_art/<artifact>
_cache: dict = {}


def _read(rel: str, key: str):
    if key.startswith("recompute:"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import checks  # row-level recomputation functions
        return checks.RECOMPUTE[key.split(":", 1)[1]]()
    p = RUN_ROOT / rel
    if key.startswith("csv:"):
        if p not in _cache:
            with open(p, newline="") as fh:
                _cache[p] = list(csv.DictReader(fh))
        cond, target = key[4:].rsplit("|", 1)
        conds = [c.split("=", 1) for c in cond.split(";") if c]
        rows = [r for r in _cache[p] if all(str(r.get(a, "")).strip() == b for a, b in conds)]
        if target == "#count":
            return len(rows)
        return rows[0][target]
    if p not in _cache:
        _cache[p] = json.loads(p.read_text())
    o = _cache[p]
    for part in [x for x in key.split("/") if x]:
        o = o[int(part)] if isinstance(o, list) else o[part]
    return o


def _parse(s: str):
    t = s.strip().replace("−", "-").replace(",", "")
    pct = t.endswith("%")
    t = t.rstrip("%")
    m = re.fullmatch(r"[+\-]?(\d+(?:\.\d+)?|\.\d+)(?:e([+\-]?\d+))?", t)
    if not m:
        return None
    mant = m.group(1)
    dec = len(mant.split(".")[1]) if "." in mant else 0
    if m.group(2):
        dec -= int(m.group(2))
    return float(t), dec, pct


def check_value(display: str, src_val, kind: str) -> tuple[bool, str]:
    p = _parse(str(display))
    if p is None:
        return False, f"display '{display}' is not numeric"
    v, dec, pct = p
    try:
        s = float(src_val)
    except (TypeError, ValueError):
        return False, f"source '{src_val}' not numeric"
    if pct or kind == "pct":
        s = s * 100.0
    if kind == "count":
        return abs(s - v) < 1e-9, f"source {s}"
    if kind == "p" and s < 0.001:
        sig = len(re.sub(r"[^0-9]", "", str(display).split("e")[0]).lstrip("0")) or 1
        rs = float(f"{s:.{sig}g}")
        return abs(rs - v) <= 1e-12 * max(1, abs(v)) or abs(s - v) <= 0.5 * 10 ** (-dec), f"source {s:.4g}"
    return abs(s - v) <= 0.5 * 10 ** (-dec) + 1e-9, f"source {s:.6g}"


def check_cell(c: dict) -> tuple[bool, str]:
    chk = c.get("check", "value")
    if chk == "literal" or not c.get("src"):
        return True, "literal"
    src = str(c["src"])
    if chk == "text":
        rel = src.split("::")[0]
        txt = (RUN_ROOT / rel).read_text(errors="ignore")
        ok = str(c.get("needle") or "") in txt or str(c.get("needle") or "").replace('"', '\\"') in txt
        return ok, "needle found" if ok else f"needle not found in {rel}"
    if src.startswith("recompute:"):
        rel, key = "", src
    else:
        rel, key = src.split("::", 1)
    try:
        val = _read(rel, key)
    except (KeyError, IndexError, FileNotFoundError, ValueError, StopIteration) as e:
        return False, f"source read failed: {type(e).__name__} {e}"
    if chk == "exact":
        return str(val) == str(c["display"]), f"source '{val}'"
    return check_value(c["display"], val, c.get("kind", "cont"))


def check_dir(d: Path, out: Path) -> int:
    res = {"tables": {}, "failures": []}
    for f in sorted(d.glob("*.cells.json")):
        name = f.name.replace(".cells.json", "")
        cells = json.loads(f.read_text())
        n_chk = n_fail = 0
        for c in cells:
            ok, why = check_cell(c)
            if c.get("check") != "literal" and c.get("src"):
                n_chk += 1
            if not ok:
                n_fail += 1
                res["failures"].append(dict(table=name, row=c["row"], col=c["col"], display=c["display"], src=c["src"], why=why))
        res["tables"][name] = dict(n_cells=len(cells), n_checked=n_chk, n_fail=n_fail, pass_=n_fail == 0, **{"pass": n_fail == 0})
    out.write_text(json.dumps(res, indent=1, default=str))
    n_pass = sum(1 for t in res["tables"].values() if t["pass"])
    print(f"{n_pass}/{len(res['tables'])} tables pass; {len(res['failures'])} failing cells")
    return 0 if n_pass == len(res["tables"]) else 1


def check_rows(path: Path, value_col: str, source_col: str, kind_col: str | None) -> int:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    bad = 0
    for i, r in enumerate(rows):
        c = dict(display=r[value_col], src=r[source_col], kind=(r.get(kind_col) if kind_col else "cont") or "cont", check="value", row=i, col=value_col)
        ok, why = check_cell(c)
        if not ok:
            bad += 1
            print(f"FAIL row {i}: {r[value_col]} vs {r[source_col]} ({why})")
    print(f"{len(rows) - bad}/{len(rows)} rows match their sources")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("check-dir")
    a.add_argument("dir")
    a.add_argument("--out", required=True)
    b = sub.add_parser("check-rows")
    b.add_argument("csv")
    b.add_argument("--value-col", default="value")
    b.add_argument("--source-col", default="source")
    b.add_argument("--kind-col", default=None)
    args = ap.parse_args()
    if args.cmd == "check-dir":
        return check_dir(Path(args.dir), Path(args.out))
    return check_rows(Path(args.csv), args.value_col, args.source_col, args.kind_col)


if __name__ == "__main__":
    sys.exit(main())
