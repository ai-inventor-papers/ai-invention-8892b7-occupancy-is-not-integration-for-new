#!/usr/bin/env python3
"""Steps 2 (sense check) + 3 (strata, sampling, FREEZE).
Inputs: screen/screen_results.jsonl, screen/early_window.jsonl, vocab/candidates_*.jsonl, vocab/arxiv_candidates.jsonl.
Output: sample_frame_frozen.json (+ .sha256). Everything here uses only information from years <= F+2."""
import asyncio
import hashlib
import random
from collections import Counter, defaultdict

import numpy as np
import orjson
from loguru import logger

from common import ROOT, setup_logging
from llm_utils import LLM, BudgetStop

SEED = 20260928
N_TARGET = 600
N_REF_TARGET = 60
REF_EVERY = 8  # one reference concept after every 8 main concepts
SENSE_SYS = ("You judge word senses. For each numbered item you get a phrase and paper titles from ONE year that "
             "(may) use it. Decide whether the titles use the phrase in one technical sense. Return ONLY a JSON array "
             "of {\"i\": <item number>, \"single_sense\": true|false, \"dominant_share\": <0..1 share of titles "
             "using the dominant sense; titles that do not contain the phrase count as neither>}.")


def f_band(F: int) -> str:
    return "2005-07" if F <= 2007 else ("2008-11" if F <= 2011 else "2012-16")


def fold_of(cid: str) -> str:
    return "screen" if int(hashlib.sha1(cid.encode()).hexdigest(), 16) % 10 < 7 else "heldout_concept"


async def sense_check(items: list[dict]) -> dict[str, dict]:
    cache_p = ROOT / "screen" / "sense_check.jsonl"
    cache = {}
    if cache_p.exists():
        for line in cache_p.read_text().splitlines():
            r = orjson.loads(line)
            cache[r["concept_id"]] = r
    todo = [x for x in items if x["concept_id"] not in cache and x["yearF_titles"]]
    llm = LLM(ROOT / "screen" / "llm_cost_sense.json")
    batches = [todo[i:i + 8] for i in range(0, len(todo), 8)]

    async def one(b: list[dict]) -> list[dict]:
        txt = "\n\n".join(f"ITEM {k}: phrase = \"{x['phrase']}\"\n" + "\n".join(f"- {t}" for t in x["yearF_titles"])
                          for k, x in enumerate(b))
        res = await llm.json_call(SENSE_SYS, txt, max_tokens=1500)
        out = []
        byi = {int(r.get("i", -1)): r for r in res} if isinstance(res, list) else {}
        for k, x in enumerate(b):
            r = byi.get(k)
            out.append({"concept_id": x["concept_id"], "llm_ok": r is not None,
                        "single_sense": bool(r.get("single_sense", True)) if r else None,
                        "dominant_share": float(r.get("dominant_share", 1.0)) if r else None})
        return out

    try:
        results = await asyncio.gather(*[one(b) for b in batches], return_exceptions=True)
    except BudgetStop:
        results = []
    with cache_p.open("ab") as f:
        for res in results:
            if isinstance(res, BaseException):
                logger.warning(f"sense batch failed: {res}")
                continue
            for r in res:
                cache[r["concept_id"]] = r
                f.write(orjson.dumps(r) + b"\n")
    logger.info(f"sense check cost ${llm.cost:.4f}")
    return cache


def load_candidates() -> dict[str, dict]:
    c = {}
    for fn in ["candidates_main.jsonl", "candidates_ref.jsonl", "arxiv_candidates.jsonl"]:
        p = ROOT / "vocab" / fn
        if p.exists():
            for line in p.read_text().splitlines():
                x = orjson.loads(line)
                c.setdefault(x["concept_id"], x)
    return c


