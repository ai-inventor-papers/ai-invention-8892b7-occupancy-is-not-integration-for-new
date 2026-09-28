"""Shared paths, guards, logging, hardware limits and dataset loaders for the concept-cleaning experiment."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import resource
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

MINI = os.environ.get("AII_MINI", "0") == "1"  # T2 mini pipeline switch: all derived outputs go to mini_run/
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DATA = ROOT / "data"
CACHE = ROOT / "cache"  # inputs and paid/rate-limited API caches (shared by full and mini runs)
WORK = (ROOT / "mini_run" / "work") if MINI else CACHE  # derived features: termhood, lexical, embeddings
MODELS = (ROOT / "mini_run" / "models") if MINI else ROOT / "models"
RESULTS = (ROOT / "mini_run" / "results") if MINI else ROOT / "results"
LOGS = ROOT / "logs"
for _d in (DATA, CACHE, WORK, MODELS, RESULTS, LOGS, CACHE / "llm", CACHE / "wikidata", WORK / "emb"):
    _d.mkdir(parents=True, exist_ok=True)

# dependency workspaces (read-only): <run>/3_invention_loop/iter_1/gen_art/gen_art_dataset_{1,3,4}; override with AII_DEPS_ROOT
ITER1 = Path(os.environ.get("AII_DEPS_ROOT", str(ROOT.parents[2] / "round-1" / ".")))
# one env var per input artifact (a published repository has them as sibling folders):
#   AII_DS1 = art_94GEMUsgAmgK (concept pool / frozen frame), AII_DS3 = art_HGiVAYhqO-6q (MeSH pairs),
#   AII_DS4 = art_QpM5SM6a7SH6 (labelled phrases, anchors, vocabularies)
DS1 = Path(os.environ.get("AII_DS1", str(ITER1 / "gen_art_dataset_1")))
DS3 = Path(os.environ.get("AII_DS3", str(ITER1 / "gen_art_dataset_3")))
DS4 = Path(os.environ.get("AII_DS4", str(ITER1 / "gen_art_dataset_4")))
FRAME_SHA = "80e3f244235b120be3e1201fdd8fb275ace4ba549f9a8884b96d2ea51c9a0c44"
SEED = 20261001
N_BOOT = 2000

sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "vendor"))
from textnorm import normalise, plural_to_singular, schwartz_hearst, _best_long_form  # noqa: E402,F401


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def open_guard(path: str | Path) -> Path:
    """Every data file open goes through here; the sealed outcome file must never be read."""
    p = Path(path)
    if "SEALED" in str(p):
        raise PermissionError(f"refusing to open sealed outcome file: {p}")
    return p


def read_json(path: str | Path):
    p = open_guard(path)
    if str(p).endswith(".gz"):
        with gzip.open(p, "rt") as f:
            return json.load(f)
    return json.loads(p.read_text())


def write_json(path: str | Path, obj, indent: int | None = 1) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=indent, ensure_ascii=False, default=_json_default))


def _json_default(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(type(o))


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(open_guard(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_limits(ram_gb: float = 40.0) -> None:
    """Hard RAM cap (container limit is 57 GB): raise MemoryError instead of an OOM kill."""
    b = int(ram_gb * 1024 ** 3)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (b * 3, b * 3))
    except (ValueError, OSError) as e:
        logger.warning(f"could not set RLIMIT_AS: {e}")


def detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return max(1, math.ceil(q / p))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


# ------------------------------------------------------------------ text helpers
TOK_RE = re.compile(r"[a-z0-9][a-z0-9+.']*[a-z0-9+]|[a-z0-9]")


def match_form(s: str) -> str:
    """Matching key: textnorm.normalise, then the same regex tokeniser as the corpus stream, every token singularised.
    Applied identically to phrases and to corpus text so plural/hyphen variants meet."""
    n = normalise(s)
    return " ".join(plural_to_singular(t) for t in TOK_RE.findall(n))


def stream_tokens(text: str) -> list[str]:
    """Corpus token stream (same pipeline as match_form but without the head-only singularisation step)."""
    n = normalise(text)
    return [plural_to_singular(t) for t in TOK_RE.findall(n)]


SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")


# ------------------------------------------------------------------ loaders
def load_ds4() -> dict[str, list[dict]]:
    import glob
    ds: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(glob.glob(str(DS4 / "full_data_out" / "full_data_out_*.json"))):
        for g in read_json(f)["datasets"]:
            ds[g["dataset"]].extend(g["examples"])
    return dict(ds)


def load_ds4_subset(names: list[str]) -> dict[str, list[dict]]:
    """Load only the named DS4 datasets (the corpus D1 is ~250 MB; free the rest as we go)."""
    import gc
    import glob
    ds: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(glob.glob(str(DS4 / "full_data_out" / "full_data_out_*.json"))):
        d = read_json(f)
        for g in d["datasets"]:
            if g["dataset"] in names:
                ds[g["dataset"]].extend(g["examples"])
        del d
        gc.collect()
    return dict(ds)


def load_ds3() -> dict[str, list[dict]]:
    d = read_json(DS3 / "full_data_out.json")
    return {g["dataset"]: g["examples"] for g in d["datasets"]}


def load_frame() -> dict:
    """Verify the frozen frame hash, then return {concept_id: record} for main + reference arms."""
    got = sha256_file(DATA / "sample_frame_frozen.json")
    want = (DATA / "sample_frame_frozen.sha256").read_text().split()[0]
    orig = sha256_file(DS1 / "sample_frame_frozen.json")
    assert got == want == orig == FRAME_SHA, f"frame sha mismatch {got} {want} {orig}"
    fr = read_json(DATA / "sample_frame_frozen.json")
    out = {}
    for c in fr["eligible"]:
        out[c["concept_id"]] = {**c, "arm": c.get("arm", "main")}
    for c in fr["reference"]:
        out[c["concept_id"]] = {**c, "arm": "reference"}
    return out


def load_hydrated() -> dict[str, dict]:
    d = read_json(DATA / "data_out.json")
    rows = {}
    for e in d["datasets"][0]["examples"]:
        inp = json.loads(e["input"])
        rows[e["metadata_concept_id"]] = {"input": inp, "meta": {k: v for k, v in e.items() if k.startswith("metadata_")}}
    return rows


def f_band(F: int) -> str:
    return "2005-07" if F <= 2007 else ("2008-11" if F <= 2011 else "2012-16")
