#!/usr/bin/env python3
"""Step 1: candidate vocabulary (free). Arms: OpenAlex keywords, legacy concepts (level>=2), MeSH descriptors
introduced 2005-2016. Normalise, deduplicate, deterministic stop-list, outcome-blind pre-2005 tag pre-filter,
then a seeded uniform random order (the LLM screen walks this order).

Outputs vocab/vocab_clean.parquet and vocab/vocab_stats.json."""
import glob
import gzip
import random
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger
from wordfreq import zipf_frequency

from common import ROOT, normalise, setup_logging, concept_id

SEED = 20260928
VOC = ROOT / "vocab"
# Pre-2005 tag-count pre-filter threshold (classifier tags over 1995-2004 works; pre-2005 info only).
TAG_MAX_PRE2005 = {"keywords": 200, "concepts": 200}  # ~25th percentile of pre-2005 tag counts

GENERIC = set("""case study|systematic review|meta analysis|machine learning|risk factor|cross sectional study|
randomized controlled trial|literature review|data analysis|statistical analysis|mathematical model|
numerical simulation|computer simulation|experimental study|pilot study|cohort study|control group|
quality of life|decision making|public health|health care|data collection|research design|
qualitative research|quantitative research|survey|questionnaire|regression analysis|
logistic regression|linear regression|principal component analysis|factor analysis|sensitivity analysis|
case report|clinical trial|follow up|retrospective study|prospective study|descriptive statistics|
standard deviation|confidence interval|odds ratio|hazard ratio|p value|sample size|
significant difference|theoretical framework|conceptual framework|empirical study|empirical research|
research method|research methodology|methodology|analysis|model|system|method|approach|framework|
performance|evaluation|design|optimization|simulation|management|development|application|
data mining|big data|artificial intelligence|neural network|deep learning|computer science|
information technology|social science|natural science|engineering|biology|chemistry|physics|
mathematics|medicine|psychology|economics|sociology|political science|environmental science|
climate change|global warming|sustainable development|renewable energy|energy efficiency|
signal processing|image processing|feature extraction|pattern recognition|computer vision|
natural language processing|software engineering|information system|decision support system|
internet|world wide web|social media|social network|mobile phone|smartphone|
cell biology|molecular biology|genetics|gene expression|protein|enzyme|metabolism|
cancer|tumor|disease|treatment|therapy|diagnosis|prognosis|epidemiology|
mortality|morbidity|prevalence|incidence|risk assessment|risk management|
literature|education|teaching|learning|student|curriculum|pedagogy|
business|marketing|finance|accounting|economy|economic growth|
government|policy|law|regulation|ethics|philosophy|history|
art|music|religion|culture|language|linguistics|communication|
time series|time series analysis|monte carlo method|finite element method|
control theory|control system|feedback|stability|convergence|algorithm|
upper and lower bounds|boundary value problem|differential equation|
first order|second order|real time|high performance|low cost|state of the art|
large scale|small scale|long term|short term|in vitro|in vivo|
""".replace("\n", "").split("|"))
GENERIC = {g.strip() for g in GENERIC if g.strip()}
UNITS = re.compile(r"^(\d[\d.,]*|[ivxlcdm]+)$")


def load_keywords() -> pd.DataFrame:
    fs = glob.glob(str(ROOT / "snapshot_entities/keywords/**/*.parquet"), recursive=True)
    k = pd.concat([pq.read_table(f, columns=["id", "display_name"]).to_pandas() for f in fs])
    k["kid"] = k["id"].str.rsplit("/", n=1).str[-1]
    return k


def load_concepts() -> pd.DataFrame:
    fs = glob.glob(str(ROOT / "snapshot_entities/concepts/**/*.parquet"), recursive=True)
    c = pd.concat([pq.read_table(f, columns=["id", "display_name", "level", "wikidata"]).to_pandas() for f in fs])
    c = c[c["level"] >= 2].copy()
    c["cid"] = c["id"].str.rsplit("/", n=1).str[-1]
    return c


def load_mesh() -> list[dict]:
    out = []
    with gzip.open(ROOT / "mesh_raw/desc2026.gz") as f:
        for _, el in ET.iterparse(f, events=("end",)):
            if el.tag != "DescriptorRecord":
                continue
            if el.get("DescriptorClass") == "1":
                di = el.find("DateIntroduced/Year")
                year = int(di.text) if di is not None else None
                if year is not None and 2005 <= year <= 2016:
                    ui = el.findtext("DescriptorUI")
                    name = el.findtext("DescriptorName/String")
                    terms = []
                    for con in el.findall("ConceptList/Concept"):
                        if con.get("PreferredConceptYN") != "Y":
                            continue
                        for t in con.findall("TermList/Term"):
                            s = t.findtext("String")
                            if s and s != name:
                                terms.append(s)
                    out.append({"mesh_ui": ui, "name": name, "entry_terms": terms, "year_introduced": year})
            el.clear()
    return out


def uninvert(s: str) -> str:
    """MeSH inverted labels 'Neoplasms, Radiation-Induced' -> 'Radiation-Induced Neoplasms'."""
    if s.count(",") == 1:
        a, b = [x.strip() for x in s.split(",")]
        return f"{b} {a}"
    return s


