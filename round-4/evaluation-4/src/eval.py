#!/usr/bin/env python3
"""Evaluation of the frozen RQ2 descriptive layer (held-out confirmation, MeSH second population, type x rooting,
lead-lag denominators, cases, figures) -> eval_out.json (exp_eval_sol_out).

Usage: python eval.py <step> [<step> ...]   steps: typology rooting mesh leadlag cases figures assemble all
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS / "evalsteps"))
(WS / "logs").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs/eval.log"), rotation="30 MB", level="DEBUG")

STEPS = ["typology", "rooting", "mesh", "leadlag", "confirmation", "cases", "figures", "assemble"]


@logger.catch(reraise=True)
def main() -> None:
    import importlib
    todo = sys.argv[1:] or ["all"]
    if todo == ["all"]:
        todo = STEPS
    mod = {"typology": "typology_extras", "rooting": "rooting", "mesh": "mesh", "leadlag": "leadlag_table",
           "confirmation": "confirmation", "cases": "cases_rooting", "figures": "make_figures", "assemble": "assemble"}
    for st in todo:
        t0 = time.time()
        logger.info(f"=== step {st}")
        importlib.import_module(mod[st]).run()
        logger.info(f"=== step {st} done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
