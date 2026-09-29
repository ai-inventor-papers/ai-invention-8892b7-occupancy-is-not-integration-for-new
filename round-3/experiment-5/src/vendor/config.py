"""Shared configuration: dependency paths, the frozen SPEC, logging and resource helpers."""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
# Dependency artifacts are sibling folders in the published repository: <invention_loop>/iter_1/gen_art/<artifact>.
# Override with AII_DEPS_ROOT if they live elsewhere.
RUN = Path(os.environ.get("AII_DEPS_ROOT", ROOT.parents[2] / "round-1" / ".")).resolve()
D1 = RUN / "gen_art_dataset_1"          # art_94GEMUsgAmgK concept pool + c-papers
D2 = RUN / "gen_art_dataset_2"          # background whole-science sample (not a registered dependency; by path)
D4 = RUN / "gen_art_dataset_4"          # art_QpM5SM6a7SH6 stratified corpus (fallback / substrate robustness)
DR = RUN / "gen_art_research_1"         # art_bNCGUJX2MUhX pre-registration dossier

WORK = ROOT / "work"                    # regenerable intermediates
OUT = ROOT / "results"
FIG = ROOT / "figures"
for _d in (WORK, OUT, FIG, ROOT / "logs"):
    _d.mkdir(parents=True, exist_ok=True)

SPEC: dict = dict(
    years=list(range(2000, 2025)), window=3, tag_min_score=0.3, min_level=1, kept_edge_min_raw=2,
    leiden=dict(type="RBConfiguration", resolution=1.0, seed=42, n_runs=5),
    alluvial_min_jaccard=0.3, alluvial_min_comm_size=5,
    topk_closure=20, closure_min_neighbours=5, rewire_n=20, rewire_snapshots=[2008, 2013, 2018],
    stability_resamples=20, stability_snapshots=[2008, 2013, 2018],
    betweenness_pivots=500, rarefy_m=10, rarefy_m_sensitivity=5, rarefy_draws=50,
    E_uptake_mean=20, E_max_fall=0.30, E_pct_gain=20, ages=[3, 8], t_max=2019,
    sealed_focal_years=[2016, 2017, 2018], screen_onset_years=list(range(2008, 2016)),
    match=dict(band=True, origin_group=True, vol_caliper=0.20, widen=0.30, ratio=3, replace=True),
    bootstrap=1000, holm_precursors=["accretion_shift_rar", "closure", "P_rar"],
    precursor_signs={"accretion_shift_rar": "+", "closure": "+", "P_rar": "+"},
    es_rel_years=list(range(-5, 1)), es_summary_window=[-3, 0],
    test_origins=[2013, 2014, 2015, 2019], min_train_rows=30, min_train_pos=5,
    h3_test_origins=[2011, 2012, 2013, 2014, 2015, 2019],
    frame_types=["article", "review", "preprint", "book-chapter"],
    kleinberg=dict(s=2.0, gamma=1.0),
    sensitivity_grid=dict(uptake=[10, 20, 30], pct_gain=[10, 20, 30]),
    early_bridging=dict(P_raw=0.6, btw_pct=90, min_comm_share=0.10, min_comms=2),
    gradual_centralisation=dict(min_len=3, tau=0.5, P_max=0.3),
    incubation=dict(min_run=2, burst_pct=90),
    typology=dict(channels=["strength_growth", "beta_sim_rar", "beta_sne_rar", "P_rar", "closure", "btw_pct", "H"],
                  ages=list(range(0, 9)), max_missing=3, max_fill=2, k_range=[2, 3, 4, 5, 6],
                  sakoe_chiba_radius=2, boot=200, jaccard_min=0.75),
    clarifications=[
        "(i) kept-graph edges = >= 2 RAW sample co-occurrences in the 3-year window (weighted c_ij >= 2 is non-binding because "
        "design weights are >= 1, median 293); strengths use ALL edges.",
        "(ii) background-comparable pool quantities (strength, strength percentile, association strength, closure neighbour "
        "set, within-module z, betweenness attachment) use frame-type c-papers (article, review, preprint, book-chapter); "
        "volume, uptake, neighbourhood turnover (Baselga, novelty), participation/community touch and disciplinary "
        "diversity/incidence use all c-paper types.",
        "(iii) works with topic_score < 0.05 (default-topic hazard H1) get subfield 'unknown' in the concept-subfield view "
        "only and are excluded from diversity measures; they stay in the co-word network.",
        "(iv) 'cross-community betweenness' (early bridging) = betweenness percentile >= 90 on the kept graph AND the node's "
        "frame-type tag weight touches >= 2 communities with >= 10% each.",
        "(v) background yearly weights are post-stratified w_year = n_frame(s,y)/n_sampled(s,y); design weight is the "
        "fallback when a subfield-year has no post-stratification cell.",
        "(vi) residualised (_res) indicator versions are fit on the full screen panel and are used only in the event "
        "study, never as prediction features (avoids pooled look-ahead).",
        "(vii) the pool concept strength percentile is computed among all nodes of snapshot y (background legacy concepts "
        "+ attached pool concepts); ALT percentile is among pool (screen+reference) nodes only.",
    ],
)


def spec_hash() -> str:
    return hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest()


def write_spec() -> str:
    h = spec_hash()
    (ROOT / "spec.json").write_text(json.dumps({"spec": SPEC, "sha256": h}, indent=1))
    return h


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{name}:{line}|{message}")
    logger.add(ROOT / "logs" / f"{name}.log", rotation="30 MB", level="DEBUG")


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
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
        b = min(b, hard)  # a child process cannot raise the limit it inherited
    resource.setrlimit(resource.RLIMIT_AS, (b, b if hard == resource.RLIM_INFINITY else hard))


SEALED_IDS: set[str] = set()


def assert_not_sealed(concept_ids, focal_years=()) -> None:
    """Code guard: held-out concepts and sealed focal years never enter E/W2 computations."""
    bad = set(concept_ids) & SEALED_IDS
    if bad:
        raise RuntimeError(f"SEALED concept ids requested: {sorted(bad)[:5]}")
    bad_t = set(int(t) for t in focal_years) & set(SPEC["sealed_focal_years"])
    if bad_t:
        raise RuntimeError(f"SEALED focal years requested: {sorted(bad_t)}")
