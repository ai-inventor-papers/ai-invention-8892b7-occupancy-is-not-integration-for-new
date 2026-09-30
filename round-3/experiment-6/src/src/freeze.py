"""Step 9b: freeze the held-out confirmation spec (sha256-hashed) for iteration 4."""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from loguru import logger

import common as K
from common import OUT, SEALED, WS

import stats_core as S

HDIR = OUT / "heldout"
BOOT_SEED = 20261001


def code_hashes() -> dict:
    files = sorted([*(WS / "vendor").glob("*.py"), WS / "vendor" / "spec.json", *(WS / "src").glob("*.py"),
                    WS / "confirm_heldout.py", WS / "method.py"])
    return {str(p.relative_to(WS)): K.sha256_file(p) for p in files}


def run() -> None:
    HDIR.mkdir(parents=True, exist_ok=True)
    verdict = json.loads((OUT / "d1" / "verdict.json").read_text())
    r1a = json.loads((OUT / "openness" / "r1a_fit.json").read_text())
    mde = json.loads((OUT / "power" / "mde.json").read_text()) if (OUT / "power" / "mde.json").exists() else None
    fill = json.loads((OUT / "d1" / "features_fill_medians.json").read_text())
    sealed_ids = json.loads((OUT / "population" / "sealed_ids.json").read_text())
    met = verdict["outcomes_meeting_rule"]
    carried = met if met else []
    spec = dict(
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), iteration=3,
        artifact="RQ2-D1 screen test (openness -> W2 disciplinary breadth gain)",
        screen_verdict=verdict["verdict"],
        population_files={
            "results/population/main_population_hydrated.json": K.sha256_file(OUT / "population" / "main_population_hydrated.json"),
            "sealed/openness_ct_heldout.parquet": K.sha256_file(SEALED / "openness_ct_heldout.parquet"),
            "sealed/features_ct_heldout.parquet": K.sha256_file(SEALED / "features_ct_heldout.parquet"),
            "results/d1/panel_ct.parquet (screen training rows for the transfer test)": K.sha256_file(OUT / "d1" / "panel_ct.parquet")},
        sealed_ids_sha256=hashlib.sha256(json.dumps(sorted(sealed_ids)).encode()).hexdigest(), n_sealed_ids=len(sealed_ids),
        unit_rows="held-out MAIN concepts (fold heldout_concept, in_MAIN), t in [F+3, F+8], t <= 2015; W1 = [t-5, t], W2 = [t+1, t+5]",
        estimands=(dict(carried_outcomes=carried,
                        per_outcome={y: f"coefficient of closure_res_z in OLS {y} ~ BASE + closure_res_z on held-out MAIN rows"
                                     for y in carried})
                   if carried else dict(carried_outcomes=[], note="D1 not supported on screen; held-out estimates are "
                                                                  "descriptive only, no confirmation claim")),
        descriptive_outcomes=["Y1r", "Y2", "log1p_Y3"], openness_measures=["closure_res_z", "closure_res_imp_z"],
        estimator=dict(formula="Y ~ 1 + openness_z + " + " + ".join(S.NUM_BASE) + " + C(origin_group) + C(F_band) + C(route) + C(t)",
                       BASE=S.NUM_BASE, categorical=S.CATS, dummy_levels="frozen screen levels (unknown held-out levels -> reference level)",
                       closure_res="closure - X b with the frozen screen R1a coefficients (results/openness/r1a_fit.json)",
                       r1a_coefficients=dict(primary=r1a["primary"]["beta"], imputed=r1a["imputed_variant"]["beta"],
                                             imputed_beta_sim_median=r1a["imputed_variant"].get("beta_sim_median")),
                       z_scaling=r1a["z_scaling"], fill_medians=fill, complete_case=True),
        inference=dict(cluster_bootstrap_reps=2000, seed=BOOT_SEED, ci="percentile 95%", cluster="concept"),
        decision_rule=("one-sided: coef(openness_z) < 0 with the 95% cluster-bootstrap CI excluding 0 AND Holm across the carried "
                       "outcomes (p_boot, two-sided bootstrap p) < 0.05; secondary: transfer delta-R2 = FULL vs BASE fitted "
                       "on the SCREEN MAIN rows, evaluated on the held-out rows, concept-bootstrap (2000) CI lower bound > 0. "
                       "With co-primary closure_res_imp (F3), both measures must meet the rule."),
        mde=({ov: {y: dict(mde_heldout_sd=v["mde_heldout_sd"], transfer_mde_sd=v["transfer_mde_sd"])
                   for y, v in per["outcomes"].items()} for ov, per in mde["per_measure"].items()} if mde else None),
        code_sha256=code_hashes(),
        no_re_screen_clause=("Iteration 4 runs confirm_heldout.py once, unchanged. No re-screening, no new outcomes, no new "
                             "covariates and no re-tuning on held-out data; any deviation is reported as exploratory."),
    )
    txt = json.dumps(spec, indent=1, default=K._json_default)
    p = HDIR / "heldout_spec.json"
    p.write_text(txt)
    h = K.sha256_file(p)
    (HDIR / "heldout_spec.sha256").write_text(h + "\n")
    with open(K.LOGS / "freeze_log.txt", "a") as f:
        f.write(f"{spec['created_utc']}\theldout_spec.json\t{h}\n")
    logger.info(f"held-out spec frozen: sha256 {h}; carried outcomes {carried or 'none (descriptive only)'}")
