#!/usr/bin/env python3
"""Independent re-derivation audit (T8), run AFTER stage 10.

Plain Python loops over the RAW MeSH works rows (works/*.jsonl.gz), the raw profile files and the keyword/concept
tables. It shares no code with src/ except path constants:
  * 20 random MESH_MAIN events whose partners all have exact profiles: A_cont, CT, n_tags, Y_strict, Y_all
  * R2 (co-primary) b_A re-estimated with pyfixest.fepois on the retained sample (must match to 1e-4)
Writes results/audit_rederive.json.
"""
from __future__ import annotations

import gzip
import json
import random
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import pandas as pd

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "src"))
import common  # noqa: E402  (paths only)


def load_raw():
    rows = []
    for p in sorted((common.MESH / "works").glob("works_part_*.jsonl.gz")):
        with gzip.open(p, "rt") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def main() -> None:
    random.seed(common.SEED)
    om = pd.read_parquet(WS / "results" / "outcomes_mesh.parquet")
    cand = om[om.nat_source == "exact"]
    pick = cand.sample(20, random_state=common.SEED)
    con = pd.read_parquet(common.D5 / "deps" / "gen_art_dataset_2" / "concepts.parquet",
                          columns=["concept_id", "display_name", "level"])
    kw = pd.read_parquet(common.D5 / "deps" / "gen_art_dataset_2" / "keywords.parquet",
                         columns=["keyword_slug", "display_name"])
    name2c, level, fold = {}, {}, defaultdict(set)
    for cid, n, lv in zip(con.concept_id, con.display_name, con.level):
        name2c.setdefault(n, int(cid[1:]))
        level[int(cid[1:])] = int(lv)
        if isinstance(n, str):
            fold[n.casefold().strip()].add(int(cid[1:]))
    slug2c = {s: name2c[n] for s, n in zip(kw.keyword_slug, kw.display_name) if n in name2c}
    prof = {}
    for f in (common.D5 / "p2" / "profiles.jsonl", WS / "results" / "nativeness" / "profiles_fetched.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                key = (int(r["node_id"][1:]), r["block"])
                if key in prof:
                    continue
                sc = r["subfield_counts"]
                tot = r["total"] - sc.get("unknown", 0)
                prof[key] = (tot, {int(k): v for k, v in sc.items() if k != "unknown"})
    raw = load_raw()
    cmeta = {}
    for r in json.loads((common.MESH / "data_out.json").read_text()):
        inp = r["input"] if isinstance(r["input"], dict) else json.loads(r["input"])
        forms = {inp["preferred_term"], *(inp.get("surface_forms") or []), *(inp.get("acronyms") or [])}
        own = set()
        for fm in forms:
            own |= fold.get(str(fm).casefold().strip(), set())
        cmeta[inp["concept_id"]] = {"o": int(inp["origin_subfield"]), "own": own}
    works = {}
    by_c = defaultdict(dict)
    for r in raw:
        w = int(r["work_id"])
        works.setdefault(w, r)
        if r.get("verified_text_match"):
            by_c[r["concept_id"]][w] = r

    def partners(r, own):
        s = set()
        for c in r.get("concepts") or []:
            if c["score"] >= 0.3:
                s.add(int(c["id"]))
        for k in r.get("keywords") or []:
            if k["id"] in slug2c:
                s.add(slug2c[k["id"]])
        return [x for x in s if level.get(x) != 0 and x not in own]

    def sub(r):
        return int((r.get("primary_topic") or {}).get("subfield_id") or -1)

    def authors(r):
        return {int(a["author_id"]) for a in (r.get("authorships") or []) if a.get("author_id") is not None}

    def blk(e):
        return "2000-2004" if e < 2010 else ("2005-2009" if e < 2015 else "2010-2014")

    out = []
    for ev in pick.itertuples():
        cm = cmeta[ev.concept_id]
        cw = by_c[ev.concept_id]
        # DOI dedup as in load_mesh: keep earliest year then min work_id among same normalised DOI
        seen, keep = {}, {}
        for w, r in sorted(cw.items(), key=lambda kv: (kv[1]["publication_year"], kv[0])):
            d = (r.get("doi") or "").lower().replace("https://doi.org/", "").strip() or None
            if d and d in seen:
                continue
            if d:
                seen[d] = w
            keep[w] = r
        e, d_, o = int(ev.e), int(ev.d), cm["o"]
        ent = [r for r in keep.values() if sub(r) == d_ and r["publication_year"] == e]
        tags = [j for r in ent for j in partners(r, cm["own"])]
        comp = set()
        for r in keep.values():
            if sub(r) == o and e - 5 <= r["publication_year"] <= e - 1:
                comp |= set(partners(r, cm["own"]))
        sh = []
        for j in tags:
            p = prof.get((j, blk(e)))
            if p is not None:
                sh.append(p[1].get(d_, 0) / p[0] if p[0] > 0 else 0.0)
        a_cont = sum(sh) / len(sh) if sh else None
        ct = sum(1 for j in tags if j in comp) / len(tags) if tags else None
        seeds = set()
        for r in keep.values():
            if e - 5 <= r["publication_year"] <= e:
                seeds |= authors(r)
        pset = set(seeds)
        for r in works.values():
            if e - 5 <= r["publication_year"] <= e:
                a = authors(r)
                if a & seeds:
                    pset |= a
        ys = ya = 0
        for r in keep.values():
            if sub(r) == d_ and e + 1 <= r["publication_year"] <= e + 5:
                ya += 1
                a = authors(r)
                if a and not (a & pset):
                    ys += 1
        out.append({"concept_id": ev.concept_id, "d": d_, "e": e, "A_cont_pipeline": ev.A_cont, "A_cont_audit": a_cont,
                    "CT_pipeline": ev.CT, "CT_audit": ct, "n_tags_pipeline": int(ev.n_tags), "n_tags_audit": len(tags),
                    "Y_strict_pipeline": int(ev.Y_strict), "Y_strict_audit": ys, "Y_all_pipeline": int(ev.Y_all),
                    "Y_all_audit": ya})
    df = pd.DataFrame(out)
    ok_events = bool(((df.A_cont_pipeline - df.A_cont_audit).abs().max() < 1e-9)
                     and ((df.CT_pipeline - df.CT_audit).abs().max() < 1e-9)
                     and (df.n_tags_pipeline == df.n_tags_audit).all()
                     and (df.Y_strict_pipeline == df.Y_strict_audit).all() and (df.Y_all_pipeline == df.Y_all_audit).all())
    # R2 via pyfixest on the retained sample
    import pyfixest as pf
    g4 = json.loads((WS / "results" / "g4_models.json").read_text())
    spec = json.loads((WS / "results" / "mesh_spec.json").read_text())
    sc = spec["models"]["secondary_controls"]
    import ppml  # vendored estimator only to obtain the iterated-pruning retained sample
    from models_mesh import sample
    import models as vmodels
    s = sample(om, ["A_cont", "CT"] + sc)
    xv = ["A_cont", "CT"] + sc
    rr = ppml.fit(s.Y_strict.to_numpy(float), s[xv].to_numpy(float), vmodels.fe_arrays(s, "secondary"),
                  s.offset.to_numpy(), s.concept_id.to_numpy(), maxit=500, tol=1e-12)
    dd = s[rr["keep"]].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pf.fepois(f"Y_strict ~ {' + '.join(xv)} | cfe + efe + dfe", data=dd, offset="offset",
                      vcov={"CRV1": "concept_id"}, demeaner_backend="scipy", fixef_tol=1e-12, iwls_tol=1e-12,
                      iwls_maxiter=500)
    b_pf = float(m.coef()["A_cont"])
    b_pipe = g4["rows"]["R2"]["row"]["A_cont"]["b"]
    res = {"n_events_checked": int(len(df)), "events_all_match": ok_events,
           "max_abs_diff_A_cont": float((df.A_cont_pipeline - df.A_cont_audit).abs().max()),
           "max_abs_diff_CT": float((df.CT_pipeline - df.CT_audit).abs().max()),
           "Y_strict_mismatches": int((df.Y_strict_pipeline != df.Y_strict_audit).sum()),
           "R2": {"b_A_pipeline": b_pipe, "b_A_pyfixest": b_pf, "abs_diff": abs(b_pipe - b_pf),
                  "match_1e-4": abs(b_pipe - b_pf) < 1e-4, "n_pyfixest": int(m._N)},
           "events": out}
    res["all_match"] = bool(ok_events and res["R2"]["match_1e-4"])
    (WS / "results" / "audit_rederive.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: v for k, v in res.items() if k != "events"}, indent=1, default=float))


if __name__ == "__main__":
    main()
