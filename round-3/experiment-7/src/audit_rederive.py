"""Independent re-derivation: A_cont, CT and Y_strict for 20 random screen events with plain Python loops read directly
from the raw dataset_5 files (no shared cache, no CSR code), plus the headline b_A with pyfixest.fepois.

  .venv/bin/python audit_rederive.py      -> results/audit_rederive.json
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import orjson
import pandas as pd
import pyarrow.parquet as pq

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))
from config import D5, RESULTS, SEED  # noqa: E402


def main() -> None:
    ev = pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet")
    ev = ev[ev.MAIN & ev.kw5].dropna(subset=["A_cont"])
    rng = np.random.default_rng(SEED)
    pick = ev.iloc[rng.choice(len(ev), 20, replace=False)]
    # raw inputs
    cols = ["work_id", "publication_year", "subfield_id", "topic_score", "author_ids", "keyword_idx", "concept_ids",
            "concept_scores", "n_refs"]
    works = pd.concat([pq.read_table(p, columns=cols).to_pandas()
                       for p in sorted((D5 / "hyd" / "works").glob("works_part_*.parquet"))], ignore_index=True)
    i2k = orjson.loads((D5 / "hyd" / "keywords_dict.json").read_bytes())["index_to_keyword_id"]
    con = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "concepts.parquet", columns=["concept_id", "display_name", "level"])
    kwd = pd.read_parquet(D5 / "deps" / "gen_art_dataset_2" / "keywords.parquet", columns=["keyword_slug", "display_name"])
    name2c = {}
    for c, n in zip(con.concept_id, con.display_name):
        name2c.setdefault(n, int(c[1:]))
    slug2c = {s: name2c.get(n) for s, n in zip(kwd.keyword_slug, kwd.display_name)}
    level = {int(c[1:]): int(lv) for c, lv in zip(con.concept_id, con.level)}
    prof = {}
    for line in (D5 / "p2" / "profiles.jsonl").read_bytes().splitlines():
        if line.strip():
            r = orjson.loads(line)
            unk = r["subfield_counts"].get("unknown", 0)
            prof[(int(r["node_id"][1:]), r["block"])] = (r["total"] - unk, r["subfield_counts"])
    pool = orjson.loads((D5 / "hyd" / "data_out.json").read_bytes())
    own = {}
    for ds in pool["datasets"]:
        if ds["dataset"] == "concept_pool_2005_2016":
            for e in ds["examples"]:
                lk = (orjson.loads(e["input"]).get("links") or {}).get("legacy_concept_id")
                own[e["metadata_concept_id"]] = int(lk[1:]) if lk else None
    cw = pd.read_parquet(D5 / "hyd" / "concept_work.parquet")
    W = works.set_index("work_id")
    by_year = defaultdict(list)
    for wid, y, au in zip(works.work_id, works.publication_year, works.author_ids):
        by_year[int(y)].append(set(au) if au is not None else set())

    def partners(wid, drop):
        r = W.loc[wid]
        s = set()
        for c, sc in zip(r.concept_ids if r.concept_ids is not None else [], r.concept_scores if r.concept_scores is not None else []):
            if sc >= 0.2:
                s.add(int(c))
        for k in (r.keyword_idx if r.keyword_idx is not None else []):
            c = slug2c.get(i2k[k])
            if c is not None:
                s.add(c)
        return [x for x in s if level.get(x) != 0 and x != drop]

    def known_sub(wid):
        r = W.loc[wid]
        return int(r.subfield_id) if pd.notna(r.subfield_id) and r.topic_score >= 0.05 else -1

    rows = []
    for ev_ in pick.itertuples():
        cid, d, e, o = ev_.concept_id, int(ev_.d), int(ev_.e), int(ev_.o)
        lk = cw[cw.concept_id == cid].copy()
        lk["n_refs"] = [W.loc[w].n_refs if w in W.index else 0 for w in lk.work_id]
        lk["g"] = [("g%d" % g) if pd.notna(g) else ("w%d" % w) for g, w in zip(lk.dup_group, lk.work_id)]
        lk = lk.sort_values(["g", "year", "n_refs", "work_id"], ascending=[True, True, False, True]).drop_duplicates("g")
        papers = [(int(w), int(y), known_sub(int(w))) for w, y in zip(lk.work_id, lk.year)]
        blk = {2005: "2000-2004", 2010: "2005-2009", 2015: "2010-2014"}[2005 if e < 2010 else 2010 if e < 2015 else 2015]
        tags = []
        for w, y, s in papers:
            if s == d and y == e:
                tags += partners(w, own[cid])
        comp = set()
        for w, y, s in papers:
            if s == o and e - 5 <= y <= e - 1:
                comp |= set(partners(w, own[cid]))
        shares = []
        for j in tags:
            if (j, blk) in prof:
                tot, cnt = prof[(j, blk)]
                shares.append(cnt.get(str(d), 0) / tot if tot > 0 else 0.0)
        A = sum(shares) / len(shares) if shares else float("nan")
        CT = sum(1 for j in tags if j in comp) / len(tags) if tags else float("nan")
        seeds = set()
        for w, y, s in papers:
            if e - 5 <= y <= e:
                au = W.loc[w].author_ids
                seeds |= set(au) if au is not None else set()
        pset = set(seeds)
        for yy in range(e - 5, e + 1):
            for au in by_year[yy]:
                if au & seeds:
                    pset |= au
        ys = 0
        for w, y, s in papers:
            if s == d and e + 1 <= y <= e + 5:
                au = W.loc[w].author_ids
                if au is not None and len(au) and not (set(au) & pset):
                    ys += 1
        rows.append({"concept_id": cid, "d": d, "e": e, "A_cont_loop": A, "A_cont_pipeline": float(ev_.A_cont),
                     "CT_loop": CT, "CT_pipeline": float(ev_.CT), "Y_strict_loop": ys,
                     "Y_strict_pipeline": int(ev_.Y_strict)})
    t = pd.DataFrame(rows)
    ok = bool(np.allclose(t.A_cont_loop, t.A_cont_pipeline, atol=1e-12) and np.allclose(t.CT_loop, t.CT_pipeline, atol=1e-12)
              and (t.Y_strict_loop == t.Y_strict_pipeline).all())
    # headline coefficient with pyfixest (co-primary secondary FE)
    import models
    import pyfixest as pf
    df = pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet")
    s = models.primary_sample(df)
    xs = ["A_cont", "CT"] + models.EVENT_CONTROLS + models.SECONDARY_EXTRA
    own_fit = models.fit_one(s, "Y_strict", xs, "secondary")
    import ppml
    rr = ppml.fit(s.Y_strict.to_numpy(float), s[xs].to_numpy(float), models.fe_arrays(s, "secondary"),
                  s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.fepois(f"Y_strict ~ {' + '.join(xs)} | cfe + efe + dfe", data=s[rr["keep"]], offset="offset",
                      vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-10, iwls_tol=1e-10,
                      iwls_maxiter=300)
    head = {"b_A_pipeline": own_fit["coef"]["A_cont"], "b_A_pyfixest": float(m.coef()["A_cont"]),
            "se_A_pipeline": own_fit["se"]["A_cont"], "se_A_pyfixest": float(m.se()["A_cont"])}
    head["match_1e-4"] = abs(head["b_A_pipeline"] - head["b_A_pyfixest"]) < 1e-4
    # shuffled-input check: the same pyfixest test with Y_strict permuted within concept must NOT be significant
    shuf = []
    rs = np.random.default_rng(SEED + 99)
    for i in range(40):
        d = s[rr["keep"]].copy()
        y = d.Y_strict.to_numpy().copy()
        for _, ix in d.groupby("cfe").indices.items():
            y[ix] = y[ix][rs.permutation(len(ix))]
        d["Y_strict"] = y
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mm = pf.fepois(f"Y_strict ~ {' + '.join(xs)} | cfe + efe + dfe", data=d, offset="offset",
                           vcov={"CRV1": "concept_id"}, demeaner_backend="scipy")
        shuf.append({"b_A": float(mm.coef()["A_cont"]), "p_A": float(mm.pvalue()["A_cont"]),
                     "z_A": float(mm.coef()["A_cont"] / mm.se()["A_cont"])})
    z_obs = float(m.coef()["A_cont"] / m.se()["A_cont"])
    head["shuffled_within_concept"] = shuf
    head["shuffled_share_significant_p05"] = float(np.mean([x["p_A"] < 0.05 for x in shuf]))
    head["z_obs"] = z_obs
    head["shuffled_share_abs_z_ge_obs"] = float(np.mean([abs(x["z_A"]) >= abs(z_obs) for x in shuf]))
    head["shuffled_z_sd"] = float(np.std([x["z_A"] for x in shuf], ddof=1))
    # establishment by graft label, re-derived from the raw parquet files with plain pandas
    so = pd.read_parquet(RESULTS / "screen_events_with_outcomes.parquet")
    lab = pd.read_parquet(RESULTS / "graft_labels_screen.parquet")
    mm_ = so[so.MAIN & so.kw5].merge(lab[["concept_id", "d", "e", "anchored"]], on=["concept_id", "d", "e"])
    est = {"n": int(len(mm_)), "EST_bin_anchored": float(mm_[mm_.anchored].EST_bin.mean()),
           "EST_bin_unanchored": float(mm_[~mm_.anchored].EST_bin.mean()),
           "anchored_share": float(mm_.anchored.mean())}
    summ = json.loads((RESULTS / "labels_summary.json").read_text())["establishment_by_label_screen_MAIN"]["EST_bin"]
    est["match_labels_summary"] = bool(abs(est["EST_bin_anchored"] - summ["anchored"]) < 1e-12 and
                                       abs(est["EST_bin_unanchored"] - summ["unanchored"]) < 1e-12)
    out = {"events_checked": len(t), "all_match": ok, "rows": t.to_dict(orient="records"), "headline_secondary": head,
           "establishment_by_label": est}
    (RESULTS / "audit_rederive.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"all_match": ok, **{k: v for k, v in head.items() if k != "shuffled_within_concept"}, **est},
                     default=float))


if __name__ == "__main__":
    main()
