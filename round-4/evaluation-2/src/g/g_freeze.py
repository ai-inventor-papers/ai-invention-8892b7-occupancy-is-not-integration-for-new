#!/usr/bin/env python3
"""Step 1 FREEZE: sample sizes, MDE simulations (controls-only fits; no G coefficient is read) and g_spec.json.

  python g/g_freeze.py --draft      # results/g_spec_draft.json (then: g_run.py --fold screen --smoke)
  python g/g_freeze.py --finalize   # results/g_spec.json + results/g_spec.sha256 + logs/freeze_log.txt (UTC)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time

import numpy as np
import pandas as pd

import g_lib as L
import g_samples as S
from g_lib import logger

CODE = ["g/g_lib.py", "g/g_samples.py", "g/g_features.py", "g/g_run.py", "g/g_freeze.py"]
PARAMS = {"g2_native_cuts": [0.2, 0.3, 0.4], "g2_adjacent_lower_cuts": [0.02, 0.05, 0.1], "g2_headline": [0.3, 0.05],
          "pct_bootstrap_reps": 499, "placebo_host_draws": 100, "wild_reps": 999, "mde_reps": 200,
          "mde_grid": [1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40, 1.50], "seed": L.SEED}

DEFINITIONS = {
    "estimator": "vendored ppml.fit (tol 1e-12, maxit 500, iterated singleton/separation pruning); CRV1 by concept; "
                 "IRR per SD of the regressor on the retained sample with t(G-1) 95% CI; wild cluster score bootstrap "
                 "(999 Rademacher); placebo-calibrated p = 2*Phi(-|z|/SDz), SDz = SD of the iteration-3 placebo z "
                 "(results/placebo_draws.csv, per FE spec)",
    "co_primary_spec": "FE concept + e + d; x = regressor(s) + CT + controls_secondary (prox_od, RD, log_n_partner_tags, "
                       "cov, demic, mean_topic_score, boundary_share, abstract_share, mom_d, log_centrality, log_W1); "
                       "offset log(n entry papers); outcome Y_strict",
    "G1": {"universe": "main-arm host entries of results/events_all.parquet, SENSITIVITY population (MAIN flag kept), "
                       "F <= e <= 2018; entries past the horizon dropped; no exposure offsets",
           "window": "c's d-papers (primary-topic subfield d, topic_score >= 0.05) with year in {e, e+1}",
           "multi_team": ">= 2 window papers AND >= 1 pair of window papers with non-empty, disjoint author-id sets",
           "partners": "legacy-concept tags of all window papers (own node dropped; score >= 0.2, level >= 1); "
                       "kw5 = >= 5 distinct partners over the window",
           "A_cont_w": "mean pre-entry host share of the profiled window tags (block_of(e), same Nativeness object)",
           "CT_w": "share of window tags that are companions on o(c) papers in [e-5, e-1]",
           "controls": "mean_topic_score, boundary_share, abstract_share, demic, log_n_partner_tags, cov over window "
                       "papers; mom_d, prox_od, RD (pre-e basis) unchanged; log_centrality partners up to e+1; "
                       "log_W1 over [e-4, e+1]",
           "offset": "log(n window papers)", "outcome": "outcomes.compute_Y_shifted(shift=1): Y_strict over "
                     "[e+2, e+6] with seeds from c-papers in [e-5, e+1] and co-authors in [e-4, e+1]",
           "rows": ["G1-multi (co-primary FE) = HEADLINE", "G1-multi concept + d x e FE (primary controls)",
                    "G1-multi primary FE (reported; G < 50 -> underpowered)", "G1-multi MAIN only",
                    "G1-single complement (1 window paper or no disjoint-team pair)", "G1-all-window",
                    "G1-interaction A_cont x multi (+ multi main effect) on the all-window sample: ratio of IRRs "
                    "exp(b_int * SD_A) and its p", "G1-bridge: the iteration-3 row recomputed (1.558 [1.342, 1.809], "
                    "N 1,345, G 140)", "descriptive count / share of multi-team entries"],
           "reading": "G1-multi null (CI includes 1) with MDE > 1.20 -> 'inconclusive (underpowered)'; G < 30 -> "
                      "underpowered, cannot trigger 'artefact'"},
    "G2": {"sample": "co-primary sample (screen MAIN kw5, complete controls; 1,740 input events)",
           "classes": "each profiled partner tag with host share s: NATIVE s >= 0.3, ADJACENT 0.05 <= s < 0.3, "
                      "FOREIGN s < 0.05 (reference)",
           "G2a": "tag-weighted NATIVE share and ADJACENT share entered jointly in place of A_cont (+ CT + co-primary "
                  "controls); IRR per SD and per 0.1 for each; Wald test of equal per-0.1 effects (reparametrised "
                  "fit: NAT + (NAT + ADJ)); corr(NAT, ADJ); VIFs",
           "G2b": "exact decomposition A_cont = A_nat + A_adj + A_for, A_k = sum(s * 1[class k]) / n_prof; the three "
                  "entered jointly",
           "grid": "native cut {0.2, 0.3, 0.4} x adjacent lower cut {0.02, 0.05, 0.1}; all 9 cells reported",
           "reading": "grafting if NATIVE CI > 1 and NATIVE per-SD >= ADJACENT per-SD; host-vocabulary if ADJACENT "
                      "CI > 1 and ADJACENT per-SD >= NATIVE per-SD; both CIs > 1 -> the larger per-SD labels it, "
                      "flagged 'both'; neither -> 'unresolved' (joint Wald p reported)"},
    "G3": {"base": "co-primary spec (contains mean_topic_score = G3(i), reported explicitly)",
           "i_plus": "add min_topic_score; plus the restriction to entries whose entry papers all have "
                     "topic_score >= 0.9 (iteration-3 row 1.275 [1.110, 1.465])",
           "ii": "add host_topic_share (mean over entry papers of the share of their up-to-3 topics whose subfield is "
                 "d) and sec_host_share (same over topics 2-3; 0 when a paper has no secondary topic)",
           "combined": "(i+) + (ii)",
           "iii": "venue_d_share = mean over entry papers in a COVERED, citation-independent venue "
                  "(venue_habitat_asjc.json) of the venue's ASJC fractional share for d; events with >= 1 covered "
                  "entry paper; coverage-limited, excluded from the mechanism rule",
           "pct_change": "100 * (1 - b_A,with / b_A,base), base and with-control models on the IDENTICAL input sample "
                         "(pruning depends on y and FE only); CI = percentile of a 499-rep concept-cluster bootstrap",
           "iv": "outcome Y_strict_hc = Y_strict counting only W2 d-papers with topic_score >= 0.9",
           "placebo_host": "100 draws: per event d' uniform among subfields with d' != o(c), d' != d, no c-paper in d' "
                           "at years <= e, same size decile as d (subfield totals in year e, all_types); A_plac = mean "
                           "share in d' of the same profiled tags (same block); co-primary fit with A_plac in place "
                           "of A_cont (outcome still in d) and a joint A_cont + A_plac model; a second 100-draw set "
                           "stratified by proximity-to-o decile (sensitivity)",
           "placebo_pass_rule": "PASS if share of draws with p < 0.05 and IRR > 1 is <= 0.10 AND median placebo "
                                "IRR/SD < 1.10"},
    "holm_families": {"screen_G": ["G1-multi b_A", "G2a NATIVE", "G2a ADJACENT", "G3(combined) b_A"],
                      "heldout_D2": "b_A and b_CT per the frozen heldout_spec"},
    "mechanism_rule": "computed on the POOLED rows: 'artefact' if G1-multi IRR/SD < 1.10 with a CI including 1 AND "
                      "the G1 MDE <= 1.20 AND G3(combined) removes > 50% of the log-IRR; otherwise the G2a reading "
                      "('grafting' / 'host-vocabulary'; 'unresolved' if G2a is unresolved). G1 null with MDE > 1.20 -> "
                      "G1 'inconclusive (underpowered)', cannot trigger 'artefact'. Placebo-host result attached as a "
                      "qualifier. Label is 'pooled, partially pre-specified'.",
    "outputs": {"screen": "results/g_screen_rows.csv, results/g_screen_summary.json, "
                          "results/g_placebo_host_draws_screen.csv",
                "heldout": "results/g_heldout_rows.csv (SUPPLEMENTARY), results/g_heldout_summary.json",
                "pooled": "results/g_pooled_rows.csv, results/g_pooled_summary.json, results/mechanism_label.json"},
}


def draft() -> None:
    t0 = time.time()
    G = L.io_load_prepare()
    win, cop = S.load("screen")
    ws = S.window_samples(win, "screen")
    sc = S.coprimary_sample(cop, "screen")
    sizes = {}
    X2c = ["CT"] + L.CTRL2
    for k, s in list(ws.items()) + [("coprimary", sc)]:
        r0 = L.ppml.fit(s.Y_strict.to_numpy(float), s[X2c].to_numpy(float), L.models.fe_arrays(s, "secondary"),
                        s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
        sizes[k] = {"N_input": int(len(s)), "G_input": int(s.concept_id.nunique()),
                    "N_retained_controls_only": int(r0["n"]) if r0 else None, "G_retained": int(r0["G"]) if r0 else None}
    ev = pd.read_parquet(L.D2 / "results" / "events_all.parquet")
    ev = ev[(ev.arm == "main") & ev.SENSITIVITY & (ev.e <= 2018)]
    nc = ev.groupby("fold").concept_id.nunique().to_dict()
    g_scr = sizes["G1_multi"]["G_input"]
    proj = {"heldout": int(round(g_scr * nc["heldout"] / nc["screen"])),
            "pooled": int(round(g_scr * (nc["heldout"] + nc["screen"]) / nc["screen"]))}
    logger.info(f"sizes {sizes}; projected G1-multi concepts {proj}")
    mde = {}
    P = PARAMS
    kw = dict(reps=P["mde_reps"], grid=tuple(P["mde_grid"]))
    s = ws["G1_multi"]
    mde["G1_multi_screen"] = L.mde_sim(s, "Y_strict", ["A_cont"] + X2c, "A_cont", **kw)
    mde["G1_multi_heldout_projected"] = L.mde_sim(s, "Y_strict", ["A_cont"] + X2c, "A_cont", n_conc=proj["heldout"],
                                                  seed=L.SEED + 1, **kw)
    mde["G1_multi_pooled_projected"] = L.mde_sim(s, "Y_strict", ["A_cont"] + X2c, "A_cont", n_conc=proj["pooled"],
                                                 seed=L.SEED + 2, **kw)
    logger.info(f"G1 MDE done ({time.time() - t0:.0f}s): " + str({k: v["MDE_irr_sd_power80"] for k, v in mde.items()}))
    import placebo as PL
    arr = PL.build_arrays(G, sc)
    sh = L.g2_shares(arr, *P["g2_headline"])
    s2 = sc.copy()
    for c in sh.columns:
        s2[c] = sh[c].to_numpy()
    for tgt in ("NAT", "ADJ"):
        mde[f"G2a_{tgt}_screen"] = L.mde_sim(s2, "Y_strict", ["NAT", "ADJ"] + X2c, tgt, mu0_x=X2c, seed=L.SEED + 3, **kw)
    mde["G3_combined_A_screen"] = L.mde_sim(
        S.refac(sc.dropna(subset=["min_topic_score", "host_topic_share", "sec_host_share"])), "Y_strict",
        ["A_cont"] + X2c + ["min_topic_score", "host_topic_share", "sec_host_share"], "A_cont",
        mu0_x=X2c + ["min_topic_score", "host_topic_share", "sec_host_share"], seed=L.SEED + 4, **kw)
    logger.info(f"MDE done ({time.time() - t0:.0f}s): " + str({k: v["MDE_irr_sd_power80"] for k, v in mde.items()}))
    spec = {"name": "iteration-4 G1-G3 discriminating tests for the D2 host-entry result",
            "created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "heldout_spec_sha256": (L.D2 / "heldout_spec.sha256").read_text().split()[0],
            "definitions": DEFINITIONS, "parameters": PARAMS, "sample_sizes_screen": sizes,
            "concepts_by_fold_sensitivity_e_le_2018": nc, "projected_G1_multi_concepts": proj, "mde": mde,
            "mde_note": "NB2 simulation; mu0 from the controls-only co-primary fit (no target term); concepts "
                        "resampled to the stated count; power 0.8 at one-sided b > 0 and two-sided p < 0.025; "
                        "held-out/pooled counts projected from W1 concept counts (G1 window data of held-out concepts "
                        "is sealed until the opening)",
            "code_sha256_at_freeze": {rel: L.sha256_file(L.EVAL / rel) for rel in CODE}}
    (L.RES / "g_spec_draft.json").write_text(json.dumps(spec, indent=1, default=float))
    logger.info(f"draft spec written ({time.time() - t0:.0f}s)")


def finalize() -> None:
    spec = json.loads((L.RES / "g_spec_draft.json").read_text())
    spec["code_sha256_at_freeze"] = {rel: L.sha256_file(L.EVAL / rel) for rel in CODE}
    spec["frozen_utc"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L.G_SPEC.write_text(json.dumps(spec, indent=1, default=float))
    h = L.sha256_file(L.G_SPEC)
    L.G_SHA.write_text(f"{h}  g_spec.json\n")
    with open(L.LOGS / "freeze_log.txt", "a") as f:
        f.write(f"{spec['frozen_utc']} g_spec.json sha256 {h} (before any G coefficient and before the held-out "
                f"opening)\n")
    logger.info(f"FROZEN g_spec.json {h}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args()
    L.setup_logging("g_freeze")
    if a.draft:
        draft()
    if a.finalize:
        finalize()
