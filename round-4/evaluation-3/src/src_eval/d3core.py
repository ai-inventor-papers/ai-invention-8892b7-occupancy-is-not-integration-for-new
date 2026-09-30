"""D3 building blocks: concept-level exposure X (early closure), outcome Y (later host-entry anchoring), covariates and
the partial-Spearman statistics (concept bootstrap, Freedman-Lane permutation, Bonett-Wright MDE).

Only W1 quantities are read: exp_6 openness rows (t <= 2015) and exp_7 event-level features (pre-entry partner host
share A_cont). The held-out parquet files are read only after their .sha256 sidecars are verified (verify_sealed).
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

WS = Path(__file__).resolve().parents[1]
LOOP = WS.parents[2]
EXP5C = WS / "deps_run" / "exp5"                      # byte copy (population, labels)
EXP6 = LOOP / "round-3" / "." / "experiment-6/src"   # read-only originals
EXP7 = LOOP / "round-3" / "." / "experiment-7/src"
DS5 = LOOP / "round-2" / "." / "dataset-5/src"

LADDER = {  # level: (min age, max age, min entry lag e - F, Y source)
    "L1": (3, 5, 6, "events"),
    "L2": (3, 4, 5, "events"),
    "L3": (3, 3, 4, "events"),
    "L4": (3, 5, None, "exported"),
}
ORIGIN_MAP = {"F31": "Physics&Astronomy", "F17": "Computer Science", "F25": "Materials/Chem/Eng",
              "F16": "Materials/Chem/Eng", "F22": "Materials/Chem/Eng", "F15": "Materials/Chem/Eng",
              "F26": "Mathematics"}
MAX_T = 2015


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sealed(p: Path) -> str:
    side = p.with_suffix(".sha256")
    exp = side.read_text().split()[0].strip()
    got = sha(p)
    if got != exp:
        raise RuntimeError(f"sealed file hash mismatch: {p.name} {got[:12]} != {exp[:12]}")
    return got


# ----------------------------------------------------------------------------- inputs
def population() -> pd.DataFrame:
    p = pd.read_parquet(EXP5C / "work" / "population.parquet")
    p = p[p.arm == "main"].copy()
    p["origin5"] = [ORIGIN_MAP.get(str(g).split(":")[0], "Other") for g in p.origin_group]
    return p[["concept_id", "fold", "MAIN", "F", "origin_group", "origin5", "route", "old_new"]]


def openness(fold: str) -> pd.DataFrame:
    if fold == "screen":
        o = pd.read_parquet(EXP6 / "results" / "openness" / "openness_ct.parquet")
    else:
        f = EXP6 / "sealed" / "openness_ct_heldout.parquet"
        verify_sealed(f)
        o = pd.read_parquet(f)
    return o[o.t <= MAX_T]


def events(fold: str) -> pd.DataFrame:
    if fold == "screen":
        f = EXP7 / "results" / "features_screen.parquet"
    else:
        f = EXP7 / "sealed" / "heldout_features.parquet"
        verify_sealed(f)
    cols = ["concept_id", "arm", "d", "e", "F", "kw5", "MAIN", "A_cont", "A_cont_ex"]
    ev = pd.read_parquet(f, columns=cols)
    return ev[(ev.arm == "main")]


def exported(fold: str) -> pd.DataFrame:
    if fold == "screen":
        return pd.read_parquet(EXP7 / "results" / "d3_concept_anchoring.parquet")
    f = EXP7 / "sealed" / "d3_concept_anchoring_heldout.parquet"
    verify_sealed(f)
    return pd.read_parquet(f)


def early_volume(ids: set, F: dict) -> pd.Series:
    """log1p(mean yearly all-type c-papers over F..F+5) from dataset_5 links x works publication year (exp_5 vol rule)."""
    links = pd.read_parquet(DS5 / "hyd" / "concept_work.parquet", columns=["concept_id", "work_id"])
    links = links[links.concept_id.isin(ids)]
    wids = set(links.work_id)
    yrs = []
    for f in sorted((DS5 / "hyd" / "works").glob("works_part_*.parquet")):
        w = pd.read_parquet(f, columns=["work_id", "publication_year"])
        yrs.append(w[w.work_id.isin(wids)])
    cp = links.merge(pd.concat(yrs, ignore_index=True), on="work_id", how="inner")
    cp["year"] = cp.publication_year.astype(int)
    cp["F"] = cp.concept_id.map(F)
    cp = cp[(cp.year >= cp.F) & (cp.year <= cp.F + 5)]
    cnt = cp.groupby("concept_id").size()
    out = pd.Series({c: math.log1p(cnt.get(c, 0) / 6.0) for c in ids}, name="log_vol_early")
    return out


# ----------------------------------------------------------------------------- concept frame
def exposure(o: pd.DataFrame, pop: pd.DataFrame, col: str, a0: int, a1: int, onset: dict | None = None) -> pd.DataFrame:
    d = o.merge(pop[["concept_id", "F"]], on="concept_id", how="inner")
    d["age_F"] = d.t - d.F
    d = d[(d.age_F >= a0) & (d.age_F <= a1) & np.isfinite(d[col].astype(float))]
    if onset:
        d = d[[not (c in onset and t >= onset[c]) for c, t in zip(d.concept_id, d.t)]]
    g = d.groupby("concept_id")
    return pd.DataFrame({"X": g[col].mean(), "n_X_years": g[col].size()})


def h_end(o: pd.DataFrame, pop: pd.DataFrame, a0: int, a1: int) -> pd.Series:
    d = o.merge(pop[["concept_id", "F"]], on="concept_id", how="inner")
    d["age_F"] = d.t - d.F
    d = d[(d.age_F >= a0) & (d.age_F <= a1) & np.isfinite(d.H_W1.astype(float))].sort_values("t")
    return d.groupby("concept_id").H_W1.last().rename("H_end")


def outcome(ev: pd.DataFrame, pop: pd.DataFrame, lag: int | None, median_A: float | None = None,
            col: str = "A_cont") -> pd.DataFrame:
    d = ev.merge(pop[["concept_id", "F"]].rename(columns={"F": "F_pop"}), on="concept_id", how="inner")
    d = d[d.kw5.astype(bool) & np.isfinite(d[col].astype(float))]
    if lag is not None:
        d = d[d.e >= d.F_pop + lag]
    g = d.groupby("concept_id")
    out = pd.DataFrame({"Y": g[col].mean(), "n_events": g[col].size()})
    if median_A is not None:
        out["Y2"] = g["A_cont"].apply(lambda s: float((s > median_A).mean()))
    return out


def origin_dummies(groups: pd.Series, min_n: int = 5) -> tuple[pd.DataFrame, pd.Series]:
    g = groups.copy()
    vc = g.value_counts()
    small = [k for k, v in vc.items() if v < min_n]
    g[g.isin(small)] = "Other"
    vc = g.value_counts()
    if "Other" in vc and vc["Other"] < min_n and len(vc) > 1:  # merged Other still tiny -> fold into largest group
        g[g == "Other"] = vc.index[0]
    levels = sorted(g.unique())
    ref = g.value_counts().index[0]
    D = pd.DataFrame({f"og_{lv}": (g == lv).astype(float) for lv in levels if lv != ref}, index=g.index)
    return D, g


# ----------------------------------------------------------------------------- statistics
def avg_rank(x: np.ndarray) -> np.ndarray:
    return stats.rankdata(x, method="average")


def design(Z: np.ndarray | None, n: int) -> np.ndarray:
    one = np.ones((n, 1))
    return one if Z is None or Z.shape[1] == 0 else np.column_stack([one, Z])


def resid(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(a @ a) * float(b @ b))
    return float(a @ b / den) if den > 0 else np.nan


def prep_Z(Zraw: pd.DataFrame, rank_cols: list[str]) -> np.ndarray:
    Z = Zraw.copy()
    for c in rank_cols:
        Z[c] = avg_rank(Z[c].values.astype(float))
    return Z.values.astype(float)


def partial_spearman(x: np.ndarray, y: np.ndarray, Zraw: pd.DataFrame | None, rank_cols: list[str]) -> float:
    n = len(x)
    rx, ry = avg_rank(x), avg_rank(y)
    if Zraw is None or Zraw.shape[1] == 0:
        return _corr(rx, ry)
    X = design(prep_Z(Zraw, rank_cols), n)
    return _corr(resid(rx, X), resid(ry, X))


def boot_ci(x, y, Zraw, rank_cols, B: int, seed: int) -> dict:
    """Concept bootstrap; ranks and covariate residualisation recomputed inside each draw. Percentile + BCa."""
    rng = np.random.default_rng(seed)
    n = len(x)
    est = partial_spearman(x, y, Zraw, rank_cols)
    draws = np.full(B, np.nan)
    for b in range(B):
        idx = rng.integers(0, n, n)
        Zb = None if Zraw is None else Zraw.iloc[idx].reset_index(drop=True)
        if Zb is not None:  # drop dummy columns that are constant in the draw (collinear with intercept)
            keep = [c for c in Zb.columns if c in rank_cols or Zb[c].nunique() > 1]
            Zb = Zb[keep]
        draws[b] = partial_spearman(x[idx], y[idx], Zb, [c for c in rank_cols if Zb is None or c in Zb.columns])
    d = draws[np.isfinite(draws)]
    pct = [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]
    # BCa
    try:
        z0 = stats.norm.ppf((d < est).mean() + 0.5 * (d == est).mean())
        jk = np.array([partial_spearman(np.delete(x, i), np.delete(y, i),
                                        None if Zraw is None else Zraw.drop(index=Zraw.index[i]).reset_index(drop=True),
                                        rank_cols) for i in range(n)])
        jm = jk.mean()
        a = float(((jm - jk) ** 3).sum() / (6 * (((jm - jk) ** 2).sum()) ** 1.5))
        qs = []
        for al in (0.025, 0.975):
            za = stats.norm.ppf(al)
            qs.append(float(np.quantile(d, stats.norm.cdf(z0 + (z0 + za) / (1 - a * (z0 + za))))))
        bca = qs
    except (ValueError, FloatingPointError, ZeroDivisionError):
        bca = [np.nan, np.nan]
    return dict(rho=est, ci=pct, ci_bca=bca, se_boot=float(d.std(ddof=1)), n_valid_draws=int(len(d)))


def freedman_lane(x, y, Zraw, rank_cols, n_perm: int, seed: int) -> dict:
    """One-sided (rho < 0) Freedman-Lane permutation: permute the X-residuals of the reduced model (X on covariates),
    rebuild X* = fitted + permuted residuals, re-residualise X* on the covariates and correlate with the Y-residuals."""
    n = len(x)
    rx, ry = avg_rank(x), avg_rank(y)
    X = design(None if Zraw is None or Zraw.shape[1] == 0 else prep_Z(Zraw, rank_cols), n)
    Q, _ = np.linalg.qr(X)
    ex, ey = resid(rx, X), resid(ry, X)
    fx = rx - ex
    obs = _corr(ex, ey)
    rng = np.random.default_rng(seed)
    perm = np.empty(n_perm)
    eyc = ey - ey.mean()
    for s0 in range(0, n_perm, 1000):
        m = min(1000, n_perm - s0)
        P = np.stack([ex[rng.permutation(n)] for _ in range(m)], axis=1)  # n x m
        XS = fx[:, None] + P
        R = XS - Q @ (Q.T @ XS)
        R = R - R.mean(0, keepdims=True)
        perm[s0:s0 + m] = (eyc @ R) / np.sqrt((R * R).sum(0) * float(eyc @ eyc))
    p_lo = (1 + int((perm <= obs).sum())) / (n_perm + 1)
    p_hi = (1 + int((perm >= obs).sum())) / (n_perm + 1)
    p_two = (1 + int((np.abs(perm) >= abs(obs)).sum())) / (n_perm + 1)
    return dict(rho_obs=obs, p_one_neg=p_lo, p_one_pos=p_hi, p_two=p_two, n_perm=n_perm,
                perm_mean=float(perm.mean()), perm_sd=float(perm.std(ddof=1)))


def mde_rho(n: int, k: int) -> float:
    dfree = n - 3 - k
    return float(math.tanh((1.645 + 0.842) * math.sqrt(1.06 / dfree))) if dfree > 0 else np.nan


def power_rho(rho: float, n: int, k: int) -> float:
    dfree = n - 3 - k
    if dfree <= 0:
        return np.nan
    return float(stats.norm.cdf(abs(math.atanh(rho)) / math.sqrt(1.06 / dfree) - 1.645))
