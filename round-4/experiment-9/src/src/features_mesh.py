"""STAGE 7: W1 features for the MeSH entry events and the G1 multi-team events (vendored exp_7 formulas).

Per event (entry year e; for G1 the window [t, t+1] with reference year t):
  A_cont       tag-weighted mean pre-entry host share over profiled partners (block = vendored block_of(e))
  A_cont_lo/hi unprofiled tags counted with share 0 / 1;  cov = profiled / all tags;  A_cont_exact uses exact
               profiles only (bg fill off)
  CT           share of focal partner tags that are origin companions (partners on c-papers with sub == o in
               [e-5, e-1]); CT_any = companions from any earlier c-paper
  G2           NATIVE s >= 0.30, ADJACENT 0.05 <= s < 0.30, FOREIGN s < 0.05 (shares of profiled tags)
  A_placebo    the same partners' mean share toward d' = seeded random covered subfield != o, != d, not entered
               by c at or before e
  controls     prox_od = 1 - rs(o, d); RD (exp_7 formula, rs_distance of iteration-2 exp_3); log_n_partner_tags;
               cov; demic; abstract_share; mom_d (dataset all_types totals); log_centrality (distinct partners of c
               up to e); log_W1 = log1p(c-papers in [e-5, e]); mean_topic_score / boundary_share from the entry
               papers' hydrated OpenAlex topics (<= 70 list calls; if unavailable they are dropped, D-M3)
Leakage test: every feature is recomputed after deleting all c-papers with year > e (G1: > t+1) and must be identical.
"""
from __future__ import annotations

import json
import time
from collections import Counter

import numpy as np
import orjson
import pandas as pd
from loguru import logger

import common
from common import RESULTS, SEED, CreditStop, OpenAlex, dump, sha256_file

HYD = RESULTS / "topic_hydration.jsonl"
G2_BINS = (0.05, 0.30)


class Nat:
    """Exact profiles (dataset_5 reuse + fetched) first; bg shares fill gaps only if admitted in 6a."""

    def __init__(self, exact: dict, bg: dict | None):
        self.exact = exact
        self.bg = bg or {}

    def share(self, node: int, blk: str, d: int) -> tuple[float | None, str | None]:
        p = self.exact.get((node, blk))
        if p is not None:
            tot, counts, _ = p
            return (counts.get(d, 0) / tot if tot > 0 else 0.0), "exact"
        v = self.bg.get((node, blk))
        if v is not None:
            return v[2].get(d, 0.0) / v[1], "bg"
        return None, None


def load_nat(use_bg: bool) -> Nat:
    import nativeness
    exact = nativeness.all_profiles()
    bg = None
    if use_bg:
        nodes = {k[0] for k in exact}
        for f in (nativeness.NAT / "needed_pairs.csv", RESULTS / "mini" / "nativeness_needed.csv"):
            if f.exists():
                nodes |= set(pd.read_csv(f).node.astype(int))
        bg = nativeness.bg_shares(nodes)
    return Nat(exact, bg)


def load_rs() -> dict:
    rs = pd.read_parquet(common.E3 / "results" / "concept_subfield" / "rs_distance.parquet")
    return {(int(a), int(b)): float(x) for a, b, x in zip(rs.subfield_i, rs.subfield_j, rs.d)}


# -------------------------------------------------------------------------------------------------- topic hydration
def hydrate_topics(G: dict, rows: np.ndarray, max_calls: int = 70) -> dict:
    """work row -> {primary_score, top3 subfields}; cached in results/topic_hydration.jsonl (paid data, kept)."""
    have = {}
    if HYD.exists():
        for line in HYD.read_text().splitlines():
            if line.strip():
                r = orjson.loads(line)
                have[int(r["work_id"])] = r
    wid = G["W"]["work_id"]
    todo = [int(wid[r]) for r in np.unique(rows) if int(wid[r]) not in have]
    oa = OpenAlex("topic_hydration", rps=4.0, guard_remaining=100)
    calls = 0
    if todo and oa.available():
        with open(HYD, "a") as f:
            for i in range(0, len(todo), 100):
                if calls >= max_calls:
                    logger.warning(f"hydration call cap {max_calls} reached")
                    break
                chunk = todo[i:i + 100]
                try:
                    d = oa.get("/works", {"filter": "openalex:" + "|".join(f"W{x}" for x in chunk),
                                          "select": "id,primary_topic,topics", "per_page": 100}, tag=f"hydrate {i}")
                except (CreditStop, RuntimeError) as ex:
                    logger.warning(f"hydration stopped: {ex!r}")
                    break
                calls += 1
                got = set()
                for w in d.get("results", []):
                    x = int(str(w["id"]).rsplit("/W", 1)[-1])
                    pt = w.get("primary_topic") or {}
                    tops = sorted(w.get("topics") or [], key=lambda t: -(t.get("score") or 0))[:3]
                    rec = {"work_id": x, "primary_score": pt.get("score"),
                           "primary_sub": int(str((pt.get("subfield") or {}).get("id", "/-1")).rsplit("/", 1)[-1]) if pt else None,
                           "top3_subs": [int(str((t.get("subfield") or {}).get("id", "/-1")).rsplit("/", 1)[-1]) for t in tops]}
                    have[x] = rec
                    got.add(x)
                    f.write(json.dumps(rec) + "\n")
                for x in chunk:
                    if x not in got:
                        rec = {"work_id": x, "primary_score": None, "primary_sub": None, "top3_subs": [], "missing": True}
                        have[x] = rec
                        f.write(json.dumps(rec) + "\n")
    logger.info(f"topic hydration: {calls} calls this run; {len(have)} works cached; todo was {len(todo)}")
    return have


