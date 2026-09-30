#!/usr/bin/env python3
"""Independent re-derivation of headline numbers through a DIFFERENT code path (plain dict/set loops over the raw
DS1 parquet files; no import of src/ lineage/labels/benchmark code), plus placebo checks.

Writes results/audit/rederive.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

WS = Path(__file__).resolve().parent
RUN = Path(os.environ.get("AII_RUN_DIR", WS.parents[3]))
DS1 = Path(os.environ["AII_DS1_DIR"]) if os.environ.get("AII_DS1_DIR") else RUN / yaml.safe_load((WS / "config.yaml").read_text())["ds1"]
R = WS / "results"


def gate_a_independent() -> dict:
    d1 = json.loads((DS1 / "data_out.json").read_text())["datasets"][0]["examples"]
    meta = {}
    for e in d1:
        if e["metadata_arm"] != "main":
            continue
        inp = json.loads(e["input"])
        meta[e["metadata_concept_id"]] = (int(inp["F"]), int(inp["origin_subfield"]["id"]))
    cw = pd.read_parquet(DS1 / "concept_work.parquet")
    works = pd.concat([pd.read_parquet(p, columns=["work_id", "subfield_id", "refs_in_corpus", "cited_by_count", "n_refs"])
                       for p in sorted((DS1 / "works").glob("works_part_*.parquet"))])
    sub = dict(zip(works.work_id, works.subfield_id))
    refs = dict(zip(works.work_id, works.refs_in_corpus))
    cbc = dict(zip(works.work_id, works.cited_by_count.fillna(0)))
    nref = dict(zip(works.work_id, works.n_refs.fillna(0)))
    shares = []
    for cid, g in cw.groupby("concept_id"):
        if cid not in meta:
            continue
        F, o = meta[cid]
        # dedup: keep earliest year, then max n_refs, then min work_id per dup group
        best = {}
        for w, y, dg in zip(g.work_id, g.year, g.dup_group):
            key = ("g", int(dg)) if pd.notna(dg) else ("w", int(w))
            cand = (int(y), -int(nref.get(w, 0)), int(w))
            if key not in best or cand < best[key]:
                best[key] = cand
        yr = {c[2]: c[0] for c in best.values()}
        ranked = sorted(yr, key=lambda w: (-cbc.get(w, 0), w))[:5]
        canon = set(ranked) | {w for w, y in yr.items() if y == F}
        for t in range(F + 3, min(F + 8, 2019) + 1):
            w1 = [w for w, y in yr.items() if t - 5 <= y <= t]
            cnt = {}
            for w in w1:
                s = sub.get(w)
                if s is not None and not pd.isna(s):
                    cnt[int(s)] = cnt.get(int(s), 0) + 1
            for d, n in cnt.items():
                if d == o or n < 10:
                    continue
                kids = [w for w, y in yr.items() if t - 4 <= y <= t and sub.get(w) == d]
                hit = 0
                for k in kids:
                    for p in refs.get(k, []):
                        p = int(p)
                        if p != k and p in yr and p not in canon and sub.get(p) == d and t - 5 <= yr[p] <= yr[k]:
                            hit += 1
                            break
                shares.append((cid, t, d, len(kids), hit / len(kids) if kids else np.nan))
    df = pd.DataFrame(shares, columns=["concept_id", "t", "d", "n_children", "within"])
    vs = df[df.n_children >= 10]
    return {"n_host_edges_eligible": int(len(df)), "n_edges_verdict_set": int(len(vs)),
            "n_concepts": int(vs.concept_id.nunique()), "share_ge_040": float((vs.within >= 0.4).mean()),
            "mean_within": float(vs.within.mean()), "_df": df}


def main() -> None:
    out = {}
    ga = gate_a_independent()
    df = ga.pop("_df")
    out["gate_A_independent"] = ga
    pipe = json.loads((R / "gate_a" / "gate_A_verdict.json").read_text())
    out["gate_A_pipeline"] = {"share_ge_040": pipe["share_edges_ge_040"], "n_edges": pipe["n_edges"], "n_concepts": pipe["n_concepts"]}
    # edge-level agreement with pipeline table
    h = pd.read_parquet(R / "gate_a" / "gate_a_host_edges.parquet")[["concept_id", "t", "d", "within_host_share"]]
    m = df.merge(h, on=["concept_id", "t", "d"], how="outer", indicator=True)
    both = m[m._merge == "both"]
    out["gate_A_edge_agreement"] = {"only_independent": int((m._merge == "left_only").sum()),
                                    "only_pipeline": int((m._merge == "right_only").sum()),
                                    "max_abs_diff": float((both.within - both.within_host_share).abs().max())}
    # placebo for the within-vs-lenient contrast: paired sign-flip test on real data vs on column-swapped placebo
    g = pd.read_parquet(R / "gate_a" / "gate_a_host_edges.parquet")
    g = g[g.n_children >= 10]
    diff = (g.lenient_share - g.within_host_share).to_numpy()
    rng = np.random.default_rng(1)

    def signflip_p(x: np.ndarray) -> float:
        obs = abs(x.mean())
        null = np.abs((rng.choice([-1, 1], size=(5000, len(x))) * x).mean(1))
        return float((1 + (null >= obs).sum()) / 5001)
    placebo = diff * rng.choice([-1, 1], size=len(diff))  # random swap of the two columns per edge
    out["within_vs_lenient_signflip"] = {"real_mean_diff": float(diff.mean()), "real_p": signflip_p(diff),
                                         "placebo_mean_diff": float(placebo.mean()), "placebo_p": signflip_p(placebo)}
    # viability headline counts from the raw per-edge table
    e = pd.read_csv(R / "viability" / "viability_layer.csv")
    t = e[(e.n_children >= 30) & (e.n_parents >= 1) & (e.n_traced >= 1)]
    out["viability"] = {"n_eligible": int(len(e)), "n_tested": int(len(t)), "n_concepts_tested": int(t.concept_id.nunique()),
                        "state_counts": e.state_main.value_counts().to_dict()}
    # re-derive SOURCE labels by a hand-coded BH (not statsmodels) per (c,t)
    def bh(p, q=0.10):
        p = np.asarray(p)
        o = np.argsort(p)
        thr = q * np.arange(1, len(p) + 1) / len(p)
        ok = np.nonzero(p[o] <= thr)[0]
        rej = np.zeros(len(p), bool)
        if len(ok):
            rej[o[: ok.max() + 1]] = True
        return rej
    src = sink = 0
    for _, gg in t.groupby(["concept_id", "t"]):
        rg, rl = bh(gg.p_greater_main), bh(gg.p_less_main)
        src += int((rg & ~rl).sum())
        sink += int((rl & ~rg & (gg.m_lo > 0.5)).sum())
    out["viability"]["handBH_SOURCE"], out["viability"]["handBH_SINK"] = src, sink
    # placebo: shuffle p_greater across edges within the tested set -> BH should give far fewer / similar-to-chance SOURCE
    sh = t.copy()
    sh["p_greater_main"] = rng.uniform(size=len(sh))  # uniform null p-values
    src0 = sum(int(bh(gg.p_greater_main).sum()) for _, gg in sh.groupby(["concept_id", "t"]))
    out["viability"]["placebo_uniform_p_SOURCE"] = src0
    # synthetic FDR from raw per-edge parquet
    s = pd.read_parquet(R / "synth" / "synth_edges_correct.parquet")
    lab = s["state_n30"]
    det = s[lab != "UNDETERMINED"]
    out["synthetic_FDR_nmin30"] = float((det["state_n30"] != det.truth).mean())
    # H1 MDE from raw power curve rows (fresh interpolation)
    c = pd.read_csv(R / "power" / "h1_power_curves.csv")
    res = {}
    for key, gg in c[c.outcome == "auc"].groupby("key"):
        gg = gg.sort_values("gamma")
        x, pw = gg.true_delta.to_numpy(), gg.power.to_numpy()
        idx = np.nonzero(pw >= 0.8)[0]
        if not len(idx):
            res[key] = None
            continue
        i = idx[0]
        res[key] = float(x[0]) if i == 0 else float(np.interp(0.8, [pw[i - 1], pw[i]], [x[i - 1], x[i]]))
    out["H1_MDE_rederived_main"] = {k: v for k, v in res.items() if "nmin30" in k}
    # Gate B episodes from raw states + onsets
    on = pd.read_csv(R / "origin" / "cooling_onsets.csv").set_index("concept_id")["onset_0.7"]
    n_ep = 0
    for (cid, tt), gg in e.groupby(["concept_id", "t"]):
        o_ = on.get(cid)
        if pd.notna(o_) and tt + 1 <= o_ <= tt + 5 and (gg.state_main == "SOURCE").any() and (gg.state_main == "SINK").any():
            n_ep += 1
    out["gate_B_labelled_episodes"] = n_ep
    (R / "audit" / "rederive.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    sys.exit(main())
