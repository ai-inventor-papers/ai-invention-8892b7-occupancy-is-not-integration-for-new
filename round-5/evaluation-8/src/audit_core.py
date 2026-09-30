#!/usr/bin/env python3
"""Core of the numbers-of-record audit: report parsing, the frozen match rule,
source loading by (path, key) and a per-artifact numeric index for auto-location.

Everything here is READ-ONLY on the run volume. Paths in outputs are always
relative to the run root (RUN_ROOT), never absolute.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

RUN_ROOT = Path(os.environ.get("AII_RUN_ROOT", str(Path(__file__).resolve().parents[4])))  # run root: this folder is <run>/3_invention_loop/iter_5/gen_art/<artifact>
REPORT_REL = "3_invention_loop/iter_5/gen_strat/current_report.md"
HYPO_REL = "3_invention_loop/iter_4/upd_hypo/upd_hypo/.terminal_claude_agent_struct_out.json"

# artifact id -> workspace (run-root-relative). Taken from the report's own
# 'Source:' lines and [ARTIFACT:] markers, checked against the directory layout.
ARTIFACTS: dict[str, str] = {
    "art_94GEMUsgAmgK": "round-1/dataset-1/src",
    "iter1_dataset_2": "3_invention_loop/iter_1/gen_art/gen_art_dataset_2",
    "art_HGiVAYhqO-6q": "round-1/dataset-3/src",
    "art_QpM5SM6a7SH6": "round-1/dataset-4/src",
    "art_bNCGUJX2MUhX": "round-1/research-1/src",
    "art_eR1Z7fMlOcxs": "round-2/dataset-5/src",
    "art_BdBvbNuNU8E7": "round-2/experiment-1/src",
    "art_yjFB8Spw2w6M": "round-2/experiment-2/src",
    "art_mbFjmo5rbbf8": "round-2/experiment-3/src",
    "art_yWUkgWWKyq_h": "round-2/experiment-4/src",
    "art__i2cIye01VnN": "round-3/evaluation-1/src",
    "art_htO_gJuUn6Pr": "round-3/experiment-5/src",
    "art_62TVG6A4f7Iy": "round-3/experiment-6/src",
    "art_2Cd2JJypeGuA": "round-3/experiment-7/src",
    "art_QKsLguxnGFQT": "round-3/experiment-8/src",
    "art_WZ8fbLn79nCq": "round-4/evaluation-2/src",
    "art_zw_JJGsUFSnd": "round-4/evaluation-3/src",
    "art_mu0h0npvNX_u": "round-4/evaluation-4/src",
    "art_FZ2OCJwV6xHs": "round-4/evaluation-5/src",
    "art_XGdzjWgi-a88": "round-4/experiment-9/src",
}
PATH_TO_ART = {v: k for k, v in ARTIFACTS.items()}

# ---------------------------------------------------------------- flags / rule
FLAGS = ["OK", "DRIFT_VALUE", "WRONG_ESTIMATOR", "WRONG_DEFINITION", "WRONG_FOLD",
         "NOT_TRACEABLE", "VERDICT_DRIFT", "MISSING_IN_REPORT"]
MATCH_RULE = {
    "counts_and_n_G": "exact equality after removing thousands separators",
    "continuous_and_ci_bounds": "|source - reported| <= 0.5 * 10^-d (+1e-9), d = decimals shown in the report; "
                                 "percentages compare source*100 at the shown decimals",
    "p_values": "equal after rounding the source to the reported significant figures (or 'p < x' holds), AND same side "
                "of 0.05, AND same side of the Holm threshold when one is attached to the claim",
    "verdicts": "the verdict string must equal the one the decision rule gives on the source numbers",
    "ci_structure": "a reported 'x [lo, hi]' must satisfy lo <= hi and lo <= x <= hi at the shown precision",
}
FLAG_DEFS = {
    "OK": "value/verdict matches its intended source under the match rule",
    "DRIFT_VALUE": "a source exists for the intended quantity but the reported value differs and matches no alternative",
    "WRONG_ESTIMATOR": "the number is real but comes from a different estimator/spec/model than the one the text names",
    "WRONG_DEFINITION": "the number or sentence is real but is given a wrong meaning (e.g. OR read as a risk ratio)",
    "WRONG_FOLD": "screen number labelled held-out (or the reverse), or MeSH/main mixed",
    "NOT_TRACEABLE": "no file contains the number; a replacement value is given or the number is dropped",
    "VERDICT_DRIFT": "the verdict stated differs from what the frozen decision rule gives on the source numbers",
    "MISSING_IN_REPORT": "a number of record (hypothesis evidence list / artifact output) that the report never states",
}

NUM_RE = re.compile(r"(?<![\w.\^])([−\-+]?)(\d[\d,]*(?:\.\d+)?|\.\d+)(?:\s?[×x]\s?10\^?([−\-]?\d+)|e([−\-]?\d+))?(%?)(?![\w])")
MINUS = str.maketrans({"−": "-", "–": "-", "‑": "-"})


@dataclass
class Reported:
    """A reported number as written, with its precision."""
    text: str
    value: float
    decimals: int
    sig: int
    is_pct: bool
    is_sci: bool
    lt: bool = False  # 'p < x'


def parse_reported(s: str) -> Reported | None:
    """Parse '1,544', '−0.391', '26%', '9.7e-5', '1e-5', '< 0.001', '1.4e-13'."""
    t = s.strip().translate(MINUS).replace(" ", "").replace(" ", "")
    lt = False
    if t.startswith("<"):
        lt, t = True, t[1:]
    if t.startswith("≤"):
        lt, t = True, t[1:]
    is_pct = t.endswith("%")
    t = t.rstrip("%")
    m = re.fullmatch(r"([+\-]?)(\d[\d,]*(?:\.\d+)?|\.\d+)(?:e([+\-]?\d+)|[×x]10\^?([+\-]?\d+))?", t)
    if not m:
        return None
    sign, mant, e1, e2 = m.groups()
    mant_clean = mant.replace(",", "")
    exp = e1 or e2
    val = float(mant_clean) * (10 ** int(exp) if exp else 1.0)
    if sign == "-":
        val = -val
    dec = len(mant_clean.split(".")[1]) if "." in mant_clean else 0
    digits = mant_clean.replace(".", "").lstrip("0")
    sig = max(1, len(digits))
    if exp:
        dec = dec - int(exp)
    return Reported(text=s.strip(), value=val, decimals=dec, sig=sig, is_pct=is_pct, is_sci=bool(exp), lt=lt)


def round_sig(x: float, sig: int) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    return round(x, sig - int(math.floor(math.log10(abs(x)))) - 1)


def match_value(rep: Reported, src: float, kind: str = "cont", holm_threshold: float | None = None,
                sign_mode: str = "signed") -> bool:
    """Frozen match rule (see MATCH_RULE)."""
    if src is None or (isinstance(src, float) and not math.isfinite(src)):
        return False
    src = float(src)
    rv = rep.value
    if sign_mode == "abs":
        src, rv = abs(src), abs(rv)
    if kind == "count":
        return abs(src - rv) < 1e-9
    if kind == "pct":  # source is a fraction, report in percent
        src = src * 100.0
        return abs(src - rv) <= 0.5 * 10 ** (-rep.decimals) + 1e-9
    if kind == "p":
        if rep.lt:
            ok = src < rv + 1e-15
        elif rep.is_sci or rv < 0.001:
            ok = abs(round_sig(src, rep.sig) - rv) <= 1e-12 * max(1.0, abs(rv)) or \
                abs(src - rv) <= 0.5 * 10 ** (-rep.decimals) + 1e-15
        else:
            ok = abs(src - rv) <= 0.5 * 10 ** (-rep.decimals) + 1e-12 or abs(round_sig(src, rep.sig) - rv) < 1e-12
        same_side = (src < 0.05) == (rv < 0.05) or rep.lt
        if holm_threshold is not None:
            same_side = same_side and ((src < holm_threshold) == (rv < holm_threshold) or rep.lt)
        return ok and same_side
    # continuous
    return abs(src - rv) <= 0.5 * 10 ** (-rep.decimals) + 1e-9


# ---------------------------------------------------------------- source access
@lru_cache(maxsize=512)
def load_json(rel: str) -> Any:
    return json.loads((RUN_ROOT / rel).read_text())


@lru_cache(maxsize=512)
def load_csv(rel: str) -> list[dict]:
    with open(RUN_ROOT / rel, newline="") as fh:
        return list(csv.DictReader(fh))


def _num(v: Any) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return v
    return v


def get_by_key(rel: str, key: str) -> Any:
    """key syntax: JSON 'a/b/0/c'; CSV 'csv:col=v;col2=v2|target'; CSV count 'csv:col=v|#count'."""
    if key.startswith("csv:"):
        cond, target = key[4:].rsplit("|", 1)
        rows = load_csv(rel)
        conds = [c.split("=", 1) for c in cond.split(";") if c]
        hit = [r for r in rows if all(str(r.get(c, "")).strip() == v for c, v in conds)]
        if target == "#count":
            return float(len(hit))
        if not hit:
            raise KeyError(f"no CSV row {cond} in {rel}")
        return _num(hit[0][target])
    obj = load_json(rel)
    for part in [p for p in key.split("/") if p != ""]:
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return _num(obj)


def read_source(spec: str) -> Any:
    rel, key = spec.split("::", 1)
    return get_by_key(rel, key)


def file_sha256(rel: str) -> str:
    import hashlib
    return hashlib.sha256((RUN_ROOT / rel).read_bytes()).hexdigest()


# ---------------------------------------------------------------- report parsing
def read_report(path: Path | None = None) -> list[str]:
    p = path or (RUN_ROOT / REPORT_REL)
    return p.read_text().split("\n")


@dataclass
class Token:
    line: int  # 1-based
    col: int
    text: str
    rep: Reported
    kind: str  # 'year', 'ref', 'num'
    section: str = ""


YEAR_OK = range(1985, 2031)


def tokenize_line(text: str, lineno: int) -> list[Token]:
    toks: list[Token] = []
    if re.match(r"^\[\d+\]\s", text):  # reference list entries
        return toks
    for m in NUM_RE.finditer(text):
        sign, mant, e_x, e_e, pct = m.groups()
        s = (sign or "") + mant + (f"e{(e_x or e_e)}" if (e_x or e_e) else "") + (pct or "")
        rep = parse_reported(s)
        if rep is None:
            continue
        start = m.start()
        before = text[max(0, start - 12):start]
        after = text[m.end():m.end() + 3]
        kind = "num"
        if re.search(r"\[$", before) and after.startswith("]") and "." not in mant and "," not in text[m.end():m.end() + 1]:
            kind = "ref"
        elif re.search(r"(Table|Artifact|Iteration|iteration|Figure|activity|Activity|F\d|M|m|R|E|S|G|W|k|C|D|H|Y)\s?$", before) and "." not in mant and not pct:
            # 'Table 16', 'Artifact 12', 'M3', 'R1', 'E4', 'G2', 'W2', 'Y3' identifiers
            kind = "label" if re.search(r"(Table|Artifact|Iteration|iteration|Figure|activity|Activity)\s$", before) or re.search(r"[A-Za-z]$", before) else "num"
        if kind == "num" and "." not in mant and "," not in mant and not pct and rep.value in YEAR_OK and not sign:
            kind = "year"
        if kind == "num" and re.search(r"(sha|SHA|hash|\.\.\.)", text[max(0, start - 30):m.end() + 6]) and re.search(r"[0-9a-f]{6,}", text[max(0, start - 10):m.end() + 10]):
            kind = "hash"
        toks.append(Token(line=lineno, col=start, text=s, rep=rep, kind=kind))
    return toks


def sections(lines: list[str]) -> list[tuple[int, int, str]]:
    """(start, end, heading) 1-based inclusive ranges for '#'/'##'/'###' headings."""
    heads = [(i + 1, l.strip("# ").strip()) for i, l in enumerate(lines) if l.startswith("#")]
    out = []
    for j, (s, h) in enumerate(heads):
        e = heads[j + 1][0] - 1 if j + 1 < len(heads) else len(lines)
        out.append((s, e, h))
    return out


def iteration_of_line(lines: list[str], lineno: int) -> int:
    it = 0
    for i in range(lineno):
        m = re.match(r"^# Iteration (\d)", lines[i])
        if m:
            it = int(m.group(1))
    return it


# ---------------------------------------------------------------- numeric index
SKIP_DIRS = {".venv", "cache", "__pycache__", "node_modules", ".git", "hf_cache", "mini_run", "sealed", "models",
             "dryrun_synthetic", "mini", "smoke", "deps_run", "exp8_frozen", "d2", "vendor", "logs", "nativeness",
             "frames", "gate", "data", "hyd"}
MAX_FILE = 4_000_000


def _flatten(o: Any, prefix: str, out_v: list, out_c: list, cap: int) -> None:
    if len(out_v) >= cap:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            _flatten(v, f"{prefix}/{k}", out_v, out_c, cap)
    elif isinstance(o, list):
        for i, v in enumerate(o[:5000]):
            _flatten(v, f"{prefix}/{i}", out_v, out_c, cap)
    elif isinstance(o, bool):
        return
    elif isinstance(o, (int, float)):
        if math.isfinite(o):
            out_v.append(float(o))
            out_c.append(prefix)
    elif isinstance(o, str):
        try:
            f = float(o)
            if math.isfinite(f):
                out_v.append(f)
                out_c.append(prefix)
        except ValueError:
            for m in re.finditer(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w])", o[:4000]):
                out_v.append(float(m.group(0)))
                out_c.append(prefix + "#text")


@dataclass
class ArtifactIndex:
    art: str
    values: np.ndarray
    contexts: list[str]
    order: np.ndarray = field(default=None)  # type: ignore
    n_files: int = 0

    def __post_init__(self):
        self.order = np.argsort(self.values)
        self.sorted = self.values[self.order]

    def candidates(self, lo: float, hi: float, limit: int = 400) -> list[int]:
        a = np.searchsorted(self.sorted, lo, side="left")
        b = np.searchsorted(self.sorted, hi, side="right")
        return [int(self.order[i]) for i in range(a, min(b, a + limit))]


def build_index(art: str, cap: int = 1_500_000) -> ArtifactIndex:
    root = RUN_ROOT / ARTIFACTS[art]
    vals: list[float] = []
    ctx: list[str] = []
    nfiles = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(fns):
            if fn.startswith((".", "mini_", "preview_", "full_")):
                continue
            if not fn.endswith((".json", ".csv", ".md")):
                continue
            p = Path(dp) / fn
            try:
                if p.stat().st_size > MAX_FILE:
                    continue
                rel = str(p.relative_to(RUN_ROOT))
                if fn.endswith(".json"):
                    _flatten(json.loads(p.read_text()), rel + "::", vals, ctx, cap)
                elif fn.endswith(".csv"):
                    with open(p, newline="") as fh:
                        rdr = csv.reader(fh)
                        header = next(rdr, [])
                        for ri, row in enumerate(rdr):
                            if len(vals) >= cap or ri > 20000:
                                break
                            label = " ".join(c for c in row[:3] if c and not re.fullmatch(r"-?[\d.e+-]+", c))
                            for ci, c in enumerate(row):
                                try:
                                    f = float(c)
                                except ValueError:
                                    continue
                                if math.isfinite(f):
                                    vals.append(f)
                                    ctx.append(f"{rel}::row{ri}:{label}|{header[ci] if ci < len(header) else ci}")
                else:  # markdown: numbers in prose/tables of artifact READMEs
                    txt = p.read_text(errors="ignore")[:400000]
                    for m in re.finditer(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?(?![\w])", txt.replace("−", "-")):
                        try:
                            vals.append(float(m.group(0).replace(",", "")))
                            ctx.append(f"{rel}::md")
                        except ValueError:
                            pass
                nfiles += 1
            except (OSError, json.JSONDecodeError, UnicodeDecodeError, csv.Error):
                continue
            if len(vals) >= cap:
                break
    return ArtifactIndex(art=art, values=np.array(vals, dtype=float), contexts=ctx, n_files=nfiles)


def locate(token: Reported, indexes: list[ArtifactIndex], cap: int = 50) -> list[str]:
    """Return contexts of source values matching a reported token under the match rule (no semantics)."""
    tol = 0.5 * 10 ** (-token.decimals) + 1e-9
    targets = [token.value]
    if token.is_pct:
        targets = [token.value / 100.0, token.value]
        tol_list = [0.5 * 10 ** (-(token.decimals + 2)) + 1e-12, tol]
    else:
        tol_list = [tol]
    hits: list[str] = []
    for ix in indexes:
        for t, tl in zip(targets, tol_list):
            for sign in ([1.0, -1.0] if t != 0 else [1.0]):
                tt = sign * t
                for i in ix.candidates(tt - tl, tt + tl, limit=cap):
                    hits.append(ix.contexts[i])
                    if len(hits) > cap:
                        return hits
    return hits
