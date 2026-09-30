#!/usr/bin/env python3
"""S5b/D3: variant pairs (SAME / DIFFERENT) for the variant merger.

Positives (curated): (i) Schwartz-Hearst acronym <-> long form from the corpus; (ii) MeSH heading <-> entry
term with BOTH strings in the corpus; (iii) Wikidata label <-> alias for legacy-concept-linked phrases.
(iv) VARIANT_OF links from labellers A/B (LLM-judged SAME/DIFFERENT).
Hard negatives: (v) one acronym with different long forms in the corpus; (vi) lexical near-duplicates
(rapidfuzz token_set_ratio >= 85) that are not curated synonyms (LLM-judged).
LLM: A and B judge (iv), (vi) and a 50-pair audit subset of (i)-(iii); the adjudicator resolves A/B disagreements.
Output: labelling/variant_pairs.json
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm import LLM, MODEL_A, MODEL_ADJ, MODEL_B, BudgetStop, pair_system_prompt  # noqa: E402
from linking import Linker, wikidata_aliases  # noqa: E402
from textnorm import normalise  # noqa: E402
from rawio import load_pickle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labelling"
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s5b_pairs.log", rotation="30 MB", level="DEBUG")
SEED = 20260930


def squash(k: str) -> str:
    return re.sub(r"[^a-z0-9]", "", k.lower())


def main() -> None:
    rng = random.Random(SEED)
    C = load_pickle("candidates")
    M = load_pickle("docs_meta")
    items = json.loads((LAB / "items.json").read_text())
    AB = json.loads((LAB / "labels_AB.json").read_text())
    sp = json.loads((LAB / "split.json").read_text())
    split, cluster = sp["split"], sp["cluster"]
    docs = C["docs_by_key"]

    def ctx(k: str) -> str:
        for di, s0, s1 in C["snips"].get(k, [])[:1]:
            t = M["texts"][di][s0:s1].strip()
            return t[:220] + ("…" if len(t) > 220 else "")
        return ""

    pairs: list[dict] = []
    seen = set()

    def add(p1: str, p2: str, k1: str, k2: str, source: str, label: str | None, gold: str | None):
        sig = tuple(sorted([squash(p1), squash(p2)]))
        if sig[0] == sig[1] or sig in seen:
            return False
        seen.add(sig)
        pairs.append({"phrase_1": p1, "phrase_2": p2, "key_1": k1, "key_2": k2, "source": source,
                      "curated_label": label, "gold_source": gold, "context_1": ctx(k1), "context_2": ctx(k2)})
        return True

    # (i) acronym <-> long form (>=2 docs define it)
    acr = sorted([(n, sf, lk) for (sf, lk), n in C["acr_pairs"].items() if n >= 2 and len(sf) >= 2], reverse=True)
    rng.shuffle(acr)
    n_i = 0
    for n, sf, lk in acr:
        lf_surf = max(C["acr_lf_surface"][(sf, lk)].items(), key=lambda x: x[1])[0]
        if add(sf, lf_surf, sf.lower(), lk, "acronym_long_form_schwartz_hearst", "SAME", "Schwartz-Hearst(corpus)"):
            n_i += 1
        if n_i >= 90:
            break
    # (ii) MeSH heading <-> entry term, both in corpus
    linker = Linker()
    mesh_c = []
    for h, e, ui in linker.mesh_pairs:
        kh, ke = normalise(h), normalise(e)
        if kh != ke and kh in docs and ke in docs and squash(kh) != squash(ke):
            mesh_c.append((h, e, kh, ke, ui))
    rng.shuffle(mesh_c)
    n_ii = 0
    for h, e, kh, ke, ui in mesh_c:
        if add(h, e, kh, ke, "mesh_entry_term", "SAME", f"MeSH:{ui}"):
            n_ii += 1
        if n_ii >= 90:
            break
    # (iii) Wikidata label <-> alias for L-track phrases linked to legacy concepts (QIDs known)
    qid_key = {}
    for k in items:
        l = linker.link(k, items[k]["surface_forms"])
        if l["concept"] and l["concept"].get("wikidata"):
            qid_key[l["concept"]["wikidata"]] = k
    qids = sorted(qid_key)[:400]
    al = asyncio.run(wikidata_aliases(qids)) if qids else {}
    n_iii = 0
    wd_c = []
    for q, d in al.items():
        for a in d.get("aliases", []):
            if d.get("label") and squash(a) != squash(d["label"]) and len(a) > 2:
                wd_c.append((d["label"], a, q))
    rng.shuffle(wd_c)
    for lab, a, q in wd_c:
        if add(lab, a, normalise(lab), normalise(a), "wikidata_alias", "SAME", f"Wikidata:{q}"):
            n_iii += 1
        if n_iii >= 60:
            break
    # (iv) VARIANT_OF links from labellers
    n_iv = 0
    for name in ("A", "B"):
        for k, r in AB[name].items():
            vo = r.get("variant_of")
            if r.get("label") == "VARIANT_OF" and vo and vo in items:
                if add(items[k]["surface_forms"][0], items[vo]["surface_forms"][0], k, vo, f"llm_variant_of_{name}", None, None):
                    n_iv += 1
    # (v) same acronym, different long forms
    by_sf = defaultdict(list)
    for (sf, lk), n in C["acr_pairs"].items():
        by_sf[sf].append((n, lk))
    n_v = 0
    sfs = sorted(by_sf)
    rng.shuffle(sfs)
    for sf in sfs:
        lfs = sorted(by_sf[sf], reverse=True)
        if len(lfs) < 2:
            continue
        (n1, a), (n2, b) = lfs[0], lfs[1]
        if fuzz.token_set_ratio(a, b) >= 70:
            continue
        sa = max(C["acr_lf_surface"][(sf, a)].items(), key=lambda x: x[1])[0]
        sb = max(C["acr_lf_surface"][(sf, b)].items(), key=lambda x: x[1])[0]
        if add(sa, sb, a, b, f"acronym_ambiguity({sf})", "DIFFERENT", "corpus: distinct expansions of one short form"):
            n_v += 1
        if n_v >= 90:
            break
    # (vi) lexical near-duplicates among labelled keys (L + P tracks), not curated synonyms
    keys = sorted(items)
    by_head = defaultdict(list)
    for k in keys:
        by_head[k.split(" ")[-1]].append(k)
    cand = []
    for h, ks in by_head.items():
        if len(ks) < 2 or len(ks) > 400:
            continue
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = ks[i], ks[j]
                if fuzz.token_set_ratio(a, b) >= 85 and squash(a) != squash(b):
                    cand.append((a, b))
    rng.shuffle(cand)
    n_vi = 0
    for a, b in cand:
        if add(items[a]["surface_forms"][0], items[b]["surface_forms"][0], a, b, "lexical_near_duplicate", None, None):
            n_vi += 1
        if n_vi >= 170:
            break
    logger.info(f"pairs: acr={n_i} mesh={n_ii} wikidata={n_iii} llm_variant={n_iv} acr_ambig={n_v} near_dup={n_vi}")

    # LLM judging: all uncurated pairs + a 50-pair audit of curated positives/negatives
    curated_idx = [i for i, p in enumerate(pairs) if p["curated_label"]]
    audit_idx = set(rng.sample(curated_idx, min(50, len(curated_idx))))
    todo = [i for i, p in enumerate(pairs) if not p["curated_label"] or i in audit_idx]
    sysmsg = pair_system_prompt()

    async def judge(model: str, idxs: list[int], tag: str) -> dict[int, dict]:
        llm = LLM(concurrency=10)
        out: dict[int, dict] = {}

        async def run(bi: int, b: list[int]):
            lines = [json.dumps({"id": f"p{j}", "phrase_1": pairs[i]["phrase_1"], "phrase_2": pairs[i]["phrase_2"],
                                 "context_1": pairs[i]["context_1"][:200], "context_2": pairs[i]["context_2"][:200]},
                                ensure_ascii=False) for j, i in enumerate(b)]
            try:
                d = await llm.call_json(model=model, system=sysmsg, user="Judge each pair.\n" + "\n".join(lines), tag=f"{tag}:{bi}")
            except (BudgetStop, RuntimeError) as e:
                logger.error(f"{tag} batch {bi}: {e}")
                return
            for r in d.get("items") or []:
                if not isinstance(r, dict):
                    continue
                m = re.match(r"p(\d+)$", str(r.get("id")))
                if m and int(m.group(1)) < len(b):
                    lab = str(r.get("label", "")).upper()
                    out[b[int(m.group(1))]] = {"label": "SAME" if lab.startswith("SAME") else "DIFFERENT",
                                               "confidence": r.get("confidence"), "model": d.get("_model")}
        await asyncio.gather(*[run(bi, idxs[i:i + 20]) for bi, i in enumerate(range(0, len(idxs), 20))])
        logger.info(f"{tag}: {len(out)}/{len(idxs)}; spent ${llm.spent:.4f}")
        return out

    A = asyncio.run(judge(MODEL_A, todo, "pairA"))
    B = asyncio.run(judge(MODEL_B, todo, "pairB"))
    dis = [i for i in todo if i in A and i in B and A[i]["label"] != B[i]["label"] and not pairs[i]["curated_label"]]
    ADJ = asyncio.run(judge(MODEL_ADJ, dis, "pairADJ")) if dis else {}

    def fold_of(k: str) -> str | None:
        if k in split:
            return split[k]
        return None

    for i, p in enumerate(pairs):
        p["llm_label_A"] = A.get(i, {}).get("label")
        p["llm_label_B"] = B.get(i, {}).get("label")
        p["llm_label_adj"] = ADJ.get(i, {}).get("label")
        if p["curated_label"]:
            p["final_label"] = p["curated_label"]
            p["label_basis"] = "curated"
        elif p["llm_label_adj"]:
            p["final_label"] = p["llm_label_adj"]
            p["label_basis"] = "adjudicator (A/B disagreed)"
        elif p["llm_label_A"] and p["llm_label_A"] == p["llm_label_B"]:
            p["final_label"] = p["llm_label_A"]
            p["label_basis"] = "A/B consensus"
        else:
            p["final_label"] = "UNRESOLVED"
            p["label_basis"] = "missing LLM label"
        f1, f2 = fold_of(p["key_1"]), fold_of(p["key_2"])
        if f1 and f2:
            p["fold"] = f1 if f1 == f2 else "test"
            p["cross_split"] = f1 != f2
        elif f1 or f2:
            p["fold"] = f1 or f2
            p["cross_split"] = False
        else:
            h = int(hashlib.sha1("|".join(sorted([squash(p["key_1"]), squash(p["key_2"])])).encode()).hexdigest(), 16)
            p["fold"] = "test" if h % 5 == 0 else "train"
            p["cross_split"] = False
        p["cluster_1"] = cluster.get(p["key_1"])
        p["cluster_2"] = cluster.get(p["key_2"])
    aud = [i for i in audit_idx if i in A and i in B]
    agree = {"n_audit_curated": len(aud),
             "A_agrees_with_curated": round(sum(A[i]["label"] == pairs[i]["curated_label"] for i in aud) / max(1, len(aud)), 4),
             "B_agrees_with_curated": round(sum(B[i]["label"] == pairs[i]["curated_label"] for i in aud) / max(1, len(aud)), 4),
             "n_AB_disagreements_uncurated": len(dis)}
    (LAB / "variant_pairs.json").write_text(json.dumps({"pairs": pairs, "llm_vs_curated": agree}, ensure_ascii=False))
    from collections import Counter
    logger.info(f"{len(pairs)} pairs; labels {Counter(p['final_label'] for p in pairs)}; agreement {agree}")


if __name__ == "__main__":
    main()
