"""Shared paths, loaders and the reproduction gate for the adopter-level mechanism evaluation.

The exp_7 (art_2Cd2JJypeGuA) source is vendored byte-identical under vendor/ (see vendor/SHA256SUMS). Because the
vendored config derives WS from its own location (vendor/..), every cache/result/log it writes lands in THIS workspace.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "vendor"))

import config  # noqa: E402  (vendored)
import io_load  # noqa: E402
import models  # noqa: E402
import ppml  # noqa: E402

LOOP = config.LOOP
EXP7 = LOOP / "round-3" / "." / "gen_art_experiment_7"
D5 = config.D5
RESULTS = WS / "results"
FRAMES = WS / "frames"
FIGS = WS / "figures"
LOGS = WS / "logs"
for _d in (RESULTS, FRAMES, FIGS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)
SEED = 20260929
LABEL = "screen-fold mechanism evidence, not confirmation"

CTRL = models.EVENT_CONTROLS + models.SECONDARY_EXTRA
XVARS = [models.A_VAR, models.CT_VAR] + CTRL
TARGET = {"b_A": 4.7391, "N": 1544, "G": 140}


def sha256_file(p: Path) -> str:
    return config.sha256_file(Path(p))


def vendor_check() -> dict:
    out = {}
    for line in (WS / "vendor" / "SHA256SUMS").read_text().splitlines():
        h, name = line.split()
        out[name] = sha256_file(WS / "vendor" / name) == h
    if not all(out.values()):
        raise RuntimeError(f"vendored source changed: {out}")
    return out


def load_screen() -> pd.DataFrame:
    return pd.read_parquet(EXP7 / "results" / "screen_events_with_outcomes.parquet")


def coprimary_sample(df: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """exp_7 co-primary sample (screen MAIN kw5, complete controls) and its retained rows after PPML pruning."""
    s = models.primary_sample(load_screen() if df is None else df)
    r = ppml.fit(s.Y_strict.to_numpy(float), s[XVARS].to_numpy(float), models.fe_arrays(s, "secondary"),
                 s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    s["retained"] = r["keep"]
    return s, r


def reproduction_gate() -> dict:
    s, _ = coprimary_sample()
    fit = models.fit_one(s, "Y_strict", XVARS, "secondary")
    b = fit["coef"][models.A_VAR]
    res = {"b_A": b, "N": fit["n_retained"], "G": fit["G"], "irr_sd": fit["irr_sd"][models.A_VAR],
           "ci_irr_sd": fit["ci_irr_sd"][models.A_VAR], "p": fit["p"][models.A_VAR], "target": TARGET,
           "pass": bool(abs(b - TARGET["b_A"]) < 1e-4 and fit["n_retained"] == TARGET["N"] and fit["G"] == TARGET["G"])}
    return res


def author_raw_ids() -> np.ndarray:
    """Dense author index -> raw OpenAlex author integer (same np.unique order as io_load.prepare)."""
    p = config.CACHE / "author_raw_ids.npy"
    if p.exists():
        return np.load(p)
    import pyarrow.parquet as pq
    parts = sorted((D5 / "hyd" / "works").glob("works_part_*.parquet"))
    arrs = []
    for f in parts:
        t = pq.read_table(f, columns=["author_ids"]).to_pandas()
        arrs.append(np.concatenate([np.asarray(x, np.int64) for x in t.author_ids if x is not None and len(x)]))
    uniq = np.unique(np.concatenate(arrs))
    np.save(p, uniq)
    return uniq


def dump(obj, p: Path) -> None:
    Path(p).write_text(json.dumps(obj, indent=1, default=_default))


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)