def stop_reason(phrase: str) -> str | None:
    toks = phrase.split()
    if not toks:
        return "empty"
    if len(toks) > 6:
        return "too_long"
    if any(UNITS.match(t) for t in toks) and len(toks) <= 2:
        return "number_or_unit"
    if any(ch.isdigit() for ch in phrase) and len(toks) == 1:
        return "number_or_unit"
    if phrase in GENERIC:
        return "generic_method"
    z = [zipf_frequency(t, "en") for t in toks]
    if len(toks) == 1:
        if not (len(toks[0]) >= 8 and z[0] < 3.0):
            return "single_token_common_or_short"
    if all(v > 4.5 for v in z):
        return "all_tokens_generic_english"
    if len(phrase) < 4:
        return "too_short"
    return None


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("build_vocab")
    VOC.mkdir(exist_ok=True)
    tagk = orjson.loads((VOC / "pre2005_tag_counts_keywords.json").read_bytes())
    tagc = orjson.loads((VOC / "pre2005_tag_counts_concepts.json").read_bytes())
    logger.info(f"tag counts: keywords={len(tagk)} concepts={len(tagc)}")

    rows: dict[str, dict] = {}

    def add(label: str, arm: str, links: dict, pre_tag: int | None) -> None:
        phrase, acr = normalise(label)
        if not phrase:
            return
        r = rows.setdefault(phrase, {"phrase": phrase, "labels": set(), "acronyms": set(), "vocab_arms": set(),
                                     "links": {}, "pre2005_tag_counts": {}})
        r["labels"].add(label)
        if acr:
            r["acronyms"].add(acr)
        r["vocab_arms"].add(arm)
        for k, v in links.items():
            if v is not None:
                r["links"].setdefault(k, v)
        if pre_tag is not None:
            r["pre2005_tag_counts"][arm] = pre_tag

    k = load_keywords()
    for kid, name in zip(k["kid"], k["display_name"]):
        add(name, "openalex_keyword", {"openalex_keyword_id": kid}, int(tagk.get(kid, 0)))
    c = load_concepts()
    for cid, name, lvl, wd in zip(c["cid"], c["display_name"], c["level"], c["wikidata"]):
        qid = wd.rsplit("/", 1)[-1] if isinstance(wd, str) else None
        add(name, "legacy_concept", {"legacy_concept_id": cid, "legacy_concept_level": int(lvl), "wikidata_qid": qid},
            int(tagc.get(cid, 0)))
    mesh = load_mesh()
    logger.info(f"MeSH descriptors introduced 2005-2016: {len(mesh)}")
    for m in mesh:
        label = m["name"]
        if "," in label:
            alt = [t for t in m["entry_terms"] if "," not in t]
            label = alt[0] if alt else uninvert(label)
        add(label, "mesh_new_descriptor", {"mesh_ui": m["mesh_ui"], "mesh_year_introduced": m["year_introduced"]}, None)
        rows[normalise(label)[0]].setdefault("mesh_entry_terms", [])
        rows[normalise(label)[0]]["mesh_entry_terms"] = [t for t in m["entry_terms"] if "," not in t][:2]

    df = pd.DataFrame(rows.values())
    df["concept_id"] = df["phrase"].map(concept_id)
    df["stop_reason"] = df["phrase"].map(stop_reason)
    # outcome-blind pre-filter: many pre-2005 tagged works in ANY tagging arm => pre-existing concept
    def pre_reason(r) -> str | None:
        tc = r["pre2005_tag_counts"]
        if "openalex_keyword" in tc and tc["openalex_keyword"] > TAG_MAX_PRE2005["keywords"]:
            return "pre2005_keyword_tags"
        if "legacy_concept" in tc and tc["legacy_concept"] > TAG_MAX_PRE2005["concepts"]:
            return "pre2005_concept_tags"
        return None
    df["prefilter_reason"] = df.apply(pre_reason, axis=1)
    for col in ["labels", "acronyms", "vocab_arms"]:
        df[col] = df[col].map(sorted)
    df["links"] = df["links"].map(lambda d: orjson.dumps(d).decode())
    df["pre2005_tag_counts"] = df["pre2005_tag_counts"].map(lambda d: orjson.dumps(d).decode())
    if "mesh_entry_terms" not in df:
        df["mesh_entry_terms"] = None
    df["mesh_entry_terms"] = df["mesh_entry_terms"].map(lambda x: x if isinstance(x, list) else [])
    rng = random.Random(SEED)
    order = list(range(len(df)))
    rng.shuffle(order)
    df["rand_order"] = pd.Series(range(len(df)), index=[df.index[i] for i in order]).sort_index().values
    df = df.sort_values("rand_order").reset_index(drop=True)
    df.to_parquet(VOC / "vocab_clean.parquet", index=False)

    stats = {
        "n_total_unique": int(len(df)),
        "by_arm_total": {a: int(df["vocab_arms"].map(lambda x: a in x).sum())
                         for a in ["openalex_keyword", "legacy_concept", "mesh_new_descriptor"]},
        "stop_reasons": df["stop_reason"].value_counts(dropna=False).to_dict(),
        "prefilter_reasons_among_stop_pass": df[df.stop_reason.isna()]["prefilter_reason"].value_counts(dropna=False).to_dict(),
        "n_pass": int((df.stop_reason.isna() & df.prefilter_reason.isna()).sum()),
        "tag_thresholds": TAG_MAX_PRE2005, "seed": SEED,
    }
    ok = df[df.stop_reason.isna() & df.prefilter_reason.isna()]
    stats["by_arm_pass"] = {a: int(ok["vocab_arms"].map(lambda x: a in x).sum())
                            for a in ["openalex_keyword", "legacy_concept", "mesh_new_descriptor"]}
    stats = {k: ({str(kk): vv for kk, vv in v.items()} if isinstance(v, dict) else v) for k, v in stats.items()}
    (VOC / "vocab_stats.json").write_bytes(orjson.dumps(stats, option=orjson.OPT_INDENT_2))
    logger.info(orjson.dumps(stats).decode())


if __name__ == "__main__":
    main()
