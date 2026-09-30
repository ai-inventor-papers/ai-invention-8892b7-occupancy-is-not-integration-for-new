"""Feature-matrix assembly for the concept classifier (identical code path for D2, D4a and frame phrases),
model-pipeline factory and bootstrap metrics shared by s3 (training/evaluation) and s7 (application)."""
from __future__ import annotations

import json
import pickle

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, brier_score_loss, cohen_kappa_score,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from common import WORK, SEED
from featlib import EmbStore, emb_text

TH_NAMES = ["th_log_f", "th_src_ratio", "th_log_df", "th_cvalue", "th_right_entropy", "th_left_entropy",
            "th_share_right_ext_noun", "th_share_left_ext_adj_noun", "th_max_right_ext_share", "th_right_boundary_share",
            "th_missing"]


class FeatureSource:
    def __init__(self, with_ctx: bool = True) -> None:
        self.lex = pd.read_parquet(WORK / "lexical.parquet")
        self.lex_names = json.loads((WORK / "lexical_meta.json").read_text())["names"]
        self.lex_idx = {(r.ns, r.id): i for i, r in enumerate(self.lex[["ns", "id"]].itertuples(index=False))}
        self.lexM = self.lex[self.lex_names].to_numpy(dtype=np.float32)
        th = pickle.load(open(WORK / "termhood.pkl", "rb"))
        self.th = th["features"]
        self.th_meta = th["meta"]
        self.mini = EmbStore("minilm")
        self.spec = EmbStore("specter2")
        self.ctx = None
        if with_ctx and (WORK / "emb" / "minilm_ctx.npy").exists():
            self.ctx = EmbStore("minilm_ctx")
            self.ctx_map = json.loads((WORK / "emb" / "ctx_map.json").read_text())

    def build(self, items: list[dict]) -> tuple[np.ndarray, dict[str, list[int]], list[str]]:
        """items: {ns, id, th_qid, text, ctx_key}. Returns X, block -> column indices, column names."""
        L = np.stack([self.lexM[self.lex_idx[(it["ns"], it["id"])]] for it in items])
        T = np.array([[self.th.get(it["th_qid"], {}).get(n, 0.0) if it["th_qid"] in self.th else (1.0 if n == "th_missing" else 0.0)
                       for n in TH_NAMES] for it in items], dtype=np.float32)
        texts = [emb_text(it["text"]) for it in items]
        M = self.mini.get(texts)
        S = self.spec.get(texts)
        blocks_arr = [L, T, M, S]
        names = list(self.lex_names) + TH_NAMES + [f"mini_{i}" for i in range(M.shape[1])] + [f"spec_{i}" for i in range(S.shape[1])]
        if self.ctx is not None:
            C = np.zeros((len(items), M.shape[1]), dtype=np.float32)
            flag = np.zeros((len(items), 1), dtype=np.float32)
            for i, it in enumerate(items):
                cs = self.ctx_map.get(it.get("ctx_key") or "", [])
                if cs:
                    C[i] = self.ctx.get(cs).mean(0)
                else:
                    C[i] = M[i]
                    flag[i] = 1.0
            blocks_arr += [C, flag]
            names += [f"ctx_{i}" for i in range(C.shape[1])] + ["ctx_missing"]
        X = np.concatenate(blocks_arr, axis=1)
        o = 0
        blocks = {}
        for b, arr in zip(["lex", "th", "mini", "spec", "ctx", "ctxflag"], blocks_arr):
            blocks[b] = list(range(o, o + arr.shape[1]))
            o += arr.shape[1]
        return X, blocks, names


def make_pipeline(blocks: dict[str, list[int]], use: list[str], *, pca: int | None, model: str = "lr", C: float = 1.0,
                  class_weight=None, hgb: dict | None = None, multinomial: bool = False) -> Pipeline:
    tr = []
    tab = [c for b in use if b in ("lex", "th", "ctxflag") for c in blocks[b]]
    if tab:
        tr.append(("tab", StandardScaler(), tab))
    for b in use:
        if b in ("mini", "spec", "ctx"):
            n = pca if pca else None
            if n:
                tr.append((b, Pipeline([("pca", PCA(n_components=n, random_state=SEED)), ("sc", StandardScaler())]), blocks[b]))
            else:
                tr.append((b, StandardScaler(), blocks[b]))
    ct = ColumnTransformer(tr, remainder="drop")
    if model == "lr":
        clf = LogisticRegression(C=C, class_weight=class_weight, max_iter=5000, solver="lbfgs")
    else:
        clf = HistGradientBoostingClassifier(random_state=SEED, **(hgb or {}))
    return Pipeline([("ct", ct), ("clf", clf)])


