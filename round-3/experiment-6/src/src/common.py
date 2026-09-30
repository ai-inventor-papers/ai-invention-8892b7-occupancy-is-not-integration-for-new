"""Shared paths, the vendored-config shim, the held-out guard, logging and hardware helpers.

Every dependency path is derived from this file's location (<loop>/iter_3/gen_art/<this artifact>), so the
repository works wherever the run tree is mounted; override the loop root with AII_LOOP_ROOT.
The vendored iteration-2 code (vendor/) is imported unchanged; only its output folders and input paths are
re-pointed here. SPEC is never modified (its hash is asserted).
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parents[1]
VENDOR = WS / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

LOOP = Path(os.environ.get("AII_LOOP_ROOT", WS.parents[2])).resolve()
# each dependency artifact can also be pointed at directly (e.g. sibling folders of a published repository)
EXP3 = Path(os.environ.get("AII_EXP3_DIR", LOOP / "round-2" / "." / "experiment-3/src")).resolve()  # art_mbFjmo5rbbf8
DS5 = Path(os.environ.get("AII_DS5_DIR", LOOP / "round-2" / "." / "dataset-5/src")).resolve()      # art_eR1Z7fMlOcxs
EXP1 = Path(os.environ.get("AII_EXP1_DIR", LOOP / "round-2" / "." / "experiment-1/src")).resolve()  # frozen population
DS1 = Path(os.environ.get("AII_DS1_DIR", LOOP / "round-1" / "." / "dataset-1/src")).resolve()      # art_94GEMUsgAmgK

SNAP = EXP3 / "work" / "snapshots"
COMM = EXP3 / "work" / "communities"
RSD = EXP3 / "results" / "concept_subfield" / "rs_distance.parquet"
REF_IND = EXP3 / "results" / "indicators" / "concept_year_indicators.parquet"
EXP3_CP = EXP3 / "work" / "cp.parquet"          # DS1-derived c-papers (code-equality diagnostic)
EXP3_POOL = EXP3 / "work" / "pool.parquet"
HYD = DS5 / "hyd"
TP = EXP1 / "results" / "test_population.json"

WORK = WS / "work"
MINI = os.environ.get("AII_MINI") == "1"   # smoke run: results/figures/sealed go to mini_run/ (work/ is shared, deterministic)
OUT = WS / "mini_run" / "results" if MINI else WS / "results"
FIG = WS / "mini_run" / "figures" if MINI else WS / "figures"
SEALED = WS / "mini_run" / "sealed" if MINI else WS / "sealed"
LOGS = WS / "logs"
for _d in (WORK, OUT, FIG, SEALED, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# ---- vendored config shim (import creates vendor/{work,results,figures,logs}; re-point, then tidy)
import config as C  # noqa: E402

C.WORK, C.OUT, C.FIG = WORK, OUT, FIG
C.D1, C.D2 = HYD, DS5 / "deps" / "gen_art_dataset_2"
for _d in ("work", "results", "figures", "logs"):
    _p = VENDOR / _d
    try:  # spawned workers import this concurrently: tolerate a sibling removing the folder first
        if _p.is_dir() and not any(_p.iterdir()):
            shutil.rmtree(_p, ignore_errors=True)
    except OSError:
        pass

SPEC_SHA = "2e4c4894393b256e79c242dc834f736f67b292acac656d413fc8e152bc002614"
assert C.spec_hash() == SPEC_SHA, "vendored SPEC changed"
assert json.loads((VENDOR / "spec.json").read_text())["sha256"] == SPEC_SHA
SPEC = C.SPEC

# analysis window (screen): t in [F+3, F+8], t <= 2015 so that W2 = [t+1, t+5] ends by 2020
T_MAX_SCREEN = 2015
AGES = (3, 8)
MINI_N = 20


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{name}:{line}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def set_ram_limit(gb: float) -> None:
    C.set_ram_limit(gb)


def detect_cpus() -> int:
    return C.detect_cpus()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=_json_default))


def _json_default(o):
    import numpy as np
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


# ---- held-out guard ------------------------------------------------------------------------------------------
GUARD_CALLS = {"n": 0}


def load_sealed_ids() -> set[str]:
    p = OUT / "population" / "sealed_ids.json"
    if p.exists():
        ids = set(json.loads(p.read_text()))
        C.SEALED_IDS.update(ids)
        return ids
    return set()


def assert_not_sealed(ids, focal_years=()) -> None:
    GUARD_CALLS["n"] += 1
    C.assert_not_sealed(ids, focal_years)


def outcome_fn(f):
    """Decorator for every function that touches post-t (W2) data: f(cid, t, ...) is refused for sealed ids/years."""
    @functools.wraps(f)
    def wrap(cid, t, *a, **k):
        assert_not_sealed([cid], [t])
        return f(cid, t, *a, **k)
    wrap.__outcome_fn__ = True
    return wrap
