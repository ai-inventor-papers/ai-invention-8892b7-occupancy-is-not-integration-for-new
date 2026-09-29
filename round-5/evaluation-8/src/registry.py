#!/usr/bin/env python3
"""Curated registry of cited numbers (the audit universe part (ii) plus the report
table cells that carry the paper's claims).

Each claim names the INTENDED source (artifact file + key) for the quantity the
text says it is, and optional ALTERNATES (other estimator / fold / definition)
used only to classify a mismatch. Report values are extracted from the report
by regex at audit time; hypothesis values by regex on the hypothesis text.
Nothing in this file states a flag: flags are computed.
"""
from __future__ import annotations

N = r"([−\-]?\d[\d,]*(?:\.\d+)?(?:e[−\-]?\d+)?%?)"  # one reported number

# run-root-relative source directories
P7 = "3_invention_loop/iter_3/gen_art/gen_art_experiment_7/results"
P5X = "3_invention_loop/iter_3/gen_art/gen_art_experiment_5/results"
P6X = "3_invention_loop/iter_3/gen_art/gen_art_experiment_6/results"
P8 = "3_invention_loop/iter_3/gen_art/gen_art_experiment_8/results"
P1E = "3_invention_loop/iter_3/gen_art/gen_art_evaluation_1/results"
P2 = "3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/results"
A2 = "3_invention_loop/iter_4/gen_art/gen_art_evaluation_2/audit"
P3 = "3_invention_loop/iter_4/gen_art/gen_art_evaluation_3/results"
P3T = P3 + "/tables"
P4 = "3_invention_loop/iter_4/gen_art/gen_art_evaluation_4/results"
P5 = "3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results"
P9 = "3_invention_loop/iter_4/gen_art/gen_art_experiment_9/results"


def J(path: str, key: str) -> str:
    return f"{path}::{key}"


def CS(path: str, cond: str, target: str) -> str:
    return f"{path}::csv:{cond}|{target}"


CLAIMS: list[dict] = []


def c(cid: str, block: str, claim: str, fold: str, est: str, src: str | None, *, art: str,
      rep: tuple[int, str] | None = None, hyp: str | None = None, alt: list[tuple[str, str]] | None = None,
      kind: str = "cont", tier: str = "R", headline: bool = False, sign: str = "signed",
      replacement: str | None = None, known: str | None = None, holm: float | None = None) -> None:
    CLAIMS.append(dict(id=cid, block=block, claim=claim, fold=fold, estimator=est, src=src, art=art, rep=rep,
                       hyp=hyp, alt=alt or [], kind=kind, tier=tier, headline=headline, sign=sign,
                       replacement=replacement, known=known, holm=holm, type="number"))


G7 = "art_2Cd2JJypeGuA"
GH = "art_WZ8fbLn79nCq"
GM = "art_XGdzjWgi-a88"
GR = "art_zw_JJGsUFSnd"
GD = "art_mu0h0npvNX_u"
GA = "art_FZ2OCJwV6xHs"
G5 = "art_htO_gJuUn6Pr"
G8 = "art_QKsLguxnGFQT"

S7 = J(P7, "d2_summary.json")
cop = "coprimary_fe_concept_plus_e_plus_d"
pri = "primary_fe_concept_x_e_plus_d_x_e"

# ============================================================ D2 SCREEN (exp_7)
c("d2.scr.cop.irr", "D2", "Screen co-primary A_cont IRR/SD", "SCREEN", "co-primary FE (concept+e+host)",
  J(P7 + "/d2_summary.json", f"{cop}/A_cont/irr_per_sd"), art=G7, rep=(478, r"Co-primary \(concept \+ e \+ host\) \| " + N),
  hyp=r"co-primary FE \(concept \+ e \+ host\) A_cont IRR/SD " + N, headline=True, tier="C")
c("d2.scr.cop.lo", "D2", "Screen co-primary CI low", "SCREEN", "co-primary", J(P7 + "/d2_summary.json", f"{cop}/A_cont/irr_per_sd_ci95/0"),
  art=G7, rep=(478, r"Co-primary \(concept \+ e \+ host\) \| 1\.30 \| \[" + N), tier="C", headline=True)
c("d2.scr.cop.hi", "D2", "Screen co-primary CI high", "SCREEN", "co-primary", J(P7 + "/d2_summary.json", f"{cop}/A_cont/irr_per_sd_ci95/1"),
  art=G7, rep=(478, r"Co-primary \(concept \+ e \+ host\) \| 1\.30 \| \[1\.16, " + N), tier="C", headline=True)
c("d2.scr.cop.holm", "D2", "Screen co-primary Holm p", "SCREEN", "co-primary", "recompute:holm_screen_coprimary",
  art=G7, rep=(478, r"Co-primary \(concept \+ e \+ host\) \| 1\.30 \| \[1\.16, 1\.45\] \| " + N), kind="p", tier="C")
c("d2.scr.cop.N", "D2", "Screen co-primary N events", "SCREEN", "co-primary", J(P7 + "/d2_models_table.csv", "csv:model=M1_secondary;var=A_cont|n"),
  art=G7, rep=(642, r"\| Screen \| 1\.30 \| \[1\.16, 1\.45\] \| 1e-5 \| - \| - \| " + N), kind="count", hyp=r"N " + N + r", G 140")
c("d2.scr.cop.G", "D2", "Screen co-primary G clusters", "SCREEN", "co-primary", CS(P7 + "/d2_models_table.csv", "model=M1_secondary;var=A_cont", "G"),
  art=G7, rep=(642, r"\| Screen \| 1\.30 \| \[1\.16, 1\.45\] \| 1e-5 \| - \| - \| 1,544 \| " + N), kind="count")
c("d2.scr.cop.wild", "D2", "Screen co-primary wild p", "SCREEN", "co-primary", J(P7 + "/d2_summary.json", f"{cop}/A_cont/p_wild"),
  art=G7, rep=(484, r"wild-cluster p = " + N), kind="p")
c("d2.scr.pri.irr", "D2", "Screen primary A_cont IRR/SD", "SCREEN", "primary FE (concept x e + host x e)",
  J(P7 + "/d2_summary.json", f"{pri}/A_cont/irr_per_sd"), art=G7, rep=(477, r"Primary \(concept × e \+ host × e FE\) \| " + N))
c("d2.scr.pri.lo", "D2", "Screen primary CI low", "SCREEN", "primary", J(P7 + "/d2_summary.json", f"{pri}/A_cont/irr_per_sd_ci95/0"),
  art=G7, rep=(477, r"host × e FE\) \| 1\.39 \| \[" + N))
c("d2.scr.pri.hi", "D2", "Screen primary CI high", "SCREEN", "primary", J(P7 + "/d2_summary.json", f"{pri}/A_cont/irr_per_sd_ci95/1"),
  art=G7, rep=(477, r"host × e FE\) \| 1\.39 \| \[0\.97, " + N))
c("d2.scr.pri.holm", "D2", "Screen primary Holm p", "SCREEN", "primary", J(P7 + "/d2_summary.json", f"{pri}/decision/holm_p/A_cont"),
  art=G7, rep=(477, r"host × e FE\) \| 1\.39 \| \[0\.97, 1\.99\] \| " + N), kind="p")
c("d2.scr.pri.ct_p", "D2", "Screen PRIMARY CT p", "SCREEN", "primary", J(P7 + "/d2_summary.json", f"{pri}/CT/p_crv1"),
  art=G7, rep=(477, r"host × e FE\) \| 1\.39 \| \[0\.97, 1\.99\] \| 0\.15 \| " + N), kind="p",
  alt=[("WRONG_ESTIMATOR", J(P7 + "/d2_summary.json", f"{cop}/CT/p_crv1"))], known="K05_primary_CT_p")
c("d2.scr.pri.ct_irr", "D2", "Screen primary CT IRR/SD", "SCREEN", "primary", J(P7 + "/d2_summary.json", f"{pri}/CT/irr_per_sd"),
  art=G7, hyp=r"Primary CT " + N)
c("d2.scr.cop.ct_p", "D2", "Screen co-primary CT p", "SCREEN", "co-primary", J(P7 + "/d2_summary.json", f"{cop}/CT/p_crv1"),
  art=G7, rep=(478, r"1\.30 \| \[1\.16, 1\.45\] \| 1e-5 \| " + N), kind="p")
c("d2.scr.cdxe", "D2", "Screen concept + host x e A IRR/SD", "SCREEN", "concept + d x e FE", CS(P7 + "/d2_models_table.csv", "model=M1_c_plus_dxe;var=A_cont", "irr_sd"),
  art=G7, rep=(479, r"Concept \+ host × e \| " + N))
c("d2.scr.retained", "D2", "Screen primary retained share of events", "SCREEN", "primary", "recompute:screen_primary_retained",
  art=G7, rep=(484, r"underpowered \(" + N + r" of events retained"), kind="pct", tier="C")
c("d2.scr.pri.G", "D2", "Screen primary clusters", "SCREEN", "primary", J(P7 + "/d2_summary.json", f"{pri}/G"),
  art=G7, rep=(484, r"of events retained, " + N + r" clusters"), kind="count")
c("d2.scr.robust.count", "D2", "Co-primary robustness rows significant (iteration-3 '26 of 27')", "SCREEN", "co-primary robustness",
  "recompute:robust_sig_incl", art=G7, rep=(486, r"holds in " + N + r" of 27 robustness"), kind="count", tier="C",
  replacement="20 of 26 incl. base row and strata; 18 of 22 excl.", known="K04_26of27")
c("d2.scr.robust.count2", "D2", "Robustness count in iteration-3 'What we have learned'", "SCREEN", "co-primary robustness",
  "recompute:robust_sig_incl", art=G7, rep=(551, r"holding across " + N + r" of 27 robustness"), kind="count", tier="C",
  replacement="20 of 26 incl.; 18 of 22 excl.", known="K04_26of27")
