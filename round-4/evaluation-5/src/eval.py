#!/usr/bin/env python3
"""Do adopters already speak the partner language? Adopter-level test of the absorptive-capacity mechanism behind the
D2 host-share effect (A_cont; co-primary IRR/SD 1.30), SCREEN fold only (mechanism evidence, not confirmation).

  .venv/bin/python eval.py                     # all stages: prepare frame freeze pull analyze
  .venv/bin/python eval.py --stage prepare     # vendor check, cache rebuild, reproduction gate (b_A 4.7391, N 1544, G 140)
  .venv/bin/python eval.py --stage frame       # cases / risk-set controls / targets / mediators (no exposure read)
  .venv/bin/python eval.py --stage freeze      # mech_spec.json + sha256, simulated MDEs (mech_spec_power.json)
  .venv/bin/python eval.py --stage pull        # blind OpenAlex validation pull (guarded; reads frames/api_jobs.parquet)
  .venv/bin/python eval.py --stage analyze     # hash check, exposures, all metrics, figures, eval_out.json
Options: --B (bootstrap reps, default 1000), --mini (small B / reps smoke run; writes to results/mini/)
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

import mech_common as mc  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(mc.LOGS / "eval.log", rotation="30 MB", level="DEBUG")
import logging  # noqa: E402

logging.getLogger("fontTools").setLevel(logging.WARNING)

WORKERS = 4
API_CAP = 400           # own credit cap for this artifact (validation pull only; plan cap 3,400 not reachable)
API_RESERVE = 2500      # key-wide reserve for G4 and other iteration-4 agents (plan hard guard)
API_MIN_START = 4000    # plan: below this key-wide remaining at start, corpus exposure is PRIMARY
N_API_STRATA = 100      # validation subsample of primary strata (both members)
FR = mc.FRAMES


def _sha(p: Path) -> str:
    return mc.sha256_file(p)


# ------------------------------------------------------------------ stage: prepare
def stage_prepare() -> dict:
    mc.vendor_check()
    G = mc.io_load.prepare()
    mc.author_raw_ids()
    mc.config.load_sealed_ids()
    gate = mc.reproduction_gate()
    gate["vendor_sha256_ok"] = True
    gate["n_sealed_ids"] = len(mc.config.SEALED_IDS)
    mc.dump(gate, mc.RESULTS / "gate.json")
    logger.info(f"REPRODUCTION GATE: {gate}")
    if not gate["pass"]:
        raise SystemExit("reproduction gate FAILED: stop (see results/gate.json)")
    del G
    return gate


# ------------------------------------------------------------------ stage: frame
def stage_frame() -> dict:
    import frame
    G = mc.io_load.prepare()
    t = time.time()
    out = frame.build(G, measurable_only=True)
    C = out["C"]
    out["entries"].to_parquet(FR / "entries.parquet", index=False)
    out["long"].to_parquet(FR / "strata_long.parquet", index=False)
    out["targets"].to_parquet(FR / "targets.parquet", index=False)
    out["cases_all"].to_parquet(FR / "cases_all.parquet", index=False)
    out["bal_pre"].to_parquet(FR / "risk_balance_pre.parquet", index=False)
    logger.info(f"primary frame built in {time.time() - t:.0f}s: {out['summary']['n_strata']} strata")
    # supplementary frame: no per-concept / tercile / hard cap (entry cap 6 kept); targets reused from the primary
    ex = frame.build(G, measurable_only=True, concept_cap=10 ** 9, per_tercile=10 ** 9, hard_cap=10 ** 9,
                     with_mediators=False, C=C)
    ex["long"].to_parquet(FR / "strata_long_expanded.parquet", index=False)
    ex["bal_pre"].to_parquet(FR / "risk_balance_pre_expanded.parquet", index=False)
    summ = {"primary": out["summary"], "expanded": {k: ex["summary"][k] for k in ("caps", "n_strata", "relax_counts",
                                                                                 "widened")}}
    # blind API job file (validation subsample): no case/control/role column; separate key file for the join
    L = out["long"]
    L = L[L.role.isin(["case", "control"])]
    rng = np.random.default_rng(mc.SEED + 7)
    st = rng.choice(L.stratum.unique(), min(N_API_STRATA, L.stratum.nunique()), replace=False)
    sub = L[L.stratum.isin(st)].copy()
    tg = out["targets"].set_index("entry_id")
    jobs = []
    for r in sub.itertuples():
        t_ = tg.loc[r.entry_id]
        targets = list(dict.fromkeys(list(t_.P_nodes) + list(t_.NEG_nodes) + list(t_.PLAC_nodes)))[:100]
        jobs.append({"raw_author_id": int(r.raw_author_id), "cutoff_year": int(r.e) - 1, "targets": targets,
                     "_stratum": int(r.stratum), "_role": r.role, "_entry": r.entry_id})
    J = pd.DataFrame(jobs).sample(frac=1.0, random_state=mc.SEED).reset_index(drop=True)
    J["job_id"] = np.arange(len(J))
    J[["job_id", "_stratum", "_role", "_entry", "raw_author_id", "cutoff_year"]].to_parquet(FR / "api_jobs_key.parquet",
                                                                                             index=False)
    J[["job_id", "raw_author_id", "cutoff_year", "targets"]].to_parquet(FR / "api_jobs.parquet", index=False)
    summ["api_jobs"] = {"n_jobs": int(len(J)), "n_strata": int(len(st)), "mean_targets": float(J.targets.apply(len).mean())}
    mc.dump(summ, mc.RESULTS / "frame_summary.json")
    return summ


# ------------------------------------------------------------------ stage: freeze
SPEC_TEXT = {
    "title": "Do adopters already speak the partner language? (adopter-level absorptive-capacity test of D2)",
    "label": mc.LABEL,
    "sample": "co-primary D2 sample (exp_7 screen MAIN kw5, complete controls, retained by PPML pruning): 1,544 "
              "entries, 140 concepts; sealed (held-out) concepts never read (vendored assert_not_sealed).",
    "exposure_route": "CORPUS-ONLY primary (pre-declared fallback: key-wide OpenAlex remaining < 4,000 at start); every "
                      "row labelled 'corpus-exposure, coverage-limited'. OpenAlex exposure only on a blind validation "
                      "subsample (<= 100 strata) under the 2,500 key-wide reserve.",
    "cases": "authors of the W2=[e+1,e+5] d-papers of c counted in Y_strict (no author in Pset(c,e), vendored "
             "CoauthorIndex); adoption year Y = year of the author's first such paper; placeholder author id -1 dropped. "
             "Corpus-primary adaptation (declared before exposure): cases restricted to exposure-MEASURABLE adopters "
             "(>= 1 corpus work published <= e-1 that is not a c-paper); career-new adopters reported descriptively.",
    "controls": "incidence-density: in-corpus authors with >= 1 corpus d-paper (topic_score >= 0.05) in year Y (widen to "
                "Y+-1 if < 5 candidates); excluded: Pset(c,e), any c-author 2000-2024, any adopter of the same entry; "
                "corpus-primary: >= 1 corpus work <= e-1. Exact match on prior-corpus-works bin (1 / 2-3 / 4+; 0 excluded "
                "by construction), team size bin of index d-paper (1-2/3-5/6-10/11+), host activity bin (n d-papers "
                "[Y-2,Y]: 1/2-3/4+), in-corpus first-year bin (<=e-10 / e-9..e-3 / >=e-2). Relaxation order: first-year, "
                "activity, team, prior-bin. 1 control + 2 reserves (reserves used in the 1:3 supplementary). Seed 20260929.",
    "caps": "<= 6 cases per entry, <= 25 per concept, target 500 per A_cont tercile, hard cap 1,500; shortfall "
            "redistributed. Supplementary 'expanded' frame: entry cap only.",
    "targets": "P = entry's distinct partners (vendored event_tags, own node dropped), top 60 by tag weight; classes by "
               "pre-entry host share s (Nativeness.share, block before e): NATIVE s>=0.3, ADJACENT 0.05<=s<0.3, FOREIGN "
               "s<0.05, UNPROFILED; ORIGIN-COMPANION flag (partners on c-papers in o(c), [e-5,e-1]). NEG <= 20 "
               "profiled legacy nodes matched to random profiled partners on decile of n_p[d,block], decile of total_p "
               "[block] and level (relaxed stepwise), excluding P, companions, own node and PLAC. PLAC = top-20 (by tag "
               "weight) partners of a random other screen MAIN kw5 entry c'!=c into the same d with |e'-e|<=1, minus P.",
    "exposure": "member's corpus works published <= e-1, excluding c-papers; tags = vendored partner rule (legacy "
                "concept score >= 0.2 U keyword-mapped legacy concepts, level >= 1). E_any, E_w, E_nat/E_adj/E_for/"
                "E_unprof, E_comp/E_noncomp, E_neg (+ share), E_plac, E_swap (full partner set of the placebo entry), "
                "E_any_incl_c (sensitivity). Covariate lp = log1p(n prior corpus works excl. c-papers).",
    "models": {
        "M-i": "conditional logit on matched strata: m1 case~E_any+lp; m2 (PRIMARY) +E_neg; m3 E_w; m_plac "
               "E_any+E_neg+E_plac+lp on strata with a placebo; concept-cluster bootstrap B=1000 (percentile CI, "
               "two-sided bootstrap p), model-based and concept-CRV SEs; pyfixest LPM cross-check (stratum FE, CRV1 "
               "concept); statsmodels ConditionalLogit check.",
        "M-ii": "m2 + E_any x z(A_cont) (z over the 1,544 entries); OR by A_cont tercile descriptive with tercile MDE.",
        "M-iii": "case ~ E_nat+E_adj+E_for+E_unprof+E_neg+lp; contrasts logOR(nat)-logOR(for), logOR(adj)-logOR(for); "
                 "origin-companion: E_comp+E_noncomp+E_neg+lp.",
        "M-iv": "entry-level PPML co-primary (concept+e+d FE, offset log n_entry_papers, CRV1 concept; exp_7 controls): "
                "base, +M2, +M2_native+M2_adjacent (Gelbach), +M1, +M2_share; attenuation (b_base-b_full)/b_base; "
                "concept-cluster bootstrap B=1000; reverse attenuation; mediator validation: Spearman M2_share vs "
                "control exposure prevalence per entry (entries with >= 3 control-type members), M2 vs M1."},
    "reading_rules": {
        "SUPPORT": "primary OR(E_any|E_neg,lp) CI excludes 1 above; OR_partner/OR_neg CI excludes 1 above; and "
                   "OR_partner/OR_plac > 1 with CI excluding 1 OR OR_plac n.s.",
        "GENERIC_HOST_VOCABULARY": "primary OR > 1 but OR_partner/OR_plac CI includes 1 while OR_plac significant.",
        "ACTIVITY_ARTEFACT": "OR_partner/OR_neg CI includes 1 and OR_neg significant.",
        "NULL": "primary OR CI includes 1 while MDE80 <= 1.30; if MDE80 > 1.30 -> UNDERPOWERED.",
        "interaction": "positive CI excl 1 = interface matters more when partners are host-native; null = uniform; "
                       "negative = only boundary-spanning exposed authors adopt in low-A entries.",
        "mediation": "attenuation >= 30% with CI excluding 0 = A_cont acts partly through pre-exposed host pool size; "
                     "CI incl 0 = not reducible to pool size (M2), read beside the mediator validation (lower bound).",
        "vocabulary": "NATIVE > FOREIGN (CI excl 0) = grafting; ADJACENT > FOREIGN with NATIVE n.s. = host-adjacent "
                      "re-contextualisation.",
        "MDE_used_for_NULL": "MDE80 at the simulated p0 grid point closest to the observed control prevalence."},
    "credit_caps": {"own_cap": API_CAP, "keywide_reserve": API_RESERVE, "corpus_primary_if_keywide_below": API_MIN_START},
    "seeds": {"frame": mc.SEED, "api_subsample": mc.SEED + 7, "bootstrap": mc.SEED + 11, "permutation": mc.SEED + 13,
              "power": mc.SEED + 17, "mediation_boot": mc.SEED + 19},
}


def stage_freeze(mini: bool) -> dict:
    import power_sim
    inputs = {
        "exp7_screen_events_with_outcomes": mc.EXP7 / "results" / "screen_events_with_outcomes.parquet",
        "exp7_features_screen": mc.EXP7 / "results" / "features_screen.parquet",
        "exp7_main_population_hydrated": mc.EXP7 / "results" / "main_population_hydrated.json",
        "exp7_d2_summary": mc.EXP7 / "results" / "d2_summary.json",
        "d5_concept_work": mc.D5 / "hyd" / "concept_work.parquet",
        "d5_profiles": mc.D5 / "p2" / "profiles.jsonl",
        "d5_subfield_year_totals": mc.D5 / "hyd" / "context" / "subfield_year_totals.json",
        "d2_concepts": mc.D5 / "deps" / "gen_art_dataset_2" / "concepts.parquet",
    }
    for i in range(8):
        inputs[f"d5_works_part_0{i}"] = mc.D5 / "hyd" / "works" / f"works_part_0{i}.parquet"
    frames = sorted(p for p in FR.glob("*.parquet"))
    rel = lambda p: mc.config.rel(p)  # noqa: E731
    spec = dict(SPEC_TEXT)
    spec["frozen_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    spec["input_sha256"] = {k: {"path": rel(v), "sha256": _sha(v)} for k, v in inputs.items()}
    spec["frame_sha256"] = {p.name: _sha(p) for p in frames}
    spec["vendor_sha256"] = (WS / "vendor" / "SHA256SUMS").read_text().splitlines()
    spec["frame_summary"] = json.loads((mc.RESULTS / "frame_summary.json").read_text())
    sp = WS / "mech_spec.json"
    sp.write_text(json.dumps(spec, indent=1, default=str))
    h = _sha(sp)
    (WS / "mech_spec.sha256").write_text(f"{h}  mech_spec.json\n")
    logger.info(f"mech_spec frozen sha256 {h}")
    # ---------- MDE simulations (before exposure) ----------
    L = pd.read_parquet(FR / "strata_long.parquet")
    E = pd.read_parquet(FR / "entries.parquet")
    mA, sdA = float(E.A_cont.mean()), float(E.A_cont.std())
    cs = L[L.role == "case"]
    reps = 40 if mini else 300
    t = time.time()
    pw = power_sim.pair_power(cs.concept_id.to_numpy(), ((cs.A_cont - mA) / sdA).to_numpy(), reps, mc.SEED + 17, WORKERS)
    # tercile MDE (descriptive): power on each tercile's strata at p0 in {0.25, 0.4}
    terc = {}
    for tt in (1, 2, 3):
        c_t = cs[cs.A_tercile == tt]
        g = []
        for p0 in (0.25, 0.4):
            for orv in (1.3, 1.5, 2.0, 3.0):
                g.append({"p0": p0, "OR": orv, "power": power_sim.sim_pairs(c_t.concept_id.to_numpy(), np.zeros(len(c_t)),
                                                                          p0, orv, 1.0, max(reps // 3, 30),
                                                                          mc.SEED + 500 + tt, False)})
        terc[f"T{tt}"] = {"n_pairs": int(len(c_t)), "grid": g,
                          "MDE80_p0_0.25": min((x["OR"] for x in g if x["p0"] == 0.25 and x["power"] >= 0.8), default=None),
                          "MDE80_p0_0.4": min((x["OR"] for x in g if x["p0"] == 0.4 and x["power"] >= 0.8), default=None)}
    pw["tercile"] = terc
    logger.info(f"pair power done in {time.time() - t:.0f}s: {pw['MDE80']}")
    # mediation power
    import ppml
    import pyfixest as pf
    y = E.Y_strict.to_numpy(float)
    X = E[mc.XVARS].to_numpy(float)
    fes = [pd.factorize(E.concept_id)[0], pd.factorize(E.e.astype(str))[0], pd.factorize(E.d.astype(str))[0]]
    r0 = ppml.fit(y, X, fes, E.offset.to_numpy(), E.concept_id.to_numpy(), maxit=500, tol=1e-12)
    assert r0["n"] == len(E), "mediation base must retain all 1,544 entries"
    m = pf.feols(f"M2 ~ {' + '.join(mc.XVARS)} | concept_id + e + d", data=E, vcov={"CRV1": "concept_id"})
    Gam, Gp = float(m.coef()["A_cont"]), float(m.pvalue()["A_cont"])
    base = {"mu0": r0["mu"], "A": X[:, 0], "M": E.M2.to_numpy(float), "X": X, "fes": fes, "off": E.offset.to_numpy(),
            "cl": E.concept_id.to_numpy(), "bA": float(r0["coef"][0]), "Gamma": Gam, "vendor": str(WS / "vendor")}
    t = time.time()
    mp_ = power_sim.mediation_power(base, 20 if mini else 300, mc.SEED + 17, WORKERS, gamma_sig=Gp < 0.05)
    mp_["Gamma_p"] = Gp
    logger.info(f"mediation power done in {time.time() - t:.0f}s: {mp_['MDE80_share']}")
    power = {"pairs": pw, "mediation": mp_, "computed_before_exposure": True, "mech_spec_sha256": h,
             "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    mc.dump(power, WS / "mech_spec_power.json")
    mc.dump(power, mc.RESULTS / "power.json")
    return power


# ------------------------------------------------------------------ stage: pull
def check_hash() -> str:
    sp = WS / "mech_spec.json"
    h = _sha(sp)
    want = (WS / "mech_spec.sha256").read_text().split()[0]
    if h != want:
        raise SystemExit(f"mech_spec.json hash {h} != frozen {want}: refusing to run")
    spec = json.loads(sp.read_text())
    for name, hh in spec["frame_sha256"].items():
        if _sha(FR / name) != hh:
            raise SystemExit(f"frozen frame {name} changed: refusing to run")
    if not (WS / "mech_spec_power.json").exists():
        raise SystemExit("MDE file missing: freeze stage must run before exposure")
    return h


def stage_pull(mini_n: int | None) -> dict:
    import api_pull
    check_hash()
    res = api_pull.pull(FR / "api_jobs.parquet", cap=API_CAP, reserve=API_RESERVE, mini=mini_n)
    res["route_note"] = ("key-wide remaining below 4,000 at start -> corpus exposure PRIMARY; API = validation subsample "
                         "only" if (res["remaining_start"] or 0) < API_MIN_START else "key-wide >= 4,000")
    api_pull.save(res, mc.RESULTS / ("api_results_mini.json" if mini_n else "api_results.json"))
    return {k: v for k, v in res.items() if k not in ("results", "authors")}


# ------------------------------------------------------------------ stage: analyze
def api_exposure(T: pd.DataFrame) -> pd.DataFrame | None:
    p = mc.RESULTS / "api_results.json"
    if not p.exists():
        return None
    res = json.loads(p.read_text())
    key = pd.read_parquet(FR / "api_jobs_key.parquet")
    tg = T.set_index("entry_id")
    auth = {int(a["id"].rsplit("A", 1)[1]): a for a in res.get("authors", [])}
    rows = []
    for r in res["results"]:
        if not r.get("ok"):
            continue
        k = key[key.job_id == r["job_id"]].iloc[0]
        t = tg.loc[k._entry]
        P, neg, plac = set(t.P_nodes), set(t.NEG_nodes), set(t.PLAC_nodes)
        used02, usedany = set(), set()
        for w in r["works"]:
            for c, sc in w["c"]:
                usedany.add(c)
                if sc >= 0.2:
                    used02.add(c)
        a = auth.get(int(r["raw_author_id"]))
        prior_n, approx = None, None
        if a:
            cby = {int(x["year"]): int(x["works_count"]) for x in a.get("counts_by_year", [])}
            e = int(r["cutoff_year"]) + 1
            prior_n = int(a.get("works_count", 0)) - sum(v for y_, v in cby.items() if y_ >= e)
            approx = bool(not cby or e < min(cby))
        rows.append({"stratum": int(k._stratum), "role": k._role, "api_E_any": int(bool(P & used02)),
                     "api_E_any_anyscore": int(bool(P & usedany)), "api_E_neg": int(bool(neg & used02)),
                     "api_E_plac": int(bool(plac & used02)), "api_meta_count": r["meta_count"],
                     "api_truncated": int(r["truncated"]), "api_prior_n_approx": prior_n, "api_prior_approx_flag": approx})
    return pd.DataFrame(rows)


def stage_analyze(B: int, mini: bool) -> dict:
    import analysis as A
    import frame
    h = check_hash()
    out_dir = mc.RESULTS / "mini" if mini else mc.RESULTS
    out_dir.mkdir(exist_ok=True)
    spec = json.loads((WS / "mech_spec.json").read_text())
    power = json.loads((WS / "mech_spec_power.json").read_text())
    G = mc.io_load.prepare()
    mc.config.load_sealed_ids()
    C = frame.Corpus(G)
    T = pd.read_parquet(FR / "targets.parquet")
    E = pd.read_parquet(FR / "entries.parquet")
    mc.config.assert_not_sealed(E.concept_id.unique())
    mA, sdA = float(E.A_cont.mean()), float(E.A_cont.std())
    res = {"label": mc.LABEL, "exposure_label": "corpus-exposure, coverage-limited", "mech_spec_sha256": h}
    frames = {}
    for nm, fn in [("primary", "strata_long.parquet"), ("expanded", "strata_long_expanded.parquet")]:
        L = pd.read_parquet(FR / fn)
        mc.config.assert_not_sealed(L.concept_id.unique())
        t = time.time()
        L = A.compute_exposures(G, C, L, T)
        L["cluster"] = L.concept_id
        L = A.add_design(L, sdA, mA)
        L["has_plac_stratum"] = L.groupby("stratum").has_plac.transform("max")
        L.to_parquet(out_dir / f"exposures_{nm}.parquet", index=False)
        frames[nm] = L
        logger.info(f"exposures {nm}: {len(L)} rows in {time.time() - t:.0f}s")
    L = frames["primary"]
    D = L[L.role.isin(["case", "control"])].copy()
    # ---------- M-i / M-ii / M-iii ----------
    t = time.time()
    blk = A.full_block(D, B, mc.SEED + 11)
    logger.info(f"primary model suite + bootstrap B={B} in {time.time() - t:.0f}s")
    res["descriptives"] = A.descriptives(D)
    res["enrichment"] = {k: blk["fits"][k] for k in ("m1", "m2", "m3", "m_neg_only", "m_plac", "m_plac_only", "m_swap",
                                                    "m_any_incl_c")}
    res["ratios"] = blk["ratios"]
    res["interaction"] = {"m_int": blk["fits"]["m_int"], **{f"m2_T{t_}": blk["fits"][f"m2_T{t_}"] for t_ in (1, 2, 3)},
                          "tercile_MDE": power["pairs"]["tercile"]}
    res["vocab_class"] = {"m_voc": blk["fits"]["m_voc"], "m_comp": blk["fits"]["m_comp"]}
    res["checks"] = {"statsmodels": A.statsmodels_check(D), "lpm_pyfixest": A.lpm_crosscheck(D)}
    pre = pd.read_parquet(FR / "risk_balance_pre.parquet")
    res["match_balance"] = A.balance(D, pre)
    m2 = blk["fits"]["m2"]["terms"]["E_any"]
    pce = res["descriptives"]["prev_case_E_any"]
    res["attributable_fraction_exposed"] = pce * (1 - 1 / m2["OR"]) if m2["OR"] else None
    # ---------- placebo / sanity ----------
    t = time.time()
    res["permutation"] = A.permutation_null(D, 50 if mini else 200, mc.SEED + 13)
    logger.info(f"permutation null in {time.time() - t:.0f}s")
    # ---------- supplementary ----------
    sup = {}
    Bs = max(B // 5, 50) if not mini else 20
    for nm, mask in [("field_Physics_Astro", D.field_group == "Physics/Astro"), ("field_CS", D.field_group == "CS"),
                     ("field_other", D.field_group == "other"), ("single_paper_entries", D.single_paper_entry),
                     ("multi_paper_entries", ~D.single_paper_entry)]:
        Ds = D[mask]
        if Ds.stratum.nunique() >= 30:
            f = A.fit_model(Ds, A.MODELS["m2"])
            bb = A.bootstrap(Ds, Bs, mc.SEED + 23)["m2"]
            sup[nm] = A.summarize_model("m2", f, bb)
        else:
            sup[nm] = {"n_strata": int(Ds.stratum.nunique()), "identified": False}
    D13 = L.copy()
    f = A.fit_model(D13, A.MODELS["m2"])
    sup["one_to_three_matched"] = A.summarize_model("m2", f, A.bootstrap(D13, Bs, mc.SEED + 29)["m2"])
    Lx = frames["expanded"]
    Dx = Lx[Lx.role.isin(["case", "control"])]
    f = A.fit_model(Dx, A.MODELS["m2"])
    sup["expanded_frame_no_concept_cap"] = A.summarize_model("m2", f, A.bootstrap(Dx, Bs, mc.SEED + 31)["m2"])
    sup["expanded_frame_no_concept_cap"]["descriptives"] = A.descriptives(Dx)
    fx = A.fit_model(Dx, A.MODELS["m_voc"])
    sup["expanded_vocab_class"] = A.summarize_model("m_voc", fx, None)
    fi = A.fit_model(Dx, A.MODELS["m_int"])
    sup["expanded_interaction"] = A.summarize_model("m_int", fi, None)
    fp = A.fit_model(Dx[Dx.has_plac_stratum == 1], A.MODELS["m_plac"])
    sup["expanded_placebo"] = A.summarize_model("m_plac", fp, None)
    ca_all = pd.read_parquet(FR / "cases_all.parquet")
    sup["career_new_share_all_adopter_pairs"] = float((ca_all.n_prior_corpus == 0).mean())
    sup["career_new_n_all_adopter_pairs"] = int((ca_all.n_prior_corpus == 0).sum())
    # API validation subsample
    api = api_exposure(T)
    if api is not None and len(api):
        Dm = D.merge(api, on=["stratum", "role"], how="inner")
        both = Dm.groupby("stratum").role.transform("count") == 2
        Dm = Dm[both]
        v = {"n_rows": int(len(Dm)), "n_strata": int(Dm.stratum.nunique()),
             "kappa_corpus_vs_api_E_any": A.kappa(Dm.E_any, Dm.api_E_any) if len(Dm) else None,
             "agree_share": float((Dm.E_any == Dm.api_E_any).mean()) if len(Dm) else None,
             "api_prev_case": float(Dm[Dm.case == 1].api_E_any.mean()) if len(Dm) else None,
             "api_prev_control": float(Dm[Dm.case == 0].api_E_any.mean()) if len(Dm) else None,
             "corpus_prev_case": float(Dm[Dm.case == 1].E_any.mean()) if len(Dm) else None,
             "corpus_prev_control": float(Dm[Dm.case == 0].E_any.mean()) if len(Dm) else None,
             "api_truncated_share": float(Dm.api_truncated.mean()) if len(Dm) else None,
             "api_share_exposed_corpus_unexposed": float(((Dm.api_E_any == 1) & (Dm.E_any == 0)).mean()) if len(Dm) else None}
        if len(Dm) and Dm.stratum.nunique() >= 20:
            Dm2 = Dm.assign(E_any=Dm.api_E_any, E_neg=Dm.api_E_neg)
            f = A.fit_model(Dm2, ["E_any", "E_neg", "lp"])
            v["api_m2"] = A.summarize_model("m2_api", f, A.bootstrap(Dm2, Bs, mc.SEED + 37)["m2"])
            Dm3 = Dm2[Dm2.api_truncated == 0]
            Dm3 = Dm3[Dm3.groupby("stratum").role.transform("count") == 2]
            if Dm3.stratum.nunique() >= 20:
                v["api_m2_nontruncated"] = A.summarize_model("m2_api_nt", A.fit_model(Dm3, ["E_any", "E_neg", "lp"]), None)
            pn = Dm.dropna(subset=["api_prior_n_approx"])
            if len(pn):
                v["spearman_corpus_prior_vs_api_prior"] = float(pn.n_prior_corpus.corr(pn.api_prior_n_approx,
                                                                                     method="spearman"))
                v["median_api_prior_n"] = float(pn.api_prior_n_approx.median())
                v["median_corpus_prior_n"] = float(pn.n_prior_corpus.median())
        sup["api_validation"] = v
    else:
        ar = mc.RESULTS / "api_results.json"
        info = json.loads(ar.read_text()) if ar.exists() else {}
        sup["api_validation"] = {"ran": False, "credits_spent": info.get("spent", 0),
                                 "keywide_remaining_at_start": info.get("remaining_start"),
                                 "stop_reason": info.get("stop_reason"),
                                 "note": "key-wide OpenAlex remaining was below the 2,500 reserve for G4/other "
                                         "iteration-4 agents, so the guard blocked every paid call; no API exposure, no "
                                         "kappa; corpus exposure is the only exposure measure"}
    res["supplementary"] = sup
    # ---------- M-iv mediation ----------
    t = time.time()
    med = A.mediation(E, 60 if mini else B, mc.SEED + 19, WORKERS)
    logger.info(f"mediation + bootstrap in {time.time() - t:.0f}s")
    # mediator validation: corpus control exposure prevalence per entry (controls + reserves)
    ctl = L[L.case == 0].groupby("entry_id").agg(n_ctl=("E_any", "size"), prev=("E_any", "mean"))
    ctl = ctl[ctl.n_ctl >= 3].join(E.set_index("entry_id")[["M2_share", "M2", "M1"]], how="inner")
    val = {"n_entries_ge3_controls": int(len(ctl)),
           "spearman_M2share_vs_control_prev": float(ctl.M2_share.corr(ctl.prev, method="spearman")) if len(ctl) > 5 else None,
           "spearman_M2_vs_M1_all": float(E.M2.corr(E.M1, method="spearman")),
           "spearman_M2share_vs_M1_all": float(E.M2_share.corr(E.M1, method="spearman")),
           "spearman_M2_vs_Acont": float(E.M2.corr(E.A_cont, method="spearman")),
           "spearman_M1_vs_Acont": float(E.M1.corr(E.A_cont, method="spearman"))}
    med["validation"] = val
    res["mediation"] = med
    res["power"] = power
    res["reading"] = reading(res, power)
    mc.dump(res, out_dir / "mechanism_results.json")
    write_tables(res, out_dir)
    import figs
    figs.run(res, D, out_dir if mini else mc.FIGS)
    write_eval_out(res, D, E, out_dir, mini)
    return res["reading"]


def stage_extra(B: int, mini: bool) -> None:
    """Supplementary (added after the mini run; NOT pre-declared): is partner enrichment reducible to prior activity in
    c's ORIGIN subfield (boundary-spanner / demic reading)? E_origin = >= 1 prior corpus work (<= e-1, non-c) whose
    subfield is o(c)."""
    import analysis as A
    import frame
    check_hash()
    out_dir = mc.RESULTS / "mini" if mini else mc.RESULTS
    res = json.loads((out_dir / "mechanism_results.json").read_text())
    G = mc.io_load.prepare()
    C = frame.Corpus(G)
    E = pd.read_parquet(FR / "entries.parquet").set_index("entry_id")
    crow = {}
    extra = {}
    for nm in ("primary", "expanded"):
        L = pd.read_parquet(out_dir / f"exposures_{nm}.parquet")
        eo = []
        for r in L.itertuples():
            cr = crow.setdefault(r.concept_id, set(G["links"][r.concept_id][0].tolist()))
            w = C.prior_rows(int(r.au), int(r.e), cr)
            o = E.loc[r.entry_id, "o"]
            eo.append(int(pd.notna(o) and bool((C.sub[w] == int(o)).any())) if len(w) else 0)
        L["E_origin"] = eo
        L.to_parquet(out_dir / f"exposures_{nm}.parquet", index=False)
        D = L[L.role.isin(["case", "control"])]
        blk = {}
        for mname, cols in [("origin_only", ["E_origin", "E_neg", "lp"]),
                            ("partner_given_origin", ["E_any", "E_origin", "E_neg", "lp"]),
                            ("voc_given_origin", ["E_nat", "E_adj", "E_for", "E_unprof", "E_origin", "E_neg", "lp"])]:
            f = A.fit_model(D, cols)
            bb = None
            if nm == "primary":
                bb = A.bootstrap_one(D, cols, 100 if mini else B, mc.SEED + 41)
            blk[mname] = A.summarize_model(mname, f, bb)
        blk["prev_case_E_origin"] = float(D[D.case == 1].E_origin.mean())
        blk["prev_control_E_origin"] = float(D[D.case == 0].E_origin.mean())
        blk["phi_E_any_E_origin"] = float(np.corrcoef(D.E_any, D.E_origin)[0, 1])
        extra[nm] = blk
    extra["note"] = "supplementary, added after inspecting the mini run (not pre-declared)"
    res["supplementary"]["origin_subfield_check"] = extra
    mc.dump(res, out_dir / "mechanism_results.json")
    logger.info(json.dumps({k: (v["partner_given_origin"]["terms"] if isinstance(v, dict) and "partner_given_origin" in v
                                else v) for k, v in extra.items()}, default=str)[:1500])


def stage_assemble(mini: bool) -> None:
    """Rebuild reading, tables, figures and eval_out.json from saved results (no refit)."""
    import figs
    check_hash()
    out_dir = mc.RESULTS / "mini" if mini else mc.RESULTS
    res = json.loads((out_dir / "mechanism_results.json").read_text())
    res["reading"] = reading(res, res["power"])
    mc.dump(res, out_dir / "mechanism_results.json")
    L = pd.read_parquet(out_dir / "exposures_primary.parquet")
    D = L[L.role.isin(["case", "control"])].copy()
    E = pd.read_parquet(FR / "entries.parquet")
    write_tables(res, out_dir)
    figs.run(res, D, out_dir if mini else mc.FIGS)
    write_eval_out(res, D, E, out_dir, mini)
    logger.info(res["reading"])


def _ci_excl(ci, side="above"):
    return ci is not None and np.isfinite(ci[0]) and ((ci[0] > 1) if side == "above" else (ci[1] < 1))


def reading(res: dict, power: dict) -> dict:
    t = res["enrichment"]["m2"]["terms"]
    ci = t["E_any"].get("OR_ci95_boot")
    rn = res["ratios"].get("partner_over_neg", {})
    rp = res["ratios"].get("partner_over_plac", {})
    plac = res["enrichment"]["m_plac"]["terms"].get("E_plac", {}) if res["enrichment"]["m_plac"].get("terms") else {}
    neg = t.get("E_neg", {})
    plac_sig = _ci_excl(plac.get("OR_ci95_boot")) or _ci_excl(plac.get("OR_ci95_boot"), "below")
    neg_sig = _ci_excl(neg.get("OR_ci95_boot")) or _ci_excl(neg.get("OR_ci95_boot"), "below")
    p0 = res["descriptives"]["prev_control_E_any"]
    grid = [0.1, 0.25, 0.4, 0.6]
    pk = min(grid, key=lambda g: abs(g - p0))
    mde = power["pairs"]["MDE80"].get(f"OR_p0_{pk}")
    primary_pos = _ci_excl(ci)
    ratio_neg_pos = _ci_excl(rn.get("ci95_boot"))
    ratio_plac_pos = _ci_excl(rp.get("ci95_boot"))
    if primary_pos and ratio_neg_pos and (ratio_plac_pos or not plac_sig):
        verdict = "SUPPORT"
    elif primary_pos and not ratio_plac_pos and plac_sig:
        verdict = "GENERIC-HOST-VOCABULARY"
    elif (not ratio_neg_pos) and neg_sig:
        verdict = "ACTIVITY-ARTEFACT"
    elif not primary_pos:
        verdict = "NULL" if (mde is not None and mde <= 1.30) else "UNDERPOWERED"
    else:
        verdict = "PARTIAL (primary OR > 1 but specificity criteria not all met)"
    it = res["interaction"]["m_int"]["terms"].get("E_any_x_zA", {})
    ici = it.get("OR_ci95_boot")
    inter = ("positive: interface matters more when partners are host-native" if _ci_excl(ici) else
             "negative: in low-A entries only boundary-spanning exposed authors adopt" if _ci_excl(ici, "below") else
             "null: enrichment uniform across A_cont")
    mb = res["mediation"]["boot"].get("att_M2", {})
    att = res["mediation"]["point"]["att"].get("att_M2")
    mci = mb.get("ci95", [np.nan, np.nan])
    med = ("A_cont acts partly through the size of the pre-exposed host pool" if (att is not None and att >= 0.3 and
                                                                               np.isfinite(mci[0]) and mci[0] > 0)
           else "A_cont is not reducible to pool size (M2) [lower bound under mediator noise]" if (np.isfinite(mci[0]) and mci[0] <= 0 <= mci[1])
           else "attenuation CI excludes 0 but point < 30%: partial pool-size channel")
    vn = res["ratios"].get("native_vs_foreign", {})
    va = res["ratios"].get("adjacent_vs_foreign", {})
    voc_nat = vn.get("log_contrast_ci95")
    voc_adj = va.get("log_contrast_ci95")
    vt = res["vocab_class"]["m_voc"]["terms"]
    nat_ci = vt.get("E_nat", {}).get("OR_ci95_boot")
    if voc_nat and np.isfinite(voc_nat[0]) and voc_nat[0] > 0:
        voc = "grafting reading (NATIVE > FOREIGN)"
    elif voc_adj and np.isfinite(voc_adj[0]) and voc_adj[0] > 0 and not _ci_excl(nat_ci):
        voc = "host-adjacent re-contextualisation reading (ADJACENT > FOREIGN, NATIVE n.s.)"
    elif voc_nat and np.isfinite(voc_nat[1]) and voc_nat[1] < 0:
        voc = ("FOREIGN > NATIVE (CI excludes 0): origin-vocabulary / boundary-spanner reading - NOT a pre-declared "
               "label, reported as-is; contradicts the grafting reading at the adopter level")
    else:
        voc = "no class contrast resolved (CIs include 0)"
    return {"verdict": verdict, "interaction": inter, "mediation": med, "vocabulary": voc,
            "MDE80_primary_at_p0": {"p0_observed": p0, "grid_point": pk, "MDE80": mde},
            "criteria": {"primary_CI_excludes_1_above": primary_pos, "ratio_neg_CI_excludes_1_above": ratio_neg_pos,
                         "ratio_plac_CI_excludes_1_above": ratio_plac_pos, "OR_plac_significant": plac_sig,
                         "OR_neg_significant": neg_sig},
            "label": mc.LABEL, "exposure_label": "corpus-exposure, coverage-limited"}


def write_tables(res: dict, out: Path) -> None:
    rows = []
    for grp in ("enrichment", "interaction", "vocab_class"):
        for mname, m in res[grp].items():
            if not isinstance(m, dict) or "terms" not in m:
                continue
            for term, v in m["terms"].items():
                ci = v.get("OR_ci95_boot") or [None, None]
                rows.append({"group": grp, "model": mname, "term": term, "OR": v["OR"], "ci_lo": ci[0], "ci_hi": ci[1],
                             "p_boot": v.get("p_boot"), "p_crv": v["p_crv"], "p_model": v["p_model"],
                             "n_strata": m["n_strata"]})
    pd.DataFrame(rows).to_csv(out / "model_terms.csv", index=False)
    for k in ("enrichment", "interaction", "vocab_class", "mediation", "match_balance", "permutation", "ratios",
              "supplementary"):
        mc.dump(res[k], out / f"{k}.json")


def write_eval_out(res: dict, D: pd.DataFrame, E: pd.DataFrame, out: Path, mini: bool) -> None:
    M = {}

    def put(k, v):
        k = re.sub(r"[^A-Za-z0-9_]", "_", k)
        if v is None:
            return
        try:
            f = float(v)
        except (TypeError, ValueError):
            return
        if np.isfinite(f):
            M[k] = f
    ds = res["descriptives"]
    for k, v in ds.items():
        put(k, v)
    for mname, m in {**res["enrichment"], **{k: v for k, v in res["interaction"].items() if k != "tercile_MDE"},
                     **res["vocab_class"]}.items():
        for term, v in (m.get("terms") or {}).items():
            base = f"{mname}_{term}"
            put(f"{base}_OR", v["OR"])
            ci = v.get("OR_ci95_boot")
            if ci:
                put(f"{base}_OR_ci_lo", ci[0])
                put(f"{base}_OR_ci_hi", ci[1])
            put(f"{base}_p_boot", v.get("p_boot"))
            put(f"{base}_p_crv", v["p_crv"])
        put(f"{mname}_n_strata", m.get("n_strata"))
    for rname, r in res["ratios"].items():
        put(f"ratio_{rname}", r["ratio"])
        if r.get("ci95_boot"):
            put(f"ratio_{rname}_ci_lo", r["ci95_boot"][0])
            put(f"ratio_{rname}_ci_hi", r["ci95_boot"][1])
        put(f"ratio_{rname}_p_boot", r["p_boot"])
    for k, v in res["match_balance"].items():
        put(f"balance_{k}", v)
    put("attributable_fraction_exposed", res["attributable_fraction_exposed"])
    put("permutation_mean_OR", res["permutation"]["mean_OR"])
    put("permutation_q025_OR", res["permutation"]["q025_OR"])
    put("permutation_q975_OR", res["permutation"]["q975_OR"])
    put("statsmodels_max_abs_diff", res["checks"]["statsmodels"]["max_abs_diff"])
    for k, v in res["checks"]["lpm_pyfixest"].items():
        put(f"lpm_{k}", v)
    med = res["mediation"]
    for k, v in med["point"]["att"].items():
        put(f"med_{k}", v)
    for k, v in med["boot"].items():
        put(f"med_boot_{k}_ci_lo", v["ci95"][0])
        put(f"med_boot_{k}_ci_hi", v["ci95"][1])
        put(f"med_boot_{k}_p", v["p_boot_vs0"])
    for mname, m in med["point"]["models"].items():
        for term, v in ((m or {}).get("terms") or {}).items():
            put(f"med_{mname}_{term}_irr_sd", v["irr_sd"])
            put(f"med_{mname}_{term}_p", v["p"])
    for k, v in med["point"]["gelbach_M2_split"].items():
        put(f"gelbach_{k}_share", v["share_of_b_base"])
    for k, v in med["validation"].items():
        put(f"medval_{k}", v)
    pw = res["power"]
    for k, v in pw["pairs"]["MDE80"].items():
        put(f"MDE80_{k}", v)
    put("MDE80_mediation_share", pw["mediation"]["MDE80_share"])
    sup = res["supplementary"]
    for nm, s in sup.items():
        if isinstance(s, dict) and "terms" in s:
            for term in ("E_any", "E_neg"):
                if term in s["terms"]:
                    put(f"sup_{nm}_{term}_OR", s["terms"][term]["OR"])
                    ci = s["terms"][term].get("OR_ci95_boot")
                    if ci:
                        put(f"sup_{nm}_{term}_OR_ci_lo", ci[0])
                        put(f"sup_{nm}_{term}_OR_ci_hi", ci[1])
            put(f"sup_{nm}_n_strata", s.get("n_strata"))
        elif not isinstance(s, dict):
            put(f"sup_{nm}", s)
    for fr, blk in (sup.get("origin_subfield_check") or {}).items():
        if not isinstance(blk, dict):
            continue
        for mname, m in blk.items():
            if isinstance(m, dict) and "terms" in m:
                for term, v in m["terms"].items():
                    if term == "lp":
                        continue
                    put(f"origin_{fr}_{mname}_{term}_OR", v["OR"])
                    ci = v.get("OR_ci95_boot")
                    if ci:
                        put(f"origin_{fr}_{mname}_{term}_OR_ci_lo", ci[0])
                        put(f"origin_{fr}_{mname}_{term}_OR_ci_hi", ci[1])
            else:
                put(f"origin_{fr}_{mname}", m)
    for k, v in sup.get("api_validation", {}).items():
        if not isinstance(v, dict):
            put(f"api_{k}", v)
        elif "terms" in v:
            put(f"api_{k}_E_any_OR", v["terms"]["E_any"]["OR"])
    fs = json.loads((mc.RESULTS / "frame_summary.json").read_text())["primary"]
    for k, v in fs["adopters"].items():
        put(f"frame_{k}", v)
    put("gate_b_A", json.loads((mc.RESULTS / "gate.json").read_text())["b_A"])
    rd = res["reading"]
    code = {"SUPPORT": 1, "GENERIC-HOST-VOCABULARY": 2, "ACTIVITY-ARTEFACT": 3, "NULL": 4, "UNDERPOWERED": 5}
    put("reading_verdict_code", code.get(rd["verdict"], 0))
    # datasets
    ex1 = []
    for r in D.sort_values(["stratum", "case"], ascending=[True, False]).itertuples():
        inp = {"entry_id": r.entry_id, "A_tercile": int(r.A_tercile), "stratum": int(r.stratum), "d": int(r.d),
               "e": int(r.e), "adoption_year": int(r.Y), "author": f"A{int(r.raw_author_id)}"}
        ex1.append({"input": json.dumps(inp), "output": str(int(r.case)),
                    "metadata_role": r.role, "metadata_concept_id": r.concept_id, "metadata_field_group": r.field_group,
                    "metadata_relax_level": int(r.relax), "metadata_exposure_source": "corpus (coverage-limited)",
                    "eval_E_any": float(r.E_any), "eval_E_w": float(r.E_w), "eval_E_neg": float(r.E_neg),
                    "eval_E_plac": float(r.E_plac), "eval_E_nat": float(r.E_nat), "eval_E_adj": float(r.E_adj),
                    "eval_E_for": float(r.E_for), "eval_E_unprof": float(r.E_unprof), "eval_E_comp": float(r.E_comp),
                    "eval_log1p_prior_corpus": float(r.lp), "eval_A_cont": float(r.A_cont)})
    ex2 = []
    for r in E.itertuples():
        inp = {"entry_id": r.entry_id, "concept_id": r.concept_id, "d": int(r.d), "e": int(r.e),
               "A_tercile": int(r.A_tercile)}
        ex2.append({"input": json.dumps(inp), "output": str(int(r.Y_strict)), "metadata_n_entry_papers": int(r.n_entry_papers),
                    "eval_A_cont": float(r.A_cont), "eval_CT": float(r.CT), "eval_M2": float(r.M2),
                    "eval_M2_share": float(r.M2_share), "eval_M2_native": float(r.M2_native),
                    "eval_M2_adjacent": float(r.M2_adjacent), "eval_M1": float(r.M1),
                    "eval_n_host_authors_pre": float(r.n_host_authors_pre), "eval_Y_strict": float(r.Y_strict)})
    o = {"metadata": {"evaluation_name": "adopter-level absorptive-capacity test of the D2 host-share effect",
                      "label": mc.LABEL, "exposure_label": "corpus-exposure, coverage-limited",
                      "reading": rd, "mech_spec_sha256": res["mech_spec_sha256"],
                      "depends_on": ["art_2Cd2JJypeGuA", "art_eR1Z7fMlOcxs"],
                      "notes": "metrics_agg keys: m<model>_<term>_OR / _OR_ci_lo/_hi (concept-cluster bootstrap) / "
                               "_p_boot / _p_crv; ratio_*; med_* (entry-level PPML attenuation); MDE80_*; sup_*; api_*"},
         "metrics_agg": M,
         "datasets": [{"dataset": "adopter_case_control_strata_primary", "examples": ex1},
                      {"dataset": "coprimary_entries_mediators", "examples": ex2}]}
    name = "eval_out_mini_run.json" if mini else "eval_out.json"
    (WS / name if not mini else out / name).write_text(json.dumps(o, indent=1))
    logger.info(f"wrote {name}: {len(M)} metrics, {len(ex1)} + {len(ex2)} examples")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "prepare", "frame", "freeze", "pull", "analyze",
                                                       "assemble", "extra"])
    ap.add_argument("--B", type=int, default=1000)
    ap.add_argument("--mini", action="store_true")
    ap.add_argument("--pull-mini", type=int, default=None)
    a = ap.parse_args()
    mc.config.set_ram_limit(24)
    stages = ["prepare", "frame", "freeze", "pull", "analyze"] if a.stage == "all" else [a.stage]
    timings = {}
    for st in stages:
        t = time.time()
        if st == "prepare":
            stage_prepare()
        elif st == "frame":
            logger.info(stage_frame())
        elif st == "freeze":
            stage_freeze(a.mini)
        elif st == "pull":
            logger.info(stage_pull(a.pull_mini))
        elif st == "analyze":
            logger.info(stage_analyze(20 if a.mini else a.B, a.mini))
        elif st == "extra":
            stage_extra(a.B, a.mini)
        elif st == "assemble":
            stage_assemble(a.mini)
        timings[st] = round(time.time() - t, 1)
        logger.info(f"stage {st} done in {timings[st]}s")
    tp = mc.LOGS / "timings.json"
    try:
        prev = json.loads(tp.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        prev = {}
    prev.update(timings)
    tp.write_text(json.dumps(prev, indent=1))


if __name__ == "__main__":
    main()
