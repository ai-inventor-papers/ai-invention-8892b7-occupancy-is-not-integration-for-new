#!/usr/bin/env python3
"""S2: noun-phrase + Schwartz-Hearst acronym candidates from the OpenAlex corpus.

Reads raw/corpus_works/ (split parts), runs spaCy en_core_web_sm (parser for noun chunks,
sentences) in a spawn-based process pool, normalises each chunk to a key and
aggregates per-key statistics. Writes raw/candidates.pkl.gz (all keys) and
raw/docs_meta.pkl.gz (per-document year/field/corpus/text for snippets).
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textnorm import clean_chunk, normalise, schwartz_hearst  # noqa: E402
from rawio import dump_pickle, read_corpus_works  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s2_candidates.log", rotation="30 MB", level="DEBUG")

_NLP = None


def _nlp():
    global _NLP
    if _NLP is None:
        import spacy
        _NLP = spacy.load("en_core_web_sm", disable=["ner"])
        _NLP.max_length = 200000
    return _NLP


def process_chunk(args: tuple[int, list[str]]) -> tuple[int, list]:
    start, texts = args
    nlp = _nlp()
    out = []
    for doc in nlp.pipe(texts, batch_size=64):
        text = doc.text
        pairs = []
        sents = list(doc.sents)
        for s in sents:
            if "(" in s.text:
                for sf, lf in schwartz_hearst(s.text):
                    pairs.append((sf, lf, normalise(lf)))
        sf_map = {sf: lk for sf, _, lk in pairs if lk}
        recs = []
        for nc in doc.noun_chunks:
            toks = [(t.text, t.pos_, t.tag_) for t in nc]
            words = clean_chunk(toks)
            if not words:
                continue
            surface = " ".join(words)
            if len(words) == 1 and words[0] in sf_map:
                key = sf_map[words[0]]
                kind = "acronym_mapped"
            else:
                key = normalise(surface)
                kind = "np"
            if not key or len(key) < 3:
                continue
            s = nc.sent
            recs.append((key, surface, s.start_char, s.end_char, kind))
        # long forms of acronyms always count as candidates, even if the parser split them
        for sf, lf, lk in pairs:
            if lk and len(lk.split()) <= 6:
                pos = text.find(lf)
                s = doc.char_span(pos, pos + len(lf), alignment_mode="expand").sent if pos >= 0 else sents[0]
                recs.append((lk, lf, s.start_char, s.end_char, "acronym_long"))
        out.append((recs, pairs))
    return start, out


def main() -> None:
    works = list(read_corpus_works())
    logger.info(f"loaded {len(works)} works")
    texts = [(w["title"] or "").strip().rstrip(".") + ". " + (w["abstract"] or "") for w in works]
    docs_meta = [{"id": w["id"], "year": w["year"], "field_id": w["field_id"], "domain": w["domain"],
                  "corpus": w["corpus"], "subfield_id": w["subfield_id"]} for w in works]
    CH = 1500
    chunks = [(i, texts[i:i + CH]) for i in range(0, len(texts), CH)]
    results: list = [None] * len(texts)
    n_workers = 4
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=mp.get_context("spawn")) as ex:
        futs = [ex.submit(process_chunk, c) for c in chunks]
        for k, f in enumerate(as_completed(futs)):
            start, out = f.result()
            results[start:start + len(out)] = out
            logger.info(f"chunk {k + 1}/{len(chunks)} done")

    # ---------- aggregate ----------
    docs_by_key: dict[str, list[int]] = defaultdict(list)
    surfaces: dict[str, Counter] = defaultdict(Counter)
    snips: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    kinds: dict[str, Counter] = defaultdict(Counter)
    acr_pairs: Counter = Counter()  # (sf, lf_key) -> docs
    acr_lf_surface: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for di, (recs, pairs) in enumerate(results):
        seen = set()
        for key, surface, s0, s1, kind in recs:
            surfaces[key][surface] += 1
            kinds[key][kind] += 1
            if key in seen:
                continue
            seen.add(key)
            docs_by_key[key].append(di)
            if len(snips[key]) < 6:
                snips[key].append((di, s0, s1))
        for sf, lf, lk in {(a, b, c) for a, b, c in pairs}:
            acr_pairs[(sf, lk)] += 1
            acr_lf_surface[(sf, lk)][lf] += 1
    logger.info(f"{len(docs_by_key)} distinct keys; {len(acr_pairs)} acronym pairs")

    # ---------- C-value (Frantzi et al. 2000; log2(|a|+1) variant so unigrams are scored) ----------
    freq = {k: len(v) for k, v in docs_by_key.items()}
    nest_sum: dict[str, int] = defaultdict(int)
    nest_cnt: dict[str, int] = defaultdict(int)
    for k, f in freq.items():
        toks = k.split(" ")
        n = len(toks)
        if n < 2:
            continue
        subs = set()
        for L in range(1, n):
            for i in range(0, n - L + 1):
                sub = " ".join(toks[i:i + L])
                if sub in freq:
                    subs.add(sub)
        for sub in subs:
            nest_sum[sub] += f
            nest_cnt[sub] += 1
    cvalue = {}
    for k, f in freq.items():
        ln = math.log2(len(k.split(" ")) + 1)
        if nest_cnt.get(k):
            cvalue[k] = ln * (f - nest_sum[k] / nest_cnt[k])
        else:
            cvalue[k] = ln * f
    dump_pickle({"docs_by_key": dict(docs_by_key), "surfaces": {k: dict(v) for k, v in surfaces.items()},
                     "snips": dict(snips), "kinds": {k: dict(v) for k, v in kinds.items()},
                     "acr_pairs": dict(acr_pairs), "acr_lf_surface": {k: dict(v) for k, v in acr_lf_surface.items()},
                 "cvalue": cvalue}, "candidates")
    dump_pickle({"meta": docs_meta, "texts": texts}, "docs_meta")
    logger.info("saved raw/candidates.pkl.gz and raw/docs_meta.pkl.gz")


if __name__ == "__main__":
    main()