c("d2.scr.robust.den", "D2", "Robustness rows with A (denominator)", "SCREEN", "co-primary robustness", "recompute:robust_rows_incl",
  art=G7, rep=(486, r"holds in 26 of " + N), kind="count", tier="C")
c("d2.scr.robust.excl", "D2", "Robustness significant excl. base and strata", "SCREEN", "co-primary robustness", "recompute:robust_sig_excl",
  art=G7, hyp=r"significant INCLUDING the base row and strata, " + N + r" of 22 EXCLUDING", kind="count", tier="C")
c("d2.scr.robust.lo", "D2", "IRR range low among significant robustness rows", "SCREEN", "co-primary robustness", "recompute:robust_irr_min",
  art=G7, rep=(486, r"variants \(IRR " + N + r"-1\.56"), tier="C")
c("d2.scr.robust.lo_corr", "D2", "IRR range low (iteration-4 correction note)", "SCREEN", "co-primary robustness", "recompute:robust_irr_min",
  art=G7, rep=(486, r"IRR range among significant rows: " + N), tier="C")
c("d2.scr.perm_cop", "D2", "Screen nativeness-permutation co-primary p", "SCREEN", "placebo", J(P7 + "/placebo_summary.json", "secondary/perm_p_two_sided_z (primary placebo p)"),
  art=G7, rep=(486, r"centred on 0; co-primary p = " + N), kind="p")
c("d2.scr.mde_ho", "D2", "Held-out MDE (co-primary) declared on screen", "SCREEN", "power", J(P7 + "/power_heldout.json", "MDE_irr_per_sd_power80/secondary"),
  art=G7, rep=(490, r"MDE \(co-primary\): IRR/SD " + N))
c("d2.scr.native05", "D2", "Share of partner tags >= 0.5 host-native", "SCREEN", "descriptive", J(P7 + "/d2_summary.json", "nativeness/native_share_at_0.5"),
  art=G7, rep=(469, r"Only " + N + r" of partner tags"), kind="pct")
c("d2.scr.package", "D2", "Entry as package share", "SCREEN", "descriptive", J(P7 + "/d2_summary.json", "nativeness/partition_t03/package"),
  art=G7, rep=(467, r"Entry is mostly a package: " + N), kind="pct")
c("d2.scr.graft", "D2", "Native-graft share", "SCREEN", "descriptive", J(P7 + "/d2_summary.json", "nativeness/partition_t03/graft"),
  art=G7, rep=(467, r"origin companions, " + N + r" native grafts"), kind="pct")
c("d2.scr.events_main", "D2", "Main-arm host entries", "SCREEN", "descriptive", J(P7 + "/d2_summary.json", "events/main_arm"),
  art=G7, rep=(467, N + r" main-arm host entries"), kind="count")
c("d2.scr.single_share", "D2", "Single-paper share of entry events ('83%')", "SCREEN", "descriptive", "recompute:single_paper_share_coprimary",
  art=GH, rep=(650, N + r" of entry-year events are single-paper"), kind="pct", tier="C",
  alt=[("WRONG_DEFINITION", "recompute:single_paper_share_all_screen_kw5")],
  replacement="87% of screen co-primary events (1,344 of 1,544); 83% is the share over all 1,746 screen MAIN kw5 entries (denominator must be stated)", known="K06_83pct")
c("d2.scr.single_share2", "D2", "Single-paper share in iteration-4 caveats paragraph", "SCREEN", "descriptive", "recompute:single_paper_share_coprimary",
  art=GH, rep=(863, r"Single-paper entries \(" + N + r" of events\)"), kind="pct", tier="C",
  alt=[("WRONG_DEFINITION", "recompute:single_paper_share_all_screen_kw5")],
  replacement="87% (1,344 / 1,544)", known="K06_83pct")
c("d2.scr.single_n", "D2", "Single-paper screen co-primary events (1,344)", "SCREEN", "descriptive", "recompute:single_paper_n_coprimary",
  art=GH, hyp=r"87% of screen co-primary events \(" + N, kind="count", tier="C")

# ============================================================ D2 HELD-OUT (art_WZ8fbLn79nCq)
HP = P2 + "/heldout_post.json"
c("d2.ho.cop.irr", "D2", "Held-out co-primary A_cont IRR/SD", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/irr_sd_A"),
  art=GH, rep=(641, r"Co-primary \(concept \+ e \+ host\) \| Held-out \| " + N), hyp=r"Co-primary " + N + r" \[1\.057", headline=True, tier="C")
c("d2.ho.cop.lo", "D2", "Held-out co-primary CI low", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/ci_A/0"),
  art=GH, rep=(641, r"Held-out \| 1\.19 \| \[" + N), headline=True, tier="C")
c("d2.ho.cop.hi", "D2", "Held-out co-primary CI high", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/ci_A/1"),
  art=GH, rep=(641, r"Held-out \| 1\.19 \| \[1\.06, " + N), headline=True, tier="C")
c("d2.ho.cop.irr_sum", "D2", "Held-out co-primary IRR/SD in opening summary", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/irr_sd_A"),
  art=GH, rep=(7, r"held-out co-primary IRR/SD " + N), headline=True, tier="C")
c("d2.ho.cop.p_sum", "D2", "Held-out co-primary p in opening summary", "CONFIRMATORY", "co-primary CRV1", J(HP, "flags/secondary/p_A"),
  art=GH, rep=(7, r"\[1\.06, 1\.33\], p = " + N), kind="p", headline=True)
c("d2.ho.cop.p", "D2", "Held-out co-primary CRV1 p", "CONFIRMATORY", "co-primary CRV1", J(HP, "flags/secondary/p_A"),
  art=GH, rep=(641, r"Held-out \| 1\.19 \| \[1\.06, 1\.33\] \| " + N), kind="p", hyp=r"CRV1 p " + N)
c("d2.ho.cop.wild", "D2", "Held-out co-primary wild p", "CONFIRMATORY", "co-primary wild bootstrap", J(HP, "flags/secondary/p_wild_A"),
  art=GH, rep=(644, r"wild-cluster p = " + N), kind="p", hyp=r"wild " + N)
c("d2.ho.cop.holm", "D2", "Held-out co-primary Holm p", "CONFIRMATORY", "co-primary", "recompute:holm_heldout_coprimary",
  art=GH, hyp=r"Holm " + N + r"; wild 0\.012", kind="p", tier="C")
c("d2.ho.cop.N", "D2", "Held-out co-primary N", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/N"),
  art=GH, rep=(641, r"1\.04 \| 0\.60 \| " + N), kind="count")
c("d2.ho.cop.G", "D2", "Held-out co-primary G", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/G"),
  art=GH, rep=(641, r"1\.04 \| 0\.60 \| 972 \| " + N), kind="count")
c("d2.ho.cop.ct", "D2", "Held-out co-primary CT IRR/SD", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/irr_sd_CT"),
  art=GH, rep=(641, r"\[1\.06, 1\.33\] \| 0\.0045 \| " + N))
c("d2.ho.cop.ct_p", "D2", "Held-out co-primary CT p", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/p_CT"),
  art=GH, rep=(641, r"0\.0045 \| 1\.04 \| " + N), kind="p")
c("d2.ho.pri.irr", "D2", "Held-out primary IRR/SD", "CONFIRMATORY", "primary", J(HP, "flags/primary/irr_sd_A"),
  art=GH, rep=(640, r"host × e\) \| Held-out \| " + N), hyp=r"Primary FE " + N + r" \[0\.70")
c("d2.ho.pri.lo", "D2", "Held-out primary CI low", "CONFIRMATORY", "primary", J(HP, "flags/primary/ci_A/0"),
  art=GH, rep=(640, r"Held-out \| 0\.98 \| \[" + N))
c("d2.ho.pri.hi", "D2", "Held-out primary CI high", "CONFIRMATORY", "primary", J(HP, "flags/primary/ci_A/1"),
  art=GH, rep=(640, r"Held-out \| 0\.98 \| \[0\.70, " + N))
c("d2.ho.pri.p", "D2", "Held-out primary p", "CONFIRMATORY", "primary", J(HP, "flags/primary/p_A"),
  art=GH, rep=(640, r"\[0\.70, 1\.37\] \| " + N), kind="p")
c("d2.ho.pri.ct", "D2", "Held-out primary CT IRR/SD", "CONFIRMATORY", "primary", J(HP, "flags/primary/irr_sd_CT"),
  art=GH, rep=(640, r"\[0\.70, 1\.37\] \| 0\.91 \| " + N))
c("d2.ho.pri.ct_p", "D2", "Held-out primary CT p", "CONFIRMATORY", "primary", J(HP, "flags/primary/p_CT"),
  art=GH, rep=(640, r"\| 0\.91 \| 0\.82 \| " + N), kind="p")
c("d2.ho.pri.N", "D2", "Held-out primary N", "CONFIRMATORY", "primary", J(HP, "flags/primary/N"),
  art=GH, rep=(640, r"0\.82 \| 0\.22 \| " + N), kind="count")
c("d2.ho.pri.G", "D2", "Held-out primary G", "CONFIRMATORY", "primary", J(HP, "flags/primary/G"),
  art=GH, rep=(640, r"0\.22 \| 250 \| " + N), kind="count")
c("d2.ho.pri.retained", "D2", "Held-out primary retained share", "CONFIRMATORY", "primary", J(HP, "flags/primary/retained_share"),
  art=GH, rep=(644, r"retains only " + N + r" of events"), kind="pct")
c("d2.ho.n_events", "D2", "Held-out events", "CONFIRMATORY", "descriptive", J(HP, "n_events"),
  art=GH, rep=(644, r"\(250 of " + N), kind="count")
c("d2.ho.het", "D2", "Screen vs held-out co-primary heterogeneity p", "CONFIRMATORY", "co-primary", J(HP, "flags/secondary/heterogeneity_screen_vs_heldout/p"),
  art=GH, rep=(644, r"not significant \(p = " + N), kind="p", hyp=r"co-primary heterogeneity p " + N)
