"""Shared paths, config, logging and small helpers."""
from __future__ import annotations

import hashlib
import math
import os
import sys
from pathlib import Path

import yaml
from loguru import logger

WS = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((WS / "config.yaml").read_text())
RUN = Path(os.environ.get("AII_RUN_DIR", WS.parents[3]))
DS1 = Path(os.environ["AII_DS1_DIR"]) if os.environ.get("AII_DS1_DIR") else RUN / CFG["ds1"]
RESEARCH1 = RUN / CFG["research1"]
STRAT1 = RUN / CFG["strat1"]
SEED = int(CFG["seed"])
B = int(CFG["B"])
RESULTS = WS / "results"
FIGS = WS / "figures"
LOGS = WS / "logs"


def setup_logging(name: str) -> None:
    LOGS.mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
    logger.add(LOGS / f"{name}.log", rotation="30 MB", level="DEBUG")


def h32(s: str) -> int:
    """Stable 32-bit hash of a string (for per-task seeds, independent of scheduling)."""
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


def detect_cpus() -> int:
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
    except (FileNotFoundError, ValueError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def set_ram_limit(gb: float) -> None:
    import resource
    b = int(gb * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def f_band(F: int) -> str:
    return "2005-07" if F <= 2007 else ("2008-11" if F <= 2011 else "2012-16")
