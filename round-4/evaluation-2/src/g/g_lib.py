"""G1-G3 discriminating tests for the D2 host-entry result: features, fits, MDE simulations, placebo host.

Imports the vendored (frozen, hash-checked) iteration-3 modules from ../d2/src and never modifies them.
Every quantity that reads data after the entry year e (the G1 window [e, e+1] and all outcomes) goes through
config.assert_not_sealed, so held-out concepts are refused until the post-opening scripts clear SEALED_IDS.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):  # one BLAS thread per worker process
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EVAL = Path(__file__).resolve().parents[1]
D2 = EVAL / "d2"
os.environ.setdefault("AII_DEPS_ROOT", str(EVAL.parents[2]))  # <loop>/iter_4/gen_art/<artifact> -> <loop>
sys.path.insert(0, str(D2 / "src"))

import config  # noqa: E402
import io_load  # noqa: E402
import models  # noqa: E402
import outcomes  # noqa: E402
import placebo  # noqa: E402
import ppml  # noqa: E402
from features import Nativeness, block_of, event_tags, load_rs, partner_set  # noqa: E402
from loguru import logger  # noqa: E402
from scipy import stats  # noqa: E402

RES = EVAL / "results"
LOGS = EVAL / "logs"
FIGS = EVAL / "figures"
for _d in (RES, LOGS, FIGS):
    _d.mkdir(parents=True, exist_ok=True)

CTRL = models.EVENT_CONTROLS
CTRL2 = models.EVENT_CONTROLS + models.SECONDARY_EXTRA
SEED = 20260930
G_SPEC = RES / "g_spec.json"
G_SHA = RES / "g_spec.sha256"


def io_load_prepare() -> dict:
    return io_load.prepare()


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def assert_spec_frozen() -> dict:
    """Refuse to run any G coefficient code unless g_spec.json matches its frozen sha256."""
    want = G_SHA.read_text().split()[0]
    got = sha256_file(G_SPEC)
    if want != got:
        raise SystemExit(f"REFUSED: g_spec.json sha256 {got} != frozen {want}")
    return json.loads(G_SPEC.read_text())


def placebo_z_sd() -> dict:
    """SD of the nativeness-permutation placebo z statistic (iteration-3 draws), per FE spec."""
    pl = pd.read_csv(D2 / "results" / "placebo_draws.csv")
    return {"primary": float(pl.z_A_primary.dropna().std()), "secondary": float(pl.z_A_secondary.dropna().std())}


# ------------------------------------------------------------------------------------------------ G1 features
def multi_team(rows: np.ndarray, AUp: np.ndarray, AUi: np.ndarray) -> bool:
    """>= 2 papers and at least one pair with non-empty, disjoint author-id sets."""
    if len(rows) < 2:
        return False
    sets = [set(AUi[AUp[r]:AUp[r + 1]].tolist()) for r in rows]
    for i in range(len(sets)):
        if not sets[i]:
            continue
        for j in range(i + 1, len(sets)):
            if sets[j] and not (sets[i] & sets[j]):
                return True
    return False


def build_features_window(G: dict, ev: pd.DataFrame, w: int) -> pd.DataFrame:
    """Parameterised copy of features.build_features for the entry window [e, e+w] (w=0 reproduces the frozen
    features on every model column; gate R0c). Pre-entry quantities (nativeness block, CT companions, RD,
    prox_od, mom_d, demic's prior-origin author set) keep their pre-e definitions."""
    if w:
        config.assert_not_sealed(ev.concept_id.unique())
    W = G["W"]
    nat = Nativeness(G["prof"])
    rs = load_rs()
    totals = G["totals"]
    con = G["concepts"].set_index("concept_id")
    AUp, AUi = G["AU"]
    T3p, T3i = G["T3"]
    ptr, idx = G["P"]
    out = {}
    for cid, g in ev.groupby("concept_id"):
        c = con.loc[cid]
        r, y = G["links"][cid]
        sub = W["sub"][r]
        o = int(c.origin) if pd.notna(c.origin) else -999
        own = int(c.own_node) if pd.notna(c.own_node) else None
        for evr in g.itertuples():
            d, e = int(evr.d), int(evr.e)
            blk = block_of(e)
            er = r[(sub == d) & (y >= e) & (y <= e + w)]
            nodes = np.concatenate([idx[ptr[k]:ptr[k + 1]] for k in er]) if len(er) else np.zeros(0, np.int64)
            if own is not None:
                nodes = nodes[nodes != own]
            comp = partner_set(G, r[(sub == o) & (y >= e - 5) & (y <= e - 1)], own)
            sh = [nat.share(int(j), blk, d) for j in nodes]
            prof = [s for s in sh if s is not None]
            n_all, n_prof = len(nodes), len(prof)
            f = {"n_win": int(len(er)), "n_partners_distinct_w": int(len(set(nodes.tolist()))),
                 "n_tags": n_all, "n_prof_tags": n_prof,
                 "cov": n_prof / n_all if n_all else np.nan,
                 "CT": float(np.mean([int(j) in comp for j in nodes])) if n_all else np.nan,
                 "A_cont": float(np.mean(prof)) if n_prof else np.nan}
            t0, t3 = totals.get((d, e), 0), totals.get((d, e - 3), 0)
            f["mom_d"] = float(np.log(t0 / t3)) if t0 > 0 and t3 > 0 else np.nan
            f["prox_od"] = 1 - rs.get((o, d), np.nan)
            pre = (sub >= 0) & (sub != d) & (y < e)
            if not pre.any():
                pre = (sub >= 0) & (sub != d) & (y <= e)
            cnt = Counter(sub[pre].tolist())
            num = sum(n * (1 - rs.get((s, d), np.nan)) for s, n in cnt.items())
            den = sum(cnt.values())
            f["RD"] = num / den if den else np.nan
            f["log_centrality"] = float(np.log1p(len(partner_set(G, r[y <= e + w], own))))
            f["log_W1"] = float(np.log1p(((y >= e - 5 + w) & (y <= e + w)).sum()))
            f["log_n_partner_tags"] = float(np.log(max(n_all, 1)))
            ent_auth = set()
            for k in er:
                ent_auth.update(AUi[AUp[k]:AUp[k + 1]].tolist())
            prior_orig = set()
            for k in r[(sub == o) & (y < e)]:
                prior_orig.update(AUi[AUp[k]:AUp[k + 1]].tolist())
            f["demic"] = len(ent_auth & prior_orig) / len(ent_auth) if ent_auth else np.nan
            f["mean_topic_score"] = float(W["topic_score"][er].mean()) if len(er) else np.nan
            f["min_topic_score"] = float(W["topic_score"][er].min()) if len(er) else np.nan
            f["boundary_share"] = float(np.mean([o in set(T3i[T3p[k]:T3p[k + 1]].tolist()) for k in er])) if len(er) else np.nan
            f["abstract_share"] = float(W["has_abstract"][er].mean()) if len(er) else np.nan
            f["multi"] = multi_team(er, AUp, AUi)
            out[evr.Index] = f
    return pd.DataFrame.from_dict(out, orient="index")


# ------------------------------------------------------------------------------------------------ G3 features
def load_venues(G: dict) -> dict:
    """source_id per corpus work row (aligned with G['W']) and the citation-independent ASJC habitat per venue."""
    import pyarrow.parquet as pq
    parts = sorted((config.D5 / "hyd" / "works").glob("works_part_*.parquet"))
    t = pd.concat([pq.read_table(p, columns=["work_id", "source_id"]).to_pandas() for p in parts], ignore_index=True)
    src = pd.Series(t.source_id.to_numpy(), index=t.work_id.to_numpy())
    src = src[~src.index.duplicated()]
    src_row = src.reindex(G["W"]["work_id"]).fillna(-1).to_numpy(np.int64)
    vh = json.loads((config.D5 / "outputs" / "venue_habitat_asjc.json").read_text())["venues"]
    hab = {}
    for v in vh:
        if v.get("habitat_subfield") != "UNCOVERED" and v.get("citation_independent", False):
            hab[int(v["source_id"])] = {int(k): float(x) for k, x in (v.get("fractional_shares") or {}).items()}
    return {"src_row": src_row, "hab": hab}


def g3_features(G: dict, ev: pd.DataFrame, ven: dict) -> pd.DataFrame:
    """Entry-year (W1) classifier-circularity controls: host_topic_share, sec_host_share, venue_d_share."""
    W = G["W"]
    T3p, T3i = G["T3"]
    con = G["concepts"].set_index("concept_id")
    out = {}
    for evr in ev.itertuples():
        c = con.loc[evr.concept_id]
        own = int(c.own_node) if pd.notna(c.own_node) else None
        er, _, _ = event_tags(G, evr.concept_id, int(evr.d), int(evr.e), own)
        d = int(evr.d)
        hs, ss, vs = [], [], []
        n_sec = 0
        for k in er:
            t = [x for x in T3i[T3p[k]:T3p[k + 1]].tolist() if x >= 0]
            if t:
                hs.append(np.mean([x == d for x in t]))
            if len(t) >= 2:
                n_sec += 1
                ss.append(np.mean([x == d for x in t[1:3]]))
            sv = int(ven["src_row"][k])
            if sv in ven["hab"]:
                vs.append(ven["hab"][sv].get(d, 0.0))
        out[evr.Index] = {"host_topic_share": float(np.mean(hs)) if hs else np.nan,
                          "sec_host_share": float(np.mean(ss)) if ss else 0.0,
                          "n_papers_with_secondary_topics": n_sec,
                          "venue_d_share": float(np.mean(vs)) if vs else np.nan,
                          "n_venue_covered_papers": len(vs), "n_entry_papers_chk": len(er)}
    return pd.DataFrame.from_dict(out, orient="index")


def y_strict_hc(G: dict, events: pd.DataFrame, cai: outcomes.CoauthorIndex, min_ts: float = 0.9) -> pd.Series:
    """Y_strict counting only W2 d-papers with topic_score >= min_ts (outcome-side circularity, G3(iv)).
    Same prior-set rule as outcomes.compute_Y."""
    config.assert_not_sealed(events.concept_id.unique())
    W = G["W"]
    AUp, AUi = G["AU"]
    vals = {}
    for cid, g in events.groupby("concept_id"):
        r, y = G["links"][cid]
        sub = W["sub"][r]
        cache = {}
        for evr in g.itertuples():
            d, e = int(evr.d), int(evr.e)
            if e not in cache:
                seeds = np.unique(np.concatenate([AUi[AUp[k]:AUp[k + 1]] for k in r[(y >= e - 5) & (y <= e)]]
                                                 or [np.zeros(0, np.int64)]))
                cache[e] = cai.prior_set(seeds, e)
            ps = cache[e]
            w2 = (sub == d) & (y >= e + 1) & (y <= e + 5)
            s = 0
            for k in r[w2]:
                if W["topic_score"][k] < min_ts:
                    continue
                a = AUi[AUp[k]:AUp[k + 1]]
                if len(a) and not ps[a].any():
                    s += 1
            vals[evr.Index] = s
    return pd.Series(vals)


# ------------------------------------------------------------------------------------------------ G2 features
def g2_shares(arr: dict, nat_cut: float, adj_lo: float) -> pd.DataFrame:
    """Tag-weighted NATIVE / ADJACENT shares (G2a) and the exact decomposition A_nat + A_adj + A_for (G2b)."""
    sh = arr["S"][arr["tn"], arr["tb"], arr["td"]]
    n = arr["n"]
    den = np.bincount(arr["te"], minlength=n).astype(float)
    isn, isa = sh >= nat_cut, (sh >= adj_lo) & (sh < nat_cut)
    isf = ~(isn | isa)
    with np.errstate(invalid="ignore", divide="ignore"):
        return pd.DataFrame({
            "NAT": np.bincount(arr["te"], weights=isn.astype(float), minlength=n) / den,
            "ADJ": np.bincount(arr["te"], weights=isa.astype(float), minlength=n) / den,
            "A_nat": np.bincount(arr["te"], weights=sh * isn, minlength=n) / den,
            "A_adj": np.bincount(arr["te"], weights=sh * isa, minlength=n) / den,
            "A_for": np.bincount(arr["te"], weights=sh * isf, minlength=n) / den})


# ------------------------------------------------------------------------------------------------ fitting
def prep_sample(df: pd.DataFrame, pop: str, fold: str, need: list[str]) -> pd.DataFrame:
    """models.primary_sample plus a drop of rows missing any extra regressor, then fresh FE ids."""
    s = models.primary_sample(df, pop=pop, fold=fold)
    s = s.dropna(subset=[c for c in need if c in s.columns]).reset_index(drop=True)
    for c, key in (("cxe", s.concept_id + "_" + s.e.astype(str)), ("dxe", s.d.astype(str) + "_" + s.e.astype(str)),
                   ("cfe", s.concept_id), ("efe", s.e.astype(str)), ("dfe", s.d.astype(str))):
        s[c] = pd.factorize(key)[0]
    return s


def fit_row(name: str, s: pd.DataFrame, y: str, xvars: list[str], spec: str, targets: list[str], *, fold: str,
            family: str = "", wild: bool = True, zsd: dict | None = None, rng=None, extra: dict | None = None) -> list[dict]:
    """One PPML fit -> one row per target regressor with the full reporting set."""
    base = {"row": name, "fold": fold, "spec": spec, "y": y, "family": family, **(extra or {})}
    try:
        r = models.fit_one(s, y, xvars, spec, wild=wild, wild_vars=tuple(targets), rng=rng or np.random.default_rng(SEED))
    except (np.linalg.LinAlgError, ValueError, RuntimeError) as ex:
        logger.warning(f"{name}: fit failed {ex!r}")
        r = None
    if r is None:
        return [{**base, "var": t, "note": "fit failed / too few observations", "N_input": int(len(s))} for t in targets]
    rows = []
    for t in targets:
        b, se = r["coef"][t], r["se"][t]
        z = b / se if se > 0 else np.nan
        zs = (zsd or {}).get("secondary" if spec != "primary" else "primary")
        rows.append({**base, "var": t, "b": b, "se": se, "z": z, "p": r["p"][t], "irr_sd": r["irr_sd"][t],
                     "irr_sd_lo": r["ci_irr_sd"][t][0], "irr_sd_hi": r["ci_irr_sd"][t][1], "irr_01": r["irr_01"][t],
                     "sd_retained": r["sd_retained"][t], "p_wild": (r.get("p_wild") or {}).get(t),
                     "p_placebo_cal": float(2 * stats.norm.sf(abs(z) / zs)) if zs else None,
                     "N_input": r["n_input"], "N": r["n_retained"], "G": r["G"], "retained_share": r["retained_share"]})
    return rows


def wald_equal_01(s: pd.DataFrame, y: str, a: str, b: str, others: list[str], spec: str) -> dict:
    """Test b_a == b_b (equal per-0.1 effects) by reparametrisation: b_a*a + b_b*b = (b_a - b_b)*a + b_b*(a + b)."""
    ss = s.copy()
    ss["_sum"] = ss[a] + ss[b]
    try:
        r = models.fit_one(ss, y, [a, "_sum"] + others, spec)
    except (np.linalg.LinAlgError, ValueError, RuntimeError):
        r = None
    if r is None:
        return {"diff": None, "p": None}
    return {"diff_b": r["coef"][a], "se": r["se"][a], "p": r["p"][a], "G": r["G"]}


def vif(s: pd.DataFrame, cols: list[str]) -> dict:
    X = s[cols].to_numpy(float)
    X = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)
    C = np.corrcoef(X, rowvar=False)
    try:
        Ci = np.linalg.inv(C)
    except np.linalg.LinAlgError:
        Ci = np.linalg.pinv(C)
    return {c: float(Ci[i, i]) for i, c in enumerate(cols)}