c("d2.ho.pcal_ho", "D2", "Placebo-calibrated p (held-out SD)", "CONFIRMATORY", "placebo", J(HP, "flags/secondary/p_placebo_cal_heldoutSD"),
  art=GH, rep=(644, r"calibrated p = " + N), kind="p", hyp=r"/ " + N + r" \(held-out SD\)")
c("d2.ho.pcal_scr", "D2", "Placebo-calibrated p (screen SD)", "CONFIRMATORY", "placebo", J(HP, "flags/secondary/p_placebo_cal_screenSD"),
  art=GH, hyp=r"placebo-calibrated " + N + r" \(screen SD\)", kind="p")
c("d2.ho.perm_nat", "D2", "Nativeness-permutation p (held-out co-primary)", "CONFIRMATORY", "placebo", J(HP, "nativeness_permutation_placebo/secondary/perm_p_two_sided_z"),
  art=GH, hyp=r"nativeness permutation " + N, kind="p")
c("d2.ho.perm_within", "D2", "Within-concept A-shuffle permutation p", "CONFIRMATORY", "permutation", J(A2 + "/audit_perm.json", "perm_p_two_sided"),
  art=GH, hyp=r"within-concept A-shuffle permutation " + N, kind="p", headline=True)
c("d2.ho.crv1_rej", "D2", "CRV1 rejection rate under null shuffles", "CONFIRMATORY", "CRV1 size", J(A2 + "/audit_perm.json", "share_crv1_p_lt_0.05"),
  art=GH, hyp=r"CRV1 rejects " + N, kind="pct")
c("d2.ho.estbin_cop", "D2", "EST_bin LPM A_cont p (co-primary)", "CONFIRMATORY", "EST_bin LPM", J(HP, "EST_bin_LPM/secondary/p/A_cont"),
  art=GH, hyp=r"A_cont p " + N + r" \(co-primary\)", kind="p", headline=True)
c("d2.ho.estbin_pri", "D2", "EST_bin LPM A_cont p (primary)", "CONFIRMATORY", "EST_bin LPM", J(HP, "EST_bin_LPM/primary/p/A_cont"),
  art=GH, hyp=r"\(co-primary\), " + N + r" \(primary\)", kind="p")
c("d2.ho.pri_het_p", "D2", "Primary heterogeneity p", "CONFIRMATORY", "primary", J(HP, "flags/primary/heterogeneity_screen_vs_heldout/p"),
  art=GH, hyp=r"held-out -0\.37, p " + N, kind="p")
c("d2.ho.pri_het_bs", "D2", "Primary heterogeneity b screen", "CONFIRMATORY", "primary", J(HP, "flags/primary/heterogeneity_screen_vs_heldout/b_screen"),
  art=GH, hyp=r"screen b " + N)
c("d2.ho.robust7", "D2", "Held-out spec-robustness rows significant", "CONFIRMATORY", "co-primary robustness", "recompute:heldout_robust_sig",
  art=GH, hyp=N + r" of 7 held-out spec-robustness", kind="count", tier="C")
c("d2.ho.oos", "D2", "Held-out OOS deviance change", "CONFIRMATORY", "OOS", J(HP, "oos/deviance_diff_with_minus_controls"),
  art=GH, rep=(646, r"deviance by " + N), sign="abs")
c("d2.ho.oos_lo", "D2", "Held-out OOS deviance CI low", "CONFIRMATORY", "OOS", J(HP, "oos/ci95_concept_bootstrap/0"),
  art=GH, rep=(646, r"deviance by 0\.50 \[" + N))

# ---- G1 single-paper test (Table 20)
GP = P2 + "/g_pooled_rows.csv"
GHR = P2 + "/g_heldout_rows.csv"
INT = "row=G1-interaction (A_cont x multi)"
c("g1.pooled.single", "D2", "Table 20 pooled 'single' IRR/SD", "SUPPLEMENTARY", "G1 interaction model, A_cont main effect",
  CS(GP, INT + ";var=A_cont", "irr_sd"), art=GH, rep=(656, r"\| Pooled \| " + N))
c("g1.pooled.multi", "D2", "Table 20 pooled 'multi' IRR/SD", "SUPPLEMENTARY", "G1-multi co-primary", None, art=GH,
  rep=(656, r"\| Pooled \| 1\.26 \| " + N), alt=[("WRONG_ESTIMATOR", CS(GP, "row=G1-multi (co-primary FE);var=A_cont", "irr_sd"))],
  replacement="1.28 [1.11, 1.48] (G1-multi co-primary, g_pooled_rows.csv)", known="K08_table20")
c("g1.pooled.ratio", "D2", "Table 20 pooled ratio (A x multi)", "SUPPLEMENTARY", "G1 interaction", CS(GP, INT + ";var=A_x_multi", "irr_sd"),
  art=GH, rep=(656, r"\| Pooled \| 1\.26 \| 1\.14 \| " + N))
c("g1.pooled.p_int", "D2", "Table 20 pooled interaction p", "SUPPLEMENTARY", "G1 interaction", CS(GP, INT + ";var=A_x_multi", "p"),
  art=GH, rep=(656, r"\| Pooled \| 1\.26 \| 1\.14 \| 0\.91 \| " + N), kind="p")
c("g1.ho.single", "D2", "Table 20 held-out 'single' IRR/SD", "SUPPLEMENTARY", "G1 interaction model, A_cont main effect",
  CS(GHR, INT + ";var=A_cont", "irr_sd"), art=GH, rep=(657, r"\| Held-out \| " + N))
c("g1.ho.multi", "D2", "Table 20 held-out 'multi' IRR/SD", "SUPPLEMENTARY", "G1-multi co-primary", None, art=GH,
  rep=(657, r"\| Held-out \| 1\.37 \| " + N), alt=[("WRONG_ESTIMATOR", CS(GHR, "row=G1-multi (co-primary FE);var=A_cont", "irr_sd"))],
  replacement="1.19 [0.98, 1.44], p 0.08 (G1-multi co-primary, g_heldout_rows.csv)", known="K08_table20")
c("g1.ho.ratio", "D2", "Table 20 held-out ratio", "SUPPLEMENTARY", "G1 interaction", CS(GHR, INT + ";var=A_x_multi", "irr_sd"),
  art=GH, rep=(657, r"\| Held-out \| 1\.37 \| 1\.09 \| " + N))
c("g1.ho.ratio_txt", "D2", "Held-out interaction ratio in text", "SUPPLEMENTARY", "G1 interaction", CS(GHR, INT + ";var=A_x_multi", "irr_sd"),
  art=GH, rep=(659, r"interaction is significant \(ratio " + N))
c("g1.ho.p_int", "D2", "Table 20 held-out interaction p", "SUPPLEMENTARY", "G1 interaction", CS(GHR, INT + ";var=A_x_multi", "p"),
  art=GH, rep=(657, r"\| Held-out \| 1\.37 \| 1\.09 \| 0\.80 \| " + N), kind="p")
c("g1.pooled.multi_txt", "D2", "Pooled multi-team IRR/SD in text", "SUPPLEMENTARY", "G1-multi co-primary", CS(GP, "row=G1-multi (co-primary FE);var=A_cont", "irr_sd"),
  art=GH, rep=(659, r"multi-team IRR/SD is " + N + r" \[1\.11"), hyp=r"pooled " + N + r" \[1\.11, 1\.48\]")
c("g1.pooled.multi_G", "D2", "Pooled multi-team G", "SUPPLEMENTARY", "G1-multi", CS(GP, "row=G1-multi (co-primary FE);var=A_cont", "G"),
  art=GH, rep=(659, r"\(G = " + N + r"\), CI excluding 1"), kind="count")
c("g1.ho.multi_txt", "D2", "Held-out multi-team IRR/SD in text", "SUPPLEMENTARY", "G1-multi co-primary", CS(GHR, "row=G1-multi (co-primary FE);var=A_cont", "irr_sd"),
  art=GH, rep=(659, r"and the multi-team IRR/SD is " + N), hyp=r"held-out alone " + N + r" \[0\.98", known="K08_table20")
c("g1.ho.multi_p", "D2", "Held-out multi-team p", "SUPPLEMENTARY", "G1-multi", CS(GHR, "row=G1-multi (co-primary FE);var=A_cont", "p"),
  art=GH, hyp=r"\[0\.98, 1\.44\], p " + N, kind="p")
c("g1.ho.mde", "D2", "Held-out G1 MDE", "SUPPLEMENTARY", "G1 status", J(P2 + "/g_heldout_summary.json", "G1_status/mde"),
  art=GH, rep=(659, r"with MDE " + N))
c("g1.ho.G", "D2", "Held-out G1 G", "SUPPLEMENTARY", "G1 status", J(P2 + "/g_heldout_summary.json", "G1_status/G"),
  art=GH, rep=(690, r"MDE 1\.30 and G = " + N), kind="count")
c("g1.pooled.mde", "D2", "Pooled G1 projected MDE", "SUPPLEMENTARY", "G1 status", J(P2 + "/mechanism_label.json", "inputs/G1_mde_pooled_projected"),
  art=GH, rep=(659, r"projected MDE " + N))
