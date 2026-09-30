"""STAGE 8: MDE simulation, synthetic dry run of the model stage, and the sha256 freeze of mesh_spec.json.

Order (no MeSH outcome exists at any point here):
  1. topic-score controls kept iff hydrated for >= 80% of MESH_MAIN events (else dropped: deviation D-M3)
  2. power_mesh.run on the actual MeSH W1 designs (R2, R1, G1 co-primary) -> power_mesh.json (MDE80, T3 recovery)
  3. dry run: models_mesh.run on SYNTHETIC outcomes (NB2 DGP of step 2, IRR/SD 1.30) -> results/dryrun_synthetic/
     (validates every model row, the placebo and the crosscheck code paths before the one look)
  4. mesh_spec.json (definitions, decision rules, deviations, MDE table, design N/G, file hashes) -> sha256 ->
     results/mesh_spec.sha256 and logs/freeze_log.txt (UTC). outcomes_mesh refuses to run without a matching hash.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from loguru import logger

import common
from common import MAIN_COPRIMARY, MAIN_NONPHYS, RESULTS, SEED, WS, dump, sha256_file

TOPIC = ["mean_topic_score", "boundary_share"]


def controls(fm: pd.DataFrame) -> tuple[list[str], list[str], dict]:
    import models as vmodels
    pc, sc = list(vmodels.EVENT_CONTROLS), list(vmodels.EVENT_CONTROLS) + list(vmodels.SECONDARY_EXTRA)
    share = float(fm.mean_topic_score.notna().mean()) if "mean_topic_score" in fm else 0.0
    keep = share >= 0.80
    if not keep:
        pc = [c for c in pc if c not in TOPIC]
        sc = [c for c in sc if c not in TOPIC]
    return pc, sc, {"topic_controls_kept": keep, "hydrated_event_share": share}


def designs(pc: list[str], sc: list[str]) -> dict:
    from models_mesh import sample
    fm = pd.read_parquet(RESULTS / "features_mesh.parquet")
    fg = pd.read_parquet(RESULTS / "features_mesh_g1.parquet")
    s = sample(fm, ["A_cont", "CT"] + sc)
    sg = sample(fg, ["A_cont", "CT"] + sc)
    return {"R2": {"s": s, "controls": sc, "controls_sim": sc, "fe": ["cfe", "efe", "dfe"]},
            "R1": {"s": s, "controls": pc, "controls_sim": sc, "fe": ["cxe", "dxe"]},
            "S1": {"s": sg, "controls": sc, "controls_sim": sc, "fe": ["cfe", "efe", "dfe"]}}


def design_counts(dsg: dict) -> dict:
    out = {}
    for k, d in dsg.items():
        s = d["s"]
        f0 = s[d["fe"][0]]
        vc = f0.value_counts()
        keep = f0.isin(vc[vc >= 2].index)
        out[k] = {"events_input": int(len(s)), "concepts_input": int(s.concept_id.nunique()),
                  "events_non_singleton_first_fe": int(keep.sum()),
                  "concepts_non_singleton_first_fe": int(s[keep].concept_id.nunique()),
                  "sd_A_cont": float(s.A_cont.std())}
    return out


def synthetic_outcomes(dsg: dict, bl: dict, irr: float = 1.30) -> dict:
    rng = np.random.default_rng(SEED + 777)
    out = {}
    for name, key in (("R2", "outcomes_mesh.parquet"), ("S1", "outcomes_mesh_g1.parquet")):
        s = dsg[name]["s"].copy()
        conc = s.concept_id.to_numpy()
        uc = {c: rng.choice(bl["u"]) for c in np.unique(conc)}
        eta = s.offset.to_numpy() + s[dsg[name]["controls_sim"]].to_numpy(float) @ bl["gamma"] + \
            np.array([uc[c] for c in conc]) + rng.choice(bl["v"], len(s))
        a = s.A_cont.to_numpy()
        mu = np.exp(np.clip(eta + np.log(irr) / a.std(ddof=1) * (a - a.mean()), -20, 12))
        y = rng.poisson(rng.gamma(bl["theta"], mu / bl["theta"]))
        s["Y_strict"] = y
        s["Y_lenient"] = y + rng.poisson(0.2 * mu)
        s["Y_all"] = s.Y_lenient + rng.poisson(0.3 * mu)
        s["EST_bin"] = (y >= 3).astype(int)
        out[key] = s
    u = pd.read_parquet(RESULTS / "features_mesh_union.parquet")
    lam = np.exp(np.log(u.n_entry_papers.astype(float)) + 0.5)
    u["Y_strict"] = rng.poisson(lam)
    u["Y_lenient"] = u.Y_strict
    u["Y_all"] = u.Y_strict
    u["EST_bin"] = (u.Y_strict >= 3).astype(int)
    out["outcomes_mesh_union.parquet"] = u
    return out


def run(power_reps: int = 200) -> dict:
    import models_mesh
    import power_mesh
    if (RESULTS / "outcomes_mesh.parquet").exists():
        raise RuntimeError("MeSH outcomes already exist: the spec cannot be (re)frozen")
    fm = pd.read_parquet(RESULTS / "features_mesh.parquet")
    pc, sc, tinfo = controls(fm)
    logger.info(f"controls: primary {pc}; secondary {sc}; {tinfo}")
    dsg = designs(pc, sc)
    dc = design_counts(dsg)
    esum = json.loads((RESULTS / "events_mesh_summary.json").read_text())
    nsum = json.loads((RESULTS / "nativeness_ledger_summary.json").read_text())
    fsum = json.loads((RESULTS / "features_mesh_summary.json").read_text())
    fb = json.loads((RESULTS / "nativeness_fallback_check.json").read_text())
    cov = fsum["tag_weighted_cov"]
    placebo = {"draws": 200, "outcome_shuffles": 40}
    spec_models = {"primary_controls": pc, "secondary_controls": sc}
    # ---- dry run on synthetic outcomes (code-path validation; nothing is read from MeSH outcomes)
    dry = RESULTS / "dryrun_synthetic"
    dry.mkdir(exist_ok=True)
    bl = power_mesh.main_baseline(sc)
    for k, df in synthetic_outcomes(dsg, bl).items():
        df.to_parquet(dry / k, index=False)
    t0 = time.time()
    dres = models_mesh.run(src=dry, out_dir=dry, spec={"models": spec_models, "placebo": placebo,
                                                        "prediction": "dry run"}, draws=8, shuffles=4)
    dry_info = {"seconds": round(time.time() - t0, 1), "R2_irr_sd_true_1.30": dres["rows"]["R2"]["row"]["A_cont"]["irr_sd"],
                "verdict_on_synthetic": dres["g4"]["verdict"], "n_rows": len(dres["rows"]),
                "crosscheck": {k: v for k, v in (dres["pyfixest_crosscheck"] or {}).items() if k.startswith("pass")}}
    logger.info(f"dry run: {dry_info}")
    t0 = time.time()
    pw = power_mesh.run(dsg, sc, reps=power_reps)
    logger.info(f"power done in {time.time() - t0:.0f}s")
    mde = pw["MDE80_irr_per_sd"]
    spec = {
        "name": "G4: MeSH replication of the D2 host-entry grafting test (iteration 4)",
        "mirrors": "iteration-3 exp_7 spec f800a0a9 (results/d2_prereg.json) definitions",
        "population": {"source": "art_HGiVAYhqO-6q (191 MeSH descriptors, metadata_fold heldout_mesh)",
                       "c_paper_set": "verified_text_match == True (union for S12)",
                       "dedup": "(concept, work_id), then (concept, normalised DOI): earliest year, min work_id",
                       "overlap_rule": "drop MeSH concepts whose casefolded surface forms collide with a main-pool phrase",
                       "overlap_dropped": esum["overlap_dropped_concepts"],
                       "origin": "dataset origin_subfield (frozen)"},
        "event_rule": {"entry": "e(c, d) = first year with a verified d-paper, d != o(c), sub = primary_topic.subfield "
                                "(no topic-score filter); keep F <= e <= 2019",
                       "partner_rule": "legacy concepts level >= 1, score >= 0.3, U keyword slugs mapped to legacy "
                                       "concepts by exact display name (level >= 1); own nodes (display name = preferred "
                                       "term / surface form / acronym, casefolded) dropped",
                       "host_coverage": "covered(d, e) = OpenAlex has_pmid share of subfield d in the entry block >= "
                                        "threshold (results/host_coverage.json)",
                       "declared": "kw5 and coverage 0.50",
                       "F6_widening": esum["widening_steps"], "chosen": esum["chosen"],
                       "underpowered_by_design": esum["underpowered_by_design"],
                       "G1": "t = first year >= e with >= 2 d-papers in [t, t+1] incl. two author-disjoint papers; t <= 2018"},
        "nativeness": {"blocks": {"2005-2009": "2000-2004", "2010-2014": "2005-2009", "2015-2019": "2010-2014"},
                       "share": "counts[d] / (total - unknown); truncated_top200 and d absent -> 0",
                       "source": nsum["source_decision"], "fallback_check": fb,
                       "calls": nsum.get("calls_this_run"), "fetch_stop": nsum.get("fetch_stop"),
                       "exact_weight_share_needed_pairs": nsum.get("exact_weight_share"),
                       "tag_weighted_coverage_MESH_MAIN": cov,
                       "tag_weighted_coverage_exact_only": fsum["tag_weighted_cov_exact_only"],
                       "coverage_cap_rule": "coverage < 0.50 -> verdict ceiling COVERAGE_LIMITED"},
        "features": {"A_cont": "tag-weighted mean pre-entry host share over profiled partners",
                     "A_cont_lo_hi": "unprofiled = 0 / 1", "CT": "share of entry-year partner tags that are origin "
                     "companions (partners on c-papers with sub == o in [e-5, e-1])",
                     "G2": "NATIVE s >= 0.30, ADJACENT 0.05 <= s < 0.30, FOREIGN s < 0.05 (shares of profiled tags)",
                     "A_placebo": "same partners' mean share toward a seeded random covered subfield != o, != d, not "
                                  "entered by c at or before e",
                     "controls": "prox_od, RD (rs_distance of iteration-2 exp_3), log_n_partner_tags, cov, demic, "
                                 "mean_topic_score, boundary_share (entry papers' hydrated topics), abstract_share, "
                                 "mom_d, log_centrality, log_W1", "topic_controls": tinfo},
        "outcomes": {"W2": "{e+k : k = 1..5} (the five years after entry)", "Pset": "authors of c-papers in [e-5, e] U their co-authors on any MeSH-corpus "
                     "work (117,253) in [e-5, e]", "primary": "Y_strict", "secondary": ["Y_lenient", "Y_all", "EST_bin"],
                     "G1": "W2 [t+2, t+6], Pset window [t-5, t+1]"},
        "models": {**spec_models, "estimator": "vendored exp_7 PPML (ppml.fit via models.fit_one), offset "
                   "log(n_entry_papers), CRV1 by concept", "R1_primary_fe": ["concept x e", "d x e"],
                   "R2_coprimary_fe": ["concept", "e", "d"], "R3": ["concept", "d x e"], "R4": ["concept x 2-yr", "d x e"],
                   "wild_bootstrap": "Kline-Santos score, Rademacher, H0 imposed; 999 (R1, R2, S1), 499 others",
                   "holm_family": ["A_cont", "CT"],
                   "thin_cell_rule": "R1 retained < 30% or G < 50 -> co-primary decisive for GRAFTING/TOOLKIT",
                   "rows": ["R1", "R2", "R3", "R4", "R2_A_only", "S1", "S1_primary", "S2", "S2_primary", "S3", "S4", "S5",
                            "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S14_health", "S14_life", "S15", "S16",
                            "S17", "S18"]},
        "placebo": placebo,
        "decision_rules": {"GRAFTING": "b_A > 0, Holm p < .05, b_CT not significantly > 0",
                           "TOOLKIT": "b_CT > 0, Holm p < .05, b_A n.s.", "BOTH": "both significantly > 0",
                           "NEITHER": "otherwise"},
        "G4_verdict_rule": "From R2 (co-primary, the hypothesis restricts the claim to across entries): REPLICATED if "
                           "IRR/SD > 1, 95% CI excludes 1, Holm p < .05 and p_wild < .05; REVERSED if significantly "
                           "< 1; else UNDERPOWERED if MDE80(R2) > 1.29, else NOT_REPLICATED -> 'claim restricted to "
                           "the physical/CS pool'. Coverage < 0.5 caps at COVERAGE_LIMITED.",
        "prediction": "IRR/SD > 1 in biomedicine, consistent with the main non-physics stratum 1.29",
        "comparison": {"main_coprimary": MAIN_COPRIMARY, "main_nonphysics": MAIN_NONPHYS,
                       "test": "z = dlog / sqrt(se1^2 + se2^2) on the per-SD log IRR; IVW pooled; Cochran Q / I2"},
        "MDE": {"MDE80_irr_per_sd": mde, "power_curve": pw["power_curve"], "reps_per_cell": power_reps,
                "T3": pw["T3_synthetic_recovery"]},
        "design_counts_W1": dc,
        "dry_run_synthetic": dry_info,
        "deviations": deviations(esum, nsum, fb, tinfo, cov),
        "hashes": {"features": {n: sha256_file(RESULTS / n) for n in ("features_mesh.parquet", "features_mesh_g1.parquet",
                                                                         "features_mesh_union.parquet")},
                   "code": {str(p.relative_to(WS)): sha256_file(p) for p in sorted(list((WS / "src").glob("*.py")) +
                                                                                 list((WS / "vendor").glob("*.py")) +
                                                                                 [WS / "method.py"])}},
        "seed": SEED,
    }
    p = RESULTS / "mesh_spec.json"
    dump(p, spec)
    spec_back = json.loads(p.read_text())
    sha = common.sha256_json(spec_back)
    (RESULTS / "mesh_spec.sha256").write_text(f"{sha}  mesh_spec.json\n")
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(common.LOGS / "freeze_log.txt", "a") as f:
        f.write(f"{ts} mesh_spec.json frozen sha256={sha}; features_mesh.parquet sha256="
                f"{spec['hashes']['features']['features_mesh.parquet']}; no MeSH outcome file exists\n")
    logger.info(f"FROZEN mesh_spec.json sha256 {sha} at {ts}")
    return {"sha256": sha, "utc": ts, "MDE80": mde}


def deviations(esum: dict, nsum: dict, fb: dict, tinfo: dict, cov: float) -> list[str]:
    ch = esum["chosen"]
    out = [
        "D-M1 (data-forced) MeSH works carry legacy concepts at score >= 0.3 only, no topic score and no dup_group: "
        "partner floor 0.3 (main 0.2), no known-sub topic-score filter, no dup_group dedup. Harmonisation rows h1-h5 "
        "apply exactly these rules to the main screen (results/harmonisation_rows.csv).",
        "D-M2 (declared) entries restricted to PubMed-covered hosts (has_pmid share of the host subfield in the entry "
        "block); non-biomedical hosts are dropped (results/entry_counts_by_host_field.csv).",
        "D-M3 topic-score controls use the entry papers' LIVE OpenAlex topics hydrated in this run (main used stored "
        f"scores); kept = {tinfo['topic_controls_kept']} (hydrated event share {tinfo['hydrated_event_share']:.3f}).",
        "D-M4 coverage group_by split by OpenAlex domain because group_by returns <= 200 of 252 subfields: 24 list "
        "calls instead of the planned 6.",
        f"D-M5 (pre-declared F6 widening, W1 counts only) the declared kw5 + coverage 0.50 design had "
        f"{esum['widening_steps'][0]['design_G_non_singleton']} non-singleton concepts (< 50); chosen step "
        f"{ch['step']}: {ch['kw']} + coverage {ch['coverage_threshold']} ({ch['events']} events, {ch['concepts']} concepts).",
        f"D-M6 the $0 background-sample fallback was {'ADMITTED' if fb['admitted'] else 'NOT admitted'} "
        f"(r = {fb['r_weighted']:.3f}, bg coverage {fb['bg_coverage_tag_weight']:.3f}); exact profiles are primary and "
        "bg shares fill only pairs without an exact profile (nat_source column; S16 = exact only).",
        f"D-M7 exact profile fetch limited by the key's remaining daily credits (not the 3,000 cap): "
        f"{nsum.get('calls_this_run')} calls, stop reason '{nsum.get('fetch_stop')}'; tag-weighted coverage of the "
        f"model sample {cov:.3f}.",
        "D-M8 power: rejection = b > 0 and two-sided CRV1 p < 0.025 (Holm level for the smaller p); the wild bootstrap "
        "is simulated only for T3 size (first 50 reps at 1.00 and 1.30, 399 draws).",
        "D-M9 the co-primary (concept + e + d) decides G4 (hypothesis restricts the claim to across entries); R1 is "
        "reported with its MDE and the thin-cell rule.",
        "D-M10 own-node matching also uses MeSH acronyms; only exact casefolded display-name matches are dropped.",
        "D-M11 co-authorship prior set limited to the MeSH corpus (117,253 works), as the main pool is within-corpus.",
        "D-M12 S12 (union c-paper set) runs without topic controls (union-only entry papers were not hydrated).",
        "D-M13 the workspace is not a git repository: the freeze is recorded by sha256 + UTC in logs/freeze_log.txt.",
    ]
    return out
