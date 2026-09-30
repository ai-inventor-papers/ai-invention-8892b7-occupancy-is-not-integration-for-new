"""K2 shared library: host-specific vs generic-accessibility test of the confirmed A_cont host-entry effect.

POST-CONFIRMATION EXPLORATORY. Imports the vendored (byte-identical) exp_7 modules from ../d2/src, the eval_2 G helpers
from ../g and the exp_9 MeSH modules from ../mesh/src; never edits them.

Folds: 'screen' and 'heldout' (main OpenAlex population, co-primary sample of eval_2 g_samples.coprimary_sample) and
'mesh' (exp_9 MeSH replication sample, models_mesh.sample rule).
"""
from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

WS = Path(__file__).resolve().parents[1]
os.environ.setdefault("AII_DEPS_ROOT", str(WS.parents[2]))
os.environ.pop("OPENALEX_API_KEY", None)  # no network anywhere in K2
sys.path.insert(0, str(WS / "g"))
sys.path.insert(0, str(WS / "d2" / "src"))

import config  # noqa: E402
import g_lib  # noqa: E402
import g_samples  # noqa: E402
import models  # noqa: E402
import placebo  # noqa: E402
import ppml  # noqa: E402
from features import block_of  # noqa: E402
from loguru import logger  # noqa: E402
from scipy import stats  # noqa: E402

RES = WS / "results"
LOGS = WS / "logs"
FIGS = WS / "figures"
INP = WS / "inputs"
KCACHE = WS / "cache"
for _d in (RES, LOGS, FIGS, KCACHE):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 20261001
FOLDS = ("screen", "heldout", "mesh")
BLK = ["2000-2004", "2005-2009", "2010-2014", "2015-2019"]
BLOCK_YEARS = {b: list(range(int(b[:4]), int(b[:4]) + 5)) for b in BLK}
CTRL = models.EVENT_CONTROLS + models.SECONDARY_EXTRA  # co-primary controls (identical list in mesh_spec)
NAT_CUT, ADJ_LO = 0.30, 0.05  # g_spec G2 class cuts
SPEC_PATH = RES / "k2_spec.json"
SPEC_SHA = RES / "k2_spec.sha256"
RUN_ROOT = WS.parents[3]  # <run>/ (3_invention_loop's parent)

MODELS = {  # focal term first
    "M0": ["A_cont"],
    "M1": ["A_cont", "G_H", "G_F"],
    "M2": ["A_lift"],
    "M3": ["A_lift", "G_H", "G_F"],
}
FOCAL = {"M0": "A_cont", "M1": "A_cont", "M2": "A_lift", "M3": "A_lift"}


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path | str) -> str:
    """Run-root-relative path string (no absolute server paths in published files)."""
    try:
        return str(Path(p).resolve().relative_to(RUN_ROOT.resolve()))
    except ValueError:
        return str(p)


def dump(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, indent=1, default=_default))


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return rel(o)
    raise TypeError(type(o))


