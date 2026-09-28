#!/usr/bin/env python3
"""STEP 2: phrase features.
(a) Lexical features for every classifier phrase (D2, D4a, frame), POS-pattern vocabulary fitted on D2-train only.
(b) MiniLM + SPECTER2 embeddings of the union of all phrase strings and linking targets (fp16 on GPU) ->
    cache/emb/{minilm,specter2}.npy (+ _strings.json). Context embeddings (MiniLM of 'phrase [SEP] title') for the
    secondary classifier variant -> cache/emb/minilm_ctx.npy.
Sampling-artefact fields of D2 (track, prescreen flag, audit arm, stratum, sample counts, n_fields, macro-domain)
are deliberately NOT features: they describe how D2 was sampled and do not exist for frame phrases."""
from __future__ import annotations

import json
import pickle
import random
import time

import numpy as np
import pandas as pd
from loguru import logger

from common import CACHE, WORK, DATA, DS4, MINI, SEED, load_frame, normalise, read_json, set_limits, setup_logging, write_json
from featlib import LexicalFeaturizer, emb_text

import sys
sys.path.insert(0, str(DATA.parent / "src" / "vendor"))


def mesh_variants(term: str) -> list[str]:
    from linking import _mesh_variants  # reused DS4 logic (inverted MeSH entry terms)
    return _mesh_variants(term)


def vocab_strings() -> list[str]:
    V = DS4 / "data_out" / "vocab"
    out = []
    for r in read_json(V / "openalex_keywords_snapshot_2026-09-23.json.gz"):
        out.append(emb_text(r["display_name"] or ""))
    for r in read_json(V / "openalex_legacy_concepts_snapshot_2026-09-23.json.gz"):
        out.append(emb_text(r["display_name"] or ""))
    for r in read_json(V / "mesh_descriptors_2026.json.gz"):
        for t in [r["heading"]] + r["entry_terms"]:
            for v in mesh_variants(t):
                out.append(emb_text(v))
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("s2_features")
    set_limits(40)
    t0 = time.time()
    d2 = read_json(DATA / "d2.json")
    d4a = read_json(DATA / "d4a.json")
    d3 = read_json(DATA / "d3.json")
    mp = read_json(DATA / "mesh_pairs.json")
    hm = read_json(DATA / "heldout_mesh_concepts.json")
    d5 = read_json(DATA / "d5.json")
    frame = load_frame()

    # ---------------- (a) lexical
    lf = LexicalFeaturizer()
    train_keys = [r["key"] for r in d2 if r["metadata_fold"] == "train"]
    lf.fit_patterns(train_keys)
    rows = []
    items = [("d2", r["key"], r["key"], r["surface_forms"], r["acronym_short_forms"]) for r in d2]
    items += [("d4a", p, normalise(p) or p.lower(), [p], []) for p in sorted({r["phrase"] for r in d4a})]
    items += [("frame", cid, normalise(c["phrase"]), list(c.get("surface_forms") or []), list(c.get("acronyms") or []))
              for cid, c in frame.items()]
    lf.pos([it[2] for it in items])
    names = lf.names()
    for ns, ident, key, sfs, acr in items:
        rows.append({"ns": ns, "id": ident, **dict(zip(names, lf.transform(key, sfs, acr)))})
    lex = pd.DataFrame(rows)
    lex.to_parquet(WORK / "lexical.parquet")
    write_json(WORK / "lexical_meta.json", {"names": names, "pos_patterns_fit_on": "D2-train", "patterns": lf.patterns})
    logger.info(f"lexical features: {lex.shape} ({time.time() - t0:.0f}s)")

    # ---------------- (b) embeddings
    S: list[str] = []
    S += [emb_text(r["key"]) for r in d2]
    S += [emb_text(r["phrase"]) for r in d4a]
    for r in d3:
        S += [emb_text(r["phrase_1"]), emb_text(r["phrase_2"])]
    for r in mp:
        S += [emb_text(r["term_a"]), emb_text(r["term_b"])]
    for r in hm:
        S += [emb_text(x) for x in [r["preferred_term"]] + r["surface_forms"] + r["acronyms"]]
    for c in frame.values():
        S += [emb_text(x) for x in [c["phrase"]] + list(c.get("surface_forms") or []) + list(c.get("acronyms") or [])]
    for r in d5:
        ph = r["input"].get("phrase") or r["input"].get("key") or ""
        S.append(emb_text(ph))
    if not MINI:
        S += vocab_strings()
    else:
        S += random.Random(SEED).sample(vocab_strings(), 1000)
    S = sorted({s for s in S if s})
    logger.info(f"{len(S)} distinct strings to embed")

    # context strings (secondary classifier variant): phrase [SEP] title/snippet
    th = pickle.load(open(WORK / "termhood.pkl", "rb"))
    ctx: dict[str, list[str]] = {}
    for r in d2:
        ctx[f"d2:{r['key']}"] = [f"{r['key']} [SEP] {s[:300]}" for s in r["snippets"][:5]]
    rng = random.Random(SEED)
    for cid, c in frame.items():
        hits = th["frame_title_hits"].get(f"frame:{cid}", [])
        titles = [t for src, y, t in hits if t]
        titles = [t for t in titles if t]
        rng.shuffle(titles)
        ctx[f"frame:{cid}"] = [f"{c['phrase']} [SEP] {t[:300]}" for t in titles[:5]]
    ctx_strings = sorted({s for v in ctx.values() for s in v})

    from encoders import Encoder
    import gc
    import torch
    notes = {}
    for name in ("minilm", "specter2"):
        enc = Encoder(name)
        notes[name] = enc.note
        # T5 timing on 10k strings, extrapolate
        t1 = time.time()
        _ = enc.encode(S[:10000])
        dt = time.time() - t1
        logger.info(f"{name}: 10k strings in {dt:.1f}s -> projected {dt * len(S) / 10000 / 60:.1f} min for {len(S)}")
        M = enc.encode(S)
        np.save(WORK / "emb" / f"{name}.npy", M.astype(np.float16))
        (WORK / "emb" / f"{name}_strings.json").write_text(json.dumps(S, ensure_ascii=False))
        if name == "minilm":
            C = enc.encode(ctx_strings, batch=256)
            np.save(WORK / "emb" / "minilm_ctx.npy", C.astype(np.float16))
            (WORK / "emb" / "minilm_ctx_strings.json").write_text(json.dumps(ctx_strings, ensure_ascii=False))
            write_json(WORK / "emb" / "ctx_map.json", ctx, indent=None)
        del enc, M
        gc.collect()
        torch.cuda.empty_cache()
    write_json(WORK / "emb" / "meta.json", {"n_strings": len(S), "n_ctx": len(ctx_strings), "notes": notes,
                                             "runtime_s": time.time() - t0})
    logger.info(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
