"""Vectorised Burt constraint / effective size == networkx; closure on a hand-built graph; xcomm share."""
import math
import sys
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import attach  # noqa: E402
import lib_metrics as lm  # noqa: E402


def _ego_matrix(G: nx.Graph, ego: int) -> tuple[np.ndarray, list]:
    order = [ego] + sorted(n for n in G.nodes if n != ego)
    A = nx.to_numpy_array(G, nodelist=order, weight="w")
    return A, order


def test_constraint_esize_match_networkx():
    rng = np.random.default_rng(0)
    for k in range(20):
        n = int(rng.integers(5, 61))
        G = nx.gnp_random_graph(n, float(rng.uniform(0.1, 0.6)), seed=int(k))
        for u, v in G.edges:
            G[u][v]["w"] = float(rng.uniform(0.1, 5.0))
        ego = max(G.degree, key=lambda t: t[1])[0]
        ego_nodes = [ego] + list(G.neighbors(ego))
        H = G.subgraph(ego_nodes).copy()
        A, _ = _ego_matrix(H, ego)
        c, e, deg = attach.burt_from_ego(A)
        assert deg == H.degree(ego)
        assert math.isclose(c, nx.constraint(H, [ego], weight="w")[ego], rel_tol=1e-9, abs_tol=1e-12)
        assert math.isclose(e, nx.effective_size(H, [ego], weight="w")[ego], rel_tol=1e-9, abs_tol=1e-12)


def test_star_is_open_and_clique_is_closed():
    star = np.zeros((6, 6))
    star[0, 1:] = star[1:, 0] = 1.0
    c_star, e_star, _ = attach.burt_from_ego(star)
    clique = np.ones((6, 6)) - np.eye(6)
    c_cl, e_cl, _ = attach.burt_from_ego(clique)
    assert math.isclose(c_star, 5 * (1 / 5) ** 2)   # 0.2: no indirect paths
    assert math.isclose(e_star, 5.0)                 # all 5 contacts non-redundant
    assert c_cl > c_star and e_cl < e_star


def test_closure_hand_value():
    # 8 background nodes; top-K = nodes 0..4 with a known internal weight
    s = np.array([4.0, 3.0, 3.0, 2.0, 2.0, 1.0, 1.0, 2.0])
    S = s.sum()
    obs = 5.0
    exp = sum(s[i] * s[j] for i in range(5) for j in range(i + 1, 5)) / S
    assert math.isclose(lm.chung_lu_expected(s[:5], S), exp)
    assert math.isclose(lm.closure_log_ratio(obs, exp, 0.5), math.log((obs + 0.5) / (exp + 0.5)))


def test_xcomm_share():
    assert attach.xcomm_share(np.array([1, 1, 1]))[0] == 0.0
    assert attach.xcomm_share(np.array([1, 2, 3]))[0] == 1.0
    v, n = attach.xcomm_share(np.array([1, 1, 2, 2]))
    assert n == 6 and math.isclose(v, 4 / 6)
