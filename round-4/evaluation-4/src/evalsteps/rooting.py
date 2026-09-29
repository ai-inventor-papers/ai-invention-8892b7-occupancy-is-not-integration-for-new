"""STEP 2c/2d: type x occupancy / rooting (screen, held-out W1, pooled W1) and host share per lagged role."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from loguru import logger

from base import BROAD, E7, E8, HO, LOCAL, RES, TYPE_SHORT, cluster_boot_many, sha256, write_json

CTRL_EVENT = ["prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share", "abstract_share"]
CTRL_SEC = ["mom_d", "log_centrality", "log_W1"]
FORBIDDEN = ("Y_", "EST", "n_w2", "w2_", "present_")


def d2_sample(df: pd.DataFrame, fold: str) -> pd.DataFrame:
    s = df[(df.arm == "main") & (df.fold == fold) & df.kw5 & df.MAIN].copy()
    need = ["A_cont", "CT"] + CTRL_EVENT + CTRL_SEC
    return s.dropna(subset=[c for c in need if c in s.columns]).reset_index(drop=True)


def load_heldout_w1() -> pd.DataFrame:
    p = E7 / "sealed/heldout_features.parquet"
    want = (E7 / "sealed/heldout_features.sha256").read_text().split()[0]
    got = sha256(p)
    assert got == want, f"held-out features sha256 mismatch {got} != {want}"
    h = pd.read_parquet(p)
    bad = [c for c in h.columns if c.startswith(FORBIDDEN)]
    assert not bad, f"outcome/W2 columns present in held-out features: {bad}"
    return h


def descriptives(s: pd.DataFrame, all_main: pd.DataFrame, with_outcomes: bool, B: int = 2000) -> dict:
    out = {}
    for t, g in s.groupby("type"):
        stats = {"A_cont_mean": lambda d: d.A_cont.mean(), "A_cont_concept_avg": lambda d: d.groupby("concept_id").A_cont.mean().mean(),
                 "excess_A": lambda d: (d.A_cont - d.A0_cont).mean(), "CT_mean": lambda d: d.CT.mean(),
                 "anchored_share": lambda d: d.anchored.astype(float).mean() if d.anchored.notna().any() else np.nan}
        if with_outcomes:
            stats.update({"Y_strict_mean": lambda d: d.Y_strict.mean(), "Y_pos_share": lambda d: (d.Y_strict > 0).mean(),
                          "EST_rate": lambda d: d.EST_bin.mean(), "rooted_share": lambda d: d.groupby("concept_id").EST_bin.mean().mean()})
        b = cluster_boot_many(g, stats, B=B, seed=1)
        b["A_cont_median"] = float(g.A_cont.median())
        b["n_entries"] = len(g)
        b["n_concepts"] = int(g.concept_id.nunique())
        out[t] = b
    # occupancy: entries per concept, all MAIN kw-any entries and co-primary sample (concepts with 0 entries included)
    occ = {}
    for t in ("BROAD", "LOCALISED"):
        a = all_main[all_main.type == t]
        occ[t] = dict(all_main_entries_per_concept=float(a.groupby("concept_id").size().mean()) if len(a) else None,
                      coprimary_entries_per_concept=float(s[s.type == t].groupby("concept_id").size().mean()) if (s.type == t).any() else None)
    out["occupancy"] = occ
    # type difference (BROAD - LOCALISED) by concept-cluster bootstrap, stratified by type
    diffs = {}
    keys = ["A_cont", "CT"] + (["Y_strict", "EST_bin"] if with_outcomes else [])
    rng = np.random.default_rng(7)
    gb = {t: {c: g for c, g in s[s.type == t].groupby("concept_id")} for t in ("BROAD", "LOCALISED")}
    obs = {k: s[s.type == "BROAD"][k].mean() - s[s.type == "LOCALISED"][k].mean() for k in keys}
    draws = {k: [] for k in keys}
    for _ in range(B):
        m = {}
        for t in ("BROAD", "LOCALISED"):
            cs = list(gb[t])
            pick = rng.integers(0, len(cs), len(cs))
            m[t] = pd.concat([gb[t][cs[i]] for i in pick])
        for k in keys:
            draws[k].append(m["BROAD"][k].mean() - m["LOCALISED"][k].mean())
    for k in keys:
        diffs[k] = dict(diff=obs[k], ci=np.percentile(draws[k], [2.5, 97.5]).tolist())
    out["diff_BROAD_minus_LOCALISED"] = diffs
    return out


def feols(s: pd.DataFrame, y: str) -> dict:
    import pyfixest as pf
    d = s.copy()
    d["BROAD"] = (d.type == "BROAD").astype(float)
    d["dxe"] = d.d.astype(str) + "_" + d.e.astype(str)
    extra = " + C(fold)" if d.fold.nunique() > 1 else ""
    f = pf.feols(f"{y} ~ BROAD + log_n_partner_tags + RD{extra} | dxe", data=d, vcov={"CRV1": "concept_id"})
    t = f.tidy()
    r = t.loc["BROAD"]
    return dict(y=y, n=int(f._N), n_concepts=int(d.concept_id.nunique()), coef=float(r["Estimate"]), se=float(r["Std. Error"]),
                p=float(r["Pr(>|t|)"]), ci=[float(r["2.5%"]), float(r["97.5%"])], sd_y=float(d[y].std()),
                coef_in_sd=float(r["Estimate"]) / float(d[y].std()), fe="host x entry year (d x e)", cluster="concept")


def ppml_interaction(s: pd.DataFrame) -> dict:
    import sys
    sys.path.insert(0, str(E7 / "src"))
    import ppml
    d = s.copy()
    d["BROAD"] = (d.type == "BROAD").astype(float)
    sdA = d.A_cont.std()
    d["A_x_BROAD"] = d.A_cont * d.BROAD
    xv = ["A_cont", "A_x_BROAD", "CT"] + CTRL_EVENT + CTRL_SEC
    fes = [pd.factorize(d.concept_id)[0], pd.factorize(d.e.astype(str))[0], pd.factorize(d.d.astype(str))[0]]
    off = np.log(d.n_entry_papers.astype(float).to_numpy())
    r = ppml.fit(d.Y_strict.to_numpy(float), d[xv].to_numpy(float), fes, off, d.concept_id.to_numpy(), maxit=500, tol=1e-12)
    d["A_x_LOCAL"] = d.A_cont * (1 - d.BROAD)
    xv2 = ["A_x_LOCAL", "A_x_BROAD", "CT"] + CTRL_EVENT + CTRL_SEC
    r2 = ppml.fit(d.Y_strict.to_numpy(float), d[xv2].to_numpy(float), fes, off, d.concept_id.to_numpy(), maxit=500, tol=1e-12)
    if r is None or r2 is None:
        return dict(note="PPML did not converge")
    from scipy.stats import norm
    bi, sei = float(r["coef"][1]), float(r["se"][1])
    irr = lambda bb, se: dict(coef=float(bb), se=float(se), irr_per_sd=float(np.exp(bb * sdA)),
                              ci=[float(np.exp((bb - 1.96 * se) * sdA)), float(np.exp((bb + 1.96 * se) * sdA))],
                              p=float(2 * norm.sf(abs(bb / se))))
    return dict(n_retained=int(r["n"]), G=int(r["G"]), sd_A_cont=float(sdA), LOCALISED=irr(r2["coef"][0], r2["se"][0]),
                BROAD=irr(r2["coef"][1], r2["se"][1]), interaction_coef=bi, interaction_se=sei,
                interaction_p=float(2 * norm.sf(abs(bi / sei))), fe="concept + e + host (D2 co-primary)",
                note="exploratory; type main effect absorbed by concept FE")


def role_host_share(ev: pd.DataFrame, roles: pd.DataFrame, with_outcomes: bool) -> dict:
    r = roles[["concept_id", "year", "role_modal", "robust", "GA_class"]].copy()
    r["role_lag"] = np.where(r.robust, r.role_modal, "NONROBUST")
    r["year"] = r.year + 1  # role in e-1 attaches to entry year e
    m = ev.merge(r.rename(columns={"year": "e"}), on=["concept_id", "e"], how="left")
    m["role_lag"] = m.role_lag.fillna("NO_ROLE_ROW")
    m["GA_class"] = m.GA_class.fillna("NO_ROLE_ROW")
    out = {}
    for by in ("role_lag", "GA_class"):
        tab = {}
        for k, g in m.groupby(by):
            st = {"A_cont": lambda d: d.A_cont.mean(), "CT": lambda d: d.CT.mean()}
            if with_outcomes:
                st["EST_rate"] = lambda d: d.EST_bin.mean()
            b = cluster_boot_many(g, st, B=1000, seed=3)
            b["n_entries"] = len(g)
            b["n_concepts"] = int(g.concept_id.nunique())
            tab[str(k)] = b
        out[by] = tab
    return out


def run() -> dict:
    ev = pd.read_parquet(E7 / "results/screen_events_with_outcomes.parquet")
    gl = pd.read_parquet(E7 / "results/graft_labels_screen.parquet")[["concept_id", "d", "e", "anchored"]]
    asg_s = pd.read_csv(E8 / "typology/assignments.csv")[["concept_id", "cluster_name"]]
    ev = ev.merge(gl, on=["concept_id", "d", "e"], how="left")
    ev["type"] = ev.concept_id.map(asg_s.set_index("concept_id").cluster_name.map(TYPE_SHORT))
    all_main_s = ev[(ev.arm == "main") & (ev.fold == "screen") & ev.MAIN & ev.type.notna()]
    s = d2_sample(ev, "screen")
    s = s[s.type.notna()].reset_index(drop=True)
    out = dict(spec_sha256=sha256(RES / "rooting_spec.json"), screen=dict(label="descriptive (screened data)", n_entries=len(s),
               n_concepts=int(s.concept_id.nunique()), n_unmatched_concepts=int(d2_sample(ev, "screen").type.isna().sum())))
    out["screen"]["descriptives"] = descriptives(s, all_main_s, True)
    out["screen"]["model_i_Acont"] = feols(s, "A_cont")
    out["screen"]["model_ii_CT"] = feols(s, "CT")
    try:
        out["screen"]["model_iii_ppml"] = ppml_interaction(s)
    except (KeyError, ValueError, np.linalg.LinAlgError) as e:
        logger.exception("PPML interaction failed")
        out["screen"]["model_iii_ppml"] = dict(error=repr(e))
    # A_cont quintile x type EST rate (for F2b)
    s["A_q"] = pd.qcut(s.A_cont.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["screen"]["EST_by_Aq_type"] = {f"{t}_q{q}": dict(n=len(g), EST_rate=float(g.EST_bin.mean())) for (t, q), g in s.groupby(["type", "A_q"])}
    roles_s = pd.read_parquet(E8 / "results/roles.parquet")
    out["screen"]["host_share_per_role"] = role_host_share(s, roles_s, True)
    s.assign(population="screen").to_parquet(RES / "rooting_screen_sample.parquet", index=False)
    # ---- held-out W1
    ho_asg = HO / "typology/assignments.csv"
    if ho_asg.exists():
        h = load_heldout_w1()
        gh = pd.read_parquet(E7 / "sealed/graft_labels_heldout.parquet")[["concept_id", "d", "e", "anchored"]]
        h = h.merge(gh, on=["concept_id", "d", "e"], how="left")
        a = pd.read_csv(ho_asg)[["concept_id", "cluster_name"]]
        h["type"] = h.concept_id.map(a.set_index("concept_id").cluster_name.map(TYPE_SHORT))
        fold_h = h.fold.iloc[0]
        all_main_h = h[(h.arm == "main") & h.MAIN & h.type.notna()]
        sh = d2_sample(h, fold_h)
        n_unm = int(sh.type.isna().sum())
        sh = sh[sh.type.notna()].reset_index(drop=True)
        ho = dict(label="held-out W1 (confirmatory in spirit: association)", fold_value=fold_h, n_entries=len(sh),
                  n_concepts=int(sh.concept_id.nunique()), n_entries_without_type=n_unm)
        ho["descriptives"] = descriptives(sh, all_main_h, False)
        ho["model_i_Acont"] = feols(sh, "A_cont")
        ho["model_ii_CT"] = feols(sh, "CT")
        sc = out["screen"]["model_i_Acont"]
        hi = ho["model_i_Acont"]
        ho["prediction_holds"] = bool(np.sign(hi["coef"]) == np.sign(sc["coef"]) and (hi["ci"][0] > 0 or hi["ci"][1] < 0))
        ho["prediction_direction_declared"] = "BROAD higher A_cont (coef > 0)"
        ho["declared_direction_confirmed"] = bool(hi["coef"] > 0 and hi["ci"][0] > 0)
        roles_h = pd.read_parquet(HO / "results/roles.parquet") if (HO / "results/roles.parquet").exists() else None
        if roles_h is not None:
            ho["host_share_per_role"] = role_host_share(sh, roles_h, False)
        out["heldout"] = ho
        pool = pd.concat([s.assign(fold="screen"), sh.assign(fold="heldout")], ignore_index=True)
        out["pooled_W1"] = dict(n_entries=len(pool), n_concepts=int(pool.concept_id.nunique()), model_i_Acont=feols(pool, "A_cont"),
                                model_ii_CT=feols(pool, "CT"))
        sh.assign(population="heldout").to_parquet(RES / "rooting_heldout_sample_W1.parquet", index=False)
    write_json(RES / "rooting.json", out)
    return out