def _fit_b(s: pd.DataFrame, y: str, xs: list[str], spec: str, target: str) -> float | None:
    try:
        r = ppml.fit(s[y].to_numpy(float), s[xs].to_numpy(float), models.fe_arrays(s, spec), s.offset.to_numpy(),
                     s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    except (np.linalg.LinAlgError, ValueError, RuntimeError):
        return None
    return None if r is None else float(r["coef"][xs.index(target)])


def resample_concepts(s: pd.DataFrame, rng, n_conc: int | None = None) -> pd.DataFrame:
    cids = s.concept_id.unique()
    pick = rng.choice(cids, n_conc or len(cids))
    g = {c: x for c, x in s.groupby("concept_id")}
    parts = []
    for i, c in enumerate(pick):
        x = g[c].copy()
        x["concept_id"] = f"{c}#{i}"
        parts.append(x)
    b = pd.concat(parts, ignore_index=True)
    for c, key in (("cxe", b.concept_id + "_" + b.e.astype(str)), ("dxe", b.d.astype(str) + "_" + b.e.astype(str)),
                   ("cfe", b.concept_id), ("efe", b.e.astype(str)), ("dfe", b.d.astype(str))):
        b[c] = pd.factorize(key)[0]
    return b


_W: dict = {}


def _init_worker(payload: dict) -> None:
    import warnings
    warnings.filterwarnings("ignore")
    _W.update(payload)


def _boot_rep(seed: int) -> tuple:
    """One concept-cluster bootstrap replicate of b_A with and without the added control block."""
    s, y, xb, xw, spec, t = (_W[k] for k in ("s", "y", "xb", "xw", "spec", "t"))
    b = resample_concepts(s, np.random.default_rng(seed))
    return _fit_b(b, y, xb, spec, t), _fit_b(b, y, xw, spec, t)


def pct_removed(s: pd.DataFrame, y: str, xbase: list[str], xwith: list[str], spec: str, target: str = "A_cont",
                reps: int = 499, seed: int = SEED) -> dict:
    """100 * (1 - b_with / b_base) on the IDENTICAL input sample (pruning depends on y and FE only), with a
    concept-cluster bootstrap percentile CI of the ratio."""
    s = s.dropna(subset=list(set(xbase + xwith))).reset_index(drop=True)
    bb, bw = _fit_b(s, y, xbase, spec, target), _fit_b(s, y, xwith, spec, target)
    if bb is None or bw is None:
        return {"pct": None, "note": "fit failed"}
    seeds = [seed + i for i in range(reps)]
    with ProcessPoolExecutor(config.detect_cpus(), mp_context=mp.get_context("spawn"), initializer=_init_worker,
                             initargs=({"s": s, "y": y, "xb": xbase, "xw": xwith, "spec": spec, "t": target},)) as ex:
        res = list(ex.map(_boot_rep, seeds, chunksize=8))
    pc = np.array([100 * (1 - w / b) for b, w in res if b is not None and w is not None and b != 0])
    return {"b_base": bb, "b_with": bw, "pct": 100 * (1 - bw / bb), "N_input": int(len(s)),
            "G_input": int(s.concept_id.nunique()), "boot_reps_ok": int(len(pc)), "boot_reps": reps,
            "ci95": [float(np.quantile(pc, .025)), float(np.quantile(pc, .975))] if len(pc) > 20 else None}


# ------------------------------------------------------------------------------------------------ MDE
def _mde_rep(args) -> dict:
    irr, seed = args
    base, xs, target, spec, n_conc, sd_t, mean_t, theta = (_W[k] for k in ("base", "xs", "target", "spec", "n_conc",
                                                                           "sd_t", "mean_t", "theta"))
    rng = np.random.default_rng(seed)
    s = resample_concepts(base, rng, n_conc)
    b = np.log(irr) / sd_t
    mu = s.mu0.to_numpy() * np.exp(b * (s[target].to_numpy() - mean_t))
    s["Y_sim"] = rng.poisson(rng.gamma(theta, mu / theta))
    try:
        r = ppml.fit(s.Y_sim.to_numpy(float), s[xs].to_numpy(float), models.fe_arrays(s, spec), s.offset.to_numpy(),
                     s.concept_id.to_numpy())
    except (RuntimeError, np.linalg.LinAlgError, ValueError):
        r = None
    if r is None:
        return {"irr": irr, "reject": None}
    j = xs.index(target)
    p = 2 * stats.t.sf(abs(r["coef"][j] / r["se"][j]), r["G"] - 1)
    return {"irr": irr, "reject": bool(p < 0.025 and r["coef"][j] > 0)}


def mde_sim(s: pd.DataFrame, y: str, xs: list[str], target: str, spec: str = "secondary", n_conc: int | None = None,
            grid=(1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.50), reps: int = 200, seed: int = SEED,
            mu0_x: list[str] | None = None) -> dict:
    """NB2 simulation MDE (power 0.8) as power.py: mu0 from the controls-only fit (no target term, so the target
    coefficient is never read), concepts resampled to n_conc, one-sided rejection b > 0 and two-sided p < .025."""
    ctrl = mu0_x or [x for x in xs if x != target]
    r0 = ppml.fit(s[y].to_numpy(float), s[ctrl].to_numpy(float), models.fe_arrays(s, spec), s.offset.to_numpy(),
                  s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    base = s[r0["keep"]].copy()
    base["mu0"] = r0["mu"]
    theta = float(np.sum(base.mu0 ** 2) / max(np.sum((base[y] - base.mu0) ** 2 - base[y]), 1e-9))
    theta = theta if theta > 0 else 1e6
    n_conc = n_conc or int(s.concept_id.nunique())
    payload = {"base": base, "xs": xs, "target": target, "spec": spec, "n_conc": n_conc,
               "sd_t": float(base[target].std()), "mean_t": float(base[target].mean()), "theta": theta}
    tasks = [(irr, seed + 1000 * gi + k) for gi, irr in enumerate(grid) for k in range(reps)]
    with ProcessPoolExecutor(config.detect_cpus(), mp_context=mp.get_context("spawn"), initializer=_init_worker,
                             initargs=(payload,)) as ex:
        res = pd.DataFrame(list(ex.map(_mde_rep, tasks, chunksize=10)))
    curve = res.groupby("irr").reject.apply(lambda x: float(pd.Series(x).dropna().astype(float).mean())).to_dict()
    mde = next((float(k) for k, v in sorted(curve.items()) if v >= 0.80), None)
    return {"target": target, "spec": spec, "n_conc": n_conc, "n_events_base": int(len(base)), "theta": theta,
            "reps": reps, "power_curve": {str(k): v for k, v in curve.items()},
            "failed": int(res.reject.isna().sum()), "MDE_irr_sd_power80": mde}


# ------------------------------------------------------------------------------------------------ placebo host
def placebo_candidates(G: dict, s: pd.DataFrame, labels: list[int], strat: str) -> list[np.ndarray]:
    """Per event: label indices of eligible placebo hosts d' (d' != o, d' != d, no c-paper in d' at years <= e),
    in the same size decile as d (subfield totals in year e) or the same proximity-to-o decile."""
    rs = load_rs()
    totals = G["totals"]
    W = G["W"]
    lab = {x: i for i, x in enumerate(labels)}
    lab_arr = np.array(labels)
    dec_cache: dict = {}
    out = []
    for evr in s.itertuples():
        d, e, o = int(evr.d), int(evr.e), int(evr.o)
        r, y = G["links"][evr.concept_id]
        used = set(W["sub"][r][y <= e].tolist())
        if strat == "size":
            key = ("size", e)
            if key not in dec_cache:
                v = np.array([totals.get((x, e), 0) for x in labels], float)
                dec_cache[key] = pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()
        else:
            key = ("prox", o)
            if key not in dec_cache:
                v = np.array([1 - rs.get((o, x), np.nan) for x in labels], float)
                v = np.where(np.isnan(v), -1, v)
                dec_cache[key] = pd.qcut(pd.Series(v).rank(method="first"), 10, labels=False).to_numpy()
        dec = dec_cache[key]
        if d not in lab:
            out.append(np.zeros(0, np.int64))
            continue
        ok = (dec == dec[lab[d]]) & (lab_arr != o) & (lab_arr != d) & ~np.isin(lab_arr, list(used))
        out.append(np.flatnonzero(ok))
    return out


def _plac_draw(seed: int) -> dict:
    s, arr, cand, xs_ctrl = (_W[k] for k in ("s", "arr", "cand", "xs"))
    rng = np.random.default_rng(seed)
    pick = np.array([c[rng.integers(len(c))] if len(c) else -1 for c in cand])
    lab_tag = pick[arr["te"]]
    ok = lab_tag >= 0
    sh = np.zeros(len(lab_tag))
    sh[ok] = arr["S"][arr["tn"][ok], arr["tb"][ok], lab_tag[ok]]
    num = np.bincount(arr["te"], weights=sh, minlength=arr["n"])
    den = np.bincount(arr["te"], minlength=arr["n"])
    with np.errstate(invalid="ignore", divide="ignore"):
        ap = np.where(pick >= 0, num / den, np.nan)
    ss = s.copy()
    ss["A_plac"] = ap
    ss = ss.dropna(subset=["A_plac"]).reset_index(drop=True)
    for c in ("cfe", "efe", "dfe"):
        ss[c] = pd.factorize(ss[c])[0]
    out = {"seed": seed, "n_events": int(len(ss))}
    for name, xs in (("plac", ["A_plac", "CT"] + xs_ctrl), ("joint", ["A_cont", "A_plac", "CT"] + xs_ctrl)):
        try:
            r = models.fit_one(ss, "Y_strict", xs, "secondary")
        except (np.linalg.LinAlgError, ValueError, RuntimeError):
            r = None
        if r is None:
            out[f"{name}_ok"] = False
            continue
        out[f"{name}_ok"] = True
        out[f"{name}_irr_sd_plac"] = r["irr_sd"]["A_plac"]
        out[f"{name}_p_plac"] = r["p"]["A_plac"]
        out[f"{name}_b_plac"] = r["coef"]["A_plac"]
        if name == "joint":
            out["joint_irr_sd_A"] = r["irr_sd"]["A_cont"]
            out["joint_p_A"] = r["p"]["A_cont"]
    return out


def placebo_host(G: dict, s: pd.DataFrame, draws: int, strat: str, seed: int) -> tuple[pd.DataFrame, dict]:
    arr = placebo.build_arrays(G, s)
    labels = sorted(G["tax"]["sub_field"])
    cand = placebo_candidates(G, s, labels, strat)
    payload = {"s": s, "arr": arr, "cand": cand, "xs": CTRL2}
    with ProcessPoolExecutor(config.detect_cpus(), mp_context=mp.get_context("spawn"), initializer=_init_worker,
                             initargs=(payload,)) as ex:
        res = pd.DataFrame(list(ex.map(_plac_draw, [seed + i for i in range(draws)], chunksize=4)))
    res["strat"] = strat
    ok = res[res.plac_ok]
    pos_sig = ((ok.plac_p_plac < 0.05) & (ok.plac_irr_sd_plac > 1)).mean() if len(ok) else np.nan
    med = float(ok.plac_irr_sd_plac.median()) if len(ok) else np.nan
    summ = {"strat": strat, "draws": draws, "fit_failures": int((~res.plac_ok).sum()),
            "events_without_candidate": int(sum(len(c) == 0 for c in cand)), "n_events": int(len(s)),
            "median_candidates": float(np.median([len(c) for c in cand])),
            "placebo_irr_sd_median": med,
            "placebo_irr_sd_q025_q975": [float(ok.plac_irr_sd_plac.quantile(.025)), float(ok.plac_irr_sd_plac.quantile(.975))] if len(ok) else None,
            "share_pos_sig": float(pos_sig),
            "joint_A_cont_irr_sd_median": float(res.joint_irr_sd_A.median()) if "joint_irr_sd_A" in res else None,
            "joint_A_cont_share_p05": float((res.joint_p_A < 0.05).mean()) if "joint_p_A" in res else None,
            "joint_plac_irr_sd_median": float(res.joint_irr_sd_plac.median()) if "joint_irr_sd_plac" in res else None,
            "pass_rule": "PASS if share_pos_sig <= 0.10 AND median placebo IRR/SD < 1.10"}
    summ["PASS"] = bool(summ["share_pos_sig"] <= 0.10 and med < 1.10)
    return res, summ
