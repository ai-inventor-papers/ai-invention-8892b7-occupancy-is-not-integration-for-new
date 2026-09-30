"""STEP 6c: Gate B power (PPML b2 on Sink x Cool) by simulation on the realised / upper-bound / projected designs.

Uses only W1 host volumes, labels, W1 momentum and ORIGIN cooling onsets (origin.py); no host W2 counts are read.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from loguru import logger

import io_load
from common import RESULTS, SEED, detect_cpus

OUT = RESULTS / "power"
GRID = [-5, -10, -15, -20, -25, -35, -50, -60]
N_SIMS = 300
TAUS = 5


def episodes(e: pd.DataFrame, on: pd.DataFrame, theta: float, n_min_col: str = "state_main") -> dict:
    ons = on.set_index("concept_id")[f"onset_{theta}"]
    out = {}
    lab = e[e[n_min_col].isin(["SOURCE", "SINK", "FADING"])]
    eps = []
    for (c, t), g in lab.groupby(["concept_id", "t"]):
        o = ons.get(c)
        if pd.notna(o) and t + 1 <= o <= t + 5 and (g[n_min_col] == "SOURCE").any() and (g[n_min_col] == "SINK").any():
            eps.append((c, t, int(o)))
    out["labelled"] = eps
    nm = int(e.n_min_main.iloc[0])
    tested = e[(e.n_children >= nm) & (e.n_parents >= 1) & (e.n_traced >= 1)]
    ub = []
    for (c, t), g in tested.groupby(["concept_id", "t"]):
        o = ons.get(c)
        if len(g) >= 2 and pd.notna(o) and t + 1 <= o <= t + 5:
            ub.append((c, t, int(o)))
    out["upper_bound"] = ub
    t5 = e[(e.n_children >= 5) & (e.n_parents >= 1) & (e.n_traced >= 1)]
    ub5 = []
    for (c, t), g in t5.groupby(["concept_id", "t"]):
        o = ons.get(c)
        if len(g) >= 2 and pd.notna(o) and t + 1 <= o <= t + 5:
            ub5.append((c, t, int(o)))
    out["upper_bound_nmin5"] = ub5
    return out


def design_table(eps: list, e: pd.DataFrame, n_min: int, labelled: bool) -> pd.DataFrame:
    rows = []
    idx = e.set_index(["concept_id", "t"])
    for c, t, o in eps:
        g = idx.loc[(c, t)]
        g = g if isinstance(g, pd.DataFrame) else g.to_frame().T
        g = g[(g.n_children >= n_min) & (g.n_parents >= 1) & (g.n_traced >= 1)]
        if labelled:
            g = g[g.state_main.isin(["SOURCE", "SINK"])]
            sink = (g.state_main == "SINK").astype(int)
        else:  # descriptive proxy for the upper-bound design: observed SINK, else rho~ < 1 and m > 0.5
            sink = ((g.state_main == "SINK") | ((g.rho_tilde < 1) & (g.m > 0.5))).astype(int)
        for (_, r), s in zip(g.iterrows(), sink):
            rows.append({"ep": f"{c}_{t}", "cid": c, "t": t, "onset": o, "d": int(r.d), "v": float(r.n_w1),
                         "mom": float(r.mom), "sink": int(s)})
    df = pd.DataFrame(rows)
    if len(df):
        df["mom"] = (df.mom - df.mom.mean()) / (df.mom.std() or 1)
    return df


def phi_mom(e: pd.DataFrame, G: dict, n_min: int) -> float:
    """1/phi = sum(s2 - m) / sum(m^2) over W1 yearly host counts of tested edges (method of moments)."""
    t = e[(e.n_children >= n_min) & (e.n_parents >= 1)]
    num = den = 0.0
    for r in t.itertuples():
        p = G["per"][r.concept_id]["papers"]
        yrs = p.year[(p["sub"] == r.d) & (p.year <= r.t)].to_numpy()
        cnt = np.array([(yrs == y).sum() for y in range(r.t - 5, r.t + 1)], float)
        m, s2 = cnt.mean(), cnt.var(ddof=1)
        num += s2 - m
        den += m * m
    inv = num / den if den > 0 else 0.1
    return float(np.clip(1 / max(inv, 1e-2), 0.1, 100))


def panel(des: pd.DataFrame) -> pd.DataFrame:
    p = des.loc[des.index.repeat(TAUS)].reset_index(drop=True)
    p["tau"] = np.tile(np.arange(1, TAUS + 1), len(des)) + p.t
    p["cool"] = (p.tau >= p.onset).astype(int)
    p["lv"] = np.log(p.v / 6)
    return p


def simulate_y(p: pd.DataFrame, b2: float, phi: float, rng: np.random.Generator) -> np.ndarray:
    ep_tau = pd.factorize(p.ep + "_" + p.tau.astype(str))[0]
    d_tau = pd.factorize(p.d.astype(str) + "_" + p.tau.astype(str))[0]
    a = rng.normal(0, 0.3, ep_tau.max() + 1)[ep_tau]
    g = rng.normal(0, 0.2, d_tau.max() + 1)[d_tau]
    eta = p.lv.to_numpy() + a + g + b2 * p.sink * p.cool + 0.1 * p.mom * p.cool
    mu = np.exp(eta.to_numpy() if hasattr(eta, "to_numpy") else eta)
    return rng.negative_binomial(phi, phi / (phi + mu))


def _arrays(p: pd.DataFrame):
    X = np.column_stack([p.sink, p.sink * p.cool, p.mom, p.mom * p.cool]).astype(float)
    f1 = pd.factorize(p.ep + "_" + p.tau.astype(str))[0]
    f2 = pd.factorize(p.d.astype(str) + "_" + p.tau.astype(str))[0]
    return X, [f1, f2]


def fit_b2(p: pd.DataFrame) -> tuple[float, float] | None:
    """PPML y ~ sink + sink:cool + mom + mom:cool | ep^tau + d^tau, offset log(v/6), CRV1 by concept (ppml.py;
    numerically equal to pyfixest.fepois with the scipy demeaner, see tests/test_ppml.py)."""
    import ppml
    X, fes = _arrays(p)
    r = ppml.fit(p.y.to_numpy(), X, fes, p.lv.to_numpy(), p.cid.to_numpy())
    if r is None or not np.isfinite(r["se"][1]) or r["G"] < 2:
        return None
    return float(r["coef"][1]), float(r["se"][1])


def wild_score_pvalue(p: pd.DataFrame, rng: np.random.Generator, reps: int = 199) -> float | None:
    """Kline-Santos wild cluster (Rademacher) score bootstrap of b2 = 0 (restricted PPML with the same FEs)."""
    import ppml
    X, fes = _arrays(p)
    return ppml.wild_score_test(p.y.to_numpy(), X[:, [0, 2, 3]], X[:, 1], fes, p.lv.to_numpy(), p.cid.to_numpy(), rng, reps)


def sim_task(args: dict) -> dict:
    des = pd.DataFrame(args["des"])
    rng = np.random.default_rng(args["seed"])
    b2 = np.log(1 + args["pct"] / 100)
    cl = des.cid.unique()
    rej = fails = size_crv = 0
    wild = []
    for s in range(args["n_sims"]):
        if args.get("subsample"):
            pick = rng.choice(cl, size=int(round(args["target_clusters"])), replace=False)
            d = des[des.cid.isin(pick)]
        elif args["target_clusters"] and args["target_clusters"] > len(cl):
            pick = rng.choice(cl, size=int(round(args["target_clusters"])), replace=True)
            parts = []
            for i, c in enumerate(pick):
                q = des[des.cid == c].copy()
                q["cid"] = f"{c}#{i}"
                q["ep"] = q.ep + f"#{i}"
                parts.append(q)
            d = pd.concat(parts, ignore_index=True)
        else:
            d = des
        p = panel(d)
        p["y"] = simulate_y(p, b2, args["phi"], rng)
        r = fit_b2(p)
        if r is None:
            fails += 1
            continue
        rej += (r[0] + 1.96 * r[1]) < 0
        size_crv += abs(r[0]) > 1.96 * r[1]
        if args.get("wild") and s < 100:
            wp = wild_score_pvalue(p, rng)
            if wp is not None:
                wild.append(wp)
    n = args["n_sims"]
    return {"key": args["key"], "pct": args["pct"], "power": rej / n, "fail_share": fails / n,
            "two_sided_reject_crv": size_crv / n, "wild_size_005": float(np.mean(np.array(wild) < 0.05)) if wild else None,
            "wild_n": len(wild)}


def run(n_sims: int = N_SIMS) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    G = io_load.prepare()
    e = pd.read_csv(RESULTS / "viability" / "viability_layer.csv")
    on = pd.read_csv(RESULTS / "origin" / "cooling_onsets.csv")
    proj = json.loads((OUT / "projection.json").read_text())
    nm = int(e.n_min_main.iloc[0])
    counts = {}
    for th in [0.6, 0.7, 0.8]:
        ep = episodes(e, on, th)
        counts[f"theta_{th}"] = {k: {"episodes": len(v), "clusters": len({c for c, _, _ in v})} for k, v in ep.items()}
    ep7 = episodes(e, on, 0.7)
    phi = phi_mom(e, G, nm)
    ratio = proj[f"n_min_{nm}"]["projected_N_c"] / max(proj[f"n_min_{nm}"]["realised_N_c"], 1)
    designs = {}
    d_lab = design_table(ep7["labelled"], e, nm, True)
    d_ub = design_table(ep7["upper_bound"], e, nm, False)
    d_ub5 = design_table(ep7["upper_bound_nmin5"], e, 5, False)
    for name, des in [("realised_labelled", d_lab), ("upper_bound", d_ub), ("upper_bound_nmin5", d_ub5)]:
        ncl = des.cid.nunique() if len(des) else 0
        designs[name] = {"des": des, "clusters": ncl, "target": None}
    if designs["upper_bound"]["clusters"]:
        designs["projected_upper_bound"] = {"des": d_ub, "clusters": designs["upper_bound"]["clusters"],
                                            "target": designs["upper_bound"]["clusters"] * ratio}
    if designs["upper_bound_nmin5"]["clusters"]:
        designs["projected_upper_bound_nmin5"] = {"des": d_ub5, "clusters": designs["upper_bound_nmin5"]["clusters"],
                                                  "target": designs["upper_bound_nmin5"]["clusters"] * ratio}
    # hypothetical cluster-count designs (clearly NOT the realised design): all (c,t) with >= 2 tested hosts at
    # n_min 5, cooling onset drawn uniformly in W2; concepts bootstrapped to 10/30/60/120 clusters
    t5 = e[(e.n_children >= 5) & (e.n_parents >= 1) & (e.n_traced >= 1)]
    g5 = t5.groupby(["concept_id", "t"]).size()
    rng_h = np.random.default_rng([SEED, 72])
    hyp_eps = [(c, t, int(t + rng_h.integers(1, 6))) for c, t in g5[g5 >= 2].index]
    d_hyp = design_table(hyp_eps, e, 5, False)
    for ncl in [10, 30, 60, 120]:
        designs[f"hypothetical_{ncl}_clusters"] = {"des": d_hyp, "clusters": d_hyp.cid.nunique(), "target": float(ncl),
                                                   "subsample": ncl < d_hyp.cid.nunique()}
    tasks, info = [], {}
    for name, dd in designs.items():
        eff = int(round(dd["target"] or dd["clusters"]))
        info[name] = {"clusters": dd["clusters"], "target_clusters": dd["target"], "episodes": int(dd["des"].ep.nunique()) if len(dd["des"]) else 0,
                      "hosts": int(len(dd["des"])), "sink_share": float(dd["des"].sink.mean()) if len(dd["des"]) else None}
        if eff < 10 or len(dd["des"]) == 0 or dd["des"].sink.nunique() < 2:
            info[name]["MDE"] = "not estimable (< 10 clusters or no sink variation)"
            continue
        for pct in [0] + GRID:
            tasks.append({"key": name, "pct": pct, "des": dd["des"].to_dict("list"), "phi": phi, "n_sims": n_sims,
                          "target_clusters": dd["target"], "seed": [SEED, 71, len(tasks)],
                          "wild": pct == 0 and eff < 30, "subsample": dd.get("subsample", False)})
    logger.info(f"Gate B: phi={phi:.2f}; designs {info}; {len(tasks)} tasks")
    res = []
    t0 = time.time()
    if tasks:
        with ProcessPoolExecutor(max_workers=min(4, detect_cpus()), mp_context=mp.get_context("spawn")) as ex:
            futs = [ex.submit(sim_task, t) for t in tasks]
            for i, f in enumerate(as_completed(futs)):
                res.append(f.result())
                logger.info(f"Gate B {i + 1}/{len(tasks)} ({time.time() - t0:.0f}s)")
    rows = pd.DataFrame(res)
    if len(rows):
        rows.to_csv(OUT / "gate_b_power_curves.csv", index=False)
    for name in info:
        r = rows[rows.key == name] if len(rows) else pd.DataFrame()
        if not len(r):
            continue
        r = r.set_index("pct")
        info[name]["power_by_pct"] = {int(k): float(v) for k, v in r.power.items()}
        info[name]["size_b2_0_one_sided"] = float(r.power.get(0, np.nan))
        info[name]["size_b2_0_two_sided_crv"] = float(r.two_sided_reject_crv.get(0, np.nan))
        info[name]["wild_size_005"] = r.wild_size_005.get(0)
        info[name]["fail_share_mean"] = float(r.fail_share.mean())
        m = "> 60% (not reached)"
        prev = (0, 0.0)
        for pct in GRID:
            pw = float(r.power[pct])
            if pw >= 0.8:
                a, pa = abs(prev[0]), prev[1]
                m = float(a + (0.8 - pa) * (abs(pct) - a) / (pw - pa)) if pw != pa else float(abs(pct))
                break
            prev = (pct, pw)
        info[name]["MDE_pct"] = m
    real = info["realised_labelled"]
    gate_b = "FAIL" if (not isinstance(real.get("MDE_pct"), float) or real["MDE_pct"] > 25) else "PASS"
    out = {"episode_counts": counts, "phi": phi, "projection_ratio": ratio, "designs": info,
           "gate_B_verdict": gate_b + " (realised labelled design)" + ("; H2 demoted to secondary" if gate_b == "FAIL" else ""),
           "rule": "FAIL if MDE > 25% or < 10 clusters (MDE not estimable)"}
    (OUT / "gate_b.json").write_text(json.dumps(out, indent=2, default=float))
    logger.info(f"Gate B verdict: {out['gate_B_verdict']}")
    write_decisions()


def write_decisions() -> dict:
    """6d decision lines."""
    proj = json.loads((OUT / "projection.json").read_text())
    h1 = json.loads((OUT / "h1_mde.json").read_text())
    gb = json.loads((OUT / "gate_b.json").read_text())
    e = pd.read_csv(RESULTS / "viability" / "viability_layer.csv", usecols=["n_min_main"])
    nm = int(e.n_min_main.iloc[0])
    pr = proj[f"n_min_{nm}"]
    mde = {k: v["MDE"] for k, v in h1.items() if k.startswith("auc|") and f"nmin{nm}|" in k}
    real = pr["realised_N_c"]
    status = ("testable" if real >= 150 else
              f"pilot only (realised N_c = {real}; MDE delta-AUC = {mde.get(f'auc|nmin{nm}|AUC0.7|realised')} at BASE 0.70, "
              f"{mde.get(f'auc|nmin{nm}|AUC0.8|realised')} at BASE 0.80)")
    d = {"n_min_main": nm, "realised_N_c": real, "realised_ge_150": real >= 150,
         "projected_N_c": pr["projected_N_c"], "projected_N_c_90": pr.get("projected_N_c_90"),
         "projected_ge_150": pr["projected_N_c"] >= 150,
         "realised_and_projected_by_nmin": {k: {"realised": v["realised_N_c"], "projected": v["projected_N_c"]}
                                            for k, v in proj.items() if k.startswith("n_min_")},
         "H1_status": status, "H1_MDE_main_nmin": mde,
         "H1_MDE_all_cells": {k: v["MDE"] for k, v in h1.items()},
         "H1_size_at_gamma0": {k: v["size_at_gamma0"] for k, v in h1.items()},
         "maillart_endogenous_R2_prior": 0.018,
         "gate_B_verdict": gb["gate_B_verdict"],
         "gate_B_MDE_by_design": {k: v.get("MDE_pct", v.get("MDE")) for k, v in gb["designs"].items()},
         "gate_A_verdict": json.loads((RESULTS / "gate_a" / "gate_A_verdict.json").read_text())["verdict"]}
    (OUT / "decisions.json").write_text(json.dumps(d, indent=2, default=float))
    logger.info(f"decisions: {d['H1_status']} | Gate B {d['gate_B_verdict']}")
    return d
