"""Shared configuration: dependency paths, the frozen D2 SPEC, sealing guard, logging and resource helpers.

Vendored from iteration-2 gen_art_experiment_3/config.py (detect_cpus, set_ram_limit, assert_not_sealed) and extended
with the RQ2-D2 host-entry SPEC. Every dependency is read-only prior-round output on the run volume.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parents[1]
# ONE relative root for every input artifact: the invention-loop folder that holds iter_1/, iter_2/, iter_3/.
# Default: this artifact sits at <loop>/iter_3/gen_art/<artifact>, so the root is WS.parents[2] (relative to this file).
# Override with AII_DEPS_ROOT, or point a single dependency elsewhere with its own variable below.
LOOP = Path(os.environ.get("AII_DEPS_ROOT", os.environ.get("AII_LOOP_DIR", WS.parents[2]))).resolve()
I2 = LOOP / "round-2" / "."
D1 = Path(os.environ.get("AII_DATASET1_DIR", LOOP / "round-1" / "." / "gen_art_dataset_1"))  # art_94GEMUsgAmgK
D5 = Path(os.environ.get("AII_DATASET5_DIR", I2 / "gen_art_dataset_5"))        # art_eR1Z7fMlOcxs: hydrated corpus
E1 = Path(os.environ.get("AII_EXP1_DIR", I2 / "gen_art_experiment_1"))         # frozen test population
E2 = Path(os.environ.get("AII_EXP2_DIR", I2 / "gen_art_experiment_2"))         # graft_fallback() events, ppml.py
E3 = Path(os.environ.get("AII_EXP3_DIR", I2 / "gen_art_experiment_3"))         # rs_distance

RESULTS = WS / "results"
SEALED = WS / "sealed"
FIGS = WS / "figures"
LOGS = WS / "logs"
CACHE = RESULTS / "cache"
for _d in (RESULTS, SEALED, FIGS, LOGS, CACHE):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 20260929

SPEC: dict = dict(
    name="RQ2-D2 host-entry anchoring (grafting) vs co-transfer (toolkit)",
    event=dict(
        known_sub_min_topic_score=0.05, e_max=2019, main_rule="F <= e <= 2019",
        reference_rule="2005 <= e <= 2019 and no d-paper in 2000-2004", kw5_min_distinct_partners=5,
        dedup="within (concept, dup_group): earliest year, then max n_refs, then min work_id (iteration-1 rule)",
        year_field="concept_work link year"),
    partners=dict(source="legacy OpenAlex concept tags of the entry-year d-papers", min_score=0.2, min_level=1,
                  drop_own_linked_concept=True, weighting="tag-weighted multiset over (paper, partner) pairs"),
    nativeness=dict(blocks={"2005-2009": "2000-2004", "2010-2014": "2005-2009", "2015-2019": "2010-2014"},
                    share="counts[d] / (total - unknown); truncated_top200 and d absent -> 0",
                    native_threshold=0.5, threshold_curve=[0.3, 0.7]),
    co_transfer=dict(companions="partners on c-papers with sub == o(c) in [e-5, e-1]",
                     variant_any="partners on any earlier c-paper (years < e)"),
    outcomes=dict(W2="[e+1, e+5]", primary="Y_strict", prior_set="authors of c-papers in [e-5, e] plus their "
                  "co-authors on any corpus work in [e-5, e]", Y_strict="W2 d-papers of c with no author in Pset "
                  "(papers without author ids excluded)", Y_lenient="W2 d-papers with >= 1 author not in Pset",
                  Y_all="all W2 d-papers of c", EST_bin="Y_strict >= 3 and d-papers in >= 3 of the 5 W2 years",
                  zero_share_switch=0.85),
    models=dict(estimator="PPML (IRLS, exact sparse FE projection, singleton/separation pruning)",
                primary_fe=["concept x e", "d x e"], offset="log(n_entry_papers)", cluster="concept",
                primary_controls=["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score",
                                  "boundary_share", "abstract_share"],
                secondary_fe=["concept", "e", "d"],
                secondary_controls=["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score",
                                    "boundary_share", "abstract_share", "mom_d", "log_centrality", "log_W1",
                                    "route_A"],
                sample="screen fold, MAIN population, kw5, main arm (F <= e <= 2019)",
                coefficient_scale="IRR per 0.1 of A / CT and per SD",
                inference="CRV1 by concept (pyfixest small-sample factor); wild cluster score bootstrap p (999)",
                holm_family=["b_A", "b_CT"],
                decision={"GRAFTING": "b_A > 0, Holm p < .05, b_CT not significantly > 0",
                          "TOOLKIT": "b_CT > 0, Holm p < .05, b_A n.s.",
                          "BOTH": "both significantly > 0", "NEITHER": "otherwise (report MDE)",
                          "negative": "a significant negative sign is reported as such"},
                fallback_thin_cells="retained < 30% of events or G < 50 -> secondary spec co-primary"),
    placebo=dict(draws=500, label_shuffle_draws=50),
    bootstrap_reps=1000, wild_reps=999, power_reps=300, power_grid=[1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.40],
    label=dict(benchmark="median entry A over REFERENCE_ACCEPTED reference-arm events in d (>= 5), else field, "
               "else global", lower_bound="bootstrap 90% lower (n_entry_papers >= 3) else Clopper-Pearson 90% "
               "lower"),
    fold_rule="screen iff int(sha1(concept_id), 16) % 10 < 7",
    seed=SEED,
)


def spec_hash() -> str:
    return hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path) -> str:
    """Path relative to the run root (no absolute server paths in published files)."""
    try:
        return str(Path(p).resolve().relative_to(LOOP.parent))
    except ValueError:
        return str(p)


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{name}:{line}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


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
    """Cap the address space so runaway memory raises MemoryError instead of OOM-killing the container."""
    b = int(gb * 1024 ** 3)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        b = min(b, hard)
    resource.setrlimit(resource.RLIMIT_AS, (b, b if hard == resource.RLIM_INFINITY else hard))


SEALED_IDS: set[str] = set()


def load_sealed_ids() -> set[str]:
    p = RESULTS / "main_population_hydrated.json"
    if p.exists():
        SEALED_IDS.clear()
        SEALED_IDS.update(json.loads(p.read_text())["sealed_ids"])
    return SEALED_IDS


def assert_not_sealed(concept_ids) -> None:
    """Code guard: held-out concepts never enter W2 (outcome) computations outside confirm_heldout.py."""
    bad = set(concept_ids) & SEALED_IDS
    if bad:
        raise RuntimeError(f"SEALED concept ids requested: {sorted(bad)[:5]}")


def fold_of(concept_id: str) -> str:
    return "screen" if int(hashlib.sha1(concept_id.encode()).hexdigest(), 16) % 10 < 7 else "heldout"