# ---- G2a vocabulary decomposition (Table 20a)
G2A = "row=G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3))"
for fold, path, line, lab in [("pooled", GP, 671, "Pooled"), ("ho", GHR, 673, "Held-out")]:
    for comp, var, off in [("NAT", "NAT", 0), ("ADJ", "ADJ", 1)]:
        ln = line + off
        name = "NATIVE" if comp == "NAT" else "ADJACENT"
        fl = "SUPPLEMENTARY"
        c(f"g2a.{fold}.{comp}.irr", "D2", f"G2a {name} {lab} IRR/SD", fl, "co-primary G2a", CS(path, G2A + f";var={var}", "irr_sd"),
          art=GH, rep=(ln, rf"\| {name} \| {lab} \| " + N))
        c(f"g2a.{fold}.{comp}.lo", "D2", f"G2a {name} {lab} CI low", fl, "co-primary G2a", CS(path, G2A + f";var={var}", "irr_sd_lo"),
          art=GH, rep=(ln, rf"\| {name} \| {lab} \| [\d.]+ \| \[" + N))
        c(f"g2a.{fold}.{comp}.hi", "D2", f"G2a {name} {lab} CI high", fl, "co-primary G2a", CS(path, G2A + f";var={var}", "irr_sd_hi"),
          art=GH, rep=(ln, rf"\| {name} \| {lab} \| [\d.]+ \| \[[\d.]+, " + N))
        c(f"g2a.{fold}.{comp}.p", "D2", f"G2a {name} {lab} p (unadjusted)", fl, "co-primary G2a", CS(path, G2A + f";var={var}", "p"),
          art=GH, rep=(ln, rf"\| {name} \| {lab} \| [\d.]+ \| \[[\d.]+, [\d.]+\] \| " + N), kind="p")
c("g2a.ho.NAT.holm", "D2", "Held-out G2a NATIVE Holm p", "SUPPLEMENTARY", "G2a Holm", CS(GHR, G2A + ";var=NAT", "p_holm_G"),
  art=GH, hyp=r"held-out Holm p " + N, kind="p")
c("g2a.ho.ADJ.holm", "D2", "Held-out G2a ADJACENT Holm p", "SUPPLEMENTARY", "G2a Holm", CS(GHR, G2A + ";var=ADJ", "p_holm_G"),
  art=GH, hyp=r"held-out Holm p 0\.071 / " + N, kind="p")
c("g2a.pooled.wald", "D2", "G2a Wald equality p (pooled)", "SUPPLEMENTARY", "G2a Wald", J(P2 + "/g_pooled_summary.json", "G2a/wald_equal_per01/p"),
  art=GH, rep=(676, r"p = " + N + r" \(pooled\)"), kind="p")
c("g2a.ho.wald", "D2", "G2a Wald equality p (held-out)", "SUPPLEMENTARY", "G2a Wald", J(P2 + "/g_heldout_summary.json", "G2a/wald_equal_per01/p"),
  art=GH, rep=(676, r"\(pooled\), p = " + N), kind="p")
c("g2b.pooled.for", "D2", "G2b FOREIGN IRR/SD pooled", "SUPPLEMENTARY", "G2b decomposition", CS(GP, "row=G2b exact decomposition A_nat + A_adj + A_for;var=A_for", "irr_sd"),
  art=GH, rep=(676, r"FOREIGN IRR/SD " + N))
c("g2b.ho.for", "D2", "G2b FOREIGN IRR/SD held-out", "SUPPLEMENTARY", "G2b decomposition", CS(GHR, "row=G2b exact decomposition A_nat + A_adj + A_for;var=A_for", "irr_sd"),
  art=GH, rep=(676, r"\(pooled\) and " + N + r" \(held-out\)"))
c("g3.pooled.pct", "D2", "G3 combined % log-IRR removed (pooled)", "SUPPLEMENTARY", "G3", J(P2 + "/mechanism_label.json", "inputs/G3_combined_pct_logirr_removed"),
  art=GH, rep=(682, r"absorption: " + N), kind="pctval")
c("g3.pooled.lo", "D2", "G3 pooled CI low", "SUPPLEMENTARY", "G3", J(P2 + "/mechanism_label.json", "inputs/G3_combined_pct_ci/0"),
  art=GH, rep=(682, r"absorption: −7\.3% \[" + N))
c("g3.pooled.hi", "D2", "G3 pooled CI high", "SUPPLEMENTARY", "G3", J(P2 + "/mechanism_label.json", "inputs/G3_combined_pct_ci/1"),
  art=GH, rep=(682, r"absorption: −7\.3% \[−27\.5, \+?" + N))
c("g3.placebo.share", "D2", "Placebo host share of significant draws (prox)", "SUPPLEMENTARY", "placebo host", J(P2 + "/mechanism_label.json", "placebo_host_qualifier/prox/share_pos_sig"),
  art=GH, rep=(682, r"share of significant draws ≤ " + N))

# ============================================================ MeSH G4 (art_XGdzjWgi-a88)
G4 = P9 + "/g4_summary.json"
c("g4.R1.irr", "MeSH", "MeSH R1 primary IRR/SD", "MESH", "primary FE", J(G4, "R1/irr_sd"), art=GM, rep=(704, r"R1: primary \(concept × e \+ d × e\) \| " + N), hyp=r"primary FE " + N + r" \[1\.098")
c("g4.R1.lo", "MeSH", "MeSH R1 CI low", "MESH", "primary FE", J(G4, "R1/ci/0"), art=GM, rep=(704, r"d × e\) \| 1\.32 \| \[" + N))
c("g4.R1.hi", "MeSH", "MeSH R1 CI high", "MESH", "primary FE", J(G4, "R1/ci/1"), art=GM, rep=(704, r"d × e\) \| 1\.32 \| \[1\.10, " + N))
c("g4.R1.holm", "MeSH", "MeSH R1 Holm p", "MESH", "primary FE", "recompute:holm_mesh_R1", art=GM, rep=(704, r"\[1\.10, 1\.60\] \| " + N), kind="p", tier="C")
c("g4.R1.p", "MeSH", "MeSH R1 CRV1 p", "MESH", "primary FE", J(G4, "R1/p_crv1"), art=GM, hyp=r"\[1\.098, 1\.598\], p " + N, kind="p")
c("g4.R1.ct", "MeSH", "MeSH R1 CT IRR/SD", "MESH", "primary FE", J(G4, "R1/CT_irr_sd"), art=GM, rep=(704, r"\[1\.10, 1\.60\] \| 0\.007 \| " + N))
c("g4.R1.ct_p", "MeSH", "MeSH R1 CT p", "MESH", "primary FE", J(G4, "R1/CT_p"), art=GM, rep=(704, r"0\.007 \| 1\.10 \| " + N), kind="p")
c("g4.R1.N", "MeSH", "MeSH R1 N", "MESH", "primary FE", J(G4, "R1/N"), art=GM, rep=(704, r"0\.46 \| " + N), kind="count")
c("g4.R1.G", "MeSH", "MeSH R1 G", "MESH", "primary FE", J(G4, "R1/G"), art=GM, rep=(704, r"0\.46 \| 1,004 \| " + N), kind="count")
c("g4.R2.irr", "MeSH", "MeSH R2 co-primary IRR/SD", "MESH", "co-primary", J(G4, "R2/irr_sd"), art=GM, rep=(705, r"R2: co-primary \(concept \+ e \+ d\) \| " + N),
  hyp=r"Co-primary " + N + r" \[1\.117", headline=True, tier="C")
c("g4.R2.irr_sum", "MeSH", "MeSH co-primary IRR/SD in summary", "MESH", "co-primary", J(G4, "R2/irr_sd"), art=GM, rep=(7, r"MeSH replication IRR/SD " + N), headline=True, tier="C")
c("g4.R2.lo", "MeSH", "MeSH R2 CI low", "MESH", "co-primary", J(G4, "R2/ci/0"), art=GM, rep=(705, r"d\) \| 1\.23 \| \[" + N), headline=True, tier="C")
c("g4.R2.hi", "MeSH", "MeSH R2 CI high", "MESH", "co-primary", J(G4, "R2/ci/1"), art=GM, rep=(705, r"d\) \| 1\.23 \| \[1\.12, " + N), headline=True, tier="C")
c("g4.R2.holm", "MeSH", "MeSH R2 Holm p", "MESH", "co-primary", "recompute:holm_mesh_R2", art=GM, rep=(705, r"\[1\.12, 1\.36\] \| " + N), kind="p", tier="C", headline=True)
c("g4.R2.ct", "MeSH", "MeSH R2 CT IRR/SD", "MESH", "co-primary", J(G4, "R2/CT_irr_sd"), art=GM, rep=(705, r"9\.7e-5 \| " + N))
c("g4.R2.ct_p", "MeSH", "MeSH R2 CT p", "MESH", "co-primary", J(G4, "R2/CT_p"), art=GM, rep=(705, r"9\.7e-5 \| 1\.10 \| " + N), kind="p")
c("g4.R2.N", "MeSH", "MeSH R2 N", "MESH", "co-primary", J(G4, "R2/N"), art=GM, rep=(705, r"0\.053 \| " + N), kind="count")
c("g4.R2.G", "MeSH", "MeSH R2 G", "MESH", "co-primary", J(G4, "R2/G"), art=GM, rep=(705, r"0\.053 \| 2,171 \| " + N), kind="count")
c("g4.R2.wild", "MeSH", "MeSH R2 wild p", "MESH", "co-primary", J(G4, "R2/p_wild"), art=GM, hyp=r"Holm 9\.7e-5, wild " + N, kind="p")
c("g4.ivw", "MeSH", "IVW main + MeSH co-primary", "MESH", "IVW", "recompute:ivw_main_mesh", art=GM, rep=(707, r"1\.23\) is " + N), tier="C", headline=True)
c("g4.ivw.lo", "MeSH", "IVW CI low", "MESH", "IVW", "recompute:ivw_main_mesh_lo", art=GM, rep=(707, r"1\.23\) is 1\.26 \[" + N), tier="C")
c("g4.ivw.hi", "MeSH", "IVW CI high", "MESH", "IVW", "recompute:ivw_main_mesh_hi", art=GM, rep=(707, r"1\.23\) is 1\.26 \[1\.17, " + N), tier="C")
c("g4.ivw.i2", "MeSH", "IVW I2", "MESH", "IVW", "recompute:ivw_main_mesh_i2", art=GM, rep=(707, r"I² = " + N), kind="cont", tier="C")
c("g4.S1", "MeSH", "MeSH G1 multi-team IRR/SD", "MESH", "G1 multi co-primary", J(G4, "rows/S1/irr_sd"), art=GM, rep=(709, r"Multi-team test: IRR/SD " + N))
c("g4.S1.lo", "MeSH", "MeSH G1 CI low", "MESH", "G1", J(G4, "rows/S1/ci/0"), art=GM, rep=(709, r"IRR/SD 1\.08 \[" + N))
c("g4.S1.hi", "MeSH", "MeSH G1 CI high", "MESH", "G1", J(G4, "rows/S1/ci/1"), art=GM, rep=(709, r"IRR/SD 1\.08 \[0\.96, " + N))
c("g4.S2.nat", "MeSH", "MeSH G2 NATIVE", "MESH", "G2", J(G4, "rows/S2/irr_sd"), art=GM, rep=(709, r"NATIVE " + N + r" \[1\.08"))
c("g4.R3", "MeSH", "MeSH R3 row", "MESH", "concept + d x e", J(G4, "rows/R3/irr_sd"), art=GM, hyp=r"R3 " + N)
c("g4.R4", "MeSH", "MeSH R4 row", "MESH", "concept x 2yr + d x e", J(G4, "rows/R4/irr_sd"), art=GM, hyp=r"R4 " + N)
c("g4.dev_events", "MeSH", "MeSH host-entry events after F6 widening", "MESH", "descriptive", J(P9 + "/events_mesh_summary.json", "chosen/events"),
  art=GM, rep=(698, r"yields " + N + r" host-entry events"), kind="count")
