"""Shared library for the iteration-5 K1 / K3 / INFERENCE evaluation (post-confirmation exploratory).

Imports the vendored, byte-exact D2 stack (d2/src: models, ppml; MeSH sample() from mesh/src/models_mesh) WITHOUT
editing it. Everything new lives here: fold loaders, a cached-projection LPM with HDFE, an FE-logit (IRLS with
weighted within-transformation), PPML wrappers, the Webb-weight wild cluster score bootstrap, the randomization
engines (plain within-concept shuffle and Freedman-Lane), a concept-cluster bootstrap helper and IVW pooling.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # one BLAS thread per worker process
    os.environ[_v] = "1"
import resource
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse, stats
from scipy.sparse.linalg import splu

WS = Path(__file__).resolve().parents[1]
os.environ.setdefault("AII_DEPS_ROOT", str(WS.parents[2]))
for _p in (WS / "d2" / "src", WS / "mesh" / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import models  # noqa: E402  (vendored d2/src/models.py, unchanged)
import ppml  # noqa: E402    (vendored d2/src/ppml.py, unchanged)

RESULTS = WS / "results"
LOGS = WS / "logs"
INPUTS = WS / "inputs"
FIGS = WS / "figures"
SPEC_PATH = RESULTS / "k13_spec.json"
SPEC_HASH_PATH = RESULTS / "k13_spec.sha256"
for _d in (RESULTS, LOGS, FIGS):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 20261001
CTRL2 = models.EVENT_CONTROLS + models.SECONDARY_EXTRA
FOLDS = ("SCREEN", "HELDOUT", "MESH")
LOOP_REL = "3_invention_loop"
SRC_MAIN = {"SCREEN": "art_WZ8fbLn79nCq:results/g_features_screen_coprimary.parquet",
            "HELDOUT": "art_WZ8fbLn79nCq:results/g_features_heldout_coprimary.parquet",
            "MESH": "art_XGdzjWgi-a88:results/outcomes_mesh.parquet"}
FIELD_OF_GROUP = {31: "Physics/Astro", 17: "CS"}
GROUPS = ("Physics/Astro", "CS", "other")


# ---------------------------------------------------------------------------------------------------- hardware
def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def container_ram_bytes() -> int:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v)
        except (FileNotFoundError, ValueError):
            pass
    import psutil
    return int(psutil.virtual_memory().total)


def n_workers() -> int:
    return max(1, detect_cpus() - 1)


def set_worker_ram_limit(frac_total: float = 0.70) -> None:
    """Per-process address-space cap: 70% of container RAM split over the worker processes (x3 virtual headroom
    is NOT applied: numpy/scipy virtual reservations are small here; cap stays well below physical)."""
    per = int(container_ram_bytes() * frac_total)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (per, per))
    except (ValueError, OSError):
        pass


def set_main_ram_limit(frac_total: float = 0.70) -> None:
    ram = container_ram_bytes()
    lim = int(ram * frac_total)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
    except (ValueError, OSError):
        pass


# ---------------------------------------------------------------------------------------------------- utilities
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=_json_default))


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def clean(x):
    """Recursively replace NaN / inf with None so the JSON is strict."""
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def assert_spec_hash() -> str:
    """Every run script calls this first: the frozen spec must hash to the recorded value."""
    want = SPEC_HASH_PATH.read_text().split()[0]
    got = sha256_file(SPEC_PATH)
    if want != got:
        raise RuntimeError(f"k13_spec.json hash mismatch: recorded {want}, file {got}")
    return got


def rel(p: Path | str) -> str:
    """Path relative to the run root (…/run_xxx) for source columns; never an absolute server path."""
    p = Path(p).resolve()
    root = WS.parents[3]
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------------------------------- loaders
def add_outcomes(s: pd.DataFrame) -> pd.DataFrame:
    s = s.copy()
    y = s["Y_strict"].astype(float)
    s["Any"] = (y >= 1).astype(float)
    s["Y_ge3"] = (y >= 3).astype(float)
    s["Y_ge5"] = (y >= 5).astype(float)
    s["EST_bin"] = s["EST_bin"].astype(float)
    s["log_nep"] = np.log(s["n_entry_papers"].astype(float))
    return s


def load_fold(fold: str) -> pd.DataFrame:
    """Frozen per-event sample of a fold with the co-primary FE columns (cfe/efe/dfe, cxe/dxe) and offset.
    SCREEN/HELDOUT: models.primary_sample (arm main, fold, kw5, MAIN, complete A_cont/CT/CTRL2) exactly as
    audit/audit_perm.py filters. MESH: models_mesh.sample(outcomes_mesh, [A_cont, CT] + secondary_controls)."""
    if fold == "SCREEN":
        s = models.primary_sample(pd.read_parquet(INPUTS / "g_features_screen_coprimary.parquet"), fold="screen")
    elif fold == "HELDOUT":
        s = models.primary_sample(pd.read_parquet(INPUTS / "g_features_heldout_coprimary.parquet"), fold="heldout")
    elif fold == "MESH":
        import models_mesh
        sc = mesh_controls()
        s = models_mesh.sample(pd.read_parquet(INPUTS / "outcomes_mesh.parquet"), ["A_cont", "CT"] + sc)
    else:
        raise ValueError(fold)
    s = add_outcomes(s)
    s["fold"] = fold
    return s.reset_index(drop=True)


def mesh_controls() -> list[str]:
    return json.loads((WS / "mesh" / "results" / "mesh_spec.json").read_text())["models"]["secondary_controls"]


def controls(fold: str) -> list[str]:
    return mesh_controls() if fold == "MESH" else CTRL2


def fe_cols_for(fe: str) -> list[str]:
    return {"coprimary": ["cfe", "efe", "dfe"], "primary": ["cxe", "dxe"], "k3": ["cfe", "fxe", "dfe"]}[fe]


def load_pooled_k3() -> pd.DataFrame:
    """Union of the frozen SCREEN and HELDOUT samples with fold x e FE (K3)."""
    a, b = load_fold("SCREEN"), load_fold("HELDOUT")
    s = pd.concat([a, b], ignore_index=True)
    s["cfe"] = pd.factorize(s.concept_id)[0]
    s["fxe"] = pd.factorize(s.fold + "_" + s.e.astype(str))[0]
    s["dfe"] = pd.factorize(s.d.astype(str))[0]
    s["host_group"] = s.field_d.map(lambda v: FIELD_OF_GROUP.get(int(v), "other") if pd.notna(v) else "other")
    s["origin_group"] = s["field_group"].astype(str)
    return s


# ---------------------------------------------------------------------------------------------------- pruning
def prune_singletons(fes: list[np.ndarray]) -> np.ndarray:
    """Iterated singleton pruning (LPM / binary models: no separation rule)."""
    keep = np.ones(len(fes[0]), bool)
    for _ in range(100):
        changed = False
        for f in fes:
            cnt = np.bincount(f[keep], minlength=f.max() + 1)
            drop = keep & (cnt[f] <= 1)
            if drop.any():
                keep &= ~drop
                changed = True
        if not changed:
            break
    return keep


def prune_binary_separation(y: np.ndarray, fes: list[np.ndarray]) -> np.ndarray:
    """Iterated pruning for FE-logit: singleton levels and levels whose outcome is all-0 or all-1."""
    keep = np.ones(len(y), bool)
    for _ in range(100):
        changed = False
        for f in fes:
            cnt = np.bincount(f[keep], minlength=f.max() + 1)
            sy = np.bincount(f[keep], weights=y[keep], minlength=f.max() + 1)
            bad = (cnt <= 1) | (sy <= 0) | (sy >= cnt)
            drop = keep & bad[f]
            if drop.any():
                keep &= ~drop
                changed = True
        if not changed:
            break
    return keep


def _relabel(fes: list[np.ndarray], keep: np.ndarray) -> list[np.ndarray]:
    return [np.unique(f[keep], return_inverse=True)[1] for f in fes]


def _dummy(fes: list[np.ndarray]) -> sparse.csc_matrix:
    n = len(fes[0])
    rows, cols, off = [], [], 0
    for f in fes:
        rows.append(np.arange(n))
        cols.append(f + off)
        off += int(f.max()) + 1
    return sparse.csc_matrix((np.ones(n * len(fes)), (np.concatenate(rows), np.concatenate(cols))), shape=(n, off))


def ssc_adj(n: int, kx: int, fes: list[np.ndarray], g: np.ndarray) -> float:
    """pyfixest CRV1 small-sample factor with fixef_k='nested' (identical rule to vendored ppml.fit)."""
    G = int(g.max()) + 1
    k_fe = 0
    for f in fes:
        if not (ppml.pd_nunique_per_level(f, g) <= 1):
            k_fe += int(f.max())
    k = kx + k_fe + (1 if k_fe else 0)
    return G / (G - 1) * (n - 1) / (n - k) if G > 1 and n > k else 1.0


# ---------------------------------------------------------------------------------------------------- LPM
class LPM:
    """OLS with HDFE by exact projection. The retained sample (iterated singleton pruning) depends only on the FE
    structure, so the projector is factorised ONCE and reused for every outcome / permuted regressor."""

    def __init__(self, fes: list[np.ndarray], cluster: np.ndarray):
        self.keep = prune_singletons(fes)
        self.fes = _relabel(fes, self.keep)
        self.D = _dummy(self.fes)
        A = sparse.csc_matrix(self.D.T @ self.D) + sparse.identity(self.D.shape[1], format="csc") * 1e-9
        self.lu = splu(A)
        self.g = np.unique(cluster[self.keep], return_inverse=True)[1]
        self.G = int(self.g.max()) + 1
        self.n = int(self.keep.sum())

    def __getstate__(self):  # SuperLU is not picklable: refactorise in the worker
        st = dict(self.__dict__)
        st.pop("lu", None)
        return st

    def __setstate__(self, st):
        self.__dict__.update(st)
        A = sparse.csc_matrix(self.D.T @ self.D) + sparse.identity(self.D.shape[1], format="csc") * 1e-9
        self.lu = splu(A)

    def demean(self, M: np.ndarray) -> np.ndarray:
        M = np.asarray(M, float)
        return M - self.D @ self.lu.solve(np.asarray(self.D.T @ M))

    def fit(self, y: np.ndarray, X: np.ndarray, Xt: np.ndarray | None = None) -> dict:
        """y, X on the FULL input sample (keep applied here); Xt optional pre-demeaned X on the kept sample."""
        yk = np.asarray(y, float)[self.keep]
        if Xt is None:
            Xt = self.demean(np.asarray(X, float)[self.keep])
        yt = self.demean(yk[:, None])[:, 0]
        XtX = Xt.T @ Xt
        beta = np.linalg.solve(XtX, Xt.T @ yt)
        e = yt - Xt @ beta
        Hi = np.linalg.inv(XtX)
        S = np.zeros((self.G, Xt.shape[1]))
        np.add.at(S, self.g, Xt * e[:, None])
        adj = ssc_adj(self.n, Xt.shape[1], self.fes, self.g)
        V = adj * Hi @ (S.T @ S) @ Hi
        return {"coef": beta, "se": np.sqrt(np.diag(V)), "V": V, "n": self.n, "G": self.G, "resid": e, "Xt": Xt,
                "yt": yt}


def lpm_row(s: pd.DataFrame, y: str, xvars: list[str], fe: str, target: str = "A_cont") -> dict:
    fes = [s[c].to_numpy() for c in fe_cols_for(fe)]
    eng = LPM(fes, s.concept_id.to_numpy())
    r = eng.fit(s[y].to_numpy(float), s[xvars].to_numpy(float))
    j = xvars.index(target)
    b, se = float(r["coef"][j]), float(r["se"][j])
    sd = float(s.loc[eng.keep, target].std())
    G = r["G"]
    tq = stats.t.ppf(0.975, G - 1)
    base = float(s.loc[eng.keep, y].mean())
    return {"model": "LPM", "y": y, "fe": fe, "b": b, "se": se, "t": b / se, "p_crv1": float(2 * stats.t.sf(abs(b / se), G - 1)),
            "sd": sd, "pp_per_sd": 100 * b * sd, "ci_pp_per_sd": [100 * (b - tq * se) * sd, 100 * (b + tq * se) * sd],
            "base_rate": base, "rel_to_base": (b * sd) / base if base > 0 else None,
            "N": r["n"], "N_input": int(len(s)), "G": G, "retained_share": r["n"] / len(s)}


# ---------------------------------------------------------------------------------------------------- FE logit
def logit_fe_fit(y: np.ndarray, X: np.ndarray, fes: list[np.ndarray], cluster: np.ndarray, maxit: int = 200,
                 tol: float = 1e-10) -> dict | None:
    """Unconditional FE logit by IRLS with a weighted within-transformation (exact sparse projection, as vendored
    ppml.fit does for the log link). FE levels with all-0 / all-1 outcomes and singletons are pruned (iterated)."""
    keep = prune_binary_separation(y.astype(float), fes)
    if keep.sum() < X.shape[1] + 5:
        return None
    yk, Xk, cl = y[keep].astype(float), X[keep].astype(float), cluster[keep]
    fk = _relabel(fes, keep)
    p = np.clip(0.5 * np.ones_like(yk) * 0 + (yk + 0.5) / 2, 0.05, 0.95)
    eta = np.log(p / (1 - p))
    dev_old = np.inf
    beta = np.zeros(Xk.shape[1])
    for _ in range(maxit):
        w = p * (1 - p)
        z = eta + (yk - p) / w
        M = ppml._demean(np.column_stack([z, Xk]), w, fk)
        zt, Xt = M[:, 0], M[:, 1:]
        WX = Xt * w[:, None]
        beta = np.linalg.solve(Xt.T @ WX, WX.T @ zt)
        resid = zt - Xt @ beta
        eta = np.clip(z - resid, -30, 30)
        p = 1 / (1 + np.exp(-eta))
        p = np.clip(p, 1e-12, 1 - 1e-12)
        dev = -2 * np.sum(yk * np.log(p) + (1 - yk) * np.log(1 - p))
        if abs(dev - dev_old) / (abs(dev) + 0.1) < tol:
            break
        dev_old = dev
    w = p * (1 - p)
    Xt = ppml._demean(Xk, w, fk)
    Hi = np.linalg.inv(Xt.T @ (Xt * w[:, None]))
    g = np.unique(cl, return_inverse=True)[1]
    G = int(g.max()) + 1
    S = np.zeros((G, Xk.shape[1]))
    np.add.at(S, g, Xt * (yk - p)[:, None])
    adj = ssc_adj(len(yk), Xk.shape[1], fk, g)
    V = adj * Hi @ (S.T @ S) @ Hi
    return {"coef": beta, "se": np.sqrt(np.diag(V)), "n": int(len(yk)), "G": G, "keep": keep}


def logit_row(s: pd.DataFrame, y: str, xvars: list[str], fe: str, target: str = "A_cont") -> dict:
    fes = [s[c].to_numpy() for c in fe_cols_for(fe)]
    r = logit_fe_fit(s[y].to_numpy(float), s[xvars].to_numpy(float), fes, s.concept_id.to_numpy())
    if r is None:
        return {"model": "FE-logit", "y": y, "fe": fe, "status": "not estimable (too few events after pruning)"}
    j = xvars.index(target)
    b, se = float(r["coef"][j]), float(r["se"][j])
    sd = float(s.loc[r["keep"], target].std())
    tq = stats.t.ppf(0.975, r["G"] - 1)
    conc_all = s.concept_id.nunique()
    conc_kept = s.loc[r["keep"], "concept_id"].nunique()
    return {"model": "FE-logit", "y": y, "fe": fe, "b": b, "se": se, "t": b / se,
            "p_crv1": float(2 * stats.t.sf(abs(b / se), r["G"] - 1)), "sd": sd, "or_per_sd": math.exp(b * sd),
            "ci_or_per_sd": [math.exp((b - tq * se) * sd), math.exp((b + tq * se) * sd)], "N": r["n"],
            "N_input": int(len(s)), "G": r["G"], "concepts_dropped_all0_all1_or_singleton": int(conc_all - conc_kept),
            "retained_share": r["n"] / len(s), "status": "ok"}


# ---------------------------------------------------------------------------------------------------- PPML
def ppml_fit(s: pd.DataFrame, y: str, xvars: list[str], fe: str, offset: bool = True, A: np.ndarray | None = None,
             target: str = "A_cont", yv: np.ndarray | None = None) -> dict | None:
    """Vendored ppml.fit (unchanged). A overrides the target column (randomization draws); yv overrides y."""
    X = s[xvars].to_numpy(float)
    j = xvars.index(target)
    if A is not None:
        X = X.copy()
        X[:, j] = A
    fes = [s[c].to_numpy() for c in fe_cols_for(fe)]
    yy = s[y].to_numpy(float) if yv is None else np.asarray(yv, float)
    off = s["offset"].to_numpy() if offset else np.zeros(len(s))
    try:
        r = ppml.fit(yy, X, fes, off, s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    except (np.linalg.LinAlgError, ValueError, RuntimeError, FloatingPointError):
        return None
    if r is None:
        return None
    b, se = float(r["coef"][j]), float(r["se"][j])
    if not (np.isfinite(b) and np.isfinite(se)) or se <= 0:
        return None
    return {"b": b, "se": se, "t": b / se, "n": r["n"], "G": r["G"], "keep": r["keep"], "coef": r["coef"],
            "se_all": r["se"], "mu": r["mu"], "Xt": r["Xt"], "y": r["y"], "cl": r["cl"]}


def ppml_row(s: pd.DataFrame, y: str, xvars: list[str], fe: str, offset: bool = True, target: str = "A_cont",
             label: str = "") -> dict:
    r = ppml_fit(s, y, xvars, fe, offset=offset, target=target)
    if r is None:
        return {"model": "PPML", "y": y, "fe": fe, "status": "not estimable", "label": label}
    sd = float(s.loc[r["keep"], target].std())
    G = r["G"]
    tq = stats.t.ppf(0.975, G - 1)
    b, se = r["b"], r["se"]
    return {"model": "PPML", "y": y, "fe": fe, "offset": offset, "b": b, "se": se, "t": b / se,
            "p_crv1": float(2 * stats.t.sf(abs(b / se), G - 1)), "sd": sd, "irr_per_sd": math.exp(b * sd),
            "ci_irr_per_sd": [math.exp((b - tq * se) * sd), math.exp((b + tq * se) * sd)], "N": r["n"],
            "N_input": int(len(s)), "G": G, "retained_share": r["n"] / len(s), "status": "ok", "label": label}


# ---------------------------------------------------------------------------------------------------- wild bootstrap
WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])


def score_components_ppml(s: pd.DataFrame, y: str, xvars: list[str], fe: str, target: str = "A_cont",
                          offset: bool = True) -> np.ndarray | None:
    """Cluster scores of the target under the restricted (b_target = 0) PPML fit, target partialled on the
    restricted design with the restricted weights -- identical construction to vendored ppml.wild_score_test."""
    j = xvars.index(target)
    X = s[xvars].to_numpy(float)
    Xr, x2 = np.delete(X, j, axis=1), X[:, j]
    fes = [s[c].to_numpy() for c in fe_cols_for(fe)]
    off = s["offset"].to_numpy() if offset else np.zeros(len(s))
    r = ppml.fit(s[y].to_numpy(float), Xr, fes, off, s.concept_id.to_numpy())
    if r is None:
        return None
    keep, mu = r["keep"], r["mu"]
    fk = _relabel(fes, keep)
    D = ppml._demean(np.column_stack([x2[keep], Xr[keep]]), mu, fk)
    x2t, Xrt = D[:, 0], D[:, 1:]
    b = np.linalg.solve(Xrt.T @ (Xrt * mu[:, None]), (Xrt * mu[:, None]).T @ x2t)
    x2r = x2t - Xrt @ b
    return np.bincount(r["cl"], weights=x2r * (r["y"] - mu))


def score_components_lpm(s: pd.DataFrame, y: str, xvars: list[str], fe: str, target: str = "A_cont") -> np.ndarray:
    """Linear analogue: restricted OLS residuals times the target partialled on the restricted design (HDFE)."""
    j = xvars.index(target)
    fes = [s[c].to_numpy() for c in fe_cols_for(fe)]
    eng = LPM(fes, s.concept_id.to_numpy())
    X = s[xvars].to_numpy(float)[eng.keep]
    M = eng.demean(np.column_stack([s[y].to_numpy(float)[eng.keep], X]))
    yt, Xt = M[:, 0], M[:, 1:]
    Xrt, x2t = np.delete(Xt, j, axis=1), Xt[:, j]
    br = np.linalg.lstsq(Xrt, yt, rcond=None)[0]
    er = yt - Xrt @ br
    x2r = x2t - Xrt @ np.linalg.lstsq(Xrt, x2t, rcond=None)[0]
    return np.bincount(eng.g, weights=x2r * er)


def wild_score_test_webb(sc: np.ndarray | None, rng: np.random.Generator, reps: int = 9999,
                         weights: str = "webb", chunk: int = 2000) -> dict | None:
    """Kline-Santos score bootstrap statistic T = (sum s_g)^2 / sum s_g^2 with Webb 6-point (default) or Rademacher
    cluster weights. Mirrors ppml.wild_score_test; returns p and the number of clusters."""
    if sc is None or len(sc) < 2 or (sc ** 2).sum() == 0:
        return None
    T = sc.sum() ** 2 / (sc ** 2).sum()
    ge = 0
    done = 0
    while done < reps:
        m = min(chunk, reps - done)
        if weights == "webb":
            eps = WEBB[rng.integers(0, 6, size=(m, len(sc)))]
        else:
            eps = rng.choice([-1.0, 1.0], size=(m, len(sc)))
        Ts = (eps @ sc) ** 2 / (sc ** 2).sum()
        ge += int((Ts >= T).sum())
        done += m
    return {"p": float((1 + ge) / (reps + 1)), "T": float(T), "G": int(len(sc)), "reps": reps, "weights": weights}


# ---------------------------------------------------------------------------------------------------- randomization
def within_concept_perm(values: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Permute values within each group (single-member groups are unchanged). Vectorised: sort by (group, random)."""
    r = rng.random(len(values))
    order = np.lexsort((r, groups))          # positions sorted by group then random key
    base = np.lexsort((np.arange(len(values)), groups))  # positions sorted by group, stable
    out = np.empty_like(values)
    out[base] = values[order]
    return out


