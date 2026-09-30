"""STAGE 5: W1-only event features (entry-year partners, anchoring A, co-transfer CT, partition, controls).

Every quantity uses data up to and including the entry year e (the nativeness block ends before e). Held-out rows are
written ONLY to sealed/heldout_features.parquet (with sha256); results/features_screen.parquet holds screen + reference.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger

from config import E3, RESULTS, SEALED, sha256_file

PERIODS = {range(2005, 2010): "2000-2004", range(2010, 2015): "2005-2009", range(2015, 2020): "2010-2014"}


def block_of(e: int) -> str:
    for rg, b in PERIODS.items():
        if e in rg:
            return b
    raise ValueError(f"entry year {e} outside 2005-2019 has no pre-entry nativeness block")


def period_of(e: int) -> int:
    return 2005 if e < 2010 else (2010 if e < 2015 else 2015)


class Nativeness:
    def __init__(self, prof: dict):
        self.prof = prof

    def share(self, node: int, blk: str, d: int) -> float | None:
        p = self.prof.get((node, blk))
        if p is None:
            return None
        tot, counts, _ = p
        return counts.get(d, 0) / tot if tot > 0 else 0.0


def load_rs() -> dict[tuple[int, int], float]:
    rs = pd.read_parquet(E3 / "results" / "concept_subfield" / "rs_distance.parquet")
    return {(int(a), int(b)): float(x) for a, b, x in zip(rs.subfield_i, rs.subfield_j, rs.d)}


def event_tags(G: dict, cid: str, d: int, e: int, own) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Entry-year d-papers of c (rows) and their tag multiset (paper position, node)."""
    r, y = G["links"][cid]
    sub = G["W"]["sub"][r]
    er = r[(sub == d) & (y == e)]
    ptr, idx = G["P"]
    pp, nn = [], []
    for k, row in enumerate(er):
        a = idx[ptr[row]:ptr[row + 1]]
        if own is not None:
            a = a[a != own]
        pp.append(np.full(len(a), k))
        nn.append(a)
    return er, (np.concatenate(pp) if pp else np.zeros(0, int)), (np.concatenate(nn) if nn else np.zeros(0, np.int64))


def partner_set(G: dict, rows: np.ndarray, own) -> set:
    ptr, idx = G["P"]
    s = set()
    for row in rows:
        s.update(idx[ptr[row]:ptr[row + 1]].tolist())
    s.discard(own)
    return s


def anchoring(nodes: np.ndarray, comp: set, nat: Nativeness, blk: str, d: int, thr: float = 0.5) -> dict:
    n_all = len(nodes)
    shares = [nat.share(int(j), blk, d) for j in nodes]
    prof = np.array([s is not None for s in shares], bool)
    sh = np.array([s if s is not None else np.nan for s in shares], float)
    is_comp = np.array([int(j) in comp for j in nodes], bool)
    n_prof = int(prof.sum())
    out = {"n_tags": n_all, "n_prof_tags": n_prof, "cov": n_prof / n_all if n_all else np.nan,
           "CT": is_comp.mean() if n_all else np.nan}
    nat_ = prof & (np.nan_to_num(sh, nan=-1) >= thr)
    if n_prof:
        out["A"] = nat_.sum() / n_prof
        out["A_cont"] = float(np.nanmean(sh[prof]))
        for t in (0.3, 0.7):
            out[f"A_t{int(t * 10):02d}"] = float(((np.nan_to_num(sh, nan=-1) >= t) & prof).sum() / n_prof)
        pc = is_comp[prof]
        nv = nat_[prof]
        out.update({"graft": float((nv & ~pc).mean()), "native_companion": float((nv & pc).mean()),
                    "package": float((~nv & pc).mean()), "third_party": float((~nv & ~pc).mean())})
        dn = {}
        for j, s in zip(nodes[prof], sh[prof]):
            dn[int(j)] = s
        out["A_distinct"] = float(np.mean([s >= thr for s in dn.values()]))
    else:
        for k in ["A", "A_cont", "A_t03", "A_t07", "graft", "native_companion", "package", "third_party", "A_distinct"]:
            out[k] = np.nan
    out["A_lo"] = nat_.sum() / n_all if n_all else np.nan
    out["A_hi"] = (nat_.sum() + (~prof).sum()) / n_all if n_all else np.nan
    out["unknown_share"] = (~prof).mean() if n_all else np.nan
    out["n_native_tags"] = int(nat_.sum())
    return out


