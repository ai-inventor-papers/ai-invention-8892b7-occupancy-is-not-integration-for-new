"""Shared paths, logging, hashing and the OpenAlex client (with a credit ledger) for the G4 MeSH replication.

The exp_7 (iteration-3 D2 screen) modules are vendored UNCHANGED under vendor/ (SHA256SUMS there). They are imported
as top-level modules (config, ppml, models, features, outcomes, events, placebo, power, io_load); vendor/config.py
resolves its own dependency paths relative to this workspace (<loop>/iter_4/gen_art/<artifact> -> <loop>).
Every dependency path can be overridden with an env variable (AII_MESH_DIR, AII_DATASET5_DIR, AII_DATASET1_DIR,
AII_EXP7_DIR, AII_EXP3_DIR, AII_BG_DIR, AII_DEPS_ROOT).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
import threading
import time
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "vendor"))

LOOP = Path(os.environ.get("AII_DEPS_ROOT", WS.parents[2])).resolve()
MESH = Path(os.environ.get("AII_MESH_DIR", LOOP / "round-1" / "." / "dataset-3/src"))   # art_HGiVAYhqO-6q
D5 = Path(os.environ.get("AII_DATASET5_DIR", LOOP / "round-2" / "." / "dataset-5/src"))  # art_eR1Z7fMlOcxs
D1 = Path(os.environ.get("AII_DATASET1_DIR", LOOP / "round-1" / "." / "dataset-1/src"))  # art_94GEMUsgAmgK
E7 = Path(os.environ.get("AII_EXP7_DIR", LOOP / "round-3" / "." / "experiment-7/src"))   # D2 screen
E3 = Path(os.environ.get("AII_EXP3_DIR", LOOP / "round-2" / "." / "experiment-3/src"))   # rs_distance
BG = Path(os.environ.get("AII_BG_DIR", LOOP / "round-1" / "." / "gen_art_dataset_2" / "data"))

RESULTS = WS / "results"
GATE = RESULTS / "gate"
MRES = RESULTS               # MeSH outputs live at results/ top level
CACHE = WS / "cache"         # regenerable pickles / API response cache (not published)
FIGS = WS / "figures"
LOGS = WS / "logs"
for _d in (RESULTS, GATE, CACHE, FIGS, LOGS, RESULTS / "substrate"):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 20260929
BLOCKS = ["2000-2004", "2005-2009", "2010-2014", "2015-2019"]

# iteration-3 targets (exp_7 results/d2_models.json, d2_robustness.csv)
MAIN_COPRIMARY = {"b_A": 4.739105939721475, "se_A": 1.0102888770711833, "irr_sd": 1.300076888024346,
                  "ci": [1.1639421314281162, 1.452133975682496], "N": 1544, "G": 140}
MAIN_PRIMARY = {"b_A": 5.952633617485952, "irr_sd": 1.385942489788976, "N": 452, "G": 77}
MAIN_NONPHYS = {"b_A": 4.686456999087919, "se_A": 1.354122141289332, "irr_sd": 1.290186634471277,
                "ci": [1.112923630330427, 1.495683536950425], "N": 692, "G": 52,
                "source": "exp_7 results/d2_robustness.csv 'stratum other (descriptive)', secondary FE"}
MAIN_PHYS = {"irr_sd": 0.9516637634583498, "ci": [0.7743171600115374, 1.272165287569658], "N": 248, "G": 50,
             "source": "exp_7 results/d2_robustness.csv 'stratum Physics/Astro (descriptive)', secondary FE"}


def setup_logging(name: str) -> None:
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{module}:{line}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def set_ram_limit(gb: float) -> None:
    b = int(gb * 1024 ** 3)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if hard != resource.RLIM_INFINITY:
        b = min(b, hard)
    resource.setrlimit(resource.RLIMIT_AS, (b, b if hard == resource.RLIM_INFINITY else hard))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def dump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=_default))


def _default(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(LOOP.parent))
    except ValueError:
        return str(p)


# ----------------------------------------------------------------------------------------------------------- OpenAlex
class CreditStop(Exception):
    pass


class OpenAlex:
    """Thread-safe OpenAlex client: <= rps requests/s, tenacity-style retry on 429/5xx, credit ledger per call.

    The API key is read from env OPENALEX_API_KEY and never written to disk (URLs in the ledger omit it).
    """

    BASE = "https://api.openalex.org"

    def __init__(self, purpose: str, rps: float = 4.0, guard_remaining: int = 150):
        import requests
        self.key = os.environ.get("OPENALEX_API_KEY", "")
        self.purpose = purpose
        self.rps = rps
        self.guard = guard_remaining
        self.sess = requests.Session()
        self.lock = threading.Lock()
        self.last = 0.0
        self.calls = 0
        self.credits = 0
        self.remaining: int | None = None
        self.ledger = LOGS / "openalex_credit_ledger.jsonl"
        self.mail = os.environ.get("AII_POLITE_CONTACT", "")

    def available(self) -> bool:
        return bool(self.key)

    def _throttle(self) -> None:
        with self.lock:
            now = time.time()
            wait = self.last + 1.0 / self.rps - now
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()

    def rate_limit(self) -> dict:
        r = self.sess.get(f"{self.BASE}/rate-limit", params={"api_key": self.key}, timeout=30)
        r.raise_for_status()
        return r.json().get("rate_limit", {})

    def get(self, path: str, params: dict, tag: str = "") -> dict:
        if not self.key:
            raise CreditStop("no OPENALEX_API_KEY")
        if self.remaining is not None and self.remaining <= self.guard:
            raise CreditStop(f"remaining {self.remaining} <= guard {self.guard}")
        q = dict(params)
        q["api_key"] = self.key
        if self.mail:
            q["mailto"] = self.mail
        last_err = None
        for attempt in range(6):
            self._throttle()
            try:
                r = self.sess.get(f"{self.BASE}{path}", params=q, timeout=60)
            except Exception as ex:  # noqa: BLE001 - network error: retry with backoff
                last_err = repr(ex)
                time.sleep(min(30, 2 ** attempt))
                continue
            cred = int(r.headers.get("x-ratelimit-credits-used", 0) or 0)
            rem = r.headers.get("x-ratelimit-remaining")
            with self.lock:
                self.calls += 1
                self.credits += cred
                if rem is not None:
                    self.remaining = int(rem)
                with open(self.ledger, "a") as f:
                    f.write(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                        "purpose": self.purpose, "tag": tag, "path": path,
                                        "filter": params.get("filter", "")[:300], "http": r.status_code,
                                        "credits": cred, "remaining": self.remaining}) + "\n")
            if r.status_code == 200:
                return r.json()
            body = r.text[:300]
            if r.status_code == 429 and ("credit" in body.lower() or "budget" in body.lower()
                                         or (self.remaining is not None and self.remaining <= 0)):
                raise CreditStop(f"credits exhausted: {body}")
            if r.status_code in (429, 500, 502, 503, 504):
                last_err = f"{r.status_code} {body}"
                time.sleep(min(30, 2 ** attempt))
                continue
            raise RuntimeError(f"OpenAlex {r.status_code}: {body}")
        raise RuntimeError(f"OpenAlex retries exhausted: {last_err}")
