#!/usr/bin/env python3
"""STEP 0: freeze every rule BEFORE any statistic is computed. Writes prereg/prereg_freeze.json + sha256.

The prereg file is never edited after this; deviations go to prereg/deviations.md.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from loguru import logger

from common import SEED, STRAT1, WS, setup_logging

PREREG = WS / "prereg" / "prereg_freeze.json"


def selection_rule_verbatim() -> dict:
    try:
        d = json.loads(STRAT1.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"strategy file unreadable: {e}")
        return {"source": "verbatim source not found", "text": (
            "SELECTION RULE (paraphrase from plan): delta-AUC over BASE, concept-bootstrap 1,000 reps, 95% CI lower > 0, "
            "point gain >= 0.01, sign matches; the largest lower bound wins; joint carry-forward if the CI overlaps and "
            "the gain is within 0.005.")}
    hits = []

    def walk(x, p=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{p}/{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")
        elif isinstance(x, str) and "SELECTION RULE" in x:
            hits.append((p, x))
    walk(d)
    if not hits:
        return {"source": "verbatim source not found", "text": None}
    return {"source": "iter_1/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json" + hits[0][0], "text": hits[0][1]}


def build() -> dict:
    return {
        "title": "Citation gate, viability labels and power check (iteration 2, gen_art_experiment_2)",
        "frozen_before_any_statistic": True,
        "data": "iter_1 gen_art_dataset_1 (art_94GEMUsgAmgK): 184 main + 22 reference concepts; no API / LLM calls",
        "seed": SEED,
        "focal_rule": {
            "units": "main-arm concept c, focal year t with 3 <= t-F <= 8 and t <= 2019; age = t-F",
            "fold": "D1 metadata_fold (sha1 split): screen = screen partition, heldout_concept = held-out",
            "cross_fold_comparisons": "age-matched (strata = age)",
            "secondary_subset": "focal years 2016-2018 flagged as out-of-time subset",
        },
        "windows": {"W1": "[t-5,t]", "parent_cohort": "[t-5,t-3]", "children": "[t-4,t]", "W2": "[t+1,t+5] never touched"},
        "origin": "o(c) = D1 origin_subfield (modal subfield of c-papers in F..F+2); audit recomputes, logs mismatch, never replaces",
        "dedup": "within (concept, dup_group) keep one work: earliest year, then max n_refs, then min work_id; undup'ed works own group",
        "canonical": {
            "main": "all c-papers with year == F plus top-5 c-papers by 2026 cited_by_count (ties -> lower work_id), after dedup",
            "reference": "top-5 by cited_by_count only",
            "routing": "canonical papers are 'background': never parents",
            "sensitivity_CANON_W1": "F-year papers + top-5 by citations received from c-papers with year <= t (per focal year)",
        },
        "parentage": ("P(k) = {p in refs(k) cap cset(c): p not canonical, p != k, year(p) <= year(k)}; "
                      "w_kp = exp(-(year_k-year_p)/2) / sum over P(k); traced(k) = |P(k)|>0; children whose only cset "
                      "parents are canonical = background-only (counted separately)"),
        "edge_estimators": {
            "scope": "edge (c,d,t), d != o(c), using only papers with year <= t",
            "Pd": "non-canonical d-papers with year in [t-5,t-3]", "Kd": "d-papers with year in [t-4,t]",
            "a_k": "sum_{p in Pd} w_kp", "imp_k": "sum_{p: sub(p) != d} w_kp", "tr_k": "sum_p w_kp (0 or 1)",
            "rho": "sum_k a_k / |Pd|", "m": "sum imp_k / sum tr_k", "untraced": "#{tr_k = 0}/|Kd|",
            "rho_tilde": "rho / rho0(d,t)",
        },
        "eligibility": {
            "eligible": ">= 10 W1 d-papers (years t-5..t)",
            "tested": "eligible AND |Kd| >= n_min AND |Pd| >= 1 AND sum tr > 0",
            "undetermined_reason_codes": ["below_nmin", "no_cohort_parents", "no_traced_children"],
        },
        "n_min_rule": ("bin eligible edges with |Kd| >= 5 into [5,10),[10,15),[15,20),[20,30),[30,inf); median 90% CI width "
                       "of log rho per bin (= width of log rho~); n_min_rule = smallest bin lower bound whose median width "
                       "<= 0.7 AND all higher bins <= 0.7 (if none: 30, flagged); main n_min = max(10, n_min_rule); "
                       "curves at 5/10/15/20/30; continuity: log((sum a*+0.5)/(sum b*+0.5)) only for reps with sum a* = 0"),
        "bootstrap": ("paper-cluster, B = 1000; units = papers in Pd union Kd with (a_i, b_i = 1[i in Pd], imp_i, tr_i); "
                      "counts C ~ Multinomial(n, 1/n) (implemented as bincount of B x n uniform index draws; identical "
                      "distribution); rho* = C@a / C@b (NaN if C@b = 0, NaN share reported, NaN = fail to reject); "
                      "m* = C@imp / C@tr; 90% percentile CIs; p_greater = (1 + #{rho~* <= 1 or NaN})/(B+1); "
                      "p_less = (1 + #{rho~* >= 1 or NaN})/(B+1); per-edge seed = (SEED, sha1(concept), t, d)"),
        "states": ("within each (c,t) family of tested edges: BH q = 0.10 separately on p_greater and p_less "
                   "(statsmodels fdr_bh). SOURCE = greater rejected; reject_low = less rejected; SINK = reject_low AND "
                   "lower 90% CI of m > 0.5; FADING = reject_low AND NOT (m_lo > 0.5); UNDETERMINED otherwise; the "
                   "origin edge = ORIGIN (never tested)"),
        "benchmark": {
            "stationary_cell": ("(r,d,t): r reference-arm concept, >= 30 W1 d-papers, |slope| < 0.05/yr where slope = OLS "
                                "slope of log(1e4*n_{r,d,y}/T_{d,y} + 1e-3) on y in [t-5,t], T = subfield_year_totals "
                                "'all_types'"),
            "rho_r": "same estimator code; origin not excluded; canonical = top-5 only",
            "hierarchy": ["L1: >= 3 stationary refs in (d,t) -> median", "L2: >= 3 stationary cells with field(d') = field(d) at t -> median",
                          "L3: same over t-2..t+2", "L4: global median at t (>= 3 cells)", "L5: global median over all t",
                          "skip a level if its median <= 0"],
            "sensitivities": ["EB: log rho0 at L1 shrunk toward the field mean of log rho_r with method-of-moments tau^2 "
                              "(cells without stationary refs keep the hierarchy)",
                              "PAST_L3: L3 over t-4..t (no future reference cells)",
                              "REF_BOOT: in each bootstrap rep, reference concepts resampled with replacement and rho0 "
                              "recomputed through the hierarchy"],
            "fallback_F2": ("if no stationary cell at all: (a) L4/L5 global over any stationary cells; (b) reference "
                            "concepts' modal subfield cells with >= 30 W1 papers regardless of slope; (c) main-arm "
                            "concepts with age >= 10 meeting the stationarity rule; every rho~ flagged benchmark-relaxed"),
        },
        "gate_A": {
            "lenient_loader_check": ("re-implementation of iter-1 assemble.py lines 360-377: no dedup; parents = refs in cset "
                                     "with year < child year; traced_excl_F; host = subfield != origin_subfield; must "
                                     "reproduce main host 0.5518 (n = 41,861), by year 2010-2014 = 0.3174/0.3613/0.3476/"
                                     "0.4130/0.5171, reference traced_any 0.5311 (n = 92,969) to 3 decimals"),
            "primary_statistic": ("within-host share per eligible edge (c,d,t): among Kd, share of children citing >= 1 "
                                  "non-canonical c-parent with subfield == d and year in [t-5, year_k]; denominator all "
                                  "of Kd; secondary denominator Kd with n_refs > 0"),
            "verdict_rule": ("over main-arm edge-years with |Kd| >= 10 (W1 d-children), Gate A PASSES iff more than 50% of "
                             "those host edge-years have within-host share >= 0.40; applied ONCE on the pooled set; "
                             "per-year and per-fold verdicts are descriptive only"),
            "on_fail": ("'FAIL -> graft fallback supplies H1/H2 labels in iteration 3'; steps 3-5 continue labelled "
                        "DESCRIPTIVE ONLY; focal years, windows and canonical rule are not changed after the table is seen"),
            "graft_fallback_units": ("host entry events (c, d != o(c), e), e = first year with >= 1 d-paper, e <= 2019; "
                                     "counted if year-e d-papers carry >= 5 distinct keyword_idx"),
        },
        "cooling_rule": ("O*(c,y) = #origin c-papers in y citing no non-origin c-paper x 1e4 / T_{o(c),y} (all_types), "
                         "y = F..2024; M_y = (O*_y + O*_{y-1})/2; onset = first y >= F+3 with M_y <= theta * "
                         "max(O*_{y-3..y-1}) AND O*_{y-1} >= O*_{y-2} >= O*_{y-3}; theta in {0.6, 0.7 main, 0.8}"),
        "P1": ("per (c,t): p_d = W1 d-paper share over all subfields (origin included); H = -sum p log p; state share = "
               "sum_{d in s} (-p_d log p_d)/H over {SOURCE, SINK, FADING, UNDETERMINED (incl. ineligible), ORIGIN}; "
               "Rao-Stirling RS = sum_{i != j} d_ij p_i p_j with fixed 2000-2004 distance (1 - cosine of subfield "
               "citation profiles for subfields with >= 50 outgoing in-corpus citations; else taxonomy distance "
               "0/1/3/2/3/1); curves over n_min 5/10/15/20/30 in F_band x age cells with concept-bootstrap 95% CI; "
               "tercile transition H vs H_S (entropy over SOURCE edges + origin); broad-but-hollow list = top tercile "
               "of SINK share within cell"),
        "power": {
            "H1": ("unit (c,t) with >= 1 tested edge; BASE = [H, active subfields, growing-edge breadth, mean host momentum, "
                   "log W1 volume]; S = [source-only breadth, sink entropy share]; Y ~ Bernoulli(logit^-1(a + beta z(BASE_lin) "
                   "+ gamma z(resid(S|BASE)))), BASE_lin = sum of z-scored BASE features, S_lin = sum of z-scored S; "
                   "beta tuned for oracle BASE AUC 0.70 / 0.80, prevalence 0.35, gamma grid 8 values 0..1.5; true "
                   "delta-AUC on 100k oracle draws; pipeline = GroupKFold(5) by concept, StandardScaler + "
                   "LogisticRegression(C=1, lbfgs), OOF probabilities, delta-AUC, 1,000-rep concept bootstrap; success = "
                   "CI95 lower > 0 AND point >= 0.01 AND sign of gamma recovered (Model B coefficient on S_lin > 0); "
                   "200 sims per cell; cells N {realised, projected} x n_min {5,10,20} x BASE AUC {0.70,0.80}; MDE = "
                   "interpolated true delta-AUC at power 0.80. Continuous variant: Y = beta z(BASE_lin) + gamma "
                   "z(resid S) + N(0,1), beta for BASE R2 0.10 / 0.30, OLS OOF R2 gain, same CV + bootstrap; success = "
                   "CI95 lower > 0 AND sign recovered; MDE in delta-R2 vs Maillart 0.018"),
            "gate_B": ("episode = (c,t) with >= 1 SOURCE and >= 1 SINK host at t AND origin cooling onset in [t+1,t+5] "
                       "(theta 0.7); upper-bound episodes = >= 2 tested hosts and cooling in W2; simulated NegBin panel "
                       "with alpha_{episode,tau} ~ N(0,0.3^2), gamma_{d,tau} ~ N(0,0.2^2), b1 = b3 = 0, b4 = 0.1, phi by "
                       "method of moments on W1 host yearly counts; fit pyfixest fepois('y ~ sink + sink:cool + mom + "
                       "mom:cool | ep^tau + d^tau', offset log v_h, CRV1 by concept); grid exp(b2)-1 in {-5,-10,-15,-20,"
                       "-25,-35,-50,-60}%, 300 sims; power = share with CI95 upper for b2 < 0; < 30 clusters -> wild "
                       "cluster Rademacher score bootstrap (199 reps) size check on 100 sims at b2 = 0; MDE = interpolated "
                       "|%| at power 0.8; FAIL if MDE > 25% or < 10 clusters"),
            "decision_lines": "realised N_c >= 150 concepts with a tested edge -> H1 testable, else 'pilot only (MDE = x)'; Gate B MDE <= 25%",
            "projection": ("NB regression of tested edges per concept on log V, F_band, origin field group, offset log(#focal "
                           "years); pending main concepts via model without origin group; projected N_c = realised + sum "
                           "P(>= 1 tested edge), parametric bootstrap 90% interval"),
        },
        "synthetic_validation": ("production functions on synthetic concepts in the real schema; grid R {0.5,0.8,1,1.3,2} x "
                                 "iota {0,0.3,0.6,0.9} x n_p {5,10,20,40,80}, 200 edges per cell; truth SOURCE R>1, SINK "
                                 "R<1 & iota>0.5, FADING R<1 & iota<=0.5, NULL R=1; pass: realised FDR <= 0.15 at main "
                                 "n_min under correct calibration; misspecification: host pi 0.8x / 1.25x, pi drift "
                                 "+10%/yr, rho0 from only 3 references"),
        "leakage": ("all edge-year functions accept only a w1_view (t_max attr asserted); only origin.py reads years > t "
                    "and only origin-subfield rows; mutation test with injected post-t papers must leave outputs "
                    "byte-identical"),
        "iteration1_preregistered_screen_verbatim": selection_rule_verbatim(),
        "iteration2_revisions": [
            "all focal years with age 3..8 and t <= 2019 (replaces the cohort-confounded 2010-14 / 2016-18 tags)",
            "sha1 fold = screen / held-out concept partition",
            "2016-18 focal years = secondary out-of-time check",
            "Gate A measured as WITHIN-HOST non-canonical traced share per edge (iteration-1 0.552 counted any parent)",
            "habitat = OpenAlex primary_topic subfield only (venue habitat not used)",
        ],
    }


def main() -> None:
    setup_logging("prereg")
    if PREREG.exists():
        logger.warning("prereg already frozen; not rewriting (the prereg file is never edited)")
        return
    PREREG.parent.mkdir(exist_ok=True)
    blob = json.dumps(build(), indent=2, sort_keys=False).encode()
    PREREG.write_bytes(blob)
    sha = hashlib.sha256(blob).hexdigest()
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (PREREG.parent / "prereg_freeze.sha256").write_text(f"{sha}  prereg_freeze.json\nfrozen_at_utc {ts}\n")
    (PREREG.parent / "deviations.md").write_text("# Deviations from prereg_freeze.json\n\n")
    logger.info(f"prereg frozen sha256={sha} at {ts}")


if __name__ == "__main__":
    main()
