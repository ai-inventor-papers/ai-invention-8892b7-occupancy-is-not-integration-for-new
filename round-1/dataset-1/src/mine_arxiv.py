#!/usr/bin/env python3
"""Step 1(iv): failure-inclusive arXiv-mined arm. Title n-grams (2-4 tokens, stop-word boundaries) from arXiv
papers first submitted <= 2018. Rules use only counts up to Y0+2 (Y0 = first year with >= 3 titles):
2005 <= Y0 <= 2016, titles before Y0 <= 2, titles in Y0..Y0+2 >= 10. Fragments (an n-gram whose Y0..Y0+2 count
is >= 80% explained by one longer kept n-gram) are dropped. Output: vocab/arxiv_mined.parquet in random order."""
import random
import re
from collections import Counter, defaultdict

import pandas as pd
import pyarrow.parquet as pq
from loguru import logger
from wordfreq import zipf_frequency

from common import ROOT, concept_id, normalise, setup_logging
from build_vocab import GENERIC

SEED = 20260928
STOP = set("""a an the of in on for to and or with by from at as is are was were be been being this that these those
its it their our we via using use based new novel towards toward into over under between within without about
than then case study studies approach method methods model models analysis results result effect effects first
second two three one some any all can may non high low large small general simple improved efficient fast
problem problems application applications system systems theory note remarks comment reply part i ii iii iv
evidence observation observations measurement measurements properties property role through against after
before during near far up down out do does not no more most less very""".split())
TOK = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")


def ngrams(title: str) -> set[str]:
    t = re.sub(r"\$[^$]*\$", " ", title.lower())
    toks = TOK.findall(t)
    out = set()
    for n in (2, 3, 4):
        for i in range(len(toks) - n + 1):
            g = toks[i:i + n]
            if g[0] in STOP or g[-1] in STOP:
                continue
            if any(len(x) < 2 for x in g):
                continue
            out.add(" ".join(g))
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("mine_arxiv")
    t = pq.read_table(ROOT / "arxiv_raw" / "arxiv_titles_le2018.parquet", columns=["title", "year"]).to_pandas()
    logger.info(f"{len(t)} arXiv titles <= 2018")
    counts: dict[str, Counter] = defaultdict(Counter)
    for title, y in zip(t.title.values, t.year.values):
        for g in ngrams(str(title).replace("\n", " ")):
            counts[g][int(y)] += 1
    logger.info(f"{len(counts)} distinct n-grams")
    rows = []
    for g, c in counts.items():
        if sum(c.values()) < 10:
            continue
        y0 = next((y for y in range(1991, 2019) if c.get(y, 0) >= 3), None)
        if y0 is None or not (2005 <= y0 <= 2016):
            continue
        if sum(c.get(y, 0) for y in range(1991, y0)) > 2:
            continue
        early = sum(c.get(y, 0) for y in range(y0, y0 + 3))
        if early < 10:
            continue
        rows.append({"ngram": g, "Y0": y0, "early_titles": early,
                     "arxiv_title_counts_le_Y0p2": {y: c.get(y, 0) for y in range(y0 - 2, y0 + 3)}})
    logger.info(f"{len(rows)} n-grams pass the arXiv first-use rules")
    # fragment removal: drop g if some longer passing n-gram containing g has >= 80% of g's early count
    by_len = sorted(rows, key=lambda r: -len(r["ngram"].split()))
    kept: list[dict] = []
    longer: list[dict] = []
    for r in by_len:
        g = f" {r['ngram']} "
        if any(g in f" {L['ngram']} " and L["early_titles"] >= 0.8 * r["early_titles"] for L in longer):
            continue
        kept.append(r)
        longer.append(r)
    logger.info(f"{len(kept)} after fragment removal")
    out = []
    for r in kept:
        phrase, _ = normalise(r["ngram"])
        toks = phrase.split()
        if phrase in GENERIC or len(toks) < 2:
            continue
        if all(zipf_frequency(x, "en") > 4.5 for x in toks):
            continue
        out.append({"phrase": phrase, "concept_id": concept_id(phrase), "arxiv_Y0": r["Y0"],
                    "arxiv_early_titles": r["early_titles"],
                    "arxiv_counts": {str(k): v for k, v in r["arxiv_title_counts_le_Y0p2"].items()}})
    df = pd.DataFrame(out).drop_duplicates("phrase")
    rng = random.Random(SEED)
    idx = list(range(len(df)))
    rng.shuffle(idx)
    df = df.iloc[idx].reset_index(drop=True)
    df["rand_order"] = range(len(df))
    df.to_parquet(ROOT / "vocab" / "arxiv_mined.parquet", index=False)
    logger.info(f"arxiv arm pool: {len(df)}; Y0 dist {df.arxiv_Y0.value_counts().sort_index().to_dict()}")


if __name__ == "__main__":
    main()
