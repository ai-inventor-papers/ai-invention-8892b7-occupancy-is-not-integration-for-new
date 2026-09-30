#!/usr/bin/env python3
"""STAGE 10: freeze the held-out test (sealed/heldout_spec.json + sha256 hashlog).

The spec holds: population file + sha256, the sha256 of the held-out id list (ids only, no data), estimands E1-E5 with
decision rules written verbatim, the screen reference values each rule compares against, and sha256 of every code file
and frozen artefact (scaling, medoids, pct_alt reference arrays, pattern thresholds). Run LAST: any later code edit
changes a hash and makes confirm_heldout.py refuse.
"""
from __future__ import annotations

import json

import pandas as pd
from loguru import logger

from common import RES, ROOT, SEALED, TYP, WORK, setup_logging, sha256_file, sha256_json

RULES = {
    "E1": "Assign each held-out MAIN concept to the nearest frozen medoid (typology/medoids.json) under the frozen channel "
          "scaling (mean/sd), the frozen missing-value rule and normalised multivariate DTW (Sakoe-Chiba radius 3, "
          "dtw/sqrt(path length)). Report cluster shares with Wilson 95% CIs. Descriptive; success = every cluster share's "
          "Wilson CI overlaps the screen share's Wilson CI.",
    "E2": "Replicate the validation: Kruskal-Wallis epsilon^2 of V1 (newcomer share), V2 (pct_alt gain F+3->F+8) and V3 "
          "(communities touched, seed 0) across assigned clusters. SUCCESS = the rank order of cluster medians equals the "
          "screen order for >= 2 of the 3 V's AND KW p < 0.05 for >= 1 of them.",
    "E3": "Lead-lag share expansion_first (primary definitions, from_start excluded) with a 2,000-draw concept bootstrap CI. "
          "SUCCESS = the held-out CI overlaps the screen CI AND the held-out point estimate lies on the same side of the "
          "screen year-shuffle null mean as the screen estimate.",
    "E4": "Role shares by age (pre-declared rules, robust rows) and the entry-hazard logit ORs (same model, same covariates, "
          "robust lagged roles, STAYER reference). Descriptive; report each OR with 95% CI next to the screen OR; "
          "agreement = same sign of log-OR for every role level estimated in both.",
    "E5": "Pattern frequencies (incubation-then-expansion, gradual centralisation, early bridging, aligned early bridging) "
          "with frozen screen thresholds, bootstrap CIs; agreement = CI overlaps the screen CI.",
}


def screen_reference() -> dict:
    typ = json.loads((RES / "typology.json").read_text())
    val = json.loads((RES / "validation.json").read_text())
    ll = json.loads((RES / "leadlag.json").read_text())
    roles = json.loads((RES / "roles.json").read_text())
    pat = pd.read_csv(RES / "patterns.csv")
    pat = pat[(pat.population == "screen_MAIN") & (pat.subset == "all") & (pat.threshold_version == "recomputed_hydrated")]
    asg = pd.read_csv(TYP / "assignments.csv")
    n = len(asg)
    return dict(
        E1_cluster_shares={k: dict(n=int(v), share=v / n) for k, v in asg.cluster_name.value_counts().items()},
        E1_k=typ["k_selected"],
        E2={v: dict(eps2=val["results"][v]["3ch"]["eps2"], kw_p=val["results"][v]["3ch"]["kw_p"],
                    median_rank_order_by_cluster_id=val["results"][v]["3ch"]["median_rank_order"])
            for v in ("V1_newcomer_share", "V2_pct_alt_gain", "V3_comm_touched")},
        E3=dict(share=ll["primary"]["share_expansion_first"], ci=ll["primary"]["share_expansion_first_ci"],
                n_both=ll["primary"]["n_both_onsets"], null_mean=ll["null"]["null_mean"]),
        E4=dict(robust_shares=roles["predeclared"]["robust_shares"],
                entry_ORs=roles["predeclared"]["entry_hazard"]["primary_logit_robust"]["terms"]),
        E5={r.pattern: dict(freq=r.freq, ci=[r.ci_lo, r.ci_hi], n=r.n) for r in pat.itertuples()},
    )


def main() -> None:
    setup_logging("freeze")
    sealed = json.loads((WORK / "sealed_ids.json").read_text())
    code = {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(list((ROOT / "vendor").glob("*.py")) +
                                                                     list((ROOT / "src").glob("*.py")) +
                                                                     [ROOT / "method.py", ROOT / "confirm_heldout.py"])}
    frozen = {str(p.relative_to(ROOT)): sha256_file(p) for p in [TYP / "medoids.json", TYP / "scaling.json",
                                                                SEALED / "pct_alt_reference.npz", RES / "patterns.json",
                                                                RES / "roles_spec.json", RES / "main_population_hydrated.json"]}
    spec = dict(
        title="RQ2 diffusion typology / roles / lead-lag: one-time held-out confirmation (iteration 4)",
        population=dict(file="results/main_population_hydrated.json", sha256=frozen["results/main_population_hydrated.json"],
                        heldout_fold="heldout_concept (DS5 metadata_fold, sealed by iteration 2)", heldout_rule="MAIN",
                        n_heldout_ids=len(sealed), heldout_ids_sha256=sha256_json(sorted(sealed))),
        estimands=RULES, screen_reference=screen_reference(), code_sha256=code, frozen_artifacts_sha256=frozen,
        procedure="python confirm_heldout.py --expected-sha <sha> --open-heldout  (runs prep -> attach -> indicators -> labels -> "
                  "leiden_seeds -> typology(assign) -> roles -> leadlag -> patterns -> validation with AII_HELDOUT_OPEN=1 into "
                  "heldout_run/, then evaluates the rules; refuses a second opening)",
    )
    txt = json.dumps(spec, sort_keys=True, indent=1, default=str)
    (SEALED / "heldout_spec.json").write_text(txt)
    h = sha256_json(json.loads(txt))
    with (RES / "heldout_spec_hashlog.jsonl").open("a") as f:
        f.write(json.dumps(dict(sha256=h, utc=pd.Timestamp.utcnow().isoformat())) + "\n")
    (SEALED / "heldout_spec.sha256").write_text(h)
    logger.info(f"held-out spec frozen: sha256={h}")


if __name__ == "__main__":
    main()
