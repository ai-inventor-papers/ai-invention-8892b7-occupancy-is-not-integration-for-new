"""Time the frozen leiden_single on one MeSH snapshot (decides whether the 5-seed MeSH rerun fits the 30-min budget)."""
import os, sys, time, types
from pathlib import Path
import numpy as np, pandas as pd
WS = Path(__file__).resolve().parents[1]
os.environ.setdefault("AII_LOOP_ROOT", str(WS.parents[2]))
sys.path.insert(0, str(WS / "exp8_frozen/src")); sys.path.insert(0, str(WS / "exp8_frozen/vendor"))
from leiden_seeds import leiden_single
E4 = Path(os.environ["AII_LOOP_ROOT"]) / "round-2/experiment-4/src/results/snapshots"
y = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
e = pd.read_parquet(E4 / f"edges_{y}.parquet")
nodes = np.unique(np.concatenate([e.i.values, e.j.values]))
idx = {n: k for k, n in enumerate(nodes)}
g = types.SimpleNamespace(ei=np.searchsorted(nodes, e.i.values), ej=np.searchsorted(nodes, e.j.values), AS=e.AS.values.astype(float),
                          kept=np.ones(len(e), bool), nodes=nodes)
t0 = time.time(); m = leiden_single(g, 101); print(y, len(nodes), len(e), "secs", round(time.time() - t0, 1), "n_comm", len(set(m)))
