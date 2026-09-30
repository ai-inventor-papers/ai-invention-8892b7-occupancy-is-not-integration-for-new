"""STAGE 10: PPML rows, inference, placebo, crosscheck, comparison with the main pool, G4 verdict (MeSH, one look).

Estimator: vendored exp_7 ppml.fit via models.fit_one (IRLS, exact sparse FE projection, iterated singleton and
separation pruning), offset log(n_entry_papers), CRV1 by concept (pyfixest small-sample factor), Kline-Santos wild
cluster score bootstrap (Rademacher, H0 imposed; 999 draws for R1/R2, 499 otherwise). A_cont and CT effects are
reported per SD on the retained estimation sample and per 0.1. Holm over {A_cont, CT} within R1 and within R2.
Rows follow the frozen mesh_spec.json (row list in ROWS below; any row the spec marks as dropped is skipped).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

import common
from common import MAIN_COPRIMARY, MAIN_NONPHYS, MAIN_PHYS, RESULTS, SEED, dump

_S: dict = {}


def sample(df: pd.DataFrame, need: list[str]) -> pd.DataFrame:
    from power_mesh import fe_cols
    s = df.dropna(subset=[c for c in need if c in df.columns]).copy()
    return fe_cols(s).reset_index(drop=True)


def fit_row(s: pd.DataFrame, y: str, xvars: list[str], spec: str, wild_vars: tuple = (), reps: int = 999,
            rng=None) -> dict | None:
    import models as vmodels
    import ppml
    if len(s) < len(xvars) + 10:
        return None
    try:
        r = vmodels.fit_one(s, y, xvars, spec)
    except (np.linalg.LinAlgError, RuntimeError, ValueError) as ex:
        logger.warning(f"fit failed {spec} {y}: {ex!r}")
        return None
    if r is None:
        return None
    if wild_vars:
        rng = rng or np.random.default_rng(SEED)
        X = s[xvars].to_numpy(float)
        fes = vmodels.fe_arrays(s, spec)
        r["p_wild"] = {}
        for v in wild_vars:
            j = xvars.index(v)
            r["p_wild"][v] = ppml.wild_score_test(s[y].to_numpy(float), np.delete(X, j, axis=1), X[:, j], fes,
                                                  s.offset.to_numpy(), s.concept_id.to_numpy(), rng, reps=reps)
    r["n_concepts_input"] = int(s.concept_id.nunique())
    return r


def compact(r: dict | None, vars_: tuple = ("A_cont", "CT")) -> dict | None:
    if r is None:
        return None
    out = {"spec": r["spec"], "y": r["y"], "N": r["n_retained"], "N_input": r["n_input"], "G": r["G"],
           "retained_share": r["retained_share"], "controls": [x for x in r["x"] if x not in vars_]}
    for v in r["x"]:
        if v in vars_ or v in ("NATIVE", "ADJACENT", "A_placebo", "A_cont_lo", "A_cont_hi", "A_cont_exact"):
            out[v] = {"b": r["coef"][v], "se": r["se"][v], "p_crv1": r["p"][v], "irr_sd": r["irr_sd"][v],
                      "ci_irr_sd": r["ci_irr_sd"][v], "irr_01": r["irr_01"][v], "sd": r["sd_retained"][v],
                      "p_wild": (r.get("p_wild") or {}).get(v)}
    return out


def decide_row(r: dict, a: str = "A_cont") -> dict:
    import models as vmodels
    rr = dict(r)
    if a != "A_cont":
        rr = {**r, "coef": {**r["coef"], "A_cont": r["coef"][a]}, "p": {**r["p"], "A_cont": r["p"][a]}}
    return vmodels.decide(rr)


# ------------------------------------------------------------------------------------------------------ placebo
def perm_arrays(G: dict, nat, s: pd.DataFrame) -> dict:
    """Share tensor over all profiled nodes (exact + admitted bg) and the profiled tags of each event in s."""
    from features import block_of
    BLK = common.BLOCKS
    subs = sorted(G["tax"]["sub_field"])
    lab = {x: i for i, x in enumerate(subs)}
    W = G["W"]
    ptr, idx = G["P"]
    con = G["concepts"].set_index("concept_id")
    te, tn_raw, tb, td = [], [], [], []
    for i, ev in enumerate(s.itertuples()):
        c = con.loc[ev.concept_id]
        own = set(c.own_nodes)
        r, y = G["links"][ev.concept_id]
        sub = W["sub"][r]
        er = r[(sub == ev.d) & (y == ev.e)]
        blk = block_of(int(ev.e))
        for row in er:
            for j in idx[ptr[row]:ptr[row + 1]].tolist():
                if j in own:
                    continue
                if nat.share(int(j), blk, int(ev.d))[0] is None:
                    continue
                te.append(i)
                tn_raw.append(int(j))
                tb.append(BLK.index(blk))
                td.append(lab[int(ev.d)])
    nodes = sorted(set(tn_raw))
    nid = {x: k for k, x in enumerate(nodes)}
    S = np.zeros((len(nodes), 4, len(subs)))
    for j in nodes:
        for b in BLK[:3]:
            p = nat.exact.get((j, b))
            if p is not None:
                tot, counts, _ = p
                if tot > 0:
                    for sf, n in counts.items():
                        if sf in lab:
                            S[nid[j], BLK.index(b), lab[sf]] = n / tot
                continue
            v = nat.bg.get((j, b))
            if v is not None:
                for sf, w in v[2].items():
                    if sf in lab:
                        S[nid[j], BLK.index(b), lab[sf]] = w / v[1]
    return {"S": S, "te": np.array(te), "tn": np.array([nid[j] for j in tn_raw]), "tb": np.array(tb),
            "td": np.array(td), "n": len(s), "n_labels": len(subs)}


def _pinit(rows: dict, arr: dict):
    _S.update(rows=rows, arr=arr)


def _pdraw(seed: int) -> dict:
    import placebo as vplacebo
    arr = _S["arr"]
    rng = np.random.default_rng(seed)
    perm = np.stack([rng.permutation(arr["n_labels"]) for _ in range(arr["S"].shape[0])])
    a = vplacebo.a_cont(arr, perm)
    out = {"seed": seed}
    for name, (s, xs, spec) in _S["rows"].items():
        ss = s.copy()
        ss["A_cont"] = a[ss["_pos"].to_numpy()]
        r = fit_row(ss, "Y_strict", ["A_cont", "CT"] + xs, spec)
        out[f"z_A_{name}"] = None if r is None else r["coef"]["A_cont"] / r["se"]["A_cont"]
        out[f"lnirr_sd_A_{name}"] = None if r is None else float(np.log(r["irr_sd"]["A_cont"]))
    return out


def _shuffle(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    s, xs, spec = _S["rows"]["R2"]
    ss = s.copy()
    y = ss.Y_strict.to_numpy().copy()
    for _, ix in ss.groupby("cfe").indices.items():
        y[ix] = y[ix][rng.permutation(len(ix))]
    ss["Y_strict"] = y
    r = fit_row(ss, "Y_strict", ["A_cont", "CT"] + xs, spec)
    return {"seed": seed, "z_A_R2": None if r is None else r["coef"]["A_cont"] / r["se"]["A_cont"]}


def placebo_run(G: dict, nat, s_full: pd.DataFrame, rows: dict, obs: dict, draws: int, shuffles: int,
                out_dir=None) -> dict:
    out_dir = out_dir or RESULTS
    import placebo as vplacebo
    arr = perm_arrays(G, nat, s_full)
    chk = vplacebo.a_cont(arr)
    diff = float(np.nanmax(np.abs(chk - s_full.A_cont.to_numpy())))
    if not diff < 1e-9:
        raise RuntimeError(f"placebo A_cont reconstruction differs by {diff}")
    seeds = [SEED + 1000 + i for i in range(draws)]
    with ProcessPoolExecutor(common.detect_cpus(), mp_context=mp.get_context("spawn"), initializer=_pinit,
                             initargs=(rows, arr)) as ex:
        res = pd.DataFrame(list(ex.map(_pdraw, seeds, chunksize=4)))
        sh = pd.DataFrame(list(ex.map(_shuffle, [SEED + 5000 + i for i in range(shuffles)], chunksize=2)))
    res.to_csv(out_dir / "placebo_draws_mesh.csv", index=False)
    sh.to_csv(out_dir / "outcome_shuffle_draws_mesh.csv", index=False)
    out = {"draws": draws, "shuffles": shuffles, "A_cont_reconstruction_max_abs_diff": diff,
           "permutation": "per-node permutation of the subfield labels (same for all blocks), vendored placebo.a_cont"}
    for name in rows:
        o = obs[name]
        if o is None:
            continue
        zo = o["coef"]["A_cont"] / o["se"]["A_cont"]
        eo = float(np.log(o["irr_sd"]["A_cont"]))
        z = res[f"z_A_{name}"].dropna()
        e = res[f"lnirr_sd_A_{name}"].dropna()
        out[name] = {"z_obs": zo, "lnirr_sd_obs": eo, "n_ok": int(len(z)), "placebo_z_mean": float(z.mean()),
                     "placebo_z_sd": float(z.std()),
                     "perm_p_two_sided_z": float((1 + (z.abs() >= abs(zo)).sum()) / (1 + len(z))),
                     "perm_p_two_sided_per_sd_effect": float((1 + (e.abs() >= abs(eo)).sum()) / (1 + len(e))),
                     "placebo_lnirr_sd_mean": float(e.mean()), "placebo_lnirr_sd_sd": float(e.std())}
    if obs.get("R2") is not None:
        zo = obs["R2"]["coef"]["A_cont"] / obs["R2"]["se"]["A_cont"]
        lz = sh["z_A_R2"].dropna()
        out["outcome_shuffle_within_concept_R2"] = {"n": int(len(lz)), "z_mean": float(lz.mean()),
                                                    "z_sd": float(lz.std()),
                                                    "p_two_sided_z": float((1 + (lz.abs() >= abs(zo)).sum()) / (1 + len(lz)))}
    return out


def crosscheck_pyfixest(s: pd.DataFrame, xvars: list[str], r_own: dict) -> dict:
    import ppml
    import pyfixest as pf
    import models as vmodels
    rr = ppml.fit(s.Y_strict.to_numpy(float), s[xvars].to_numpy(float), vmodels.fe_arrays(s, "secondary"),
                  s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    d = s[rr["keep"]].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.fepois(f"Y_strict ~ {' + '.join(xvars)} | cfe + efe + dfe", data=d, offset="offset",
                      vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-12, iwls_tol=1e-12,
                      iwls_maxiter=500)
    cf, se = m.coef(), m.se()
    per = {v: {"coef_own": r_own["coef"][v], "coef_pf": float(cf[v]), "abs_diff": abs(r_own["coef"][v] - float(cf[v])),
               "se_own": r_own["se"][v], "se_pf": float(se[v]),
               "se_rel_diff": abs(r_own["se"][v] - float(se[v])) / float(se[v])} for v in ("A_cont", "CT")}
    return {"pass_coef_1e-4": all(x["abs_diff"] < 1e-4 for x in per.values()),
            "pass_se_rel_1e-3": all(x["se_rel_diff"] < 1e-3 for x in per.values()), "n_pf": int(m._N), "per_var": per}


# --------------------------------------------------------------------------------------------------- comparison
def compare(r2: dict) -> dict:
    b, se, sd = r2["coef"]["A_cont"], r2["se"]["A_cont"], r2["sd_retained"]["A_cont"]
    l_m, s_m = b * sd, se * sd
    out = {"mesh_R2": {"ln_irr_sd": l_m, "se": s_m, "irr_sd": float(np.exp(l_m))}}
    refs = {"main_coprimary_1.30": (MAIN_COPRIMARY["b_A"], MAIN_COPRIMARY["se_A"], MAIN_COPRIMARY["irr_sd"]),
            "main_nonphysics_1.29": (MAIN_NONPHYS["b_A"], MAIN_NONPHYS["se_A"], MAIN_NONPHYS["irr_sd"])}
    for k, (bm, sem, irr) in refs.items():
        sd_m = np.log(irr) / bm
        l_r, s_r = np.log(irr), sem * sd_m
        z = (l_m - l_r) / np.sqrt(s_m ** 2 + s_r ** 2)
        w1, w2 = 1 / s_m ** 2, 1 / s_r ** 2
        lp = (w1 * l_m + w2 * l_r) / (w1 + w2)
        sp = np.sqrt(1 / (w1 + w2))
        q = w1 * (l_m - lp) ** 2 + w2 * (l_r - lp) ** 2
        i2 = max(0.0, (q - 1) / q) if q > 0 else 0.0
        out[k] = {"ref_ln_irr_sd": float(l_r), "ref_se": float(s_r), "dlog": float(l_m - l_r), "z": float(z),
                  "p_two_sided": float(2 * stats.norm.sf(abs(z))), "ivw_pooled_irr_sd": float(np.exp(lp)),
                  "ivw_ci": [float(np.exp(lp - 1.96 * sp)), float(np.exp(lp + 1.96 * sp))],
                  "cochran_Q": float(q), "I2": float(i2)}
    return out


def verdict(a: dict, holm_p: float, p_wild: float | None, mde80: float | None, coverage: float,
            underpowered_by_design: bool) -> dict:
    """a = compact A_cont entry of the R2 row: {'irr_sd', 'ci_irr_sd', ...}."""
    irr = a["irr_sd"]
    lo, hi = a["ci_irr_sd"]
    if irr > 1 and lo > 1 and holm_p < 0.05 and (p_wild is not None and p_wild < 0.05):
        v = "REPLICATED"
    elif irr < 1 and hi < 1 and holm_p < 0.05:
        v = "REVERSED"
    elif mde80 is None or mde80 > 1.29 or underpowered_by_design:
        v = "UNDERPOWERED"
    else:
        v = "NOT_REPLICATED"
    ceiling = None
    if coverage < 0.5 and v == "REPLICATED":
        ceiling, v = "COVERAGE_LIMITED", "COVERAGE_LIMITED"
    return {"verdict": v, "irr_sd": irr, "ci95": [lo, hi], "holm_p": holm_p, "p_wild": p_wild, "MDE80_R2": mde80,
            "tag_weighted_coverage": coverage, "ceiling_applied": ceiling,
            "rule": "REPLICATED if IRR/SD > 1, 95% CI excludes 1, Holm p < .05 and p_wild < .05; REVERSED if "
                    "significantly < 1; else UNDERPOWERED if MDE80(R2) > 1.29, else NOT_REPLICATED ('claim restricted "
                    "to the physical/CS pool'); coverage < 0.5 caps REPLICATED at COVERAGE_LIMITED"}


# ---------------------------------------------------------------------------------------------------------- run
def run(src=None, out_dir=None, spec: dict | None = None, draws: int | None = None,
        shuffles: int | None = None) -> dict:
    src = src or RESULTS
    out_dir = out_dir or RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)
    import features_mesh
    import load_mesh
    import models as vmodels
    spec = spec or json.loads((RESULTS / "mesh_spec.json").read_text())
    pc, sc = spec["models"]["primary_controls"], spec["models"]["secondary_controls"]
    draws = draws or spec["placebo"]["draws"]
    shuffles = shuffles or spec["placebo"]["outcome_shuffles"]
    rng = np.random.default_rng(SEED)
    om = pd.read_parquet(src / "outcomes_mesh.parquet")
    need = ["A_cont", "CT"] + sc
    s = sample(om, need)
    s["_pos"] = np.arange(len(s))
    base = {"n_events_outcomes": int(len(om)), "n_sample": int(len(s)), "n_concepts": int(s.concept_id.nunique()),
            "dropped_missing_controls": int(len(om) - len(s))}
    logger.info(f"model sample: {base}")
    R, rows_csv = {}, []

    def add(key, label, r, a="A_cont"):
        R[key] = {"label": label, "row": compact(r, ("A_cont", "CT", a))}
        if r is not None:
            for v in [a, "CT"] if a != "NATIVE" else ["NATIVE", "ADJACENT", "CT"]:
                if v in r["coef"]:
                    rows_csv.append({"key": key, "label": label, "spec": r["spec"], "y": r["y"], "var": v,
                                     "b": r["coef"][v], "se": r["se"][v], "p_crv1": r["p"][v],
                                     "p_wild": (r.get("p_wild") or {}).get(v), "irr_sd": r["irr_sd"][v],
                                     "irr_sd_lo": r["ci_irr_sd"][v][0], "irr_sd_hi": r["ci_irr_sd"][v][1],
                                     "irr_01": r["irr_01"][v], "sd": r["sd_retained"][v], "N": r["n_retained"],
                                     "G": r["G"], "retained_share": r["retained_share"]})
        else:
            rows_csv.append({"key": key, "label": label, "note": "not estimable (too few observations / fit failed)"})
        logger.info(f"{key}: {None if r is None else (r['n_retained'], r['G'], round(r['irr_sd'].get(a, np.nan), 3), round(r['p'].get(a, np.nan), 4))}")

    r1 = fit_row(s, "Y_strict", ["A_cont", "CT"] + pc, "primary", ("A_cont", "CT"), 999, rng)
    r2 = fit_row(s, "Y_strict", ["A_cont", "CT"] + sc, "secondary", ("A_cont", "CT"), 999, rng)
    add("R1", "primary: concept x e + d x e", r1)
    add("R2", "co-primary (G4-decisive): concept + e + d", r2)
    add("R3", "concept + d x e", fit_row(s, "Y_strict", ["A_cont", "CT"] + pc, "c_plus_dxe", ("A_cont",), 499, rng))
    add("R4", "concept x 2-year bin + d x e", fit_row(s, "Y_strict", ["A_cont", "CT"] + pc, "coarse_cx2y", ("A_cont",), 499, rng))
    add("R2_A_only", "co-primary, A_cont without CT", fit_row(s, "Y_strict", ["A_cont"] + sc, "secondary"))
    # S1 G1 multi-team entry
    og = pd.read_parquet(src / "outcomes_mesh_g1.parquet")
    sg = sample(og, need)
    add("S1", "G1 multi-team entry (co-primary FE)", fit_row(sg, "Y_strict", ["A_cont", "CT"] + sc, "secondary",
                                                            ("A_cont",), 999, rng))
    add("S1_primary", "G1 multi-team entry (primary FE)", fit_row(sg, "Y_strict", ["A_cont", "CT"] + pc, "primary"))
    # S2 G2 decomposition
    s2 = s.dropna(subset=["NATIVE", "ADJACENT"])
    add("S2", "G2: NATIVE + ADJACENT (FOREIGN ref), co-primary",
        fit_row(s2, "Y_strict", ["NATIVE", "ADJACENT", "CT"] + sc, "secondary", ("NATIVE", "ADJACENT"), 499, rng), a="NATIVE")
    add("S2_primary", "G2: NATIVE + ADJACENT, primary", fit_row(s2, "Y_strict", ["NATIVE", "ADJACENT", "CT"] + pc, "primary"),
        a="NATIVE")
    # S3 placebo host
    s3 = s.dropna(subset=["A_placebo"])
    add("S3", "placebo host d' (A_placebo in place of A_cont), co-primary",
        fit_row(s3, "Y_strict", ["A_placebo", "CT"] + sc, "secondary", ("A_placebo",), 499, rng), a="A_placebo")
    add("S4", "A_cont_lo (unprofiled = 0)", fit_row(s, "Y_strict", ["A_cont_lo", "CT"] + sc, "secondary"), a="A_cont_lo")
    add("S5", "A_cont_hi (unprofiled = 1)", fit_row(s, "Y_strict", ["A_cont_hi", "CT"] + sc, "secondary"), a="A_cont_hi")
    add("S6", "coverage rule 0.50 subset (declared threshold)",
        fit_row(s[s.covered50], "Y_strict", ["A_cont", "CT"] + sc, "secondary"))
    add("S7", "coverage rule 0.70 subset", fit_row(s[s.covered70], "Y_strict", ["A_cont", "CT"] + sc, "secondary"))
    add("S8", "rule_parity concepts only (172)", fit_row(s[s.rule_parity], "Y_strict", ["A_cont", "CT"] + sc, "secondary"))
    add("S9", "retrieval_complete concepts dropped", fit_row(s[~s.retrieval_complete], "Y_strict", ["A_cont", "CT"] + sc,
                                                             "secondary"))
    add("S10", "Y_lenient", fit_row(s, "Y_lenient", ["A_cont", "CT"] + sc, "secondary"))
    add("S11", "Y_all", fit_row(s, "Y_all", ["A_cont", "CT"] + sc, "secondary"))
    sc_nt = [c for c in sc if c not in ("mean_topic_score", "boundary_share")]
    ou = pd.read_parquet(src / "outcomes_mesh_union.parquet")
    su = sample(ou, ["A_cont", "CT"] + sc_nt)
    add("S12", "union c-paper set (no topic controls)", fit_row(su, "Y_strict", ["A_cont", "CT"] + sc_nt, "secondary"))
    s13 = sample(om, ["A_cont", "CT"] + sc_nt)
    add("S13", "without topic-score controls", fit_row(s13, "Y_strict", ["A_cont", "CT"] + sc_nt, "secondary"))
    add("S14_health", "Health Sciences hosts (descriptive)", fit_row(s[s.domain_d == 4], "Y_strict", ["A_cont", "CT"] + sc,
                                                                      "secondary"))
    add("S14_life", "Life Sciences hosts (descriptive)", fit_row(s[s.domain_d == 1], "Y_strict", ["A_cont", "CT"] + sc,
                                                                  "secondary"))
    s16 = s.dropna(subset=["A_cont_exact"])
    add("S16", "exact-profile nativeness only (bg fill off)",
        fit_row(s16, "Y_strict", ["A_cont_exact", "CT"] + sc, "secondary"), a="A_cont_exact")
    add("S17", "kw5 subset (declared partner rule)", fit_row(s[s.kw5], "Y_strict", ["A_cont", "CT"] + sc, "secondary"))
    add("S18", "Y_strict with n_entry_papers == 1 (single-paper entries)",
        fit_row(s[s.n_entry_papers == 1], "Y_strict", ["A_cont", "CT"] + sc, "secondary"))
    try:
        lpm = {"primary": vmodels.lpm_fe(s, "EST_bin", ["A_cont", "CT"] + pc, "primary"),
               "secondary": vmodels.lpm_fe(s, "EST_bin", ["A_cont", "CT"] + sc, "secondary")}
    except Exception as ex:  # noqa: BLE001 - descriptive row; record and continue
        lpm = {"error": repr(ex)}
    R["S15"] = {"label": "EST_bin linear probability (same FE)", "row": lpm}
    # decisions
    thin = r1 is None or r1["retained_share"] < 0.30 or r1["G"] < 50
    dec = {"R1": decide_row(r1) if r1 else None, "R2": decide_row(r2) if r2 else None,
           "thin_cell_rule": {"triggered": bool(thin), "retained_share": None if r1 is None else r1["retained_share"],
                              "G": None if r1 is None else r1["G"],
                              "rule": "retained < 30% of events or G < 50 -> co-primary decisive"}}
    # placebo + shuffle
    nat = features_mesh.load_nat(json.loads((RESULTS / "nativeness_fallback_check.json").read_text())["admitted"])
    G = load_mesh.prepare()
    prow = {"R2": (s, sc, "secondary"), "R1": (s, pc, "primary")}
    pl = placebo_run(G, nat, s, prow, {"R1": r1, "R2": r2}, draws, shuffles, out_dir)
    dump(out_dir / "placebo_mesh.json", pl)
    cc = crosscheck_pyfixest(s, ["A_cont", "CT"] + sc, r2) if r2 else None
    cmp_ = compare(r2)
    pwp = RESULTS / "power_mesh.json"
    pw = json.loads(pwp.read_text()) if pwp.exists() else {"MDE80_irr_per_sd": {}}
    cov = float(s.n_prof_tags.sum() / s.n_tags.sum())
    esum = json.loads((RESULTS / "events_mesh_summary.json").read_text())
    g4 = verdict(R["R2"]["row"]["A_cont"], dec["R2"]["holm_p"]["A_cont"], R["R2"]["row"]["A_cont"]["p_wild"],
                 pw["MDE80_irr_per_sd"].get("R2"), cov, esum["underpowered_by_design"]) if r2 else {"verdict": "NOT_ESTIMABLE"}
    g4["reading_R2"] = dec["R2"]["reading"] if dec["R2"] else None
    g4["reading_R1"] = dec["R1"]["reading"] if dec["R1"] else None
    g4["prediction"] = spec["prediction"]
    g4["prediction_consistent"] = bool(r2 and R["R2"]["row"]["A_cont"]["irr_sd"] > 1)
    s1 = R.get("S1", {}).get("row")
    g4["mechanism"] = {"G1_multi_team": None if s1 is None else {"irr_sd": s1["A_cont"]["irr_sd"],
                                                                 "ci": s1["A_cont"]["ci_irr_sd"],
                                                                 "p_crv1": s1["A_cont"]["p_crv1"],
                                                                 "p_wild": s1["A_cont"]["p_wild"], "N": s1["N"], "G": s1["G"],
                                                                 "MDE80": pw["MDE80_irr_per_sd"].get("S1")}}
    s2r = R.get("S2", {}).get("row")
    if s2r:
        g4["mechanism"]["G2"] = {k: {"irr_sd": s2r[k]["irr_sd"], "ci": s2r[k]["ci_irr_sd"], "p_crv1": s2r[k]["p_crv1"],
                                     "p_wild": s2r[k]["p_wild"]} for k in ("NATIVE", "ADJACENT")}
        sig = {k: s2r[k]["p_crv1"] < 0.05 and s2r[k]["irr_sd"] > 1 for k in ("NATIVE", "ADJACENT")}
        g4["mechanism"]["G2_carrier"] = ("both" if all(sig.values()) else
                                         next((k for k, v in sig.items() if v), "neither"))
    out = {"sample": base, "rows": R, "decisions": dec, "placebo": pl, "pyfixest_crosscheck": cc,
           "comparison_main_vs_mesh": cmp_, "g4": g4, "spec_sha256": (RESULTS / "mesh_spec.sha256").read_text().split()[0]
           if (RESULTS / "mesh_spec.sha256").exists() else "DRY RUN (no freeze)"}
    dump(out_dir / "g4_models.json", out)
    pd.DataFrame(rows_csv).to_csv(out_dir / "g4_rows.csv", index=False)
    crow = [{"estimate": "MeSH R2 (co-primary)", **cmp_["mesh_R2"]}]
    for k in ("main_coprimary_1.30", "main_nonphysics_1.29"):
        crow.append({"estimate": k, "ln_irr_sd": cmp_[k]["ref_ln_irr_sd"], "se": cmp_[k]["ref_se"],
                     "irr_sd": float(np.exp(cmp_[k]["ref_ln_irr_sd"])), "dlog_mesh_minus_ref": cmp_[k]["dlog"],
                     "z": cmp_[k]["z"], "p": cmp_[k]["p_two_sided"], "ivw_pooled_irr_sd": cmp_[k]["ivw_pooled_irr_sd"],
                     "ivw_lo": cmp_[k]["ivw_ci"][0], "ivw_hi": cmp_[k]["ivw_ci"][1], "I2": cmp_[k]["I2"]})
    crow.append({"estimate": "main physics stratum (descriptive)", "irr_sd": MAIN_PHYS["irr_sd"]})
    pd.DataFrame(crow).to_csv(out_dir / "comparison_main_vs_mesh.csv", index=False)
    dump(out_dir / "g4_verdict.json", g4)
    logger.info(f"G4 VERDICT: {g4}")
    return out