c("g4.dev_concepts", "MeSH", "MeSH concepts after F6 widening", "MESH", "descriptive", J(P9 + "/events_mesh_summary.json", "widening_steps/2/concepts"),
  art=GM, rep=(698, r"events across " + N + r" concepts"), kind="count")
c("g4.declared_events", "MeSH", "Declared kw5/coverage-0.50 design events", "MESH", "descriptive", J(P9 + "/events_mesh_summary.json", "widening_steps/0/events"),
  art=GM, rep=(698, r"gave only " + N + r" events"), kind="count")
c("g4.declared_G", "MeSH", "Declared design non-singleton clusters", "MESH", "descriptive", J(P9 + "/events_mesh_summary.json", "widening_steps/0/design_G_non_singleton"),
  art=GM, rep=(698, r"concepts, " + N + r" non-singleton"), kind="count")
c("g4.coverage_removed", "MeSH", "Share of partner-qualified entries removed by coverage rule", "MESH", "scope", J(P9 + "/events_mesh_summary.json", "removed_by_coverage_among_kw/share"),
  art=GM, hyp=r"coverage rule removes " + N, kind="pct")

# ============================================================ RQ1 held-out (art_zw_JJGsUFSnd)
PP = P3T + "/r1_pooled_panel_screen_vs_heldout.csv"
ES = P3T + "/r1_event_study_screen_vs_heldout.csv"
HD = P3T + "/r1_holm_decisions.csv"
IV = P3T + "/r1_iv_synthesis_descriptive.csv"
for row, lab, line in [("closure", r"Closure \(pooled panel\)", 731), ("closure_resT", r"Turnover-residualised closure", 732),
                       ("closure_persist", r"Persistent-neighbour closure", 733)]:
    c(f"rq1.{row}.scr", "RQ1", f"{row} screen pooled-panel coef", "SCREEN", "pooled panel", CS(PP, f"row={row}", "coef_screen"),
      art=GR, rep=(line, rf"\| {lab} \| " + N), alt=[("WRONG_ESTIMATOR", CS(ES, f"row={row}", "S_screen"))])
    c(f"rq1.{row}.ho", "RQ1", f"{row} held-out pooled-panel coef", "CONFIRMATORY", "pooled panel", CS(PP, f"row={row}", "coef_heldout"),
      art=GR, rep=(line, rf"\| {lab} \| [−\d.]+ \| " + N), alt=[("WRONG_ESTIMATOR", CS(ES, f"row={row}", "S_heldout"))], headline=(row == "closure"))
    c(f"rq1.{row}.lo", "RQ1", f"{row} held-out CI low", "CONFIRMATORY", "pooled panel", CS(PP, f"row={row}", "ci_heldout_lo"),
      art=GR, rep=(line, rf"\| {lab} \| [−\d.]+ \| [−\d.]+ \| \[" + N))
    c(f"rq1.{row}.hi", "RQ1", f"{row} held-out CI high", "CONFIRMATORY", "pooled panel", CS(PP, f"row={row}", "ci_heldout_hi"),
      art=GR, rep=(line, rf"\| {lab} \| [−\d.]+ \| [−\d.]+ \| \[[−\d.]+, " + N))
    c(f"rq1.{row}.holm", "RQ1", f"{row} held-out Holm p", "CONFIRMATORY", "pooled panel Holm", "recompute:holm_rq1_" + row,
      art=GR, rep=(line, rf"\| {lab} \| [−\d.]+ \| [−\d.]+ \| \[[−\d.]+, [−\d.]+\] \| " + N), kind="p", tier="C", headline=True)
c("rq1.constraint.scr", "RQ1", "Burt constraint screen S (Table 20c)", "SCREEN", "event study (frozen estimator for constraint)",
  CS(ES, "row=constraint", "S_screen"), art=GR, rep=(734, r"\| Burt constraint \| \+?" + N),
  alt=[("WRONG_ESTIMATOR", CS(PP, "row=constraint", "coef_screen"))], known="K13_constraint_mixed")
c("rq1.constraint.ho", "RQ1", "Burt constraint held-out S", "CONFIRMATORY", "event study", CS(ES, "row=constraint", "S_heldout"),
  art=GR, rep=(734, r"\| Burt constraint \| [+\-−\d.]+ \| \+?" + N))
c("rq1.constraint.lo", "RQ1", "Burt constraint held-out CI low", "CONFIRMATORY", "event study", CS(ES, "row=constraint", "ci_heldout_lo"),
  art=GR, rep=(734, r"\| Burt constraint \| [+\-−\d.]+ \| [+\-−\d.]+ \| \[" + N))
c("rq1.constraint.holm", "RQ1", "Burt constraint Holm p", "CONFIRMATORY", "event study", CS(HD, "row=constraint", "p_one_holm"),
  art=GR, hyp=r"Holm decision for constraint \(" + N, kind="p")
c("rq1.persist.sum", "RQ1", "Persistent-neighbour held-out value in opening summary (labelled 'S')", "CONFIRMATORY", "pooled panel coef",
  CS(PP, "row=closure_persist", "coef_heldout"), art=GR, rep=(7, r"held-out S = " + N), alt=[("WRONG_ESTIMATOR", CS(ES, "row=closure_persist", "S_heldout"))], headline=True)
c("rq1.persist.sum_holm", "RQ1", "Persistent-neighbour Holm in opening summary", "CONFIRMATORY", "pooled panel Holm", "recompute:holm_rq1_closure_persist",
  art=GR, rep=(7, r"held-out S = −1\.07, Holm p = " + N), kind="p", tier="C", headline=True)
c("rq1.es.closure", "RQ1", "Held-out event-study closure S", "CONFIRMATORY", "event study", CS(ES, "row=closure", "S_heldout"),
  art=GR, hyp=r"event-study rows closure " + N)
c("rq1.es.resT", "RQ1", "Held-out event-study resT S", "CONFIRMATORY", "event study", CS(ES, "row=closure_resT", "S_heldout"),
  art=GR, hyp=r"\[−?-?1\.200, 0\.074\], resT " + N)
c("rq1.es.persist", "RQ1", "Held-out event-study persistent S", "CONFIRMATORY", "event study", CS(ES, "row=closure_persist", "S_heldout"),
  art=GR, hyp=r"event study " + N + r" \[-1\.706")
c("rq1.es.persist.scr", "RQ1", "Screen event-study persistent S", "SCREEN", "event study", CS(ES, "row=closure_persist", "S_screen"),
  art=G5, rep=(421, r"R1b persistent-neighbour closure \| " + N), hyp=r"screen event-study CI included 0 \(" + N)
c("rq1.es.persist.scr_hi", "RQ1", "Screen event-study persistent CI high", "SCREEN", "event study", CS(ES, "row=closure_persist", "ci_screen_hi"),
  art=G5, rep=(421, r"R1b persistent-neighbour closure \| −0\.575 \| \[−1\.270, " + N))
c("rq1.ivw.resT", "RQ1", "IVW resT pooled", "SUPPLEMENTARY", "IVW descriptive", CS(IV, "row=closure_resT", "S_pooled"), art=GR, hyp=r"IVW resT " + N)
c("rq1.ivw.closure", "RQ1", "IVW closure pooled", "SUPPLEMENTARY", "IVW descriptive", "recompute:ivw_rq1_closure", art=GR, rep=(738, r"closure " + N + r" \[−0\.790"), tier="C")
c("rq1.ivw.closure.lo", "RQ1", "IVW closure CI low", "SUPPLEMENTARY", "IVW descriptive", CS(IV, "row=closure", "ci_lo"), art=GR, rep=(738, r"closure −0\.464 \[" + N))
c("rq1.ivw.persist", "RQ1", "IVW persistent pooled", "SUPPLEMENTARY", "IVW descriptive", CS(IV, "row=closure_persist", "S_pooled"), art=GR, rep=(738, r"persistent-neighbour closure " + N))
c("rq1.ivw.constraint", "RQ1", "IVW constraint pooled", "SUPPLEMENTARY", "IVW descriptive", CS(IV, "row=constraint", "S_pooled"), art=GR, rep=(738, r"constraint \+?" + N + r" \[0\.040"))
c("rq1.xc.ho", "RQ1", "xc_excess held-out S", "CONFIRMATORY", "event study", CS(ES, "row=xc_excess", "S_heldout"), art=GR, rep=(736, r"\(S = " + N + r" \[−0\.061"))
c("rq1.effsize", "RQ1", "Held-out effective size S", "CONFIRMATORY", "event study", CS(ES, "row=effsize", "S_heldout"), art=GR, hyp=r"effective size LOWER on held-out \(" + N)
c("rq1.wmz", "RQ1", "Held-out pooled-panel wmz", "CONFIRMATORY", "pooled panel", CS(PP, "row=wmz", "coef_heldout"), art=GR, hyp=r"pooled-panel wmz \+" + N)
c("rq1.H_smd", "RQ1", "Held-out balance: entropy H SMD at k=0", "CONFIRMATORY", "balance", CS(P3T + "/r1_balance_smd.csv", "covariate=H;k=0", "smd"),
  art=GR, rep=(725, r"entropy H has SMD " + N), hyp=r"H SMD " + N)
