#!/usr/bin/env python3
"""Build the held-out MeSH confirmation population (metadata_fold='heldout_mesh') end to end.

Pipeline (each step caches to temp/ and is resumable):
  0. download MeSH files (desc2017/desc2026 XML, ASCII d2005..d2016, replace2005..2016) into raw/
  1. scripts/s01_mesh_candidates.py   candidates, provenance classes, surface forms, synonym pairs (free)
  2. scripts/s02_pubmed_prescreen.py  PubMed [tiab] novelty / early-volume pre-screen (free, NCBI E-utilities)
  3. scripts/s03_sample_and_indexed.py stratified outcome-blind working list + [MeSH Terms:noexp] PMID sets (free)
  4. scripts/s06_calibrate.py fetch   plain main-corpus OpenAlex query for 10 calibration concepts (paid, ~150 credits)
  5. scripts/s04_retrieve.py remainder OpenAlex title_and_abstract.search restricted to has_pmid:false (paid, capped)
  6. scripts/s04_retrieve.py pubmed    OpenAlex singleton lookups for all [tiab] PMIDs (free)
  7. scripts/s05_finalize.py final     final rule, data_out.json, works parts, pairs, selection flow, QA
  8. scripts/s06_calibrate.py compare  route calibration table (local)
  widening (plan failure scenario, used in this run): s01/s02 with AII_TAG=w1 (2004-2005, desc2017) and
  AII_TAG=w2 (2017-2018, desc2019), then s03b_extend.py; s04b_nonpubmed_counts.py sizes the paid remainder;
  s04c_pmid_list_batches.py fetches part of the PubMed route with 1-credit batched lists.
  (in this run the paid steps ran first and the free singleton fetch ran concurrently, because the shared key was draining)

usage: .venv/bin/python build_population.py [--from-step N] [--skip-download] [--download-only] [--concept-min-score 0.3]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
PY = sys.executable
MESH = "https://nlmpubs.nlm.nih.gov/projects/mesh"
(ROOT / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "data_py.log", rotation="30 MB", level="DEBUG")


def downloads() -> list[tuple[str, str]]:
    out = [(f"{MESH}/2017/xmlmesh/desc2017.gz", "desc2017.xml.gz"),
           (f"{MESH}/2019/xmlmesh/desc2019.gz", "desc2019.xml.gz"),
           (f"{MESH}/MESH_FILES/xmlmesh/desc2026.gz", "desc2026.xml.gz")]
    for y in range(2003, 2019):
        folder = "1999-2010" if y <= 2010 else str(y)
        out.append((f"{MESH}/{folder}/asciimesh/d{y}.bin", f"d{y}.bin"))
        out.append((f"{MESH}/{folder}/newterms/replace{y}.txt", f"replace{y}.txt"))
    return out


def run(args: list[str], env: dict | None = None) -> None:
    import os
    t = time.time()
    logger.info(f"RUN {env or ''} {' '.join(args)}")
    subprocess.run([PY, *args], cwd=ROOT, check=True, env={**os.environ, **(env or {})})
    logger.info(f"DONE {args[0]} in {time.time() - t:.0f}s")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-step", type=int, default=0)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--concept-min-score", default="0.3")
    ap.add_argument("--download-only", action="store_true", help="only (re)download the MeSH files into raw/")
    a = ap.parse_args()
    raw = ROOT / "raw"
    raw.mkdir(exist_ok=True)
    if (a.from_step <= 0 or a.download_only) and not a.skip_download:
        import requests
        for url, name in downloads():
            p = raw / name
            if not p.exists():
                logger.info(f"download {url}")
                r = requests.get(url, timeout=600)
                r.raise_for_status()
                p.write_bytes(r.content)
    if a.download_only:
        return
    w1 = {"AII_TAG": "w1", "AII_YEARS": "2004,2005", "AII_SNAPSHOT": "desc2017.xml.gz"}
    w2 = {"AII_TAG": "w2", "AII_YEARS": "2017,2018", "AII_SNAPSHOT": "desc2019.xml.gz"}
    steps: list[tuple[list[str], dict]] = [
        (["scripts/s01_mesh_candidates.py"], {}),
        (["scripts/s02_pubmed_prescreen.py"], {}),
        (["scripts/s03_sample_and_indexed.py"], {}),
        (["scripts/s01_mesh_candidates.py"], w1),            # widening (plan failure scenario)
        (["scripts/s01_mesh_candidates.py"], w2),
        (["scripts/s02_pubmed_prescreen.py"], {"AII_TAG": "w1"}),
        (["scripts/s02_pubmed_prescreen.py"], {"AII_TAG": "w2"}),
        (["scripts/s03b_extend.py"], {}),
        (["scripts/s06_calibrate.py", "fetch"], {}),
        (["scripts/s04b_nonpubmed_counts.py"], {}),
        (["scripts/s04_retrieve.py", "remainder"], {}),
        (["scripts/s04c_pmid_list_batches.py", "700"], {}),
        (["scripts/s04_retrieve.py", "pubmed"], {"AII_SINGLETON_RPS": "18"}),
        (["scripts/s05_finalize.py", "final", a.concept_min_score], {}),
        (["scripts/s06_calibrate.py", "compare"], {}),
        (["scripts/s09_sanity.py"], {}),
        (["scripts/s07_docs.py"], {}),
        (["scripts/s10_export_datasets.py"], {}),   # prepared inputs for data.py in temp/datasets/
        (["data.py"], {}),                           # -> full_data_out.json (exp_sel_data_out)
    ]
    for i, (s, env) in enumerate(steps, 1):
        if i >= a.from_step:
            run(s, env)


if __name__ == "__main__":
    main()
