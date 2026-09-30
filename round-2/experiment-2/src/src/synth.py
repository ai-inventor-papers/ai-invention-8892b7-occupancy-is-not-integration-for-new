"""STEP 4: synthetic validation of the labeller with KNOWN states, running the unchanged production functions
(w1_view -> canonical_main -> parentage -> edge_vectors -> bootstrap_edge; reference_concept -> stationary_cells ->
rho0_table; assign_states).

Generative model per host edge (c, d, t): n_p cohort parents in d (years t-5..t-3); each parent has Poisson(R*lambda0)
local children (years uniform in [max(y_p, t-4), t]); imported children ~ Poisson(R*lambda0*n_p*iota/(1-iota)) each
with a true parent in the origin pool; a child has references with prob kappa, then cites its true parent with prob
pi, plus Poisson(0.3) noise citations to random earlier c-papers. 5% extra papers sit in the F year (canonical) and
top-5 cited_by_count papers are random (routing exercised). Stationary R = 1 reference concepts are built with the
same process (iota 0.3, n_p 40, flattened yearly counts) so rho0 is calibrated like the real one.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from loguru import logger

import benchmark
from common import RESULTS, SEED, detect_cpus, h32
from edges import reference_concept
from labels import assign_states, bootstrap_edge
from leakage import w1_view
from lineage import canonical_main, edge_vectors, parentage, point_estimates

OUT = RESULTS / "synth"
T = 2019
F_SYN = T - 6
ORIGIN = 9000
HOSTS = list(range(9001, 9009))
FIELD = {s: 90 for s in [ORIGIN] + HOSTS}
RS_ = [0.5, 0.8, 1.0, 1.3, 2.0]
IOTAS = [0.0, 0.3, 0.6, 0.9]
NPS = [5, 10, 20, 40, 80]


def truth(R: float, iota: float) -> str:
    if R > 1:
        return "SOURCE"
    if R < 1:
        return "SINK" if iota > 0.5 else "FADING"
    return "NULL"


class Builder:
    """Accumulates synthetic c-papers in the production schema."""

    def __init__(self, rng: np.random.Generator):
        self.rng = rng
        self.year, self.sub, self.nrefs = [], [], []
        self.cites = []

    def add(self, year: int, sub: int, has_refs: bool) -> int:
        self.year.append(int(year))
        self.sub.append(int(sub))
        self.nrefs.append(int(has_refs) * 10)
        return len(self.year) - 1

    def child(self, year: int, sub: int, parent: int | None, kappa: float, pi: float) -> int:
        has = self.rng.uniform() < kappa
        k = self.add(year, sub, has)
        if has:
            if parent is not None and self.rng.uniform() < pi:
                self.cites.append((k, parent))
            for _ in range(self.rng.poisson(0.3)):
                for _try in range(20):  # rejection sampling of a random earlier c-paper
                    j = int(self.rng.integers(0, max(k, 1)))
                    if k > 0 and self.year[j] <= year:
                        self.cites.append((k, j))
                        break
        return k

    def to_cdata(self) -> dict:
        n = len(self.year)
        cbc = self.rng.lognormal(1.0, 1.2, n).astype(np.int64)
        p = pd.DataFrame({"work_id": np.arange(1, n + 1, dtype=np.int64), "year": np.array(self.year, np.int32),
                          "sub": np.array(self.sub, np.int32), "field": 90, "n_refs": np.array(self.nrefs, np.int32),
                          "cbc": cbc, "n_kw": 0, "lenient_excl_F": False})
        order = np.argsort(p.year.to_numpy(), kind="stable")
        remap = np.empty(n, np.int64)
        remap[order] = np.arange(n)
        p = p.iloc[order].reset_index(drop=True)
        c = np.array(self.cites, np.int64).reshape(-1, 2)
        c = remap[c] if len(c) else c
        return {"papers": p, "cites": c.astype(np.int32)}


def pi_at(pi: float, year: int, drift: float) -> float:
    return float(min(1.0, pi * (1 + drift) ** (year - (T - 4))))


def build_edge(b: Builder, d: int, R: float, iota: float, n_p: int, lam0: float, kappa: float, pi: float,
               origin_pool: list[int], drift: float = 0.0, parent_split: tuple | None = None) -> None:
    rng = b.rng
    if parent_split is None:
        yrs = rng.integers(T - 5, T - 2, n_p)
    else:
        yrs = np.concatenate([np.full(int(round(s)), T - 5 + i) for i, s in enumerate(parent_split)])
    parents = [b.add(int(y), d, rng.uniform() < kappa) for y in yrs]
    for par, yp in zip(parents, yrs):
        for _ in range(rng.poisson(R * lam0)):
            yc = int(rng.integers(max(int(yp), T - 4), T + 1))
            b.child(yc, d, par, kappa, pi_at(pi, yc, drift))
    if iota > 0:
        n_imp = rng.poisson(R * lam0 * n_p * iota / (1 - iota))
        for _ in range(n_imp):
            yc = int(rng.integers(T - 4, T + 1))
            cand = [o for o in origin_pool if b.year[o] <= yc]
            b.child(yc, d, int(rng.choice(cand)) if cand else None, kappa, pi_at(pi, yc, drift))


def origin_pool(b: Builder, kappa: float) -> list[int]:
    return [b.add(int(y), ORIGIN, b.rng.uniform() < kappa) for y in b.rng.integers(T - 8, T + 1, 60)]


def add_canonical(b: Builder) -> None:
    for _ in range(int(np.ceil(0.05 * len(b.year)))):
        b.add(F_SYN, ORIGIN, False)


def ref_split(n_p: int, lam: float, imp_per_year: float) -> tuple:
    """Parent counts per cohort year so expected yearly totals over t-5..t-3 are flat."""
    a = np.array([n_p / 3] * 3)
    for _ in range(50):
        e4 = lam * (a[0] / 5 + a[1] / 5) + imp_per_year
        e3 = lam * (a[0] / 5 + a[1] / 5 + a[2] / 4) + imp_per_year
        tgt = (n_p + e4 + e3) / 3
        a = np.array([tgt, tgt - e4, tgt - e3])
        a = np.clip(a, 1, None) * n_p / np.clip(a, 1, None).sum()
    return tuple(a)


def build_reference(rng: np.random.Generator, lam0: float, kappa: float, pi: float) -> dict:
    b = Builder(rng)
    pool = origin_pool(b, kappa)
    n_p, iota = 40, 0.3
    imp = lam0 * n_p * iota / (1 - iota) / 5
    split = ref_split(n_p, lam0, imp)
    for d in HOSTS:
        build_edge(b, d, 1.0, iota, n_p, lam0, kappa, pi, pool, parent_split=split)
        yrs = np.array(b.year)
        subs = np.array(b.sub)
        level = np.mean([((yrs == y) & (subs == d)).sum() for y in range(T - 5, T - 2)])
        for y in range(T - 2, T + 1):
            for _ in range(max(0, int(round(level - ((yrs == y) & (subs == d)).sum())))):
                b.add(y, d, False)
    return b.to_cdata()


def label_concept(cid: str, cdata: dict, rho0: dict, B: int) -> list[dict]:
    """Production path for one synthetic concept at t = T (origin excluded)."""
    papers = cdata["papers"]
    canon = canonical_main(papers, F_SYN)
    view = w1_view(cdata, T)
    par = parentage(view, canon, T)
    rows = []
    for d in sorted(set(papers["sub"]) - {ORIGIN}):
        ev = edge_vectors(view, par, int(d), T)
        if ev.n_w1 < 10:
            rows.append({"concept_id": cid, "t": T, "d": int(d), "eligible": False, "n_w1": ev.n_w1,
                         "n_children": ev.n_children, "n_parents": ev.n_parents, "n_traced": ev.stats["n_traced"]})
            continue
        pe = point_estimates(ev)
        row = {"concept_id": cid, "t": T, "d": int(d), "eligible": True, "n_w1": ev.n_w1, "n_children": ev.n_children,
               "n_parents": ev.n_parents, "n_traced": ev.stats["n_traced"], "rho": pe["rho"], "m": pe["m"]}
        if ev.n_parents >= 1 and ev.stats["n_traced"] >= 1 and ev.n_children >= 5:
            rng = np.random.default_rng([SEED, h32(cid), T, int(d)])
            row.update(bootstrap_edge(ev, rng, B, {"main": rho0.get(int(d), np.nan)}))
        rows.append(row)
    return rows


def run_chunk(args: dict) -> list[dict]:
    rng = np.random.default_rng(args["seed"])
    out = []
    sc = args["scenario"]
    for ci, edges_ in enumerate(args["concepts"]):
        b = Builder(rng)
        pool = origin_pool(b, sc["kappa"])
        spec = {}
        for (R, iota, n_p), d in zip(edges_, HOSTS):
            build_edge(b, d, R, iota, n_p, sc["lam0"], sc["kappa"], sc["pi_host"], pool, drift=sc["drift"])
            spec[d] = (R, iota, n_p)
        add_canonical(b)
        cid = f"syn_{args['tag']}_{args['chunk']}_{ci}"
        for r in label_concept(cid, b.to_cdata(), args["rho0"], args["B"]):
            R, iota, n_p = spec[r["d"]]
            r.update({"R": R, "iota": iota, "n_p": n_p, "truth": truth(R, iota)})
            out.append(r)
    return out


def benchmark_for(scn: dict, n_refs: int, rng: np.random.Generator) -> tuple[dict, pd.DataFrame]:
    rows = []
    totals = {(d, y): 10_000 for d in [ORIGIN] + HOSTS for y in range(2000, 2025)}
    for i in range(n_refs):
        cd = build_reference(rng, scn["lam0"], scn["kappa"], scn["pi_ref"])
        rows += reference_concept(f"synref_{i}", cd, totals)
    refs = pd.DataFrame(rows)
    cells, mode = benchmark.stationary_cells(refs)
    tb = benchmark.rho0_table(cells, [(d, T) for d in HOSTS], FIELD)
    return {d: tb[(d, T)][0] for d in HOSTS}, refs.assign(mode=mode, rho0_level=",".join(sorted({tb[(d, T)][1] for d in HOSTS})))


def metrics(df: pd.DataFrame, col: str) -> dict:
    lab = df[col]
    det = df[lab != "UNDETERMINED"]
    wrong = det[det[col] != det.truth]
    conf = pd.crosstab(df.truth, lab).to_dict()
    per = {}
    for s in ["SOURCE", "SINK", "FADING"]:
        d_s = det[det[col] == s]
        tr = df[df.truth == s]
        per[s] = {"n_labelled": int(len(d_s)), "fdr": float((d_s.truth != s).mean()) if len(d_s) else None,
                  "power": float((tr[col] == s).mean()) if len(tr) else None}
    return {"n_edges": int(len(df)), "n_determined": int(len(det)), "realised_FDR": float(len(wrong) / len(det)) if len(det) else None,
            "null_edges_determined_share": float((df[df.truth == "NULL"][col] != "UNDETERMINED").mean()),
            "per_state": per, "confusion_truth_x_label": conf}


def run_scenario(name: str, scn: dict, n_edges_cell: int, B: int, n_min_main: int, grid: list | None = None,
                 n_refs: int = 6) -> dict:
    rng = np.random.default_rng([SEED, 40, h32(name)])
    rho0, refs = benchmark_for(scn, n_refs, rng)
    specs = []
    for R, iota, n_p in (grid or [(R, i, n) for R in RS_ for i in IOTAS for n in NPS]):
        specs += [(R, iota, n_p)] * n_edges_cell
    rng.shuffle(specs)
    concepts, i = [], 0
    while i < len(specs):
        k = int(rng.integers(3, 9))
        concepts.append(specs[i:i + k])
        i += k
    chunks = [concepts[j:j + 40] for j in range(0, len(concepts), 40)]
    tasks = [{"concepts": ch, "scenario": scn, "rho0": rho0, "B": B, "seed": [SEED, 41, h32(name), j], "tag": name,
              "chunk": j} for j, ch in enumerate(chunks)]
    rows = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(4, detect_cpus()), mp_context=mp.get_context("spawn")) as ex:
        for f in as_completed([ex.submit(run_chunk, t) for t in tasks]):
            rows += f.result()
    logger.info(f"synth {name}: {len(rows)} edges in {time.time() - t0:.0f}s; rho0={ {k: round(v, 3) for k, v in rho0.items()} }")
    df = pd.DataFrame(rows)
    for c in ["p_greater_main", "p_less_main", "m_lo", "rt_lo_main", "rt_hi_main", "m_hi"]:
        if c not in df:
            df[c] = np.nan
    res = {"scenario": scn, "rho0": rho0, "n_refs": n_refs, "ref_stationary_share": float(
        ((refs.n_w1 >= 30) & (refs.slope.abs() < 0.05)).mean()), "benchmark_mode": refs["mode"].iloc[0],
           "rho0_levels": refs["rho0_level"].iloc[0]}
    for nm in sorted({5, 10, 20, n_min_main}):
        df = assign_states(df, nm, "p_greater_main", "p_less_main", f"state_n{nm}")
        res[f"n_min_{nm}"] = metrics(df, f"state_n{nm}")
    main_col = f"state_n{n_min_main}"
    df["rt_cover"] = (df.rt_lo_main <= df.R) & (df.R <= df.rt_hi_main)
    df["m_cover"] = (df.m_lo <= df.iota) & (df.iota <= df.m_hi)
    tst = df[df[f"{main_col}__tested"]]
    res["coverage_rho_tilde_tested"] = float(tst.rt_cover.mean()) if len(tst) else None
    res["coverage_m_tested"] = float(tst.m_cover.mean()) if len(tst) else None
    res["median_rho_tilde_by_R"] = {str(R): float(g.rho.div(g.d.map(rho0)).median()) for R, g in df[df.eligible].groupby("R")}
    df["nk_bin"] = pd.cut(df.n_children, [0, 10, 20, 30, 50, 100, 1e9], right=False).astype(str)
    pw = []
    for (s, b_), g in df[df.truth != "NULL"].groupby(["truth", "nk_bin"]):
        pw.append({"truth": s, "n_children_bin": b_, "n": int(len(g)), "power_main": float((g[main_col] == s).mean()),
                   "power_nmin5": float((g["state_n5"] == s).mean())})
    res["power_by_n_children"] = pw
    cell = []
    for (R, iota, n_p), g in df.groupby(["R", "iota", "n_p"]):
        cell.append({"R": R, "iota": iota, "n_p": n_p, "truth": truth(R, iota), "n_edges": int(len(g)),
                     "median_n_children": float(g.n_children.median()), "tested_share": float(g[f"{main_col}__tested"].mean()),
                     **{f"share_{s}": float((g[main_col] == s).mean()) for s in ["SOURCE", "SINK", "FADING", "UNDETERMINED"]},
                     "share_correct_nmin5": float((g["state_n5"] == truth(R, iota)).mean())})
    res["cells"] = cell
    df[[c for c in df.columns if "__" not in c or c.endswith("__tested")]].to_parquet(OUT / f"synth_edges_{name}.parquet", index=False)
    return res


def calibrate() -> dict:
    """pi, kappa from real W1 host children; lambda0 = median stationary reference rho / (kappa * pi)."""
    e = pd.read_parquet(RESULTS / "cache" / "main_edges_noboot.parquet")
    h = e[e.role == "host"]
    kappa = float((h.n_children_with_refs.sum()) / h.n_children.sum())
    traced_given_refs = float(((1 - h.untraced_share) * h.n_children).sum() / h.n_children_with_refs.sum())
    refs = pd.read_parquet(RESULTS / "cache" / "ref_cells.parquet")
    cells, _ = benchmark.stationary_cells(refs)
    med = float(cells.rho.median())
    pi = min(0.95, traced_given_refs)
    return {"kappa": kappa, "pi": pi, "median_ref_rho": med, "lam0": max(0.05, med / (kappa * pi))}


def run(n_edges_cell: int = 200, B: int = 1000) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cal = calibrate()
    logger.info(f"synthetic calibration: {cal}")
    n_main = int(pd.read_csv(RESULTS / "viability" / "viability_layer.csv", usecols=["n_min_main"]).n_min_main.iloc[0])
    base = {"kappa": cal["kappa"], "pi_host": cal["pi"], "pi_ref": cal["pi"], "lam0": cal["lam0"], "drift": 0.0}
    out = {"calibration": cal, "n_min_main": n_main}
    # T3 smoke
    sm1 = run_scenario("smoke_R2", base, 60, B, n_main, grid=[(2.0, 0.0, 40)])
    sm0 = run_scenario("smoke_R1", base, 60, B, n_main, grid=[(1.0, 0.0, 40)])
    out["smoke"] = {"R2_iota0_np40_source_share_nmin5": sm1["cells"][0]["share_correct_nmin5"],
                    "R2_source_share_main": sm1["cells"][0]["share_SOURCE"],
                    "R1_determined_share_main": 1 - sm0["cells"][0]["share_UNDETERMINED"],
                    "R1_determined_share_nmin5": sm0["n_min_5"]["null_edges_determined_share"]}
    logger.info(f"synthetic smoke: {out['smoke']}")
    out["correct"] = run_scenario("correct", base, n_edges_cell, B, n_main)
    half = max(40, n_edges_cell // 2)
    out["pi_host_0.8x"] = run_scenario("pi08", {**base, "pi_host": cal["pi"] * 0.8}, half, B, n_main)
    out["pi_host_1.25x"] = run_scenario("pi125", {**base, "pi_host": min(1.0, cal["pi"] * 1.25)}, half, B, n_main)
    out["pi_drift_10pct"] = run_scenario("drift", {**base, "drift": 0.10}, half, B, n_main)
    out["rho0_3refs"] = run_scenario("refs3", base, half, B, n_main, n_refs=3)
    fdr = out["correct"][f"n_min_{n_main}"]["realised_FDR"]
    out["pass_criterion"] = {"rule": "realised FDR <= 0.15 at main n_min under correct calibration", "FDR": fdr,
                             "pass": bool(fdr is not None and fdr <= 0.15)}
    out["breaks"] = {k: out[k][f"n_min_{n_main}"]["realised_FDR"] for k in ["pi_host_0.8x", "pi_host_1.25x", "pi_drift_10pct", "rho0_3refs"]}
    (OUT / "synth_results.json").write_text(json.dumps(out, indent=2, default=float))
    logger.info(f"synthetic: pass={out['pass_criterion']} breaks={out['breaks']}")
