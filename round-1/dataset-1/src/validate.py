#!/usr/bin/env python3
"""Step 8 assertions: (1) no screening record holds a year > F+2 (or > 2004 for pre-existing, > 2016 no-onset);
(2) sample-frame sha256 unchanged; (3) 50 random concept-work links re-verified by regex on stored text;
(4) every D3 work_id is in D2; (5) fold ratio ~70/30; (6) credit ledger total <= cap; (7) no API key in outputs;
(8) file sizes < 100 MB. Writes logs/validation.json."""
import glob
import hashlib
import random
from collections import Counter
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

from common import ROOT, ARTIFACT_CAP, api_key, fold, ledger_total, setup_logging, verify_regex
from hydrate_lib import Store


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("validate")
    res = {}
    # (1)
    bad = 0
    for line in (ROOT / "screen" / "screen_results.jsonl").read_text().splitlines():
        r = orjson.loads(line)
        ys = [int(y) for y in r.get("counts", {})]
        lim = r["F"] + 2 if "F" in r else (2004 if r["status"] == "REJECT_PREEXISTING" else 2016)
        if ys and max(ys) > lim:
            bad += 1
    fr = orjson.loads((ROOT / "sample_frame_frozen.json").read_bytes())
    for x in fr["eligible"]:
        if max(int(y) for y in x["screen_counts_by_year"]) > x["F"] + 2:
            bad += 1
    res["1_no_post_F2_years_in_screening"] = bad == 0
    # (2)
    h = hashlib.sha256((ROOT / "sample_frame_frozen.json").read_bytes()).hexdigest()
    res["2_frame_sha256_unchanged"] = h == (ROOT / "sample_frame_frozen.sha256").read_text().split()[0]
    # (3)
    cw = pd.read_parquet(ROOT / "concept_work.parquet")
    byid = {x["concept_id"]: x for x in fr["eligible"] + fr["reference"]}
    smp = cw.sample(min(50, len(cw)), random_state=1)
    works = Store().get_many([int(w) for w in smp.work_id])
    ok = 0
    for r in smp.itertuples():
        w = works.get(int(r.work_id))
        rx = verify_regex(fold(byid[r.concept_id]["phrase"]))
        if w and (rx.search(fold(w["text"])) or r.match_evidence in ("s2_only", "oa_index_only")):
            ok += 1
    res["3_links_reverified"] = f"{ok}/{len(smp)}"
    # (4)
    d2 = set()
    for f in sorted(glob.glob(str(ROOT / "works" / "works_part_*.parquet"))):
        d2 |= set(pq.read_table(f, columns=["work_id"]).column(0).to_pylist())
    res["4_all_D3_in_D2"] = set(cw.work_id.unique()) <= d2
    # (5)
    d = orjson.loads((ROOT / "data_out.json").read_bytes())
    fc = Counter(e["metadata_fold"] for e in d["datasets"][0]["examples"] if e["metadata_arm"] == "main")
    res["5_fold_counts_main"] = dict(fc)
    res["5_screen_share"] = round(fc["screen"] / max(sum(fc.values()), 1), 3)
    # (6)
    res["6_ledger_total"] = ledger_total()
    res["6_ledger_le_cap"] = ledger_total() <= ARTIFACT_CAP
    # (7)
    key = api_key()
    leaks = []
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in {".json", ".jsonl", ".md", ".py", ".yaml", ".log", ".txt", ".out", ".toml"} \
                and ".venv" not in p.parts and "raw_cache" not in p.parts and p.name != ".env" and p.stat().st_size < 200e6:
            try:
                if key in p.read_text(errors="ignore"):
                    leaks.append(str(p.relative_to(ROOT)))
            except OSError:
                pass
    res["7_api_key_leaks"] = leaks
    # (8)
    big = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and p.stat().st_size >= 100e6
           and ".venv" not in p.parts]
    res["8_files_ge_100MB"] = big
    (ROOT / "logs" / "validation.json").write_bytes(orjson.dumps(res, option=orjson.OPT_INDENT_2))
    logger.info(orjson.dumps(res).decode())


if __name__ == "__main__":
    main()
