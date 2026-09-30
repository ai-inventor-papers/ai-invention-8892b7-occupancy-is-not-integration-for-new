#!/usr/bin/env python3
"""P3: journal-level ASJC venue habitat (citation-independent), plus a labelled pre-period topic-derived fallback.

Sources
  * SCImago Journal & Country Rank annual exports 1999-2025 (data from Scopus), taken from the standardised
    journal x category x year panel in Zenodo record 22954453 (Dorado et al. 2026, CC BY 4.0), because the
    scimagojr.com export is behind a Cloudflare challenge (HTTP 403, logged in logs/p3_venue_habitat.log).
  * OpenAlex S3 snapshot `sources` entity (issn_l, issn[], type, display_name), in hyd/snapshot_entities/sources.
  * OpenAlex subfield ids == ASJC 4-digit codes (hyd/taxonomy.json + gen_art_dataset_2 taxonomy_subfields check).

Rule (fixed before any outcome is looked at; see README):
  UNCOVERED(repository)   OpenAlex type == repository, or arXiv/bioRxiv/medRxiv/SSRN/Zenodo/RePEc
  UNCOVERED(megajournal)  on the iteration-1 MEGA list, or its only ASJC codes are 1000 Multidisciplinary
  otherwise drop GENERAL codes (names 'General ...', '... (miscellaneous)', 'Multidisciplinary'), then
  COVERED                 exactly one specific subfield left
  UNCOVERED(general_only) none left (the 2-digit field is recorded)
  UNCOVERED(multi_subfield) >= 2 left (fractional_shares = 1/k each, secondary variant)
  unmatched in SCImago:   >= 20 c-papers -> one OpenAlex call (2000-2004 group_by primary_topic.subfield.id);
                          covered if >= 20 works in 2000-04 and dominant share > 0.40 (citation_independent=false);
                          < 20 c-papers -> UNCOVERED(no_match_small).

Usage:  python p3_venue_habitat.py scimago            # build ASJC name->code map + ISSN index (free)
        python p3_venue_habitat.py build [--fallback]  # join with the corpus; --fallback buys the group_by calls
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

ROOT = Path(__file__).resolve().parent
HYD = ROOT / "hyd"
OUT = ROOT / "outputs"
SCI = ROOT / "scimago_raw"
# copy of gen_art_dataset_2 data/taxonomy_subfields.parquet (iteration-1 artifact), see README
DS2_SUBFIELDS = Path(os.environ.get("DATASET2_DATA_DIR", ROOT / "deps" / "gen_art_dataset_2")) / "taxonomy_subfields.parquet"
sys.path.insert(0, str(HYD))

MEGA = {"plos one", "scientific reports", "ieee access", "heliyon", "peerj", "cureus", "medicine",
        "sage open", "f1000research", "royal society open science", "aip advances", "applied sciences",
        "sustainability", "international journal of environmental research and public health", "molecules",
        "sensors", "nature communications", "science advances", "plos computational biology",
        "journal of physics conference series", "iop conference series materials science and engineering"}
REPO_NAMES = re.compile(r"\b(arxiv|biorxiv|medrxiv|ssrn|social science research network|zenodo|repec|"
                        r"research papers in economics)\b", re.I)
PANEL_YEARS_UNION = (2005, 2010, 2015, 2019)
FALLBACK_MIN_CPAPERS = 20
FALLBACK_MIN_WORKS = 20
FALLBACK_SHARE = 0.40
FALLBACK_CAP = 800


def setup_logging() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(ROOT / "logs" / "p3_venue_habitat.log", rotation="30 MB", level="DEBUG")


def norm_name(s: str) -> str:
    s = (s or "").lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9() ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_issn(x) -> str | None:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = re.sub(r"[^0-9Xx]", "", str(x)).upper()
    return s if len(s) == 8 else None


HAND_CODES = {  # SCImago label -> ASJC code, spelling variants of labels in the ASJC table (checked by hand)
    "Advanced and Specialized Nursing": 2902, "Aging": 1302, "Archeology": 3302,
    "Archeology (arts and humanities)": 1204, "Critical Care Nursing": 2906, "Ecological Modeling": 2302,
    "Emergency Nursing": 2907, "Medical and Surgical Nursing": 2914, "Modeling and Simulation": 2611,
    "Neurology (clinical)": 2728, "Obstetrics and Gynecology": 2729, "Veterinary (miscellaneous)": 3401,
    "Genetics (clinical)": 2716, "Health (social science)": 3306, "Oncology (nursing)": 2917,
}


def is_general_code(code: int, asjc: pd.DataFrame) -> bool:
    n = asjc.loc[asjc["asjc_code"] == code, "asjc_description"]
    return bool(len(n)) and is_general(str(n.iloc[0]).replace("miscalleneous", "miscellaneous"))


def is_general(name: str) -> bool:
    n = name.strip()
    return n.startswith("General ") or n.endswith("(miscellaneous)") or n == "Multidisciplinary"


# ---------------------------------------------------------------- stage 1: SCImago index
def build_scimago() -> None:
    tax = orjson.loads((HYD / "taxonomy.json").read_bytes())
    oa_sf = {norm_name(v if isinstance(v, str) else v.get("display_name", v.get("name", ""))): int(k)
             for k, v in tax["subfields"].items()}
    oa_fields = {norm_name(v if isinstance(v, str) else v.get("display_name", v.get("name", ""))): int(k)
                 for k, v in tax["fields"].items()}
    ds2 = pd.read_parquet(DS2_SUBFIELDS)
    ds2_ids = set(ds2["subfield_id"].astype(int))
    assert ds2_ids == {int(k) for k in tax["subfields"]}, "taxonomy.json subfields differ from gen_art_dataset_2"
    names = Counter(norm_name(v) for v in tax["subfields"].values())
    dup = {n: [int(k) for k, v in tax["subfields"].items() if norm_name(v) == n] for n, c in names.items() if c > 1}
    if dup:
        logger.warning(f"OpenAlex subfield names shared by several ids (name map ambiguous): {dup}")
    panel = pd.read_parquet(SCI / "sjr_category_panel.parquet",
                            columns=["source_id", "year", "category_standardized", "issn_print", "issn_online",
                                     "source_type_standardized", "title_raw"])
    cats = sorted(panel["category_standardized"].unique())
    # authoritative ASJC code table (dhimmel/scopus data/asjc-codes.tsv, from the Scopus source list), then
    # spelling variants (British vs American spelling / renamed labels) resolved by hand against that table
    asjc = pd.read_csv(SCI / "asjc-codes_dhimmel.tsv", sep="\t")
    asjc_by_name: dict[str, list[int]] = defaultdict(list)
    for code, n in zip(asjc["asjc_code"], asjc["asjc_description"]):
        asjc_by_name[norm_name(n).replace("(", "").replace(")", "")].append(int(code))
    name2code, unmapped = {}, []
    for c in cats:
        k = norm_name(c).replace("(", "").replace(")", "")
        code, how = None, None
        if c in HAND_CODES:
            code, how = HAND_CODES[c], "hand_spelling_variant"
        elif len(asjc_by_name.get(k, [])) == 1:
            code, how = asjc_by_name[k][0], "asjc_table_exact"
        elif norm_name(c) in oa_sf and list(oa_sf).count(norm_name(c)) == 1:
            code, how = oa_sf[norm_name(c)], "openalex_subfield_name"
        if code is None:
            unmapped.append(c)
            how = "unmapped_new_sjr_category"
        name2code[c] = {"code": code, "general": is_general(c) or code == 1000 or (code is not None and code % 100 in (0, 1)
                        and code != 1000 and is_general_code(code, asjc)),
                        "in_openalex_subfields": code in ds2_ids if code else False, "how": how,
                        "label": f"SJR:{c}" if code is None else code}
    logger.info(f"SCImago categories: {len(cats)}; mapped {len(cats) - len(unmapped)}; unmapped {len(unmapped)}: "
                f"{unmapped}")
    # journal x year -> categories; ISSN -> scopus source ids
    panel["issns"] = [[i for i in (norm_issn(a), norm_issn(b)) if i] for a, b in
                      zip(panel["issn_print"], panel["issn_online"])]
    by_sy: dict[str, dict[int, set]] = defaultdict(lambda: defaultdict(set))
    meta: dict[str, dict] = {}
    issn2src: dict[str, set] = defaultdict(set)
    for r in panel.itertuples(index=False):
        sid = str(r.source_id)
        by_sy[sid][int(r.year)].add(r.category_standardized)
        for i in r.issns:
            issn2src[i].add(sid)
        m = meta.setdefault(sid, {"title": r.title_raw, "type": r.source_type_standardized})
        m["title"] = r.title_raw
    out = {"source": "Zenodo 22954453 sjr_category_panel.parquet (SCImago annual exports 1999-2025, data: Scopus)",
           "name2code": name2code, "unmapped_names": unmapped,
           "journals": {sid: {"title": meta[sid]["title"], "type": meta[sid]["type"],
                              "cats_by_year": {str(y): sorted(v) for y, v in ys.items()}}
                        for sid, ys in by_sy.items()},
           "issn2src": {k: sorted(v) for k, v in issn2src.items()}}
    (SCI / "scimago_index.json").write_bytes(orjson.dumps(out))
    logger.info(f"SCImago index: {len(out['journals'])} Scopus sources, {len(issn2src)} ISSNs")


# ---------------------------------------------------------------- stage 2: corpus sources
def corpus_source_counts() -> tuple[Counter, set[int]]:
    """n c-papers per source_id and the set of all source ids in the assembled works table (hyd/works)."""
    works = sorted((HYD / "works").glob("works_part_*.parquet"))
    if not works:
        raise FileNotFoundError("hyd/works/*.parquet missing: run hyd/assemble.py first")
    sids: Counter = Counter()
    for f in works:
        t = pq.read_table(f, columns=["work_id", "source_id"]).to_pandas()
        sids.update(int(s) for s in t["source_id"].dropna())
    return sids, set(sids)


def openalex_sources(source_ids: set[int]) -> dict[int, dict]:
    out = {}
    for f in glob.glob(str(HYD / "snapshot_entities/sources/**/*.parquet"), recursive=True):
        t = pq.read_table(f, columns=["id", "issn_l", "issn", "display_name", "type", "is_preprint_repository"]
                          ).to_pandas()
        t["sid"] = t["id"].str.rsplit("/S", n=1).str[-1].astype("int64")
        t = t[t["sid"].isin(source_ids)]
        for r in t.itertuples(index=False):
            issns = [x for x in (list(r.issn) if r.issn is not None else []) if x]
            out[int(r.sid)] = {"source_id": int(r.sid), "issn_l": r.issn_l, "issns": issns,
                               "display_name": r.display_name, "openalex_type": r.type,
                               "is_preprint_repository": bool(r.is_preprint_repository)}
    return out


def n2c_in_oa(sci: dict, code: int) -> bool:
    return any(v["code"] == code and v["in_openalex_subfields"] for v in sci["name2code"].values())


def pick_year(years: list[int]) -> int:
    """SJR year closest to 2010; earlier wins ties."""
    return sorted(years, key=lambda y: (abs(y - 2010), y))[0]


def classify(v: dict, sci: dict) -> dict:
    name = norm_name(v.get("display_name") or "").replace("(", "").replace(")", "")
    name = re.sub(r"\s+", " ", name)
    n2c = sci["name2code"]
    rec = {"habitat_subfield": "UNCOVERED", "fractional_shares": {}, "asjc_codes_raw": [], "route": "none",
           "sjr_year_used": None, "uncovered_reason": None, "citation_independent": None,
           "scopus_source_ids": [], "asjc_codes_union_2005_2010_2015_2019": [], "general_field": None}
    # ISSN match
    issns = {norm_issn(v.get("issn_l"))} | {norm_issn(x) for x in v.get("issns") or []}
    issns.discard(None)
    srcs = sorted({s for i in issns for s in sci["issn2src"].get(i, [])})
    rec["scopus_source_ids"] = srcs
    if v.get("openalex_type") == "repository" or v.get("is_preprint_repository") or REPO_NAMES.search(
            v.get("display_name") or ""):
        rec["uncovered_reason"] = "repository"
        rec["citation_independent"] = True
        return rec
    if not srcs:
        rec["uncovered_reason"] = "no_match"
        return rec
    # several Scopus ids for one OpenAlex source: use the one with the most SJR years
    sid = max(srcs, key=lambda s: (len(sci["journals"][s]["cats_by_year"]), s))
    cby = {int(y): c for y, c in sci["journals"][sid]["cats_by_year"].items()}
    y = pick_year(list(cby))
    cats = cby[y]
    rec.update(route="scimago", sjr_year_used=y, citation_independent=True,
               asjc_codes_raw=[n2c[c]["label"] for c in cats])
    rec["asjc_codes_union_2005_2010_2015_2019"] = sorted({n2c[c]["label"] for yy in PANEL_YEARS_UNION
                                                           for c in cby.get(yy, [])}, key=str)
    codes = [n2c[c]["code"] for c in cats]
    if name in MEGA or (codes and all(c == 1000 for c in codes)):
        rec["uncovered_reason"] = "megajournal"
        return rec
    specific = sorted({n2c[c]["label"] for c in cats if not n2c[c]["general"]}, key=str)
    if len(specific) == 1 and isinstance(specific[0], int):
        rec["habitat_subfield"] = specific[0]
        rec["fractional_shares"] = {str(specific[0]): 1.0}
        rec["habitat_in_openalex_subfields"] = bool(n2c_in_oa(sci, specific[0]))
    elif len(specific) == 1:
        rec["uncovered_reason"] = "unmapped_sjr_category"
    elif not specific:
        rec["uncovered_reason"] = "general_only"
        g = [c for c in codes if c]
        rec["general_field"] = (g[0] // 100) if g else None
    else:
        rec["uncovered_reason"] = "multi_subfield"
        rec["fractional_shares"] = {str(x): round(1 / len(specific), 6) for x in specific}
    return rec


async def fallback_calls(sids: list[int]) -> dict[int, dict]:
    """1 credit each: 2000-2004 works of the source grouped by primary-topic subfield (cached per source)."""
    os.environ.setdefault("AII_STEP", "p3_fallback")
    from common import CreditExhausted, OAClient  # noqa: E402  (hyd/common.py, shared ledger)
    res: dict[int, dict] = {}
    async with OAClient(cap=int(os.environ.get("AII_ARTIFACT_CAP", FALLBACK_CAP))) as oa:
        async def one(s: int) -> None:
            try:
                d = await oa.get("/works", {"filter": f"primary_location.source.id:S{s},publication_year:2000-2004",
                                            "group_by": "primary_topic.subfield.id", "per_page": 200})
            except CreditExhausted:
                return
            if d is None or "__error__" in d:
                return
            groups = {str(g["key"]).rstrip("/").split("/")[-1]: int(g["count"]) for g in d.get("group_by", [])}
            res[s] = {"total": int(d["meta"]["count"]), "groups": groups}
        for i in range(0, len(sids), 16):
            await asyncio.gather(*[one(s) for s in sids[i:i + 16]])
    return res


def build(do_fallback: bool) -> None:
    sci = orjson.loads((SCI / "scimago_index.json").read_bytes())
    counts, sids = corpus_source_counts()
    src = openalex_sources(sids)
    logger.info(f"corpus sources: {len(sids)}; found in snapshot: {len(src)}")
    rows = []
    for s in sorted(sids):
        v = src.get(s, {"source_id": s, "issn_l": None, "issns": [], "display_name": None,
                        "openalex_type": None, "is_preprint_repository": False})
        rec = classify(v, sci)
        rows.append({**v, **rec, "n_c_papers": counts[s]})
    need = [r["source_id"] for r in rows if r["uncovered_reason"] == "no_match"
            and r["n_c_papers"] >= FALLBACK_MIN_CPAPERS]
    logger.info(f"unmatched venues with >= {FALLBACK_MIN_CPAPERS} c-papers: {len(need)} (fallback calls)")
    fb: dict[int, dict] = {}
    if do_fallback and need:
        fb = asyncio.run(fallback_calls(need[:FALLBACK_CAP]))
        logger.info(f"fallback responses: {len(fb)}")
    for r in rows:
        if r["uncovered_reason"] != "no_match":
            continue
        if r["n_c_papers"] < FALLBACK_MIN_CPAPERS:
            r["uncovered_reason"] = "no_match_small"
            continue
        f = fb.get(r["source_id"])
        if f is None:
            r["uncovered_reason"] = "no_preperiod_call"  # fallback not bought (no credits / not run)
            continue
        r["route"] = "preperiod_groupby"
        r["citation_independent"] = False
        r["preperiod_total_2000_2004"] = f["total"]
        known = {k: n for k, n in f["groups"].items() if k.isdigit()}
        tot = sum(known.values())
        if f["total"] < FALLBACK_MIN_WORKS or not tot:
            r["uncovered_reason"] = "no_preperiod"
            continue
        dom, n = max(known.items(), key=lambda kv: kv[1])
        share = n / f["total"]
        r["preperiod_dominant_share"] = round(share, 4)
        if share > FALLBACK_SHARE:
            r["habitat_subfield"] = int(dom)
            r["fractional_shares"] = {dom: 1.0}
            r["uncovered_reason"] = None
        else:
            r["uncovered_reason"] = "preperiod_share_le_0.40"
    OUT.mkdir(exist_ok=True)
    (OUT / "venue_habitat_asjc.json").write_bytes(orjson.dumps({
        "definition": __doc__, "scimago_unmapped_names": sci["unmapped_names"], "n_venues": len(rows),
        "venues": rows}, default=str))
    df = pd.DataFrame(rows)
    logger.info("route x covered:\n" + str(pd.crosstab(df["route"], df["habitat_subfield"] != "UNCOVERED")))
    logger.info("uncovered reasons: " + str(df["uncovered_reason"].value_counts(dropna=False).to_dict()))
    w = df.groupby(df["habitat_subfield"] != "UNCOVERED")["n_c_papers"].sum()
    logger.info(f"c-paper-weighted covered share: {w.get(True, 0) / max(w.sum(), 1):.4f}")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["scimago", "build"])
    ap.add_argument("--fallback", action="store_true")
    a = ap.parse_args()
    setup_logging()
    if a.stage == "scimago":
        build_scimago()
    else:
        build(a.fallback)


if __name__ == "__main__":
    main()