def host_benchmark(G: dict, nat: Nativeness) -> dict:
    """A0 inputs: native / profiled tag counts per (concept, d, entry period) over pool concepts' HOST d-papers in
    the years of that period, judged with the period's pre-period profile block (leave-one-concept-out later)."""
    W = G["W"]
    con = G["concepts"].set_index("concept_id")
    acc = defaultdict(lambda: [0, 0, 0.0, 0])  # (cid, d, period) -> [native@0.5, profiled, share sum, native@0.3]
    ptr, idx = G["P"]
    for cid, c in con.iterrows():
        r, y = G["links"][cid]
        sub = W["sub"][r]
        o = int(c.origin) if pd.notna(c.origin) else -999
        own = int(c.own_node) if pd.notna(c.own_node) else None
        m = (sub >= 0) & (sub != o) & (y >= 2005) & (y <= 2019)
        for row, d, yy in zip(r[m], sub[m], y[m]):
            blk = block_of(int(yy))
            per = period_of(int(yy))
            for j in idx[ptr[row]:ptr[row + 1]]:
                if j == own:
                    continue
                s = nat.share(int(j), blk, int(d))
                if s is None:
                    continue
                a = acc[(cid, int(d), per)]
                a[1] += 1
                a[0] += s >= 0.5
                a[2] += s
                a[3] += s >= 0.3
    return dict(acc)


