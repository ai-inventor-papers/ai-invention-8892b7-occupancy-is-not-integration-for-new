"""Shared paths, logging, JSON helpers and small statistics for the iteration-3 evaluation.

All iteration-2 inputs are READ-ONLY. Every path written into a published file is made relative to RUN_ROOT.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
from pathlib import Path

import numpy as np
from loguru import logger

sys.dont_write_bytecode = True  # never write __pycache__ into the read-only iteration-2 folders we import from
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

WS = Path(__file__).resolve().parent
# Run layout: <run>/3_invention_loop/iter_3/gen_art/<this folder>. Every input is located relative to this file.
# Overrides (paths may be relative to this folder):
#   AII_RUN_ROOT   the run root (default: four levels above this folder)
#   AII_DEPS_ROOT  folder holding the iteration-2 artifact folders gen_art_experiment_1..4 and gen_art_dataset_5
#                  (default: <run>/3_invention_loop/iter_2/gen_art); use it when they are published as sibling folders.
RUN_ROOT = (WS / os.environ["AII_RUN_ROOT"]).resolve() if os.environ.get("AII_RUN_ROOT") else WS.parents[3]
IT2 = (WS / os.environ["AII_DEPS_ROOT"]).resolve() if os.environ.get("AII_DEPS_ROOT") else RUN_ROOT / "." / "round-2" / "."
E1 = IT2 / "gen_art_experiment_1"
E2 = IT2 / "gen_art_experiment_2"
E3 = IT2 / "gen_art_experiment_3"
E4 = IT2 / "gen_art_experiment_4"
D5 = IT2 / "gen_art_dataset_5"
D1_IT1 = RUN_ROOT / "." / "round-1" / "." / "gen_art_dataset_1"
REPORT = RUN_ROOT / "." / "round-3" / "gen_strat" / "current_report.md"
RES = WS / "results"
R1A = RES / "r1a"
for _d in (RES, R1A, WS / "logs"):
    _d.mkdir(parents=True, exist_ok=True)

HEADER = "PRE-CHECK ON ALREADY-SCREENED DATA; NOT CONFIRMATION; E_up promoted post hoc"
ART_IDS = {"exp_1": "art_BdBvbNuNU8E7", "exp_2": "art_yjFB8Spw2w6M", "exp_3": "art_mbFjmo5rbbf8",
           "exp_4": "art_yWUkgWWKyq_h", "dataset_5": "art_eR1Z7fMlOcxs"}


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(WS / "logs" / f"{name}.log", rotation="30 MB", level="DEBUG")


def set_ram_limit(gb: float = 16) -> None:
    b = int(gb * 1024 ** 3)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        b = min(b, hard)  # an already-capped process can only lower its limit
    resource.setrlimit(resource.RLIMIT_AS, (b, hard if hard != resource.RLIM_INFINITY else b))


def rel(p: Path | str) -> str:
    """Run-root-relative POSIX path (never absolute in published outputs)."""
    p = Path(p).resolve()
    try:
        return p.relative_to(RUN_ROOT).as_posix()
    except ValueError:
        return p.name


def clean(x):
    """JSON-safe conversion (NaN/inf -> None, numpy -> python)."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return None if not math.isfinite(v) else v
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    return x


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(obj), indent=1, allow_nan=False))


def load_json(p: Path):
    return json.loads(Path(p).read_text())


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def import_from(dirpath: Path, *modules: str) -> list:
    """Import modules from a read-only dependency folder (bytecode writing disabled)."""
    import importlib
    sys.path.insert(0, str(dirpath))
    try:
        return [importlib.import_module(m) for m in modules]
    finally:
        sys.path.remove(str(dirpath))


# ------------------------------------------------------------------ meta-analysis helpers
def ivw(y: list[float], se: list[float]) -> dict:
    """Fixed-effect inverse-variance pooling, Cochran Q, I^2 with Q-profile CI (k small => very imprecise)."""
    from scipy import optimize, stats
    y, se = np.asarray(y, float), np.asarray(se, float)
    w = 1 / se ** 2
    mu = float((w * y).sum() / w.sum())
    se_mu = float(1 / math.sqrt(w.sum()))
    Q = float((w * (y - mu) ** 2).sum())
    k = len(y)
    df = k - 1
    pQ = float(stats.chi2.sf(Q, df)) if df > 0 else float("nan")
    I2 = max(0.0, (Q - df) / Q) if Q > 0 else 0.0
    s2 = df * w.sum() / (w.sum() ** 2 - (w ** 2).sum())  # Higgins-Thompson typical within-study variance

    def qgen(t2: float) -> float:
        ww = 1 / (se ** 2 + t2)
        m = (ww * y).sum() / ww.sum()
        return float((ww * (y - m) ** 2).sum())

    def solve(target: float) -> float:
        if qgen(0.0) <= target:
            return 0.0
        hi = 1.0
        while qgen(hi) > target:
            hi *= 10
            if hi > 1e8:
                return float("nan")
        return float(optimize.brentq(lambda t: qgen(t) - target, 0.0, hi))

    t2_lo = solve(stats.chi2.ppf(0.975, df))
    t2_hi = solve(stats.chi2.ppf(0.025, df))
    i2 = lambda t: t / (t + s2) if np.isfinite(t) else float("nan")  # noqa: E731
    return dict(k=k, S_ivw=mu, se_ivw=se_mu, ci=[mu - 1.96 * se_mu, mu + 1.96 * se_mu],
                z=mu / se_mu, p=float(2 * stats.norm.sf(abs(mu / se_mu))), Q=Q, df=df, p_Q=pQ, I2=I2,
                I2_ci_qprofile=[i2(t2_lo), i2(t2_hi)], tau2_ci_qprofile=[t2_lo, t2_hi],
                note="Cochran Q has very low power at k = 2; a non-significant Q is NOT evidence of homogeneity; "
                     "I^2 CI via Q-profile tau^2 bounds mapped with the Higgins-Thompson typical variance.")