c("rq1.smd_count", "RQ1", "Covariates with |SMD| > 0.25", "CONFIRMATORY", "balance", "recompute:rq1_smd_flag_count", art=GR, hyp=r"; " + N + r" of 11 covariates", kind="count", tier="C")
c("rq1.n_onsets", "RQ1", "Held-out onsets", "CONFIRMATORY", "matching", CS(P3T + "/r1_n_flow.csv", "step=n_onsets", "value"), art=GR, rep=(725, r"yields " + N + r" onsets"), kind="count")
c("rq1.n_matched", "RQ1", "Held-out matched", "CONFIRMATORY", "matching", CS(P3T + "/r1_n_flow.csv", "step=n_matched", "value"), art=GR, rep=(725, r"onsets, " + N + r" matched"), kind="count")
c("rq1.n_before", "RQ1", "Matched before fallback", "CONFIRMATORY", "matching", CS(P3T + "/r1_n_flow.csv", "step=n_matched_before_fallback", "value"), art=GR, rep=(725, r"\(" + N + r" before fallback"), kind="count")
c("rq1.ctrl_screen", "RQ1", "Event-study controls that are screen concepts", "CONFIRMATORY", "matching", CS(P3T + "/r1_n_flow.csv", "step=controls_from_screen", "value"), art=GR, rep=(742, r"\(" + N + r" of 25 unique"), kind="count")
c("rq1.match_rate", "RQ1", "Held-out match rate", "CONFIRMATORY", "matching", CS(P3T + "/r1_n_flow.csv", "step=match_rate", "value"), art=GR, rep=(740, r"22/30 = " + N), kind="pct")
c("rq1.retained_ho", "RQ1", "Held-out retained fraction |S_res|/|S_raw|", "CONFIRMATORY", "event study", "recompute:rq1_retained_heldout", art=GR, rep=(740, r"\|S_raw\|\) is " + N), tier="C")
c("rq1.retained_scr", "RQ1", "Screen retained fraction", "SCREEN", "event study", "recompute:rq1_retained_screen", art=GR, rep=(740, r"compared to " + N + r" on the screen"), tier="C")
c("rq1.Hmatched", "RQ1", "H-matched subset resT", "SUPPLEMENTARY", "event study", CS(P3T + "/r1_n_flow.csv", "step=H_matched_S_closure_resT", "value"), art=GR, hyp=r"H-matched subset \(n 11\) resT " + N)
# D3
D3 = P3 + "/d3/d3_table.csv"
for fold, line, n in [("screen", 752, "Screen"), ("heldout", 753, "Held-out")]:
    c(f"d3.{fold}.rho", "RQ1", f"D3 partial rho {fold}", "CONFIRMATORY" if fold == "heldout" else "SCREEN", "D3 partial rho",
      CS(D3, f"fold={fold};analysis=primary", "partial_rho"), art=GR, rep=(line, rf"\| {n} \| \d+ \| \+?" + N))
    c(f"d3.{fold}.p", "RQ1", f"D3 p {fold}", "CONFIRMATORY" if fold == "heldout" else "SCREEN", "D3 permutation p",
      CS(D3, f"fold={fold};analysis=primary", "p_two_perm"), art=GR, rep=(line, rf"\| {n} \| \d+ \| \+?[\d.]+ \| \[[−\d.]+, [\d.]+\] \| " + N), kind="p")
    c(f"d3.{fold}.mde", "RQ1", f"D3 MDE {fold}", "CONFIRMATORY" if fold == "heldout" else "SCREEN", "D3", CS(D3, f"fold={fold};analysis=primary", "mde_rho"),
      art=GR, rep=(line, rf"\| {n} \| \d+ \| \+?[\d.]+ \| \[[−\d.]+, [\d.]+\] \| [\d.]+ \| " + N))
c("d3.pooled.rho", "RQ1", "D3 pooled rho", "SUPPLEMENTARY", "D3", CS(D3, "fold=pooled;analysis=S8_fold_pooled", "partial_rho"), art=GR, rep=(754, r"\| Pooled \| 151 \| \+?" + N))
# RQ1 screen (exp_5) Table 14
R5 = P5X + "/results_summary.json"
for key, lab, line in [("closure", "Raw closure", 419), ("closure_resT", "R1a residualised closure", 420), ("constraint", "R1c Burt constraint", 422),
                       ("xc_excess", "R1c cross-community pair excess", 423)]:
    c(f"rq1s.{key}.S", "RQ1", f"Screen {lab} S", "SCREEN", "event study", J(R5, f"headline/rows/{key}/S"), art=G5, rep=(line, rf"\| {lab} \| \+?" + N))
    c(f"rq1s.{key}.lo", "RQ1", f"Screen {lab} CI low", "SCREEN", "event study", J(R5, f"headline/rows/{key}/ci/0"), art=G5, rep=(line, rf"\| {lab} \| \+?[−\d.]+ \| \[" + N))
    c(f"rq1s.{key}.hi", "RQ1", f"Screen {lab} CI high", "SCREEN", "event study", J(R5, f"headline/rows/{key}/ci/1"), art=G5, rep=(line, rf"\| {lab} \| \+?[−\d.]+ \| \[[−\d.]+, " + N))
c("rq1s.r1d", "RQ1", "Screen R1d hub-not-clique diff", "SCREEN", "R1d", J(R5.replace("results_summary.json", "r1d.json"), "diff") if False else J(P5X + "/results_summary.json", "r1d/diff"),
  art=G5, rep=(424, r"R1d hub-not-clique \| \+?" + N))
c("rq1s.pp.resT", "RQ1", "Screen pooled-panel resT", "SCREEN", "pooled panel", J(R5, "pooled_panel/closure_resT/coef"), art=G5, rep=(430, r"turnover-residualised closure " + N))
c("rq1s.pp.persist", "RQ1", "Screen pooled-panel persistent", "SCREEN", "pooled panel", J(R5, "pooled_panel/closure_persist/coef"), art=G5, rep=(430, r"persistent-neighbour closure " + N))
c("rq1s.pp.persist.holm", "RQ1", "Screen pooled-panel persistent Holm", "SCREEN", "pooled panel", J(R5, "pooled_panel/closure_persist/p_holm"), art=G5, rep=(430, r"Holm p = " + N), kind="p")
c("rq1s.band", "RQ1", "Band-only matched", "SCREEN", "matching", J(R5, "sensitivities/band_only/n_matched"), art=G5, rep=(430, r"Band-only matching \(" + N), kind="count")
c("rq1s.fresh.S", "RQ1", "Fresh replication S", "SCREEN", "event study", J(R5, "headline/flags/fresh_replication/S"), art=G5, rep=(432, r"Raw S = " + N))
c("rq1s.fresh.p", "RQ1", "Fresh replication one-sided p", "SCREEN", "event study", J(R5, "headline/flags/fresh_replication/p_one_screened"), art=G5, rep=(432, r"one-sided p = " + N), kind="p")
c("rq1s.fresh.n", "RQ1", "Fresh replication n_matched (report never states it)", "SCREEN", "event study", J(R5, "headline/flags/fresh_replication/n_matched"), art=G5, kind="count")
c("rq1s.n_matched", "RQ1", "Screen MAIN x E_up matched", "SCREEN", "event study", J(R5, "headline/n_matched"), art=G5, rep=(415, r"68 onsets, " + N + r" matched"), kind="count")

# ============================================================ DESCRIPTIVE (art_mu0h0npvNX_u, art_QKsLguxnGFQT)
LD = P4 + "/leadlag_denominator_table.csv"
for pop, col_i in [("screen", 1), ("heldout", 2), ("pooled_main", 3), ("mesh", 4)]:
    for cat, lab in [("n_neither", "Neither"), ("n_diffusion_only", "Diffusion only"), ("n_expansion_only", "Expansion only"),
                     ("n_expansion_first", "Expansion first"), ("n_same_year", "Same year"), ("n_diffusion_first", "Diffusion first")]:
        pre = r"\| " + lab + r" \| " + r"".join([r"[^|]+\| "] * (col_i - 1))
        c(f"ll.{pop}.{cat}", "descriptive", f"Lead-lag {lab} count ({pop})", "CONFIRMATORY" if pop == "heldout" else ("MESH" if pop == "mesh" else "SCREEN"),
          "lead-lag category count", "recompute:leadlag_" + pop + "_" + cat if pop in ("screen", "mesh") else CS(LD, f"population={pop}", cat),
          art=GD, rep=(771 + ["n_neither", "n_diffusion_only", "n_expansion_only", "n_expansion_first", "n_same_year", "n_diffusion_first"].index(cat), pre + r"(\d+)"),
          kind="count", tier="C" if pop in ("screen", "mesh") else "R")
c("ll.pooled.ef", "descriptive", "Pooled main expansion-first of dual-onset (25)", "SUPPLEMENTARY", "lead-lag", CS(LD, "population=pooled_main", "n_expansion_first"),
  art=GD, rep=(779, r"expansion precedes diffusion in " + N + r" of 26"), kind="count")
c("ll.pooled.both", "descriptive", "Pooled main dual-onset (26)", "SUPPLEMENTARY", "lead-lag", CS(LD, "population=pooled_main", "n_both"),
  art=GD, rep=(779, r"in 25 of " + N + r" pooled"), kind="count")
