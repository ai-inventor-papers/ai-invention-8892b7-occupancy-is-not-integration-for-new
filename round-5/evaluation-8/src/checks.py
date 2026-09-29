#!/usr/bin/env python3
"""Tier-C recomputations from row-level files, decision-rule re-application
(verdicts) and text assertions for the numbers-of-record audit."""
from __future__ import annotations

import math
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from audit_core import RUN_ROOT, load_csv, load_json, get_by_key
from registry import P2, P3, P3T, P4, P5, P5X, P6X, P7, P8, P9, P1E

Z = 1.959963984540054


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * pvals[i]))
        adj[i] = run
    return adj


def ivw(est: list[float], se: list[float]) -> dict:
    w = np.array([1 / s ** 2 for s in se])
    e = np.array(est)
    m = float((w * e).sum() / w.sum())
    s = float(math.sqrt(1 / w.sum()))
    q = float((w * (e - m) ** 2).sum())
    i2 = max(0.0, (q - (len(e) - 1)) / q) if q > 0 else 0.0
    return dict(est=m, se=s, lo=m - Z * s, hi=m + Z * s, Q=q, I2=i2)


def _rob() -> pd.DataFrame:
    return pd.read_csv(RUN_ROOT / P7 / "d2_robustness.csv")


def _rob_sel(excl: bool) -> pd.DataFrame:
    d = _rob()
    d = d[(d.fe == "secondary") & d.irr_sd_A.notna()]
    if excl:
        d = d[(d.spec != "PRIMARY (MAIN)") & ~d.spec.str.contains("stratum", case=False)]
    return d


def _sig(d: pd.DataFrame) -> pd.Series:
    return (d.irr_sd_A_lo > 1) & (d.p_A < 0.05)


@lru_cache(maxsize=1)
def _exposures() -> pd.DataFrame:
    x = pd.read_parquet(RUN_ROOT / P5 / "exposures_primary.parquet", columns=["stratum", "case", "role", "E_any"])
    return x[x.role.isin(["case", "control"])]  # the 1:1 primary strata (reserve controls are for the 1:3 robustness row)


def _case_diff(concept_phrase: str) -> float:
    rows = [r for r in load_csv(P4 + "/case_entries.csv") if r["phrase"] == concept_phrase and r["in_coprimary_sample"] == "True"]
    rooted = [float(r["A_cont"]) for r in rows if r["EST_bin"] == "1"]
    un = [float(r["A_cont"]) for r in rows if r["EST_bin"] != "1"]
    return float(np.mean(rooted) - np.mean(un))


def _ll_count(path: str, cat: str) -> float:
    rows = load_csv(path)
    return float(sum(1 for r in rows if r["category"] == cat))


def _ivw_main_mesh() -> dict:
    s = load_json(P7 + "/d2_summary.json")["coprimary_fe_concept_plus_e_plus_d"]["A_cont"]
    g = load_json(P9 + "/g4_summary.json")["R2"]
    ests, ses = [], []
    for irr, lo, hi in [(s["irr_per_sd"], *s["irr_per_sd_ci95"]), (g["irr_sd"], *g["ci"])]:
        ests.append(math.log(irr))
        ses.append((math.log(hi) - math.log(lo)) / (2 * Z))
    r = ivw(ests, ses)
    return dict(est=math.exp(r["est"]), lo=math.exp(r["lo"]), hi=math.exp(r["hi"]), I2=r["I2"], Q=r["Q"])


def _holm_rq1(row: str) -> float:
    rows = load_csv(P3T + "/r1_holm_decisions.csv")
    names = [r["row"] for r in rows]
    adj = holm([float(r["p_one"]) for r in rows])
    return adj[names.index(row)]


def _es(row: str, col: str) -> float:
    return float(get_by_key(P3T + "/r1_event_study_screen_vs_heldout.csv", f"csv:row={row}|{col}"))


def _mainpop() -> list[dict]:
    return load_json("3_invention_loop/iter_3/gen_art/gen_art_experiment_5/results/main_population_hydrated.json")["concepts"]


def _single_all_screen() -> float:
    ev = pd.read_parquet(RUN_ROOT / P7 / "screen_events_with_outcomes.parquet", columns=["fold", "MAIN", "kw5", "n_entry_papers"])
    ev = ev[(ev.fold == "screen") & ev.MAIN & ev.kw5]
    return float((ev.n_entry_papers == 1).mean())


