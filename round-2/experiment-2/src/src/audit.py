"""STEP 1: reconciliation audit of the iteration-1 numbers (each table names its source file)."""
from __future__ import annotations

import json
from collections import Counter

import pandas as pd
from loguru import logger

import io_load
from common import DS1, RESULTS

OUT = RESULTS / "audit"
HYP_QUOTE_OLD = {2010: 13, 2011: 23, 2012: 40, 2013: 54, 2014: 63}


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    G = io_load.prepare()
    con = G["concepts"]
    lk = G["links_lenient"]
    res = {}
    # 1a match evidence
    t = lk.groupby(["arm", "match_evidence"]).size().unstack(fill_value=0)
    t.loc["all"] = t.sum()
    sh = t.div(t.sum(1), axis=0).round(4)
    pd.concat([t.add_prefix("n_"), sh.add_prefix("share_")], axis=1).to_csv(OUT / "1a_match_evidence.csv")
    res["1a_match_evidence"] = {"source": "concept_work.parquet + data_out.json arm", "counts": t.to_dict("index"),
                                "shares": sh.to_dict("index")}
    # 1b route counts
    rc = con.groupby(["arm", "route"]).size().unstack(fill_value=0)
    rc.to_csv(OUT / "1b_route_counts.csv")
    exp = {"main": {"A_openalex_native": 24, "B_s2_index": 160}, "reference": {"A_openalex_native": 2, "B_s2_index": 20}}
    got = rc.to_dict("index")
    res["1b_route_counts"] = {"source": "data_out.json metadata_retrieval_route", "counts": got, "expected": exp,
                              "match": all(got.get(a, {}).get(r) == n for a, d in exp.items() for r, n in d.items())}
    # 1c sense flags
    sf = con[con.sense_check_fail][["concept_id", "phrase", "sense_share", "fold", "arm", "n_works_d1"]].copy()
    sf["threshold"] = 0.70
    sf.to_csv(OUT / "1c_sense_flagged.csv", index=False)
    res["1c_sense_flagged"] = {"source": "data_out.json metadata_flags / metadata_sense_dominant_share (assemble.py: < 0.7)",
                               "n": int(len(sf))}
    # 1d reference rule as coded
    scr = (DS1 / "screen.py").read_text().splitlines()
    smp = (DS1 / "sample_frame.py").read_text().splitlines()
    res["1d_reference_rule"] = {"screen.py_lines_28_31": scr[27:31], "sample_frame.py_line_132": smp[131:132],
                                "n_reference_eligible": 263, "n_reference_sampled": 60, "n_reference_in_prefix": int((con.arm == "reference").sum()),
                                "note": "status REJECT_PREEXISTING, >= 5 hits every year 1998-2004, sum 1998-2004 in [70,700]; "
                                        "drawn from all screened candidates with reference_eligible"}
    # 1e fold x F_band, old tags vs new focal rule
    m = con[con.arm == "main"].copy()
    m["old_screen_nonempty"] = m.focal_screen.map(len) > 0
    m["old_heldout_nonempty"] = m.focal_heldout.map(len) > 0
    m["new_nfocal"] = m.F.astype(int).map(lambda F: len([t for t in range(F + 3, F + 9) if t <= 2019]))
    old = {b: {"screen": int(g.old_screen_nonempty.sum()), "heldout": int(g.old_heldout_nonempty.sum())} for b, g in m.groupby("F_band")}
    new = m.groupby(["F_band", "fold"]).agg(n_concepts=("concept_id", "size"), focal_years_total=("new_nfocal", "sum")).reset_index()
    new.to_csv(OUT / "1e_fold_fband_new_rule.csv", index=False)
    res["1e_fold_fband"] = {"source": "data_out.json metadata_focal_years_* (OLD) / F (NEW)",
                            "old_tags_nonempty (both folds pooled per tag)": old,
                            "assemble_summary_reported": json.loads((DS1 / "logs" / "assemble_summary.json").read_text())[
                                "screen_heldout_focal_nonempty_by_band"],
                            "new_rule": new.to_dict("records")}
    # 1f eligible units by fold x focal year
    e = pd.read_parquet(RESULTS / "cache" / "main_edges_noboot.parquet")
    h = e[e.role == "host"].copy()
    h["fold"] = h.concept_id.map(con.set_index("concept_id").fold)
    new_t = h.groupby(["fold", "t"]).agg(units=("d", "size"), concepts=("concept_id", "nunique"), hosts=("d", "nunique")).reset_index()
    new_t.to_csv(OUT / "1f_eligible_units_new_rule.csv", index=False)
    old_h = h[(h.fold == "screen") & h.t.between(2010, 2014)]
    old_t = old_h.groupby("t").agg(units=("d", "size"), concepts=("concept_id", "nunique"), hosts=("d", "nunique")).reset_index()
    old_t["hypothesis_quote"] = old_t.t.map(HYP_QUOTE_OLD)
    old_t.to_csv(OUT / "1f_eligible_units_old_rule.csv", index=False)
    nd = {}
    for scope, mm in [("screen_fold", m[m.fold == "screen"]), ("all_main", m)]:
        for t in range(2010, 2015):
            n = 0
            for c in mm.itertuples():
                if not 3 <= t - int(c.F) <= 8:
                    continue
                g = lk[(lk.concept_id == c.concept_id) & lk["sub"].notna() & (lk["sub"] != c.origin_sub) & lk.year.between(t - 5, t)]
                n += int((g.groupby("sub").size() >= 10).sum())
            nd[f"{scope}|{t}"] = n
    by_age = h.groupby(["fold", "age"]).agg(units=("d", "size"), concepts=("concept_id", "nunique")).reset_index()
    by_age.to_csv(OUT / "1f_eligible_units_by_age.csv", index=False)
    res["1f_eligible_units"] = {"source": "results/cache/main_edges_noboot.parquet (this artifact; >= 10 W1 d-papers after dedup)",
                                "old_rule_screen_2010_14": old_t.to_dict("records"),
                                "note": "the hypothesis quote 13/23/40/54/63 is compared per year; our counts use dedup'ed c-papers "
                                        "and D1 origin_subfield; differences reflect the unit definition used in the quote "
                                        "(unknown: units vs concepts) — both are reported",
                                "old_rule_no_dedup_variant": nd,
                                "new_rule_total_units": int(len(h)), "new_rule_concepts": int(h.concept_id.nunique())}
    # 1g origin recompute (no dedup, modal subfield in F..F+2)
    agree = []
    for c in m.itertuples():
        g = lk[(lk.concept_id == c.concept_id) & lk.year.between(int(c.F), int(c.F) + 2) & lk["sub"].notna()]
        mode = Counter(g["sub"].astype(int)).most_common(1)
        rec = int(mode[0][0]) if mode else None
        agree.append({"concept_id": c.concept_id, "d1_origin": c.origin_sub, "recomputed": rec, "agree": rec == c.origin_sub})
    ag = pd.DataFrame(agree)
    ag.to_csv(OUT / "1g_origin_recompute.csv", index=False)
    res["1g_origin_recompute"] = {"source": "concept_work.parquet + works parquet", "agreement_share": float(ag.agree.mean()),
                                  "n_mismatch": int((~ag.agree).sum()), "policy": "mismatches logged, D1 origin kept"}
    res["loader_year_check"] = G["year_check"]
    (OUT / "audit_summary.json").write_text(json.dumps(res, indent=2, default=str))
    logger.info(f"audit: routes match={res['1b_route_counts']['match']}, sense={res['1c_sense_flagged']['n']}, "
                f"origin agreement={res['1g_origin_recompute']['agreement_share']:.3f}")