c("ll.pooled.ef_sum", "descriptive", "Expansion-first count in opening summary", "SUPPLEMENTARY", "lead-lag", CS(LD, "population=pooled_main", "n_expansion_first"),
  art=GD, rep=(7, r"diffusion in " + N + r" of 26"), kind="count", headline=True)
c("ll.mesh.ef", "descriptive", "MeSH expansion-first of dual-onset", "MESH", "lead-lag", CS(LD, "population=mesh", "n_expansion_first"), art=GD, rep=(779, r"On MeSH, " + N + r" of 13"), kind="count")
c("ll.mesh.null_p", "descriptive", "MeSH lead-lag year-shuffle null p", "MESH", "lead-lag null", J(P4 + "/mesh_results.json", "leadlag/null/p_one_sided_greater"),
  art=GD, hyp=r"null 0\.62, p " + N, kind="p", known="K12_mesh_leadlag")
c("ll.logrank", "descriptive", "Pooled log-rank censoring p", "SUPPLEMENTARY", "censoring", CS(LD, "population=pooled_main", "logrank_p"), art=GD, hyp=r"log-rank p " + N, kind="p")
c("ll.granger_b", "descriptive", "Granger panel b (dP -> dH)", "SCREEN", "Granger panel", J(P4 + "/leadlag_table.json", "screen/granger_panel/dH_on_lags/coefs/dP_l1/b"), art=GD, hyp=r"Granger panel is b " + N)
c("ll.restricted", "descriptive", "F <= 2012 dual-onset concepts (pooled)", "SUPPLEMENTARY", "censoring", CS(LD, "population=pooled_main", "restricted_n_both"), art=GD, hyp=r"cohort has only " + N + r" dual-onset", kind="count")
c("ll.share_both", "descriptive", "Share of main concepts with both onsets", "SUPPLEMENTARY", "lead-lag", "recompute:leadlag_share_both_pooled", art=GD, rep=(781, r"only " + N + r" of main-arm concepts have both"), kind="pct", tier="C")
c("typ.ho.broad", "descriptive", "Held-out BROAD share", "CONFIRMATORY", "typology E1", J(P4 + "/confirmation_report.json", "confirmation/E1/by_cluster/broad from the start (rapid interdisciplinary)/heldout_share"),
  art=GD, rep=(787, r"BROAD share " + N + r" \(held-out\)"))
c("typ.scr.broad", "descriptive", "Screen BROAD share", "SCREEN", "typology", J(P4 + "/confirmation_report.json", "confirmation/E1/by_cluster/broad from the start (rapid interdisciplinary)/screen_share"),
  art=GD, rep=(787, r"\(held-out\) vs " + N + r" \(screen\)"))
c("typ.mesh.broad", "descriptive", "MeSH BROAD share", "MESH", "typology assignment", J(P4 + "/mesh_results.json", "typology/type_shares/broad from the start (rapid interdisciplinary)/share"),
  art=GD, rep=(799, r"BROAD share is " + N))
c("typ.mesh.ks", "descriptive", "MeSH typology KS p vs screen", "MESH", "support check", J(P4 + "/mesh_results.json", "typology/distances/ks_vs_screen_d1/p"), art=GD, hyp=r"KS p " + N + r"; BROAD 0\.71", kind="p")
c("typ.mesh.oos", "descriptive", "MeSH out-of-support share", "MESH", "support check", J(P4 + "/mesh_results.json", "typology/distances/out_of_support_d1_gt_screen_p95/share"),
  art=GD, hyp=r"\(" + N + r" out, KS", kind="pct")
c("typ.mesh.cramer", "descriptive", "MeSH type x branch Cramer V", "MESH", "typology", J(P4 + "/mesh_results.json", "typology/crosstabs/branch_group/cramers_v"), art=GD, rep=(799, r"Cramér's V = " + N))
c("roles.mesh.bridge", "descriptive", "MeSH BRIDGE share", "MESH", "roles", J(P4 + "/mesh_results.json", "roles/role_shares/BRIDGE/share"), art=GD, rep=(799, r"BRIDGE " + N + r" \(vs 0\.61"))
c("roles.ho.bridge", "descriptive", "Held-out BRIDGE share", "CONFIRMATORY", "roles", J(P4 + "/confirmation_report.json", "confirmation/E4/heldout_robust_shares/BRIDGE"), art=GD, hyp=r"BRIDGE 0\.61 screen / " + N)
c("e4.ho.bridge_or", "descriptive", "E4 held-out BRIDGE entry-hazard OR", "CONFIRMATORY", "lagged-role entry hazard", J(P4 + "/confirmation_report.json", "confirmation/E4/heldout_ORs/BRIDGE/ratio"), art=GD, hyp=r"0\.64 screen vs " + N)
c("e2.ho.eps1", "descriptive", "E2 held-out eps2 newcomer share", "CONFIRMATORY", "Kruskal-Wallis", J(P4 + "/confirmation_report.json", "confirmation/E2/by_V/V1_newcomer_share/heldout/eps2"), art=GD)
c("root.scr.acont_adj", "descriptive", "Adjusted A_cont BROAD-LOCALISED (screen)", "SCREEN", "d x e FE", J(P4 + "/rooting.json", "screen/model_i_Acont/coef"), art=GD, rep=(795, r"difference: " + N))
c("root.ho.acont_adj", "descriptive", "Adjusted A_cont (held-out)", "CONFIRMATORY", "d x e FE", J(P4 + "/rooting.json", "heldout/model_i_Acont/coef"), art=GD, rep=(795, r"held-out: \+?" + N))
c("root.ho.ct", "descriptive", "CT difference held-out", "CONFIRMATORY", "d x e FE", J(P4 + "/rooting.json", "heldout/model_ii_CT/coef"), art=GD, rep=(795, r"CT difference " + N))
c("root.ho.ct.lo", "descriptive", "CT difference held-out CI low", "CONFIRMATORY", "d x e FE", J(P4 + "/rooting.json", "heldout/model_ii_CT/ci/0"), art=GD, rep=(795, r"CT difference −0\.125 \[" + N))
c("root.scr.ct", "descriptive", "CT difference screen", "SCREEN", "d x e FE", J(P4 + "/rooting.json", "screen/model_ii_CT/coef"), art=GD, hyp=r"REPLICATED: " + N + r" screen")
c("root.scr.raw", "descriptive", "Raw A_cont BROAD minus LOCALISED", "SCREEN", "descriptive", J(P4 + "/rooting.json", "screen/descriptives/diff_BROAD_minus_LOCALISED/A_cont/diff"), art=GD, hyp=r"raw A_cont LOWER, " + N)
c("root.occ.broad", "descriptive", "BROAD entries per concept", "SCREEN", "descriptive", J(P4 + "/rooting.json", "screen/descriptives/occupancy/BROAD/all_main_entries_per_concept"), art=GD, hyp=r"BROAD concepts: " + N)
c("root.est.broad", "descriptive", "BROAD EST rate", "SCREEN", "descriptive", J(P4 + "/rooting.json", "screen/descriptives/BROAD/EST_rate/est"), art=GD, hyp=r"EST " + N + r" vs 0\.13")
c("root.ppml.broad", "descriptive", "PPML A_cont BROAD", "SCREEN", "co-primary by type", J(P4 + "/rooting.json", "screen/model_iii_ppml/BROAD/irr_per_sd"), art=GD, hyp=r"BROAD " + N + r" \[1\.20")
c("root.ppml.loc", "descriptive", "PPML A_cont LOCALISED", "SCREEN", "co-primary by type", J(P4 + "/rooting.json", "screen/model_iii_ppml/LOCALISED/irr_per_sd"), art=GD, hyp=r"LOCALISED " + N)
c("root.ppml.p", "descriptive", "PPML type interaction p", "SCREEN", "co-primary by type", J(P4 + "/rooting.json", "screen/model_iii_ppml/interaction_p"), art=GD, hyp=r"interaction p " + N + r" \(exploratory\)", kind="p")
c("cases.ws.diff", "descriptive", "Wireless backhaul rooted-minus-unrooted A_cont", "SCREEN", "cases", "recompute:case_diff_wireless", art=GD, hyp=r"highest A_cont \(\+" + N, tier="C")
c("cases.epr.diff", "descriptive", "EPR steering rooted-minus-unrooted A_cont", "SCREEN", "cases", "recompute:case_diff_epr", art=GD, hyp=r"\(\+0\.062, \+" + N, tier="C")

# ============================================================ ADOPTER (art_FZ2OCJwV6xHs)
EN = P5 + "/enrichment.json"
VC = P5 + "/vocab_class.json"
c("ad.or", "adopter", "Adopter E_any OR (Table 22)", "SCREEN", "pre-declared primary m2", J(EN, "m2/terms/E_any/OR"), art=GA,
  rep=(811, r"E_any \(any prior partner exposure\) \| " + N), alt=[("WRONG_ESTIMATOR", J(EN, "m1/terms/E_any/OR"))], hyp=r"partners OR " + N, known="K09_or_31x")
c("ad.or.lo", "adopter", "Adopter E_any OR CI low", "SCREEN", "m2", J(EN, "m2/terms/E_any/OR_ci95_boot/0"), art=GA,
  rep=(811, r"exposure\) \| 3\.14 \| \[" + N), alt=[("WRONG_ESTIMATOR", J(EN, "m1/terms/E_any/OR_ci95_boot/0"))])
c("ad.or.hi", "adopter", "Adopter E_any OR CI high", "SCREEN", "m2", J(EN, "m2/terms/E_any/OR_ci95_boot/1"), art=GA,
  rep=(811, r"exposure\) \| 3\.14 \| \[2\.37, " + N), alt=[("WRONG_ESTIMATOR", J(EN, "m1/terms/E_any/OR_ci95_boot/1"))])