# ------------------------------------------------------------------------------------------------------ features
def event_features(G: dict, nat: Nat, rs: dict, hyd: dict | None, c, d: int, tref: int, tmax: int,
                   focus_lo: int, focus_hi: int, r: np.ndarray, y: np.ndarray, placebo_d: int | None) -> dict:
    """Features of one event from the concept's link arrays (r, y). Focal papers: d-papers in [focus_lo, focus_hi]."""
    from features import block_of  # vendored
    W = G["W"]
    ptr, idx = G["P"]
    AUp, AUi = G["AU"]
    sub = W["sub"][r]
    o = int(c.origin)
    own = set(c.own_nodes)
    er = r[(sub == d) & (y >= focus_lo) & (y <= focus_hi)]
    nodes_l = []
    for row in er:
        a = idx[ptr[row]:ptr[row + 1]]
        nodes_l.append(a[~np.isin(a, list(own))] if own else a)
    nodes = np.concatenate(nodes_l) if nodes_l else np.zeros(0, np.int64)
    blk = block_of(tref)

    def pset(rows):
        s = set()
        for row in rows:
            s.update(idx[ptr[row]:ptr[row + 1]].tolist())
        return s - own

    comp = pset(r[(sub == o) & (y >= tref - 5) & (y <= tref - 1)])
    comp_any = pset(r[y < tref])
    n = len(nodes)
    sh, src = [], []
    for j in nodes.tolist():
        s, sr = nat.share(int(j), blk, d)
        sh.append(np.nan if s is None else s)
        src.append(sr)
    sh = np.array(sh, float)
    prof = ~np.isnan(sh)
    exact = np.array([s == "exact" for s in src], bool)
    isc = np.array([int(j) in comp for j in nodes.tolist()], bool)
    f = {"n_tags": n, "n_prof_tags": int(prof.sum()), "n_exact_tags": int(exact.sum()),
         "cov": prof.sum() / n if n else np.nan, "cov_exact": exact.sum() / n if n else np.nan,
         "CT": isc.mean() if n else np.nan,
         "CT_any": float(np.mean([int(j) in comp_any for j in nodes.tolist()])) if n else np.nan,
         "A_cont": float(sh[prof].mean()) if prof.any() else np.nan,
         "A_cont_exact": float(sh[exact].mean()) if exact.any() else np.nan,
         "nat_source": "none" if not prof.any() else ("exact" if exact.sum() == prof.sum() else "exact+bg")}
    ssum = float(sh[prof].sum()) if prof.any() else 0.0
    f["A_cont_lo"] = ssum / n if n else np.nan
    f["A_cont_hi"] = (ssum + (n - prof.sum())) / n if n else np.nan
    if prof.any():
        s = sh[prof]
        f["NATIVE"] = float((s >= G2_BINS[1]).mean())
        f["ADJACENT"] = float(((s >= G2_BINS[0]) & (s < G2_BINS[1])).mean())
        f["FOREIGN"] = float((s < G2_BINS[0]).mean())
    else:
        f["NATIVE"] = f["ADJACENT"] = f["FOREIGN"] = np.nan
    if placebo_d is not None and n:
        ps = [nat.share(int(j), blk, placebo_d)[0] for j in nodes.tolist()]
        ps = [x for x in ps if x is not None]
        f["A_placebo"] = float(np.mean(ps)) if ps else np.nan
    else:
        f["A_placebo"] = np.nan
    f["placebo_d"] = placebo_d if placebo_d is not None else -1
    tot = G["totals"]
    t0, t3 = tot.get((d, tref), 0), tot.get((d, tref - 3), 0)
    f["mom_d"] = float(np.log(t0 / t3)) if t0 > 0 and t3 > 0 else np.nan
    f["prox_od"] = 1 - rs.get((o, d), np.nan)
    pre = (sub >= 0) & (sub != d) & (y < tref)
    f["RD_basis"] = "before_e"
    if not pre.any():
        pre = (sub >= 0) & (sub != d) & (y <= tref)
        f["RD_basis"] = "up_to_e"
    cnt = Counter(sub[pre].tolist())
    den = sum(cnt.values())
    f["RD"] = sum(k * (1 - rs.get((s_, d), np.nan)) for s_, k in cnt.items()) / den if den else np.nan
    f["log_centrality"] = float(np.log1p(len(pset(r[y <= tmax]))))
    f["log_W1"] = float(np.log1p(((y >= tref - 5) & (y <= tmax)).sum()))
    f["log_n_partner_tags"] = float(np.log(max(n, 1)))
    ent = set()
    for row in er:
        ent.update(AUi[AUp[row]:AUp[row + 1]].tolist())
    prior = set()
    for row in r[(sub == o) & (y < tref)]:
        prior.update(AUi[AUp[row]:AUp[row + 1]].tolist())
    f["n_entry_authors"] = len(ent)
    f["demic"] = len(ent & prior) / len(ent) if ent else np.nan
    f["abstract_share"] = float(W["has_abstract"][er].mean()) if len(er) else np.nan
    f["n_focus_papers"] = int(len(er))
    if hyd is not None:
        ts, bs = [], []
        for row in er:
            h = hyd.get(int(W["work_id"][row]))
            if h is None or h.get("missing") or h.get("primary_score") is None:
                continue
            ts.append(float(h["primary_score"]))
            bs.append(o in set(h.get("top3_subs") or []))
        f["mean_topic_score"] = float(np.mean(ts)) if ts else np.nan
        f["boundary_share"] = float(np.mean(bs)) if bs else np.nan
        f["n_hydrated"] = len(ts)
    return f