def clean(o):
    """Recursively replace NaN/inf by None for JSON."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def assert_spec_frozen() -> dict:
    """Refuse to run any K2 coefficient code unless k2_spec.json matches its frozen sha256."""
    if not SPEC_SHA.exists():
        raise SystemExit("REFUSED: k2_spec.sha256 missing (spec not frozen)")
    want = SPEC_SHA.read_text().split()[0]
    got = sha256_file(SPEC_PATH)
    if want != got:
        raise SystemExit(f"REFUSED: k2_spec.json sha256 {got} != frozen {want}")
    return json.loads(SPEC_PATH.read_text())


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.floor(q / p))
    except (FileNotFoundError, ValueError):
        pass
    return config.detect_cpus()


# ------------------------------------------------------------------------------------------------ data
def load_G(fold: str) -> dict:
    if fold == "mesh":
        return pickle.loads((WS / "mesh" / "cache" / "mesh_prepared.pkl").read_bytes())
    import io_load
    return io_load.prepare()


def refac(s: pd.DataFrame) -> pd.DataFrame:
    s = s.reset_index(drop=True).copy()
    for c, key in (("cxe", s.concept_id + "_" + s.e.astype(str)), ("dxe", s.d.astype(str) + "_" + s.e.astype(str)),
                   ("cfe", s.concept_id), ("efe", s.e.astype(str)), ("dfe", s.d.astype(str))):
        s[c] = pd.factorize(key)[0]
    s["offset"] = np.log(s.n_entry_papers.astype(float))
    return s


def coprimary_sample(fold: str) -> pd.DataFrame:
    """The gate-B (co-primary) input sample of a fold, in the recorded row order."""
    if fold == "mesh":
        om = pd.read_parquet(WS / "mesh" / "results" / "outcomes_mesh.parquet")
        sc = json.loads((WS / "mesh" / "results" / "mesh_spec.json").read_text())["models"]["secondary_controls"]
        assert sc == CTRL, f"MeSH secondary controls differ from main: {sc}"
        s = om.dropna(subset=["A_cont", "CT"] + sc).copy()
        return refac(s)
    cop = pd.read_parquet(INP / f"g_features_{fold}_coprimary.parquet")
    return refac(g_samples.coprimary_sample(cop, fold))


def source_paths(fold: str) -> str:
    if fold == "mesh":
        return ("3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results/outcomes_mesh.parquet; "
                "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results/nativeness/profiles_fetched.jsonl; "
                "3_invention_loop/iter_2/gen_art/gen_art_dataset_5/p2/profiles.jsonl")
    return (f"3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results/g_features_{fold}_coprimary.parquet; "
            "3_invention_loop/iter_2/gen_art/gen_art_dataset_5/p2/profiles.jsonl; "
            "3_invention_loop/iter_2/gen_art/gen_art_dataset_5/hyd/context/subfield_year_totals.json")


# ------------------------------------------------------------------------------------------------ profiles -> H, F
def active_K(totals: dict) -> dict:
    """K_B = number of subfields with > 0 works in 'all_types' summed over the block's five years."""
    out = {}
    for b in BLK:
        acc = {}
        for (sf, y), n in totals.items():
            if y in BLOCK_YEARS[b]:
                acc[sf] = acc.get(sf, 0) + n
        out[b] = int(sum(1 for v in acc.values() if v > 0))
    return out


def host_size(totals: dict) -> dict:
    """s_{d,B} = sum_{y in B} totals(d, y) / sum_{y in B} sum_sf totals(sf, y)."""
    num, den = {}, {}
    for (sf, y), n in totals.items():
        for b in BLK:
            if y in BLOCK_YEARS[b]:
                num[(sf, b)] = num.get((sf, b), 0) + n
                den[b] = den.get(b, 0) + n
    return {(sf, b): v / den[b] for (sf, b), v in num.items() if den.get(b, 0) > 0}


def entropy_norm(counts: dict, K: int) -> float:
    v = np.array([x for x in counts.values() if x > 0], float)
    if len(v) == 0 or K <= 1:
        return np.nan
    p = v / v.sum()
    return float(-(p * np.log(p)).sum() / np.log(K))


def entropy_ub(counts: dict, tot_known: float, K: int) -> float:
    """Truncation upper bound: missing mass (tot_known - observed) spread evenly over the unobserved active subfields."""
    v = np.array([x for x in counts.values() if x > 0], float)
    if len(v) == 0 or K <= 1:
        return np.nan
    miss = float(tot_known) - v.sum()
    ku = K - len(v)
    if miss > 0 and ku > 0:
        v = np.concatenate([v, np.full(ku, miss / ku)])
    p = v / v.sum()
    return float(-(p * np.log(p)).sum() / np.log(K))


def profile_measures(tot: float, counts: dict, K: int) -> tuple[float, float, float]:
    """(H_p, H_p_ub, F_p) of one exact (node, block) profile; counts exclude 'unknown'; tot = total - unknown."""
    H = entropy_norm(counts, K)
    Hub = entropy_ub(counts, tot, K)
    F = float(np.log(tot)) if tot > 0 else np.nan
    return H, Hub, F


