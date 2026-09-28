"""Size-safe storage of the large intermediates in raw/ (every file < 100 MB for GitHub).

- corpus works: raw/corpus_works/corpus_works_part_001.jsonl, ... (split, <= 80 MB each)
- pickles: gzip-compressed (raw/candidates.pkl.gz, raw/docs_meta.pkl.gz, raw/key_stats.pkl.gz)
"""
from __future__ import annotations

import gzip
import json
import pickle
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "raw" / "corpus_works"
PART_BYTES = 80_000_000


def write_corpus_works(rows: Iterator[dict]) -> int:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    for f in CORPUS_DIR.glob("corpus_works_part_*.jsonl"):
        f.unlink()
    n, part, size, fo = 0, 0, PART_BYTES, None
    for r in rows:
        line = (json.dumps(r, ensure_ascii=False) + "\n").encode()
        if size + len(line) > PART_BYTES:
            if fo:
                fo.close()
            part += 1
            fo = (CORPUS_DIR / f"corpus_works_part_{part:03d}.jsonl").open("wb")
            size = 0
        fo.write(line)
        size += len(line)
        n += 1
    if fo:
        fo.close()
    return n


def read_corpus_works() -> Iterator[dict]:
    parts = sorted(CORPUS_DIR.glob("corpus_works_part_*.jsonl"))
    if not parts:
        raise FileNotFoundError(f"no corpus parts in {CORPUS_DIR}; run scripts/s1_fetch_corpus.py")
    for p in parts:
        with p.open() as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def dump_pickle(obj, name: str) -> Path:
    p = ROOT / "raw" / f"{name}.pkl.gz"
    with gzip.open(p, "wb", compresslevel=6) as f:
        pickle.dump(obj, f, protocol=5)
    return p


def load_pickle(name: str):
    p = ROOT / "raw" / f"{name}.pkl.gz"
    with gzip.open(p, "rb") as f:
        return pickle.load(f)