c("ad.or.p", "adopter", "Adopter E_any p (CRV)", "SCREEN", "m2", J(EN, "m2/terms/E_any/p_crv"), art=GA,
  rep=(811, r"\[2\.37, 4\.29\] \| " + N), kind="p", alt=[("WRONG_ESTIMATOR", J(EN, "m1/terms/E_any/p_crv"))])
c("ad.or.text", "adopter", "'3.1x more likely' reading of the OR", "SCREEN", "m2", "recompute:adopter_rr", art=GA,
  rep=(816, r"Adopters are " + N + r"× more likely"), tier="C", alt=[("WRONG_DEFINITION", J(EN, "m1/terms/E_any/OR"))], known="K09_or_31x", headline=True,
  replacement="OR 3.09 [2.32, 4.28] (m2); exposure prevalence 0.79 vs 0.61, risk ratio about 1.30")
c("ad.or.text2", "adopter", "'3.1x more likely' in What we have learned", "SCREEN", "m2", "recompute:adopter_rr", art=GA,
  rep=(871, r"are " + N + r"× more likely"), tier="C", alt=[("WRONG_DEFINITION", J(EN, "m1/terms/E_any/OR"))], known="K09_or_31x",
  replacement="OR 3.09; risk ratio about 1.30")
c("ad.prev.case", "adopter", "Exposure prevalence among adopters", "SCREEN", "descriptive", "recompute:adopter_prev_case", art=GA, hyp=r"prevalence " + N + r" vs", tier="C")
c("ad.prev.ctrl", "adopter", "Exposure prevalence among controls", "SCREEN", "descriptive", "recompute:adopter_prev_ctrl", art=GA, hyp=r"prevalence 0\.79 vs " + N, tier="C")
c("ad.neg", "adopter", "E_neg OR", "SCREEN", "m2", J(EN, "m2/terms/E_neg/OR"), art=GA, rep=(812, r"E_neg \(exposure to non-partner concepts\) \| " + N))
c("ad.neg.p", "adopter", "E_neg p", "SCREEN", "m2", J(EN, "m2/terms/E_neg/p_crv"), art=GA, rep=(812, r"\[0\.49, 0\.77\] \| " + N), kind="p",
  alt=[("WRONG_ESTIMATOR", J(VC, "m_voc/terms/E_neg/p_crv"))])
c("ad.plac", "adopter", "E_plac OR", "SCREEN", "m_plac (partner + placebo)", J(EN, "m_plac/terms/E_plac/OR"), art=GA, rep=(813, r"E_plac \(placebo-host exposure\) \| " + N),
  alt=[("WRONG_ESTIMATOR", J(EN, "m_plac_only/terms/E_plac/OR"))], hyp=r"\(PLAC " + N)
c("ad.plac.lo", "adopter", "E_plac CI low", "SCREEN", "m_plac", J(EN, "m_plac/terms/E_plac/OR_ci95_boot/0"), art=GA, rep=(813, r"exposure\) \| 0\.76 \| \[" + N),
  alt=[("WRONG_ESTIMATOR", J(EN, "m_plac_only/terms/E_plac/OR_ci95_boot/0"))])
c("ad.swap", "adopter", "E_swap OR", "SCREEN", "m_swap", J(EN, "m_swap/terms/E_swap/OR"), art=GA, rep=(814, r"E_swap \(exposure swap control\) \| " + N))
c("ad.swap.hi", "adopter", "E_swap CI high", "SCREEN", "m_swap", J(EN, "m_swap/terms/E_swap/OR_ci95_boot/1"), art=GA, rep=(814, r"control\) \| 1\.11 \| \[0\.87, " + N))
for term, lab, line in [("E_for", r"E_for \(FOREIGN partner exposure\)", 824), ("E_adj", r"E_adj \(ADJACENT partner exposure\)", 825),
                        ("E_nat", r"E_nat \(NATIVE partner exposure\)", 826), ("E_neg", r"E_neg \(non-partner exposure\)", 827)]:
    c(f"ad.voc.{term}", "adopter", f"Vocab-class {term} OR", "SCREEN", "m_voc", J(VC, f"m_voc/terms/{term}/OR"), art=GA, rep=(line, lab + r" \| " + N))
    c(f"ad.voc.{term}.lo", "adopter", f"Vocab-class {term} CI low", "SCREEN", "m_voc", J(VC, f"m_voc/terms/{term}/OR_ci95_boot/0"), art=GA, rep=(line, lab + r" \| [\d.]+ \| \[" + N))
    c(f"ad.voc.{term}.hi", "adopter", f"Vocab-class {term} CI high", "SCREEN", "m_voc", J(VC, f"m_voc/terms/{term}/OR_ci95_boot/1"), art=GA, rep=(line, lab + r" \| [\d.]+ \| \[[\d.]+, " + N))
c("ad.int", "adopter", "E_any x A_cont interaction OR", "SCREEN", "m_int", J(P5 + "/interaction.json", "m_int/terms/E_any_x_zA/OR"), art=GA, rep=(831, r"null: OR " + N))
c("ad.med", "adopter", "Gelbach attenuation of A_cont by E_any", "SCREEN", "mediation", J(P5 + "/mediation.json", "point/att/att_M2"), art=GA, rep=(833, r"coefficient by " + N))
c("ad.med.rev", "adopter", "Reverse attenuation", "SCREEN", "mediation", J(P5 + "/mediation.json", "point/att/reverse_att_M2"), art=GA, rep=(833, r"reverse attenuation is " + N))
c("ad.ratio.neg", "adopter", "Partner over non-partner ratio", "SCREEN", "ratios", J(P5 + "/ratios.json", "partner_over_neg/ratio"), art=GA, rep=(835, r"non-partner: " + N))
c("ad.ratio.plac", "adopter", "Partner over placebo ratio", "SCREEN", "ratios", J(P5 + "/ratios.json", "partner_over_plac/ratio"), art=GA, rep=(835, r"placebo-host: " + N))
c("ad.ratio.nf", "adopter", "Native-to-foreign ratio", "SCREEN", "ratios", J(P5 + "/ratios.json", "native_vs_foreign/ratio"), art=GA, rep=(835, r"Native-to-foreign ratio: " + N))
c("ad.strata", "adopter", "Matched strata", "SCREEN", "design", J(P5 + "/mechanism_results.json", "descriptives/n_strata"), art=GA, rep=(805, r"on " + N + r" matched case-control strata"), kind="count")
c("ad.entries", "adopter", "Entries in adopter design", "SCREEN", "design", J(P5 + "/mechanism_results.json", "descriptives/n_entries"), art=GA, rep=(805, r"strata \(" + N + r" entries"), kind="count")
c("ad.concepts", "adopter", "Concepts in adopter design", "SCREEN", "design", J(P5 + "/mechanism_results.json", "descriptives/n_concepts"), art=GA, rep=(805, r"entries, " + N + r" concepts\)"), kind="count")
c("ad.excluded", "adopter", "Adopter pairs with no prior corpus work", "SCREEN", "coverage", J(P5 + "/frame_summary.json", "primary/adopters/share_adopter_pairs_career_new_corpus"), art=GA, hyp=r"Limits: " + N + r" of 21,941", kind="pct")
c("ad.pairs", "adopter", "Adopter pairs total", "SCREEN", "coverage", J(P5 + "/frame_summary.json", "primary/adopters/n_adopter_pairs_total"), art=GA, hyp=r"of " + N + r" adopter pairs", kind="count")
c("ad.origin_check", "adopter", "Origin-subfield check: partner OR given origin", "SUPPLEMENTARY", "post-hoc", J(P5 + "/supplementary.json", "origin_subfield_check/primary/partner_given_origin/terms/E_any/OR"), art=GA)
c("ad.rob.13", "adopter", "1:3 matched OR", "SUPPLEMENTARY", "robustness", J(P5 + "/supplementary.json", "one_to_three_matched/terms/E_any/OR"), art=GA)
c("ad.rob.exp", "adopter", "Expanded frame OR", "SUPPLEMENTARY", "robustness", J(P5 + "/supplementary.json", "expanded_frame_no_concept_cap/terms/E_any/OR"), art=GA)

# ============================================================ DATA / PIPELINE
c("data.concepts", "data", "Hydrated concepts in the frame", "DATA", "corpus", "recompute:n_frame_concepts", art="art_eR1Z7fMlOcxs",
  rep=(3, r"dataset of " + N + r" semantically grounded"), kind="count", tier="C")
c("data.main_screen", "data", "MAIN screen concepts", "DATA", "population", "recompute:n_main_screen", art=G5, rep=(411, r"MAIN screen " + N), kind="count", tier="C")
c("data.main_heldout", "data", "MAIN held-out concepts", "DATA", "population", "recompute:n_main_heldout", art=G5, rep=(411, r"\(102 old / 100 new\), held-out " + N), kind="count", tier="C")
c("data.d2_screen_entries", "data", "Screen MAIN kw5 entries (rooting sample)", "DATA", "population", J(P4 + "/rooting.json", "screen/n_entries"), art=GD, rep=(467, r"Primary sample: " + N), kind="count")
c("data.d2_screen_concepts", "data", "Screen MAIN kw5 concepts", "DATA", "population", J(P4 + "/rooting.json", "screen/n_concepts"), art=GD, rep=(467, r"entries with ≥ 5 partners, in " + N), kind="count")
c("data.heldout_d2_concepts", "data", "Held-out D2 concepts", "DATA", "population", J(P2 + "/heldout_post.json", "n_concepts"), art=GH, rep=(490, r"Held-out.\*\* " + N + r" concepts"), kind="count")
c("data.gateA", "data", "Gate A within-host share >= 0.40", "DATA", "Gate A", J(P1E + "/decision_rules.json", "a/value"), art="art__i2cIye01VnN", rep=(239, r"Only " + N + r" of 724"), kind="pct")
c("data.graft_events", "data", "Graft-route host-entry events (iteration 1 reproduction)", "DATA", "events", J(P7 + "/d2_summary.json", "reproduction_iter1_events/counts/0"), art=G7, rep=(254, r"graft route has " + N), kind="count")
