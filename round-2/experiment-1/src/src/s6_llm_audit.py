#!/usr/bin/env python3
"""STEP 6: sense proxy + frame silver audit (+ link audit with --links), OpenRouter only, hard cap $0.30 for this artifact.
(a) sense proxy for all 426 frame concepts: year-F titles (arXiv first, D1 if arXiv < 3; reference arm: 2000-2004 titles)
    with DS1 assemble.py SENSE_SYS verbatim, google/gemini-3.1-flash-lite, batches of 8 (as assemble.py);
    validated against the 183 OpenAlex-based values (Spearman, >= 0.70 agreement, Cohen kappa).
(b) frame silver labels: model A = google/gemini-2.5-flash-lite with DS4's codebook prompt (vendored llm.system_prompt
    + s5_label.render_batch format), batches of 20 grouped by head token, temperature 0; classifier/A disagreements
    adjudicated by anthropic/claude-haiku-4.5 with the same codebook prompt (DS4 adjudication protocol).
    Refuses to run unless results/frame_predictions_prelabel.json (+ sha256) already exists.
(c) --links: every accepted stage-2 / broader frame link judged {SAME, BROADER_TARGET, NARROWER_TARGET, DIFFERENT}.
Priority if the cap is reached: (a) > (b) labels > adjudication > (c)."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import pickle
import random
import sys
import time

import numpy as np
import requests
from loguru import logger
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

from common import CACHE, WORK, DATA, LOGS, MINI, RESULTS, SEED, SRC, load_frame, read_json, setup_logging, write_json

sys.path.insert(0, str(SRC / "vendor"))
import llm as vllm  # noqa: E402  (DS4 client, reused; paths/cap patched below)

vllm.LEDGER = LOGS / "llm_spend.jsonl"
vllm.CACHE = CACHE / "llm"
vllm.CODEBOOK = DATA / "codebook.md"
vllm.HARD_CAP_USD = 0.30
MODEL_SENSE = "google/gemini-3.1-flash-lite"
MODEL_A = vllm.MODEL_A
MODEL_ADJ = vllm.MODEL_ADJ
# DS1 assemble.py lines 35-37, verbatim
SENSE_SYS = ("You judge word senses. For each numbered item you get a phrase and paper titles from ONE year that "
             "use it. Decide whether the titles use the phrase in one technical sense. Return ONLY a JSON array of "
             "{\"i\": <item number>, \"dominant_share\": <0..1 share of titles using the dominant sense>}.")
LINK_SYS = ("You compare a scientific phrase with a vocabulary entry it was automatically linked to. Decide the relation "
            "of the TARGET to the PHRASE: SAME (same concept, incl. surface variants/synonyms), BROADER_TARGET (target is a "
            "more general parent concept), NARROWER_TARGET (target is more specific), DIFFERENT (unrelated or a different "
            "concept). Return ONLY JSON {\"items\": [{\"id\": <id>, \"relation\": \"SAME|BROADER_TARGET|NARROWER_TARGET|DIFFERENT\"}]}.")


def check_budget() -> dict:
    import os
    r = requests.get(f"{os.environ['OPENROUTER_BASE_URL']}/key", headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}, timeout=30)
    d = r.json().get("data", {})
    logger.info(f"OpenRouter phase budget: limit {d.get('limit')} remaining {d.get('limit_remaining')}")
    return d


def render_batch(keys: list[str], items: dict) -> tuple[str, dict]:
    """DS4 scripts/s5_label.py render_batch, verbatim logic."""
    idmap, lines = {}, []
    for i, k in enumerate(keys, 1):
        it = items[k]
        iid = f"k{i}"
        idmap[iid] = k
        lines.append(json.dumps({"id": iid, "phrase": it["phrase"], "surface_forms": it["surface_forms"],
                                 "acronym_short_forms": it.get("acronym_short_forms", []),
                                 "snippets": [s["text"] for s in it["snippets"]]}, ensure_ascii=False))
    user = "Label each item.\n" + "\n".join(lines)
    return user, idmap


def norm_label(x: str | None) -> str:
    x = (x or "").upper().replace("-", "_").strip()
    if x.startswith("VARIANT"):
        return "VARIANT_OF"
    return x if x in ("CONCEPT", "NOT_CONCEPT", "TOO_GENERIC") else "NOT_CONCEPT" if "NOT" in x else "INVALID"


def titles_for(th: dict, cid: str) -> list[tuple[str, int, str]]:
    return th["frame_title_hits"].get(f"frame:{cid}", [])


def rebind(llm) -> None:
    """asyncio primitives are bound to the loop that first uses them; give each asyncio.run its own."""
    llm.sem = asyncio.Semaphore(8)
    llm._lock = asyncio.Lock()


async def label_items(llm, model: str, keys: list[str], items: dict, tag: str) -> dict:
    rebind(llm)
    ks = sorted(keys, key=lambda k: (items[k]["phrase"].split(" ")[-1], items[k]["phrase"]))
    batches = [ks[i:i + 20] for i in range(0, len(ks), 20)]
    out = {}
    sysmsg = vllm.system_prompt()

    async def run(bi, b):
        user, idmap = render_batch(b, items)
        try:
            d = await llm.call_json(model=model, system=sysmsg, user=user, tag=f"{tag}:{bi}")
        except vllm.BudgetStop as e:
            logger.error(f"budget stop: {e}")
            return
        except RuntimeError as e:
            logger.error(f"batch {bi} failed: {e}")
            return
        for r in d.get("items") or []:
            if isinstance(r, dict) and idmap.get(str(r.get("id"))):
                out[idmap[str(r["id"])]] = {"label": norm_label(r.get("label")), "rationale": str(r.get("rationale", ""))[:150],
                                            "confidence": r.get("confidence"), "model": d.get("_model")}

    await asyncio.gather(*[run(i, b) for i, b in enumerate(batches)])
    return out


def part_a(llm, frame, th) -> dict:
    rng_seed = SEED
    items = []
    for cid, c in sorted(frame.items()):
        hits = titles_for(th, cid)
        if c["arm"] == "main":
            F = int(c["F"])
            arx = [t for s, y, t in hits if s == "arxiv" and y == F and t]
            d1 = [t for s, y, t in hits if s == "d1" and y == F and t]
        else:
            arx = [t for s, y, t in hits if s == "arxiv" and 2000 <= y <= 2004 and t]
            d1 = [t for s, y, t in hits if s == "d1" and 2000 <= y <= 2004 and t]
        pool = arx if len(arx) >= 3 else arx + d1
        pool = sorted(set(pool))
        random.Random(f"{rng_seed}:{cid}").shuffle(pool)
        items.append({"concept_id": cid, "phrase": c["phrase"], "titles": [t[:250] for t in pool[:20]],
                      "title_source": "arxiv" if len(arx) >= 3 else ("arxiv+d1" if pool else "none")})
    todo = [x for x in items if len(x["titles"]) >= 3]
    logger.info(f"sense proxy: {len(todo)}/{len(items)} concepts with >= 3 titles")
    res = {}

    async def go():
        rebind(llm)

        async def one(bi, b):
            txt = "\n\n".join(f"ITEM {k}: phrase = \"{x['phrase']}\"\n" + "\n".join(f"- {t}" for t in x["titles"]) for k, x in enumerate(b))
            try:
                d = await llm.call_json(model=MODEL_SENSE, system=SENSE_SYS, user=txt, tag=f"sense:{bi}", max_tokens=800)
            except (vllm.BudgetStop, RuntimeError) as e:
                logger.error(f"sense batch {bi}: {e}")
                return
            arr = d.get("items")
            if arr is None:
                arr = next((v for v in d.values() if isinstance(v, list)), [])
            byi = {int(r.get("i", -1)): r for r in arr if isinstance(r, dict) and str(r.get("i", "")).lstrip("-").isdigit()}
            for k, x in enumerate(b):
                if k in byi:
                    try:
                        res[x["concept_id"]] = float(byi[k].get("dominant_share"))
                    except (TypeError, ValueError):
                        pass
        batches = [todo[i:i + 8] for i in range(0, len(todo), 8)]
        await asyncio.gather(*[one(i, b) for i, b in enumerate(batches)])

    asyncio.run(go())
    return {"items": items, "sense_proxy": res}


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--links", action="store_true", help="run part (c) link audit only")
    ap.add_argument("--probe", action="store_true", help="T6 probe: one 5-item batch per model, extrapolate")
    ap.add_argument("--dry-run", action="store_true", help="no LLM calls (T2 mini pipeline)")
    args = ap.parse_args()
    setup_logging("s6_llm_audit")
    budget = check_budget() if not args.dry_run else {}
    frame = load_frame()
    th = pickle.load(open(WORK / "termhood.pkl", "rb"))
    llm = vllm.LLM(concurrency=8)
    logger.info(f"artifact LLM spend so far ${llm.spent:.4f} (cap ${vllm.HARD_CAP_USD})")

    if args.probe:
        cids = sorted(frame)[:5]
        items = {c: {"phrase": frame[c]["phrase"], "surface_forms": frame[c].get("surface_forms", []), "acronym_short_forms": frame[c].get("acronyms", []),
                     "snippets": [{"text": t} for _, _, t in titles_for(th, c)[:3]]} for c in cids}

        async def go():
            rebind(llm)
            for m in (MODEL_A, MODEL_ADJ, MODEL_SENSE):
                user, _ = render_batch(cids, items)
                d = await llm.call_json(model=m, system=vllm.system_prompt(), user=user + "\n", tag=f"probe:{m}")
                logger.info(f"probe {m}: 5 items ${d['_cost']:.5f} -> per item ${d['_cost'] / 5:.6f}; {json.dumps(d.get('items', [])[:2])[:300]}")
        asyncio.run(go())
        return

    if args.links:
        lk = read_json(RESULTS / "frame_links_for_audit.json")
        if args.dry_run or not lk:
            write_json(RESULTS / "link_audit.json", {"skipped": "dry-run" if args.dry_run else "no stage-2/broader links", "items": {}})
            return
        out = {}

        async def go():
            rebind(llm)

            async def one(bi, b):
                lines = [json.dumps({"id": x["id"], "phrase": x["phrase"], "target": x["target_label"], "target_vocab": x["target_vocab"]}) for x in b]
                try:
                    d = await llm.call_json(model=MODEL_A, system=LINK_SYS, user="\n".join(lines), tag=f"link:{bi}", max_tokens=1500)
                except (vllm.BudgetStop, RuntimeError) as e:
                    logger.error(f"link batch {bi}: {e}")
                    return
                for r in d.get("items") or []:
                    if isinstance(r, dict):
                        out[str(r.get("id"))] = str(r.get("relation", "")).upper()
            await asyncio.gather(*[one(i, lk[i:i + 20]) for i in range(0, len(lk), 20)])
        asyncio.run(go())
        write_json(RESULTS / "link_audit.json", {"model": MODEL_A, "n": len(lk), "items": out,
                                                 "spend_total_usd": vllm.spent_so_far()})
        logger.info(f"link audit: {len(out)}/{len(lk)} judged; spend ${vllm.spent_so_far():.4f}")
        return

    # guard: classifier predictions must be frozen first
    pre = RESULTS / "frame_predictions_prelabel.json"
    sha = RESULTS / "frame_predictions_prelabel.sha256"
    assert pre.exists() and sha.exists(), "frame_predictions_prelabel.json must exist before any frame label is requested"
    assert hashlib.sha256(pre.read_bytes()).hexdigest() == sha.read_text().strip(), "prelabel sha mismatch"
    preds = {r["concept_id"]: r for r in json.loads(pre.read_text())["predictions"]}
    out: dict = {"budget_at_start": budget, "prelabel_sha256": sha.read_text().strip(),
                 "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if args.dry_run:
        out["dry_run"] = True
        write_json(RESULTS / "frame_llm_audit.json", {**out, "sense_proxy": {}, "labels_A": {}, "labels_adj": {}, "sense_items": []})
        return
    # (a) sense proxy
    a = part_a(llm, frame, th)
    sense_oa = {json.loads(l)["concept_id"]: json.loads(l)["dominant_share"] for l in (DATA / "sense_check.jsonl").read_text().splitlines()}
    both = [c for c in sense_oa if c in a["sense_proxy"] and sense_oa[c] is not None]
    val = {"n_overlap": len(both)}
    if len(both) >= 10:
        x = np.array([sense_oa[c] for c in both])
        y = np.array([a["sense_proxy"][c] for c in both])
        val.update({"spearman": float(spearmanr(x, y).correlation), "agreement_cut_0.70": float(np.mean((x >= 0.7) == (y >= 0.7))),
                    "kappa_cut_0.70": float(cohen_kappa_score(x >= 0.7, y >= 0.7)),
                    "oa_fail_share": float(np.mean(x < 0.7)), "proxy_fail_share": float(np.mean(y < 0.7)),
                    "confusion_oa_rows_proxy_cols": [[int(np.sum((x < .7) & (y < .7))), int(np.sum((x < .7) & (y >= .7)))],
                                                     [int(np.sum((x >= .7) & (y < .7))), int(np.sum((x >= .7) & (y >= .7)))]]})
    val["F9_triggered"] = bool(val.get("kappa_cut_0.70", 0) < 0.4)
    out["sense_validation"] = val
    logger.info(f"sense proxy validation {val}; spend ${llm.spent:.4f}")
    # (b) frame silver labels with model A
    items = {}
    for cid, c in frame.items():
        hits = titles_for(th, cid)
        titles = sorted({t for _, _, t in hits if t})
        random.Random(f"{SEED}:snip:{cid}").shuffle(titles)
        items[cid] = {"phrase": c["phrase"], "surface_forms": list(c.get("surface_forms") or []),
                      "acronym_short_forms": list(c.get("acronyms") or []), "snippets": [{"text": t[:300]} for t in titles[:3]]}
    labs_A = asyncio.run(label_items(llm, MODEL_A, sorted(items), items, "frameA")) if not llm.stopped else {}
    logger.info(f"model A labelled {len(labs_A)}/{len(items)}; spend ${llm.spent:.4f}")
    dis = sorted(c for c in labs_A if (labs_A[c]["label"] == "CONCEPT") != preds[c]["accepted_primary"])
    labs_adj = asyncio.run(label_items(llm, MODEL_ADJ, dis, items, "frameADJ")) if dis and not llm.stopped else {}
    logger.info(f"adjudicated {len(labs_adj)}/{len(dis)} classifier-vs-A disagreements; spend ${llm.spent:.4f}")
    out.update({"sense_proxy": a["sense_proxy"], "sense_items": [{k: v for k, v in x.items() if k != "titles"} | {"n_titles": len(x["titles"])} for x in a["items"]],
                "labels_A": labs_A, "labels_adj": labs_adj, "disagreements": dis, "models": {"sense": MODEL_SENSE, "A": MODEL_A, "adj": MODEL_ADJ},
                "spend_total_usd": llm.spent, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    write_json(RESULTS / "frame_llm_audit.json", out)


if __name__ == "__main__":
    main()
