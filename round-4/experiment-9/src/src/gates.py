"""STAGES 1-2: correctness gates on the already-seen MAIN pool, plus harmonisation rows (screen fold only).

Gate 1  vendored events.reproduce_iter1: iteration-1 entry events 2,347 / 2,154 / 2,000, row by row vs
        iteration-2 exp_2 graft_fallback_events.csv.
Gate 2  vendored D2 pipeline (events -> W1 features -> screen outcomes -> PPML) reproduces exp_7:
        co-primary (concept + e + d) N 1,544, G 140, b_A 4.7391 (IRR/SD 1.300); primary (concept x e + d x e)
        N 452, G 77, b_A 5.9526. Held-out main concepts are removed BEFORE features; outcome functions refuse them.
Harmonisation (labelled 'harmonisation, not confirmation'): the MeSH data rules applied to the main screen
        h1 legacy-concept partner floor 0.3 (MeSH works carry concepts >= 0.3 only) instead of 0.2
        h2 no known-sub topic_score >= 0.05 filter (MeSH works carry no topic score)
        h3 no dup_group dedup (MeSH rows have no dup_group)
        h4 h1 + h2 + h3 (the MeSH pipeline applied to main)
        h5 h4 without mean_topic_score / boundary_share
        (h6, the ranking-rule check, runs after the MeSH nativeness fetch: see harmonise_h6)
"""
from __future__ import annotations

import copy
import gc
import json
import shutil

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

import common
from common import GATE, E7, MAIN_COPRIMARY, MAIN_PRIMARY, dump, sha256_file

import config as vconfig  # vendored exp_7 config (sealing guard)
import events as vevents
import features as vfeatures
import io_load as vio
import models as vmodels
import outcomes as voutcomes

PRIMARY_CTRL = list(vmodels.EVENT_CONTROLS)
SECONDARY_CTRL = list(vmodels.EVENT_CONTROLS) + list(vmodels.SECONDARY_EXTRA)
TOPIC_CTRL = ["mean_topic_score", "boundary_share"]


def _redirect_vendor_outputs(tag: str) -> None:
    d = GATE / tag
    d.mkdir(parents=True, exist_ok=True)
    vevents.RESULTS = d
    vfeatures.RESULTS = d
    vfeatures.SEALED = d


def copy_population() -> dict:
    src = E7 / "results" / "main_population_hydrated.json"
    dst = vconfig.RESULTS / "main_population_hydrated.json"
    shutil.copyfile(src, dst)
    want = (E7 / "results" / "main_population_hydrated.sha256").read_text().split()[0]
    got = sha256_file(dst)
    if want != got:
        raise RuntimeError(f"main population sha mismatch {got} != {want}")
    vconfig.load_sealed_ids()
    logger.info(f"MAIN population copied (sha {got[:12]}); sealed held-out ids: {len(vconfig.SEALED_IDS)}")
    return json.loads(dst.read_text())


def gate1(G: dict) -> dict:
    _redirect_vendor_outputs("gate1")
    r = vevents.reproduce_iter1(G)
    return r