RECOMPUTE = {
    "n_frame_concepts": lambda: float(len(_mainpop())),
    "n_main_screen": lambda: float(sum(1 for c in _mainpop() if c.get("MAIN") and c.get("fold") == "screen")),
    "n_main_heldout": lambda: float(sum(1 for c in _mainpop() if c.get("MAIN") and c.get("fold") == "heldout")),
    "single_paper_share_all_screen_kw5": _single_all_screen,
    "holm_screen_coprimary": lambda: holm([load_json(P7 + "/d2_summary.json")["coprimary_fe_concept_plus_e_plus_d"]["A_cont"]["p_crv1"],
                                           load_json(P7 + "/d2_summary.json")["coprimary_fe_concept_plus_e_plus_d"]["CT"]["p_crv1"]])[0],
    "screen_primary_retained": lambda: float(_rob().query("spec=='PRIMARY (MAIN)' and fe=='primary'").N.iloc[0]) /
                                       float(_rob().query("spec=='PRIMARY (MAIN)' and fe=='primary'").N_input.iloc[0]),
    "robust_sig_incl": lambda: float(_sig(_rob_sel(False)).sum()),
    "robust_rows_incl": lambda: float(len(_rob_sel(False))),
    "robust_sig_excl": lambda: float(_sig(_rob_sel(True)).sum()),
    "robust_irr_min": lambda: float(_rob_sel(True)[_sig(_rob_sel(True))].irr_sd_A.min()),
    "single_paper_share_coprimary": lambda: 1 - float(_rob().query("spec=='exclude n_entry_papers == 1' and fe=='secondary'").N.iloc[0]) /
                                           float(_rob().query("spec=='PRIMARY (MAIN)' and fe=='secondary'").N.iloc[0]),
    "single_paper_n_coprimary": lambda: float(_rob().query("spec=='PRIMARY (MAIN)' and fe=='secondary'").N.iloc[0]) -
                                        float(_rob().query("spec=='exclude n_entry_papers == 1' and fe=='secondary'").N.iloc[0]),
    "holm_heldout_coprimary": lambda: holm([load_json(P2 + "/heldout_post.json")["flags"]["secondary"]["p_A"],
                                            load_json(P2 + "/heldout_post.json")["flags"]["secondary"]["p_CT"]])[0],
    "heldout_robust_sig": lambda: float(sum(1 for r in load_csv(P2 + "/heldout_robustness.csv")
                                            if r["fe"] == "secondary" and "stratum" not in r["spec"] and r["irr_sd_A_lo"]
                                            and float(r["irr_sd_A_lo"]) > 1 and float(r["p_A"]) < 0.05)),
    "holm_mesh_R1": lambda: holm([load_json(P9 + "/g4_summary.json")["R1"]["p_crv1"], load_json(P9 + "/g4_summary.json")["R1"]["CT_p"]])[0],
    "holm_mesh_R2": lambda: holm([load_json(P9 + "/g4_summary.json")["R2"]["p_crv1"], load_json(P9 + "/g4_summary.json")["R2"]["CT_p"]])[0],
    "ivw_main_mesh": lambda: _ivw_main_mesh()["est"],
    "ivw_main_mesh_lo": lambda: _ivw_main_mesh()["lo"],
    "ivw_main_mesh_hi": lambda: _ivw_main_mesh()["hi"],
    "ivw_main_mesh_i2": lambda: _ivw_main_mesh()["I2"],
    "holm_rq1_closure": lambda: _holm_rq1("closure"),
    "holm_rq1_closure_resT": lambda: _holm_rq1("closure_resT"),
    "holm_rq1_closure_persist": lambda: _holm_rq1("closure_persist"),
    "ivw_rq1_closure": lambda: ivw([_es("closure", "S_screen"), _es("closure", "S_heldout")],
                                   [float(get_by_key(P3T + "/r1_iv_synthesis_descriptive.csv", "csv:row=closure|se_screen")),
                                    float(get_by_key(P3T + "/r1_iv_synthesis_descriptive.csv", "csv:row=closure|se_heldout"))])["est"],
    "rq1_smd_flag_count": lambda: float(sum(1 for r in load_csv(P3T + "/r1_balance_smd.csv") if r["flag_abs_gt_0_25"] == "True")),
    "rq1_retained_heldout": lambda: abs(_es("closure_resT", "S_heldout")) / abs(_es("closure", "S_heldout")),
    "rq1_retained_screen": lambda: abs(_es("closure_resT", "S_screen")) / abs(_es("closure", "S_screen")),
    "leadlag_share_both_pooled": lambda: float(get_by_key(P4 + "/leadlag_denominator_table.csv", "csv:population=pooled_main|n_both")) /
                                         float(get_by_key(P4 + "/leadlag_denominator_table.csv", "csv:population=pooled_main|n")),
    "case_diff_wireless": lambda: _case_diff("wireless backhaul"),
    "case_diff_epr": lambda: _case_diff(next(r["phrase"] for r in load_csv(P4 + "/case_entries.csv") if "steering" in r["phrase"].lower())),
    "adopter_prev_case": lambda: float(_exposures().query("case==1").E_any.mean()),
    "adopter_prev_ctrl": lambda: float(_exposures().query("case==0").E_any.mean()),
    "adopter_rr": lambda: float(_exposures().query("case==1").E_any.mean()) / float(_exposures().query("case==0").E_any.mean()),
}
for _pop, _path in [("screen", P8 + "/leadlag_by_concept.csv"), ("mesh", P4 + "/mesh/mesh_leadlag_by_concept.csv")]:
    for _cat in ["neither", "diffusion_only", "expansion_only", "expansion_first", "same_year", "diffusion_first"]:
        RECOMPUTE[f"leadlag_{_pop}_n_{_cat}"] = (lambda p=_path, c=_cat: _ll_count(p, c))


