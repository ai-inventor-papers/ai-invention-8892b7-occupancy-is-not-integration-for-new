#!/usr/bin/env python3
"""S0/D4: convert human-labelled SemEval-2017 Task 10 and SciERC into phrase-level rows,
convert acronym_identification into (short, long) pair rows, and evaluate our
Schwartz-Hearst extractor on the acronym_identification validation split.

Outputs: raw/anchor_phrases.jsonl, raw/anchor_acronyms.jsonl, labelling/sh_eval.json
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pandas as pd
import spacy
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from textnorm import clean_chunk, normalise, schwartz_hearst  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "temp" / "datasets"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s0_anchors.log", rotation="30 MB", level="DEBUG")

NLP = spacy.load("en_core_web_sm", disable=["ner"])
NLP.max_length = 300000


def join_tokens(tokens: list[str]) -> tuple[str, list[tuple[int, int]]]:
    offs, parts, pos = [], [], 0
    for t in tokens:
        offs.append((pos, pos + len(t)))
        parts.append(t)
        pos += len(t) + 1
    return " ".join(parts), offs


def window(text: str, s: int, e: int, width: int = 150) -> str:
    a = max(0, s - width)
    b = min(len(text), e + width)
    return ("…" if a > 0 else "") + text[a:b] + ("…" if b < len(text) else "")


def negatives(text: str, gold_char: list[tuple[int, int]], doc_id: str, source: str, fold: str, max_n: int) -> list[dict]:
    doc = NLP(text)
    out, seen = [], set()
    for nc in doc.noun_chunks:
        s, e = nc.start_char, nc.end_char
        if any(not (e <= gs or s >= ge) for gs, ge in gold_char):
            continue
        words = clean_chunk([(t.text, t.pos_, t.tag_) for t in nc])
        if not words:
            continue
        ph = " ".join(words)
        k = normalise(ph)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append({"phrase": ph, "sentence_context": nc.sent.text[:400], "source_doc_id": doc_id,
                    "label": "NOT_ANNOTATED", "source": source, "fold": fold, "entity_type": None})
        if len(out) >= max_n:
            break
    return out


def semeval2017() -> list[dict]:
    rows = []
    for fn, fold in [("train.jsonl", "train"), ("valid.jsonl", "validation"), ("test.jsonl", "test")]:
        for line in (D / "midas__semeval2017" / fn).open():
            r = json.loads(line)
            toks = r["document"] if isinstance(r["document"], list) else ast.literal_eval(r["document"])
            tags = r["doc_bio_tags"] if isinstance(r["doc_bio_tags"], list) else ast.literal_eval(r["doc_bio_tags"])
            text, offs = join_tokens(toks)
            spans, cur = [], None
            for i, t in enumerate(tags):
                if t == "B":
                    if cur:
                        spans.append(cur)
                    cur = [i, i]
                elif t == "I" and cur:
                    cur[1] = i
                else:
                    if cur:
                        spans.append(cur)
                    cur = None
            if cur:
                spans.append(cur)
            gold_char = [(offs[a][0], offs[b][1]) for a, b in spans]
            seen = set()
            for (a, b), (cs, ce) in zip(spans, gold_char):
                ph = text[cs:ce].strip(" .,;:")
                if not ph or normalise(ph) in seen:
                    continue
                seen.add(normalise(ph))
                rows.append({"phrase": ph, "sentence_context": window(text, cs, ce), "source_doc_id": r["paper_id"],
                             "label": "CONCEPT", "source": "semeval2017_task10", "fold": fold,
                             "entity_type": "keyphrase(Process|Task|Material)", "n_tokens": b - a + 1})
            rows.extend(negatives(text, gold_char, r["paper_id"], "semeval2017_task10", fold, max_n=len(spans)))
    return rows


def scierc() -> list[dict]:
    rows = []
    for fn, fold in [("train.json", "train"), ("dev.json", "validation"), ("test.json", "test")]:
        for line in (D / "zj88zj__SCIERC" / fn).open():
            r = json.loads(line)
            flat = [t for s in r["sentences"] for t in s]
            text, offs = join_tokens(flat)
            sent_bounds, k = [], 0
            for s in r["sentences"]:
                sent_bounds.append((k, k + len(s) - 1))
                k += len(s)
            gold_char, seen = [], set()
            for si, ents in enumerate(r["ner"]):
                sa, sb = sent_bounds[si]
                sent_text = text[offs[sa][0]:offs[sb][1]]
                for a, b, typ in ents:
                    cs, ce = offs[a][0], offs[b][1]
                    gold_char.append((cs, ce))
                    ph = text[cs:ce]
                    key = (normalise(ph), typ)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({"phrase": ph, "sentence_context": sent_text[:400], "source_doc_id": r["doc_key"],
                                 "label": "TOO_GENERIC_OR_NOT" if typ == "Generic" else "CONCEPT",
                                 "source": "scierc", "fold": fold, "entity_type": typ, "n_tokens": b - a + 1})
            n_pos = sum(len(e) for e in r["ner"])
            rows.extend(negatives(text, gold_char, r["doc_key"], "scierc", fold, max_n=max(3, n_pos // 2)))
    return rows


LAB = ["B-long", "B-short", "I-long", "I-short", "O"]


def bio_pairs(tokens: list[str], labels: list[int]) -> tuple[list[str], list[str]]:
    shorts, longs, cur, typ = [], [], [], None
    for t, l in zip(tokens, labels):
        name = LAB[l]
        if name.startswith("B-"):
            if cur:
                (shorts if typ == "short" else longs).append(" ".join(cur))
            cur, typ = [t], name[2:]
        elif name.startswith("I-") and cur and name[2:] == typ:
            cur.append(t)
        else:
            if cur:
                (shorts if typ == "short" else longs).append(" ".join(cur))
            cur, typ = [], None
    if cur:
        (shorts if typ == "short" else longs).append(" ".join(cur))
    return shorts, longs


def acronyms() -> tuple[list[dict], dict]:
    rows = []
    tp_sf = fp_sf = fn_sf = 0
    tp_pair = fp_pair = 0
    n_gold_pairs_paren = 0
    for fn, fold in [("train", "train"), ("validation", "validation")]:
        df = pd.read_parquet(D / "amirveyseh__acronym_identification" / "data" / f"{fn}-00000-of-00001.parquet")
        for _, r in df.iterrows():
            toks, labs = list(r["tokens"]), [int(x) for x in r["labels"]]
            shorts, longs = bio_pairs(toks, labs)
            sent = " ".join(toks)
            rows.append({"input": sent, "output": json.dumps({"short_forms": shorts, "long_forms": longs}),
                         "fold": fold, "id": r["id"]})
            if fold == "validation":
                pred = schwartz_hearst(sent)
                pred_sf = {p[0] for p in pred}
                gold_sf = set(shorts)
                tp_sf += len(pred_sf & gold_sf)
                fp_sf += len(pred_sf - gold_sf)
                # a gold pair is recoverable by a definition-based extractor only if the sentence
                # defines it with parentheses; pair correctness = predicted long form equals a gold long form
                gold_long_norm = {normalise(x) for x in longs}
                for sf, lf in pred:
                    if sf in gold_sf and normalise(lf) in gold_long_norm:
                        tp_pair += 1
                    else:
                        fp_pair += 1
                for sf in gold_sf:
                    if f"( {sf} )" in sent and longs:
                        n_gold_pairs_paren += 1
                fn_sf += len(gold_sf - pred_sf)
    ev = {
        "split": "acronym_identification validation (test labels are hidden in the HF release)",
        "short_form_precision": round(tp_sf / max(1, tp_sf + fp_sf), 4),
        "short_form_recall_all_gold_short_forms": round(tp_sf / max(1, tp_sf + fn_sf), 4),
        "pair_precision": round(tp_pair / max(1, tp_pair + fp_pair), 4),
        "pair_recall_vs_parenthetical_definitions": round(tp_pair / max(1, n_gold_pairs_paren), 4),
        "n_gold_parenthetical_short_forms": n_gold_pairs_paren,
        "note": "Schwartz-Hearst only finds definitions of the form 'long form (SF)'; acronym_identification also labels "
                "undefined short forms, so recall over ALL gold short forms is a lower bound by construction.",
    }
    return rows, ev


def main() -> None:
    se = semeval2017()
    logger.info(f"SemEval-2017 rows: {len(se)}")
    sc = scierc()
    logger.info(f"SciERC rows: {len(sc)}")
    with (ROOT / "raw" / "anchor_phrases.jsonl").open("w") as f:
        for r in se + sc:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ac, ev = acronyms()
    logger.info(f"acronym rows: {len(ac)}; SH eval {ev}")
    with (ROOT / "raw" / "anchor_acronyms.jsonl").open("w") as f:
        for r in ac:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (ROOT / "labelling").mkdir(exist_ok=True)
    (ROOT / "labelling" / "sh_eval.json").write_text(json.dumps(ev, indent=2))


if __name__ == "__main__":
    main()