# ------------------------------------------------------------------ metrics
def _prf(y: np.ndarray, yhat: np.ndarray) -> tuple[float, float, float]:
    tp = float(((y == 1) & (yhat == 1)).sum())
    fp = float(((y == 0) & (yhat == 1)).sum())
    fn = float(((y == 1) & (yhat == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def point_metrics(y: np.ndarray, p: np.ndarray | None, yhat: np.ndarray) -> dict:
    P, R, F = _prf(y, yhat)
    out = {"n": int(len(y)), "n_pos": int(y.sum()), "precision": P, "recall": R, "f1": F,
           "accuracy": float((y == yhat).mean()), "balanced_accuracy": float(balanced_accuracy_score(y, yhat)),
           "kappa": float(cohen_kappa_score(y, yhat)) if len(set(y)) > 1 or len(set(yhat)) > 1 else 0.0}
    if p is not None and len(set(y)) > 1:
        out["auc"] = float(roc_auc_score(y, p))
        out["auprc"] = float(average_precision_score(y, p))
        out["brier"] = float(brier_score_loss(y, np.clip(p, 0, 1)))
    return out


def boot_idx(n: int, reps: int = 2000, seed: int = SEED) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(reps, n))


def boot_metrics(y: np.ndarray, p: np.ndarray | None, yhat: np.ndarray, idx: np.ndarray | None = None,
                 keys=("precision", "recall", "f1", "accuracy", "auc", "auprc", "brier", "balanced_accuracy", "kappa")) -> dict:
    idx = boot_idx(len(y)) if idx is None else idx
    res: dict[str, list[float]] = {k: [] for k in keys}
    def put(k, v):
        if k in res:
            res[k].append(v)
    for b in idx:
        yb, hb = y[b], yhat[b]
        P, R, F = _prf(yb, hb)
        put("precision", P)
        put("recall", R)
        put("f1", F)
        put("accuracy", float((yb == hb).mean()))
        if len(set(yb)) > 1:
            if "balanced_accuracy" in res:
                put("balanced_accuracy", float(balanced_accuracy_score(yb, hb)))
            if "kappa" in res:
                put("kappa", float(cohen_kappa_score(yb, hb)))
            if p is not None:
                pb = p[b]
                if "auc" in res:
                    put("auc", float(roc_auc_score(yb, pb)))
                if "auprc" in res:
                    put("auprc", float(average_precision_score(yb, pb)))
                if "brier" in res:
                    put("brier", float(brier_score_loss(yb, np.clip(pb, 0, 1))))
    pt = point_metrics(y, p, yhat)
    out = {}
    for k, v in res.items():
        if v and k in pt:
            out[k] = {"point": pt[k], "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]}
    out["n"] = pt["n"]
    out["n_pos"] = pt["n_pos"]
    return out


def paired_diff(y: np.ndarray, pa: np.ndarray, ha: np.ndarray, pb: np.ndarray | None, hb: np.ndarray,
                idx: np.ndarray | None = None) -> dict:
    """Paired bootstrap of F1 and AUC differences (model a minus model b) on the same resamples."""
    idx = boot_idx(len(y)) if idx is None else idx
    df1, dauc = [], []
    for b in idx:
        yb = y[b]
        df1.append(_prf(yb, ha[b])[2] - _prf(yb, hb[b])[2])
        if len(set(yb)) > 1 and pb is not None:
            dauc.append(roc_auc_score(yb, pa[b]) - roc_auc_score(yb, pb[b]))
    out = {"f1_diff": {"point": _prf(y, ha)[2] - _prf(y, hb)[2],
                       "ci95": [float(np.percentile(df1, 2.5)), float(np.percentile(df1, 97.5))],
                       "p_le_0": float(np.mean(np.array(df1) <= 0))}}
    if dauc:
        out["auc_diff"] = {"point": float(roc_auc_score(y, pa) - roc_auc_score(y, pb)),
                           "ci95": [float(np.percentile(dauc, 2.5)), float(np.percentile(dauc, 97.5))],
                           "p_le_0": float(np.mean(np.array(dauc) <= 0))}
    return out


def best_f1_threshold(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    best = (0.5, -1.0)
    for t in np.unique(np.round(p, 4)):
        f = _prf(y, (p >= t).astype(int))[2]
        if f > best[1]:
            best = (float(t), f)
    return best


def precision_threshold(y: np.ndarray, p: np.ndarray, target: float) -> float | None:
    """Smallest threshold with precision >= target (on the given out-of-fold scores)."""
    for t in np.sort(np.unique(np.round(p, 4))):
        yh = (p >= t).astype(int)
        if yh.sum() == 0:
            break
        if _prf(y, yh)[0] >= target:
            return float(t)
    return None
