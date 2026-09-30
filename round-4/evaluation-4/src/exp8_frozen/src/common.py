"""Shared paths, logging, sealing and small statistics helpers for the RQ2 diffusion experiment.

Dependency roots are resolved relative to this repository (sibling artifacts of the invention loop) and can be
overridden with AII_LOOP_ROOT (= the folder that holds iter_1/, iter_2/, iter_3/). No absolute server path is stored.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
import config as C  # noqa: E402  (vendored iteration-2 config: SPEC, SEALED_IDS, assert_not_sealed, detect_cpus, set_ram_limit)

LOOP = Path(os.environ.get("AII_LOOP_ROOT", ROOT.parents[2])).resolve()
DS5 = LOOP / "round-2" / "." / "dataset-5/src"      # art_eR1Z7fMlOcxs (hydrated concept pool)
X3 = LOOP / "round-2" / "." / "experiment-3/src"    # iteration-2 RQ1 experiment (snapshots, communities, code)
X4 = LOOP / "round-2" / "." / "experiment-4/src"    # iteration-2 MeSH pattern results
X1 = LOOP / "round-2" / "." / "experiment-1/src"    # frozen test population rules
D2 = LOOP / "round-1" / "." / "gen_art_dataset_2"       # legacy-concept levels
MESH = LOOP / "round-1" / "." / "dataset-3/src"     # art_HGiVAYhqO-6q (MeSH held-out set; used via X4 results)

# HELDOUT mode is switched on ONLY by confirm_heldout.py --open-heldout (iteration 4). It redirects every output to
# heldout_run/, relabels held-out concepts as the analysed fold, and scores them against the FROZEN screen references
# (typology medoids + scaling, pct_alt reference arrays, pattern thresholds). Screen outputs are never touched.
HELDOUT = os.environ.get("AII_HELDOUT_OPEN") == "1"
SIMULATE = os.environ.get("AII_HELDOUT_SIMULATE") == "1"   # code-path test: pseudo-held-out = screen concepts, never real ones
MINI = os.environ.get("AII_MINI") == "1"                   # smoke test on 10 old + 10 new screen concepts
if SIMULATE:
    HELDOUT = True
BASE = (ROOT / "heldout_sim" if SIMULATE else ROOT / "heldout_run") if HELDOUT else (ROOT / "mini_run" if MINI else ROOT)
WORK = BASE / "work"
RES = BASE / "results"
FIG = BASE / "figures"
CASES = BASE / "cases"
TYP = BASE / "typology"                 # where typology outputs of THIS run are written / read
TYP_FROZEN = ROOT / "typology"          # frozen screen typology (medoids.json, scaling.json)
RES_SCREEN = ROOT / "results"           # screen results (frozen thresholds for held-out scoring)
SEALED = ROOT / "sealed"
LOGS = BASE / "logs"
for _d in (WORK, RES, FIG, CASES, TYP, SEALED, LOGS, WORK / "attach", WORK / "leiden_seeds"):
    _d.mkdir(parents=True, exist_ok=True)

SNAP_X3 = X3 / "work" / "snapshots"
YEARS = list(range(2000, 2025))
NEW_SEEDS = [101, 102, 103, 104, 105]
S = C.SPEC



def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{name}:{line}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def load_sealed() -> set:
    if HELDOUT and not SIMULATE:  # guard deliberately disabled by the explicit, one-time --open-heldout flag
        return set()
    ids = set(json.loads((WORK / "sealed_ids.json").read_text()))
    C.SEALED_IDS.update(ids)
    return ids


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def clean(o):
    """JSON-safe conversion (NaN -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return None if not math.isfinite(v) else v
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def write_json(p: Path, obj) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(clean(obj), indent=1))


def boot_mean_ci(x, B: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), (B, len(x)))].mean(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return (float(x.mean()), float(lo), float(hi))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Newcombe (1998) hybrid-score CI for p1 - p2 (method 10)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (lo, hi)