@logger.catch(reraise=True)
def main() -> None:
    """Freeze BEFORE any post-F+2 data is fetched. The eligible pool is < N_TARGET, so every eligible concept is
    sampled with design probability 1; strata (origin field group x volume tercile x F-band) are therefore only
    descriptive. Origin field/subfield and the sense check are computed after freezing from year F..F+2 c-papers
    (outcome-blind variables) by assemble.py; they never change the hydration order."""
    setup_logging("sample_frame")
    cands = load_candidates()
    screen = [orjson.loads(x) for x in (ROOT / "screen" / "screen_results.jsonl").read_text().splitlines()]
    elig = [r for r in screen if r["status"] == "ELIGIBLE"]
    logger.info(f"eligible main: {len(elig)}")
    frame = []
    for r in elig:
        c = cands[r["concept_id"]]
        frame.append({"concept_id": r["concept_id"], "phrase": r["phrase"], "F": r["F"], "V": r["V"],
                      "screen_counts_by_year": {str(k): v for k, v in r["counts"].items()},
                      "burst_start": r.get("burst_start", False), "vocab_arms": c.get("vocab_arms", []),
                      "surface_forms": c.get("surface_forms", []), "acronyms": c.get("acronyms", []),
                      "links": c.get("links", {}), "multi_sense_flag": c.get("multi_sense_flag", False),
                      "llm_screen": c.get("llm_screen", True), "arm_tag": r["arm_tag"]})
    Vs = np.array([x["V"] for x in frame])
    t1, t2 = np.quantile(Vs, [1 / 3, 2 / 3])
    for x in frame:
        x["volume_tercile"] = 1 if x["V"] <= t1 else (2 if x["V"] <= t2 else 3)
        x["F_band"] = f_band(x["F"])
    excluded = Counter()
    pool = list(frame)
    Ns = Counter(f"T{x['volume_tercile']}|{x['F_band']}" for x in pool)
    group_map = {}
    if len(pool) > N_TARGET:
        raise SystemExit("eligible pool exceeds target: stratified sampling branch required")
    sampled = list(pool)
    n_s = dict(Ns)
    for x in sampled:
        x["stratum_pre"] = f"T{x['volume_tercile']}|{x['F_band']}"
        x["stratum"] = x["stratum_pre"]
    rng_u = random.Random(SEED + 1)
    for x in sorted(sampled, key=lambda z: z["concept_id"]):
        x["sample_rank_u"] = rng_u.random()
        x["design_selection_prob"] = 1.0
        x["arm"] = "main"
        x["metadata_fold"] = fold_of(x["concept_id"])
        x["focal_years_screen"] = [t for t in range(2010, 2015) if 3 <= t - x["F"] <= 8]
        x["focal_years_heldout"] = [t for t in range(2016, 2019) if 3 <= t - x["F"] <= 8]
    # reference arm
    # any screened candidate (all arms were drawn outcome-blind) that is stationary-eligible in 1998-2004
    ref_rows = [r for r in screen if r["status"] == "REJECT_PREEXISTING" and r.get("reference_eligible")]
    rng_r = random.Random(SEED + 2)
    ref_rows = sorted(ref_rows, key=lambda z: z["concept_id"])
    ref_pick = rng_r.sample(ref_rows, min(N_REF_TARGET, len(ref_rows)))
    refs = []
    for r in sorted(ref_pick, key=lambda z: z["concept_id"]):
        c = cands[r["concept_id"]]
        refs.append({"concept_id": r["concept_id"], "phrase": r["phrase"], "arm": "reference",
                     "metadata_fold": "reference", "screen_counts_by_year": {str(k): v for k, v in r["counts"].items()},
                     "sample_rank_u": rng_r.random(), "vocab_arms": c.get("vocab_arms", []),
                     "surface_forms": c.get("surface_forms", []), "acronyms": c.get("acronyms", []),
                     "links": c.get("links", {}), "arm_tag": r["arm_tag"],
                     "design_selection_prob": len(ref_pick) / max(len(ref_rows), 1)})
    main_order = sorted(sampled, key=lambda z: z["sample_rank_u"])
    ref_order = sorted(refs, key=lambda z: z["sample_rank_u"])
    order, ri = [], 0
    for k, x in enumerate(main_order, 1):
        order.append(x["concept_id"])
        if k % REF_EVERY == 0 and ri < len(ref_order):
            order.append(ref_order[ri]["concept_id"])
            ri += 1
    order += [x["concept_id"] for x in ref_order[ri:]]
    frozen = {
        "frozen_at_utc": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "seed": SEED, "n_eligible_main": len(frame), "n_pool_after_sense": len(pool),
        "n_sampled_main": len(sampled), "n_reference_eligible": len(ref_rows), "n_reference_sampled": len(refs),
        "excluded_counts": dict(excluded),
        "volume_tercile_cuts": [float(t1), float(t2)], "origin_field_group_map": {str(k): v for k, v in group_map.items()},
        "stratum_sizes_N": dict(Ns), "stratum_alloc_n": n_s,
        "hydration_order": order,
        "eligible": frame, "reference": refs,
    }
    b = orjson.dumps(frozen, option=orjson.OPT_INDENT_2)
    (ROOT / "sample_frame_frozen.json").write_bytes(b)
    h = hashlib.sha256(b).hexdigest()
    (ROOT / "sample_frame_frozen.sha256").write_text(h + "  sample_frame_frozen.json\n")
    logger.info(f"FROZEN sample frame sha256={h}; main sampled={len(sampled)} ref={len(refs)} "
                f"strata={len(Ns)}")


if __name__ == "__main__":
    main()
