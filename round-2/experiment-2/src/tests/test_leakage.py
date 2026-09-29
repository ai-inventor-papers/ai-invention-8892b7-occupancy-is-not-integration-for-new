"""Leakage tests: (i) mutation test with injected post-t papers; (ii) static check that only origin.py reads years > t."""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
import io_load  # noqa: E402
from edges import focal_years, main_concept  # noqa: E402


def _inject(cdata: dict, t: int, rng: np.random.Generator, n: int = 50) -> dict:
    p = cdata["papers"]
    subs = p["sub"].unique()
    new = pd.DataFrame({"work_id": 10**12 + np.arange(n), "year": rng.integers(t + 1, t + 6, n).astype(np.int32),
                        "sub": rng.choice(subs, n).astype(np.int32), "field": 0, "n_refs": 5, "cbc": 0, "n_kw": 3,
                        "lenient_excl_F": True})
    p2 = pd.concat([p, new], ignore_index=True)
    k = len(p)
    ch = np.arange(k, k + n)
    pa = rng.integers(0, k, n)
    cites = np.concatenate([cdata["cites"], np.stack([ch, pa], 1).astype(np.int32)])
    return {"papers": p2, "cites": cites}


def test_mutation_byte_identical():
    G = dict(io_load.prepare())
    G["totals"] = io_load.load_totals()
    con = G["concepts"]
    main = con[con.arm == "main"].concept_id.tolist()[:5]
    rng = np.random.default_rng(7)
    for cid in main:
        base = main_concept(cid, boot=True, B=200, rho0={"main": {}}, canon_w1=True, data=G)
        F = int(con.set_index("concept_id").F[cid])
        for t in focal_years(F):
            G2 = dict(G)
            G2["per"] = dict(G["per"])
            G2["per"][cid] = _inject(G["per"][cid], t, rng)
            # the canonical set is precomputed from the ORIGINAL table (declared post-t input); injected papers cbc = 0
            mut = main_concept(cid, boot=True, B=200, rho0={"main": {}}, canon_w1=True, data=G2)
            a = pd.DataFrame([r for r in base["rows"] if r["t"] == t]).to_json()
            b = pd.DataFrame([r for r in mut["rows"] if r["t"] == t]).to_json()
            assert a == b, f"leakage for {cid} t={t}"


def _code_lines(txt: str) -> dict[int, str]:
    """Source lines with strings and comments removed (docstrings may describe the rule)."""
    import io
    import tokenize
    out: dict[int, list[str]] = {}
    for tok in tokenize.generate_tokens(io.StringIO(txt).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            continue
        out.setdefault(tok.start[0], []).append(tok.string)
    return {k: " ".join(v) for k, v in out.items()}


def test_static_no_future_reads():
    pat = re.compile(r"t\s*\+\s*[1-9]|\bW2\b|year\s*>\s*t\b")
    for f in SRC.glob("*.py"):
        if f.name in {"origin.py", "prereg.py", "power_h2.py", "synth.py", "method.py", "assemble_out.py"}:
            continue  # origin.py is the declared reader; prereg is text; power_h2 uses origin onsets only; synth is simulated
        for i, code in _code_lines(f.read_text()).items():
            code = re.sub(r"\s+", " ", code)
            if pat.search(code) and "range ( F + 3 , F + 9 )" not in code and "t + 1 )" not in code:
                raise AssertionError(f"{f.name}:{i}: {code}")
