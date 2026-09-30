"""STAGE 14: freeze the held-out confirmation spec (heldout_spec.json + .sha256 + logs/freeze.log)."""
from __future__ import annotations

import datetime as dt
import json

from loguru import logger

import models
from config import D5, E1, LOGS, RESULTS, SEED, WS, rel, sha256_file

FROZEN_CODE = ["src/config.py", "src/io_load.py", "src/features.py", "src/outcomes.py", "src/models.py", "src/ppml.py",
               "confirm_heldout.py"]


def freeze(screen_models: dict, power: dict | None) -> str:
    data_files = sorted((D5 / "hyd" / "works").glob("works_part_*.parquet")) + [
        D5 / "hyd" / "concept_work.parquet", D5 / "hyd" / "data_out.json", D5 / "p2" / "profiles.jsonl",
        D5 / "outputs" / "nativeness_coverage.json", D5 / "hyd" / "keywords_dict.json",
        D5 / "hyd" / "context" / "subfield_year_totals.json", D5 / "hyd" / "taxonomy.json",
        E1 / "results" / "test_population.json"]
    pop = json.loads((RESULTS / "main_population_hydrated.json").read_text())
    mde = None if power is None else power["MDE_irr_per_sd_power80"]
    spec = {
        "created_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "estimand": {"outcome": "Y_strict", "coefficients": ["b_A (A_cont)", "b_CT (CT)"],
                     "sample": "held-out fold, MAIN, kw5, main arm (F <= e <= 2019), complete controls"},
        "estimator": {"model": "PPML, iterated singleton/separation pruning, tol 1e-12", "x": ["A_cont", "CT"],
                      "controls": models.EVENT_CONTROLS,
                      "controls_secondary": models.EVENT_CONTROLS + models.SECONDARY_EXTRA,
                      "fe_specs": ["primary", "secondary"],
                      "fe": {"primary": "concept x e + d x e", "secondary": "concept + e + d (co-primary; fallback 3)"},
                      "offset": "log(n_entry_papers)", "cluster": "concept (CRV1, pyfixest small-sample factor)",
                      "wild_bootstrap": "Kline-Santos score, Rademacher, 999 reps"},
        "decision_rule": {"holm_family": ["b_A", "b_CT"], "alpha": 0.05,
                          "GRAFTING": "b_A > 0 and Holm p < .05 and b_CT not significantly > 0",
                          "TOOLKIT": "b_CT > 0 and Holm p < .05 and b_A n.s.", "BOTH": "both significantly > 0",
                          "NEITHER": "otherwise", "negative": "a significant negative sign is reported as such",
                          "confirmation": "the screen reading is CONFIRMED if the held-out reading in the same FE "
                                          "spec equals it; both specs are reported"},
        "secondary_outcomes": ["Y_all", "Y_lenient", "EST_bin (LPM)"],
        "robustness_to_rerun": ["STRICT population", "excess anchoring A_cont - A0_cont", "bounds A_cont_lo / A_cont_hi",
                                "nativeness permutation placebo, 500 draws, z statistic"],
        "population": {"file": "results/main_population_hydrated.json",
                       "sha256": sha256_file(RESULTS / "main_population_hydrated.json"),
                       "heldout_ids": pop["sealed_ids"]},
        "sealed_files": {k: {"path": f"sealed/{f}", "sha256": sha256_file(WS / "sealed" / f)} for k, f in
                         [("heldout_features", "heldout_features.parquet"),
                          ("graft_labels_heldout", "graft_labels_heldout.parquet"),
                          ("d3_concept_anchoring_heldout", "d3_concept_anchoring_heldout.parquet")]},
        "code_sha256": {c: sha256_file(WS / c) for c in FROZEN_CODE},
        "data_files": [{"path": rel(p), "sha256": sha256_file(p), "bytes": p.stat().st_size} for p in data_files],
        "screen_estimates": {k: {kk: screen_models[k][kk] for kk in ["n_retained", "G", "coef", "se", "p", "irr_sd",
                                                                      "p_wild"] if kk in screen_models[k]}
                             for k in ["M1", "M1_secondary"]},
        "screen_decisions": {"primary": screen_models["decision_primary"],
                             "secondary": screen_models["decision_secondary"]},
        "power": {"MDE_irr_per_sd_power80": mde, "screen_irr_per_sd": None if power is None else power["screen_irr_per_sd"],
                  "declaration": "a held-out NULL in a spec whose MDE exceeds the screen IRR (or has no MDE on the grid) "
                                 "is declared 'inconclusive (underpowered)' in advance, not a disconfirmation",
                  "adequately_powered": None if power is None else power["adequately_powered"]},
        "seed": SEED,
    }
    p = WS / "heldout_spec.json"
    p.write_text(json.dumps(spec, indent=1, default=float))
    h = sha256_file(p)
    (WS / "heldout_spec.sha256").write_text(f"{h}  heldout_spec.json\n")
    with open(LOGS / "freeze.log", "a") as f:
        f.write(f"{h} {spec['created_utc']}\n")
    logger.info(f"held-out spec frozen: {h}")
    return h