def screen_pipeline(G: dict, pop: dict, tag: str, drop_topic: bool = False) -> dict:
    """Vendored events -> features -> outcomes (screen, main arm) -> co-primary + primary fits."""
    _redirect_vendor_outputs(tag)
    ev = vevents.build_events(G, pop)
    sealed = set(vconfig.SEALED_IDS)
    ev = ev[~ev.concept_id.isin(sealed)]           # held-out main concepts never enter features or outcomes
    ev = ev[(ev.arm == "main") & (ev.fold == "screen")].copy()
    fx = vfeatures.build_features(G, ev)
    for p in ((GATE / tag) / "heldout_features.parquet", (GATE / tag) / "heldout_features.sha256"):
        p.unlink(missing_ok=True)                  # empty by construction (held-out rows removed above)
    y = voutcomes.compute_Y(G, fx.reset_index(drop=True))
    df = fx.reset_index(drop=True).join(y)
    df.to_parquet(GATE / tag / "screen_events_with_outcomes.parquet", index=False)
    s = vmodels.primary_sample(df)
    pc = [c for c in PRIMARY_CTRL if not (drop_topic and c in TOPIC_CTRL)]
    sc = [c for c in SECONDARY_CTRL if not (drop_topic and c in TOPIC_CTRL)]
    rng = np.random.default_rng(common.SEED)
    co = vmodels.fit_one(s, "Y_strict", ["A_cont", "CT"] + sc, "secondary", wild=True, wild_vars=("A_cont", "CT"),
                         rng=rng)
    pr = vmodels.fit_one(s, "Y_strict", ["A_cont", "CT"] + pc, "primary", wild=True, wild_vars=("A_cont", "CT"),
                         rng=rng)
    out = {"tag": tag, "n_sample": int(len(s)), "n_concepts": int(s.concept_id.nunique()),
           "tag_weighted_cov": float(s.n_prof_tags.sum() / s.n_tags.sum()),
           "sd_A_cont": float(s.A_cont.std()), "mean_A_cont": float(s.A_cont.mean()),
           "Y_strict_zero_share": float((s.Y_strict == 0).mean()), "coprimary": _row(co), "primary": _row(pr),
           "decision_coprimary": vmodels.decide(co) if co else None,
           "decision_primary": vmodels.decide(pr) if pr else None,
           "controls_coprimary": sc, "controls_primary": pc}
    logger.info(f"[{tag}] n={out['n_sample']} coprimary {out['coprimary']} | primary {out['primary']}")
    return out


def _row(r: dict | None) -> dict | None:
    if r is None:
        return None
    out = {"N": r["n_retained"], "G": r["G"], "retained_share": r["retained_share"]}
    for v in ("A_cont", "CT"):
        out[v] = {"b": r["coef"][v], "se": r["se"][v], "p_crv1": r["p"][v], "irr_sd": r["irr_sd"][v],
                  "ci_irr_sd": r["ci_irr_sd"][v], "irr_01": r["irr_01"][v],
                  "p_wild": (r.get("p_wild") or {}).get(v)}
    return out


# ---------------------------------------------------------------------------------------------- harmonisation variants
def variant_G(G: dict, floor: float = 0.2, topic_filter: bool = True, dedup: bool = True) -> dict:
    """Rebuild partners (concept-tag floor), the known-subfield rule and the link dedup of a prepared G."""
    H = copy.copy(G)
    H["W"] = dict(G["W"])
    if floor != 0.2:
        kmap, level = vio.keyword_map()
        parts = sorted((vio.D5 / "hyd" / "works").glob("works_part_*.parquet"))
        w = pd.concat([pq.read_table(p, columns=["work_id", "keyword_idx", "concept_ids", "concept_scores"]).to_pandas()
                       for p in parts], ignore_index=True)
        if not (w.work_id.to_numpy() == G["W"]["work_id"]).all():
            raise RuntimeError("work order differs from the prepared cache")
        plist = []
        for ci, cs, ki in zip(w.concept_ids, w.concept_scores, w.keyword_idx):
            s = set()
            if ci is not None:
                s.update(int(c) for c, sc in zip(ci, cs) if sc >= floor)
            if ki is not None and len(ki):
                m = kmap[np.asarray(ki, np.int64)]
                s.update(int(x) for x in m[m >= 0])
            plist.append(sorted(x for x in s if level.get(x) != 0))
        H["P"] = vio._csr(plist)
        del w, plist
        gc.collect()
    if not topic_filter:
        H["W"]["sub"] = G["W"]["sub_raw"].copy()
    if not dedup:
        cw = pd.read_parquet(vio.D5 / "hyd" / "concept_work.parquet", columns=["concept_id", "work_id", "year"])
        row_of = pd.Series(np.arange(len(G["W"]["work_id"])), index=G["W"]["work_id"])
        cw = cw[cw.work_id.isin(row_of.index)].copy()
        cw["row"] = row_of.reindex(cw.work_id).to_numpy()
        links = {}
        for cid, g in cw.sort_values(["concept_id", "year", "work_id"]).groupby("concept_id"):
            links[cid] = (g.row.to_numpy(np.int64), g.year.to_numpy(np.int32))
        H["links"] = links
    return H


