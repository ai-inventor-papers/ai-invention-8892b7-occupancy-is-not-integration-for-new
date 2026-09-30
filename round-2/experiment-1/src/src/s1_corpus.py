#!/usr/bin/env python3
"""STEP 1: corpus statistics for termhood.

U = arXiv titles 1991-2018 (cache/arxiv_titles_le2018.parquet, rebuilt by s1a_fetch_arxiv.py) + D1 titles + D1 abstract
sentences, all passed through the SAME normaliser (textnorm.normalise -> regex tokens -> singularised tokens).
One Aho-Corasick pass collects, per query phrase: frequency by source, document frequency, left/right extension-token
counters, and (for frame phrases) the ids of arXiv/D1 titles containing them.

OUTCOME-BLINDNESS (deviation from the plan, stated in the README): frame phrases are counted only in documents
published up to F+2 (main arm) or 2004 (reference arm), so the classifier that filters the test population never sees
post-window uptake. A second, uncensored copy of every frame phrase (qid 'framefull:') is counted for a sensitivity check.

POS of extension tokens comes from a token-level POS lexicon built by tagging a fixed random sample of titles and
abstract sentences with spaCy (share of NOUN/PROPN and ADJ tags per normalised token), instead of re-tagging every
matched sentence (deviation for runtime; the statistic is the same up to tagging context)."""
from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import pickle
import random
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

import ahocorasick
import numpy as np
import pandas as pd
from loguru import logger
from spacy.lang.en.stop_words import STOP_WORDS as STOP

from common import (CACHE, WORK, DATA, MINI, SENT_SPLIT, SEED, detect_cpus, load_frame, match_form, read_json, set_limits,
                    setup_logging, stream_tokens, write_json)

OUT = WORK / "termhood.pkl"
_AUTO = None
_CUT = None


def build_queries() -> tuple[list[dict], dict[str, list[int]]]:
    """Return query table and pattern -> [qid indices]."""
    Q: list[dict] = []
    pat: dict[str, list[int]] = defaultdict(list)

    def add(ns: str, key: str, forms: list[str], cutoff: int, extra: dict | None = None) -> None:
        qi = len(Q)
        mfs = sorted({m for m in (match_form(f) for f in forms) if m})
        Q.append({"qid": f"{ns}:{key}", "ns": ns, "key": key, "forms": mfs, "cutoff": cutoff, **(extra or {})})
        for m in mfs:
            pat[m].append(qi)

    d2 = read_json(DATA / "d2.json")
    for r in d2:
        add("d2", r["key"], [r["key"]], 2018)
    d4a = read_json(DATA / "d4a.json")
    for p in sorted({r["phrase"] for r in d4a}):
        add("d4a", p, [p], 2018)
    frame = load_frame()
    for cid, c in frame.items():
        forms = [c["phrase"]] + list(c.get("surface_forms") or [])
        cut = (int(c["F"]) + 2) if c["arm"] == "main" else 2004
        add("frame", cid, forms, cut, {"arm": c["arm"]})
        add("framefull", cid, forms, 2018, {"arm": c["arm"]})
    if MINI:
        keep = set(random.Random(SEED).sample(range(len(Q)), 800)) | {i for i, q in enumerate(Q) if q["ns"] == "frame"}
        pat = {m: [i for i in ids if i in keep] for m, ids in pat.items()}
        pat = {m: v for m, v in pat.items() if v}
    return Q, pat


def _init(auto_bytes: bytes, cut: np.ndarray) -> None:
    global _AUTO, _CUT
    _AUTO = pickle.loads(auto_bytes)
    _CUT = cut


def _work(chunk: list[tuple[int, str, int, int]]) -> dict:
    """chunk: (doc_id, text, year, source 0=arxiv 1=d1title 2=d1abs). Returns per-qid aggregates."""
    agg: dict[int, list] = {}
    doc_hits: dict[int, list[int]] = defaultdict(list)
    for doc_id, text, year, src in chunk:
        toks = stream_tokens(text)
        if not toks:
            continue
        s = " " + " ".join(toks) + " "
        seen_pos: set = set()
        for end, qids in _AUTO.iter(s):
            m_len = qids[0]
            start = end - m_len + 1
            li = s.rfind(" ", 0, start)
            left = s[li + 1:start] if li >= 0 else ""
            rj = s.find(" ", end + 1)
            right = s[end + 1:rj] if rj >= 0 else ""
            for qi in qids[1]:
                if year > _CUT[qi]:
                    continue
                key = (qi, start)
                if key in seen_pos:  # two surface forms of one concept matching at the same place
                    continue
                seen_pos.add(key)
                a = agg.get(qi)
                if a is None:
                    a = agg[qi] = [0, 0, 0, Counter(), Counter(), set()]
                a[0 if src == 0 else 1] += 1
                a[5].add(doc_id)
                a[3][right or "</s>"] += 1
                a[4][left or "<s>"] += 1
                if src in (0, 1):
                    doc_hits[qi].append(doc_id)
    out = {}
    for qi, a in agg.items():
        out[qi] = (a[0], a[1], len(a[5]), a[3], a[4])
    return {"agg": out, "doc_hits": dict(doc_hits)}


