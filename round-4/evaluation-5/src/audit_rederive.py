#!/usr/bin/env python3
"""Independent re-derivation of the headline numbers through a DIFFERENT code path.

Reads the RAW dataset_5 parquet files (not the vendored prepare() cache, not src/analysis.py) and the frozen frames:
  1. E_any / E_neg / E_plac per stratum member, recomputed with plain Python from works_part_*.parquet
     (author_ids, publication_year, concept_ids/scores, keyword_idx) -> agreement with results/exposures_primary.parquet
  2. primary OR(E_any | E_neg, lp) refit with statsmodels ConditionalLogit (BFGS/Newton, not stats_core.clogit), the
     McNemar discordant-pair OR, and a simple concept-cluster bootstrap of the McNemar OR
  3. placebo: the same statsmodels fit on within-stratum shuffled labels (x50) and on random exposure -> must FAIL
  4. entry-level b_A and attenuation by +M2 refit with pyfixest.fepois (not the vendored ppml.py), plus a
     shuffled-M2 placebo.
Writes results/audit_rederive.json.
"""
from __future__ import annotations

import json
import os
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

WS = Path(__file__).resolve().parent
LOOP = Path(os.environ.get("AII_DEPS_ROOT", WS.parents[2])).resolve()
D5 = LOOP / "round-2" / "." / "gen_art_dataset_5"   # art_eR1Z7fMlOcxs
FR, RES = WS / "frames", WS / "results"
rng = np.random.default_rng(99)


def partner_tags_table(ids: set[int]) -> tuple[dict, dict]:
    """author raw id -> list of (year, work_id, frozenset(tags), subfield_ok, sub); plus work_id -> author ids."""
    i2k = json.loads((D5 / "hyd" / "keywords_dict.json").read_text())["index_to_keyword_id"]
    con = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "concepts.parquet", columns=["concept_id", "display_name", "level"])
    kw = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "keywords.parquet", columns=["keyword_slug", "display_name"])
    name2c = {}
    for c, n in zip(con.concept_id, con.display_name):
        name2c.setdefault(n, int(c[1:]))
    slug2c = {s: name2c.get(n) for s, n in zip(kw.keyword_slug, kw.display_name)}
    level = {int(c[1:]): int(l) for c, l in zip(con.concept_id, con.level)}
    kmap = [slug2c.get(s) for s in i2k]
    by_author = defaultdict(list)
    cols = ["work_id", "publication_year", "author_ids", "concept_ids", "concept_scores", "keyword_idx"]
    for f in sorted((D5 / "hyd" / "works").glob("works_part_*.parquet")):
        t = pq.read_table(f, columns=cols).to_pylist()
        for w in t:
            au = w["author_ids"] or []
            hit = [a for a in au if a in ids]
            if not hit:
                continue
            tags = set()
            for c, s in zip(w["concept_ids"] or [], w["concept_scores"] or []):
                if s >= 0.2:
                    tags.add(int(c))
            for k in w["keyword_idx"] or []:
                m = kmap[k]
                if m is not None:
                    tags.add(m)
            tags = frozenset(x for x in tags if level.get(x) != 0)
            for a in set(hit):
                by_author[a].append((w["publication_year"], w["work_id"], tags))
    return by_author


