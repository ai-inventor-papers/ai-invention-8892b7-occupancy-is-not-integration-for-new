"""Shared paths, the iteration-3 SPEC3, logging, hashing and JSON helpers.

Every module in src/ imports this first. It puts vendor/ (exp_3 code copied byte-identical) on sys.path so
`import config`, `import lib_metrics`, `import stage_indicators`, `import analysis_event` resolve to the vendored
iteration-2 code. Only pure functions of those modules are used.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
SRC = ROOT / "src"
WORK = ROOT / "work"
SEALED = ROOT / "sealed"
RES = ROOT / "results"
FIG = ROOT / "figures"
LOGS = ROOT / "logs"
for _d in (WORK, SEALED, RES, FIG, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------- dependency workspaces (read-only)
INV = Path(os.environ.get("AII_INVENTION_LOOP", ROOT.parents[2])).resolve()  # .../3_invention_loop
EXP3 = INV / "round-2" / "." / "gen_art_experiment_3"          # art_mbFjmo5rbbf8 (by path)
DS5 = INV / "round-2" / "." / "gen_art_dataset_5"              # art_eR1Z7fMlOcxs
DS1 = INV / "round-1" / "." / "gen_art_dataset_1"              # art_94GEMUsgAmgK
TESTPOP = INV / "round-2" / "." / "gen_art_experiment_1" / "results" / "test_population.json"  # art_BdBvbNuNU8E7
TESTPOP_SHA = "6a887fb44d3a72951abbc647cb08a5be39081601e0e2647922376dcd40075505"
EXP3_SNAP = EXP3 / "work" / "snapshots"
VENDOR_FILES = ["config.py", "spec.json", "netcore.py", "lib_metrics.py", "stage_indicators.py", "analysis_event.py",
                "analysis_predict.py", "stage_snapshots.py"]

# vendored config.py resolves its (unused here) iteration-1 dependency root from this variable
os.environ.setdefault("AII_DEPS_ROOT", str(INV / "round-1" / "."))
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ----------------------------------------------------------------------------- SPEC3 (frozen before any label)
VERDICT_RULES = (
    "BROKERAGE if ALL of: S_res < 0 and CI_res excludes 0; |S_res| >= 0.5*|S_raw|; S(closure_persist) < 0; "
    "S(constraint) < 0; (CI(closure_persist) excludes 0 OR CI(constraint) excludes 0). "
    "TURNOVER if ALL of: CI_res includes 0; |S_res| < 0.5*|S_raw|; R1b null (CI(closure_persist) includes 0). "
    "MIXED otherwise. R1b NON-ESTIMABLE (< 10 matched treated with finite closure_persist in k=-3..0) counts as null "
    "for TURNOVER and as failing for BROKERAGE. S_raw = S(closure), S_res = S(closure_resT), cell = MAIN x all x E_up "
    "x route all. Flags never change the label: R1c_degree_driven, R1b_selection, H_sensitive, underpowered, "
    "fresh_replication, route_B_only agreement, R1a_model_dependent."
)
SPEC3: dict = dict(
    bootstrap=2000, bootstrap_nonprimary=2000, es_primary_window=[-3, 0], es_sens_window=[-5, -1],
    es_rel_years=list(range(-5, 1)), persist_min=5, xcomm_null_draws=50, xcomm_strength_deciles=10,
    ego_min_neighbours=5, xc_min_members=5,
    r1a_covariates=["new_relation_rate", "novelty", "beta_sim_rar", "log_vol3", "age", "H"],
    r1a_na_rule="mean-fill (screen fit-set mean) + NA dummy for any covariate with missing values "
                "(beta_sim_rar and H by declaration; novelty / new_relation_rate if NA occurs)",
    r1a_fit_set="arm main, fold screen, finite closure, age >= -2 (all years); NO label column in scope",
    r1a_sensitivities={"closure_resT_cc": "complete-case (no fill, no dummies)",
                       "closure_resT_raw": "beta_sim_raw replaces beta_sim_rar (mean-fill + NA dummy)"},
    holm_primary=["closure_resT", "closure_persist", "constraint"],
    screened_direction={"closure": "-", "closure_resT": "-", "closure_persist": "-", "constraint": "-",
                        "xc_excess": "+", "effsize": "+", "wmz": "+"},
    verdict_rules=VERDICT_RULES,
    r1b_min_treated=10, r1b_selection_points=15, h_sensitive_loss=0.5, underpowered_n=30,
    match_H_sensitivity_caliper_sd=0.25,
    betweenness_seed_base=20260928, betweenness_pivots=500,
    sealed_max_year=2015,
    seeds=dict(es=20261001, panel=7, cv=11, sim=13, xc="XC"),
    mde=dict(grid_n=25, grid_max_sd=1.5, sims=500, boot=400, power=0.80, alpha_one_sided=0.05,
             tie_rel=0.05),
    prediction=dict(ages=[3, 8], t_range=[2008, 2015], folds=5, seeds=[0, 1, 2, 3, 4], C=1.0, boot=2000,
                    shuffles=20, label="E_up", population="MAIN screen",
                    BASE="vendored analysis_predict BASELINE = BASE_A + BASE_B + BASE_C + EXTRA",
                    FULL="BASE + [closure_resT (R1a OLS refit inside each training fold), constraint]",
                    FULL_R1bc="BASE + [closure_persist (median-fill + NA dummy), xc_excess]",
                    model="StandardScaler + L2 logistic C=1, class_weight balanced (vendored _clf('logit'))",
                    cv="StratifiedGroupKFold(5, shuffle, groups=concept) x 5 seeds; OOF scores averaged over seeds"),
    populations=dict(MAIN="frozen MAIN rule after the frozen replacement rule", STRICT="frozen STRICT rule",
                     SENS="all 426 (screen part = 247 screen-fold main concepts)"),
    fold_rule="int(sha1(concept_id).hexdigest(), 16) % 10 < 7 -> screen else heldout (ds5 metadata_fold authoritative)",
)


def spec3_hash() -> str:
    return hashlib.sha256(json.dumps(SPEC3, sort_keys=True).encode()).hexdigest()


# ----------------------------------------------------------------------------- helpers
def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{name}:{line}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean(o):
    """JSON-safe conversion (NaN -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    return o


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(clean(obj), indent=1))


def append_freeze_log(file: str, sha: str, note: str = "") -> None:
    with open(RES / "freeze_log.jsonl", "a") as f:
        f.write(json.dumps(dict(file=file, sha256=sha, utc_iso=utc_now(), note=note)) + "\n")


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def set_ram_limit(gb: float) -> None:
    import resource
    b = int(gb * 1024 ** 3)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        b = min(b, hard)
    resource.setrlimit(resource.RLIMIT_AS, (b, b if hard == resource.RLIM_INFINITY else hard))
