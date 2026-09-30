#!/usr/bin/env python3
"""PART 3: decision rules (a)-(d) with per-condition verdicts, the 9-row like-for-like aligned-block table with IVW/Q
re-derived, the held-out seal audit, and the request coverage table.

Outputs: results/aligned_block_table.{csv,md}, results/decision_rules.{json,md}, results/heldout_audit.json,
results/coverage_table.{csv,md}
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

import common as K

IDRX = re.compile(rb"c_[0-9a-f]{12}")


# ------------------------------------------------------------------ T1 aligned block
def aligned_block() -> pd.DataFrame:
    sp = K.E4 / "results/side_by_side_mainpool_vs_mesh.csv"
    s = pd.read_csv(sp)
    s = s[(s.version == "primary") & s.label.isin(["E", "E_alt", "E_up"]) & s.indicator.isin(["accretion_shift_rar", "closure", "P_rar"])]
    al = pd.read_csv(K.E4 / "results/rq1_effects_mainpool_aligned.csv")
    rows = []
    for r in s.itertuples():
        fn = {"E": "summary.json", "E_alt": "summary_E_alt.json", "E_up": "summary_E_up.json"}[r.label]
        mt = [t for t in K.load_json(K.E3 / "results/event_study" / fn)["table"] if t["indicator"] == r.indicator and t["version"] == "primary"][0]
        am = al[(al.label == r.label) & (al.indicator == r.indicator) & (al.version == "primary")].iloc[0]
        se_main, se_mesh = mt["se"], float(am.se) if np.isfinite(am.se) else (r.ci_hi_mesh - r.ci_lo_mesh) / 3.92
        iv = K.ivw([r.S_mesh, r.S_main], [se_mesh, se_main])
        ivc = K.ivw([r.S_mesh, r.S_main], [(r.ci_hi_mesh - r.ci_lo_mesh) / 3.92, (r.ci_hi_main - r.ci_lo_main) / 3.92])
        interp = bool(min(r.n_treated_mesh, r.n_treated_main) >= 10 and r.n_eff_window >= 10)
        rows.append(dict(label=r.label, indicator=r.indicator, S_mesh=r.S_mesh, ci_lo_mesh=r.ci_lo_mesh, ci_hi_mesh=r.ci_hi_mesh,
                         se_mesh=se_mesh, n_treated_mesh=int(r.n_treated_mesh), n_eff_window=int(r.n_eff_window), p_holm_mesh=r.p_holm_mesh,
                         S_main=r.S_main, ci_lo_main=r.ci_lo_main, ci_hi_main=r.ci_hi_main, se_main=se_main, n_treated_main=int(r.n_treated_main),
                         p_holm_main=r.p_holm_main, p_holm_main_eventstudy_file=mt.get("p_holm"), sign_agree=bool(np.sign(r.S_mesh) == np.sign(r.S_main)),
                         S_ivw=iv["S_ivw"], se_ivw=iv["se_ivw"], ivw_ci_lo=iv["ci"][0], ivw_ci_hi=iv["ci"][1], Q=iv["Q"], p_Q=iv["p_Q"], I2=iv["I2"],
                         S_ivw_file=r.S_pooled_ivw, se_ivw_file=r.se_pooled_ivw, Q_file=r.Q_heterogeneity,
                         S_ivw_ciwidth_se=ivc["S_ivw"], se_ivw_ciwidth_se=ivc["se_ivw"], Q_ciwidth_se=ivc["Q"],
                         ivw_agrees_file=bool(abs(ivc["S_ivw"] - r.S_pooled_ivw) < 1e-6 and abs(ivc["Q"] - r.Q_heterogeneity) < 1e-6),
                         ivw_bootstrap_se_vs_file_diff=float(iv["S_ivw"] - r.S_pooled_ivw),
                         S_main_agrees_eventstudy=bool(abs(mt["S"] - r.S_main) < 1e-6),
                         interpretable=interp,
                         note="" if interp else f"NOT interpretable: n_treated main {int(r.n_treated_main)} / MeSH {int(r.n_treated_mesh)}, "
                                                f"n_eff_window {int(r.n_eff_window)} (< 10); Q is meaningless here"))
    df = pd.DataFrame(rows)
    df.to_csv(K.RES / "aligned_block_table.csv", index=False)
    L = [f"# Aligned-block table (main-pool labels/precursors on both populations)\n\n**{K.HEADER}** — both populations already screened.\n",
         "| label | indicator | S_mesh [95% CI] | n_mesh | n_eff | Holm mesh | S_main [95% CI] | n_main | Holm main | sign agree | S_ivw (se) [boot SE] | Q (p_Q) [boot SE] | S_ivw / Q [CI-width SE = file method] | file reproduced | interpretable |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        L.append(f"| {r.label} | {r.indicator} | {r.S_mesh:.3f} [{r.ci_lo_mesh:.3f}, {r.ci_hi_mesh:.3f}] | {r.n_treated_mesh} | {r.n_eff_window} | {r.p_holm_mesh:.3f} | "
                 f"{r.S_main:.3f} [{r.ci_lo_main:.3f}, {r.ci_hi_main:.3f}] | {r.n_treated_main} | {r.p_holm_main:.3f} | {r.sign_agree} | {r.S_ivw:.3f} ({r.se_ivw:.3f}) | "
                 f"{r.Q:.2f} ({r.p_Q:.3f}) | {r.S_ivw_ciwidth_se:.3f} / {r.Q_ciwidth_se:.2f} | {r.ivw_agrees_file} | {r.interpretable} |")
    L.append("\nIVW and Q re-derived twice: (i) with bootstrap SEs (main: exp_3 summary*.json 'se'; MeSH: rq1_effects_mainpool_aligned.csv 'se'); "
             "(ii) with SE = CI width / 3.92, which reproduces the side-by-side file exactly (the file's method). The two differ where bootstrap "
             "distributions are skewed (accretion rows with n_eff 3-12). "
             "Q (df = 1) has very low power at k = 2; a small Q is not evidence of homogeneity.\n")
    L.append("Source: 3_invention_loop/iter_2/gen_art/gen_art_experiment_4/results/side_by_side_mainpool_vs_mesh.csv; "
             "3_invention_loop/iter_2/gen_art/gen_art_experiment_4/results/rq1_effects_mainpool_aligned.csv; "
             "3_invention_loop/iter_2/gen_art/gen_art_experiment_3/results/event_study/summary*.json")
    (K.RES / "aligned_block_table.md").write_text("\n".join(L))
    return df


# ------------------------------------------------------------------ seal audit
def heldout_ids() -> tuple[set, set, dict]:
    cache = K.RES / "cache_d5_pool.json"
    pool = K.load_json(cache)["pool"] if cache.exists() else []
    ho119 = {c for c, f, _ in pool if f == "heldout_concept"}
    ho61, info = set(), {}
    for f in sorted(glob.glob(str(K.D1_IT1 / "full_data_out/full_data_out_*.json"))):
        d = K.load_json(f)
        for ds in d["datasets"]:
            if ds["dataset"] == "concept_pool_2005_2016":
                for ex in ds["examples"]:
                    if ex.get("metadata_fold") == "heldout_concept":
                        ho61.add(ex["metadata_concept_id"])
        del d
    info = dict(n_heldout_dataset5=len(ho119), n_heldout_iter1=len(ho61), iter1_subset_of_dataset5=ho61 <= ho119,
                n_iter1_not_in_dataset5=len(ho61 - ho119),
                source_dataset5="3_invention_loop/iter_2/gen_art/gen_art_dataset_5/full_data_out/full_data_out_*.json [concept_pool_2005_2016].metadata_fold",
                source_iter1="3_invention_loop/iter_1/gen_art/gen_art_dataset_1/full_data_out/full_data_out_*.json [concept_pool_2005_2016].metadata_fold")
    return ho119, ho61, info


def scan_file(path: Path, ids: set) -> dict:
    """All c_<12 hex> tokens in the file (parquet string columns + raw bytes for everything else)."""
    found: set = set()
    try:
        if path.suffix == ".parquet":
            import pyarrow.parquet as pq
            t = pq.read_table(path)
            for name in t.column_names:
                col = t.column(name)
                if str(col.type) in ("string", "large_string") or "dictionary" in str(col.type):
                    for v in set(col.to_pylist()):
                        if isinstance(v, str):
                            found.update(m.decode() for m in IDRX.findall(v.encode()))
                elif "list" in str(col.type):
                    for v in col.to_pylist():
                        found.update(m.decode() for m in IDRX.findall(json.dumps(v).encode()))
            found.update(m.decode() for m in IDRX.findall(" ".join(t.column_names).encode()))
        else:
            with open(path, "rb") as f:
                found.update(m.decode() for m in IDRX.findall(f.read()))
    except (OSError, ValueError) as e:
        return dict(error=str(e)[:200])
    hits = sorted(found & ids)
    return dict(n_ids_found=len(found), n_heldout_hits=len(hits), heldout_hits=hits[:20])


def seal_audit(ho119: set, ho61: set, info: dict) -> dict:
    ids = ho119 | ho61
    out = {"id_sets": info, "exp3_exp4": [], "exp2": [], "extra_checks": {}}
    for root in (K.E3 / "results", K.E4 / "results"):
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.stat().st_size < 2e9:
                r = scan_file(p, ids)
                r["file"] = K.rel(p)
                out["exp3_exp4"].append(r)
    for p in sorted((K.E2 / "results").rglob("*")):
        if p.is_file():
            r = scan_file(p, ids)
            r["file"] = K.rel(p)
            if r.get("n_heldout_hits", 0):
                cols = []
                if p.suffix == ".csv":
                    cols = list(pd.read_csv(p, nrows=0).columns)
                elif p.suffix == ".parquet":
                    import pyarrow.parquet as pq
                    cols = pq.read_schema(p).names
                r["columns"] = cols[:60]
                r["note"] = "held-out rows present by design: check whether outcome columns were computed"
                r["w2_like_columns"] = [c for c in cols if re.search(r"(W2|w2|onset|future|fut|_t5|uptake|outcome)", c)]
            out["exp2"].append(r)
    # sealed focal years in exp_3 labels
    lab = pd.read_parquet(K.E3 / "results/labels/emergence_screen.parquet")
    out["extra_checks"]["exp3_labels_focal_years_2016_18_rows"] = int(lab.t.isin([2016, 2017, 2018]).sum())
    out["extra_checks"]["exp3_labels_heldout_concepts"] = int(lab.concept_id.isin(ids).sum())
    ind = pd.read_parquet(K.E3 / "results/indicators/concept_year_indicators.parquet", columns=["concept_id", "fold"])
    out["extra_checks"]["exp3_indicator_folds"] = ind.fold.value_counts().to_dict()
    gf = pd.read_csv(K.E2 / "results/gate_a/graft_fallback_events.csv")
    ho_ev = gf[gf.fold == "heldout_concept"]
    out["extra_checks"]["exp2_graft_events_heldout_rows"] = int(len(ho_ev))
    out["extra_checks"]["exp2_graft_events_columns"] = list(gf.columns)
    out["extra_checks"]["exp2_graft_events_note"] = ("graft_fallback_events.csv lists host-ENTRY events (concept, subfield, entry year e, n entry keywords, "
                                                     "anchored proxy) for held-out concepts by design; no W2 outcome column (breadth gain, uptake) is present")
    os_ = pd.read_csv(K.E2 / "results/origin/origin_series.csv")
    ho_os = os_[os_.concept_id.isin(ids)]
    co = pd.read_csv(K.E2 / "results/origin/cooling_onsets.csv")
    ho_co = co[co.concept_id.isin(ids)]
    out["extra_checks"]["exp2_origin_series_heldout"] = dict(n_concepts=int(ho_os.concept_id.nunique()), max_year=int(ho_os.y.max()) if len(ho_os) else None,
                                                             n_rows=int(len(ho_os)))
    out["extra_checks"]["exp2_cooling_onsets_heldout"] = dict(n_concepts=int(len(ho_co)), n_with_onset_0_7=int(ho_co["onset_0.7"].notna().sum()))
    out["extra_checks"]["exp2_caveat"] = (f"exp_2 computed origin-subfield series through {out['extra_checks']['exp2_origin_series_heldout']['max_year']} and "
                                          f"cooling onsets for {len(ho_co)} held-out concepts (outcome-adjacent, post-t years); they are not RQ1 labels and are "
                                          "not read by exp_3/exp_4, but the held-out fold is no longer 'untouched' at the level of exp_2 descriptive outputs")
    tot = sum(r.get("n_heldout_hits", 0) for r in out["exp3_exp4"])
    out["hits_exp3_exp4_total"] = tot
    out["files_scanned_exp3_exp4"] = len(out["exp3_exp4"])
    out["files_with_hits_exp3_exp4"] = [r["file"] for r in out["exp3_exp4"] if r.get("n_heldout_hits", 0)]
    out["verdict"] = "SEALED" if tot == 0 and out["extra_checks"]["exp3_labels_focal_years_2016_18_rows"] == 0 else "BREACHED"
    out["limitation"] = ("Analysis-level seal only: it shows no held-out id was ANALYSED (appears) in exp_3/exp_4 outputs. It cannot show that nobody "
                         "looked at held-out raw data: dataset_5 holds full 2000-2024 works for all 426 concepts including the 119 held-out.")
    K.dump(out, K.RES / "heldout_audit.json")
    return out


# ------------------------------------------------------------------ T2 rules
def verbatim_rules() -> tuple[str | None, str | None]:
    p = K.RUN_ROOT / "3_invention_loop/iter_2/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json"
    if not p.exists():
        return None, None
    s = json.dumps(K.load_json(p))
    i = s.find("DECISION RULES FOR ITERATION 3")
    if i < 0:
        return None, K.rel(p)
    j = s.find('"', i)
    return s[i:j], K.rel(p)


def rules(audit: dict, r1a: dict | None) -> dict:
    text, src = verbatim_rules()
    status = "verbatim" if text else "reconstructed"
    parts = {}
    if text:
        for lab in "abcd":
            m = re.search(rf"\({lab}\)(.*?)(?=\([a-d]\) |$)", text)
            parts[lab] = m.group(1).strip() if m else None
    ga = K.load_json(K.E2 / "results/gate_a/gate_A_verdict.json")
    gf = pd.read_csv(K.E2 / "results/gate_a/graft_fallback_events.csv")
    dec = K.load_json(K.E2 / "results/power/decisions.json")
    gb = K.load_json(K.E2 / "results/power/gate_b.json")
    share = ga["share_edges_ge_040"]
    ra = dict(rule="a", text=parts.get("a"), text_status=status, condition="Gate A PASS iff > 50% of main-arm host edge-years (|Kd| >= 10) have within-host share >= 0.40",
              value=share, threshold=0.5, gate_A="FAIL" if share <= 0.5 else "PASS", triggered=bool(share <= 0.5),
              verdict="TRIGGERED: graft fallback supplies H1/H2 labels; claim restated as the grafting alternate" if share <= 0.5 else "NOT TRIGGERED",
              graft_events=dict(total=len(gf), kw5=int((gf.n_kw >= 5).sum()), kw5_screen=int(((gf.n_kw >= 5) & (gf.fold == "screen")).sum()),
                                kw5_heldout=int(((gf.n_kw >= 5) & (gf.fold == "heldout_concept")).sum()),
                                kw5_e_ge_F=int(((gf.n_kw >= 5) & gf.e_ge_F).sum()) if "e_ge_F" in gf else None),
              source="3_invention_loop/iter_2/gen_art/gen_art_experiment_2/results/gate_a/gate_A_verdict.json; .../graft_fallback_events.csv")
    nc = dec["realised_N_c"]
    mde = dec["H1_MDE_main_nmin"]
    ep = gb["episode_counts"]["theta_0.7"]["labelled"]["episodes"]
    rb = dict(rule="b", text=parts.get("b"), text_status=status, condition="H1 pilot iff fewer than ~150 concepts carry a tested edge; H2 primary only if Gate B MDE <= 25%",
              realised_N_c=nc, projected_N_c=dec["projected_N_c"], projected_N_c_90=dec["projected_N_c_90"], pilot_only=bool(nc < 150),
              mde_delta_auc_base070=mde["auc|nmin30|AUC0.7|realised"], mde_delta_auc_base080=mde["auc|nmin30|AUC0.8|realised"],
              gateB_labelled_episodes=ep, gateB_mde="not estimable (0 labelled episodes)", H2_primary=False,
              verdict=f"H1 PILOT-ONLY (N_c {nc} < 150; MDE delta-AUC {mde['auc|nmin30|AUC0.7|realised']:.3f} / {mde['auc|nmin30|AUC0.8|realised']:.3f}); "
                      "H2 NOT primary (Gate B: 0 labelled episodes, MDE not estimable)",
              source="3_invention_loop/iter_2/gen_art/gen_art_experiment_2/results/power/decisions.json; gate_b.json")
    # rule c: condition by condition, per pre-named precursor, on the PRIMARY label E (and E_up shown as post hoc context)
    es = {lab: K.load_json(K.E3 / "results/event_study" / fn) for lab, fn in (("E", "summary.json"), ("E_alt", "summary_E_alt.json"), ("E_up", "summary_E_up.json"))}
    pred = K.load_json(K.E3 / "results/prediction/summary.json")
    al = pd.read_csv(K.E4 / "results/rq1_effects_mainpool_aligned.csv")
    mesh_native = pd.read_csv(K.E4 / "results/rq1_effects.csv")
    conds = []
    for lab in ("E", "E_up"):
        dpred = pred[f"{lab}_h5"]["eval"]["logit"]["deltas"]["FULL_vs_BASELINE"]
        c2 = bool(dpred["ci"][0] > 0 or dpred["ci"][1] < 0) and dpred["delta"] > 0
        for t in es[lab]["table"]:
            if t.get("version") != "primary" or t["family"] not in ("accretion", "closure", "participation"):
                continue
            c1 = bool(t["ci"][0] > 0 or t["ci"][1] < 0)
            sign_plus = bool(t["S"] > 0)
            am = al[(al.label == lab) & (al.indicator == t["indicator"]) & (al.version == "primary")].iloc[0]
            c3 = bool(np.sign(am.S) == np.sign(t["S"]))
            c3_sig = bool((am.ci_lo > 0 or am.ci_hi < 0) and c3)
            conds.append(dict(label=lab, label_status="PRIMARY (pre-registered)" if lab == "E" else "post hoc (promoted)", precursor=t["indicator"],
                              n_treated=t["n_treated"], S=t["S"], ci=t["ci"],
                              c1_eventstudy_ci_excludes_0=c1, c1b_sign_as_preregistered_plus=sign_plus,
                              c2_rolling_origin_dAUC_ci_excludes_0_and_positive=c2, dAUC_logit=dpred["delta"], dAUC_ci=dpred["ci"],
                              c3_keeps_sign_on_MeSH_aligned=c3, c3b_MeSH_same_sign_and_significant=c3_sig, S_mesh=float(am.S),
                              ci_mesh=[float(am.ci_lo), float(am.ci_hi)],
                              c4_holds_on_sealed_heldout_and_2016_18=False, c4_note="not yet run (iteration-4 sealed test)",
                              all_met=bool(c1 and sign_plus and c2 and c3 and False)))
    mp = mesh_native[(mesh_native.rel_year == "D_-3_-1") & (mesh_native.volume_def == "PRIMARY") & (mesh_native.subset == "all") &
                     (mesh_native.outcome == "E") & (mesh_native.version == "raw") & mesh_native.indicator.isin(["closure_lr", "accretion_share", "dP"])]
    rc = dict(rule="c", text=parts.get("c"), text_status=status,
              conditions_verbatim=["(c1) a pre-named per-paper precursor has an event-study CI excluding 0 on the main screen fold",
                                   "(c2) AND a rolling-origin delta-AUC CI excluding 0 on the main screen fold (primary estimator = logit)",
                                   "(c3) keeps its sign on MeSH",
                                   "(c4) holds on the sealed held-out sha1 fold and the 2016-18 focal years (iteration 3+)",
                                   "(plan addition c1b) the sign is as pre-registered (+)"],
              per_precursor=conds,
              mesh_plan_native_primary=[dict(indicator=r.indicator, D=r["diff"], ci=[r.ci_lo, r.ci_hi], p_holm=r.p_holm, n_eff=int(r.n_eff_window))
                                        for _, r in mp.iterrows()],
              volume_in_disguise_clause=("not applicable: the volume-normalised primary closure (and its residualised version) carries the E_up signal, "
                                         "so the result is not 'raw-only'"),
              met=False,
              verdict="NOT MET: no pre-named precursor satisfies c1 AND c2 AND c3 AND c4 on the primary label; c2 fails for every label (logit "
                      "delta-AUC CI covers 0), c1b fails (all significant effects are NEGATIVE, opposite to the pre-registered +), and c4 is not yet run",
              source="exp_3 results/event_study/summary*.json, results/prediction/summary.json; exp_4 results/rq1_effects_mainpool_aligned.csv, rq1_effects.csv")
    rd = dict(rule="d", text=parts.get("d"), text_status=status, condition="held-out sha1 fold, 2016-18 focal years and phrase pool untouched",
              heldout_ids=audit["id_sets"], hits_exp3_exp4=audit["hits_exp3_exp4_total"], files_scanned=audit["files_scanned_exp3_exp4"],
              files_with_hits=audit["files_with_hits_exp3_exp4"], focal_2016_18_label_rows=audit["extra_checks"]["exp3_labels_focal_years_2016_18_rows"],
              exp2_files_with_heldout_rows=[r["file"] for r in audit["exp2"] if r.get("n_heldout_hits", 0)],
              sealed=audit["verdict"] == "SEALED", verdict=audit["verdict"] + " for exp_3/exp_4 label/W2 files (analysis-level); CAVEAT exp_2: "
              + audit["extra_checks"]["exp2_caveat"], limitation=audit["limitation"], exp2_caveat=audit["extra_checks"]["exp2_caveat"],
              source="results/heldout_audit.json (this artifact)")
    out = dict(header="Decision rules (a)-(d) fixed in iteration 2", rules_text_source=src, rules_text=text, text_status=status, a=ra, b=rb, c=rc, d=rd)
    if r1a:
        out["r1a_context"] = {k: v.get("verdict") for k, v in r1a["verdicts"].items()}
    K.dump(out, K.RES / "decision_rules.json")
    L = ["# Decision rules (a)-(d)\n", f"Rule text: **{status}**, from `{src}`:\n", f"> {text}\n" if text else "",
         "| rule | condition | key values | verdict |", "|---|---|---|---|",
         f"| (a) | Gate A share >= 0.40 must exceed 0.5 | share {share:.4f}; graft events {ra['graft_events']} | **{ra['verdict']}** |",
         f"| (b) | N_c >= ~150 for H1; Gate B MDE <= 25% for H2 | N_c {nc} (projected {dec['projected_N_c']} {dec['projected_N_c_90']}); MDE dAUC "
         f"{rb['mde_delta_auc_base070']:.3f}/{rb['mde_delta_auc_base080']:.3f}; Gate B episodes {ep} | **{rb['verdict']}** |",
         f"| (c) | c1 ES CI excl. 0 AND c2 rolling dAUC CI excl. 0 AND c3 MeSH same sign AND c4 held-out | see per-precursor table | **{rc['verdict']}** |",
         f"| (d) | held-out untouched | {audit['hits_exp3_exp4_total']} hits in {audit['files_scanned_exp3_exp4']} exp_3/exp_4 files; 2016-18 label rows "
         f"{rd['focal_2016_18_label_rows']}; 61 iter-1 ids subset of 119: {audit['id_sets']['iter1_subset_of_dataset5']} | **{rd['verdict']}** |",
         "\n## Rule (c), per condition\n", "| label | precursor | n | S [95% CI] | c1 | c1b (+) | c2 (dAUC logit [CI]) | c3 MeSH sign (S_mesh) | c4 | met |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for c in conds:
        L.append(f"| {c['label']} ({c['label_status']}) | {c['precursor']} | {c['n_treated']} | {c['S']:.3f} [{c['ci'][0]:.3f}, {c['ci'][1]:.3f}] | "
                 f"{'PASS' if c['c1_eventstudy_ci_excludes_0'] else 'FAIL'} | {'PASS' if c['c1b_sign_as_preregistered_plus'] else 'FAIL'} | "
                 f"{'PASS' if c['c2_rolling_origin_dAUC_ci_excludes_0_and_positive'] else 'FAIL'} ({c['dAUC_logit']:+.3f} [{c['dAUC_ci'][0]:.3f}, {c['dAUC_ci'][1]:.3f}]) | "
                 f"{'PASS' if c['c3_keeps_sign_on_MeSH_aligned'] else 'FAIL'} ({c['S_mesh']:.3f}) | NOT RUN | {c['all_met']} |")
    L.append("\nE rows: n = 3 matched treated, bootstrap CIs are not interpretable. MeSH plan-native PRIMARY: " +
             "; ".join(f"{m['indicator']} D={m['D']:.3f} [{m['ci'][0]:.3f}, {m['ci'][1]:.3f}] Holm {m['p_holm']:.3f}" for m in rc["mesh_plan_native_primary"]))
    L.append(f"\nSeal limitation: {audit['limitation']}\n")
    L.append("Source: 3_invention_loop/iter_2/gen_strat/gen_strat_1 (rule text); exp_2 results/gate_a, results/power; exp_3 results/event_study, "
             "results/prediction; exp_4 results/rq1_effects*.csv; results/heldout_audit.json")
    (K.RES / "decision_rules.md").write_text("\n".join(L))
    return out


# ------------------------------------------------------------------ T3 coverage
def coverage(rl: dict, r1a: dict | None) -> pd.DataFrame:
    v = (r1a or {}).get("verdicts", {})
    rows = [
        dict(item="RQ1", status="partial",
             evidence="art_mbFjmo5rbbf8 (main: E_up closure S -0.837 [-1.26,-0.43], n=21; pre-named + precursors not supported; logit dAUC -0.010 "
                      "[-0.045,0.021]); art_yWUkgWWKyq_h (MeSH aligned E_up closure -0.185 [-0.50,0.11], n=51; SENS1 closure_lr -0.42 Holm 0.039); "
                      f"this artifact R1a turnover pre-check: main {v.get('main', {}).get('verdict')}, MeSH {v.get('mesh', {}).get('verdict')}",
             gap="Rule (c) NOT MET; E underpowered (4 onsets); E_up promoted post hoc; no sealed held-out confirmation; turnover vs brokerage unresolved",
             scheduled="iter-3 direction 'RQ1 DEEPEN, TURNOVER vs BROKERAGE' (R1a-R1d on hydrated 247-concept screen; freezes held-out spec); iteration-4 sealed test"),
        dict(item="RQ2", status="partial",
             evidence="art_mbFjmo5rbbf8 concept-subfield bipartite + subfield_count/H/RS indicators; art_yjFB8Spw2w6M Gate A FAIL (0.173 < 0.5), "
                      "viability layer descriptive only (SOURCE 63 / SINK 26 / FADING 7 of 779), Gate B 0 episodes",
             gap="citation-lineage diffusion estimator closed (rule a triggered); no diffusion typology or grafting test yet",
             scheduled="iter-3 directions 'RQ2-D1 openness predicts how far a concept travels', 'RQ2-D2 grafting vs co-transfer (rule a fallback)', "
                       "'RQ2 descriptive answers (activities 4-6)'"),
        dict(item="A1 grounding", status="partial",
             evidence="art_BdBvbNuNU8E7: classifier F1 0.818 [0.772,0.859] AUC 0.888 at t_F1 (silver labels); merger B-cubed F1 0.78, pair F1 0.357/0.222; "
                      "NIL linker tau 0.95 (in-KB recall 0.40); frozen test population MAIN 156; art_eR1Z7fMlOcxs hydrated 426/426",
             gap="labels are silver (LLM-A co-produced them); human check sheet not executed; 312/366 main concepts unlinked (kept as nodes)",
             scheduled="not scheduled in iteration 3 (human check pending)"),
        dict(item="A2 two network views", status="done",
             evidence="art_mbFjmo5rbbf8: 25 yearly 3-yr co-word snapshots (~27k nodes, ~84k kept edges, Leiden AMI 0.62-0.63) + concept-subfield bipartite; "
                      "art_yWUkgWWKyq_h: MeSH snapshots (25) + subfield view",
             gap="year-to-year communities unstable; concept-discipline view built on OpenAlex topics only (ASJC habitat covers 12.1% of links)",
             scheduled="-"),
        dict(item="A3 RQ1 indicators/prediction", status="done",
             evidence="96-column concept-year indicator panel; matched event study (E/E_alt/E_up) and rolling-origin prediction (logit primary, HGB secondary); "
                      "MeSH replication + aligned block (IVW -0.41, Q 6.2)",
             gap="prediction: precursors add nothing beyond baselines; primary-label prediction single-origin pilot",
             scheduled="iter-3 RQ1 DEEPEN (prediction on hydrated screen)"),
        dict(item="A4 RQ2 diffusion", status="partial",
             evidence="art_yjFB8Spw2w6M P1 entropy decomposition (UNDETERMINED 70.4%, ORIGIN 27.6%); origin cooling onsets (33/51/83 at theta 0.6/0.7/0.8); "
                      "graft-fallback host-entry events 2,347 (2,154 with >= 5 kw)",
             gap="viability layer fails synthetic FDR (0.209 > 0.15); no cross-disciplinary diffusion velocity or community-migration analysis yet",
             scheduled="iter-3 'RQ2-D2 grafting vs co-transfer' and 'RQ2-D1 openness -> breadth'"),
        dict(item="A5 typology", status="partial",
             evidence="art_mbFjmo5rbbf8 DTW k-medoids typology: no stable solution (min Jaccard <= 0.51 at k=2..6); patterns: early bridging 76%, "
                      "incubation->expansion 0%; MeSH patterns early bridging 59%, incubation 17%",
             gap="no data-derived diffusion typology", scheduled="iter-3 'RQ2 descriptive answers' (typology with k chosen by stability)"),
        dict(item="A6 cases", status="planned", evidence="none yet (no medoid case studies produced)",
             gap="representative cases per empirically derived trajectory", scheduled="iter-3 'RQ2 descriptive answers' (medoid cases)"),
    ]
    df = pd.DataFrame(rows)
    df.to_csv(K.RES / "coverage_table.csv", index=False)
    L = ["# Coverage of RQ1, RQ2 and request activities 1-6\n", "| item | status | evidence | gap | scheduled |", "|---|---|---|---|---|"]
    for r in df.itertuples():
        L.append(f"| {r.item} | **{r.status}** | {r.evidence} | {r.gap} | {r.scheduled} |")
    L.append("\nSource: iteration-2 artifact summaries and files (art_eR1Z7fMlOcxs, art_BdBvbNuNU8E7, art_yjFB8Spw2w6M, art_mbFjmo5rbbf8, art_yWUkgWWKyq_h); "
             "iteration-3 directions from 3_invention_loop/iter_3/gen_strat/gen_strat_1; R1a verdicts from results/r1a/r1a_results.json")
    (K.RES / "coverage_table.md").write_text("\n".join(L))
    return df


@logger.catch(reraise=True)
def main() -> dict:
    K.setup_logging("part3_rules")
    K.set_ram_limit(20)
    r1a = K.load_json(K.R1A / "r1a_results.json") if (K.R1A / "r1a_results.json").exists() else None
    t1 = aligned_block()
    logger.info(f"aligned block: {len(t1)} rows; IVW agrees with file: {t1.ivw_agrees_file.tolist()}")
    ho119, ho61, info = heldout_ids()
    logger.info(f"held-out ids: {info}")
    audit = seal_audit(ho119, ho61, info)
    logger.info(f"seal audit: hits {audit['hits_exp3_exp4_total']} in {audit['files_scanned_exp3_exp4']} files -> {audit['verdict']}")
    rl = rules(audit, r1a)
    logger.info(f"rules: a={rl['a']['triggered']} b={rl['b']['pilot_only']} c={rl['c']['met']} d={rl['d']['sealed']}")
    cov = coverage(rl, r1a)
    return dict(aligned=t1, rules=rl, audit=audit, coverage=cov)


if __name__ == "__main__":
    main()