def placebo_host(pm: dict, thr: float, c, d: int, e: int, r, y, sub, eid: int, subs: list[int]) -> int | None:
    from coverage import covered
    entered = set(sub[(y <= e) & (sub >= 0)].tolist())
    cand = [s for s in subs if s != c.origin and s != d and s not in entered and covered(pm, s, e, thr)]
    if not cand:
        return None
    rng = np.random.default_rng([SEED, int(eid)])
    return int(cand[rng.integers(len(cand))])


def build(G: dict, ev: pd.DataFrame, nat: Nat, rs: dict, hyd: dict | None, pm: dict, thr: float,
          truncate: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = G["concepts"].set_index("concept_id")
    subs = sorted(G["tax"]["sub_field"])
    main_rows, g1_rows = [], []
    for x in ev.itertuples():
        c = con.loc[x.concept_id]
        c = c.copy()
        c["origin"] = int(c.origin)
        r_all, y_all = G["links"][x.concept_id]
        sub_all = G["W"]["sub"][r_all]
        e = int(x.e)
        r, y = (r_all[y_all <= e], y_all[y_all <= e]) if truncate else (r_all, y_all)
        pd_ = placebo_host(pm, thr, c, int(x.d), e, r_all[y_all <= e], y_all[y_all <= e], sub_all[y_all <= e],
                           x.event_id, subs)
        f = event_features(G, nat, rs, hyd, c, int(x.d), e, e, e, e, r, y, pd_)
        f["event_id"] = x.event_id
        main_rows.append(f)
        if pd.notna(x.g1_t):
            t = int(x.g1_t)
            r, y = (r_all[y_all <= t + 1], y_all[y_all <= t + 1]) if truncate else (r_all, y_all)
            g = event_features(G, nat, rs, hyd, c, int(x.d), t, t + 1, t, t + 1, r, y, None)
            g["event_id"] = x.event_id
            g1_rows.append(g)
    return pd.DataFrame(main_rows), pd.DataFrame(g1_rows)


def run(mini: bool = False) -> dict:
    import coverage
    import events_mesh
    import load_mesh
    G = load_mesh.prepare()
    ev = events_mesh.load_events(mini)
    esum = json.loads(((RESULTS / "mini") if mini else RESULTS).joinpath("events_mesh_summary.json").read_text())
    thr = esum["chosen"]["coverage_threshold"]
    ev = ev[ev.MESH_MAIN].reset_index(drop=True)
    pm = coverage.load_rule()
    fb = json.loads((RESULTS / "nativeness_fallback_check.json").read_text())
    nat = load_nat(fb["admitted"])
    rs = load_rs()
    hyd = None
    if not mini:
        W = G["W"]
        rows = []
        for x in ev.itertuples():
            r, y = G["links"][x.concept_id]
            sub = W["sub"][r]
            rows.append(r[(sub == x.d) & (y == x.e)])
        ent_rows = np.concatenate(rows)
        hyd = hydrate_topics(G, ent_rows, max_calls=40)
        g1r = []
        for x in ev[ev.g1_t.notna()].itertuples():
            r, y = G["links"][x.concept_id]
            sub = W["sub"][r]
            g1r.append(r[(sub == x.d) & (y >= x.g1_t) & (y <= x.g1_t + 1)])
        hyd = hydrate_topics(G, np.concatenate(g1r), max_calls=40)
    t0 = time.time()
    fm, fg = build(G, ev, nat, rs, hyd, pm, thr)
    logger.info(f"features built in {time.time() - t0:.1f}s: main {len(fm)}, G1 {len(fg)}")
    fm2, fg2 = build(G, ev, nat, rs, hyd, pm, thr, truncate=True)
    leak = {"main_identical": bool(fm.equals(fm2)), "g1_identical": bool(fg.equals(fg2)),
            "rule": "all features recomputed after deleting every c-paper with year > e (G1: > t+1)"}
    if not (leak["main_identical"] and leak["g1_identical"]):
        diff = [c for c in fm.columns if not fm[c].equals(fm2[c])]
        leak["differing_columns_main"] = diff
        raise RuntimeError(f"LEAKAGE TEST FAILED: {leak}")
    out_dir = RESULTS / "mini" if mini else RESULTS
    feats = ev.merge(fm, on="event_id", how="left")
    feats.to_parquet(out_dir / "features_mesh.parquet", index=False)
    g1 = ev.merge(fg, on="event_id", how="inner")
    g1.to_parquet(out_dir / "features_mesh_g1.parquet", index=False)
    m = feats
    tw = float(m.n_prof_tags.sum() / m.n_tags.sum())
    summ = {"n_events": int(len(m)), "n_concepts": int(m.concept_id.nunique()), "n_g1_events": int(len(g1)),
            "leakage_test": leak, "tag_weighted_cov": tw,
            "tag_weighted_cov_exact_only": float(m.n_exact_tags.sum() / m.n_tags.sum()),
            "cov_by_host_domain": {int(k): float(g.n_prof_tags.sum() / g.n_tags.sum()) for k, g in m.groupby("domain_d")},
            "nat_source_counts": m.nat_source.value_counts().to_dict(),
            "mean_A_cont": float(m.A_cont.mean()), "sd_A_cont": float(m.A_cont.std()),
            "mean_CT": float(m.CT.mean()), "sd_CT": float(m.CT.std()),
            "G2_means": {k: float(m[k].mean()) for k in ("NATIVE", "ADJACENT", "FOREIGN")},
            "mean_A_placebo": float(m.A_placebo.mean()), "placebo_missing": int(m.A_placebo.isna().sum()),
            "topic_controls": {"mean_topic_score_missing": int(m.mean_topic_score.isna().sum()) if "mean_topic_score" in m else None,
                               "boundary_share_missing": int(m.boundary_share.isna().sum()) if "boundary_share" in m else None},
            "missing": {k: int(m[k].isna().sum()) for k in ("A_cont", "CT", "prox_od", "RD", "demic", "mom_d")},
            "ranges": {k: [float(m[k].min()), float(m[k].max())] for k in ("A_cont", "CT", "prox_od", "RD", "log_W1",
                                                                          "log_centrality")},
            "RD_basis_counts": m.RD_basis.value_counts().to_dict()}
    dump(out_dir / "features_mesh_summary.json", summ)
    if not mini:
        # S12: union c-paper set (verified + MeSH-indexed-only / unverified rows), same event and feature rules
        Gu = dict(G)
        Gu["links"] = G["links_union"]
        evu, _ = events_mesh.build(Gu, pm)
        kwc = esum["chosen"]["kw"]
        evu = evu[evu[kwc] & evu[f"covered{int(thr * 100)}"]].reset_index(drop=True)
        evu["event_id"] = np.arange(len(evu))
        fu, _ = build(Gu, evu.assign(g1_t=np.nan), nat, rs, hyd, pm, thr)
        feats_u = evu.merge(fu, on="event_id", how="left")
        feats_u.to_parquet(RESULTS / "features_mesh_union.parquet", index=False)
        summ["union_c_paper_set"] = {"n_events": int(len(feats_u)), "n_concepts": int(feats_u.concept_id.nunique()),
                                     "tag_weighted_cov": float(feats_u.n_prof_tags.sum() / feats_u.n_tags.sum())}
        dump(out_dir / "features_mesh_summary.json", summ)
        (RESULTS / "features_mesh.sha256").write_text(
            f"{sha256_file(RESULTS / 'features_mesh_union.parquet')}  features_mesh_union.parquet\n" +f"{sha256_file(RESULTS / 'features_mesh.parquet')}  features_mesh.parquet\n"
                                                      f"{sha256_file(RESULTS / 'features_mesh_g1.parquet')}  features_mesh_g1.parquet\n")
    logger.info(f"features: {summ}")
    return summ
