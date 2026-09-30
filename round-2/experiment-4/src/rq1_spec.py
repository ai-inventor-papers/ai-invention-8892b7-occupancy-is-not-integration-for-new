"""Frozen RQ1 specification for the held-out MeSH replication.

Every constant used by the pipeline lives here. The sha256 of this file is written to
results/prereg_spec.json before any W2 outcome is computed (see method.py STEP 0).
No main-pool spec module (rq1_spec.py / rq1_features.py) existed under iter_2/gen_art/* at
run time, so these values implement the plan text verbatim; declared resolutions are listed in
DECLARED_CHOICES.
"""

POPULATION = "mesh_heldout"
SEED = 42

# ---- snapshots
YEARS = list(range(2000, 2025))
WINDOW = 3  # trailing window y-2..y, for background AND focal attachment (declared)
TAG_MIN_SCORE = 0.3
EXCLUDE_LEVEL0 = True
EDGE_MIN_WCOUNT = 2.0  # on weighted co-occurrence W_ij (population-count units)
LEIDEN = {
    "partition": "RBConfigurationVertexPartition",
    "resolution": 1.0,
    "seeds": [42, 43, 44, 45, 46],  # n_starts = 5, keep max quality
    "n_iterations": 2,  # DEVIATION from plan (-1): measured 95 s/seed/snapshot at -1 (3.3 CPU-h total);
    # n_iterations=2 reaches 99.6% of the -1 quality on the 2014 snapshot (see results/prereg_spec.json)
    "weight": "association_strength",
}
COMMUNITY_MATCH_JACCARD = 0.3
LEIDEN_TIMEOUT_S = 600  # F2: fall back to ModularityVertexPartition if slower
TOPK_CLOSURE = 20
REWIRE_FRAC = 0.10
REWIRE_REPS = 20
REWIRE_SWAPS_PER_EDGE = 10
BETWEENNESS_SAMPLES = 500

# ---- emergence labels
AGE_RANGE = (3, 8)
T_MAX = 2019
E_MIN_MEAN = 20.0
E_MAX_FALL = 0.30  # V[t+5] >= (1 - 0.30) * V[t+1]
E_PCTL_GAIN = 20.0
# Percentile reference for E_cent (declared BEFORE outcomes, from the mini feature distribution only):
# 'focal' = percentile of weighted degree among the non-isolated MeSH focal nodes of snapshot y;
# 'all_nodes' = plan-literal reference (bg + focal nodes). In the mini run every focal concept-year sat at the
# 0.04-1.5th percentile of all nodes (sampled legacy tags each stand for hundreds of population works), so a
# 20-point gain is structurally infeasible there; 'all_nodes' is still labelled and reported (E_cent_allnodes).
E_CENT_REFERENCE = "focal"
HORIZON = 5
VOLUME_DEFS = ["PRIMARY_tm", "SENS1_tm_plus_np", "SENS2_mesh_indexed"]

# ---- matching
MATCH_VOL_TOL = 0.20
MATCH_VOL_TOL_WIDE = 0.30
MATCH_RATIO = 3
F_BANDS = {"2005-07": (2005, 2007), "2008-11": (2008, 2011), "2012-16": (2012, 2016)}  # dataset_1 metadata_F_band

# ---- event study
EVENT_REL = [-5, -4, -3, -2, -1]
PRIMARY_EVENT_WINDOW = [-3, -2, -1]
PRECURSORS = ["accretion_share", "closure_lr", "dP"]
BOOT = 2000
PERM_MDE = 500
NULL_PERMS = 200

# ---- rolling-origin prediction
ORIGINS = list(range(2012, 2020))
TRAIN_LAG = 5  # train units have t <= T - 5
MIN_TRAIN_UNITS = 30
MIN_TRAIN_POS = 5
LOGREG = {"penalty": "l2", "C": 1.0, "class_weight": None, "max_iter": 5000}
GROUPED_CV_FOLDS = 5
KLEINBERG = {"s": 2.0, "gamma": 1.0}

# ---- patterns
PATTERN_QUIET_YEARS = 2
PATTERN_GROWTH_PCTL = 90
PATTERN_TAU = 0.5
PATTERN_CENTRAL_YEARS = 3
PATTERN_P_LOW = 0.3
PATTERN_P_HIGH = 0.6
PATTERN_BETW_DECILE = 0.9
PATTERN_EARLY_YEARS = 2