def build_features(G: dict, ev: pd.DataFrame) -> pd.DataFrame:
    W = G["W"]
    nat = Nativeness(G["prof"])
    rs = load_rs()
    totals = G["totals"]
    con = G["concepts"].set_index("concept_id")
    AUp, AUi = G["AU"]
    T3p, T3i = G["T3"]
    sub_field = G["tax"]["sub_field"]
    bench = host_benchmark(G, nat)
    tot_dp = defaultdict(lambda: np.zeros(4))
    for (cid, d, per), v in bench.items():
        tot_dp[(d, per)] += np.asarray(v, float)
    rows = []
    for cid, g in ev.groupby("concept_id"):
        c = con.loc[cid]
        r, y = G["links"][cid]
        sub = W["sub"][r]
        o = int(c.origin) if pd.notna(c.origin) else -999
        own = int(c.own_node) if pd.notna(c.own_node) else None
        for ev_row in g.itertuples():
            d, e = int(ev_row.d), int(ev_row.e)
            blk = block_of(e)
            er, pos, nodes = event_tags(G, cid, d, e, own)
            comp = partner_set(G, r[(sub == o) & (y >= e - 5) & (y <= e - 1)], own)
            comp_any = partner_set(G, r[y < e], own)
            f = anchoring(nodes, comp, nat, blk, d)
            f["CT_any"] = float(np.mean([int(j) in comp_any for j in nodes])) if len(nodes) else np.nan
            f03 = anchoring(nodes, comp, nat, blk, d, thr=0.3)
            for k in ["graft", "native_companion", "package", "third_party", "A_lo", "A_hi"]:
                f[f"{k}_t03"] = f03[k]
            # bounds for the continuous primary A_cont: unprofiled tags counted with share 0 (lo) or 1 (hi)
            ssum = f["A_cont"] * f["n_prof_tags"] if f["n_prof_tags"] else 0.0
            n_un = f["n_tags"] - f["n_prof_tags"]
            f["A_cont_lo"] = ssum / f["n_tags"] if f["n_tags"] else np.nan
            f["A_cont_hi"] = (ssum + n_un) / f["n_tags"] if f["n_tags"] else np.nan
            per = period_of(e)
            tv = tot_dp[(d, per)] - np.asarray(bench.get((cid, d, per), (0, 0, 0.0, 0)), float)  # leave-one-out
            f["A0"] = tv[0] / tv[1] if tv[1] > 0 else np.nan
            f["A0_cont"] = tv[2] / tv[1] if tv[1] > 0 else np.nan
            f["A0_t03"] = tv[3] / tv[1] if tv[1] > 0 else np.nan
            f["A0_n_tags"] = float(tv[1])
            f["A_ex"] = f["A"] - f["A0"] if not np.isnan(f.get("A", np.nan)) else np.nan
            f["A_cont_ex"] = f["A_cont"] - f["A0_cont"] if not np.isnan(f.get("A_cont", np.nan)) else np.nan
            # controls (all W1)
            t0, t3 = totals.get((d, e), 0), totals.get((d, e - 3), 0)
            f["mom_d"] = float(np.log(t0 / t3)) if t0 > 0 and t3 > 0 else np.nan
            f["prox_od"] = 1 - rs.get((o, d), np.nan)
            pre = (sub >= 0) & (sub != d) & (y < e)
            f["RD_basis"] = "before_e"
            if not pre.any():
                pre = (sub >= 0) & (sub != d) & (y <= e)
                f["RD_basis"] = "up_to_e"
            cnt = Counter(sub[pre].tolist())
            num = sum(n * (1 - rs.get((s, d), np.nan)) for s, n in cnt.items())
            den = sum(cnt.values())
            f["RD"] = num / den if den else np.nan
            f["log_centrality"] = float(np.log1p(len(partner_set(G, r[y <= e], own))))
            f["log_W1"] = float(np.log1p(((y >= e - 5) & (y <= e)).sum()))
            f["log_n_partner_tags"] = float(np.log(max(len(nodes), 1)))
            ent_auth = set()
            for row in er:
                ent_auth.update(AUi[AUp[row]:AUp[row + 1]].tolist())
            prior_orig = set()
            for row in r[(sub == o) & (y < e)]:
                prior_orig.update(AUi[AUp[row]:AUp[row + 1]].tolist())
            f["n_entry_authors"] = len(ent_auth)
            f["demic"] = len(ent_auth & prior_orig) / len(ent_auth) if ent_auth else np.nan
            f["mean_topic_score"] = float(W["topic_score"][er].mean())
            f["boundary_share"] = float(np.mean([o in set(T3i[T3p[row]:T3p[row + 1]].tolist()) for row in er]))
            f["abstract_share"] = float(W["has_abstract"][er].mean())
            f["min_topic_score"] = float(W["topic_score"][er].min())
            f["field_o"] = sub_field.get(o, -1)
            f["field_d"] = sub_field.get(d, -1)
            f["field_group"] = {31: "Physics/Astro", 17: "CS"}.get(sub_field.get(o, -1), "other")
            f["F_band"] = c.F_band
            f["block"] = blk
            f["index"] = ev_row.Index
            rows.append(f)
    fx = pd.DataFrame(rows).set_index("index")
    out = ev.join(fx)
    for k in ["demic"]:
        out[k + "_missing"] = out[k].isna()
    ho = out[(out.arm == "main") & (out.fold == "heldout")]
    sc = out[~((out.arm == "main") & (out.fold == "heldout"))]
    sc.to_parquet(RESULTS / "features_screen.parquet", index=False)
    hp = SEALED / "heldout_features.parquet"
    ho.to_parquet(hp, index=False)
    (SEALED / "heldout_features.sha256").write_text(f"{sha256_file(hp)}  heldout_features.parquet\n")
    m = out[(out.arm == "main") & out.kw5]
    summ = {"n_rows": int(len(out)), "screen_or_reference_rows": int(len(sc)), "heldout_rows_sealed": int(len(ho)),
            "native_share_tags_main_kw5_at_0.5": float(m.n_native_tags.sum() / m.n_prof_tags.sum()),
            "native_share_tags_main_kw5_at_0.3": float((m.A_t03 * m.n_prof_tags).sum() / m.n_prof_tags.sum()),
            "fallback6_triggered": bool(m.n_native_tags.sum() / m.n_prof_tags.sum() < 0.05),
            "mean_A_cont": float(m.A_cont.mean()), "sd_A_cont": float(m.A_cont.std()),
            "mean_A": float(m.A.mean()), "median_A": float(m.A.median()), "mean_CT": float(m.CT.mean()),
            "mean_cov_event": float(m["cov"].mean()), "median_cov_event": float(m["cov"].median()),
            "tag_weighted_cov": float(m.n_prof_tags.sum() / m.n_tags.sum()),
            "share_events_cov_ge_0.6": float((m["cov"] >= 0.6).mean()),
            "A0_sd_across_hosts": float(m.groupby("d").A0.mean().std()),
            "RD_basis_counts": m.RD_basis.value_counts().to_dict(),
            "demic_missing": int(m.demic.isna().sum()), "mom_missing": int(m.mom_d.isna().sum()),
            "prox_missing": int(m.prox_od.isna().sum()),
            "partition_means_t05": {k: float(m[k].mean()) for k in ["graft", "native_companion", "package",
                                                                      "third_party", "unknown_share"]},
            "partition_means_t03": {k: float(m[k + "_t03"].mean()) for k in ["graft", "native_companion", "package",
                                                                             "third_party"]}}
    (RESULTS / "features_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    logger.info(f"features: {summ}")
    return out