def run(G: dict | None = None) -> dict:
    G = G or vio.prepare()
    pop = copy_population()
    res = {"gate1": gate1(G)}
    if not res["gate1"]["pass"]:
        dump(common.RESULTS / "gates.json", res)
        raise RuntimeError("GATE 1 failed: iteration-1 events not reproduced (see results/gate/gate1)")
    g2 = screen_pipeline(G, pop, "gate2")
    co, pr = g2["coprimary"], g2["primary"]
    checks = {"coprimary_N": co["N"] == MAIN_COPRIMARY["N"], "coprimary_G": co["G"] == MAIN_COPRIMARY["G"],
              "coprimary_bA": abs(co["A_cont"]["b"] - MAIN_COPRIMARY["b_A"]) < 0.01,
              "coprimary_irr_sd": abs(co["A_cont"]["irr_sd"] - MAIN_COPRIMARY["irr_sd"]) < 0.005,
              "primary_N": pr["N"] == MAIN_PRIMARY["N"], "primary_G": pr["G"] == MAIN_PRIMARY["G"],
              "primary_bA": abs(pr["A_cont"]["b"] - MAIN_PRIMARY["b_A"]) < 0.02}
    g2["checks"] = checks
    g2["pass"] = all(checks.values())
    res["gate2"] = g2
    dump(common.RESULTS / "gates.json", res)
    if not g2["pass"]:
        raise RuntimeError(f"GATE 2 failed: {checks}")
    logger.info("GATES 1 and 2 PASSED")
    rows = [_flat("gate2 (exp_7 reproduction)", g2)]
    specs = {"h1_floor03": dict(floor=0.3), "h2_no_topic_filter": dict(topic_filter=False),
             "h3_no_dedup": dict(dedup=False), "h4_mesh_rules": dict(floor=0.3, topic_filter=False, dedup=False)}
    hres = {}
    for tag, kw in specs.items():
        H = variant_G(G, **kw)
        hres[tag] = screen_pipeline(H, pop, tag)
        rows.append(_flat(tag, hres[tag]))
        if tag == "h4_mesh_rules":
            hres["h5_mesh_rules_no_topic_ctrl"] = screen_pipeline(H, pop, "h5_mesh_rules_no_topic_ctrl",
                                                                  drop_topic=True)
            rows.append(_flat("h5_mesh_rules_no_topic_ctrl", hres["h5_mesh_rules_no_topic_ctrl"]))
        del H
        gc.collect()
    res["harmonisation"] = hres
    res["harmonisation_label"] = "harmonisation, not confirmation (screen fold, already seen)"
    dump(common.RESULTS / "gates.json", res)
    pd.DataFrame(rows).to_csv(common.RESULTS / "harmonisation_rows.csv", index=False)
    return res


def _flat(tag: str, r: dict) -> dict:
    out = {"row": tag, "n_sample": r["n_sample"], "tag_weighted_cov": r["tag_weighted_cov"], "sd_A_cont": r["sd_A_cont"],
           "label": "harmonisation, not confirmation" if tag.startswith("h") else "gate"}
    for spec in ("coprimary", "primary"):
        x = r[spec]
        if x is None:
            continue
        out.update({f"{spec}_N": x["N"], f"{spec}_G": x["G"], f"{spec}_b_A": x["A_cont"]["b"],
                    f"{spec}_se_A": x["A_cont"]["se"], f"{spec}_irr_sd_A": x["A_cont"]["irr_sd"],
                    f"{spec}_irr_sd_A_lo": x["A_cont"]["ci_irr_sd"][0], f"{spec}_irr_sd_A_hi": x["A_cont"]["ci_irr_sd"][1],
                    f"{spec}_p_A": x["A_cont"]["p_crv1"], f"{spec}_p_wild_A": x["A_cont"]["p_wild"],
                    f"{spec}_irr_sd_CT": x["CT"]["irr_sd"], f"{spec}_p_CT": x["CT"]["p_crv1"],
                    f"{spec}_reading": (r[f"decision_{spec}"] or {}).get("reading")})
    return out