# ------------------------------------------------------------------------------------------------ tag arrays
def tag_arrays(G: dict, s: pd.DataFrame, fold: str) -> dict:
    """Per profiled partner tag of every event in s (row order): event index te, node, block index tb, host label td,
    host share sh, source src (0 exact / 1 bg), and the per-tag profile measures H, Hub, F (bg: H from the design-
    weighted shares, Hub = H, F = NaN). Also the dense share tensor S[node, block, label] (for the placebo host)."""
    subs = sorted(G["tax"]["sub_field"])
    lab = {x: i for i, x in enumerate(subs)}
    K = active_K(G["totals"])
    con = G["concepts"].set_index("concept_id")
    ptr, idx = G["P"]
    W = G["W"]
    te, tnode, tb, td, sh, src = [], [], [], [], [], []
    if fold == "mesh":
        sys.path.insert(0, str(WS / "mesh" / "src"))
        import nativeness
        from features_mesh import Nat
        exact = nativeness.all_profiles()
        bg = pickle.loads((WS / "mesh" / "cache" / "bg_shares.pkl").read_bytes())
        nat = Nat(exact, bg)
        for i, ev in enumerate(s.itertuples()):
            c = con.loc[ev.concept_id]
            own = set(c.own_nodes)
            r, y = G["links"][ev.concept_id]
            sub = W["sub"][r]
            er = r[(sub == ev.d) & (y == ev.e)]
            blk = block_of(int(ev.e))
            for row in er:
                a = idx[ptr[row]:ptr[row + 1]]
                if own:
                    a = a[~np.isin(a, list(own))]
                for j in a.tolist():
                    v, sr = nat.share(int(j), blk, int(ev.d))
                    if v is None:
                        continue
                    te.append(i), tnode.append(int(j)), tb.append(BLK.index(blk)), td.append(lab[int(ev.d)])
                    sh.append(v), src.append(0 if sr == "exact" else 1)
        prof_exact, prof_bg = exact, bg
    else:
        for i, ev in enumerate(s.itertuples()):
            c = con.loc[ev.concept_id]
            own = int(c.own_node) if pd.notna(c.own_node) else None
            from features import event_tags
            _, _, nn = event_tags(G, ev.concept_id, int(ev.d), int(ev.e), own)
            blk = block_of(int(ev.e))
            for j in nn.tolist():
                p = G["prof"].get((int(j), blk))
                if p is None:
                    continue
                tot, counts, _ = p
                te.append(i), tnode.append(int(j)), tb.append(BLK.index(blk)), td.append(lab[int(ev.d)])
                sh.append(counts.get(int(ev.d), 0) / tot if tot > 0 else 0.0), src.append(0)
        prof_exact, prof_bg = G["prof"], {}
    te, tnode, tb, td = (np.array(x, np.int64) for x in (te, tnode, tb, td))
    sh, src = np.array(sh, float), np.array(src, np.int8)
    nodes = sorted(set(tnode.tolist()))
    nid = {x: k for k, x in enumerate(nodes)}
    tn = np.array([nid[j] for j in tnode.tolist()], np.int64)
    S = np.zeros((len(nodes), 4, len(subs)))
    Hn, Hubn, Fn = (np.full((len(nodes), 4), np.nan) for _ in range(3))
    SRC = np.full((len(nodes), 4), -1, np.int8)
    for j in nodes:
        for b in BLK[:3]:
            bi = BLK.index(b)
            p = prof_exact.get((j, b))
            if p is not None:
                tot, counts, _ = p
                if tot > 0:
                    for sf, n in counts.items():
                        if sf in lab:
                            S[nid[j], bi, lab[sf]] = n / tot
                Hn[nid[j], bi], Hubn[nid[j], bi], Fn[nid[j], bi] = profile_measures(tot, counts, K[b])
                SRC[nid[j], bi] = 0
                continue
            v = prof_bg.get((j, b))
            if v is not None:
                for sf, w in v[2].items():
                    if sf in lab:
                        S[nid[j], bi, lab[sf]] = w / v[1]
                Hn[nid[j], bi] = entropy_norm(v[2], K[b])
                Hubn[nid[j], bi] = Hn[nid[j], bi]
                SRC[nid[j], bi] = 1
    chk = S[tn, tb, td]
    if len(chk) and np.nanmax(np.abs(chk - sh)) > 1e-12:
        raise RuntimeError("share tensor does not reproduce the per-tag shares")
    return {"te": te, "tn": tn, "tnode": tnode, "tb": tb, "td": td, "sh": sh, "src": src, "S": S, "nodes": nodes,
            "H": Hn[tn, tb], "Hub": Hubn[tn, tb], "F": Fn[tn, tb], "n": len(s), "n_labels": len(subs), "K": K,
            "labels": subs}