def pos_lexicon(texts: list[str]) -> dict[str, tuple[int, float, float]]:
    import spacy
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])
    cnt: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for doc in nlp.pipe(texts, batch_size=512, n_process=min(8, detect_cpus())):
        for t in doc:
            for nt in stream_tokens(t.text):
                c = cnt[nt]
                c[0] += 1
                if t.pos_ in ("NOUN", "PROPN"):
                    c[1] += 1
                elif t.pos_ == "ADJ":
                    c[2] += 1
    return {k: (v[0], v[1] / v[0], v[2] / v[0]) for k, v in cnt.items()}


def entropy(c: Counter) -> float:
    n = sum(c.values())
    if n == 0:
        return 0.0
    return float(-sum((v / n) * math.log2(v / n) for v in c.values()))


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-arxiv", type=int, default=0, help="timing run on the first N arXiv titles")
    args = ap.parse_args()
    setup_logging("s1_corpus")
    set_limits(45)
    t0 = time.time()
    Q, pat = build_queries()
    logger.info(f"{len(Q)} queries, {len(pat)} distinct patterns")
    A = ahocorasick.Automaton()
    for m, ids in pat.items():
        p = " " + m + " "
        A.add_word(p, (len(p), ids))
    A.make_automaton()
    cut = np.array([q["cutoff"] for q in Q], dtype=np.int32)

    # ---------------- corpus units
    arx_path = CACHE / "arxiv_titles_le2018.parquet"
    units: list[tuple[int, str, int, int]] = []
    doc_meta: list[tuple[str, int, str]] = []  # (source, year, title) per doc id (titles only)
    if arx_path.exists():
        arx = pd.read_parquet(arx_path, columns=["title", "year"])
        if args.limit_arxiv:
            arx = arx.iloc[:args.limit_arxiv]
        if MINI:
            arx = arx.sample(20000, random_state=SEED)
        for t, y in zip(arx["title"].tolist(), arx["year"].tolist()):
            t = " ".join((t or "").split())
            doc_meta.append(("arxiv", int(y), t))
            units.append((len(doc_meta) - 1, t, int(y), 0))
        n_arx = len(arx)
        del arx
    else:
        logger.warning("FALLBACK F1: no arXiv titles; termhood from D1 only")
        n_arx = 0
    d1 = pd.read_parquet(CACHE / "d1_corpus.parquet")
    if MINI:
        d1 = d1.sample(3000, random_state=SEED)
    n_abs_sent = 0
    for t, a, y in zip(d1["title"].tolist(), d1["abstract"].tolist(), d1["year"].tolist()):
        doc_meta.append(("d1", int(y), t))
        did = len(doc_meta) - 1
        units.append((did, t, int(y), 1))
        for s in SENT_SPLIT.split(a or ""):
            if s.strip():
                units.append((did, s, int(y), 2))
                n_abs_sent += 1
    logger.info(f"units: {n_arx} arXiv titles, {len(d1)} D1 titles, {n_abs_sent} D1 abstract sentences")

    # ---------------- POS lexicon (fixed random sample)
    rng = random.Random(SEED)
    samp_idx = rng.sample(range(len(units)), min(len(units), 30000 if MINI else 250000))
    lex = pos_lexicon([units[i][1] for i in samp_idx])
    logger.info(f"POS lexicon: {len(lex)} tokens ({time.time() - t0:.0f}s)")

    # ---------------- Aho-Corasick pass (parallel)
    nw = max(1, detect_cpus() - 1)
    chunks = [units[i:i + 20000] for i in range(0, len(units), 20000)]
    rng.shuffle(chunks)  # chunk order only: all units of one D1 document stay in one chunk (document frequency)
    del units
    ab = pickle.dumps(A)
    tot: dict[int, list] = {}
    doc_hits: dict[int, list[int]] = defaultdict(list)
    t1 = time.time()
    with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn"), initializer=_init,
                             initargs=(ab, cut)) as ex:
        for k, res in enumerate(ex.map(_work, chunks)):
            for qi, (fa, fd, df, rc, lc) in res["agg"].items():
                a = tot.get(qi)
                if a is None:
                    tot[qi] = [fa, fd, df, rc, lc]
                else:
                    a[0] += fa
                    a[1] += fd
                    a[2] += df
                    a[3].update(rc)
                    a[4].update(lc)
            for qi, ds in res["doc_hits"].items():
                if Q[qi]["ns"] in ("frame", "framefull"):
                    doc_hits[qi].extend(ds)
            if k % 20 == 0:
                logger.info(f"chunk {k + 1}/{len(chunks)} ({time.time() - t1:.0f}s)")
    logger.info(f"AC pass done in {time.time() - t1:.0f}s")

    # ---------------- features
    feats = {}
    for qi, q in enumerate(Q):
        fa, fd, df, rc, lc = tot.get(qi, [0, 0, 0, Counter(), Counter()])
        f = fa + fd
        n_tok = max(1, len(q["forms"][0].split())) if q["forms"] else 1
        # C-value nesting: longer candidate terms = 1-token extensions by a content word (not a stopword; noun/adj
        # share >= 0.5 in the POS lexicon) seen >= 2 times; function-word contexts ('and', 'of') are not nesting terms
        ext = [v for k, v in list(rc.items()) + list(lc.items())
               if k not in ("</s>", "<s>") and v >= 2 and k not in STOP and sum(lex.get(k, (0, 0.0, 0.0))[1:]) >= 0.5]
        nested = (sum(ext) / len(ext)) if ext else 0.0
        cval = math.log2(n_tok + 1) * (f - nested)
        rn = sum(v * lex.get(k, (0, 0.0, 0.0))[1] for k, v in rc.items() if k != "</s>")
        la = sum(v * (lex.get(k, (0, 0.0, 0.0))[1] + lex.get(k, (0, 0.0, 0.0))[2]) for k, v in lc.items() if k != "<s>")
        rmax = max([v for k, v in rc.items() if k != "</s>"], default=0)
        feats[q["qid"]] = {
            "th_log_f": math.log1p(f), "th_src_ratio": math.log1p(fa) - math.log1p(fd), "th_log_df": math.log1p(df),
            "th_cvalue": math.copysign(math.log1p(abs(cval)), cval),
            "th_right_entropy": entropy(rc), "th_left_entropy": entropy(lc),
            "th_share_right_ext_noun": rn / f if f else 0.0, "th_share_left_ext_adj_noun": la / f if f else 0.0,
            "th_max_right_ext_share": rmax / f if f else 0.0,
            "th_right_boundary_share": rc.get("</s>", 0) / f if f else 0.0,
            "th_missing": float(f == 0), "_f": f, "_f_arxiv": fa, "_f_d1": fd,
            "_top_right": rc.most_common(3), "_top_left": lc.most_common(3)}
    # frame title hits (for context embeddings, sense proxy, LLM snippets): doc ids -> (source, year, title)
    hits = {}
    for qi, ds in doc_hits.items():
        q = Q[qi]
        uniq = sorted(set(ds))
        hits[q["qid"]] = [(doc_meta[d][0], doc_meta[d][1], doc_meta[d][2]) for d in uniq][:3000]
    with open(OUT, "wb") as fh:
        pickle.dump({"queries": Q, "features": feats, "frame_title_hits": hits,
                     "meta": {"n_arxiv_titles": n_arx, "n_d1": len(d1), "n_d1_abs_sent": n_abs_sent,
                              "pos_lexicon_size": len(lex), "limit_arxiv": args.limit_arxiv,
                              "runtime_s": time.time() - t0, "fallback_F1": n_arx == 0}}, fh)
    write_json(WORK / "termhood_meta.json", {"n_queries": len(Q), "n_arxiv_titles": n_arx, "n_d1": len(d1),
                                             "n_d1_abs_sent": n_abs_sent, "runtime_s": time.time() - t0,
                                             "fallback_F1": n_arx == 0,
                                             "n_frame_missing": sum(1 for q in Q if q["ns"] == "frame" and feats[q["qid"]]["_f"] == 0)})
    logger.info(f"saved {OUT} ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
