"""Independent re-reader: resolves every plotted value from its source file WITHOUT importing src/registry.py.

Selectors are re-implemented here with plain json / csv / re; sources.yaml is read only for the address
(file path + selector) of each declared key. Used by check_F*.py.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

import yaml

WS = Path(__file__).resolve().parents[1]
RUN = Path(os.environ.get("AII_RUN_ROOT", WS.parents[3])).resolve()
SPEC = yaml.safe_load((WS / "sources.yaml").read_text())
FORM = {"lin_lo": lambda x, se: x - 1.96 * se, "lin_hi": lambda x, se: x + 1.96 * se,
        "exp_lo": lambda b, se: math.exp(b - 1.96 * se), "exp_hi": lambda b, se: math.exp(b + 1.96 * se),
        "neg": lambda x: -x, "diff": lambda a, b: a - b, "pct": lambda x: 100.0 * x}
_cache: dict = {}


def fpath(alias: str) -> Path:
    return RUN / SPEC["files"][alias]["path"]


def text(alias: str) -> str:
    if alias not in _cache:
        _cache[alias] = fpath(alias).read_text()
    return _cache[alias]


def ptr(doc, pointer: str):
    for tok in [t.replace("~1", "/").replace("~0", "~") for t in pointer.lstrip("/").split("/")]:
        doc = doc[int(tok)] if isinstance(doc, list) else doc[tok]
    return doc


def num(v):
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return v
    return v


def resolve_sel(alias: str, s: dict):
    if "json_pointer" in s:
        return ptr(json.loads(text(alias)), s["json_pointer"])
    if "csv_row" in s or "csv_count" in s:
        rows = list(csv.DictReader(text(alias).splitlines()))
        if "csv_row" in s:
            hit = [r for r in rows if all(str(r[k]) == str(v) for k, v in s["csv_row"]["filters"].items())]
            assert len(hit) == 1, f"{alias}: {len(hit)} rows"
            return num(hit[0][s["csv_row"]["column"]])
        c, n = s["csv_count"], 0
        for r in rows:
            if all(str(r[k]) == str(v) for k, v in c.get("filters", {}).items()) \
                    and not any(re.search(rx, r[k]) for k, rx in c.get("exclude_regex", {}).items()) \
                    and all(r[k] not in ("", None) and float(r[k]) < t for k, t in c.get("lt", {}).items()) \
                    and all(r[k] not in ("", None) and float(r[k]) > t for k, t in c.get("gt", {}).items()):
                n += 1
        return float(n)
    if "md_regex" in s:
        return num(re.search(s["md_regex"], text(alias), flags=re.S).group(1))
    if "json_regex" in s:
        v = ptr(json.loads(text(alias)), s["json_regex"]["pointer"])
        v = " || ".join(map(str, v)) if isinstance(v, list) else str(v)
        return num(re.search(s["json_regex"]["regex"], v, flags=re.S).group(1))
    raise ValueError(s)


def resolve(key: str):
    if key.startswith("dyn:"):
        _, alias, sel = key.split(":", 2)
        return resolve_sel(alias, json.loads(sel))
    s = SPEC["keys"][key]
    if "derived" in s:
        return FORM[s["derived"]["formula"]](*[resolve(k) for k in s["derived"]["inputs"]])
    return resolve_sel(s["file"], s)


def check_rows(rows: list[dict]) -> dict:
    res = {"n_values": 0, "n_exact": 0, "n_derived": 0, "n_images": 0, "n_failed": 0,
           "n_source_missing": 0, "failures": []}
    for r in rows:
        if r.get("status") == "SOURCE_MISSING":
            res["n_source_missing"] += 1
            continue
        res["n_values"] += 1
        try:
            if r.get("source_kind") == "image_sha256":
                ok = hashlib.sha256(fpath(r["key"]).read_bytes()).hexdigest() == r["value"]
                res["n_images"] += ok
            else:
                src = resolve(r["key"])
                if r.get("source_kind") == "derived":
                    ok = abs(float(src) - float(r["value"])) <= 1e-12
                    res["n_derived"] += ok
                elif isinstance(src, (int, float)) and not isinstance(src, bool) and \
                        isinstance(r["value"], (int, float)) and not isinstance(r["value"], bool):
                    ok = float(src) == float(r["value"])
                    res["n_exact"] += ok
                else:
                    ok = src == r["value"]
                    res["n_exact"] += ok
                if ok and r.get("format") and r.get("display_string") is not None:
                    ok = format(src, r["format"]) == r["display_string"]
        except (KeyError, IndexError, AssertionError, AttributeError, ValueError, TypeError) as e:
            ok = False
            r = {**r, "error": str(e)}
        if not ok:
            res["n_failed"] += 1
            res["failures"].append({k: r.get(k) for k in ("figure", "panel", "row", "field", "key", "value",
                                                          "display_string", "error")})
    return res


def run_figure(fig_id: str, pv_path: Path | None = None) -> dict:
    pv = pv_path or (WS / "figures" / fig_id / "plotted_values.json")
    if fig_id == "caveats" and pv_path is None:
        pv = WS / "tables" / "caveats_values.json"
    res = check_rows(json.loads(pv.read_text()))
    res["figure"] = fig_id
    return res


def main_for(fig: str) -> int:
    out = run_figure(fig)
    (WS / "results").mkdir(exist_ok=True)
    (WS / "results" / f"check_{fig}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "failures"}), out["failures"][:3])
    return 1 if out["n_failed"] else 0


if __name__ == "__main__":
    sys.exit(main_for(sys.argv[1]))
