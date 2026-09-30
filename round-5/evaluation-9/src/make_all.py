#!/usr/bin/env python3
"""Regenerates every figure, table and sidecar from the source registry (sources.yaml)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
from src import build_sources  # noqa: E402
from src.registry import Registry  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(WS / "logs").mkdir(exist_ok=True)
logger.add(WS / "logs" / "make_all.log", rotation="30 MB", level="DEBUG")

FIGS = ["f2_d2_forest", "f3_mechanism", "f4_rq1", "f5_rooting", "f6_cases", "f1_method", "f7_k_template",
        "caveats"]


@logger.catch(reraise=True)
def main(only: list[str] | None = None) -> None:
    build_sources.main()
    reg = Registry()
    audits = {}
    for name in FIGS:
        if only and name not in only:
            continue
        mod = __import__(f"src.plots.{name}", fromlist=["build"])
        logger.info(f"building {name}")
        audits[name] = mod.build(reg, WS / ("tables" if name == "caveats" else "figures"))
        logger.info(f"{name}: {json.dumps(audits[name], default=str)[:300]}")
    (WS / "results").mkdir(exist_ok=True)
    (WS / "results" / "source_hashes.json").write_text(json.dumps(
        {a: {"sha256": h, "path": reg.files[a]["path"], "artifact": reg.files[a]["artifact"]}
         for a, h in sorted(reg.hashes.items())}, indent=1))
    (WS / "results" / "registry_missing.json").write_text(json.dumps(reg.missing, indent=1))
    logger.info(f"done; {len(reg.missing)} missing registry reads")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