# ============================================================ decision rules (verbatim quotes are located in gen_strat files)
STRAT = {
    2: "3_invention_loop/iter_2/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json",
    3: "3_invention_loop/iter_3/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json",
    4: "3_invention_loop/iter_4/gen_strat/gen_strat_1/.terminal_claude_agent_struct_out.json",
}


@lru_cache(maxsize=8)
def strat_text(it: int) -> str:
    import json
    return json.dumps(load_json(STRAT[it]), ensure_ascii=False)


def quote(it: int, start: str, end_marker: str | None = None, maxlen: int = 900) -> str:
    """Return the verbatim rule text from the gen_strat file (JSON-escaped text as stored)."""
    s = strat_text(it)
    i = s.find(start)
    if i < 0:
        return ""
    j = s.find(end_marker, i + len(start)) if end_marker else -1
    seg = s[i:(j + len(end_marker)) if j > 0 else i + maxlen]
    return seg.replace('\\"', '"')


def _pp(row: str, col: str) -> float:
    return float(get_by_key(P3T + "/r1_pooled_panel_screen_vs_heldout.csv", f"csv:row={row}|{col}"))


def verdict_rules() -> list[dict]:
    """Each rule: iteration, name, verbatim quote, outcome computed from audited numbers, report statement check."""
    hp = load_json(P2 + "/heldout_post.json")["flags"]["secondary"]
    ml = load_json(P2 + "/mechanism_label.json")["inputs"]
    g4 = load_json(P9 + "/g4_summary.json")
    d3 = {r["fold"]: r for r in load_csv(P3 + "/d3/d3_table.csv") if r["analysis"] == "primary"}
    dr = load_json(P1E + "/decision_rules.json")
    r5 = load_json(P5X + "/results_summary.json")["headline"]["rows"]
    out = []

    # ---- iteration 2 rules (a)-(d)
    out.append(dict(it=2, rule="(a) Gate A -> graft fallback",
                    quote=quote(2, "(a) If Gate A FAILS", "alternate."),
                    outcome="TRIGGERED" if dr["a"]["value"] < 0.5 else "NOT TRIGGERED",
                    inputs=f"within-host share>=0.40 on {dr['a']['value']:.4f} of edge-years (<0.5 => Gate A FAIL)",
                    src=P1E + "/decision_rules.json::a/value", report_regex=r"\(a\) Gate A → graft fallback \| (TRIGGERED)", report_hint=343))
    out.append(dict(it=2, rule="(b) H1 pilot-only if < ~150 concepts carry a tested edge",
                    quote=quote(2, "(b) H1 runs on the grounded", "25%."),
                    outcome="YES" if dr["b"]["realised_N_c"] < 150 else "NO",
                    inputs=f"N_c = {dr['b']['realised_N_c']}", src=P1E + "/decision_rules.json::b/realised_N_c",
                    report_regex=r"\(b\) H1 pilot-only \| (YES)", report_hint=344))
    out.append(dict(it=2, rule="(c) RQ1 CONFIRMED conditions",
                    quote=quote(2, "(c) RQ1 counts as CONFIRMED", "disguise."),
                    outcome="NOT MET" if str(dr["c"]["verdict"]).startswith("NOT MET") else "MET",
                    inputs=str(dr["c"]["verdict"])[:160], src=P1E + "/decision_rules.json::c/verdict",
                    report_regex=r"\(c\) RQ1 confirmed \| (NOT MET)", report_hint=345))
    out.append(dict(it=2, rule="(d) held-out untouched",
                    quote=quote(2, "(d) The held-out sha1 fold", "iteration."),
                    outcome="SEALED" if str(dr["d"]["verdict"]).startswith("SEALED") else "BREACHED",
                    inputs=str(dr["d"]["verdict"])[:160], src=P1E + "/decision_rules.json::d/verdict",
                    report_regex=r"\(d\) Held-out sealed \| (YES)", report_hint=346, equiv={"SEALED": "YES"}))
    # ---- iteration 3 rules
    sraw, sres = r5["closure"]["S"], r5["closure_resT"]["S"]
    res_ci = r5["closure_resT"]["ci"]
    per, con = r5["closure_persist"], r5["constraint"]
    brok = (sres < 0 and res_ci[1] < 0 and abs(sres) >= 0.5 * abs(sraw) and per["S"] < 0 and con["S"] < 0
            and (per["ci"][1] < 0 or con["ci"][1] < 0))
    turn = (res_ci[0] <= 0 <= res_ci[1]) and abs(sres) < 0.5 * abs(sraw) and (per["ci"][0] <= 0 <= per["ci"][1])
    out.append(dict(it=3, rule="R1 mechanical verdict (BROKERAGE / TURNOVER / MIXED) on the screen",
                    quote=quote(3, "PRE-DECLARED VERDICT, to be applied mechanically", "null. "),
                    outcome="BROKERAGE" if brok else ("TURNOVER" if turn else "MIXED"),
                    inputs=f"S_raw {sraw:.3f}, S_res {sres:.3f} CI [{res_ci[0]:.3f},{res_ci[1]:.3f}], S_persist {per['S']:.3f}, S_constraint {con['S']:.3f}",
                    src=P5X + "/results_summary.json::headline/rows", report_regex=r"\*\*Mechanical verdict: (MIXED)", report_hint=428))
    d1 = load_json(P6X + "/d1/verdict.json") if (RUN_ROOT / P6X / "d1/verdict.json").exists() else {}
    d1_ok = str(d1.get("verdict", d1.get("screen_verdict", ""))).upper()
    out.append(dict(it=3, rule="D1 SUPPORTED on the screen",
                    quote=quote(3, "PRE-DECLARED RULE: D1 SUPPORTED", "that outcome."),
                    outcome="NOT SUPPORTED" if ("NOT" in d1_ok or "FAIL" in d1_ok or d1_ok == "") else "SUPPORTED",
                    inputs=f"exp_6 d1/verdict.json verdict = {d1_ok[:80]}", src=P6X + "/d1/verdict.json::verdict",
                    report_regex=r"\*\*Result: breadth prediction (not supported)", report_hint=455, equiv={"NOT SUPPORTED": "not supported"}))
    out.append(dict(it=3, rule="(i) a claim that fails on the sealed fold is dead (iteration-4 rule, fixed in iteration 3)",
                    quote=quote(3, "DECISION RULES FOR ITERATION 4, fixed now: (i)", "search."),
                    outcome="R1 raw closure DEAD on held-out" if _holm_rq1("closure") >= 0.05 else "R1 raw closure alive",
                    inputs=f"held-out pooled-panel closure Holm p {_holm_rq1('closure'):.3f}", src=P3T + "/r1_holm_decisions.csv::closure",
                    report_regex=r"(Closure not confirmed on held-out for the primary measure)", report_hint=843,
                    equiv={"R1 raw closure DEAD on held-out": "Closure not confirmed on held-out for the primary measure"}))
    # ---- iteration 4 rules (paper decision rules)
    dead = hp["ci_A"][0] <= 1 <= hp["ci_A"][1] or hp["irr_sd_A"] < 1
    out.append(dict(it=4, rule="D2 DEAD if held-out co-primary CI includes 1 or sign reverses",
                    quote=quote(4, "D2 is DEAD if the held-out co-primary CI includes 1", "distinction as a measured dissociation."),
                    outcome="DEAD" if dead else "NOT DEAD (GRAFTING confirmed)",
                    inputs=f"held-out co-primary {hp['irr_sd_A']:.3f} [{hp['ci_A'][0]:.3f}, {hp['ci_A'][1]:.3f}]",
                    src=P2 + "/heldout_post.json::flags/secondary", report_regex=r"\| Held-out \| 1\.19 \|.*\| (GRAFTING confirmed) \|", report_hint=641,
                    equiv={"NOT DEAD (GRAFTING confirmed)": "GRAFTING confirmed"}))
    art = (ml["G1_multi_irr_sd"] < 1.10 and ml["G1_multi_ci"][0] <= 1) and ml["G1_mde_pooled_projected"] <= 1.20 and ml["G3_combined_pct_logirr_removed"] > 50
    label = "artefact" if art else ("host-vocabulary" if "host-vocabulary" in ml["G2a_reading"] else "grafting")
    out.append(dict(it=4, rule="Mechanism label (artefact / grafting / host-vocabulary)",
                    quote=quote(4, "Mechanism label: 'artefact'", "by G2."),
                    outcome=label, inputs=f"G1 multi {ml['G1_multi_irr_sd']:.3f} CI [{ml['G1_multi_ci'][0]:.3f},{ml['G1_multi_ci'][1]:.3f}], "
                                              f"MDE {ml['G1_mde_pooled_projected']}, G3 {ml['G3_combined_pct_logirr_removed']:.1f}%, G2a {ml['G2a_reading']}",
                    src=P2 + "/mechanism_label.json::inputs", report_regex=r"pooled mechanism label is \*\*(host-vocabulary)\*\*", report_hint=690))
    r2 = g4["R2"]
    rep_ok = r2["ci"][0] > 1 and holm([r2["p_crv1"], r2["CT_p"]])[0] < 0.05
    out.append(dict(it=4, rule="G4 success = second-family replication; failure = stated boundary",
                    quote=quote(4, "G4 success = second-family replication", "pool."),
                    outcome="REPLICATED" if rep_ok else "NOT REPLICATED", inputs=f"MeSH R2 {r2['irr_sd']:.3f} [{r2['ci'][0]:.3f},{r2['ci'][1]:.3f}]",
                    src=P9 + "/g4_summary.json::R2", report_regex=r"\*\*Verdict: (REPLICATED)\.\*\*", report_hint=707))
    r1_dead = _holm_rq1("closure") >= 0.05 or _pp("closure", "ci_heldout_hi") >= 0
    out.append(dict(it=4, rule="R1 dead if the pooled-panel held-out row fails",
                    quote=quote(4, "R1 is dead if the pooled-panel held-out row fails", "correlates'."),
                    outcome="R1_DEAD" if r1_dead else "R1_ALIVE",
                    inputs=f"pooled-panel held-out closure {_pp('closure', 'coef_heldout'):.3f} [{_pp('closure', 'ci_heldout_lo'):.3f}, {_pp('closure', 'ci_heldout_hi'):.3f}], Holm {_holm_rq1('closure'):.3f}",
                    src=P3T + "/r1_holm_decisions.csv::closure", report_regex=r"(R1_DEAD|volume/churn correlates)", report_hint=7,
                    rescue_lines=[(7, r"emerging concepts have lower persistent-neighbour triadic closure"),
                                  (867, r"\*\*Emergence question: closure is not confirmed on the primary measure; persistent-neighbour closure survives")]))
    d3null = all(float(d3[f]["ci_lo"]) <= 0 <= float(d3[f]["ci_hi"]) for f in ("screen", "heldout"))
    out.append(dict(it=4, rule="D3 null drops the unifying sentence",
                    quote=quote(4, "D3 null drops the unifying sentence", "."),
                    outcome="NULL (drop unifying sentence)" if d3null else "LINK",
                    inputs=f"screen {float(d3['screen']['partial_rho']):+.3f}, held-out {float(d3['heldout']['partial_rho']):+.3f}",
                    src=P3 + "/d3/d3_table.csv::primary", report_regex=r"\*\*Verdict: (NULL)\.\*\*", report_hint=756,
                    equiv={"NULL (drop unifying sentence)": "NULL"}))
    # ---- rules never written down in a gen_strat file
    out.append(dict(it=3, rule="Typology held-out expectations E1-E5 (pass/fail thresholds)",
                    quote="", outcome="RULE_NOT_RECORDED", inputs="thresholds live only in art_QKsLguxnGFQT sealed/heldout_spec.json, not in any gen_strat decision-rule text",
                    src="3_invention_loop/iter_3/gen_art/gen_art_experiment_8/sealed/heldout_spec.json", report_regex=None, report_hint=785))
    return out