def freedman_lane_parts(s: pd.DataFrame, xvars: list[str], fe: str, target: str = "A_cont") -> tuple[np.ndarray, np.ndarray]:
    """Residualise the target on the other regressors + FE by OLS (same FE, singleton-pruned projector);
    rows dropped by singleton pruning keep their observed value as the 'fitted' part with zero residual."""
    fes = [s[c].to_numpy() for c in fe_cols_for(fe)]
    eng = LPM(fes, s.concept_id.to_numpy())
    X = s[xvars].to_numpy(float)
    j = xvars.index(target)
    Xk = X[eng.keep]
    M = eng.demean(Xk)
    at, Zt = M[:, j], np.delete(M, j, axis=1)
    g = np.linalg.lstsq(Zt, at, rcond=None)[0]
    resid_k = at - Zt @ g
    fitted = X[:, j].copy()
    resid = np.zeros(len(s))
    fitted[eng.keep] = X[eng.keep, j] - resid_k
    resid[eng.keep] = resid_k
    return fitted, resid


def rand_p(t_obs: float, ts: np.ndarray) -> dict:
    ts = np.asarray([t for t in ts if t is not None and np.isfinite(t)], float)
    B = len(ts)
    p = (1 + int((np.abs(ts) >= abs(t_obs)).sum())) / (1 + B)
    return {"p": float(p), "draws_converged": B, "mc_se": float(math.sqrt(p * (1 - p) / max(B, 1)))}


