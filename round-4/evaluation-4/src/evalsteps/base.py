"""Shared paths, frozen-code imports and inference helpers for the evaluation steps."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WS = Path(__file__).resolve().parents[1]
LOOP = Path(os.environ.get("AII_LOOP_ROOT", WS.parents[2])).resolve()  # dependency artifacts: <LOOP>/iter_N/gen_art/<artifact>
os.environ.setdefault("AII_LOOP_ROOT", str(LOOP))
E8 = WS / "exp8_frozen"
HO = E8 / "heldout_run"
E7 = LOOP / "iter_3/gen_art/gen_art_experiment_7"
E4 = LOOP / "iter_2/gen_art/gen_art_experiment_4"
MESH_DS = LOOP / "iter_1/gen_art/gen_art_dataset_3"
RES = WS / "results"
FIG = WS / "figures"
for p in (str(E8 / "src"), str(E8 / "vendor"), str(WS / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

BROAD = "broad from the start (rapid interdisciplinary)"
LOCAL = "localised"
TYPE_SHORT = {BROAD: "BROAD", LOCAL: "LOCALISED"}
Z = 1.959964


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clean(o):
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
    if o is pd.NA or o is pd.NaT:
        return None
    return o


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(clean(obj), indent=1, default=str))


def wilson(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def newcombe(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Newcombe hybrid-score CI for p1 - p2."""
    if n1 == 0 or n2 == 0:
        return dict(diff=None, ci=[None, None])
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return dict(diff=d, ci=[lo, hi])


def share(k: int, n: int) -> dict:
    return dict(k=int(k), n=int(n), share=(k / n) if n else None, wilson_ci=wilson(int(k), int(n)))


def cluster_boot(df: pd.DataFrame, stat, cluster: str = "concept_id", B: int = 2000, seed: int = 0) -> dict:
    """Concept-cluster bootstrap of stat(df) -> float."""
    groups = {c: g for c, g in df.groupby(cluster)}
    keys = list(groups)
    obs = stat(df)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(B):
        pick = rng.integers(0, len(keys), len(keys))
        d = pd.concat([groups[keys[i]] for i in pick], ignore_index=True)
        v = stat(d)
        if v is not None and np.isfinite(v):
            draws.append(v)
    ci = np.percentile(draws, [2.5, 97.5]).tolist() if draws else [None, None]
    return dict(est=obs, ci=ci, B=B, n_clusters=len(keys), n_rows=len(df))


def cluster_boot_many(df: pd.DataFrame, stats: dict, cluster: str = "concept_id", B: int = 2000, seed: int = 0) -> dict:
    """Same resamples for several statistics (faster, index-based)."""
    codes, uniq = pd.factorize(df[cluster])
    idx_by = [np.flatnonzero(codes == i) for i in range(len(uniq))]
    rng = np.random.default_rng(seed)
    obs = {k: f(df) for k, f in stats.items()}
    draws = {k: [] for k in stats}
    for _ in range(B):
        pick = rng.integers(0, len(uniq), len(uniq))
        rows = np.concatenate([idx_by[i] for i in pick])
        d = df.iloc[rows]
        for k, f in stats.items():
            v = f(d)
            if v is not None and np.isfinite(v):
                draws[k].append(v)
    return {k: dict(est=obs[k], ci=(np.percentile(draws[k], [2.5, 97.5]).tolist() if draws[k] else [None, None]),
                    B=B, n_clusters=len(uniq), n_rows=len(df)) for k in stats}


def holm(pvals: dict) -> dict:
    items = [(k, v) for k, v in pvals.items() if v is not None and np.isfinite(v)]
    items.sort(key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def cramers_v_boot(a: pd.Series, b: pd.Series, B: int = 1000, seed: int = 0) -> list:
    m = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    ai = pd.factorize(m.a.astype(str), sort=True)[0]
    bi = pd.factorize(m.b.astype(str), sort=True)[0]
    rng = np.random.default_rng(seed)
    vs = []
    for _ in range(B):
        ix = rng.integers(0, len(m), len(m))
        x, y = ai[ix], bi[ix]
        ka, kb = len(set(x)), len(set(y))
        if ka < 2 or kb < 2:
            continue
        tab = pd.crosstab(x, y).to_numpy().astype(float)
        e = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
        chi = ((tab - e) ** 2 / e).sum()
        vs.append(math.sqrt(chi / (tab.sum() * (min(tab.shape) - 1))))
    return np.percentile(vs, [2.5, 97.5]).tolist() if vs else [None, None]
