"""Source registry: the ONLY way plot code obtains a number.

Every value is addressed by (file alias, selector). File aliases live in sources.yaml with the
producing artifact id and a run-root-relative path. Selectors:
  json_pointer  RFC 6901 pointer into a JSON file
  csv_row       {filters: {col: value}, column: col}   (exactly one matching row required)
  md_regex      regex with one capture group applied to a text/markdown file
  json_regex    pointer to a string inside JSON + regex with one capture group
  derived       {formula: name, inputs: [key, ...]} computed by a whitelisted formula
The sha256 of each file is recorded at first read; a change during the run raises.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import yaml

WS = Path(__file__).resolve().parents[1]
# Workspace = <run_root>/3_invention_loop/iter_5/gen_art/<this artifact>; override with AII_RUN_ROOT.
RUN_ROOT = Path(os.environ.get("AII_RUN_ROOT", WS.parents[3])).resolve()

FORMULAS = {
    # name: (description, function)
    "lin_lo": ("x - 1.96*se", lambda x, se: x - 1.96 * se),
    "lin_hi": ("x + 1.96*se", lambda x, se: x + 1.96 * se),
    "exp_lo": ("exp(b - 1.96*se)", lambda b, se: math.exp(b - 1.96 * se)),
    "exp_hi": ("exp(b + 1.96*se)", lambda b, se: math.exp(b + 1.96 * se)),
    "neg": ("-x", lambda x: -x),
    "diff": ("a - b", lambda a, b: a - b),
    "pct": ("100*x", lambda x: 100.0 * x),
}


class SourceMissing(Exception):
    pass


def json_pointer(doc: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return doc
    cur = doc
    for raw in pointer.lstrip("/").split("/"):
        tok = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            cur = cur[int(tok)]
        elif isinstance(cur, dict):
            if tok not in cur:
                raise SourceMissing(f"pointer {pointer}: key {tok!r} not found")
            cur = cur[tok]
        else:
            raise SourceMissing(f"pointer {pointer}: cannot descend into {type(cur).__name__}")
    return cur


def esc(tok: str) -> str:
    return tok.replace("~", "~0").replace("/", "~1")


def _num(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return v
    return v


class Registry:
    def __init__(self, sources_yaml: Path = WS / "sources.yaml", overrides: dict | None = None):
        spec = yaml.safe_load(sources_yaml.read_text())
        self.files: dict = spec["files"]
        self.keys: dict = spec["keys"]
        self.overrides = overrides or {}  # alias -> absolute path (used only by the mutation self-test)
        self.hashes: dict[str, str] = {}
        self._cache: dict[str, Any] = {}
        self.missing: list[dict] = []

    # ---------- files ----------
    def path(self, alias: str) -> Path:
        if alias in self.overrides:
            return Path(self.overrides[alias])
        return RUN_ROOT / self.files[alias]["path"]

    def _load(self, alias: str) -> tuple[Any, str]:
        if alias not in self.files:
            raise KeyError(f"unknown file alias {alias}")
        p = self.path(alias)
        if not p.exists():
            raise SourceMissing(f"file missing: {self.files[alias]['path']}")
        data = p.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        if alias in self.hashes and self.hashes[alias] != h:
            raise RuntimeError(f"source {alias} changed during the run")
        self.hashes[alias] = h
        if alias not in self._cache:
            kind = self.files[alias].get("kind") or Path(p).suffix.lstrip(".")
            if kind == "json":
                self._cache[alias] = json.loads(data)
            elif kind == "csv":
                self._cache[alias] = list(csv.DictReader(data.decode().splitlines()))
            elif kind in ("png", "jpg", "pdf"):
                self._cache[alias] = None
            else:
                self._cache[alias] = data.decode()
        return self._cache[alias], h

    def sha256(self, alias: str) -> str:
        self._load(alias)
        return self.hashes[alias]

    # ---------- selectors ----------
    def select(self, alias: str, sel: dict) -> Any:
        doc, _ = self._load(alias)
        if "json_pointer" in sel:
            return json_pointer(doc, sel["json_pointer"])
        if "csv_row" in sel:
            flt = sel["csv_row"]["filters"]
            rows = [r for r in doc if all(str(r.get(k)) == str(v) for k, v in flt.items())]
            if len(rows) != 1:
                raise SourceMissing(f"csv_row {flt}: {len(rows)} matching rows in {alias}")
            col = sel["csv_row"]["column"]
            if col not in rows[0]:
                raise SourceMissing(f"csv column {col} not in {alias}")
            v = rows[0][col]
            if v == "":
                raise SourceMissing(f"csv cell {flt}/{col} empty in {alias}")
            return _num(v)
        if "csv_count" in sel:
            c = sel["csv_count"]
            n = 0
            for r in doc:
                if not all(str(r.get(k)) == str(v) for k, v in c.get("filters", {}).items()):
                    continue
                if any(re.search(rx, str(r.get(k, ""))) for k, rx in c.get("exclude_regex", {}).items()):
                    continue
                if not all(r.get(k, "") != "" and float(r[k]) < t for k, t in c.get("lt", {}).items()):
                    continue
                if not all(r.get(k, "") != "" and float(r[k]) > t for k, t in c.get("gt", {}).items()):
                    continue
                n += 1
            return float(n)
        if "md_regex" in sel:
            m = re.search(sel["md_regex"], doc, flags=re.S)
            if not m:
                raise SourceMissing(f"md_regex not matched in {alias}")
            return _num(m.group(1))
        if "json_regex" in sel:
            s = json_pointer(doc, sel["json_regex"]["pointer"])
            if isinstance(s, list):
                s = " || ".join(map(str, s))
            m = re.search(sel["json_regex"]["regex"], str(s), flags=re.S)
            if not m:
                raise SourceMissing(f"json_regex not matched in {alias}")
            return _num(m.group(1))
        if "exists" in sel:
            return 1.0 if self.path(alias).exists() else 0.0
        raise ValueError(f"unknown selector {sel}")

    def spec(self, key: str) -> dict:
        if key not in self.keys:
            raise KeyError(f"registry key {key} not declared in sources.yaml")
        return self.keys[key]

    def get(self, key: str) -> Any:
        s = self.spec(key)
        if "derived" in s:
            name = s["derived"]["formula"]
            args = [self.get(k) for k in s["derived"]["inputs"]]
            return FORMULAS[name][1](*args)
        return self.select(s["file"], s)

    def meta(self, key: str) -> dict:
        s = self.spec(key)
        if "derived" in s:
            ins = s["derived"]["inputs"]
            return {"source_kind": "derived", "formula": FORMULAS[s["derived"]["formula"]][0],
                    "inputs": ins, "artifact_id": self.meta(ins[0])["artifact_id"],
                    "path": self.meta(ins[0])["path"], "sha256": self.meta(ins[0])["sha256"],
                    "fold_label": s.get("fold_label", ""), "ci_type": s.get("ci_type", "")}
        f = self.files[s["file"]]
        sel = {k: v for k, v in s.items() if k in ("json_pointer", "csv_row", "csv_count", "md_regex",
                                                    "json_regex", "exists")}
        return {"source_kind": "pass_through", "artifact_id": f["artifact"], "path": f["path"],
                "selector": sel, "sha256": self.sha256(s["file"]),
                "fold_label": s.get("fold_label", ""), "ci_type": s.get("ci_type", "")}

    def dyn(self, alias: str, sel: dict, fold_label: str = "DESCRIPTIVE", ci_type: str = "") -> str:
        """Declare (at run time) a key for a structure-enumerated value, e.g. one subfield share of one case.
        The key string encodes alias + selector, so the independent checker can re-resolve it."""
        key = "dyn:" + alias + ":" + json.dumps(sel, sort_keys=True)
        if key not in self.keys:
            self.keys[key] = {"file": alias, **sel, "fold_label": fold_label, "ci_type": ci_type}
        return key

    def structure(self, alias: str) -> Any:
        """Parsed file for enumerating structure (which keys/rows exist); values must still go through get()."""
        return self._load(alias)[0]

    def try_get(self, key: str) -> Any | None:
        try:
            return self.get(key)
        except (SourceMissing, KeyError, IndexError, ValueError) as e:
            self.missing.append({"key": key, "error": str(e)})
            return None


class Recorder:
    """Records every value handed to matplotlib, with its source, for plotted_values.json (M1)."""

    def __init__(self, reg: Registry, figure: str):
        self.reg, self.figure, self.rows, self.labels = reg, figure, [], []

    def label(self, row: str, shown: str, record_key: str | None = None, *, panel: str = "") -> None:
        """M6: the fold label printed for a row, plus the record's label for that row where one exists."""
        rec_label = self.reg.try_get(record_key) if record_key else None
        self.labels.append({"figure": self.figure, "panel": panel, "row": row, "shown": shown,
                            "record_key": record_key, "record_label": rec_label})

    def v(self, key: str, *, panel: str, row: str, field: str, fmt: str | None = None) -> Any:
        val = self.reg.try_get(key)
        if val is None:
            self.rows.append({"figure": self.figure, "panel": panel, "row": row, "field": field,
                              "key": key, "value": None, "display_string": "n/a - source missing",
                              "format": fmt, "status": "SOURCE_MISSING"})
            return None
        disp = None
        if fmt is not None and isinstance(val, (int, float)):
            disp = format(val, fmt)
        m = self.reg.meta(key)
        self.rows.append({"figure": self.figure, "panel": panel, "row": row, "field": field, "key": key,
                          "value": val, "display_string": disp, "format": fmt, "status": "OK", **m})
        return val

    def s(self, key: str, fmt: str, **kw) -> str:
        """Value rendered as text (annotation); returns the display string."""
        val = self.v(key, fmt=fmt, **kw)
        return "n/a - source missing" if val is None else format(val, fmt)

    def raw(self, key: str, **kw) -> Any:
        return self.v(key, fmt=None, **kw)

    def image(self, alias: str, *, panel: str, row: str) -> Path | None:
        p = self.reg.path(alias)
        if not p.exists():
            self.rows.append({"figure": self.figure, "panel": panel, "row": row, "field": "image",
                              "key": alias, "value": None, "status": "SOURCE_MISSING"})
            return None
        f = self.reg.files[alias]
        self.rows.append({"figure": self.figure, "panel": panel, "row": row, "field": "image", "key": alias,
                          "value": self.reg.sha256(alias), "display_string": None, "format": None,
                          "status": "OK", "source_kind": "image_sha256", "artifact_id": f["artifact"],
                          "path": f["path"], "sha256": self.reg.sha256(alias), "fold_label": "DESCRIPTIVE",
                          "ci_type": ""})
        return p

    def dump(self, out: Path) -> None:
        out.write_text(json.dumps(self.rows, indent=1, default=str))