# ============================================================ text assertions
@lru_cache(maxsize=1)
def REPORT_TEXT() -> str:
    from audit_core import REPORT_REL
    return (RUN_ROOT / REPORT_REL).read_text()


def assertions() -> list[dict]:
    g4 = load_json(P9 + "/g4_summary.json")
    mr = load_json(P4 + "/mesh_results.json")
    hp = load_json(P2 + "/heldout_post.json")
    ghr = {(r["row"], r["var"]): r for r in load_csv(P2 + "/g_heldout_rows.csv")}
    g2a = "G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))"
    readme9 = (RUN_ROOT / "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/README.md").read_text()
    readme5 = (RUN_ROOT / "3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/README.md").read_text()
    spec5 = (RUN_ROOT / "3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mech_spec.json").read_text()
    conf = load_json(P4 + "/confirmation_report.json")["confirmation"]
    ks = mr["typology"]["distances"]["ks_vs_screen_d1"]["p"]
    ll_p = mr["leadlag"]["null"]["p_one_sided_greater"]
    A = []

    def a(aid, line, pattern, supported, flag, correct, src, known=None, severity=None):
        A.append(dict(id=aid, hint=line, pattern=pattern, supported=bool(supported), flag=flag, correct=correct, src=src,
                      known=known, severity=severity))

    a("A.robust_note_definition", 486, r"20 of 26 significant \(excluding base row and 3 descriptive strata\)",
      supported=(RECOMPUTE["robust_sig_excl"]() == 20 and RECOMPUTE["robust_rows_incl"]() - 4 == 26), flag="WRONG_DEFINITION",
      correct="20 of 26 co-primary rows significant INCLUDING the base row and strata; 18 of 22 EXCLUDING them",
      src=P2 + "/robustness_recount.json::secondary", known="K04_26of27")
    a("A.neg_description", 816, r"Exposure to non-partner concepts in the concept's origin subfield \(E_neg\)",
      supported=bool(re.search(r"NEG[^.]{0,200}origin", spec5)) and not re.search(r"NEG[^.]{0,200}decile", spec5), flag="WRONG_DEFINITION",
      correct="NEG = exposure to frequency-matched negative-control concepts (not origin-subfield concepts)",
      src="3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mech_spec.json", known="K10_neg_plac_matching")
    a("A.plac_description", 816, r"placebo-host control confirms that the effect is specific to the actual host, not to any random subfield",
      supported=not bool(re.search(r"PLAC = [^.]{0,120}other [^.]{0,60}same d", spec5)), flag="WRONG_DEFINITION",
      correct="PLAC = partners of ANOTHER concept's entry into the SAME host (OR 0.72); it shows specificity to c's partners, not to the host",
      src="3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mech_spec.json", known="K10_neg_plac_matching")
    mb = load_json(P5 + "/match_balance.json")
    a("A.matching_description", 805, r"matched on publication volume",
      supported=any("vol" in k for k in mb) and not any(k.endswith(("team_bin", "act_bin", "fy_bin")) for k in mb), flag="WRONG_DEFINITION",
      correct="exact-matched risk-set controls on four bins: prior works, team size, host activity, first year (match_balance.json)",
      src=P5 + "/match_balance.json", known="K10_neg_plac_matching")
    a("A.k2_mesh", 883, r"k = 2 replicates on held-out and MeSH",
      supported=ks >= 0.05, flag="WRONG_DEFINITION",
      correct=f"held-out within support (KS p {load_json(P4 + '/typology_extras.json')['heldout']['distances']['ks_vs_screen_d1']['p']:.2f}); MeSH largely OUTSIDE support (KS p {ks:.1e}, 12.6% out): MeSH assignment is descriptive only",
      src=P4 + "/mesh_results.json::typology/distances/ks_vs_screen_d1/p", known="K11_k2_mesh")
    a("A.mesh_leadlag", 779, r"weaker but directionally consistent",
      supported=ll_p < 0.05, flag="VERDICT_DRIFT",
      correct=f"MeSH 9 of 13 = 0.69 vs year-shuffle null 0.62, p {ll_p:.2f}: not different from the null",
      src=P4 + "/mesh_results.json::leadlag/null/p_one_sided_greater", known="K12_mesh_leadlag")
    est_p = hp["EST_bin_LPM"]["secondary"]["p"]["A_cont"]
    a("A.establishment_829", 829, r"host-native partners predict establishment",
      supported=est_p < 0.05, flag="WRONG_DEFINITION",
      correct=f"host-leaning entries predict the newcomer-paper COUNT; binary establishment (EST_bin) is null on held-out (p {est_p:.3f}) and binary native cut-offs are null",
      src=P2 + "/heldout_post.json::EST_bin_LPM/secondary/p/A_cont", known="K14_establishment")
    a("A.establishment_871", 871, r"host-native partners predict establishment",
      supported=est_p < 0.05, flag="WRONG_DEFINITION",
      correct="host-leaning entries predict newcomer-paper counts (EST_bin null on held-out)", src=P2 + "/heldout_post.json::EST_bin_LPM",
      known="K14_establishment")
    a("A.establishment_551", 551, r"establish more durably than those that arrive as a package",
      supported=est_p < 0.05, flag="WRONG_DEFINITION",
      correct="associate with more newcomer papers (count outcome); binary establishment not confirmed on held-out",
      src=P2 + "/heldout_post.json::EST_bin_LPM", known="K14_establishment")
    a("A.cross_domain", 696, r"providing a cross-domain test of the grafting finding",
      supported=("biomedicine" not in readme9.lower()), flag="WRONG_DEFINITION",
      correct="REPLICATED for biomedicine -> biomedicine host entries only (non-biomedical hosts dropped; 34% of partner-qualified entries removed by coverage; PMID-only entry years match 50%)",
      src="3_invention_loop/iter_4/gen_art/gen_art_experiment_9/README.md")
    a("A.absorptive_support", 837, r"The artifact's verdict is SUPPORT for an absorptive capacity mechanism",
      supported=("topical proximity" not in readme5.lower() and "topical" not in readme5.lower()), flag="WRONG_DEFINITION",
      correct="consistent with absorptive capacity OR topical proximity (the design cannot separate them; Jia, Wang & Szymanski 2017)",
      src="3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/README.md")
    e4_or = conf["E4"]["heldout_ORs"]["BRIDGE"]["ratio"]
    a("A.E4_label", 790, r"Anchoring × typology interaction",
      supported="anchor" in str(conf["E4"]).lower(), flag="WRONG_DEFINITION",
      correct=f"E4 = lagged-role entry-hazard ORs keep sign: FAIL (BRIDGE OR 0.64 screen vs {e4_or:.2f} held-out)",
      src=P4 + "/confirmation_report.json::confirmation/E4")
    hn, ha = float(ghr[(g2a, "NAT")]["p_holm_G"]), float(ghr[(g2a, "ADJ")]["p_holm_G"])
    a("A.G2a_significant_both_folds", 676, r"Both NATIVE and ADJACENT components are positive and significant on both folds",
      supported=max(hn, ha) < 0.05, flag="VERDICT_DRIFT",
      correct=f"positive on both folds; on held-out not significant after Holm (NATIVE {hn:.3f}, ADJACENT {ha:.3f})",
      src=P2 + "/g_heldout_rows.csv::p_holm_G")
    a("A.mechanism_scope", 690, r"the pooled mechanism label is \*\*host-vocabulary\*\*\.",
      supported="partially pre-specified" in REPORT_TEXT(), flag="WRONG_DEFINITION",
      correct="label host-vocabulary, scope POOLED, PARTIALLY PRE-SPECIFIED (held-out G rows not in heldout_spec; screen G rows not blind)",
      src=P2 + "/mechanism_label.json::scope", severity="WORDING")
    from audit_core import ARTIFACTS
    a("A.art2_id", 77, r"calibrate host-nativeness profiles \[ARTIFACT:art_eR1Z7fMlOcxs\]",
      supported=ARTIFACTS["art_eR1Z7fMlOcxs"].endswith("gen_art_dataset_2"), flag="WRONG_DEFINITION",
      correct="Artifact 2 is the workspace 3_invention_loop/iter_1/gen_art/gen_art_dataset_2; art_eR1Z7fMlOcxs is dataset_5 (iteration 2)",
      src="3_invention_loop/iter_1/gen_art/gen_art_dataset_2", severity="WORDING")
    a("A.cases_partial", 884, r"Four medoid cases selected but not individually interpreted in the report",
      supported=not (RUN_ROOT / P4 / "case_interpretations.md").exists(), flag="DRIFT_VALUE",
      correct="Done: 4 cases with host entries and rooted vs unrooted A_cont (art_mu0h0npvNX_u results/case_interpretations.md)",
      src=P4 + "/case_interpretations.md", severity="NUMBER-ONLY")
    figs = load_json("3_invention_loop/iter_4/gen_report_text/gen_report_text/.terminal_claude_agent_struct_out.json")["figures"]
    fdesc = " ".join(str(f) for f in figs if f.get("id") == "fig_methodology")
    a("A.fig_methodology", 50, r"\[FIGURE:fig_methodology\]",
      supported=("R1_DEAD" in fdesc or "volume/churn" in fdesc) and "3.14" not in fdesc and "closure CONFIRMED" not in fdesc, flag="VERDICT_DRIFT",
      correct="methodology figure must be drawn from the 'Final design as executed' block (T_design): decision flow with dead branches greyed, R1 marked DEAD, adopter OR 3.09; it is placed in the Iteration-1 section although it depicts iteration 2-4 results",
      src="3_invention_loop/iter_4/gen_report_text/gen_report_text/.terminal_claude_agent_struct_out.json::figures/fig_methodology", known="K03_fig_methodology")
    return A


