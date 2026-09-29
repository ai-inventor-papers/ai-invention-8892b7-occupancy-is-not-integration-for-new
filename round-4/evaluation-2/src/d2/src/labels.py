"""STAGES 10-11: graft labels against the reference-arm benchmark, establishment by label (screen only), occupancy vs
integration, and the D3 per-concept anchoring export (screen in results/, held-out in sealed/ with sha256).

Label threshold: native >= 0.3 (pre-declared fallback 6, deviations.md #1). Labels use entry-year data only (W1).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

from config import RESULTS, SEALED, SEED, assert_not_sealed, sha256_file
from features import Nativeness, block_of, event_tags

THR = 0.3
LEVEL = 0.90


def per_paper_counts(G: dict, ev) -> tuple[np.ndarray, np.ndarray]:
    con = G["concepts"].set_index("concept_id")
    c = con.loc[ev.concept_id]
    own = int(c.own_node) if pd.notna(c.own_node) else None
    er, pos, nodes = event_tags(G, ev.concept_id, int(ev.d), int(ev.e), own)
    nat = Nativeness(G["prof"])
    blk = block_of(int(ev.e))
    k = np.zeros(len(er))
    n = np.zeros(len(er))
    for p, j in zip(pos, nodes):
        s = nat.share(int(j), blk, int(ev.d))
        if s is None:
            continue
        n[p] += 1
        k[p] += s >= THR
    return k, n


def lower_bound(k: np.ndarray, n: np.ndarray, rng) -> tuple[float, str]:
    if n.sum() == 0:
        return np.nan, "no_profiled_tags"
    if len(k) >= 3:
        idx = rng.integers(0, len(k), size=(1000, len(k)))
        ks, ns = k[idx].sum(1), n[idx].sum(1)
        with np.errstate(invalid="ignore", divide="ignore"):
            a = np.where(ns > 0, ks / ns, np.nan)
        return float(np.nanquantile(a, (1 - LEVEL) / 2)), "bootstrap_papers"
    K, N = int(k.sum()), int(n.sum())
    return (float(stats.beta.ppf((1 - LEVEL) / 2, K, N - K + 1)) if K > 0 else 0.0), "clopper_pearson"


def benchmark(ref: pd.DataFrame, sub_field: dict) -> tuple[dict, dict, float]:
    ref = ref.dropna(subset=["A_t03"])
    bd = {int(d): float(g.A_t03.median()) for d, g in ref.groupby("d") if len(g) >= 5}
    ref = ref.assign(fd=ref.d.map(lambda x: sub_field.get(int(x), -1)))
    bf = {int(f): float(g.A_t03.median()) for f, g in ref.groupby("fd") if len(g) >= 5}
    return bd, bf, float(ref.A_t03.median())


def cluster_boot_diff(s: pd.DataFrame, col: str, rng, reps: int = 1000) -> dict:
    cids = s.concept_id.unique()
    g = {c: x for c, x in s.groupby("concept_id")}
    vals = []
    for _ in range(reps):
        b = pd.concat([g[c] for c in rng.choice(cids, len(cids))])
        a1 = b.loc[b.anchored, col].mean()
        a0 = b.loc[~b.anchored, col].mean()
        vals.append(a1 - a0)
    v = np.array(vals)
    return {"diff": float(s.loc[s.anchored, col].mean() - s.loc[~s.anchored, col].mean()),
            "ci95": [float(np.nanquantile(v, .025)), float(np.nanquantile(v, .975))]}


def run(G: dict, feats_screen: pd.DataFrame, feats_heldout: pd.DataFrame, screen_out: pd.DataFrame) -> dict:
    rng = np.random.default_rng(SEED)
    sub_field = G["tax"]["sub_field"]
    ref = feats_screen[(feats_screen.arm == "reference") & feats_screen.REFERENCE_ACCEPTED]
    bd, bf, bg = benchmark(ref, sub_field)
    res = {"benchmark": {"n_reference_events": int(len(ref)), "n_hosts_with_own_benchmark": len(bd),
                         "n_fields_with_benchmark": len(bf), "global_median_A_t03": bg,
                         "share_host_benchmarks_zero": float(np.mean([v == 0 for v in bd.values()])) if bd else None}}
    out = {}
    for name, fr in (("screen", feats_screen[(feats_screen.arm == "main") & feats_screen.kw5]),
                     ("heldout", feats_heldout[feats_heldout.kw5])):
        rows = []
        for ev in fr.itertuples():
            k, n = per_paper_counts(G, ev)
            lo, basis = lower_bound(k, n, rng)
            d = int(ev.d)
            if d in bd:
                B, lvl = bd[d], "host"
            elif sub_field.get(d, -1) in bf:
                B, lvl = bf[sub_field[d]], "field"
            else:
                B, lvl = bg, "global"
            rows.append({"idx": ev.Index, "concept_id": ev.concept_id, "d": d, "e": int(ev.e), "A_t03_lower90": lo,
                         "label_basis": basis, "benchmark_B": B, "benchmark_level": lvl,
                         "anchored": bool(lo > B) if not np.isnan(lo) else False})
        out[name] = pd.DataFrame(rows).set_index("idx")
    lab_s = out["screen"]
    lab_h = out["heldout"]
    lab_s.to_parquet(RESULTS / "graft_labels_screen.parquet")
    hp = SEALED / "graft_labels_heldout.parquet"
    lab_h.to_parquet(hp)
    (SEALED / "graft_labels_heldout.sha256").write_text(f"{sha256_file(hp)}  graft_labels_heldout.parquet\n")
    res["labels"] = {k: {"n": int(len(v)), "anchored_share": float(v.anchored.mean()),
                         "basis": v.label_basis.value_counts().to_dict(),
                         "benchmark_level": v.benchmark_level.value_counts().to_dict()} for k, v in out.items()}
    # establishment by label: SCREEN ONLY (MAIN, kw5)
    assert_not_sealed(screen_out.concept_id.unique())
    s = screen_out[screen_out.MAIN & screen_out.kw5].join(lab_s[["anchored", "A_t03_lower90"]], how="inner")
    s["Y_per_entry_paper"] = s.Y_strict / s.n_entry_papers
    res["establishment_by_label_screen_MAIN"] = {
        "n_anchored": int(s.anchored.sum()), "n_unanchored": int((~s.anchored).sum()),
        "EST_bin": {"anchored": float(s.loc[s.anchored, "EST_bin"].mean()),
                    "unanchored": float(s.loc[~s.anchored, "EST_bin"].mean()), **cluster_boot_diff(s, "EST_bin", rng)},
        "Y_strict_per_entry_paper": {"anchored": float(s.loc[s.anchored, "Y_per_entry_paper"].mean()),
                                     "unanchored": float(s.loc[~s.anchored, "Y_per_entry_paper"].mean()),
                                     **cluster_boot_diff(s, "Y_per_entry_paper", rng)}}
    # occupancy vs integration
    pres = s[s.present_e5 == 1]
    res["occupancy"] = {"n_present_e5": int(len(pres)), "share_anchored_among_present_e5": float(pres.anchored.mean()),
                        "share_anchored_all": float(s.anchored.mean())}
    ent = []
    for cid, g in s.groupby("concept_id"):
        p = g.Y_all.to_numpy(float)
        if p.sum() <= 0:
            continue
        q = p / p.sum()
        h = -(q[q > 0] * np.log(q[q > 0]))
        H = h.sum()
        if H <= 0:
            continue
        ha = -(np.where((q > 0) & g.anchored.to_numpy(), q * np.log(np.where(q > 0, q, 1)), 0)).sum()
        ent.append({"concept_id": cid, "H_W2_hosts": H, "anchored_entropy_share": ha / H,
                    "anchored_event_share": float(g.anchored.mean())})
    ent = pd.DataFrame(ent)
    res["integration_entropy"] = {"n_concepts": int(len(ent)),
                                  "mean_anchored_entropy_share": float(ent.anchored_entropy_share.mean()),
                                  "mean_anchored_event_share": float(ent.anchored_event_share.mean()),
                                  "note": "W2 host-subfield entropy (Y_all over the concept's host entry events) and "
                                          "the share carried by anchored host edges"}
    # D3 export
    def d3(fr: pd.DataFrame, lab: pd.DataFrame) -> pd.DataFrame:
        j = fr.join(lab[["anchored"]], how="left")
        return j.groupby("concept_id").agg(n_events=("d", "size"), mean_A_cont=("A_cont", "mean"),
                                           mean_A=("A", "mean"), mean_A_cont_ex=("A_cont_ex", "mean"),
                                           mean_CT=("CT", "mean"), anchored_share=("anchored", "mean"),
                                           mean_graft_share=("graft_t03", "mean"),
                                           mean_package_share=("package_t03", "mean")).reset_index()
    d3s = d3(feats_screen[(feats_screen.arm == "main") & feats_screen.kw5], lab_s)
    d3s.to_parquet(RESULTS / "d3_concept_anchoring.parquet", index=False)
    d3h = d3(feats_heldout[feats_heldout.kw5], lab_h)
    hp2 = SEALED / "d3_concept_anchoring_heldout.parquet"
    d3h.to_parquet(hp2, index=False)
    (SEALED / "d3_concept_anchoring_heldout.sha256").write_text(f"{sha256_file(hp2)}  d3_concept_anchoring_heldout.parquet\n")
    res["d3_export"] = {"screen_concepts": int(len(d3s)), "heldout_concepts_sealed": int(len(d3h))}
    (RESULTS / "labels_summary.json").write_text(json.dumps(res, indent=1, default=float))
    logger.info(f"labels: {json.dumps(res, default=float)[:1500]}")
    return res
