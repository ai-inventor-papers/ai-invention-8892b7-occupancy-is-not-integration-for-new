"""Linking targets (OpenAlex keywords, legacy concepts, MeSH), stage-1 exact rules (DS4 linking.Linker logic incl.
_mesh_variants) and GPU nearest-neighbour search for stage-2 embedding links."""
from __future__ import annotations

import sys
from collections import defaultdict

import numpy as np
import torch

from common import DS4, SRC, normalise, read_json, match_form
from featlib import EmbStore, emb_text

sys.path.insert(0, str(SRC / "vendor"))
from linking import _mesh_variants  # noqa: E402  (DS4 code, reused unchanged)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Targets:
    """Unique target strings (emb_text form) -> list of target records."""

    def __init__(self, mesh_only: bool = False, exclude_ui: set | None = None) -> None:
        V = DS4 / "data_out" / "vocab"
        self.recs: dict[str, list[dict]] = defaultdict(list)
        # stage-1 exact dictionaries, keyed by normalise(display) exactly as DS4 linking.Linker does (setdefault)
        self.kw: dict[str, dict] = {}
        self.co: dict[str, dict] = {}
        self.mesh: dict[str, dict] = {}
        self.mesh_desc: dict[str, dict] = {}
        if not mesh_only:
            for r in read_json(V / "openalex_keywords_snapshot_2026-09-23.json.gz"):
                s = emb_text(r["display_name"] or "")
                if s:
                    rec = {"vocab": "openalex_keyword", "id": r["id"], "label": r["display_name"], "works_count": r.get("works_count")}
                    self.recs[s].append(rec)
                    self.kw.setdefault(normalise(r["display_name"] or ""), rec)
            for r in read_json(V / "openalex_legacy_concepts_snapshot_2026-09-23.json.gz"):
                s = emb_text(r["display_name"] or "")
                if s:
                    rec = {"vocab": "openalex_legacy_concept", "id": r["id"], "label": r["display_name"], "level": r.get("level"),
                           "wikidata": r.get("wikidata"), "works_count": r.get("works_count")}
                    self.recs[s].append(rec)
                    self.co.setdefault(normalise(r["display_name"] or ""), rec)
        for r in read_json(V / "mesh_descriptors_2026.json.gz"):
            if exclude_ui and r["ui"] in exclude_ui:
                continue
            self.mesh_desc[r["ui"]] = r
            for t in [r["heading"]] + r["entry_terms"]:
                for v in _mesh_variants(t):
                    s = emb_text(v)
                    if s:
                        rec = {"vocab": "mesh", "id": r["ui"], "label": r["heading"], "matched": v}
                        self.recs[s].append(rec)
                        self.mesh.setdefault(normalise(v), rec)
        for d in (self.kw, self.co, self.mesh):
            d.pop("", None)
        self.strings = sorted(self.recs)
        self.sidx = {s: i for i, s in enumerate(self.strings)}

    def exact(self, forms: list[str], removed: set | None = None) -> list[dict]:
        """Stage 1: normalised-string equality against each vocabulary (DS4 Linker.link logic)."""
        out = []
        seen = set()
        for f in forms:
            k = normalise(f)
            for d in (self.kw, self.co, self.mesh):
                r = d.get(k)
                if r is None:
                    continue
                if removed and emb_text(r.get("matched") or r["label"]) in removed:
                    continue
                key = (r["vocab"], r["id"])
                if key not in seen:
                    seen.add(key)
                    out.append({**r, "link_type": "exact", "method": "stage1_normalised_string", "score": 1.0, "query_form": f})
        return out


class NN:
    """Blocked cosine top-k on GPU over the target strings for one encoder."""

    def __init__(self, store: EmbStore, strings: list[str]) -> None:
        self.strings = strings
        M = store.get(strings) if len(strings) < 50000 else np.asarray(store.mat[[store.idx[s] for s in strings]], dtype=np.float32)
        self.M = torch.tensor(M, dtype=torch.float16, device=DEVICE)

    def topk(self, Q: np.ndarray, k: int = 50, block: int = 2048) -> tuple[np.ndarray, np.ndarray]:
        sims, idxs = [], []
        for i in range(0, len(Q), block):
            q = torch.tensor(Q[i:i + block], dtype=torch.float16, device=DEVICE)
            s = q @ self.M.T
            v, ix = torch.topk(s.float(), k=min(k, s.shape[1]), dim=1)
            sims.append(v.cpu().numpy())
            idxs.append(ix.cpu().numpy())
        return np.concatenate(sims), np.concatenate(idxs)


def is_broader(query: str, target: str) -> bool:
    """Target tokens a strict subset of the query tokens with the same head noun (a parent link, NOT identity)."""
    q, t = match_form(query).split(), match_form(target).split()
    return bool(q) and bool(t) and set(t) < set(q) and q[-1] == t[-1]