# ---------------------------------------------------------------------------------------------------- IVW
def ivw(est: list[float], se: list[float]) -> dict:
    est, se = np.asarray(est, float), np.asarray(se, float)
    ok = np.isfinite(est) & np.isfinite(se) & (se > 0)
    est, se = est[ok], se[ok]
    w = 1 / se ** 2
    m = float((w * est).sum() / w.sum())
    sm = float(math.sqrt(1 / w.sum()))
    Q = float((w * (est - m) ** 2).sum())
    k = len(est)
    I2 = float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0
    out = {"est": m, "se": sm, "ci": [m - 1.96 * sm, m + 1.96 * sm], "z": m / sm,
           "p": float(2 * stats.norm.sf(abs(m / sm))), "Q": Q, "Q_df": k - 1,
           "Q_p": float(stats.chi2.sf(Q, k - 1)) if k > 1 else None, "I2": I2, "k": k}
    if I2 > 0.5 and k > 1:
        tau2 = max(0.0, (Q - (k - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
        wr = 1 / (se ** 2 + tau2)
        mr = float((wr * est).sum() / wr.sum())
        sr = float(math.sqrt(1 / wr.sum()))
        out["random_effects_DL"] = {"est": mr, "se": sr, "ci": [mr - 1.96 * sr, mr + 1.96 * sr], "tau2": tau2}
    return out


# ---------------------------------------------------------------------------------------------------- cluster bootstrap
def cluster_resample(s: pd.DataFrame, rng: np.random.Generator, fe: str = "coprimary") -> pd.DataFrame:
    """Resample concepts with replacement; each drawn copy becomes a distinct concept (FE level and cluster)."""
    cons = s.concept_id.unique()
    draw = rng.choice(cons, size=len(cons), replace=True)
    idx = s.groupby("concept_id").indices
    parts, labels = [], []
    for k, c in enumerate(draw):
        ii = idx[c]
        parts.append(ii)
        labels.append(np.full(len(ii), k))
    ii = np.concatenate(parts)
    b = s.iloc[ii].copy()
    b["concept_id"] = np.char.add("b", np.concatenate(labels).astype(str))
    b["cfe"] = pd.factorize(b.concept_id)[0]
    b["cxe"] = pd.factorize(b.concept_id + "_" + b.e.astype(str))[0]
    return b.reset_index(drop=True)
