"""Core co-word graph construction shared by the snapshot, robustness and substrate-check stages."""
from __future__ import annotations

from dataclasses import dataclass

import igraph as ig
import leidenalg
import numpy as np
import scipy.sparse as sp


@dataclass
class CoGraph:
    nodes: np.ndarray            # concept ids (int64), index = node position
    W: np.ndarray                # weighted occurrence W_i
    s: np.ndarray                # strength (sum of weighted co-occurrence, all edges)
    Wtot: float                  # sum of weights of works with >= 1 tag
    Cw: sp.csr_matrix            # weighted co-occurrence (symmetric, zero diagonal)
    ei: np.ndarray               # upper-triangle edge endpoints
    ej: np.ndarray
    c: np.ndarray                # weighted co-occurrence per edge
    raw: np.ndarray              # raw sample co-occurrence per edge
    AS: np.ndarray               # association strength per edge
    kept: np.ndarray             # bool: raw >= kept_min
    n_works: int

    def index_of(self) -> dict:
        return {int(v): i for i, v in enumerate(self.nodes)}


def build_cograph(tag_lists: list[np.ndarray], weights: np.ndarray, kept_min_raw: int = 2) -> CoGraph:
    """Weighted co-occurrence graph from per-work tag arrays and per-work weights."""
    keep = np.array([len(t) > 0 for t in tag_lists])
    tags = [t for t, k in zip(tag_lists, keep) if k]
    w = np.asarray(weights, dtype=float)[keep]
    lens = np.array([len(t) for t in tags])
    flat = np.concatenate(tags) if tags else np.zeros(0, dtype=np.int64)
    nodes, col = np.unique(flat, return_inverse=True)
    row = np.repeat(np.arange(len(tags)), lens)
    X = sp.csr_matrix((np.ones(len(flat)), (row, col)), shape=(len(tags), len(nodes)))
    Xw = sp.csr_matrix((w[row], (row, col)), shape=(len(tags), len(nodes)))
    Cw = (X.T @ Xw).tocsr()
    Craw = (X.T @ X).tocsr()
    W = Cw.diagonal().copy()
    Cw.setdiag(0)
    Cw.eliminate_zeros()
    Craw.setdiag(0)
    Craw.eliminate_zeros()
    s = np.asarray(Cw.sum(axis=1)).ravel()
    U = sp.triu(Cw, k=1).tocoo()
    R = sp.triu(Craw, k=1).tocsr()
    raw = np.asarray(R[U.row, U.col]).ravel()
    Wtot = float(w.sum())
    AS = U.data * Wtot / (W[U.row] * W[U.col])
    return CoGraph(nodes=nodes, W=W, s=s, Wtot=Wtot, Cw=Cw, ei=U.row.astype(np.int32), ej=U.col.astype(np.int32),
                   c=U.data, raw=raw, AS=AS, kept=raw >= kept_min_raw, n_works=len(tags))


def leiden_best(g: CoGraph, resolution: float = 1.0, seed: int = 42, n_runs: int = 5) -> tuple[np.ndarray, float, int]:
    """Leiden (RBConfiguration, AS weights) on the kept graph; best quality of n_runs seeds.

    Returns (membership per node with -1 for nodes without kept edges, quality, n_kept_nodes).
    """
    ki, kj, kw = g.ei[g.kept], g.ej[g.kept], g.AS[g.kept]
    kept_nodes = np.unique(np.concatenate([ki, kj])) if len(ki) else np.zeros(0, dtype=np.int32)
    remap = -np.ones(len(g.nodes), dtype=np.int64)
    remap[kept_nodes] = np.arange(len(kept_nodes))
    G = ig.Graph(n=len(kept_nodes), edges=list(zip(remap[ki].tolist(), remap[kj].tolist())))
    G.es["weight"] = kw.tolist()
    best_q, best_m = -np.inf, None
    for r in range(n_runs):
        part = leidenalg.find_partition(G, leidenalg.RBConfigurationVertexPartition, weights="weight",
                                        resolution_parameter=resolution, seed=seed + r, n_iterations=-1)
        q = part.quality()
        if q > best_q:
            best_q, best_m = q, np.array(part.membership)
    memb = -np.ones(len(g.nodes), dtype=np.int64)
    if best_m is not None:
        memb[kept_nodes] = best_m
    # modularity (unitless, comparable across snapshots) of the best partition
    mod = G.modularity(best_m.tolist(), weights="weight") if best_m is not None and G.ecount() else float("nan")
    return memb, float(mod), len(kept_nodes)
