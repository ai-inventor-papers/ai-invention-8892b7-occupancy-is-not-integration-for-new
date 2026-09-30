#!/usr/bin/env python3
"""S0: download raw files of the external human-labelled resources from HF into temp/datasets/."""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
from loguru import logger
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "temp" / "datasets"
JOBS = {
    "midas/semeval2017": ["train.jsonl", "valid.jsonl", "test.jsonl", "README.md"],
    "zj88zj/SCIERC": ["train.json", "dev.json", "test.json"],
    "amirveyseh/acronym_identification": ["data/train-00000-of-00001.parquet", "data/validation-00000-of-00001.parquet", "data/test-00000-of-00001.parquet", "README.md"],
    "midas/inspec": ["train.jsonl", "valid.jsonl", "test.jsonl", "README.md"],
    "midas/semeval2010": ["train.jsonl", "test.jsonl", "README.md"],
    "midas/nus": ["test.jsonl", "README.md"],
    "midas/krapivin": ["test.jsonl", "README.md"],
    "taln-ls2n/kp20k": ["test.json", "README.md"],
    "batterydata/abbreviation_detection": ["train.json", "test.json", "README.md"],
}
def dl(repo, fn):
    try:
        p = hf_hub_download(repo, fn, repo_type="dataset", local_dir=OUT / repo.replace("/", "__"))
        return repo, fn, Path(p).stat().st_size
    except Exception as e:
        logger.error(f"{repo}/{fn}: {e!r}")
        return repo, fn, None
with ThreadPoolExecutor(12) as ex:
    for r in ex.map(lambda a: dl(*a), [(r, f) for r, fs in JOBS.items() for f in fs]):
        print(r)
