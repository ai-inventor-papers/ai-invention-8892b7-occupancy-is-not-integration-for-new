#!/usr/bin/env python3
"""S4 FREEZE: write eval_spec.json (R1 kill mapping, reading test, SMD covariates, descriptive IV synthesis) and
d3_spec.json (D3 exposure, outcome, timing level, covariates, seeds, B, permutations, direction, decision rule), then
append their sha256 to logs/eval_freeze_log.jsonl. Refuses to overwrite an existing frozen spec (one freeze only).
The only data value embedded is the SCREEN MAIN kw5 median of A_cont (threshold for the secondary outcome Y2)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src_eval"))
import d3core as D  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "s4_freeze.log", rotation="30 MB", level="DEBUG")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def eval_spec(r1_spec_sha: str, d1_spec_sha: str, power: dict) -> dict:
    return dict(
        title="Iteration-4 evaluation spec: one-look R1 held-out readout, D1 descriptive run (kill mapping + reading test)",
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        r1_heldout_spec_sha256=r1_spec_sha, d1_heldout_spec_sha256=d1_spec_sha,
        r1_run=dict(
            how=("deps_run/exp5/confirm_heldout.py byte-identical (hash-checked); invoked once through r1_open_once.py, "
                 "which imports it by file path, wraps run_fold with a recorder storing (feat, matches) of every call "
                 "(LAST call kept = fallback call if the fallback triggers) and calls confirm(spec, expected_sha) exactly once"),
            refusal_rule="exit 2 / REFUSED before the sealed load is not a look; a crash after the sealed load and before "
                         "verdict_heldout.json is written is logged in deviations.md and rerun once with identical code",
            holm_family=["closure_resT", "closure_persist", "constraint", "closure"],
            no_new_rows=True),
        R1_7_kill_mapping=dict(
            R1_ALIVE="tests['closure'] (pooled panel, Holm one-sided p < 0.05, negative direction) == CONFIRMED",
            R1_TURNOVER_PROOF="R1_ALIVE and tests['closure_resT'] == CONFIRMED",
            R1_PERSISTENT="R1_ALIVE and tests['closure_persist'] == CONFIRMED",
            R1_DEAD="otherwise; RQ1 sentence becomes 'structural precursors are volume/churn correlates'",
            REVERSED="held-out pooled coef(closure) > 0 (reported as REVERSED, also counts as R1_DEAD)",
            status_string="R1_DEAD | R1_ALIVE | R1_ALIVE+TURNOVER_PROOF | R1_ALIVE+PERSISTENT | R1_ALIVE+TURNOVER_PROOF+PERSISTENT"),
        R1_8_reading_test=dict(
            name="focused in the wide ego network, open at the top",
            inputs="held-out event-study S and two-sided 95% bootstrap CI (constraint, xc_excess); pooled-panel closure decision",
            SUPPORTED="closure pooled coef < 0 and CONFIRMED AND S(constraint) > 0 AND S(xc_excess) > 0 AND at least one of "
                      "CI(constraint), CI(xc_excess) excludes 0 on the positive side",
            SIGN_CONSISTENT="closure pooled coef < 0 AND S(constraint) > 0 AND S(xc_excess) > 0, but neither CI excludes 0",
            CONTRADICTED="S(constraint) < 0 with CI excluding 0 (Burt brokerage) OR S(xc_excess) < 0 with CI excluding 0",
            NOT_SUPPORTED="otherwise",
            precedence="CONTRADICTED is checked first, then SUPPORTED, SIGN_CONSISTENT, NOT_SUPPORTED",
            status="secondary, disclosed; positive constraint direction contradicts the spec's pre-registered negative "
                   "direction; never overrides the Holm decisions",
            projected_power={k: power["R1"]["rows"][k]["power_es"] for k in ("constraint", "xc_excess")},
            expectation="SIGN-CONSISTENT is the likely ceiling (power about 0.5); SIGN-CONSISTENT is read as 'not contradicted'"),
        R1_6_balance=dict(
            covariates=["log_vol3", "age", "H", "subfield_count", "closure@k=-5"],
            at_k=[0, -3],
            weights="each treated weight 1; its matched controls weight 1/n_controls each (1:3 with replacement)",
            pooled_sd="SD of the covariate over SCREEN MAIN concept-years (fold screen, year <= 2015) of "
                      "deps_run/exp5/results/indicators/concept_year_indicators_hydrated.parquet (fixed)",
            flag_abs_smd=0.25,
            also="vendored analysis_event.balance (before/after SMD, own pooled SD) reported for comparability with the screen"),
        R1_9_iv_synthesis=dict(label="DESCRIPTIVE, NOT A DECISION", se_rule="SE = (ci_hi - ci_lo) / 3.92",
                               stats=["IV pooled S", "SE", "95% CI", "Cochran Q", "I^2"],
                               rows=["closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "wmz",
                                     "cdeg_diag", "effsize"]),
        R1_10_disclosures=["E_up promoted post hoc in iteration 2 (primary E gave 4 onsets)",
                           "screen match rate 26/68 = 38%", "held-out fallback to screen never controls if n_matched < 20",
                           "recorder wrapper used (import instead of CLI)", "any refused/crashed attempt with UTC time"],
        D1=dict(run="AII_OPEN_HELDOUT=iter4 .venv/bin/python confirm_heldout.py in deps_run/exp6, once",
                report="per openness x outcome: coef, CI, p_boot, n_rows, n_concepts, transfer dR2 + CI; frozen MDE; "
                       "descriptive sign agreement with screen coefficients; status string verbatim; no Holm, no verdict",
                screen_coefs_closure_res={"Y1r": 0.019, "Y2": 0.007, "log1p_Y3": -0.065}),
        pre_open_power_file="results/pre_open_power.json",
    )


def d3_spec(power: dict, median_A: float, n_med: int) -> dict:
    lv = power["D3"]["chosen_level"]
    a0, a1, lag, src = D.LADDER[lv]
    return dict(
        title="D3: do less-closed concepts graft more later? (concept-level, one mechanism at two scales)",
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        unit="concept (MAIN, main arm; population = deps_run/exp5/work/population.parquet)",
        folds=["screen", "heldout"],
        timing_level=lv, timing_level_rule=power["D3"]["rule"], timing_counts=power["D3"]["levels"],
        exposure=dict(column="closure", source="exp_6 results/openness/openness_ct.parquet (screen) / sealed/openness_ct_heldout.parquet (held-out)",
                      window=f"concept-years with t - F in [{a0}, {a1}] and t <= 2015; finite values; X_c = mean",
                      min_years=1),
        outcome=dict(primary="Y_c = unweighted mean A_cont over MAIN-arm host entry events with kw5 (>= 5 partners) and "
                             f"e >= F + {lag}" if src == "events" else "exported mean_A_cont",
                     source="exp_7 results/features_screen.parquet / sealed/heldout_features.parquet (pre-entry partner host share)",
                     F_source="population.parquet F", min_events=1,
                     Y2=f"share of qualifying events with A_cont > {median_A:.10f} (SCREEN MAIN main-arm kw5 event median, n={n_med}, frozen)",
                     Y2_threshold=median_A,
                     Y3="mean_A_cont of d3_concept_anchoring(_heldout).parquet as exported (all entries; timing overlap disclosed)"),
        covariates=dict(list=["rank(log early volume)", "origin-field group dummies", "log number of qualifying events"],
                        early_volume="log1p(mean yearly all-type c-papers over F..F+5) from dataset_5 concept_work x works publication_year",
                        origin_groups="Physics&Astronomy (F31), Computer Science (F17), Materials/Chem/Eng (F25, F16, F22, F15), "
                                      "Mathematics (F26), Other; groups with < 5 concepts in a fold merge into Other; reference = largest group",
                        rank_transformed=["log_vol_early"]),
        statistic=dict(raw="Spearman rho(X, Y) (average ranks)",
                       primary="partial Spearman: average ranks of X and Y, OLS-residualised on [1, covariates], Pearson r of residuals",
                       direction="one-sided, predicted rho < 0",
                       bootstrap=dict(B=2000, seed=20261001, type="percentile concept bootstrap (BCa as sensitivity); ranks and residualisation recomputed per draw"),
                       permutation=dict(n=10000, seed=20261002, scheme="Freedman-Lane: permute reduced-model X-residuals",
                                        p="(1 + #{rho_perm <= rho_obs}) / 10001"),
                       mde="rho_MDE = tanh((1.645 + 0.842) * sqrt(1.06 / (n - 3 - k))), k = covariate columns",
                       projected=power["D3"]["projected"]),
        sensitivities=dict(
            S1="X = mean closure_res (frozen exp_6 R1a residualisation) over the same window; complete case",
            S2="screen only: for concepts with an E_up onset (exp_5 labels_screen onset_E_up), X restricted to t < onset",
            S3="adds rank(H_W1 at the last finite year of the exposure window) as covariate",
            S4="Y = mean A_cont_ex over the same events",
            S5="excluding Physics&Astronomy-origin concepts",
            S6="requires >= 2 qualifying events",
            S7="EXPLORATORY: X = mean constraint; X = mean xcomm_exc (R1-8 reading at concept level)",
            S8="fold-pooled partial Spearman with a fold dummy (descriptive)",
            secondary_outcomes="Y2 and Y3 with the primary covariates",
            note="sensitivities are reported, never decision-making; S-level bootstrap B = 2000, permutations 10000"),
        decision=dict(
            KEPT="screen partial rho < 0 with permutation p < 0.05 AND held-out partial rho < 0 with p < 0.05",
            SCREEN_ONLY="screen passes and held-out rho < 0 with p >= 0.05 (report as a lead; quote held-out MDE)",
            NULL="screen fails (sentence dropped; two separate findings)",
            REVERSED="either fold partial rho > 0 with 95% percentile CI excluding 0 (reported as tension; checked first)",
            HELDOUT_OPPOSITE_SIGN="screen passes and held-out rho >= 0 with CI including 0 -> reported as SCREEN_ONLY (sign not replicated)",
            sentence="'one mechanism at two scales' kept only if KEPT"),
    )


@logger.catch(reraise=True)
def main() -> None:
    es_p, ds_p = WS / "eval_spec.json", WS / "d3_spec.json"
    if es_p.exists() or ds_p.exists():
        raise SystemExit("REFUSED: a frozen spec already exists; specs are frozen once")
    integ = json.loads((WS / "results" / "integrity_report.json").read_text())
    if not integ["all_ok"]:
        raise SystemExit("REFUSED: integrity report not clean")
    power = json.loads((WS / "results" / "pre_open_power.json").read_text())
    pop = D.population()
    P = pop[(pop.fold == "screen") & pop.MAIN]
    ev = D.events("screen")
    ev = ev[ev.concept_id.isin(set(P.concept_id)) & ev.kw5.astype(bool) & np.isfinite(ev.A_cont)]
    median_A, n_med = float(np.median(ev.A_cont)), int(len(ev))
    es_p.write_text(json.dumps(eval_spec(integ["parts"]["R1_exp5"]["spec_sha256"], integ["parts"]["D1_exp6"]["spec_sha256"], power), indent=1))
    ds_p.write_text(json.dumps(d3_spec(power, median_A, n_med), indent=1))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with (WS / "logs" / "eval_freeze_log.jsonl").open("a") as f:
        for p in (es_p, ds_p):
            rec = dict(file=p.name, sha256=sha(p), utc_iso=now, note="frozen before any held-out fold is opened and before any D3 association")
            f.write(json.dumps(rec) + "\n")
            logger.info(f"frozen {p.name} sha256 {rec['sha256']}")


if __name__ == "__main__":
    main()