def main() -> None:
    out = {}
    L = pd.read_parquet(FR / "strata_long.parquet")
    T = pd.read_parquet(FR / "targets.parquet").set_index("entry_id")
    X = pd.read_parquet(RES / "exposures_primary.parquet")
    cw = pd.read_parquet(D5 / "hyd" / "concept_work.parquet", columns=["concept_id", "work_id"])
    cworks = cw.groupby("concept_id").work_id.apply(set).to_dict()
    ids = set(int(x) for x in L.raw_author_id)
    by_author = partner_tags_table(ids)
    rows = []
    for r in L.itertuples():
        t = T.loc[r.entry_id]
        cset = cworks.get(r.concept_id, set())
        used = set()
        for (y, wid, tags) in by_author.get(int(r.raw_author_id), []):
            if y is not None and y <= r.e - 1 and wid not in cset:
                used |= tags
        rows.append({"stratum": r.stratum, "role": r.role, "a_E_any": int(bool(used & set(t.P_nodes))),
                     "a_E_neg": int(bool(used & set(t.NEG_nodes))), "a_E_plac": int(bool(used & set(t.PLAC_nodes)))})
    A = pd.DataFrame(rows)
    M = X.merge(A, on=["stratum", "role"])
    agree = {k: float((M[k] == M["a_" + k]).mean()) for k in ("E_any", "E_neg", "E_plac")}
    out["exposure_agreement_all_members"] = agree
    out["n_members"] = int(len(M))
    D = M[M.role.isin(["case", "control"])].copy()
    D["lp"] = np.log1p(D.n_prior_corpus)
    # 2. statsmodels conditional logit on RE-DERIVED exposures
    from statsmodels.discrete.conditional_models import ConditionalLogit
    def cl_fit(df, cols, y="case"):
        m = ConditionalLogit(df[y].to_numpy(), df[cols].to_numpy(float), groups=df.stratum.to_numpy()).fit(disp=0, method="bfgs", maxiter=500)
        return m.params, m.bse, m.pvalues
    b, se, p = cl_fit(D, ["a_E_any", "a_E_neg", "lp"])
    out["primary_OR_statsmodels_rederived"] = {"OR_E_any": float(np.exp(b[0])), "p": float(p[0]),
                                               "OR_E_neg": float(np.exp(b[1])), "p_neg": float(p[1])}
    w = D.pivot_table(index="stratum", columns="case", values="a_E_any", aggfunc="max")
    n10, n01 = int(((w[1] == 1) & (w[0] == 0)).sum()), int(((w[1] == 0) & (w[0] == 1)).sum())
    out["mcnemar"] = {"n10": n10, "n01": n01, "OR": n10 / n01}
    conc = D.drop_duplicates("stratum").set_index("stratum").concept_id
    pair = pd.DataFrame({"d10": ((w[1] == 1) & (w[0] == 0)).astype(int), "d01": ((w[1] == 0) & (w[0] == 1)).astype(int),
                         "c": conc.reindex(w.index)})
    g = pair.groupby("c")[["d10", "d01"]].sum()
    bs = []
    for _ in range(1000):
        s = g.iloc[rng.integers(0, len(g), len(g))].sum()
        bs.append(s.d10 / s.d01 if s.d01 else np.nan)
    out["mcnemar"]["ci95_concept_boot"] = [float(np.nanquantile(bs, .025)), float(np.nanquantile(bs, .975))]
    # 3. placebos that must fail
    perm = []
    for _ in range(50):
        Dq = D.copy()
        Dq["case"] = Dq.groupby("stratum").case.transform(lambda s: rng.permutation(s.to_numpy()))
        bq, _, pq_ = cl_fit(Dq, ["a_E_any", "a_E_neg", "lp"])
        perm.append((float(np.exp(bq[0])), float(pq_[0])))
    out["placebo_shuffled_labels"] = {"mean_OR": float(np.mean([x[0] for x in perm])),
                                      "share_p_lt_0.05": float(np.mean([x[1] < 0.05 for x in perm]))}
    Dr = D.copy()
    Dr["rand"] = rng.integers(0, 2, len(Dr))
    br, _, pr = cl_fit(Dr, ["rand", "a_E_neg", "lp"])
    out["placebo_random_exposure"] = {"OR": float(np.exp(br[0])), "p": float(pr[0])}
    # 4. entry-level b_A + M2 attenuation with pyfixest (different estimator code)
    import pyfixest as pf
    E = pd.read_parquet(FR / "entries.parquet")
    ctrl = ["CT", "prox_od", "RD", "log_n_partner_tags", "cov", "demic", "mean_topic_score", "boundary_share",
            "abstract_share", "mom_d", "log_centrality", "log_W1"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f0 = pf.fepois(f"Y_strict ~ A_cont + {' + '.join(ctrl)} | concept_id + e + d", data=E, offset="offset",
                       vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-12, iwls_tol=1e-12, iwls_maxiter=500)
        f1 = pf.fepois(f"Y_strict ~ A_cont + {' + '.join(ctrl)} + M2 | concept_id + e + d", data=E, offset="offset",
                       vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-12, iwls_tol=1e-12, iwls_maxiter=500)
        E2 = E.copy()
        E2["M2_shuf"] = rng.permutation(E2.M2.to_numpy())
        f2 = pf.fepois(f"Y_strict ~ A_cont + {' + '.join(ctrl)} + M2_shuf | concept_id + e + d", data=E2, offset="offset",
                       vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-12, iwls_tol=1e-12, iwls_maxiter=500)
    b0, b1 = float(f0.coef()["A_cont"]), float(f1.coef()["A_cont"])
    out["pyfixest_entry_level"] = {"b_A_base": b0, "b_A_plus_M2": b1, "attenuation_M2": (b0 - b1) / b0,
                                   "M2_p": float(f1.pvalue()["M2"]), "n": int(f0._N),
                                   "placebo_shuffled_M2_attenuation": (b0 - float(f2.coef()["A_cont"])) / b0,
                                   "placebo_shuffled_M2_p": float(f2.pvalue()["M2_shuf"])}
    json.dump(out, open(RES / "audit_rederive.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