# ---- main-pool alignment (sibling iteration-2 main-pool RQ1 run found at run time: gen_art_experiment_3,
# spec.json sha256 d61374e1..., lib_metrics.py sha256 ecc07a08... vendored read-only as vendor/mainpool_lib_metrics.py).
# Added BEFORE any outcome of this population was computed; the plan-native block above is unchanged.
MAINPOOL = {
    "source": "iter_2/gen_art/gen_art_experiment_3 (spec.json, lib_metrics.py, stage_snapshots.py, stage_indicators.py, analysis_event.py)",
    "precursors": ["accretion_shift_rar", "closure", "P_rar"],
    "families": {"accretion": ["accretion_shift_rar", "accretion_shift_raw", "accretion_shift_rar_res"],
                 "closure": ["closure", "closure_raw", "closure_res"],
                 "participation": ["P_rar", "P_raw", "P_rar_res"]},
    "exploratory": ["new_rel_rate", "nbr_novelty", "beta_sim_rar", "beta_sne_rar", "sne_share_rar", "z_within", "betw",
                    "comm_change", "n_modules_touched", "subfield_entropy", "burst_active_tm", "accretion_shift_rar5",
                    "P_rar_m5", "wdeg_pctl_focal", "log_vol3", "wdeg_pctl", "growth"],
    "labels": {"E": "uptake AND all-node percentile gain >= 20 (main-pool primary)",
               "E_alt": "uptake AND focal-population percentile gain >= 20 (main-pool E_alt)",
               "E_up": "uptake only (mean >= 20 over t+1..t+5, no fall > 30%)"},
    "es_rel_years": [-5, -4, -3, -2, -1, 0],  # calendar year = t0 + k, t0 = onset label year
    "es_summary_window": [-3, 0],
    "controls": "never-emerging concepts (no onset in the eligible window), same F-band and origin group, "
                "nearest on log vol3 within +-20% (else +-30%), 1:3 with replacement",
    "origin_group": "OpenAlex origin field (the main pool's origin group is its stratum prefix, an OpenAlex field or "
                    "domain id such as F31 / D3)",
    "mde": "2.8 x bootstrap SE / pooled SD",
}

DECLARED_CHOICES = {
    "focal_window": "3-year trailing (y-2..y) for focal attachment, matching the background window",
    "pattern_percentile_reference": "all MeSH focal concept-years (not bg nodes)",
    "units_of_weights": "background W_i/W_ij are post-stratified population-count estimates "
    "(w_year = n_frame/n_sampled); focal W_c/W_cj are census counts of verified works (weight 1); "
    "both are counts of population works, so strengths are on one scale",
    "focal_tags_not_in_bg": "focal co-tags absent from the window's background vocabulary have no W_j "
    "and are dropped (share logged)",
    "volres_fit_set": "volume residualisation of intensive indicators is fitted on ALL focal concept-years "
    "(outcome-blind, so it can be frozen before labels) instead of 'never-emerging' concept-years",
    "E_labels_outside_age_range": "E(c,t) is computable for any t <= 2019; onsets are searched only in "
    "t in [F+3, F+8]; a control needs E(c',t*)=0 and no onset <= t*",
    "incubation_rule": "a run of >= 2 consecutive network years with beta_sim AND dk below the population "
    "median, immediately followed by a year with strength growth above the 90th percentile",
    "centralisation_rule": "any run of >= 3 consecutive network years with P < 0.3 on every year and "
    "Kendall tau(year, within-module z) > 0.5",
    "bridging_rule": "P > 0.6 or betweenness in the top decile of that snapshot's nodes in either of the "
    "first 2 network years",
    "kleinberg": "batched 2-state, s=2, gamma=1, r_t = concept volume, d_t = OpenAlex all_types total for "
    "year t (dataset_1 context/subfield_year_totals.json); Viterbi recomputed on years <= t for each t",
    "leiden_iterations": "leidenalg n_iterations=2 (package default) instead of -1: -1 took 95 s per seed per "
    "snapshot; on 2014 the n_iterations=2 partition had quality 896,789 vs 899,619 (-0.3%) and seed-to-seed "
    "NMI was <0.8 in both settings, so F2 applies: P and z are reported with their spread over the 5 seeds",
    "E_cent_reference": "PRIMARY E_cent uses the percentile of weighted degree among MeSH focal nodes of the same "
    "snapshot (wdeg_pctl_focal); the plan-literal all-node percentile label is reported as E_cent_allnodes. The "
    "A2 baseline's dpctl uses the same focal reference so the baseline sees the outcome-relevant centrality.",
    "precursor_versions": "accretion_share, closure_lr, dP are intensive: the 'raw' version is the primary "
    "test; the '_volres' version is secondary",
}