# ============================================================ verdict cells (every place a verdict word is stated in a table/row)
def verdict_cells() -> list[dict]:
    d2 = load_json(P7 + "/d2_summary.json")
    hp = load_json(P2 + "/heldout_post.json")["flags"]
    hd = {r["row"]: r["decision"] for r in load_csv(P3T + "/r1_holm_decisions.csv")}
    conf = load_json(P4 + "/confirmation_report.json")["confirmation"]
    dr = load_json(P1E + "/decision_rules.json")
    ml = load_json(P2 + "/mechanism_label.json")
    e4_flip = (conf["E4"]["screen_ORs"]["BRIDGE"]["coef"] < 0) != (conf["E4"]["heldout_ORs"]["BRIDGE"]["coef"] < 0)
    e5_ok = all(v.get("overlap", True) for v in conf.get("E5", {}).values() if isinstance(v, dict))
    V = []

    def v(vid, hint, rx, expected, src, mode="equal"):
        V.append(dict(id=vid, hint=hint, rx=rx, expected=expected, src=src, mode=mode))
    v("vc.t16.primary", 477, r"^\| Primary \(concept × e \+ host × e FE\) \|.*\| ([A-Z ]+) \|$", d2["primary_fe_concept_x_e_plus_d_x_e"]["decision"]["reading"], P7 + "/d2_summary.json")
    v("vc.t16.coprimary", 478, r"^\| Co-primary \(concept \+ e \+ host\) \| 1\.30 \|.*\| ([A-Z ]+) \|$", d2["coprimary_fe_concept_plus_e_plus_d"]["decision"]["reading"], P7 + "/d2_summary.json")
    v("vc.t16.cdxe", 479, r"^\| Concept \+ host × e \|.*\| ([A-Z ]+) \|$", d2["concept_plus_d_x_e"]["decision"]["reading"], P7 + "/d2_summary.json")
    v("vc.t16.coarse", 480, r"^\| Concept × 2-yr bin \|.*\| ([A-Z ]+) \|$", d2["coarsening_concept_x_2yr_plus_d_x_e"]["decision"]["reading"], P7 + "/d2_summary.json")
    v("vc.t19.heldout", 641, r"^\| Co-primary \(concept \+ e \+ host\) \| Held-out \|.*\| ([A-Za-z ]+) \|$",
      hp["secondary"]["heldout_reading"] + (" confirmed" if hp["secondary"]["confirmed"] else ""), P2 + "/heldout_post.json", mode="ci")
    v("vc.t19.screen", 642, r"^\| Co-primary \(concept \+ e \+ host\) \| Screen \|.*\| ([A-Za-z ]+) \|$", hp["secondary"]["screen_reading"], P2 + "/heldout_post.json")
    v("vc.t19.primary", 640, r"^\| Primary \(concept × e \+ host × e\) \| Held-out \|.*\| ([A-Za-z ()]+) \|$", "Inconclusive (underpowered)"
      if hp["primary_label"].startswith("inconclusive") else hp["primary_label"], P2 + "/heldout_post.json", mode="ci")
    for row, lab, ln in [("closure", r"Closure \(pooled panel\)", 731), ("closure_resT", "Turnover-residualised closure", 732),
                         ("closure_persist", "Persistent-neighbour closure", 733), ("constraint", "Burt constraint", 734)]:
        v(f"vc.t20c.{row}", ln, rf"^\| {lab} \|.*\| ([A-Z]+)[^|]*\|$", hd[row], P3T + "/r1_holm_decisions.csv")
    v("vc.E1", 787, r"Typology shares\.\*\* ([A-Z ]+):", "PASS" if conf["E1"]["success"] else "FAIL", P4 + "/confirmation_report.json", mode="passfail")
    v("vc.E2", 788, r"Type × outcome association\.\*\* ([A-Z ]+):", "PASS" if conf["E2"]["success"] else "FAIL", P4 + "/confirmation_report.json", mode="passfail")
    v("vc.E3", 789, r"Expansion-first ordering\.\*\* ([A-Z ]+):", "PASS" if conf["E3"]["success"] else "FAIL", P4 + "/confirmation_report.json", mode="passfail")
    v("vc.E4", 790, r"\*\* ([A-Z ]+): odds ratios flip", "FAIL" if e4_flip else "PASS", P4 + "/confirmation_report.json", mode="passfail")
    v("vc.E5", 791, r"Other descriptive patterns\.\*\* ([A-Z ]+)\.", "PASS" if e5_ok else "FAIL", P4 + "/confirmation_report.json", mode="passfail")
    v("vc.it3.c", 403, r"\(c\) ([A-Z ]+) for all labels", "NOT MET" if str(dr["c"]["verdict"]).startswith("NOT MET") else "MET", P1E + "/decision_rules.json")
    v("vc.it3.a", 403, r"\(a\) ([A-Z]+): Gate A < 0\.5", "TRIGGERED" if dr["a"]["value"] < 0.5 else "NOT TRIGGERED", P1E + "/decision_rules.json")
    v("vc.it2.c", 331, r"Per decision rule \(c\): ([A-Z ]+)\.", "NOT MET" if str(dr["c"]["verdict"]).startswith("NOT MET") else "MET", P1E + "/decision_rules.json")
    v("vc.gateA", 239, r"\*\*Gate A ([A-Z]+)\.\*\*", "FAILS" if dr["a"]["gate_A"] == "FAIL" else "PASSES", P1E + "/decision_rules.json")
    v("vc.h1", 264, r"H1 is ([A-Z\-]+):", "PILOT-ONLY" if str(dr["b"]["verdict"]).startswith("H1 PILOT-ONLY") else "PRIMARY", P1E + "/decision_rules.json")
    v("vc.mech.861", 861, r"label the mechanism as \"([a-z\-]+)\"", ml["label"], P2 + "/mechanism_label.json")
    v("vc.mech.690", 690, r"pooled mechanism label is \*\*([a-z\-]+)\*\*", ml["label"], P2 + "/mechanism_label.json")
    return V