def harmonise_h6(G: dict | None = None) -> dict:
    """h6 (run after the MeSH nativeness fetch; screen fold, harmonisation only): h4 rules on main, with nativeness
    restricted to the (node, block) profiles the MeSH ranking rule would have reached. Main screen needed pairs are
    ranked by entry-year tag weight (the MeSH rule) and kept top-down until the MeSH exact coverage of needed weight
    is reached (h6a: exact only); h6b adds the admitted bg-sample shares for the remaining pairs (the MeSH source rule).
    """
    import pickle
    from collections import defaultdict

    import nativeness
    G = G or vio.prepare()
    pop = copy_population()
    H = variant_G(G, floor=0.3, topic_filter=False, dedup=False)
    ev = pd.read_parquet(GATE / "h4_mesh_rules" / "screen_events_with_outcomes.parquet")
    s = vmodels.primary_sample(ev)
    con = H["concepts"].set_index("concept_id")
    w = defaultdict(float)
    for x in s.itertuples():
        c = con.loc[x.concept_id]
        own = int(c.own_node) if pd.notna(c.own_node) else None
        _, _, nn = vfeatures.event_tags(H, x.concept_id, int(x.d), int(x.e), own)
        for j in nn.tolist():
            w[(int(j), vfeatures.block_of(int(x.e)))] += 1
    nsum = json.loads((common.RESULTS / "nativeness_ledger_summary.json").read_text())
    target = nsum["exact_weight_share"]
    tot = sum(w.values())
    keep, cum = set(), 0.0
    for k, v in sorted(w.items(), key=lambda kv: (-kv[1], kv[0])):
        if cum / tot >= target:
            break
        if k in H["prof"]:
            keep.add(k)
        cum += v
    out = {"target_exact_weight_share_from_mesh": target, "pairs_kept": len(keep), "pairs_needed": len(w)}
    Ha = dict(H)
    Ha["prof"] = {k: v for k, v in H["prof"].items() if k in keep}
    out["h6a"] = screen_pipeline(Ha, pop, "h6a_ranking_rule_exact")
    bg = nativeness.bg_shares({k[0] for k in w})
    Hb = dict(Ha)
    Hb["prof"] = dict(Ha["prof"])
    for k in w:
        if k not in Hb["prof"] and k in bg:
            n_, wt, dd = bg[k]
            Hb["prof"][k] = (wt, dd, False)
    out["h6b"] = screen_pipeline(Hb, pop, "h6b_ranking_rule_plus_bg")
    res = json.loads((common.RESULTS / "gates.json").read_text())
    res["harmonisation"]["h6a_ranking_rule_exact"] = out["h6a"]
    res["harmonisation"]["h6b_ranking_rule_plus_bg"] = out["h6b"]
    res["h6_info"] = {k: v for k, v in out.items() if k not in ("h6a", "h6b")}
    res["h6_info"]["note"] = ("computed after the MeSH outcome look (it needs the MeSH fetch coverage); main screen "
                              "only, harmonisation, cannot change the frozen G4 verdict")
    dump(common.RESULTS / "gates.json", res)
    rows = pd.read_csv(common.RESULTS / "harmonisation_rows.csv")
    rows = rows[~rows.row.str.startswith("h6")]
    rows = pd.concat([rows, pd.DataFrame([_flat("h6a_ranking_rule_exact", out["h6a"]),
                                          _flat("h6b_ranking_rule_plus_bg", out["h6b"])])], ignore_index=True)
    rows.to_csv(common.RESULTS / "harmonisation_rows.csv", index=False)
    return out