def _emean(te: np.ndarray, w: np.ndarray, n: int, mask: np.ndarray | None = None) -> np.ndarray:
    m = np.ones(len(te), bool) if mask is None else mask
    num = np.bincount(te[m], weights=w[m], minlength=n)
    den = np.bincount(te[m], minlength=n).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def entry_measures(arr: dict, s: pd.DataFrame, G: dict, fold: str) -> pd.DataFrame:
    """Entry-level generality means (tag-weighted, same multiset as A_cont), A_cont rebuild, A_lift inputs, split
    generality, G2a class shares. MeSH: generality over EXACT-profiled tags (primary) and exact+bg (G_H_bg)."""
    n, te = arr["n"], arr["te"]
    gen = arr["src"] == 0  # tags entering G_H / G_F (main: all profiled tags are exact)
    out = pd.DataFrame(index=range(n))
    out["A_cont_rebuilt"] = _emean(te, arr["sh"], n)
    out["n_prof_tags_k2"] = np.bincount(te, minlength=n)
    ng = np.bincount(te[gen], minlength=n).astype(float)
    out["n_gen_tags"] = ng
    out["G_H"] = _emean(te, arr["H"], n, gen & ~np.isnan(arr["H"]))
    out["G_F"] = _emean(te, arr["F"], n, gen & ~np.isnan(arr["F"]))
    out["G_H_ub"] = _emean(te, arr["Hub"], n, gen & ~np.isnan(arr["Hub"]))
    out["G_H_bg"] = _emean(te, arr["H"], n, ~np.isnan(arr["H"]))  # exact + bg (MeSH sensitivity; = G_H on main)
    out.loc[ng == 0, ["G_H", "G_F", "G_H_ub"]] = np.nan
    shv = arr["sh"]
    cls = {"nat": shv >= NAT_CUT, "adj": (shv >= ADJ_LO) & (shv < NAT_CUT), "for": shv < ADJ_LO}
    with np.errstate(invalid="ignore", divide="ignore"):
        for k, m in cls.items():
            mm = gen & m
            out[f"GH_{k}"] = np.bincount(te[mm], weights=np.nan_to_num(arr["H"][mm]), minlength=n) / ng
            out[f"GF_{k}"] = np.bincount(te[mm], weights=np.nan_to_num(arr["F"][mm]), minlength=n) / ng
        den = np.bincount(te, minlength=n).astype(float)
        out["NAT"] = np.bincount(te, weights=cls["nat"].astype(float), minlength=n) / den
        out["ADJ"] = np.bincount(te, weights=cls["adj"].astype(float), minlength=n) / den
    out.loc[ng == 0, [f"G{x}_{k}" for x in "HF" for k in cls]] = np.nan
    hs = host_size(G["totals"])
    out["s_dB"] = [hs.get((int(d), block_of(int(e))), np.nan) for d, e in zip(s.d, s.e)]
    out["K_B"] = [arr["K"][block_of(int(e))] for e in s.e]
    return out


