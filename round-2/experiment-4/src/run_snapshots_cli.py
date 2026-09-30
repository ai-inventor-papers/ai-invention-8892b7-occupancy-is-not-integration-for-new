"""CLI for STEP 1-2 alone: `uv run run_snapshots_cli.py [--mini]` (also called by method.py --stage snapshots)."""

import argparse
import json
import resource
import sys

import pandas as pd
from loguru import logger

import load
import rq1_spec as S
import snapshots

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(load.ROOT / "logs" / "snapshots.log"), rotation="30 MB", level="DEBUG")


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mini", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (26 * 1024**3, 26 * 1024**3))
    info = snapshots.prepare(a.mini)
    (load.RESULTS / "load_checks.json").write_text(json.dumps(info, indent=1))
    c = pd.read_parquet(load.INTER / "concepts.parquet")
    if a.mini:
        early = c.sort_values(["F", "concept_id"]).concept_id.head(5).tolist()
        rest = c[~c.concept_id.isin(early)].sample(5, random_state=S.SEED).concept_id.tolist()
        ids, years = early + rest, list(range(2008, 2013))
    else:
        ids, years = c.concept_id.tolist(), S.YEARS
    (load.RESULTS / "snapshot_scope.json").write_text(json.dumps({"mini": a.mini, "concepts": ids, "years": years}))
    snapshots.run_snapshots(ids, years, a.workers)


if __name__ == "__main__":
    main()
