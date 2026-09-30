"""Step 0b: rebuild the regenerable caches (no network).

main: d2/results/cache/prepared.pkl via vendored io_load.prepare() (dataset_5)
mesh: mesh/cache/mesh_prepared.pkl via vendored load_mesh.prepare() (dataset_3 works + dataset_5 context),
      mesh/cache/bg_shares.pkl via nativeness.bg_shares (dataset_2 bg_work_sample; admitted fallback in exp_9)
"""
from __future__ import annotations

import os
import pickle
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
os.environ.setdefault("AII_DEPS_ROOT", str(WS.parents[2]))
os.environ.pop("OPENALEX_API_KEY", None)
from loguru import logger  # noqa: E402

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WS / "logs" / "k2_prepare.log", rotation="30 MB", level="DEBUG")


@logger.catch(reraise=True)
def main(which: str) -> None:
    t0 = time.time()
    if which in ("main", "all"):
        sys.path.insert(0, str(WS / "d2" / "src"))
        import io_load
        G = io_load.prepare()
        logger.info(f"main prepared: {len(G['links'])} concepts, {len(G['prof'])} profiles, {time.time() - t0:.0f}s")
        del G
    if which in ("mesh", "all"):
        sys.path.insert(0, str(WS / "mesh" / "src"))
        import load_mesh
        import nativeness
        G = load_mesh.prepare()
        logger.info(f"mesh prepared: {len(G['links'])} concepts ({time.time() - t0:.0f}s)")
        exact = nativeness.all_profiles()
        nodes = {k[0] for k in exact}
        import pandas as pd
        nodes |= set(pd.read_csv(nativeness.NAT / "needed_pairs.csv").node.astype(int))
        bg = nativeness.bg_shares(nodes)
        (WS / "mesh" / "cache" / "bg_shares.pkl").write_bytes(pickle.dumps(bg, protocol=5))
        logger.info(f"bg shares: {len(bg)} (node, block) ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