def a_spec(arr: dict, s: pd.DataFrame, ent: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """Tag-level OLS s_pd = a_B + b1 H_p + b2 F_p + b3 ln s_dB + e over generality-profiled tags (each tag occurrence
    one row, as A_cont weights them); A_spec = entry mean of the residuals."""
    gen = (arr["src"] == 0) & ~np.isnan(arr["H"]) & ~np.isnan(arr["F"])
    te = arr["te"][gen]
    lsd = np.log(ent.s_dB.to_numpy()[te])
    ok = np.isfinite(lsd)
    te = te[ok]
    yv = arr["sh"][gen][ok]
    B = np.eye(4)[arr["tb"][gen][ok]]
    B = B[:, B.sum(0) > 0]
    X = np.column_stack([B, arr["H"][gen][ok], arr["F"][gen][ok], lsd[ok]])
    beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
    res = yv - X @ beta
    r2 = 1 - res.var() / yv.var()
    val = _emean(te, res, arr["n"])
    return val, {"b_H": float(beta[-3]), "b_F": float(beta[-2]), "b_ln_s_dB": float(beta[-1]), "R2": float(r2),
                 "n_tags": int(len(yv))}


def add_lift(k: pd.DataFrame) -> dict:
    """A_lift = ln((A_cont + c0) / s_dB); c0 = 0.5 x smallest positive A_cont in the fold, used only if any A == 0."""
    a = k.A_cont.to_numpy(float)
    nz = int((a == 0).sum())
    c0 = 0.5 * float(a[a > 0].min()) if nz else 0.0
    k["A_lift"] = np.log((a + c0) / k.s_dB.to_numpy(float))
    k["ln_A_cont"] = np.log(a + c0)
    k["ln_s_dB"] = np.log(k.s_dB.to_numpy(float))
    k["zeroA"] = a == 0
    return {"n_zero_A": nz, "c0": c0}


# ------------------------------------------------------------------------------------------------ within-FE algebra
def within(s: pd.DataFrame, cols: list[str], fe=("cfe", "efe", "dfe")) -> np.ndarray:
    """Unweighted within-FE residuals (alternating projections) of the columns."""
    fes = [pd.factorize(s[c])[0] for c in fe]
    return ppml._demean(s[cols].to_numpy(float), np.ones(len(s)), fes)


def within_r2(s: pd.DataFrame, y: str, xs: list[str]) -> float:
    M = within(s, [y] + xs)
    yt, Xt = M[:, 0], M[:, 1:]
    b, *_ = np.linalg.lstsq(Xt, yt, rcond=None)
    r = yt - Xt @ b
    return float(1 - (r ** 2).sum() / (yt ** 2).sum())


def within_proj(s: pd.DataFrame, y: str, xs: list[str]) -> tuple[np.ndarray, np.ndarray, float]:
    """Linear projection of y on xs + FE: returns (fitted incl. FE part, residual, within R2)."""
    M = within(s, [y] + xs)
    yt, Xt = M[:, 0], M[:, 1:]
    b, *_ = np.linalg.lstsq(Xt, yt, rcond=None)
    res = yt - Xt @ b
    fitted = s[y].to_numpy(float) - res
    return fitted, res, float(1 - (res ** 2).sum() / (yt ** 2).sum())


# ------------------------------------------------------------------------------------------------ fits
def xvars_of(model: str, extra_first: list[str] | None = None) -> list[str]:
    return (extra_first or MODELS[model]) + ["CT"] + CTRL


def fit_b(s: pd.DataFrame, xs: list[str], spec: str = "secondary", y: str = "Y_strict") -> dict | None:
    """Raw PPML fit -> {'coef','se','G','n'} (no reporting overhead)."""
    try:
        r = ppml.fit(s[y].to_numpy(float), s[xs].to_numpy(float), models.fe_arrays(s, spec), s.offset.to_numpy(),
                     s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    except (np.linalg.LinAlgError, ValueError, RuntimeError, FloatingPointError):
        return None
    return r


def fit_rows(s: pd.DataFrame, xs: list[str], targets: list[str], *, fold: str, model: str, spec: str = "secondary",
             label: str, y: str = "Y_strict", wild: tuple = (), zsd: float | None = None, rng=None,
             extra: dict | None = None) -> tuple[list[dict], dict | None]:
    base = {"fold": fold, "model": model, "spec": spec, "y": y, "label": label, "source": source_paths(fold),
            **(extra or {})}
    try:
        r = models.fit_one(s, y, xs, spec, wild=bool(wild), wild_vars=tuple(wild),
                           rng=rng or np.random.default_rng(SEED))
    except (np.linalg.LinAlgError, ValueError, RuntimeError) as ex:
        logger.warning(f"{fold}/{model}: fit failed {ex!r}")
        r = None
    if r is None:
        return [{**base, "var": t, "note": "fit failed / too few observations", "N_input": int(len(s))}
                for t in targets], None
    rows = []
    tq = stats.t.ppf(0.975, r["G"] - 1)
    for t in targets:
        b, se = r["coef"][t], r["se"][t]
        z = b / se if se > 0 else np.nan
        rows.append({**base, "var": t, "b": b, "se": se, "z": z, "p_crv1": r["p"][t], "irr_sd": r["irr_sd"][t],
                     "irr_sd_lo": r["ci_irr_sd"][t][0], "irr_sd_hi": r["ci_irr_sd"][t][1], "irr_01": r["irr_01"][t],
                     "sd_retained": r["sd_retained"][t], "lnirr_sd": b * r["sd_retained"][t],
                     "lnirr_sd_se": se * r["sd_retained"][t], "tq": tq,
                     "p_wild": (r.get("p_wild") or {}).get(t),
                     "p_placebo_cal": float(2 * stats.norm.sf(abs(z) / zsd)) if zsd and np.isfinite(z) else None,
                     "N_input": r["n_input"], "N": r["n_retained"], "G": r["G"],
                     "retained_share": r["retained_share"]})
    return rows, r


def placebo_zsd(fold: str) -> float:
    if fold == "mesh":
        pl = pd.read_csv(WS / "mesh" / "results" / "placebo_draws_mesh.csv")
        return float(pl.z_A_R2.dropna().std())
    pl = pd.read_csv(INP / "placebo_draws.csv")
    return float(pl.z_A_secondary.dropna().std())


def ivw(b: np.ndarray, se: np.ndarray) -> dict:
    b, se = np.asarray(b, float), np.asarray(se, float)
    ok = np.isfinite(b) & np.isfinite(se) & (se > 0)
    b, se = b[ok], se[ok]
    w = 1 / se ** 2
    bp = float((w * b).sum() / w.sum())
    sp = float(np.sqrt(1 / w.sum()))
    Q = float((w * (b - bp) ** 2).sum())
    k = len(b)
    I2 = float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 and k > 1 else 0.0
    return {"b": bp, "se": sp, "lo": bp - 1.959963984540054 * sp, "hi": bp + 1.959963984540054 * sp,
            "z": bp / sp, "p": float(2 * stats.norm.sf(abs(bp / sp))), "Q": Q, "df": k - 1,
            "p_Q": float(stats.chi2.sf(Q, k - 1)) if k > 1 else None, "I2": I2, "k": k,
            "weights": (w / w.sum()).tolist()}


# ------------------------------------------------------------------------------------------------ workers
_W: dict = {}


def _init(payload: dict) -> None:
    import warnings
    warnings.filterwarnings("ignore")
    _W.update(payload)


def resample(s: pd.DataFrame, rng) -> pd.DataFrame:
    return g_lib.resample_concepts(s, rng)


def _boot_task(args) -> dict:
    """One concept-cluster bootstrap draw: target coefficients of every (name, xs, targets, spec) fit on the
    resampled fold sample."""
    fold, seed = args
    s = _W["samples"][fold]
    b = resample(s, np.random.default_rng(seed))
    out = {"fold": fold, "seed": seed}
    for name, xs, targets, spec in _W["pairs"][fold]:
        r = fit_b(b, xs, spec)
        for t in targets:
            out[f"{name}|{t}"] = None if r is None else float(r["coef"][xs.index(t)])
    return out


def _perm_task(args) -> dict:
    """Freedman-Lane within-concept permutation draw for one (fold, model): permute the linear residual of the
    focal regressor (on the other regressors + FE) within concept, add back the fitted part, refit the PPML."""
    fold, model, seed = args
    s = _W["samples"][fold]
    fl = _W["fl"][(fold, model)]
    rng = np.random.default_rng(seed)
    res = fl["res"].copy()
    for ix in fl["groups"]:
        res[ix] = res[ix][rng.permutation(len(ix))]
    xs = fl["xs"]
    X = s[xs].to_numpy(float).copy()
    X[:, 0] = fl["fitted"] + res
    try:
        r = ppml.fit(s.Y_strict.to_numpy(float), X, models.fe_arrays(s, "secondary"), s.offset.to_numpy(),
                     s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    except (np.linalg.LinAlgError, ValueError, RuntimeError, FloatingPointError):
        r = None
    if r is None:
        return {"fold": fold, "model": model, "seed": seed, "z": None}
    return {"fold": fold, "model": model, "seed": seed, "z": float(r["coef"][0] / r["se"][0])}


def fl_prep(s: pd.DataFrame, xs: list[str]) -> dict:
    fitted, res, r2 = within_proj(s, xs[0], xs[1:])
    groups = list(s.groupby("cfe").indices.values())
    return {"fitted": fitted, "res": res, "groups": groups, "xs": xs, "r2_focal_on_rest": r2}


def pool(payload: dict, fn, tasks: list, chunksize: int = 4) -> list:
    with ProcessPoolExecutor(detect_cpus(), mp_context=mp.get_context("spawn"), initializer=_init,
                             initargs=(payload,)) as ex:
        return list(ex.map(fn, tasks, chunksize=chunksize))
